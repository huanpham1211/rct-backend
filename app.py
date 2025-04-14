from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
import jwt
import datetime
from functools import wraps
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://rctmanager.com"]}})

# 🔐 SECRET KEY from environment
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")

# ✅ PostgreSQL or SQLite fallback
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///local.db").replace("postgres://", "postgresql://")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ✅ Users table
class Users(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

# ✅ Patients table
class Patient(db.Model):
    __tablename__ = "patient"
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, nullable=True)
    site_id = db.Column(db.Integer, nullable=True)
    para = db.Column(db.String(4), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    sex = db.Column(db.String(10), nullable=False)
    entered_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    timestamp_created = db.Column(db.DateTime, default=datetime.utcnow)
    timestamp_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ✅ Token generator
def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    
# ✅ Token decoder decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]  # Expect "Bearer <token>"

        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = Users.query.get(data['user_id'])
            if not current_user:
                return jsonify({"message": "User not found"}), 401
        except Exception as e:
            return jsonify({"message": "Invalid token"}), 401

        return f(current_user, *args, **kwargs)
    return decorated

@app.before_request
def handle_options_request():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        headers = response.headers

        # Allow specific headers and methods
        headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

# ✅ Login
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = Users.query.filter_by(username=data["username"]).first()
    if user and check_password_hash(user.password, data["password"]):
        token = generate_token(user.id)
        return jsonify({
            "success": True,
            "role": user.role,
            "token": token
        })
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

# ✅ Register user
@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    hashed_pw = generate_password_hash(data["password"])
    new_user = Users(username=data["username"], password=hashed_pw, role=data["role"])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"success": True, "message": "User created successfully."})

# ✅ Create patient API (requires token)
@app.route("/api/patients", methods=["POST"])
@token_required
def create_patient(current_user):
    data = request.get_json()
    try:
        new_patient = Patient(
            name=data["name"],
            dob=datetime.datetime.strptime(data["dob"], "%Y-%m-%d"),
            sex=data["sex"],
            para=data.get("para", "0000"),
            entered_by=current_user.id
        )
        db.session.add(new_patient)
        db.session.commit()
        return jsonify({"success": True, "message": "Patient added"}), 201
    except Exception as e:
        print("Error:", e)
        return jsonify({"success": False, "message": "Error saving patient"}), 500


@app.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.get_json()
    user = Users.query.get(user_id)

    if not check_password_hash(user.password, data['oldPassword']):
        return jsonify({"success": False, "message": "Mật khẩu cũ không đúng"}), 400

    user.password = generate_password_hash(data['newPassword'])
    db.session.commit()
    return jsonify({"success": True, "message": "Đổi mật khẩu thành công!"})

# ✅ Create all tables (local only)
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
