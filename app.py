from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity
)
import os

# App setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://rctmanager.com"]}})

# JWT & DB Configuration
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
app.config["JWT_SECRET_KEY"] = app.config["SECRET_KEY"]
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_HEADER_NAME"] = "Authorization"
app.config["JWT_HEADER_TYPE"] = "Bearer"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=2)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///local.db").replace("postgres://", "postgresql://")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

jwt = JWTManager(app)
db = SQLAlchemy(app)

# Database Models
class Users(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

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

class Site(db.Model):
    __tablename__ = "site"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False)
    location = db.Column(db.Text)
    timestamp_created = db.Column(db.DateTime, default=datetime.utcnow)
    timestamp_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

class Study(db.Model):
    __tablename__ = 'study'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    protocol_number = db.Column(db.String(100))
    irb_number = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    timestamp_created = db.Column(db.DateTime, default=datetime.utcnow)
    timestamp_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StudySite(db.Model):
    __tablename__ = 'study_site'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    timestamp_created = db.Column(db.DateTime, default=datetime.utcnow)

# JWT error handlers
@jwt.unauthorized_loader
def handle_missing_token(error):
    return jsonify({"success": False, "message": "Token is missing!"}), 401

@jwt.invalid_token_loader
def handle_invalid_token(error):
    return jsonify({"success": False, "message": "Invalid token!"}), 401

@jwt.expired_token_loader
def handle_expired_token(jwt_header, jwt_payload):
    return jsonify({"success": False, "message": "Token has expired!"}), 401

# Routes
@app.before_request
def handle_options_request():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        headers = response.headers
        headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = Users.query.filter_by(username=data["username"]).first()
    if user and check_password_hash(user.password, data["password"]):
        token = create_access_token(identity=user.id)
        return jsonify({"success": True, "role": user.role, "token": token})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route("/users", methods=["POST"])
@jwt_required()
def create_user():
    current_user = Users.query.get(get_jwt_identity())
    if current_user.role != "admin":
        return jsonify({"success": False, "message": "Access denied"}), 403
    data = request.get_json()
    hashed_pw = generate_password_hash(data["password"])
    new_user = Users(username=data["username"], password=hashed_pw, role=data["role"])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"success": True, "message": "User created successfully."})

@app.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    data = request.get_json()
    old_pw = data.get('oldPassword')
    new_pw = data.get('newPassword')
    if not old_pw or not new_pw:
        return jsonify({"success": False, "message": "Missing password fields"}), 400

    user = Users.query.get(get_jwt_identity())
    if not user or not check_password_hash(user.password, old_pw):
        return jsonify({"success": False, "message": "Incorrect old password"}), 400

    user.password = generate_password_hash(new_pw)
    db.session.commit()
    return jsonify({"success": True, "message": "Password updated successfully"})

@app.route("/api/sites", methods=["GET", "POST"])
@jwt_required()
def handle_sites():
    current_user = Users.query.get(get_jwt_identity())

    if current_user.role != "admin":
        return jsonify({"message": "Access denied"}), 403

    if request.method == "POST":
        data = request.get_json()
        if not data.get("name") or not data.get("location"):
            return jsonify({"message": "Name and location are required"}), 400
        if Site.query.filter_by(name=data["name"]).first():
            return jsonify({"message": "Site with this name already exists"}), 400

        site = Site(name=data["name"], location=data["location"], timestamp_created=datetime.utcnow())
        db.session.add(site)
        db.session.commit()
        return jsonify({"message": "Site created"}), 201

    sites = Site.query.all()
    return jsonify([{
        "id": s.id,
        "name": s.name,
        "location": s.location,
        "created": s.timestamp_created.isoformat() if s.timestamp_created else None,
        "updated": s.timestamp_updated.isoformat() if s.timestamp_updated else None
    } for s in sites])

@app.route("/api/sites/<int:site_id>", methods=["PUT", "DELETE"])
@jwt_required()
def modify_site(site_id):
    current_user = Users.query.get(get_jwt_identity())
    if current_user.role != "admin":
        return jsonify({"message": "Access denied"}), 403

    site = Site.query.get(site_id)
    if not site:
        return jsonify({"message": "Site not found"}), 404

    if request.method == "PUT":
        data = request.get_json()
        site.name = data.get("name", site.name)
        site.location = data.get("location", site.location)
        db.session.commit()
        return jsonify({"message": "Site updated"}), 200

    if StudySite.query.filter_by(site_id=site_id).first():
        return jsonify({"message": "Cannot delete: Site linked to study"}), 400

    db.session.delete(site)
    db.session.commit()
    return jsonify({"message": "Site deleted"}), 200


# Initialize tables
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
