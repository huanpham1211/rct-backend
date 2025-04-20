from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from models import db, Users  # ✅ clean and modular

users_bp = Blueprint('users', __name__, url_prefix='/api/users')

# GET: List all users (admin only)
@users_bp.route('/', methods=['GET'])
@jwt_required()
def get_users():
    current_user = Users.query.get(get_jwt_identity())
    if current_user.role != "admin":
        return jsonify({"message": "Access denied"}), 403

    users = Users.query.all()
    return jsonify([
        {
            "id": user.id,
            "username": user.username,
            "role": user.role
        } for user in users
    ]), 200

# POST: Create user (admin only)
@users_bp.route('/', methods=['POST'])
@jwt_required()
def create_user():
    current_user = Users.query.get(get_jwt_identity())
    if current_user.role != "admin":
        return jsonify({"message": "Access denied"}), 403

    data = request.get_json()
    hashed_pw = generate_password_hash(data["password"])
    new_user = Users(
        username=data["username"],
        password=hashed_pw,
        role=data["role"]
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created successfully."}), 201

# POST: Reset password
@users_bp.route('/<int:user_id>/reset-password', methods=['POST'])
@jwt_required()
def reset_password(user_id):
    current_user = Users.query.get(get_jwt_identity())
    if current_user.role != "admin":
        return jsonify({"message": "Access denied"}), 403

    data = request.get_json()
    new_password = data.get('password')
    if not new_password:
        return jsonify({"message": "Password is required"}), 400

    user = Users.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    user.password = generate_password_hash(new_password)
    db.session.commit()
    return jsonify({"message": "Password updated"}), 200

# POST: Update user role
@users_bp.route('/<int:user_id>/update-role', methods=['POST'])
@jwt_required()
def update_role(user_id):
    current_user = Users.query.get(get_jwt_identity())
    if current_user.role != "admin":
        return jsonify({"message": "Access denied"}), 403

    data = request.get_json()
    new_role = data.get('role')
    if not new_role:
        return jsonify({"message": "Role is required"}), 400

    user = Users.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    user.role = new_role
    db.session.commit()
    return jsonify({"message": "Role updated"}), 200

# routes/users.py or wherever user routes are handled
@users_bp.route('/<int:user_id>/update-info', methods=['POST'])
@jwt_required()
def update_user_info(user_id):
    current_user = get_jwt_identity()
    user = Users.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.get_json()
    user.first_name = data.get('first_name', user.first_name)
    user.last_name = data.get('last_name', user.last_name)
    user.title = data.get('title', user.title)

    db.session.commit()
    return jsonify({"message": "User info updated successfully"}), 200
