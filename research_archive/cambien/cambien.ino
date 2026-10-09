// ============================================================================
// HỆ THỐNG CẢM BIẾN & ĐIỀU KHIỂN CỤC BỘ ESP32 (cambien.ino)
// Điều khiển cục bộ: Quạt (IO18), Bơm (IO19), Đèn (IO21)
// Giám sát dữ liệu: Serial Monitor (Arduino IDE) & Cloud Web Server
// ============================================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <BH1750.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ============================================================================
// ⭐⭐⭐ KHU 1: CẤU HÌNH WIFI, ID VƯỜN & MÃ WEB (ĐIỀN TẠI ĐÂY) ⭐⭐⭐
// ============================================================================

// [1.1] TÊN MẠNG WIFI (SSID) - Điền đúng tên WiFi hoặc Hotspot điện thoại 2.4GHz
const char* ssid          = "Quoc Dat_2.4G";

// [1.2] MẬT KHẨU MẠNG WIFI (PASSWORD) - Điền mật khẩu WiFi vào đây
const char* password      = "88888888";

// [1.3] MÃ VƯỜN (VUON_ID) - Mã số vườn trên Web
const int   VUON_ID       = 30001;

// [1.4] MÃ WEB SERVER (API RENDER) - Đường dẫn gửi dữ liệu cảm biến
const char* serverUrl     = "https://nckh-ai.onrender.com/api/sensors";


// ============================================================================
// KHU 2: CẤU HÌNH CHÂN CẮM (PINOUT) - DỄ DÀNG CHỈNH SỬA
// ============================================================================

// --- 2.1. Chân Relay điều khiển thiết bị ---
#define FAN_PIN          18   // Relay Quạt gió làm mát (IO18)
#define PUMP_PIN         19   // Relay Máy bơm nước tưới ẩm (IO19)
#define LIGHT_PIN        21   // Relay Đèn bổ sung quang hợp (IO21)

// Mức kích Relay (Đa số module relay cho ESP32 là Active LOW: LOW = BẬT, HIGH = TẮT)
#define RELAY_ON   LOW
#define RELAY_OFF  HIGH

// --- 2.2. Chân cảm biến nhiệt độ DS18B20 ---
#define ONE_WIRE_BUS     5    // Chân Data cắm vào IO5 (Kèm trở kéo 4.7k lên 3.3V)

// --- 2.3. Chân cảm biến độ ẩm đất điện dung ---
#define SOIL_PIN         4    // Chân AOUT cắm vào Analog IO4

// --- 2.4. Chân giao tiếp I2C cho Cảm biến ánh sáng BH1750 ---
#define I2C_SDA          8    // SDA cắm IO8 (nếu dùng chân chuẩn thì đổi thành 21)
#define I2C_SCL          9    // SCL cắm IO9 (nếu dùng chân chuẩn thì đổi thành 22)


// ============================================================================
// KHU 3: CẤU HÌNH CÔNG THỨC QUY ĐỔI LUX & NGƯỠNG ĐIỀU KHIỂN
// ============================================================================

// --- 3.1. CÔNG THỨC QUY ĐỔI ÁNH SÁNG CHO CÂY TRỒNG ---
// Khi thử nghiệm trong phòng/hộp che, BH1750 chỉ đo được vài trăm đến ~1.000 lux.
// Ánh sáng tối ưu cho cây trồng ngoài trời: 25.000 - 40.000 lux.
// Công thức: lux_tinh_toan = raw_lux * LIGHT_SCALE_FACTOR
// Mặc định nhân 30.0 (Bạn có thể tự chỉnh hệ số này tùy môi trường thử nghiệm):
const float LIGHT_SCALE_FACTOR   = 30.0;

// Ngưỡng điều khiển ĐÈN (tính theo lux sau quy đổi)
const float LIGHT_ON_THRESHOLD   = 20000.0; // < 20.000 lux: BẬT đèn
const float LIGHT_OFF_THRESHOLD  = 25000.0; // >= 25.000 lux: TẮT đèn (Tránh chớp tắt liên tục)

// --- 3.2. Ngưỡng điều khiển QUẠT (Nhiệt độ °C) ---
const float TEMP_FAN_ON          = 30.0;    // > 30.0°C: BẬT quạt
const float TEMP_FAN_OFF         = 28.0;    // <= 28.0°C: TẮT quạt

// --- 3.3. Ngưỡng điều khiển MÁY BƠM (Độ ẩm đất %) ---
const int   PUMP_ON_THRESHOLD    = 40;      // < 40%: BẬT máy bơm
const int   PUMP_OFF_THRESHOLD   = 60;      // >= 60%: TẮT máy bơm

// Hiệu chuẩn ADC cảm biến đất
const int   SOIL_DRY_ADC         = 3500;    // Đất khô
const int   SOIL_WET_ADC         = 1200;    // Đất ướt ngập nước


