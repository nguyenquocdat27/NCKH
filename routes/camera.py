import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from database import db, Vuon, CameraAnalysis
from routes.ai_predict import perform_prediction

camera_bp = Blueprint('camera', __name__)

# Bộ nhớ đệm lưu thời điểm ping cuối của Camera Client (vuon_id -> datetime)
last_ping_times = {}

@camera_bp.route('/camera/settings/<int:vuon_id>', methods=['GET'])
def get_camera_settings(vuon_id):
    """Lấy cấu hình camera của vườn và kiểm tra trạng thái hoạt động của Client"""
    vuon = Vuon.query.get(vuon_id)
    if not vuon:
        return jsonify({'error': 'Không tìm thấy vườn'}), 404
        
    # Nếu client=true, nghĩa là client python đang ping lên
    is_client = request.args.get('client') == 'true'
    if is_client:
        last_ping_times[vuon_id] = datetime.utcnow()

    # Tính toán trạng thái online
    last_seen = last_ping_times.get(vuon_id)
    is_online = False
    last_seen_str = "Ngoại tuyến (Chưa có tín hiệu)"
    
    if last_seen:
        diff_seconds = (datetime.utcnow() - last_seen).total_seconds()
        is_online = diff_seconds < 15  # Online nếu ping trong vòng 15 giây qua
        
        if diff_seconds < 10:
            last_seen_str = "Hoạt động: Vừa xong"
        elif diff_seconds < 60:
            last_seen_str = f"Hoạt động: {int(diff_seconds)} giây trước"
        else:
            last_seen_str = f"Hoạt động: {int(diff_seconds / 60)} phút trước"

    return jsonify({
        'vuon_id': vuon.id,
        'camera_interval': vuon.camera_interval,
        'camera_command': vuon.camera_command,
        'is_online': is_online,
        'last_seen': last_seen_str
    })



@camera_bp.route('/camera/settings/<int:vuon_id>', methods=['PUT'])
def update_camera_settings(vuon_id):
    """Cập nhật chu kỳ chụp hoặc ra lệnh chụp từ server"""
    try:
        vuon = Vuon.query.get(vuon_id)
        if not vuon:
            return jsonify({'error': 'Không tìm thấy vườn'}), 404

        data = request.get_json() or {}
        
        # Cập nhật interval nếu được gửi lên
        if 'camera_interval' in data:
            vuon.camera_interval = int(data['camera_interval'])

        # Cập nhật command nếu được gửi lên (VD: 'capture')
        if 'camera_command' in data:
            vuon.camera_command = data['camera_command']

        db.session.commit()
        return jsonify({
            'message': 'Cập nhật cấu hình camera thành công!',
            'camera_interval': vuon.camera_interval,
            'camera_command': vuon.camera_command
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@camera_bp.route('/camera/upload/<int:vuon_id>', methods=['POST'])
def camera_upload(vuon_id):
    """Client upload ảnh lên sau khi chụp, phân tích AI và lưu lịch sử"""
    try:
        vuon = Vuon.query.get(vuon_id)
        if not vuon:
            return jsonify({'error': 'Không tìm thấy vườn'}), 404

        # Cập nhật thời điểm tương tác cuối của client
        last_ping_times[vuon_id] = datetime.utcnow()

        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'Thiếu dữ liệu hình ảnh (base64)'}), 400

        base64_image = data['image']

        # Chạy AI phân tích ảnh vừa chụp
        print(f"📡 [CAMERA] Đang phân tích ảnh từ Camera vườn {vuon.ten_vuon}...")
        ai_result = perform_prediction(base64_image)

        # Lưu thông tin phân tích vào lịch sử database
        new_analysis = CameraAnalysis(
            vuon_id         = vuon_id,
            image_data      = base64_image,
            scores          = json.dumps(ai_result['scores']),
            deficient_names = json.dumps(ai_result['deficient_names']),
            recommendations = json.dumps(ai_result['recommendations']),
            healthy         = ai_result['healthy']
        )
        
        # Reset lệnh chụp từ server về idle
        vuon.camera_command = 'idle'
        
        db.session.add(new_analysis)
        db.session.commit()

        print(f"✅ [CAMERA] Đã phân tích xong và lưu vào Lịch sử (ID: {new_analysis.id})")
        return jsonify({
            'message': 'Phân tích và lưu trữ thành công!',
            'analysis': new_analysis.to_dict(),
            'ai_result': ai_result
        }), 201

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"Lỗi xử lý upload camera: {str(e)}"}), 500


