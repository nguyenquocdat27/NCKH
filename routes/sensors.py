from flask import Blueprint, request, jsonify
from database import db, SensorData, Vuon, User
from datetime import datetime

sensors_bp = Blueprint('sensors', __name__)

@sensors_bp.route('/sensors', methods=['POST'])
def add_sensor_data():
    """Nhận dữ liệu từ ESP32 và lưu vào database (ESP32 tự điều khiển thiết bị)"""
    try:
        data = request.get_json()
        if not data or 'vuon_id' not in data:
            return jsonify({'error': 'Thiếu vuon_id'}), 400

        # Kiểm tra vườn có tồn tại không
        vuon = Vuon.query.get(data['vuon_id'])
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
                id=data['vuon_id'],
                user_id=user.id,
                ten_vuon=f"Vườn ESP32 ({data['vuon_id']})",
                loai_cay="Cây ớt",
            )
            db.session.add(vuon)
            db.session.commit()

        # Lưu dữ liệu lịch sử cảm biến
        new_data = SensorData(
            vuon_id     = data['vuon_id'],
            temperature = data.get('temperature'),
            humidity    = data.get('humidity'),
            light       = data.get('light')
        )
        db.session.add(new_data)
        db.session.commit()

        # ESP32 tự điều khiển cục bộ — server chỉ xác nhận đã lưu
        return jsonify({'ok': True}), 200

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

@sensors_bp.route('/device_history/<int:vuon_id>', methods=['GET'])
def get_device_last_active(vuon_id):
    """Lấy thời điểm cuối cùng thiết bị hoạt động"""
    try:
        latest_record = SensorData.query.filter_by(vuon_id=vuon_id)\
                                        .order_by(SensorData.timestamp.desc()).first()

        is_offline = True
        if latest_record:
            diff = (datetime.utcnow() - latest_record.timestamp).total_seconds()
            is_offline = diff > 45

        return jsonify({
            "is_offline": is_offline,
            "last_seen":  latest_record.timestamp.isoformat() + 'Z' if latest_record else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
