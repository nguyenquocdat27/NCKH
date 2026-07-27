from flask import Blueprint, request, jsonify
from database import db, SensorData, Vuon, User
from datetime import datetime

sensors_bp = Blueprint('sensors', __name__)

@sensors_bp.route('/sensors', methods=['POST'])
def add_sensor_data():
    """Nhận dữ liệu từ ESP32 và lưu vào database"""
    try:
        data = request.get_json()
        if not data or 'vuon_id' not in data:
            return jsonify({'error': 'Thiếu vuon_id'}), 400

        # Kiểm tra vườn có tồn tại không
        vuon = Vuon.query.get(data['vuon_id'])
        if not vuon:
            # Tạo vườn tự động nếu chưa có để ESP32 chạy thông suốt
            user = User.query.first()
            if not user:
                # Tạo một user admin mặc định nếu DB rỗng
                user = User(
                    ho_ten="Admin",
                    email="admin@gmail.com",
                    password="pbkdf2:sha256:260000$defaultpassword$123"
                )
                db.session.add(user)
                db.session.commit()
            
            vuon = Vuon(
                id=data['vuon_id'],
                user_id=user.id,
                ten_vuon=f"Vườn ESP32 ({data['vuon_id']})",
                loai_cay="Cây ớt",
                manual=False,
                fan_state=False,
                pump_state=False
            )
            db.session.add(vuon)
            db.session.commit()

        # Đọc dữ liệu cảm biến
        temperature = data.get('temperature')
        humidity = data.get('humidity')
        light = data.get('light')

        # Logic điều khiển tự động
        if not vuon.manual:
            if temperature is not None:
                # Quạt bật khi nhiệt độ > 30°C
                vuon.fan_state = True if temperature > 30.0 else False
            if humidity is not None:
                # Bơm nước bật khi độ ẩm đất < 50%
                vuon.pump_state = True if humidity < 50.0 else False

        # Lưu dữ liệu lịch sử cảm biến
        new_data = SensorData(
            vuon_id     = data['vuon_id'],
            temperature = temperature,
            humidity    = humidity,
            light       = light
        )
        db.session.add(new_data)
        db.session.commit()

        # ESP32 bắt buộc nhận về cấu hình thiết bị
        return jsonify({
            'manual': vuon.manual,
            'fan_state': vuon.fan_state,
            'pump_state': vuon.pump_state
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@sensors_bp.route('/sensors/<int:vuon_id>', methods=['GET'])
def get_sensor_history(vuon_id):
    """Lấy lịch sử dữ liệu cảm biến của 1 vườn"""
    limit = request.args.get('limit', 20, type=int)
    history = SensorData.query.filter_by(vuon_id=vuon_id)\
                        .order_by(SensorData.timestamp.desc())\
                        .limit(limit).all()
    
    # Đảo ngược lại để hiển thị từ cũ đến mới trên biểu đồ
    return jsonify([d.to_dict() for d in reversed(history)])


@sensors_bp.route('/control', methods=['GET'])
def get_control_state():
    """Lấy trạng thái thiết bị hiện tại (Cho Frontend)"""
    vuon_id = request.args.get('vuon_id', type=int)
    if not vuon_id:
        vuon = Vuon.query.first()
    else:
        vuon = Vuon.query.get(vuon_id)
        
    if not vuon:
        return jsonify({
            "manual": False,
            "fan_state": False,
            "pump_state": False
        })
        
    return jsonify({
        "manual": vuon.manual,
        "fan_state": vuon.fan_state,
        "pump_state": vuon.pump_state
    })


@sensors_bp.route('/control', methods=['POST'])
def update_control_state():
    """Cập nhật trạng thái từ nút nhấn hoặc switch trên Web"""
    try:
        data = request.get_json() or {}
        vuon_id = data.get('vuon_id') or request.args.get('vuon_id', type=int)
        
        if not vuon_id:
            vuon = Vuon.query.first()
        else:
            vuon = Vuon.query.get(vuon_id)
            
        if not vuon:
            user = User.query.first()
            if not user:
                user = User(
                    ho_ten="Admin",
                    email="admin@gmail.com",
                    password="pbkdf2:sha256:260000$defaultpassword$123"
                )
                db.session.add(user)
                db.session.commit()
            vuon = Vuon(
                id=vuon_id or 30001,
                user_id=user.id,
                ten_vuon=f"Vườn ESP32 ({vuon_id or 30001})",
                loai_cay="Cây ớt",
                manual=False,
                fan_state=False,
                pump_state=False
            )
            db.session.add(vuon)
            db.session.commit()
            
        if 'manual' in data:
            vuon.manual = bool(data['manual'])
        if 'fan_state' in data:
            vuon.fan_state = bool(data['fan_state'])
        if 'pump_state' in data:
            vuon.pump_state = bool(data['pump_state'])
            
        db.session.commit()
        return jsonify({"success": True}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@sensors_bp.route('/device_history/<int:vuon_id>', methods=['GET'])
def get_device_last_active(vuon_id):
    """Lấy thời điểm cuối cùng thiết bị hoạt động dựa trên cảm biến"""
    try:
        last_fan = SensorData.query.filter(SensorData.vuon_id == vuon_id, SensorData.temperature > 30.0)\
                                   .order_by(SensorData.timestamp.desc()).first()
        last_pump = SensorData.query.filter(SensorData.vuon_id == vuon_id, SensorData.humidity < 50.0)\
                                    .order_by(SensorData.timestamp.desc()).first()
        latest_record = SensorData.query.filter(SensorData.vuon_id == vuon_id)\
                                        .order_by(SensorData.timestamp.desc()).first()
                                   
        is_offline = True
        if latest_record:
            # So sánh thời gian (UTC)
            diff = (datetime.utcnow() - latest_record.timestamp).total_seconds()
            is_offline = diff > 15

        return jsonify({
            "last_fan_on": last_fan.timestamp.isoformat() + 'Z' if last_fan else None,
            "last_pump_on": last_pump.timestamp.isoformat() + 'Z' if last_pump else None,
            "is_offline": is_offline,
            "last_seen": latest_record.timestamp.isoformat() + 'Z' if latest_record else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
