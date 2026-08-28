// ============================================================
// esp32_sensor.ino — Hệ thống IoT Nông nghiệp v3
//
// LUỒNG CHÍNH:
//   1. Đọc cảm biến nhiệt độ & độ ẩm
//   2. Nếu độ ẩm THẤP → bật máy bơm cục bộ
//      → Tiếp tục đọc lại mỗi 3 giây cho đến khi đủ ẩm
//      → Tắt máy bơm khi độ ẩm đạt mức ổn định
//   3. Gửi dữ liệu (sau bơm xong) lên server
//   4. Nhận lệnh quạt / chế độ manual từ server
// ============================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ============================================================
// CẤU HÌNH WiFi
// ============================================================
const char* WIFI_SSID     = "Quoc Dat_2.4G";
const char* WIFI_PASSWORD = "88888888";

// ============================================================
// CẤU HÌNH CHÂN I/O
// ============================================================
#define ONE_WIRE_BUS    5     // DS18B20 (cần trở kéo 4.7kΩ lên 3.3V)
#define SOIL_PIN        4     // Cảm biến độ ẩm đất (ADC)
#define RELAY_FAN_PIN   18    // Quạt giải nhiệt  → IO18
#define RELAY_PUMP_PIN  19    // Máy bơm nước     → IO19

// Active LOW (relay module phổ biến: BẬT khi nhận LOW)
#define RELAY_ON   LOW
#define RELAY_OFF  HIGH

// ============================================================
// HIỆU CHUẨN CẢM BIẾN ĐỘ ẨM
// ============================================================
const int DRY_ADC = 3500;   // ADC khi đất khô hoàn toàn
const int WET_ADC = 1200;   // ADC khi đất ngập nước

// ============================================================
// NGƯỠNG ĐIỀU KHIỂN MÁY BƠM (Hysteresis — ngưỡng kép)
// ============================================================
//  • Bật bơm khi độ ẩm < PUMP_ON_THRESHOLD
//  • Tiếp tục bơm cho đến khi độ ẩm >= PUMP_OFF_THRESHOLD
//  • Khoảng trống giữa 2 ngưỡng tránh bơm nhấp nháy liên tục
const int PUMP_ON_THRESHOLD  = 40;  // % — Dưới ngưỡng này → BẬT bơm
const int PUMP_OFF_THRESHOLD = 60;  // % — Đạt ngưỡng này  → TẮT bơm

// Thời gian chờ giữa các lần đọc lại trong lúc đang bơm (ms)
const int PUMP_RECHECK_MS = 3000;

// Thời gian bơm tối đa (phòng tràn nước khi cảm biến lỗi): 5 phút
const unsigned long PUMP_MAX_DURATION_MS = 5UL * 60UL * 1000UL;

// ============================================================
// NGƯỠNG ĐIỀU KHIỂN NHIỆT ĐỘ (Cho quạt — Server quyết định)
// ============================================================
const float FAN_ON_TEMP  = 30.0;  // °C — Server bật quạt trên ngưỡng này

// ============================================================
// CẤU HÌNH SERVER & VƯỜN
// ============================================================
const char* SERVER_URL = "https://nckh-ai.onrender.com/api/sensors";
const int   VUON_ID    = 30001;

// ============================================================
// CẤU HÌNH LẤY TRUNG BÌNH (Chống nhiễu)
// ============================================================
const int NUM_SAMPLES     = 10;
const int SAMPLE_DELAY_MS = 200;   // 10 × 200ms ≈ 2 giây/cảm biến

// ============================================================
// CẤU HÌNH KHÁC
// ============================================================
const int          HTTP_TIMEOUT_MS  = 8000;
const unsigned int LOOP_DELAY_MS    = 5000;  // Delay cuối mỗi vòng lặp

// ============================================================
// BIẾN TOÀN CỤC
// ============================================================
bool currentFanState  = false;
bool currentPumpState = false;
bool isManualMode     = false;  // Nếu true → ESP32 không tự điều khiển bơm

OneWire           oneWire(ONE_WIRE_BUS);
DallasTemperature ds18b20(&oneWire);

// ============================================================
// KHAI BÁO HÀM (Prototypes)
// ============================================================
float readTemperature();
int   readHumidity();
int   readHumidityFast();   // Đọc nhanh (3 mẫu) dùng trong vòng bơm
void  runPumpUntilWet();
void  setFan(bool on);
void  setPump(bool on);
void  sendDataAndControl(float temperature, int humidity);
void  printSensorData(float temperature, int humidity);
void  connectWiFi();

