from flask import Blueprint, request, jsonify
from database import db, SensorData, Vuon
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
            return jsonify({'error': 'Không tìm thấy vườn'}), 404

        new_data = SensorData(
            vuon_id     = data['vuon_id'],
            temperature = data.get('temperature'),
            humidity    = data.get('humidity'),
            light       = data.get('light')
        )
        db.session.add(new_data)
        db.session.commit()
        return jsonify({'message': 'Lưu dữ liệu cảm biến thành công!', 'data': new_data.to_dict()}), 201

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
