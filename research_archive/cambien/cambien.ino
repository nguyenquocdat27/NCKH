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

// Cấu hình chân Relay điều khiển Quạt & Bơm (Active Low)
#define FAN_PIN 18 
#define PUMP_PIN 19 

// 1. Máy đo Nhiệt độ nước/đất DS18B20 (Waterproof)
#define ONE_WIRE_BUS 5   // Chân Data cắm vào IO5 (Cần trở kéo 4.7k ohm lên 3.3V)
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature ds18b20(&oneWire);

// 2. Cảm biến Độ ẩm đất điện dung
#define SOIL_MOISTURE_PIN 4  // Cắm chân analog Aout vào G4
const int DRY_VALUE_ADC = 3500;  
const int WET_VALUE_ADC = 1200;  

// Biến điều khiển nhận từ Server phản hồi
bool manualControl = false;  // false = Tự động, true = Thủ công từ web
bool manualFanState = false; // Trạng thái quạt do người dùng bấm trên web (true = bật)
bool manualPumpState = false; // Trạng thái bơm nước (true = bật)

// ==========================================
// CẤU HÌNH SERVER KẾT NỐI
// ==========================================
const char* serverUrl = "https://nckh-ai.onrender.com/api/sensors";
const int VUON_ID = 30001; 

void setup() {
  Serial.begin(115200);
  delay(2000); // Tránh lỗi reset trên ESP32-S3

  Serial.println("ESP32 STARTED");

  // KHỞI TẠO CHÂN ĐIỀU KHIỂN QUẠT VÀ BƠM
  pinMode(FAN_PIN, OUTPUT);
  digitalWrite(FAN_PIN, HIGH); // Mặc định tắt quạt ban đầu (Active Low - HIGH là TẮT)
  
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, HIGH); // Mặc định tắt bơm ban đầu

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
  // 1. ĐỌC DỮ LIỆU CÁC CẢM BIẾN
  // ==========================================
  
  // Đọc Nhiệt độ
  ds18b20.requestTemperatures();
  float temperature = ds18b20.getTempCByIndex(0);

  if (temperature == -127.00) {
    Serial.println("⚠️  Lỗi: Cảm biến DS18B20 chưa kết nối hoặc đứt cáp!");
    temperature = 25.0; // Fallback giá trị để tránh lỗi logic hệ thống
  }

  // Đọc Độ ẩm đất
  int soilAdcVal = analogRead(SOIL_MOISTURE_PIN);
  if (soilAdcVal < 100) {
    Serial.println("⚠️  Lỗi: Cảm biến độ ẩm chưa kết nối! (ADC < 100)");
    delay(2000);
    return; 
  }

  int humidity = map(soilAdcVal, DRY_VALUE_ADC, WET_VALUE_ADC, 0, 100);
  humidity = constrain(humidity, 0, 100); 
  float light = 0.0;

  // In thông tin ra màn hình kiểm tra
  Serial.println("\n===== SENSOR DATA =====");
  Serial.print("Nhiệt độ:    "); Serial.print(temperature); Serial.println(" °C");
  Serial.print("Độ ẩm đất:  "); Serial.print(humidity); Serial.println(" %");

  // ==========================================
  // 2. GỬI DỮ LIỆU LÊN SERVER & NHẬN PHẢN HỒI LỆNH
  // ==========================================
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    // Đóng gói JSON dữ liệu gửi đi
    StaticJsonDocument<200> doc;
    doc["vuon_id"]     = VUON_ID;
    doc["temperature"] = temperature;
    doc["humidity"]    = humidity;
    doc["light"]       = light;

    String requestBody;
    serializeJson(doc, requestBody);

    int httpResponseCode = http.POST(requestBody);

    if (httpResponseCode > 0) {
      Serial.print("HTTP Code: "); Serial.println(httpResponseCode);
      
      // Đọc gói tin phản hồi (Response) từ Server gửi về
      String response = http.getString();
      Serial.print("Server Response JSON: "); Serial.println(response);

      // Giải mã JSON nhận được từ Server để lấy lệnh điều khiển quạt
      StaticJsonDocument<300> responseDoc;
      DeserializationError error = deserializeJson(responseDoc, response);
      
      if (!error) {
        // Kiểm tra xem server có gửi đủ các trường dữ liệu điều khiển không
        if (responseDoc.containsKey("manual")) {
          manualControl = responseDoc["manual"].as<bool>();
          manualFanState = responseDoc["fan_state"].as<bool>();
          manualPumpState = responseDoc["pump_state"].as<bool>();
        }
      }
    } else {
      Serial.print("Lỗi kết nối POST. Mã lỗi: "); Serial.println(httpResponseCode);
    }
    http.end();
  } else {
    Serial.println("Lỗi: Mất kết nối WiFi.");
  }

  // ==========================================
  // 3. LOGIC ĐIỀU KHIỂN QUẠT & BƠM (TỰ ĐỘNG / THỦ CÔNG)
  // ==========================================
  if (manualControl) {
    // CHẾ ĐỘ THỦ CÔNG: Ưu tiên tuyệt đối lệnh bấm nút từ Giao diện Web
    Serial.println("⚙️ [CHẾ ĐỘ] -> THỦ CÔNG (Nghe theo nút nhấn trên Web)");
    
    // Điều khiển Quạt
    if (manualFanState) {
      digitalWrite(FAN_PIN, LOW);  // Mức THẤP (LOW) là BẬT quạt
      Serial.println("💨 [QUẠT] -> ĐÃ BẬT THỦ CÔNG");
    } else {
      digitalWrite(FAN_PIN, HIGH); // Mức CAO (HIGH) là TẮT quạt
      Serial.println("🛑 [QUẠT] -> ĐÃ TẮT THỦ CÔNG");
    }
    
    // Điều khiển Bơm
    if (manualPumpState) {
      digitalWrite(PUMP_PIN, LOW);
      Serial.println("💦 [BƠM] -> ĐÃ BẬT THỦ CÔNG");
    } else {
      digitalWrite(PUMP_PIN, HIGH);
      Serial.println("🛑 [BƠM] -> ĐÃ TẮT THỦ CÔNG");
    }
  } 
  else {
    // CHẾ ĐỘ TỰ ĐỘNG: Tự xử lý dựa trên cảm biến nhiệt độ & độ ẩm
    Serial.println("🤖 [CHẾ ĐỘ] -> TỰ ĐỘNG (Dựa theo cảm biến)");
    
    // Quạt: Tự động bật khi > 30 độ
    if (temperature > 30.0) {
      digitalWrite(FAN_PIN, LOW);  // LOW để BẬT quạt
      Serial.println("💨 [QUẠT] -> TỰ ĐỘNG BẬT (Nhiệt độ > 30°C)");
    } else {
      digitalWrite(FAN_PIN, HIGH); // HIGH để TẮT quạt
      Serial.println("🛑 [QUẠT] -> TỰ ĐỘNG TẮT (Nhiệt độ <= 30°C)");
    }
    
    // Bơm: Tự động tưới khi Độ ẩm đất < 50%
    if (humidity < 50) {
      digitalWrite(PUMP_PIN, LOW); // LOW để BẬT bơm
      Serial.println("💦 [BƠM] -> TỰ ĐỘNG BẬT (Độ ẩm đất < 50%)");
    } else {
      digitalWrite(PUMP_PIN, HIGH); // HIGH để TẮT bơm
      Serial.println("🛑 [BƠM] -> TỰ ĐỘNG TẮT (Độ ẩm đất >= 50%)");
    }
  }
  Serial.println("=======================");

  // Thực hiện lại chu kỳ sau mỗi 5 giây
  delay(5000);
}