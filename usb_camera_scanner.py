import cv2
import time
import base64
import requests
import json
import os
import sys
from datetime import datetime

# =========================================================================
# CẤU HÌNH CAMERA CLIENT & KẾT NỐI SERVER (MẶC ĐỊNH)
# =========================================================================

# Đổi thành URL chạy của Flask Server của bạn (Local hoặc Render)
# Chạy local: "http://localhost:5000"
# Chạy Render: "https://your-app.onrender.com"
SERVER_URL = "https://nckh-ai.onrender.com/"

# Cài đặt vườn của bạn (Xem ID vườn trên giao diện web "Vườn của tôi" hoặc "Camera")
VUON_ID = 30001

# Chọn Camera: 0 cho webcam mặc định, 1 hoặc 2 cho camera cắm USB ngoài
CAMERA_INDEX = 0

# Đường dẫn file lưu cấu hình cục bộ để tự động chạy ngầm (Headless)
CONFIG_FILE = "camera_config.json"

# =========================================================================

def load_local_config():
    """Tải cấu hình từ file camera_config.json nếu có"""
    global SERVER_URL, VUON_ID, CAMERA_INDEX
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                SERVER_URL = config.get("SERVER_URL", SERVER_URL)
                VUON_ID = int(config.get("VUON_ID", VUON_ID))
                CAMERA_INDEX = int(config.get("CAMERA_INDEX", CAMERA_INDEX))
            print(f"⚙️  [CẤU HÌNH] Đã nạp thành công cấu hình tự động từ file: {CONFIG_FILE}")
        except Exception as e:
            print(f"⚠️  [CẤU HÌNH] Không thể đọc file cấu hình: {e}. Sử dụng mặc định.")

def save_local_config():
    """Lưu cấu hình hiện tại vào file camera_config.json"""
    try:
        config = {
            "SERVER_URL": SERVER_URL,
            "VUON_ID": VUON_ID,
            "CAMERA_INDEX": CAMERA_INDEX
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"💾 [CẤU HÌNH] Đã lưu thông số mới vào file cục bộ: {CONFIG_FILE}")
    except Exception as e:
        print(f"⚠️  [CẤU HÌNH] Không thể ghi file cấu hình cục bộ: {e}")


def capture_photo(camera_index):
    """Mở camera, lấy nét và chụp lại 1 khung hình"""
    print(f"📸 [{datetime.now().strftime('%H:%M:%S')}] Đang kết nối USB Camera (Index: {camera_index})...")
    
    cap = None
    for attempt in range(3):
        print(f"   - Thử kết nối Camera lần {attempt + 1}/3...")
        cap = cv2.VideoCapture(camera_index)
        if cap.isOpened():
            break
        cap.release()
        time.sleep(1)
    else:
        # Thử fallback sang index 0 nếu index khác bị lỗi
        if camera_index != 0:
            print(f"⚠️ Cảnh báo: Không kết nối được camera index {camera_index}, thử chuyển sang webcam index 0...")
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise Exception("Không thể mở bất cứ USB Camera nào!")
        else:
            raise Exception(f"Không thể mở USB Camera tại INDEX {camera_index}!")

    # Chờ 2 giây để camera lấy nét tự động và cân bằng ánh sáng
    time.sleep(2)
    
    ret, frame = cap.read()
    cap.release() # Giải phóng camera ngay để tránh nóng máy
    
    if not ret:
        raise Exception("Không thể đọc được khung hình từ Camera!")
        
    print("🌿 Đọc hình ảnh từ Camera thành công. Tiến hành mã hóa...")
    
    # Nén ảnh thành định dạng JPG
    _, buffer = cv2.imencode('.jpg', frame)
    # Mã hóa sang chuỗi base64
    img_b64 = base64.b64encode(buffer).decode('utf-8')
    base64_data = f"data:image/jpeg;base64,{img_b64}"
    
    return base64_data

