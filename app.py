from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from traceback import format_exc  # Add this at the top if not already


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

class Site(db.Model):
    __tablename__ = "site"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False)
    location = db.Column(db.Text)
    timestamp_created = db.Column(db.DateTime)
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
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    timestamp_created = db.Column(db.DateTime, default=datetime.utcnow)

# ✅ Token generator
def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=2)
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
@token_required
def create_user(current_user):
    if current_user.role != "admin":
        return jsonify({"success": False, "message": "Access denied"}), 403

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

# ✅ Changepassword 
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

@app.route("/api/sites", methods=["GET", "POST"])
@token_required
def handle_sites(current_user):
    if current_user.role != "admin":
        return jsonify({"message": "Access denied"}), 403

    if request.method == "POST":
        data = request.get_json()
        if not data.get("name") or not data.get("location"):
            return jsonify({"message": "Name and location are required"}), 400

        existing_site = Site.query.filter_by(name=data["name"]).first()
        if existing_site:
            return jsonify({"message": "Site with this name already exists"}), 400

        try:
            new_site = Site(name=data["name"], location=data["location"], timestamp_created=datetime.utcnow())
            db.session.add(new_site)
            db.session.commit()
            return jsonify({"message": "Site created"}), 201
        except Exception as e:
            print("Error creating site:", e)
            return jsonify({"message": "Failed to create site"}), 500

    if request.method == "GET":
        try:
            sites = Site.query.all()
            return jsonify([
            {
                "id": s.id,
                "name": s.name,
                "location": s.location,
                "created": s.timestamp_created.isoformat() if s.timestamp_created else None,
                "updated": s.timestamp_updated.isoformat() if s.timestamp_updated else None
            } for s in sites])
        except Exception as e:
            print("Error fetching sites:", e)
            return jsonify({"message": "Failed to fetch sites"}), 500


@app.route("/api/sites/<int:site_id>", methods=["PUT"])
def update_site(site_id):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        user = Users.query.get(decoded["user_id"])
        if user.role != "admin":
            return jsonify({"message": "Access denied"}), 403
    except Exception as e:
        return jsonify({"message": "Invalid token"}), 401

    data = request.get_json()
    if not data.get("name") or not data.get("address"):
        return jsonify({"message": "Name and address are required"}), 400

    site = Site.query.get(site_id)
    if not site:
        return jsonify({"message": "Site not found"}), 404

    site.name = data["name"]
    site.address = data["address"]
    db.session.commit()
    return jsonify({"message": "Site updated"}), 200

@app.route("/api/studies", methods=["GET", "POST"])
@token_required
def handle_studies(current_user):
    if current_user.role not in ["admin", "studymanager"]:
        return jsonify({"message": "Access denied"}), 403

    if request.method == "POST":
        data = request.get_json()
        try:
            new_study = Study(
                name=data["name"],
                protocol_number=data.get("protocol_number"),
                irb_number=data.get("irb_number"),
                start_date=datetime.strptime(data.get("start_date"), "%Y-%m-%d") if data.get("start_date") else None,
                end_date=datetime.strptime(data.get("end_date"), "%Y-%m-%d") if data.get("end_date") else None
            )
            db.session.add(new_study)
            db.session.commit()
            return jsonify({"message": "Study created", "id": new_study.id}), 201
        except Exception as e:
            print("Error creating study:", e)
            return jsonify({"message": "Failed to create study"}), 500

    if request.method == "GET":
        studies = Study.query.order_by(Study.id.desc()).all()
        return jsonify([
            {
                "id": s.id,
                "name": s.name,
                "protocol_number": s.protocol_number,
                "irb_number": s.irb_number,
                "start_date": s.start_date.isoformat() if s.start_date else None,
                "end_date": s.end_date.isoformat() if s.end_date else None
            } for s in studies
        ])

@app.route("/api/studies/<int:id>", methods=["PUT", "DELETE"])
@token_required
def update_delete_study(current_user, id):
    if current_user.role not in ["admin", "studymanager"]:
        return jsonify({"message": "Access denied"}), 403

    study = Study.query.get_or_404(id)

    if request.method == "PUT":
        data = request.get_json()
        try:
            study.name = data.get("name", study.name)
            study.protocol_number = data.get("protocol_number", study.protocol_number)
            study.irb_number = data.get("irb_number", study.irb_number)
            study.start_date = datetime.datetime.strptime(data.get("start_date"), "%Y-%m-%d") if data.get("start_date") else study.start_date
            study.end_date = datetime.datetime.strptime(data.get("end_date"), "%Y-%m-%d") if data.get("end_date") else study.end_date
            db.session.commit()
            return jsonify({"message": "Study updated successfully"})
        except Exception as e:
            print("Error updating study:", e)
            return jsonify({"message": "Failed to update study"}), 500

    if request.method == "DELETE":
        try:
            db.session.delete(study)
            db.session.commit()
            return jsonify({"message": "Study deleted"})
        except Exception as e:
            print("Error deleting study:", e)
            return jsonify({"message": "Failed to delete study"}), 500

@app.route("/api/study-site", methods=["POST"])
@token_required
def link_study_site(current_user):
    if current_user.role not in ["admin", "studymanager"]:
        return jsonify({"message": "Access denied"}), 403

    data = request.get_json()
    try:
        new_link = StudySite(study_id=data["study_id"], site_id=data["site_id"])
        db.session.add(new_link)
        db.session.commit()
        return jsonify({"message": "Study linked to site"}), 201
    except Exception as e:
        print("Error linking study and site:", e)
        return jsonify({"message": "Link failed"}), 500


# ✅ Create all tables (local only)
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
