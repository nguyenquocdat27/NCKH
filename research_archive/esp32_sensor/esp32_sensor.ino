// ============================================================================
// HỆ THỐNG IoT NÔNG NGHIỆP THÔNG MINH - ESP32
// Điều khiển cục bộ: Quạt (IO18), Máy bơm (IO19), Đèn (IO21)
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

// [1.1] TÊN MẠNG WIFI (SSID) - Điền đúng tên WiFi nhà bạn hoặc Hotspot 2.4GHz
const char* WIFI_SSID     = "Quoc Dat_2.4G";

// [1.2] MẬT KHẨU MẠNG WIFI (PASSWORD) - Điền mật khẩu WiFi vào đây
const char* WIFI_PASSWORD = "88888888";

// [1.3] MÃ VƯỜN (VUON_ID) - Khớp với ID vườn trên Website hệ thống
const int   VUON_ID       = 30001;

// [1.4] MÃ WEB SERVER (URL API RENDER) - Nơi ESP32 gửi dữ liệu cảm biến lên
const char* SERVER_URL    = "https://nckh-ai.onrender.com/api/sensors";
const int   HTTP_TIMEOUT  = 6000; // Timeout chờ kết nối server (6s)


// ============================================================================
// KHU 2: CẤU HÌNH CHÂN CẮM (PINOUT) - BẠN CÓ THỂ TỰ ĐỔI CHÂN TẠI ĐÂY
// ============================================================================

// --- 2.1. Chân Relay điều khiển thiết bị ---
#define RELAY_FAN_PIN    18   // Relay Quạt gió làm mát (IO18)
#define RELAY_PUMP_PIN   19   // Relay Máy bơm nước tưới ẩm (IO19)
#define RELAY_LIGHT_PIN  21   // Relay Đèn bổ sung ánh sáng (IO21)

// Kiểu kích của Module Relay:
// Hầu hết module relay ESP32 là Active LOW (Xuất mức LOW = BẬT, HIGH = TẮT)
#define RELAY_ON   LOW
#define RELAY_OFF  HIGH

// --- 2.2. Chân cảm biến nhiệt độ nước/đất (DS18B20) ---
#define ONE_WIRE_BUS     5    // Chân DATA cắm vào IO5 (Cần trở kéo 4.7k lên 3.3V)

// --- 2.3. Chân cảm biến độ ẩm đất (Capacitive Soil Sensor) ---
#define SOIL_ANALOG_PIN  4    // Chân AOUT cắm vào chân Analog IO4

// --- 2.4. Chân giao tiếp I2C cho Cảm biến ánh sáng (BH1750) ---
// Chân mặc định cho ESP32-S3/ESP32:
// Nếu dùng ESP32 chuẩn (NodeMCU-32S): SDA thường là 21, SCL là 22
// Nếu board của bạn đã nối SDA=8, SCL=9 thì giữ nguyên bên dưới:
#define I2C_SDA_PIN      8    // Chân SDA của BH1750 cắm vào IO8
#define I2C_SCL_PIN      9    // Chân SCL của BH1750 cắm vào IO9


// ============================================================================
// KHU 3: CẤU HÌNH CÔNG THỨC QUY ĐỔI LUX & NGƯỠNG ĐIỀU KHIỂN
// ============================================================================

// --- 3.1. CÔNG THỨC QUY ĐỔI ÁNH SÁNG BH1750 ---
// Khi thử nghiệm trong nhà/phòng lab hoặc cảm biến đặt sau hộp kính,
// BH1750 chỉ đo được từ vài trăm đến ~1.000 lux.
// Trong khi cây trồng ngoài trời cần ngưỡng 20.000 - 40.000 lux.
//
// Công thức: lux_hien_thi = raw_lux * LIGHT_SCALE_FACTOR
// Mặc định hệ số nhân = 30.0:
//   - raw = 300 lx (tối)        -> tính ra:  9.000 lux (Thiếu sáng -> BẬT ĐÈN)
//   - raw = 650 lx              -> tính ra: 19.500 lux (Thiếu sáng -> BẬT ĐÈN)
//   - raw = 1.000 lx (sáng tốt) -> tính ra: 30.000 lux (Trong ngưỡng tối ưu -> TẮT ĐÈN)
//   - raw = 1.400 lx (rất sáng) -> tính ra: 42.000 lux (Thừa sáng)
// (Nếu mang ra ngoài trời nắng to trực tiếp, bạn có thể chỉnh lại thành 1.0)
const float LIGHT_SCALE_FACTOR = 30.0;

