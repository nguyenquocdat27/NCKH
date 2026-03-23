from flask import Blueprint, request, jsonify
from database import db, User

users_bp = Blueprint('users', __name__)

@users_bp.route('/login', methods=['POST'])
def login():
    """Đăng nhập — kiểm tra email + password"""
    try:
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Thiếu email hoặc mật khẩu'}), 400

        user = User.query.filter_by(email=data['email']).first()
        if not user:
            return jsonify({'error': 'Email không tồn tại'}), 404
        if user.password != data['password']:
            return jsonify({'error': 'Mật khẩu không đúng'}), 401

        return jsonify({'message': 'Đăng nhập thành công!', 'user': user.to_dict()})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@users_bp.route('/users', methods=['POST'])
def create_user():
    """Tạo người dùng mới"""
    try:
        data = request.get_json()
        if not data or not data.get('ho_ten') or not data.get('email'):
            return jsonify({'error': 'Thiếu họ tên hoặc email'}), 400

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email đã tồn tại'}), 400

        user = User(
            ho_ten          = data['ho_ten'],
            email           = data['email'],
            password        = data.get('password', ''),
            so_dien_thoai   = data.get('so_dien_thoai', ''),
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'Tạo người dùng thành công!', 'user': user.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@users_bp.route('/users', methods=['GET'])
def get_users():
    """Lấy danh sách người dùng"""
    users = User.query.order_by(User.ngay_tao.desc()).all()
    return jsonify([u.to_dict() for u in users])


@users_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Lấy thông tin 1 người dùng"""
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


@users_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Cập nhật thông tin người dùng"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        if 'ho_ten':        user.ho_ten         = data.get('ho_ten', user.ho_ten)
        if 'so_dien_thoai': user.so_dien_thoai  = data.get('so_dien_thoai', user.so_dien_thoai)
        db.session.commit()
        return jsonify({'message': 'Cập nhật thành công!', 'user': user.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@users_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Xóa người dùng (kèm toàn bộ vườn)"""
    try:
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': f'Đã xóa người dùng {user.ho_ten}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
