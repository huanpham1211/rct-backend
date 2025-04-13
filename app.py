from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
import jwt
import datetime

app = Flask(__name__)
CORS(app, origins=["https://rctmanager.com"])

# ✅ Securely get secret key from environment variable
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")

# ✅ Use Render PostgreSQL or fallback to local SQLite
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///local.db").replace("postgres://", "postgresql://")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ✅ Define table name to match PostgreSQL "users" table
class Users(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

# ✅ Token generator
def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token

# ✅ Login API
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

# ✅ Create user API
@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    hashed_pw = generate_password_hash(data["password"])
    new_user = Users(username=data["username"], password=hashed_pw, role=data["role"])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"success": True, "message": "User created successfully."})

# ✅ Only run locally
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # only useful for local SQLite
    app.run(debug=True)
