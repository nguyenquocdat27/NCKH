#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Thư viện cho Cảm biến
#include <Wire.h>
// #include <BH1750.h>  // [TẠM TẮT]
#include <OneWire.h>
#include <DallasTemperature.h>

const char* ssid = "Quoc Dat_2.4G";
const char* password = "88888888";

// ==========================================
// CẤU HÌNH CHÂN CẢM BIẾN & THIẾT BỊ
// ==========================================

// Cấu hình chân Relay điều khiển Quạt
#define FAN_PIN 18 

// 1. Máy đo Nhiệt độ nước/đất DS18B20 (Waterproof)
#define ONE_WIRE_BUS 5   // Chân Data cắm vào IO5 (Cần trở kéo 4.7k ohm lên 3.3V)
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature ds18b20(&oneWire);

// 2. Cảm biến Ánh sáng BH1750 (Giao tiếp I2C) [TẠM TẮT]
// // Mặc định kết nối I2C ESP32: SDA = G21, SCL = G22
// BH1750 lightMeter;

// 3. Cảm biến Độ ẩm đất điện dung (Capacitive Soil Moisture Sensor)
#define SOIL_MOISTURE_PIN 4  // Cắm chân analog Aout vào G4
const int DRY_VALUE_ADC = 3500;  // Giá trị adc khi để ngoài không khí khô
const int WET_VALUE_ADC = 1200;  // Giá trị adc khi nhúng ngập trong nước

// Biến lưu trạng thái quạt để đảo trạng thái sau mỗi chu kỳ
bool isFanOn = false; 

// ==========================================
// CẤU HÌNH SERVER KẾT NỐI
// ==========================================
const char* serverUrl = "https://nckh-ai.onrender.com/api/sensors";
const int VUON_ID = 30001; // ID Của Vườn trong Database TiDB/MySQL

void setup() {
  Serial.begin(115200);
  delay(2000); // Tránh lỗi reset trên ESP32-S3

  Serial.println("ESP32 STARTED");

  // KHỞI TẠO CHÂN ĐIỀU KHIỂN QUẠT
  pinMode(FAN_PIN, OUTPUT);
  digitalWrite(FAN_PIN, HIGH); // Mặc định tắt quạt ban đầu (Active Low)

  // Khởi tạo DS18B20
  ds18b20.begin();

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
  // ĐỌC DỮ LIỆU CÁC CẢM BIẾN
  // ==========================================

  // 1. Đọc Nhiệt độ (DS18B20)
  ds18b20.requestTemperatures();
  float temperature = ds18b20.getTempCByIndex(0);

  if (temperature == -127.00) {
    Serial.println("⚠️  Lỗi: Cảm biến DS18B20 chưa kết nối hoặc đứt cáp!");
    temperature = 25.0; // Fallback để test server
  }

  // 2. Đọc Độ ẩm đất (Capacitive Sensor)
  int soilAdcVal = analogRead(SOIL_MOISTURE_PIN);

  if (soilAdcVal < 100) {
    Serial.println("⚠️  Lỗi: Cảm biến độ ẩm chưa kết nối! (ADC < 100)");
    delay(2000);
    return; // Bỏ qua lần này, không gửi dữ liệu sai lên server
  }

  int humidity = map(soilAdcVal, DRY_VALUE_ADC, WET_VALUE_ADC, 0, 100);
  humidity = constrain(humidity, 0, 100); // Ràng buộc 0–100%

  float light = 0.0;

  // In ra Serial Monitor
  Serial.println("===== SENSOR DATA =====");
  Serial.print("Nhiệt độ:    "); Serial.print(temperature); Serial.println(" °C");
  Serial.print("Soil ADC:    "); Serial.println(soilAdcVal);
  Serial.print("Độ ẩm đất:  "); Serial.print(humidity); Serial.println(" %");
  Serial.println("=======================");

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
    doc["light"]       = light;

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

  // ==========================================
  // LOGIC BẬT TẮT QUẠT THEO THỜI GIAN (Xen kẽ mỗi chu kỳ)
  // ==========================================
  isFanOn = !isFanOn; // Đảo trạng thái quạt (Nếu đang bật -> tắt, đang tắt -> bật)

  if (isFanOn) {
    digitalWrite(FAN_PIN, LOW);  // Kích mức THẤP để BẬT quạt
    Serial.println("💨 [THIẾT BỊ] -> ĐÃ BẬT QUẠT");
  } else {
    digitalWrite(FAN_PIN, HIGH); // Kích mức CAO để TẮT quạt
    Serial.println("🛑 [THIẾT BỊ] -> ĐÃ TẮT QUẠT");
  }

  // Chờ 5 giây cho chu kỳ tiếp theo
  delay(5000);
}