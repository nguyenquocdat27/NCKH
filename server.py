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

app = Flask(__name__, static_folder='.', template_folder='.')
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'nckh_nongnghiep_2026'

# ========================================================
# ĐĂNG KÝ BLUEPRINTS
# ========================================================
app.register_blueprint(users_bp)
app.register_blueprint(farms_bp)
app.register_blueprint(ai_bp)

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
# KHỞI CHẠY SERVER
# ========================================================
if __name__ == '__main__':
    print("=" * 50)
    print("  AI Nông Nghiệp — Server + Database (Modular)")
    print("=" * 50)
    
    init_db(app)
    load_model()
    
    print(f"\n🌐 Truy cập: http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
