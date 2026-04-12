import cv2
import time
import base64
import requests
import json
from datetime import datetime

# ==========================================
# CẤU HÌNH TOOL CAMERA AI VÀ KẾT NỐI SERVER
# ==========================================

# THAY BẰNG URL RENDER CỦA BẠN (Ví dụ: https://ai-nong-nghiep.onrender.com )
API_URL = "https://your-render-app.onrender.com/api/predict"

# Thời gian chờ giữa 2 lần chụp (Tính bằng giây)
# Ví dụ: 30 phút = 30 * 60 = 1800
INTERVAL_SECONDS = 30 * 60  

# Chọn Camera: Nhập số 0 cho webcam mặc định, số 1 cho camera cắm USB rời
CAMERA_INDEX = 1  

def capture_and_predict():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Đang khởi động Camera...")
    
    # 1. Bật Camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    if not cap.isOpened():
        print("❌ Lỗi: Không thể mở Camera USB. Hãy kiểm tra kết nối cổng USB và CAMERA_INDEX!")
        return

    # Chờ 2 giây để camera lấy nét và sáng rõ
    time.sleep(2)
    
    # 2. Đọc khung hình
    ret, frame = cap.read()
    cap.release() # Chụp xong thì tắt luôn cho đỡ nóng máy
    
    if not ret:
        print("❌ Lỗi: Không thể đọc hình ảnh từ Camera!")
        return
        
    print("📸 Chụp ảnh thành công. Đang tiến hành nén...")
    
    # 3. Chuyển ảnh thành chuỗi Base64
    _, buffer = cv2.imencode('.jpg', frame)
    img_b64 = base64.b64encode(buffer).decode('utf-8')
    base64_data = f"data:image/jpeg;base64,{img_b64}"
    
    # 4. Gửi lên HTTP Server (API Predict)
    print("📡 Đang gửi ảnh lên AI Model trên Web để phân tích...")
    try:
        payload = {"image": base64_data}
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(API_URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            # In kết quả
            is_healthy = data.get('healthy', True)
            print("✅ Web AI phân tích hoàn tất.")
            
            if is_healthy:
                print("🌿 Cây hoàn toàn khỏe mạnh!")
            else:
                deficient = data.get('deficient_names', [])
                print("⚠️ CẢNH BÁO: AI phát hiện là cây bị thiếu chất!")
                print(f"👉 Thiếu: {', '.join(deficient)}")
                
                # Tại đây, chúng ta có thể gọi thêm 1 API khác (tự Code trên backend) 
                # để lưu "Cảnh Báo" này thẳng vào bảng Database (VD: api/alerts)
                
        else:
            print(f"❌ Server trả về lỗi: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Lỗi mạng hoặc Server đang ngủ: {str(e)}")

# ==========================================
# VÒNG LẶP CHÍNH
# ==========================================
if __name__ == "__main__":
    print("=============================================")
    print(" 🚀 HỆ THỐNG AUTO CAMERA SCANNER HOẠT ĐỘNG! ")
    print(f" ⏱️  Camera Số: {CAMERA_INDEX} | Chu kỳ phân tích: {INTERVAL_SECONDS / 60} Phút.")
    print("=============================================")
    
    while True:
        capture_and_predict()
        print(f"⏳ Hệ thống đang nghỉ. Sẽ tự chụp lại sau {INTERVAL_SECONDS / 60} phút nữa...")
        time.sleep(INTERVAL_SECONDS)
