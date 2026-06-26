"""
server.py — Flask Backend chính (Modularized)
  - Entry point cho Flask server
  - Đăng ký các Blueprints từ thư mục routes/
"""

from flask import Flask, render_template, send_from_directory
from flask_cors import CORS

# Cấu hình database
from database import DB_URI, init_db

# Import các Blueprints
from routes.users import users_bp
from routes.farms import farms_bp
from routes.ai_predict import ai_bp, load_model
from routes.sensors import sensors_bp
from routes.camera import camera_bp

app = Flask(__name__, static_folder='.', template_folder='.')
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'nckh_nongnghiep_2026'

if 'tidbcloud.com' in (DB_URI or ''):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "connect_args": {
            "ssl": {"ssl_mode": "REQUIRED"},
            "connect_timeout": 5,   # Tiết kiệm RAM, timeout nhanh nếu TiDB pause
        },
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

# ========================================================
# ĐĂNG KÝ BLUEPRINTS (Chuẩn hóa tiền tố /api)
# ========================================================
app.register_blueprint(users_bp, url_prefix='/api')
app.register_blueprint(farms_bp, url_prefix='/api')
app.register_blueprint(ai_bp,    url_prefix='/api')
app.register_blueprint(sensors_bp, url_prefix='/api')
app.register_blueprint(camera_bp,  url_prefix='/api')


# ========================================================
# DOWNLOAD ROUTES
# ========================================================
@app.route('/api/download-client')
def download_client():
    import os
    client_path = os.path.join(app.root_path, 'client_app', 'dist')
    if not os.path.exists(os.path.join(client_path, 'HeThongCamera_AI.exe')):
        return "File chưa được build. Vui lòng chạy build_camera_exe.bat trên Server.", 404
    return send_from_directory(client_path, 'HeThongCamera_AI.exe', as_attachment=True)


# ========================================================
# ROUTES STATIC FILES VÀ TRANG CHỦ
# ========================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)


# ========================================================
# KHỞI TẠO HỆ THỐNG TRÊN MÁY CHỦ
# ========================================================
with app.app_context():
    init_db(app)
    load_model()

# ========================================================
# CHỈ KHỞI CHẠY THỦ CÔNG (Dành cho máy tính cá nhân)
# ========================================================
if __name__ == '__main__':
    print("=" * 50)
    print("  AI Nông Nghiệp — Server + Database (Modular)")
    print("=" * 50)
    
    # Ở local thì vẫn load model để test
    load_model()
    
    print(f"\n🌐 Truy cập: http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
