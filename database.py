import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ========================================================
# ⚙️ CẤU HÌNH DATABASE (Ưu tiên MySQL từ Môi trường)
# ========================================================
# Định dạng MySQL: mysql+pymysql://user:password@host:port/dbname
# SQLite dự phòng: sqlite:///nckh_nongnghiep.db

# Ưu tiên lấy từ biến môi trường (Cho Render)
DB_URI = os.getenv('DATABASE_URL')

# Nếu không có biến môi trường, hãy cấu hình ở đây
if not DB_URI:
    # BỎ dấu # ở dòng dưới để dùng MySQL (TiDB Cloud)
    # DB_URI = 'mysql+pymysql://2s4cbshgjt2rqzt.root:BO3ldmpvD4A0hKqH@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/test'
    
    # Nếu dòng trên vẫn bị đóng (#), nó sẽ dùng SQLite dưới đây
    if not DB_URI:
        basedir = os.path.abspath(os.path.dirname(__file__))
        DB_URI = 'sqlite:///' + os.path.join(basedir, 'nckh_nongnghiep.db')

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

    # Quan hệ với cảm biến
    sensors = db.relationship('SensorData', backref='thuoc_vuon', lazy=True,
                               cascade='all, delete-orphan')

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
# BẢNG DỮ LIỆU CẢM BIẾN
# ========================================================
class SensorData(db.Model):
    __tablename__ = 'sensor_data'

    id          = db.Column(db.Integer, primary_key=True)
    vuon_id     = db.Column(db.Integer, db.ForeignKey('vuons.id'), nullable=False)
    temperature = db.Column(db.Float)
    humidity    = db.Column(db.Float)
    light       = db.Column(db.Float)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':          self.id,
            'vuon_id':     self.vuon_id,
            'temperature': self.temperature,
            'humidity':    self.humidity,
            'light':       self.light,
            'timestamp':   self.timestamp.strftime('%H:%M:%S %d/%m/%Y'),
        }


# ========================================================
# KHỞI TẠO — tạo bảng nếu chưa có
# ========================================================
def init_db(app):
    db.init_app(app)
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database sẵn sàng!")
            print("   Bảng: users, vuons, sensor_data")
        except Exception as e:
            print(f"⚠️  TiDB không phản hồi ({e}) — chuyển sang SQLite dự phòng!")
            # Fallback về SQLite nếu TiDB bị pause
            basedir = os.path.abspath(os.path.dirname(__file__))
            fallback_uri = 'sqlite:///' + os.path.join(basedir, 'nckh_nongnghiep.db')
            app.config['SQLALCHEMY_DATABASE_URI'] = fallback_uri
            app.config.pop('SQLALCHEMY_ENGINE_OPTIONS', None)
            # Reinitialize với SQLite
            db.engine.dispose()
            try:
                db.create_all()
                print("✅ Database SQLite dự phòng đã sẵn sàng!")
            except Exception as e2:
                print(f"❌ Lỗi SQLite: {e2}")

