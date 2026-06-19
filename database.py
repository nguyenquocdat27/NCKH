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
    camera_interval = db.Column(db.Integer, default=30) # Chu kỳ tự động chụp (phút), 0 là tắt
    camera_command  = db.Column(db.String(50), default='idle') # Lệnh từ server: 'idle' hoặc 'capture'
    ngay_tao    = db.Column(db.DateTime, default=datetime.utcnow)

    # Quan hệ với cảm biến
    sensors = db.relationship('SensorData', backref='thuoc_vuon', lazy=True,
                               cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':              self.id,
            'user_id':         self.user_id,
            'ten_vuon':        self.ten_vuon,
            'loai_cay':        self.loai_cay,
            'dia_chi':         self.dia_chi,
            'ghi_chu':         self.ghi_chu,
            'camera_interval': self.camera_interval,
            'camera_command':  self.camera_command,
            'ngay_tao':        self.ngay_tao.strftime('%d/%m/%Y'),
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
            'timestamp':   self.timestamp.isoformat() + 'Z',
        }


# ========================================================
# BẢNG LỊCH SỬ CAMERA PHÂN TÍCH AI
# ========================================================
class CameraAnalysis(db.Model):
    __tablename__ = 'camera_analysis'

    id              = db.Column(db.Integer, primary_key=True)
    vuon_id         = db.Column(db.Integer, db.ForeignKey('vuons.id'), nullable=False)
    image_data      = db.Column(db.Text(4294967295), nullable=False) # Base64 string ảnh chụp (để size cực lớn -> LONGTEXT)
    scores          = db.Column(db.Text) # Điểm số AI dạng chuỗi JSON
    deficient_names = db.Column(db.Text) # Các chất bị thiếu (ví dụ: JSON list ["Canxi (Ca)"])
    recommendations = db.Column(db.Text) # Lời khuyên tổng hợp từ AI dạng JSON list
    healthy         = db.Column(db.Boolean, default=True)
    timestamp       = db.Column(db.DateTime, default=datetime.utcnow)

    # Thiết lập quan hệ ngược
    vuon = db.relationship('Vuon', backref=db.backref('camera_history', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        import json
        try:
            scores_dict = json.loads(self.scores) if self.scores else {}
        except:
            scores_dict = {}

        try:
            deficient_list = json.loads(self.deficient_names) if self.deficient_names else []
        except:
            deficient_list = [self.deficient_names] if self.deficient_names else []

        try:
            recommendations_list = json.loads(self.recommendations) if self.recommendations else []
        except:
            recommendations_list = [self.recommendations] if self.recommendations else []

        return {
            'id':              self.id,
            'vuon_id':         self.vuon_id,
            'image_data':      self.image_data,
            'scores':          scores_dict,
            'deficient_names': deficient_list,
            'recommendations': recommendations_list,
            'healthy':         self.healthy,
            'timestamp':       self.timestamp.isoformat() + 'Z',
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
            print("   Bảng: users, vuons, sensor_data, camera_analysis")
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
                return

        # Thực hiện di chuyển cơ sở dữ liệu tự động (Add columns) để không lỗi dữ liệu cũ
        try:
            # Chạy các câu lệnh SQL alter table trực tiếp
            from sqlalchemy import text
            with db.engine.connect() as conn:
                # Check và thêm camera_interval
                try:
                    conn.execute(text("ALTER TABLE vuons ADD COLUMN camera_interval INTEGER DEFAULT 30"))
                    conn.commit()
                    print("⚙️  Đã thêm cột camera_interval vào bảng vuons!")
                except Exception:
                    pass

                # Check và thêm camera_command
                try:
                    conn.execute(text("ALTER TABLE vuons ADD COLUMN camera_command VARCHAR(50) DEFAULT 'idle'"))
                    conn.commit()
                    print("⚙️  Đã thêm cột camera_command vào bảng vuons!")
                except Exception:
                    pass
                    
                # Nâng cấp image_data lên LONGTEXT để chứa ảnh lớn
                try:
                    conn.execute(text("ALTER TABLE camera_analysis MODIFY image_data LONGTEXT"))
                    conn.commit()
                    print("⚙️  Đã nâng cấp cột image_data lên LONGTEXT!")
                except Exception:
                    pass
        except Exception as e_mig:
            print(f"⚠️  Lỗi khi chạy migration tự động: {e_mig}")