// Ngưỡng điều khiển ĐÈN (tính theo lux sau khi quy đổi)
const float LIGHT_ON_THRESHOLD   = 20000.0; // < 20.000 lux: BẬT đèn
const float LIGHT_OFF_THRESHOLD  = 25000.0; // >= 25.000 lux: TẮT đèn (Hysteresis chống nháy đèn)

// --- 3.2. Ngưỡng điều khiển QUẠT (Nhiệt độ DS18B20 °C) ---
const float TEMP_FAN_ON          = 30.0;    // > 30.0°C: BẬT quạt làm mát
const float TEMP_FAN_OFF         = 28.0;    // <= 28.0°C: TẮT quạt

// --- 3.3. Ngưỡng điều khiển MÁY BƠM (Độ ẩm đất %) ---
const int   PUMP_ON_THRESHOLD    = 40;      // < 40%: BẬT máy bơm
const int   PUMP_OFF_THRESHOLD   = 60;      // >= 60%: TẮT máy bơm

// Hiệu chuẩn ADC cảm biến độ ẩm đất
const int   SOIL_DRY_ADC         = 3500;    // Giá trị ADC khi đất khô hoàn toàn
const int   SOIL_WET_ADC         = 1200;    // Giá trị ADC khi đất ngập nước


// ============================================================================
// KHU 4: CẤU HÌNH CHU KỲ HOẠT ĐỘNG
// ============================================================================

// Chu kỳ đọc cảm biến & in lên Terminal Arduino IDE (2000ms = 2 giây)
// Giúp bạn theo dõi nhanh và thử nghiệm tức thì mà không phải chờ lâu.
const unsigned long SENSOR_READ_INTERVAL_MS = 2000UL;

// Chu kỳ gửi dữ liệu lên Cloud Server Render (15000ms = 15 giây)
// Gửi định kỳ để không làm nghẽn mạng và tiết kiệm tài nguyên Server.
const unsigned long SERVER_SEND_INTERVAL_MS = 15000UL;


// ============================================================================
// KHAI BÁO BIẾN TOÀN CỤC & ĐỐI TƯỢNG CẢM BIẾN
// ============================================================================
OneWire           oneWire(ONE_WIRE_BUS);
DallasTemperature ds18b20(&oneWire);
BH1750            lightMeter;

bool bh1750Connected   = false;
bool fanState          = false;
bool pumpState         = false;
bool lightState        = false;

// Biến lưu dữ liệu đo mới nhất
float currentTemp      = 25.0;
int   currentHumidity  = 50;
float currentRawLux    = 0.0;
float currentCalibLux  = 0.0;

// Bộ đếm thời gian Non-blocking (Không dùng delay làm nghẽn chương trình)
unsigned long lastSensorReadTime = 0;
unsigned long lastServerSendTime = 0;


// ============================================================================
// KHU 5: CÁC HÀM XỬ LÝ RELAY (ĐIỀU KHIỂN CỤC BỘ)
// ============================================================================

void initRelays() {
  pinMode(RELAY_FAN_PIN,   OUTPUT);
  pinMode(RELAY_PUMP_PIN,  OUTPUT);
  pinMode(RELAY_LIGHT_PIN, OUTPUT);

  // Mặc định khởi động tắt hết thiết bị để đảm bảo an toàn
  digitalWrite(RELAY_FAN_PIN,   RELAY_OFF);
  digitalWrite(RELAY_PUMP_PIN,  RELAY_OFF);
  digitalWrite(RELAY_LIGHT_PIN, RELAY_OFF);
}

