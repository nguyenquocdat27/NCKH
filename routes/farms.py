from flask import Blueprint, request, jsonify
from database import db, Vuon

farms_bp = Blueprint('farms', __name__)

@farms_bp.route('/api/vuons', methods=['POST'])
def create_vuon():
    """Thêm vườn mới"""
    try:
        data = request.get_json()
        if not data or not data.get('user_id') or not data.get('ten_vuon'):
            return jsonify({'error': 'Thiếu user_id hoặc tên vườn'}), 400

        vuon = Vuon(
            user_id   = data['user_id'],
            ten_vuon  = data['ten_vuon'],
            loai_cay  = data.get('loai_cay', 'Cây ớt'),
            dia_chi   = data.get('dia_chi', ''),
            ghi_chu   = data.get('ghi_chu', ''),
        )
        db.session.add(vuon)
        db.session.commit()
        return jsonify({'message': 'Thêm vườn thành công!', 'vuon': vuon.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@farms_bp.route('/api/vuons', methods=['GET'])
def get_vuons():
    """Lấy tất cả vườn (hoặc lọc theo user_id)"""
    user_id = request.args.get('user_id')
    if user_id:
        vuons = Vuon.query.filter_by(user_id=user_id).order_by(Vuon.ngay_tao.desc()).all()
    else:
        vuons = Vuon.query.order_by(Vuon.ngay_tao.desc()).all()
    return jsonify([v.to_dict() for v in vuons])


@farms_bp.route('/api/vuons/<int:vuon_id>', methods=['GET'])
def get_vuon(vuon_id):
    """Lấy thông tin 1 vườn"""
    vuon = Vuon.query.get_or_404(vuon_id)
    return jsonify(vuon.to_dict())


@farms_bp.route('/api/vuons/<int:vuon_id>', methods=['PUT'])
def update_vuon(vuon_id):
    """Cập nhật thông tin vườn"""
    try:
        vuon = Vuon.query.get_or_404(vuon_id)
        data = request.get_json()
        vuon.ten_vuon  = data.get('ten_vuon',  vuon.ten_vuon)
        vuon.loai_cay  = data.get('loai_cay',  vuon.loai_cay)
        vuon.dia_chi   = data.get('dia_chi',   vuon.dia_chi)
        vuon.ghi_chu   = data.get('ghi_chu',   vuon.ghi_chu)
        db.session.commit()
        return jsonify({'message': 'Cập nhật vườn thành công!', 'vuon': vuon.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@farms_bp.route('/api/vuons/<int:vuon_id>', methods=['DELETE'])
def delete_vuon(vuon_id):
    """Xóa vườn"""
    try:
        vuon = Vuon.query.get_or_404(vuon_id)
        db.session.delete(vuon)
        db.session.commit()
        return jsonify({'message': f'Đã xóa vườn {vuon.ten_vuon}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