def upload_and_analyze(image_base64):
    """Gửi ảnh lên server để chạy AI phân tích và lưu vào cơ sở dữ liệu"""
    upload_url = f"{SERVER_URL}/api/camera/upload/{VUON_ID}"
    print(f"📡 Đang gửi ảnh lên Server AI tại: {upload_url}...")
    
    payload = {"image": image_base64}
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(upload_url, json=payload, headers=headers, timeout=30)
    
    if response.status_code in [200, 201]:
        res_data = response.json()
        ai = res_data.get('ai_result', {})
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🎉 KẾT QUẢ PHÂN TÍCH AI HOÀN TẤT:")
        
        if ai.get('healthy', True):
            print("🌿 TRẠNG THÁI: Cây hoàn toàn khỏe mạnh!")
        else:
            deficient = ai.get('deficient_names', [])
            print(f"⚠️ TRẠNG THÁI: PHÁT HIỆN LÁ CÂY BỊ THIẾU CHẤT!")
            print(f"👉 Danh sách thiếu hụt: {', '.join(deficient)}")
            print("💡 LỜI KHUYÊN:")
            for rec in ai.get('recommendations', []):
                print(f"   - {rec}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    else:
        print(f"❌ Server trả về mã lỗi: {response.status_code}")
        print(response.text)

def main():
    global SERVER_URL, VUON_ID, CAMERA_INDEX
    
    # 1. Tải cấu hình đã lưu trước đó nếu có
    load_local_config()
    
    print("=========================================================================")
    print("   🚀 HỆ THỐNG GIÁM SÁT USB CAMERA & AI PHÂN TÍCH BẮT ĐẦU HOẠT ĐỘNG! ")
    print("=========================================================================")
    
    # 2. Kiểm tra xem Terminal có tương tác được không (Interactive mode)
    # Nếu chạy ngầm (headless service) thì sys.stdin.isatty() sẽ trả về False
    if sys.stdin and sys.stdin.isatty():
        try:
            print("💡 Phát hiện chạy ở chế độ tương tác (Interactive terminal).")
            
            user_url = input(f"👉 Nhập URL Server (Nhấn Enter để giữ nguyên {SERVER_URL}): ").strip()
            if user_url:
                SERVER_URL = user_url
                
            user_vuon = input(f"👉 Nhập ID Vườn muốn giám sát (Xem trên Web, nhấn Enter để lấy mặc định {VUON_ID}): ").strip()
            if user_vuon:
                VUON_ID = int(user_vuon)
                
            user_cam = input(f"👉 Nhập Camera Index (0 = webcam, 1 = camera ngoài, nhấn Enter để lấy mặc định {CAMERA_INDEX}): ").strip()
            if user_cam:
                CAMERA_INDEX = int(user_cam)
                
            # Lưu lại cấu hình để lần sau khởi chạy ngầm tự động nhận diện
            save_local_config()
        except Exception as e:
            print(f"⚠️ Có lỗi trong quá trình nhập liệu: {e}. Sử dụng cấu hình nạp sẵn.")
    else:
        print("🤖 [HEADLESS] Chạy ở chế độ ẩn/dịch vụ ngầm (No TTY). Bỏ qua nhập thông số.")
        print(f"⚙️  Sử dụng cấu hình nạp sẵn: ID Vườn={VUON_ID}, Camera={CAMERA_INDEX}, Server={SERVER_URL}")

    print("\n-------------------------------------------------------------------------")
    print(f"   📍 Vườn Giám Sát ID: {VUON_ID} | Server: {SERVER_URL}")
    print(f"   📷 Camera Index: {CAMERA_INDEX} | Trạng thái: Đang kết nối...")
    print("-------------------------------------------------------------------------\n")
    
    last_capture_time = time.time()
    
    # Chạy lần chụp đầu tiên khi khởi động để xác nhận camera hoạt động
    try:
        img_b64 = capture_photo(CAMERA_INDEX)
        upload_and_analyze(img_b64)
    except Exception as e:
        print(f"⚠️ Chụp ảnh khởi động thất bại: {e}")
        print("👉 Vẫn tiếp tục vòng lặp để lắng nghe lệnh từ Server.")

    while True:
        try:
            # 1. Gửi ping và lấy cài đặt từ server (pass client=true)
            settings_url = f"{SERVER_URL}/api/camera/settings/{VUON_ID}?client=true"
            response = requests.get(settings_url, timeout=5)
            
            if response.status_code == 200:
                settings = response.json()
                
                camera_command = settings.get('camera_command', 'idle')
                camera_interval = settings.get('camera_interval', 30) # phút
                
                # In trạng thái ping nhẹ
                print(f"✨ [Ping] Đã gửi tín hiệu lên Server | Chu kỳ hiện tại: {camera_interval} phút | Lệnh: {camera_command}")
                
                # 2. Xử lý Lệnh chụp từ Server (Manual Trigger)
                if camera_command == 'capture':
                    print("⚡ PHÁT HIỆN YÊU CẦU CHỤP HÌNH KHẨN CẤP TỪ WEB SERVER!")
                    try:
                        img_b64 = capture_photo(CAMERA_INDEX)
                        upload_and_analyze(img_b64)
                    except Exception as ex_cap:
                        print(f"❌ Lỗi khi thực hiện lệnh chụp khẩn cấp: {ex_cap}")
                        # Gửi lại upload trống hoặc reset lệnh bằng cách update settings về idle
                        requests.put(f"{SERVER_URL}/api/camera/settings/{VUON_ID}", json={"camera_command": "idle"}, timeout=5)

                # 3. Xử lý Chụp ảnh theo Chu kỳ Tự động (Scheduled Capture)
                if camera_interval > 0:
                    elapsed_time = time.time() - last_capture_time
                    interval_seconds = camera_interval * 60
                    
                    if elapsed_time >= interval_seconds:
                        print(f"⏰ Đã đến chu kỳ chụp tự động ({camera_interval} phút)...")
                        try:
                            img_b64 = capture_photo(CAMERA_INDEX)
                            upload_and_analyze(img_b64)
                            last_capture_time = time.time() # Reset mốc thời gian chụp tự động
                        except Exception as ex_sched:
                            print(f"❌ Lỗi chụp tự động theo chu kỳ: {ex_sched}")
                            # Thử lại sau 1 phút
                            last_capture_time = time.time() - (camera_interval * 60) + 60
            else:
                print(f"⚠️ Lỗi kết nối Server Settings: Mã lỗi {response.status_code}")
                
        except requests.exceptions.RequestException as e_net:
            print(f"🔌 Lỗi Mạng: Không thể kết nối với server ({e_net}). Đang thử kết nối lại...")
        except Exception as e_gen:
            print(f"🔥 Lỗi hệ thống: {e_gen}")
            
        # Nghỉ 5 giây trước khi thực hiện lần Ping/Lấy lệnh tiếp theo
        time.sleep(5)

if __name__ == "__main__":
    main()