void setFan(bool enable) {
  if (fanState == enable) return;
  fanState = enable;
  digitalWrite(RELAY_FAN_PIN, enable ? RELAY_ON : RELAY_OFF);
  Serial.print("   -> [QUAT] ");
  Serial.println(enable ? "BAT (Nhiet do cao)" : "TAT (Nhiet do on dinh)");
}

void setPump(bool enable) {
  if (pumpState == enable) return;
  pumpState = enable;
  digitalWrite(RELAY_PUMP_PIN, enable ? RELAY_ON : RELAY_OFF);
  Serial.print("   -> [BOM] ");
  Serial.println(enable ? "BAT (Dat kho)" : "TAT (Da du am)");
}

void setLight(bool enable) {
  if (lightState == enable) return;
  lightState = enable;
  digitalWrite(RELAY_LIGHT_PIN, enable ? RELAY_ON : RELAY_OFF);
  Serial.print("   -> [DEN] ");
  Serial.println(enable ? "BAT (Thieu anh sang)" : "TAT (Du anh sang)");
}

// Logic tự động quyết định trạng thái thiết bị cục bộ dựa trên số liệu cảm biến
void runLocalAutomation() {
  // 1. Quạt làm mát
  if (currentTemp > TEMP_FAN_ON) {
    setFan(true);
  } else if (currentTemp <= TEMP_FAN_OFF) {
    setFan(false);
  }

  // 2. Máy bơm tưới nước
  if (currentHumidity >= 0) {
    if (currentHumidity < PUMP_ON_THRESHOLD) {
      setPump(true);
    } else if (currentHumidity >= PUMP_OFF_THRESHOLD) {
      setPump(false);
    }
  }

  // 3. Đèn bổ sung ánh sáng cho cây
  if (bh1750Connected && currentCalibLux >= 0) {
    if (currentCalibLux < LIGHT_ON_THRESHOLD) {
      setLight(true);   // Dưới 20.000 lux -> Bật đèn
    } else if (currentCalibLux >= LIGHT_OFF_THRESHOLD) {
      setLight(false);  // Từ 25.000 lux trở lên -> Tắt đèn
    }
  }
}


// ============================================================================
// KHU 6: CÁC HÀM ĐỌC CẢM BIẾN (SENSOR DRIVERS)
// ============================================================================

void initSensors() {
  // Khởi tạo DS18B20
  ds18b20.begin();

  // Khởi tạo I2C cho BH1750
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  Wire.setTimeOut(1000);

  if (lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    bh1750Connected = true;
    Serial.println("✓ [BH1750] Da ket noi cam bien anh sang I2C thanh cong!");
  } else {
    bh1750Connected = false;
    Serial.println("⚠ [BH1750] Chua tim thay cam bien! Kiem tra day SDA/SCL/VCC/GND");
  }
}

// Đọc nhiệt độ (°C) từ DS18B20
float readTemperature() {
  ds18b20.requestTemperatures();
  float temp = ds18b20.getTempCByIndex(0);
  if (temp == -127.00 || temp == DEVICE_DISCONNECTED_C) {
    return -1.0; // Báo lỗi chưa cắm cảm biến
  }
  return temp;
}

// Đọc độ ẩm đất (%) từ cảm biến điện dung
int readSoilHumidity() {
  long sum = 0;
  for (int i = 0; i < 5; i++) {
    sum += analogRead(SOIL_ANALOG_PIN);
    delay(10);
  }
  int adcVal = sum / 5;

  if (adcVal < 100) return -1; // Cảm biến bị lỏng dây

  int percent = map(adcVal, SOIL_DRY_ADC, SOIL_WET_ADC, 0, 100);
  return constrain(percent, 0, 100);
}

