# routes/sites.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from models import db, Users, Site, StudySite

sites_bp = Blueprint('sites', __name__, url_prefix='/api/sites')

@sites_bp.route('', methods=['GET', 'POST'])
@jwt_required()
def handle_sites():
    try:
        user_id = get_jwt_identity()
        current_user = Users.query.get(user_id)

        if not current_user:
            return jsonify({"message": "User not found"}), 404
        if current_user.role != "admin":
            return jsonify({"message": "Access denied"}), 403

        if request.method == "POST":
            data = request.get_json()
            if not data.get("name") or not data.get("location"):
                return jsonify({"message": "Name and location are required"}), 400
            if Site.query.filter_by(name=data["name"]).first():
                return jsonify({"message": "Site with this name already exists"}), 400

            site = Site(
                name=data["name"],
                location=data["location"],
                timestamp_created=datetime.utcnow()
            )
            db.session.add(site)
            db.session.commit()
            return jsonify({"message": "Site created"}), 201

        sites = Site.query.all()
        return jsonify([
            {
                "id": s.id,
                "name": s.name,
                "location": s.location,
                "created": s.timestamp_created.isoformat() if s.timestamp_created else None,
                "updated": s.timestamp_updated.isoformat() if s.timestamp_updated else None
            }
            for s in sites
        ])

    except Exception as e:
        print("❌ /api/sites ERROR:", e)
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500


@sites_bp.route('/<int:site_id>', methods=['PUT', 'DELETE'])
@jwt_required()
def modify_site(site_id):
    try:
        user_id = get_jwt_identity()
        current_user = Users.query.get(user_id)

        if not current_user:
            return jsonify({"message": "User not found"}), 404
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

    except Exception as e:
        print("❌ /api/sites/<id> ERROR:", e)
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