// ============================================================================
// KHU 4: CẤU HÌNH THỜI GIAN CHU KỲ (CHU KỲ NGẮN ĐỂ THỬ NGHIỆM DỄ DÀNG)
// ============================================================================

// Chu kỳ đọc cảm biến & in lên Terminal Arduino IDE (2000ms = 2 giây)
const unsigned long SENSOR_READ_INTERVAL_MS = 2000UL;

// Chu kỳ gửi dữ liệu lên Server (15000ms = 15 giây - không gửi dồn dập)
const unsigned long SERVER_SEND_INTERVAL_MS = 15000UL;


// ============================================================================
// KHAI BÁO BIẾN & ĐỐI TƯỢNG CẢM BIẾN
// ============================================================================
OneWire           oneWire(ONE_WIRE_BUS);
DallasTemperature ds18b20(&oneWire);
BH1750            lightMeter;

bool bh1750Ready    = false;
bool fanState       = false;
bool pumpState      = false;
bool lightState     = false;

float currentTemp   = 25.0;
int   currentHum    = 50;
float currentRawLux = 0.0;
float currentLux    = 0.0;

unsigned long lastReadTime = 0;
unsigned long lastSendTime = 0;


// ============================================================================
// KHU 5: ĐIỀU KHIỂN RELAY CỤC BỘ
// ============================================================================

void initRelays() {
  pinMode(FAN_PIN,   OUTPUT);
  pinMode(PUMP_PIN,  OUTPUT);
  pinMode(LIGHT_PIN, OUTPUT);

  digitalWrite(FAN_PIN,   RELAY_OFF);
  digitalWrite(PUMP_PIN,  RELAY_OFF);
  digitalWrite(LIGHT_PIN, RELAY_OFF);
}

void setFan(bool on) {
  if (fanState == on) return;
  fanState = on;
  digitalWrite(FAN_PIN, on ? RELAY_ON : RELAY_OFF);
  Serial.print("   -> [QUAT] "); Serial.println(on ? "BAT (Nhiet do > 30°C)" : "TAT");
}

void setPump(bool on) {
  if (pumpState == on) return;
  pumpState = on;
  digitalWrite(PUMP_PIN, on ? RELAY_ON : RELAY_OFF);
  Serial.print("   -> [BOM] "); Serial.println(on ? "BAT (Do am < 40%)" : "TAT");
}

void setLight(bool on) {
  if (lightState == on) return;
  lightState = on;
  digitalWrite(LIGHT_PIN, on ? RELAY_ON : RELAY_OFF);
  Serial.print("   -> [DEN] "); Serial.println(on ? "BAT (Anh sang < 20.000 lux)" : "TAT");
}

void runLocalControl() {
  // 1. Quạt
  if (currentTemp > TEMP_FAN_ON)       setFan(true);
  else if (currentTemp <= TEMP_FAN_OFF) setFan(false);

  // 2. Bơm
  if (currentHum >= 0) {
    if (currentHum < PUMP_ON_THRESHOLD)       setPump(true);
    else if (currentHum >= PUMP_OFF_THRESHOLD) setPump(false);
  }

  // 3. Đèn
  if (bh1750Ready && currentLux >= 0) {
    if (currentLux < LIGHT_ON_THRESHOLD)       setLight(true);
    else if (currentLux >= LIGHT_OFF_THRESHOLD) setLight(false);
  }
}


// ============================================================================
// KHU 6: ĐỌC CẢM BIẾN & IN TERMINAL ARDUINO IDE
// ============================================================================

void initSensors() {
  ds18b20.begin();

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setTimeOut(1000);

  if (lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    bh1750Ready = true;
    Serial.println("✓ [BH1750] Ket noi cam bien anh sang thanh cong!");
  } else {
    bh1750Ready = false;
    Serial.println("⚠ [BH1750] Khong tim thay cam bien anh sang!");
  }
}

float readTemperature() {
  ds18b20.requestTemperatures();
  float t = ds18b20.getTempCByIndex(0);
  if (t == -127.00 || t == DEVICE_DISCONNECTED_C) return -1.0;
  return t;
}

int readSoilHumidity() {
  long sum = 0;
  for (int i = 0; i < 5; i++) {
    sum += analogRead(SOIL_PIN);
    delay(10);
  }
  int adcVal = sum / 5;
  if (adcVal < 100) return -1;
  return constrain(map(adcVal, SOIL_DRY_ADC, SOIL_WET_ADC, 0, 100), 0, 100);
}

void readLightData(float &raw, float &calib) {
  if (!bh1750Ready) { raw = -1.0; calib = -1.0; return; }
  float lux = lightMeter.readLightLevel();
  if (lux < 0) { raw = -1.0; calib = -1.0; }
  else {
    raw = lux;
    calib = raw * LIGHT_SCALE_FACTOR;
  }
}

