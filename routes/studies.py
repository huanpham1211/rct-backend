from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Study, StudySite, Users
from datetime import datetime

studies_bp = Blueprint("studies", __name__, url_prefix="/api/studies")

@studies_bp.route('', methods=['GET', 'POST'])
@jwt_required()
def handle_studies():
    user_id = get_jwt_identity()
    current_user = Users.query.get(user_id)

    if request.method == 'POST':
        if current_user.role not in ['admin', 'studymanager']:
            return jsonify({"message": "Permission denied"}), 403
        try:
            data = request.get_json()
            new_study = Study(
                name=data['name'],
                protocol_number=data.get('protocol_number'),
                irb_number=data.get('irb_number'),
                start_date=data.get('start_date'),
                end_date=data.get('end_date'),
                created_by=user_id,
                timestamp_created=datetime.utcnow(),
                timestamp_updated=datetime.utcnow()
            )
            db.session.add(new_study)
            db.session.commit()
            return jsonify({"message": "Study created"}), 201
        except Exception as e:
            return jsonify({"message": "Error creating study", "error": str(e)}), 500

    try:
        search = request.args.get('search', '', type=str)
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)

        query = Study.query

        if current_user.role == 'studymanager':
            query = query.filter(Study.created_by == user_id)

        if search:
            query = query.filter(Study.name.ilike(f"%{search}%"))

        studies = query.order_by(Study.timestamp_created.desc()).paginate(page=page, per_page=limit, error_out=False)

        result = []
        for s in studies.items:
            result.append({
                "id": s.id,
                "name": s.name,
                "protocol_number": s.protocol_number,
                "irb_number": s.irb_number,
                "start_date": s.start_date.isoformat() if s.start_date else None,
                "end_date": s.end_date.isoformat() if s.end_date else None,
                "created_by": s.created_by,
                "updated_by": s.updated_by
            })

        return jsonify({
            "studies": result,
            "total": studies.total,
            "pages": studies.pages,
            "page": studies.page
        }), 200
    except Exception as e:
        return jsonify({"message": "Error retrieving studies", "error": str(e)}), 500


@studies_bp.route('/<int:study_id>', methods=['PUT'])
@jwt_required()
def update_study(study_id):
    user_id = get_jwt_identity()
    current_user = Users.query.get(user_id)

    study = Study.query.get(study_id)
    if not study:
        return jsonify({"message": "Study not found"}), 404

    if current_user.role != 'admin' and study.created_by != user_id:
        return jsonify({"message": "Access denied"}), 403

    try:
        data = request.get_json()
        study.name = data.get('name', study.name)
        study.protocol_number = data.get('protocol_number', study.protocol_number)
        study.irb_number = data.get('irb_number', study.irb_number)
        study.start_date = data.get('start_date', study.start_date)
        study.end_date = data.get('end_date', study.end_date)
        study.timestamp_updated = datetime.utcnow()
        study.updated_by = user_id

        db.session.commit()
        return jsonify({"message": "Study updated"}), 200
    except Exception as e:
        return jsonify({"message": "Update failed", "error": str(e)}), 500


@studies_bp.route('/assign', methods=['POST'])
@jwt_required()
def assign_study_site():
    user_id = get_jwt_identity()
    current_user = Users.query.get(user_id)
    data = request.get_json()

    study = Study.query.get(data['study_id'])
    if not study:
        return jsonify({"message": "Study not found"}), 404

    if current_user.role != 'admin' and study.created_by != user_id:
        return jsonify({"message": "Access denied"}), 403

    # Check for duplicate
    existing = StudySite.query.filter_by(study_id=data['study_id'], site_id=data['site_id']).first()
    if existing:
        return jsonify({"message": "Site already assigned"}), 400

    assignment = StudySite(
        study_id=data['study_id'],
        site_id=data['site_id'],
        created_by=user_id,
        timestamp_created=datetime.utcnow(),
        timestamp_updated=datetime.utcnow()
    )
    db.session.add(assignment)
    db.session.commit()
    return jsonify({"message": "Site assigned to study"}), 201
