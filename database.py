"""
database.py — Quản lý MySQL
Bảng: users (người dùng) + vuons (nhà vườn)

Cách dùng: import từ server.py
  from database import db, User, Vuon, init_db
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ========================================================
# ⚙️ CẤU HÌNH DATABASE (Đã chuyển sang SQLite cho dễ Deploy)
# ========================================================
import os
basedir = os.path.abspath(os.path.dirname(__file__))
DB_URI = 'sqlite:///' + os.path.join(basedir, 'nckh_nongnghiep.db')
# ========================================================
# ========================================================


# ========================================================
# BẢNG NGƯỜI DÙNG
# ========================================================
class User(db.Model):
    __tablename__ = 'users'

    id          = db.Column(db.Integer, primary_key=True)
    ho_ten      = db.Column(db.String(100), nullable=False)
    email       = db.Column(db.String(100), unique=True, nullable=False)
    password    = db.Column(db.String(255), nullable=False)
    so_dien_thoai = db.Column(db.String(20))
    ngay_tao    = db.Column(db.DateTime, default=datetime.utcnow)

    # 1 user có nhiều vườn
    vuons = db.relationship('Vuon', backref='chu_vuon', lazy=True,
                             cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':             self.id,
            'ho_ten':         self.ho_ten,
            'email':          self.email,
            'so_dien_thoai':  self.so_dien_thoai,
            'ngay_tao':       self.ngay_tao.strftime('%d/%m/%Y'),
            'so_vuon':        len(self.vuons),
        }


# ========================================================
# BẢNG NHÀ VƯỜN
# ========================================================
class Vuon(db.Model):
    __tablename__ = 'vuons'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ten_vuon    = db.Column(db.String(100), nullable=False)
    loai_cay    = db.Column(db.String(100), default='Cây ớt')
    dia_chi     = db.Column(db.String(200))
    ghi_chu     = db.Column(db.Text)
    ngay_tao    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':       self.id,
            'user_id':  self.user_id,
            'ten_vuon': self.ten_vuon,
            'loai_cay': self.loai_cay,
            'dia_chi':  self.dia_chi,
            'ghi_chu':  self.ghi_chu,
            'ngay_tao': self.ngay_tao.strftime('%d/%m/%Y'),
        }


# ========================================================
# KHỞI TẠO — tạo bảng nếu chưa có
# ========================================================
def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        print("✅ Database sẵn sàng!")
        print("   Bảng: users, vuons")