// Đọc ánh sáng từ BH1750 và áp dụng công thức quy đổi
void readLightData(float &rawLux, float &calibLux) {
  if (!bh1750Connected) {
    rawLux = -1.0;
    calibLux = -1.0;
    return;
  }

  float lux = lightMeter.readLightLevel();
  if (lux < 0) {
    rawLux = -1.0;
    calibLux = -1.0;
  } else {
    rawLux = lux;
    // Áp dụng công thức quy đổi sang dải cây trồng
    calibLux = rawLux * LIGHT_SCALE_FACTOR;
  }
}

// In toàn bộ dữ liệu ra Terminal của Arduino IDE (Serial Monitor)
void printTerminalReport() {
  Serial.println("==================== [ESP32 SENSOR TERMINAL] ====================");
  
  // 1. Nhiệt độ
  Serial.print("🌡️  Nhiet do  : ");
  if (currentTemp >= 0) {
    Serial.print(currentTemp, 1);
    Serial.print(" °C");
    if (currentTemp > TEMP_FAN_ON) Serial.print("  [NONG -> Can bat quat]");
    else if (currentTemp >= 22.0 && currentTemp <= 28.0) Serial.print("  [TOI UU (22-28°C)]");
    Serial.println();
  } else {
    Serial.println("Loi ket noi DS18B20");
  }

  // 2. Độ ẩm đất
  Serial.print("💧 Do am dat : ");
  if (currentHumidity >= 0) {
    Serial.print(currentHumidity);
    Serial.print(" %");
    if (currentHumidity < PUMP_ON_THRESHOLD) Serial.print("  [KHO -> Can bat bom]");
    else if (currentHumidity >= 60 && currentHumidity <= 70) Serial.print("  [TOI UU (60-70%)]");
    Serial.println();
  } else {
    Serial.println("Loi ket noi cam bien dat");
  }

  // 3. Ánh sáng
  Serial.print("☀️  Anh sang  : ");
  if (bh1750Connected && currentRawLux >= 0) {
    Serial.print(currentCalibLux, 0);
    Serial.print(" lux (Gia tri raw doc duoc: ");
    Serial.print(currentRawLux, 1);
    Serial.print(" lx * ");
    Serial.print(LIGHT_SCALE_FACTOR, 1);
    Serial.print(")");
    
    if (currentCalibLux < LIGHT_ON_THRESHOLD) {
      Serial.print("  [THIEU SANG -> Bat den]");
    } else if (currentCalibLux >= 25000.0 && currentCalibLux <= 40000.0) {
      Serial.print("  [TOI UU (25k-40k lux)]");
    } else if (currentCalibLux > 40000.0) {
      Serial.print("  [THUA SANG (>40k lux)]");
    }
    Serial.println();
  } else {
    Serial.println("Chua ket noi BH1750");
  }

  // 4. Trạng thái Relay hiện tại
  Serial.print("⚙️  Thiet bi  : ");
  Serial.print("Quat ["); Serial.print(fanState ? "BAT" : "TAT"); Serial.print("] | ");
  Serial.print("Bom [");  Serial.print(pumpState ? "BAT" : "TAT"); Serial.print("] | ");
  Serial.print("Den [");  Serial.print(lightState ? "BAT" : "TAT"); Serial.println("]");
  
  Serial.println("=================================================================\n");
}


// ============================================================================
// KHU 7: QUẢN LÝ KẾT NỐI WIFI
// ============================================================================

void setupWiFi() {
  Serial.print("\n[WIFI] Dang ket noi den: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int count = 0;
  while (WiFi.status() != WL_CONNECTED && count < 20) {
    delay(500);
    Serial.print(".");
    count++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ [WIFI] Da ket noi thanh cong!");
    Serial.print("   IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n⚠ [WIFI] Ket noi that bai! ESP32 se tiep tuc chay cuc bo va thu lai sau.");
  }
}

void checkWiFiConnection() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.reconnect();
  }
}