void printToTerminal() {
  Serial.println("==================== [SERIAL TERMINAL] ====================");
  
  // Nhiệt độ
  Serial.print("🌡️  Nhiet do  : ");
  if (currentTemp >= 0) {
    Serial.print(currentTemp, 1); Serial.print(" °C");
    if (currentTemp > TEMP_FAN_ON) Serial.print("  [NONG -> Bat quat]");
    else if (currentTemp >= 22.0 && currentTemp <= 28.0) Serial.print("  [TOI UU (22-28°C)]");
    Serial.println();
  } else {
    Serial.println("Loi ket noi DS18B20");
  }

  // Độ ẩm đất
  Serial.print("💧 Do am dat : ");
  if (currentHum >= 0) {
    Serial.print(currentHum); Serial.print(" %");
    if (currentHum < PUMP_ON_THRESHOLD) Serial.print("  [KHO -> Bat bom]");
    else if (currentHum >= 60 && currentHum <= 70) Serial.print("  [TOI UU (60-70%)]");
    Serial.println();
  } else {
    Serial.println("Loi ket noi cam bien dat");
  }

  // Ánh sáng
  Serial.print("☀️  Anh sang  : ");
  if (bh1750Ready && currentRawLux >= 0) {
    Serial.print(currentLux, 0);
    Serial.print(" lux (Gia tri goc: ");
    Serial.print(currentRawLux, 1);
    Serial.print(" lx * ");
    Serial.print(LIGHT_SCALE_FACTOR, 1);
    Serial.print(")");
    if (currentLux < LIGHT_ON_THRESHOLD) Serial.print("  [THIEU SANG -> Bat den]");
    else if (currentLux >= 25000.0 && currentLux <= 40000.0) Serial.print("  [TOI UU (25k-40k lux)]");
    else if (currentLux > 40000.0) Serial.print("  [THUA SANG (>40k lux)]");
    Serial.println();
  } else {
    Serial.println("Chua ket noi BH1750");
  }

  // Trạng thái thiết bị
  Serial.print("⚙️  Relay     : ");
  Serial.print("Quat ["); Serial.print(fanState ? "BAT" : "TAT"); Serial.print("] | ");
  Serial.print("Bom [");  Serial.print(pumpState ? "BAT" : "TAT"); Serial.print("] | ");
  Serial.print("Den [");  Serial.print(lightState ? "BAT" : "TAT"); Serial.println("]");
  Serial.println("===========================================================\n");
}


// ============================================================================
// KHU 7: KẾT NỐI WIFI
// ============================================================================

void setupWiFi() {
  Serial.print("[WIFI] Dang ket noi: "); Serial.println(ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 20) {
    delay(500);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ [WIFI] Da ket noi! IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n⚠ [WIFI] Ket noi that bai! ESP32 van tu dong chay cuc bo.");
  }
}


// ============================================================================
// KHU 8: GỬI DỮ LIỆU LÊN SERVER CLOUD (HTTP POST JSON)
// ============================================================================

void sendDataToServer() {
  if (WiFi.status() != WL_CONNECTED) return;

  Serial.println("📡 [CLOUD] Dang gui du lieu len Server Render...");
  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  if (http.begin(client, serverUrl)) {
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(6000);

    StaticJsonDocument<256> doc;
    doc["vuon_id"]     = VUON_ID;
    doc["temperature"] = (currentTemp >= 0) ? currentTemp : 25.0;
    doc["humidity"]    = (currentHum >= 0) ? currentHum : 0;
    doc["light"]       = (currentLux >= 0) ? round(currentLux) : -1;

    String body;
    serializeJson(doc, body);

    int httpCode = http.POST(body);
    if (httpCode == 200) {
      Serial.print("✓ [CLOUD] Gui thanh cong (HTTP 200). Lux: ");
      Serial.println(doc["light"].as<float>());
    } else {
      Serial.print("⚠ [CLOUD] Loi HTTP: "); Serial.println(httpCode);
    }
    http.end();
  }
  client.stop();
}


// ============================================================================
// KHU 9: SETUP & MAIN LOOP
// ============================================================================

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("\n--- ESP32 CAM BIEN NONG NGHIEP KHOI DONG ---");

  initRelays();
  initSensors();
  setupWiFi();

  Serial.println("--- HE THONG DA SAN SANG ---\n");
}

void loop() {
  unsigned long now = millis();

  // Chu kỳ 1: Đọc cảm biến + In Terminal + Điều khiển Relay (Mỗi 2 giây)
  if (now - lastReadTime >= SENSOR_READ_INTERVAL_MS) {
    lastReadTime = now;

    currentTemp = readTemperature();
    currentHum  = readSoilHumidity();
    readLightData(currentRawLux, currentLux);

    printToTerminal();
    runLocalControl();
  }

  // Chu kỳ 2: Gửi lên Server (Mỗi 15 giây)
  if (now - lastSendTime >= SERVER_SEND_INTERVAL_MS) {
    lastSendTime = now;

    if (WiFi.status() != WL_CONNECTED) {
      WiFi.reconnect();
    }
    sendDataToServer();
  }
}