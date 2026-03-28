# Hướng dẫn triển khai (Deployment Guide)

Để đưa hệ thống lên Cloud với MySQL, bạn cần thực hiện các bước sau:

## 1. Chuẩn bị MySQL (Dùng TiDB Cloud - Miễn phí & Tốt nhất)
Để có một database MySQL chạy online (Cloud), bạn hãy dùng **TiDB Cloud**. Các bước như sau:

1.  **Đăng ký**: Truy cập [tidbcloud.com](https://tidbcloud.com/) và tạo tài khoản (không cần thẻ tín dụng).
2.  **Tạo Cluster**: Chọn gói **Starter (Free)**. Chờ khoảng 30 giây để nó khởi tạo.
3.  **Lấy mật khẩu**: Nhấn nút **Connect**, chọn "MySQL CLI" hoặc bất kỳ mục nào. Nó sẽ yêu cầu bạn tạo mật khẩu (Mật khẩu này rất quan trọng, hãy copy lưu lại ngay).
4.  **Cấu hình Truy cập (Quan trọng)**: Trong phần **Security**, bạn phải thêm IP `0.0.0.0/0` vào Danh sách trắng (Allowlist) để Render có thể kết nối được từ mọi nơi.
5.  **Lấy thông tin**: Copy các mục: **Host**, **Port**, **User**.

**Ví dụ chuỗi kết nối của bạn sẽ có dạng:**
`mysql+pymysql://<user>.<prefix>:<password>@<host>:4000/test`

*(Lưu ý: TiDB Cloud dùng cổng 4000 thay vì 3306, hãy nhớ điền đúng cổng này vào chuỗi kết nối).*

## 2. Triển khai lên Render.com
1. Đưa toàn bộ code lên **GitHub/GitLab**.
2. Trên Render, tạo một **Web Service** mới và kết nối với Repository của bạn.
3. Cấu hình các biến môi trường (Environment Variables) trong tab **Settings -> Environment**:
   - `DATABASE_URL`: Điền chuỗi kết nối MySQL ở bước 1.
   - `PYTHON_VERSION`: `3.10.12`
   - `SECRET_KEY`: (Tự tạo một chuỗi ngẫu nhiên hoặc Render tự tạo).
4. Render sẽ tự động chạy lệnh `pip install -r requirements.txt` và khởi chạy server bằng `gunicorn server:app`.

## 3. Cấu hình Frontend
Nếu bạn host Frontend (HTML/JS) ở một nơi khác (ví dụ Vercel/Netlify), hãy vào file `js/state.js` và cập nhật:
- `BACKEND_URL`: URL của Render Web Service (ví dụ: `https://nckh-backend.onrender.com`).
- `AI_URL`: (Tương tự nếu dùng chung, hoặc để trống).

## 4. Dữ liệu cảm biến từ ESP32
Để ESP32 gửi dữ liệu về, code trong ESP32 cần thực hiện POST request đến:
`https://<your-render-url>/api/sensors`
Body JSON:
```json
{
  "vuon_id": 1,
  "temperature": 28.5,
  "humidity": 65,
  "light": 800
}
```