@camera_bp.route('/camera/history/<int:vuon_id>', methods=['GET'])
def get_camera_history(vuon_id):
    """Lấy danh sách các bức ảnh đã chụp & phân tích lịch sử của vườn"""
    try:
        limit = request.args.get('limit', 20, type=int)
        history = CameraAnalysis.query.filter_by(vuon_id=vuon_id)\
                                      .order_by(CameraAnalysis.timestamp.desc())\
                                      .limit(limit).all()
        return jsonify([item.to_dict() for item in history])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@camera_bp.route('/camera/capture_local/<int:vuon_id>', methods=['POST'])
def capture_local(vuon_id):
    """Dành cho chạy LOCAL: Server trực tiếp mở OpenCV Camera để chụp và phân tích luôn"""
    try:
        import cv2
        import time
        import base64

        vuon = Vuon.query.get(vuon_id)
        if not vuon:
            return jsonify({'error': 'Không tìm thấy vườn'}), 404

        camera_index = request.args.get('index', 0, type=int)
        print(f"📸 [LOCAL CAPTURE] Đang mở Camera local với index: {camera_index}...")

        # Thử mở camera tối đa 3 lần với khoảng cách 1 giây để phần cứng ổn định
        cap = None
        for attempt in range(3):
            print(f"   - [LOCAL CAPTURE] Thử kết nối Camera lần {attempt + 1}/3...")
            cap = cv2.VideoCapture(camera_index)
            if cap.isOpened():
                break
            cap.release()
            time.sleep(1)
        else:
            # Thử chuyển về index 0 nếu index chỉ định bị lỗi
            if camera_index != 0:
                print(f"⚠️ [LOCAL CAPTURE] Không mở được camera {camera_index}, thử chuyển về index 0...")
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    return jsonify({'error': f'Không thể mở USB Camera tại INDEX {camera_index} hoặc INDEX 0!'}), 400
            else:
                return jsonify({'error': f'Không thể mở USB Camera tại INDEX {camera_index}!'}), 400

        # Chờ camera tự động lấy nét và phơi sáng
        time.sleep(2)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return jsonify({'error': 'Không thể đọc hình ảnh từ Camera!'}), 400

        # Nén ảnh thành Base64
        _, buffer = cv2.imencode('.jpg', frame)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        base64_image = f"data:image/jpeg;base64,{img_b64}"

        # Chạy AI phân tích
        ai_result = perform_prediction(base64_image)

        # Lưu lịch sử
        new_analysis = CameraAnalysis(
            vuon_id         = vuon_id,
            image_data      = base64_image,
            scores          = json.dumps(ai_result['scores']),
            deficient_names = json.dumps(ai_result['deficient_names']),
            recommendations = json.dumps(ai_result['recommendations']),
            healthy         = ai_result['healthy']
        )
        
        # Reset lệnh chụp về idle
        vuon.camera_command = 'idle'
        
        db.session.add(new_analysis)
        db.session.commit()

        return jsonify({
            'message': 'Chụp ảnh local và phân tích AI thành công!',
            'analysis': new_analysis.to_dict(),
            'ai_result': ai_result
        }), 201



@camera_bp.route('/camera/history/<int:vuon_id>/<int:record_id>', methods=['DELETE'])
def delete_camera_history(vuon_id, record_id):
    """Xóa một ảnh trong lịch sử"""
    try:
        record = CameraAnalysis.query.filter_by(id=record_id, vuon_id=vuon_id).first()
        if not record:
            return jsonify({'error': 'Không tìm thấy bản ghi'}), 404
            
        db.session.delete(record)
        db.session.commit()
        return jsonify({'message': 'Đã xóa bản ghi thành công!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@camera_bp.route('/camera/history/cleanup/<int:vuon_id>', methods=['DELETE'])
def cleanup_camera_history(vuon_id):
    """Xóa tất cả ảnh đã chụp của vườn này"""
    try:
        records = CameraAnalysis.query.filter_by(vuon_id=vuon_id).all()
        count = len(records)
        
        for record in records:
            db.session.delete(record)
            
        db.session.commit()
        return jsonify({'message': f'Đã xóa {count} bản ghi cũ thành công!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