// ============================================================
// SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("========================================");
  Serial.println("  ESP32 - IoT Nong Nghiep v3           ");
  Serial.println("  Bom tu dong: Hysteresis Control       ");
  Serial.println("========================================");

  // Relay: TẮT hết khi khởi động tránh kích nhầm
  pinMode(RELAY_FAN_PIN,  OUTPUT);
  pinMode(RELAY_PUMP_PIN, OUTPUT);
  digitalWrite(RELAY_FAN_PIN,  RELAY_OFF);
  digitalWrite(RELAY_PUMP_PIN, RELAY_OFF);

  ds18b20.begin();
  connectWiFi();
}

// ============================================================
// LOOP CHÍNH
// ============================================================
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wifi mat ket noi — thu lai...");
    connectWiFi();
    return;
  }

  // 1. Đọc cảm biến
  float temperature = readTemperature();
  int   humidity    = readHumidity();

  if (humidity < 0) {
    Serial.println("Cam bien do am chua ket noi (ADC < 100). Bo qua...");
    delay(3000);
    return;
  }

  printSensorData(temperature, humidity);

  // 2. Xử lý máy bơm (chỉ khi không ở chế độ manual)
  if (!isManualMode) {
    if (humidity < PUMP_ON_THRESHOLD) {
      // Vào vòng bơm — chạy đến khi đủ ẩm rồi mới thoát
      runPumpUntilWet();

      // Đọc lại sau khi bơm xong để gửi số liệu chính xác
      temperature = readTemperature();
      humidity    = readHumidity();
      if (humidity < 0) humidity = PUMP_OFF_THRESHOLD; // Fallback an toàn
    }
  }

  // 3. Gửi dữ liệu lên server (sau khi bơm xong)
  //    Server sẽ trả về lệnh quạt + trạng thái manual
  sendDataAndControl(temperature, humidity);

  delay(LOOP_DELAY_MS);
}

// ============================================================
// VÒNG BƠM: chạy cho đến khi độ ẩm đạt PUMP_OFF_THRESHOLD
// ============================================================
void runPumpUntilWet() {
  Serial.println("");
  Serial.println("===========================================");
  Serial.println("[BOM] Do am thap! Bat may bom...");
  Serial.print  ("[BOM] Bat bom khi: < "); Serial.print(PUMP_ON_THRESHOLD); Serial.println("%");
  Serial.print  ("[BOM] Tat bom khi: >= "); Serial.print(PUMP_OFF_THRESHOLD); Serial.println("%");
  Serial.println("===========================================");

  setPump(true);

  unsigned long startTime = millis();
  int currentHumidity = readHumidityFast();

  while (currentHumidity < PUMP_OFF_THRESHOLD) {
    // Kiểm tra timeout an toàn (tránh tràn nước)
    if (millis() - startTime > PUMP_MAX_DURATION_MS) {
      Serial.println("[BOM] CANH BAO: Da dat thoi gian bom toi da (5 phut)! Tat bom.");
      break;
    }

    Serial.print("[BOM] Dang bom... Do am hien tai: ");
    Serial.print(currentHumidity);
    Serial.print("% | Muc tieu: ");
    Serial.print(PUMP_OFF_THRESHOLD);
    Serial.println("%");

    delay(PUMP_RECHECK_MS);
    currentHumidity = readHumidityFast();
  }

  setPump(false);

  unsigned long duration = (millis() - startTime) / 1000;
  Serial.println("===========================================");
  Serial.print  ("[BOM] Bom xong! Do am dat: ");
  Serial.print  (currentHumidity); Serial.println("%");
  Serial.print  ("[BOM] Thoi gian bom: "); Serial.print(duration); Serial.println(" giay");
  Serial.println("[BOM] Gui du lieu len server...");
  Serial.println("===========================================\n");
}

// ============================================================
// ĐỌC NHIỆT ĐỘ (Trung bình NUM_SAMPLES lần)
// ============================================================
float readTemperature() {
  float sum   = 0;
  int   count = 0;
  for (int i = 0; i < NUM_SAMPLES; i++) {
    ds18b20.requestTemperatures();
    float t = ds18b20.getTempCByIndex(0);
    if (t != -127.00 && t != DEVICE_DISCONNECTED_C) {
      sum += t;
      count++;
    }
    delay(SAMPLE_DELAY_MS);
  }
  if (count == 0) {
    Serial.println("DS18B20 loi! Dung gia tri 25.0°C.");
    return 25.0;
  }
  return sum / count;
}

