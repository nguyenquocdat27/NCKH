import cv2
import time
import base64
import requests
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from datetime import datetime

# =========================================================================
# CẤU HÌNH MẶC ĐỊNH
# =========================================================================
SERVER_URL = "http://localhost:5000"
VUON_ID = 1
CAMERA_INDEX = 0
CONFIG_FILE = "camera_config.json"

def load_local_config():
    global SERVER_URL, VUON_ID, CAMERA_INDEX
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                SERVER_URL = config.get("SERVER_URL", SERVER_URL)
                VUON_ID = int(config.get("VUON_ID", VUON_ID))
                CAMERA_INDEX = int(config.get("CAMERA_INDEX", CAMERA_INDEX))
        except Exception as e:
            pass

def save_local_config():
    try:
        config = {
            "SERVER_URL": SERVER_URL,
            "VUON_ID": VUON_ID,
            "CAMERA_INDEX": CAMERA_INDEX
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Không thể lưu cấu hình: {e}")

def capture_photo(camera_index):
    """Mở camera, lấy nét và chụp lại 1 khung hình"""
    print(f"📸 [{datetime.now().strftime('%H:%M:%S')}] Đang kết nối USB Camera (Index: {camera_index})...")
    cap = None
    for attempt in range(3):
        cap = cv2.VideoCapture(camera_index)
        if cap.isOpened():
            break
        cap.release()
        time.sleep(1)
    else:
        if camera_index != 0:
            print(f"⚠️ Cảnh báo: Không kết nối được camera index {camera_index}, thử chuyển sang webcam index 0...")
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise Exception("Không thể mở bất cứ USB Camera nào!")
        else:
            raise Exception(f"Không thể mở USB Camera tại INDEX {camera_index}!")

    time.sleep(2)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise Exception("Không thể đọc được khung hình từ Camera!")
        
    print("🌿 Đọc hình ảnh từ Camera thành công. Tiến hành mã hóa...")
    _, buffer = cv2.imencode('.jpg', frame)
    img_b64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{img_b64}"

def upload_and_analyze(image_base64):
    upload_url = f"{SERVER_URL}/api/camera/upload/{VUON_ID}"
    print(f"📡 Đang gửi ảnh lên Server AI tại: {SERVER_URL}...")
    
    payload = {"image": image_base64}
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(upload_url, json=payload, headers=headers, timeout=30)
    
    if response.status_code in [200, 201]:
        res_data = response.json()
        ai = res_data.get('ai_result', {})
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🎉 KẾT QUẢ PHÂN TÍCH AI:")
        if ai.get('healthy', True):
            print("🌿 TRẠNG THÁI: Cây hoàn toàn khỏe mạnh!")
        else:
            deficient = ai.get('deficient_names', [])
            print(f"⚠️ CẢNH BÁO: Phát hiện lá cây bị thiếu chất!")
            print(f"👉 Danh sách thiếu hụt: {', '.join(deficient)}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    else:
        print(f"❌ Server trả về lỗi: {response.status_code}\n{response.text}")


# Lớp định tuyến Print Log vào giao diện
class RedirectText:
    def __init__(self, text_ctrl):
        self.output = text_ctrl
    def write(self, string):
        self.output.insert(tk.END, string)
        self.output.see(tk.END)
    def flush(self):
        pass


class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hệ Thống Giám Sát Camera AI - Client")
        self.root.geometry("750x550")
        
        # State
        self.is_running = False
        self.monitor_thread = None
        self.last_capture_time = 0
        
        self.server_url = tk.StringVar()
        self.vuon_id = tk.StringVar()
        self.camera_index = tk.StringVar()
        
        self.setup_ui()
        
        # Nạp cấu hình
        load_local_config()
        self.server_url.set(SERVER_URL)
        self.vuon_id.set(str(VUON_ID))
        self.camera_index.set(str(CAMERA_INDEX))
        
        # Ghi đè Print
        sys.stdout = RedirectText(self.log_text)
        sys.stderr = RedirectText(self.log_text)
        
        print("=========================================================================")
        print("   🚀 HỆ THỐNG GIÁM SÁT USB CAMERA & AI PHÂN TÍCH ĐÃ KHỞI ĐỘNG! ")
        print("=========================================================================")
        print("💡 Vui lòng kiểm tra lại cấu hình và nhấn [▶ BẮT ĐẦU GIÁM SÁT].")

    def setup_ui(self):
        # Khu vực Cấu hình
        config_frame = ttk.LabelFrame(self.root, text=" ⚙ Cấu Hình Kết Nối ", padding=(10, 10))
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(config_frame, text="🔗 Server URL:").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(config_frame, textvariable=self.server_url, width=45).grid(row=0, column=1, sticky=tk.W, padx=5, pady=4)
        
        ttk.Label(config_frame, text="📍 Mã Vườn (ID):").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(config_frame, textvariable=self.vuon_id, width=15).grid(row=1, column=1, sticky=tk.W, padx=5, pady=4)
        
        ttk.Label(config_frame, text="📷 Camera Index:").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Entry(config_frame, textvariable=self.camera_index, width=15).grid(row=2, column=1, sticky=tk.W, padx=5, pady=4)
        
        btn_save = tk.Button(config_frame, text="💾 LƯU CẤU HÌNH", bg="#f0f0f0", font=("Arial", 9, "bold"), command=self.save_config)
        btn_save.grid(row=0, column=2, rowspan=3, padx=20, sticky="nsew", pady=5)
        
        # Khu vực Nút điều khiển
        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.btn_start = tk.Button(ctrl_frame, text="▶ BẮT ĐẦU GIÁM SÁT", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), pady=8, command=self.start_monitoring)
        self.btn_start.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.btn_stop = tk.Button(ctrl_frame, text="⏸ DỪNG LẠI", bg="#f44336", fg="white", font=("Arial", 10, "bold"), pady=8, state=tk.DISABLED, command=self.stop_monitoring)
        self.btn_stop.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.btn_capture = tk.Button(ctrl_frame, text="📸 CHỤP THỬ NGAY", bg="#2196F3", fg="white", font=("Arial", 10, "bold"), pady=8, command=self.manual_capture)
        self.btn_capture.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Khu vực Log
        log_frame = ttk.LabelFrame(self.root, text=" 📝 Nhật ký Hoạt động (Logs) ", padding=(5, 5))
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, bg="#1e1e1e", fg="#4CAF50", font=("Consolas", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Thanh trạng thái
        self.status_var = tk.StringVar(value="Trạng thái: Đang chờ...")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, font=("Arial", 9), bg="#e0e0e0")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def save_config(self):
        global SERVER_URL, VUON_ID, CAMERA_INDEX
        SERVER_URL = self.server_url.get().strip()
        try:
            VUON_ID = int(self.vuon_id.get().strip())
            CAMERA_INDEX = int(self.camera_index.get().strip())
        except ValueError:
            messagebox.showerror("Lỗi Nhập Liệu", "ID Vườn và Camera Index phải là số nguyên!")
            return
            
        save_local_config()
        print(f"\n[SYSTEM] Đã lưu thông số: Server={SERVER_URL} | Vườn={VUON_ID} | Camera={CAMERA_INDEX}")
        messagebox.showinfo("Thành công", "Đã lưu cấu hình!")

    def start_monitoring(self):
        self.save_config() # Đảm bảo biến toàn cục được update
        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_var.set("Trạng thái: Đang hoạt động (Theo dõi lệnh & Chụp tự động)...")
        print("\n==================================================")
        print("▶ BẮT ĐẦU CHẠY GIÁM SÁT NGẦM...")
        
        self.last_capture_time = time.time()
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_var.set("Trạng thái: Đã tạm dừng.")
        print("⏸ ĐÃ DỪNG GIÁM SÁT!")

    def manual_capture(self):
        self.save_config()
        print("\n📸 [MANUAL] Bắt đầu chụp thử thủ công...")
        # Chạy trên thread phụ để không đơ giao diện
        threading.Thread(target=self._capture_and_upload_task, daemon=True).start()

    def _capture_and_upload_task(self):
        try:
            self.status_var.set("Trạng thái: Đang mở camera chụp ảnh...")
            img_b64 = capture_photo(CAMERA_INDEX)
            self.status_var.set("Trạng thái: Đang phân tích AI...")
            upload_and_analyze(img_b64)
            self.status_var.set("Trạng thái: Hoàn tất.")
        except Exception as e:
            print(f"❌ LỖI: {e}")
            self.status_var.set("Trạng thái: Lỗi chụp ảnh.")

    def monitor_loop(self):
        while self.is_running:
            try:
                settings_url = f"{SERVER_URL}/api/camera/settings/{VUON_ID}?client=true"
                response = requests.get(settings_url, timeout=5)
                
                if response.status_code == 200:
                    settings = response.json()
                    camera_command = settings.get('camera_command', 'idle')
                    camera_interval = settings.get('camera_interval', 30)
                    
                    if camera_command == 'capture':
                        print("\n⚡ YÊU CẦU CHỤP HÌNH TỪ XA PHÁT HIỆN ĐƯỢC!")
                        self._capture_and_upload_task()
                        requests.put(f"{SERVER_URL}/api/camera/settings/{VUON_ID}", json={"camera_command": "idle"}, timeout=5)

                    if camera_interval > 0:
                        elapsed = time.time() - self.last_capture_time
                        if elapsed >= camera_interval * 60:
                            print(f"\n⏰ Đã đến chu kỳ chụp tự động ({camera_interval} phút)...")
                            self._capture_and_upload_task()
                            self.last_capture_time = time.time()
                else:
                    print(f"⚠️ Lỗi kết nối Server: {response.status_code}")
                    
            except requests.exceptions.RequestException:
                pass # Bỏ qua lỗi kết nối (tránh in quá nhiều)
            except Exception as e:
                print(f"🔥 Lỗi hệ thống: {e}")
                
            # Nghỉ 3 giây trước khi kiểm tra lại vòng lặp
            for _ in range(30):
                if not self.is_running: break
                time.sleep(0.1)

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
        
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()