// ============================================================================
// KHU 8: GỬI DỮ LIỆU LÊN SERVER CLOUD (HTTP POST JSON)
// ============================================================================

void sendDataToServer() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("📡 [CLOUD] Khong co WiFi, bo qua luot gui nay.");
    return;
  }

  Serial.println("📡 [CLOUD] Dang gui du lieu len Server...");

  WiFiClientSecure client;
  client.setInsecure(); // Bỏ qua kiểm tra SSL cert để gửi HTTPS ổn định

  HTTPClient http;
  if (http.begin(client, SERVER_URL)) {
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(HTTP_TIMEOUT);

    // Đóng gói JSON gửi dữ liệu cảm biến
    StaticJsonDocument<256> doc;
    doc["vuon_id"]     = VUON_ID;
    doc["temperature"] = (currentTemp >= 0) ? currentTemp : 25.0;
    doc["humidity"]    = (currentHumidity >= 0) ? currentHumidity : 0;
    // Gửi giá trị lux đã được tính toán theo dải cây trồng
    doc["light"]       = (currentCalibLux >= 0) ? round(currentCalibLux) : -1;

    String body;
    serializeJson(doc, body);

    int httpCode = http.POST(body);

    if (httpCode == 200) {
      Serial.print("✓ [CLOUD] Gui thanh cong (HTTP 200). Lux gui len: ");
      Serial.println(doc["light"].as<float>());
    } else {
      Serial.print("⚠ [CLOUD] Loi HTTP POST: ");
      Serial.println(httpCode);
    }

    http.end();
  } else {
    Serial.println("⚠ [CLOUD] Khong the khoi tao ket noi HTTPS!");
  }

  client.stop(); // Giải phóng socket tránh tràn bộ nhớ RAM
}


// ============================================================================
// KHU 9: SETUP CHÍNH & VÒNG LẶP LOOP
// ============================================================================

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("\n\n");
  Serial.println("###################################################");
  Serial.println("#  HE THONG IOT NONG NGHIEP - DIEU KHIEN CUC BO   #");
  Serial.println("#  QUAT (IO18) | BOM (IO19) | DEN (IO21)          #");
  Serial.println("###################################################");

  // 1. Khởi tạo Relay
  initRelays();

  // 2. Khởi tạo Cảm biến
  initSensors();

  // 3. Kết nối WiFi
  setupWiFi();

  Serial.println("-> He thong da san sang chay!\n");
}

void loop() {
  unsigned long now = millis();

  // -------------------------------------------------------------
  // CHU KỲ 1: ĐỌC CẢM BIẾN, IN TERMINAL & ĐIỀU KHIỂN CỤC BỘ
  // (Chạy mỗi SENSOR_READ_INTERVAL_MS = 2 giây)
  // -------------------------------------------------------------
  if (now - lastSensorReadTime >= SENSOR_READ_INTERVAL_MS) {
    lastSensorReadTime = now;

    // 1. Đọc dữ liệu từ tất cả cảm biến
    currentTemp = readTemperature();
    currentHumidity = readSoilHumidity();
    readLightData(currentRawLux, currentCalibLux);

    // 2. In đầy đủ ra Terminal của Arduino IDE
    printTerminalReport();

    // 3. Tự động điều khiển Quạt, Bơm, Đèn theo số liệu vừa đọc
    runLocalAutomation();
  }

  // -------------------------------------------------------------
  // CHU KỲ 2: GỬI DỮ LIỆU LÊN SERVER ĐỂ LƯU LỊCH SỬ & VẼ BIỂU ĐỒ WEB
  // (Chạy mỗi SERVER_SEND_INTERVAL_MS = 15 giây, không gửi liên tục)
  // -------------------------------------------------------------
  if (now - lastServerSendTime >= SERVER_SEND_INTERVAL_MS) {
    lastServerSendTime = now;

    checkWiFiConnection();
    sendDataToServer();
  }
}