// ============================================================
// ĐỌC ĐỘ ẨM ĐẤT (Trung bình NUM_SAMPLES lần — chính xác)
// Trả về -1 nếu cảm biến chưa cắm
// ============================================================
int readHumidity() {
  long adcSum = 0;
  for (int i = 0; i < NUM_SAMPLES; i++) {
    adcSum += analogRead(SOIL_PIN);
    delay(SAMPLE_DELAY_MS);
  }
  int adcAvg = adcSum / NUM_SAMPLES;
  if (adcAvg < 100) return -1;
  return constrain(map(adcAvg, DRY_ADC, WET_ADC, 0, 100), 0, 100);
}

// ============================================================
// ĐỌC ĐỘ ẨM ĐẤT NHANH (3 mẫu — dùng trong vòng bơm)
// ============================================================
int readHumidityFast() {
  long adcSum = 0;
  const int FAST_SAMPLES = 3;
  for (int i = 0; i < FAST_SAMPLES; i++) {
    adcSum += analogRead(SOIL_PIN);
    delay(100);
  }
  int adcAvg = adcSum / FAST_SAMPLES;
  if (adcAvg < 100) return 0;
  return constrain(map(adcAvg, DRY_ADC, WET_ADC, 0, 100), 0, 100);
}

// ============================================================
// ĐẶT TRẠNG THÁI RELAY (chỉ gọi digitalWrite khi state thay đổi)
// ============================================================
void setFan(bool on) {
  if (on == currentFanState) return;
  currentFanState = on;
  digitalWrite(RELAY_FAN_PIN, on ? RELAY_ON : RELAY_OFF);
  Serial.print("Quat: "); Serial.println(on ? "BAT" : "TAT");
}

void setPump(bool on) {
  if (on == currentPumpState) return;
  currentPumpState = on;
  digitalWrite(RELAY_PUMP_PIN, on ? RELAY_ON : RELAY_OFF);
  Serial.print("May bom: "); Serial.println(on ? "BAT" : "TAT");
}

// ============================================================
// GỬI DỮ LIỆU → NHẬN LỆNH ĐIỀU KHIỂN QUẠT / MANUAL
// ============================================================
void sendDataAndControl(float temperature, int humidity) {
  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(HTTP_TIMEOUT_MS);

  StaticJsonDocument<256> reqDoc;
  reqDoc["vuon_id"]     = VUON_ID;
  reqDoc["temperature"] = temperature;
  reqDoc["humidity"]    = humidity;
  reqDoc["light"]       = -1;       // BH1750 chưa kết nối
  reqDoc["pump_state"]  = currentPumpState;

  String body;
  serializeJson(reqDoc, body);

  int httpCode = http.POST(body);

  if (httpCode == 200) {
    String payload = http.getString();
    Serial.print("Server: "); Serial.println(payload);

    StaticJsonDocument<128> resDoc;
    DeserializationError err = deserializeJson(resDoc, payload);

    if (!err) {
      // Cập nhật chế độ manual (nếu người dùng bật trên web)
      isManualMode = resDoc["manual"] | false;

      // Quạt do server quyết định (dựa trên nhiệt độ)
      setFan(resDoc["fan_state"] | false);

      // Nếu đang manual: server cũng kiểm soát bơm
      if (isManualMode) {
        setPump(resDoc["pump_state"] | false);
      }
    } else {
      Serial.print("Loi parse JSON: "); Serial.println(err.c_str());
    }
  } else {
    Serial.print("Loi POST HTTP "); Serial.println(httpCode);
  }

  http.end();
}

// ============================================================
// IN DỮ LIỆU RA SERIAL MONITOR
// ============================================================
void printSensorData(float temperature, int humidity) {
  Serial.println("===== SENSOR DATA =====");
  Serial.print("Nhiet do  : "); Serial.print(temperature, 2); Serial.println(" C");
  Serial.print("Do am dat : "); Serial.print(humidity);       Serial.println(" %");
  Serial.print("Quat      : "); Serial.println(currentFanState  ? "BAT" : "TAT");
  Serial.print("May bom   : "); Serial.println(currentPumpState ? "BAT" : "TAT");
  Serial.print("Che do    : "); Serial.println(isManualMode ? "MANUAL (Web)" : "TU DONG");
  Serial.println("=======================");
}

// ============================================================
// KẾT NỐI WiFi (Có Retry)
// ============================================================
void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int retries = 0;
  Serial.print("Dang ket noi WiFi");
  while (WiFi.status() != WL_CONNECTED && retries < 20) {
    delay(1000);
    Serial.print(".");
    retries++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi OK! IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\nWiFi that bai. Thu lai sau...");
  }
}
