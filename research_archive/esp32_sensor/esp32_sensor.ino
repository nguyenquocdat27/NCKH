#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Thư viện cho Cảm biến
#include <Wire.h>
// #include <BH1750.h>  // [TẠM TẮT - Chưa kết nối]
#include <OneWire.h>
#include <DallasTemperature.h>

const char* ssid = "Quoc Dat_2.4G";
const char* password = "88888888";

// ==========================================
// CẤU HÌNH CHÂN CẢM BIẾN
// ==========================================

// 1. Nhiệt kế đất/nước DS18B20 (Waterproof)
#define ONE_WIRE_BUS 5   // Chân Data cắm vào IO5 (Cần trở kéo 4.7k ohm lên 3.3V)
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature ds18b20(&oneWire);

// 2. Cảm biến Ánh sáng BH1750 (I2C) [TẠM TẮT - Chưa kết nối]
// // Mặc định kết nối I2C ESP32: SDA = G21, SCL = G22
// BH1750 lightMeter;

// 3. Cảm biến Độ ẩm đất điện dung (Capacitive Soil Moisture Sensor)
#define SOIL_MOISTURE_PIN 4  // Cắm chân analog Aout vào G4
// Hiệu chuẩn Độ ẩm: (Nhúng xuống nước → ghi WET, để khô → ghi DRY)
const int DRY_VALUE_ADC = 3500;  // Giá trị ADC khi khô hoàn toàn (ngoài không khí)
const int WET_VALUE_ADC = 1200;  // Giá trị ADC khi nhúng ngập trong nước

// ==========================================
// CẤU HÌNH SERVER KẾT NỐI
// ==========================================
const char* serverUrl = "https://nckh-ai.onrender.com/api/sensors";

// ID Của Vườn trong Database TiDB/MySQL
const int VUON_ID = 30001;

// ==========================================
// CẤU HÌNH LẤY TRUNG BÌNH
// ==========================================
const int NUM_SAMPLES = 10;      // Số lần đọc để tính trung bình
const int SAMPLE_DELAY_MS = 200; // Khoảng cách giữa 2 lần đọc (ms)

void setup() {
  Serial.begin(115200);
  delay(2000); // Tránh lỗi reset trên ESP32-S3

  Serial.println("ESP32 STARTED");

  // Khởi tạo DS18B20
  ds18b20.begin();

  // // Khởi tạo BH1750 [TẠM TẮT]
  // Wire.begin();
  // if (lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
  //   Serial.println(F("BH1750 OK"));
  // } else {
  //   Serial.println(F("Lỗi: Không tìm thấy BH1750!"));
  // }

  // Kết nối WiFi
  Serial.println("\nĐang kết nối WiFi...");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }

  Serial.println("\nKết nối WiFi thành công!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // ==========================================
  // ĐỌC TRUNG BÌNH 10 LẦN → GIẢM NHIỄU / LAG
  // ==========================================

  // --- 1. Nhiệt độ DS18B20 (Lấy trung bình NUM_SAMPLES lần) ---
  float tempSum = 0;
  int tempValidCount = 0;

  for (int i = 0; i < NUM_SAMPLES; i++) {
    ds18b20.requestTemperatures();
    float t = ds18b20.getTempCByIndex(0);

    if (t != -127.00 && t != DEVICE_DISCONNECTED_C) {
      tempSum += t;
      tempValidCount++;
    }
    delay(SAMPLE_DELAY_MS);
  }

  float temperature;
  if (tempValidCount == 0) {
    Serial.println("⚠️  Lỗi: DS18B20 chưa kết nối hoặc đứt cáp!");
    temperature = 25.0; // Fallback để tránh crash (server vẫn nhận được)
  } else {
    temperature = tempSum / tempValidCount;
  }

  // --- 2. Độ ẩm đất Capacitive (Lấy trung bình NUM_SAMPLES lần) ---
  long soilSum = 0;
  for (int i = 0; i < NUM_SAMPLES; i++) {
    soilSum += analogRead(SOIL_MOISTURE_PIN);
    delay(SAMPLE_DELAY_MS);
  }
  int soilAdcAvg = soilSum / NUM_SAMPLES;

  // Kiểm tra cảm biến chưa cắm (ADC < 100 → bỏ qua, không gửi)
  if (soilAdcAvg < 100) {
    Serial.println("⚠️  Lỗi: Cảm biến độ ẩm chưa kết nối! (ADC < 100)");
    delay(2000);
    return;
  }

  int humidity = map(soilAdcAvg, DRY_VALUE_ADC, WET_VALUE_ADC, 0, 100);
  humidity = constrain(humidity, 0, 100); // Ràng buộc 0–100%

  // --- 3. Ánh sáng BH1750 [TẠM TẮT - Chưa kết nối] ---
  // Gửi -1 để frontend biết "không có cảm biến ánh sáng"
  // (Khác với 0 lux = ban đêm/tối hoàn toàn)
  float light = -1.0;
  // Khi kết nối BH1750 thì thay bằng:
  // float lightSum = 0;
  // for (int i = 0; i < NUM_SAMPLES; i++) {
  //   lightSum += lightMeter.readLightLevel();
  //   delay(SAMPLE_DELAY_MS);
  // }
  // float light = lightSum / NUM_SAMPLES;

  // In ra Serial Monitor
  Serial.println("===== SENSOR DATA (AVG 10 samples) =====");
  Serial.print("Nhiệt độ:    "); Serial.print(temperature, 2); Serial.println(" °C");
  Serial.print("Soil ADC:    "); Serial.println(soilAdcAvg);
  Serial.print("Độ ẩm đất:  "); Serial.print(humidity); Serial.println(" %");
  Serial.println("Ánh sáng:    [Chưa kết nối - BH1750 disabled]");
  Serial.println("=========================================");

  // ==========================================
  // GỬI DỮ LIỆU LÊN API DATABASE TiDB / RENDER
  // ==========================================
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<200> doc;
    doc["vuon_id"]     = VUON_ID;
    doc["temperature"] = temperature;
    doc["humidity"]    = humidity;
    doc["light"]       = light; // -1 = không có cảm biến ánh sáng

    String requestBody;
    serializeJson(doc, requestBody);

    int httpResponseCode = http.POST(requestBody);

    if (httpResponseCode > 0) {
      Serial.print("HTTP Code: "); Serial.print(httpResponseCode);
      Serial.println(" -> Đã lưu vào Database!");
    } else {
      Serial.print("Lỗi POST. Server đang Sleep hoặc mất mạng. Mã lỗi: ");
      Serial.println(httpResponseCode);
    }

    http.end();
  } else {
    Serial.println("Lỗi: Mất kết nối WiFi.");
  }

  // Chờ 5 giây (Keep-alive giúp Server Render không ngủ)
  // Lưu ý: Vòng lặp đọc 10 mẫu × 200ms × 2 cảm biến ≈ 4 giây
  // Tổng chu kỳ ≈ 4 + 5 = ~9 giây/lần gửi
  delay(5000);
}
