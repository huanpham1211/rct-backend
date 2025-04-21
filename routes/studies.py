from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Study, StudySite, Users, StudyUser 
from datetime import datetime
from dateutil.parser import parse
from datetime import date

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
            end_date_str = data.get('end_date')
            end_date = parse(end_date_str).date() if end_date_str else None
            start_date_str = data.get('start_date')
            start_date = parse(start_date_str).date() if start_date_str else None

            new_study = Study(
                name=data['name'],
                protocol_number=data.get('protocol_number'),
                irb_number=data.get('irb_number'),
                start_date=start_date,
                end_date=end_date,
                created_by=user_id,
                timestamp_created=datetime.utcnow(),
                timestamp_updated=datetime.utcnow()
            )
            db.session.add(new_study)
            db.session.commit()
            return jsonify({"message": "Study created"}), 201
        except Exception as e:
            return jsonify({"message": "Error creating study", "error": str(e)}), 500

    # GET request logic
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
                "updated_by": s.updated_by,
                "is_randomized": s.is_randomized,
                "randomization_type": s.randomization_type,
                "block_size": s.block_size,
                "stratification_factors": s.stratification_factors,
                "sites": [
                    {
                        "id": ss.site.id,
                        "name": ss.site.name,
                        "location": ss.site.location
                    } for ss in s.study_sites
                ],
                "users": [
                    {
                        "id": u.id,
                        "username": u.username,
                        "first_name": u.first_name,
                        "last_name": u.last_name,
                        "title": u.title,
                        "role": u.role
                    } for u in s.users
                ]
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
        end_date_str = data.get('end_date')
        start_date_str = data.get('start_date')

        study.name = data.get('name', study.name)
        study.protocol_number = data.get('protocol_number', study.protocol_number)
        study.irb_number = data.get('irb_number', study.irb_number)
        study.start_date = parse(start_date_str).date() if start_date_str else study.start_date
        study.end_date = parse(end_date_str).date() if end_date_str else None
        study.timestamp_updated = datetime.utcnow()
        study.updated_by = user_id
       # ✅ Handle RCT fields
        study.is_randomized = data.get('is_randomized', study.is_randomized)
        study.randomization_type = data.get('randomization_type', study.randomization_type)
        study.block_size = data.get('block_size', study.block_size)
        study.stratification_factors = data.get('stratification_factors', study.stratification_factors)
        
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

@studies_bp.route('/unassign', methods=['POST'])
@jwt_required()
def unassign_study_site():
    user_id = get_jwt_identity()
    current_user = Users.query.get(user_id)
    data = request.get_json()

    study = Study.query.get(data['study_id'])
    if not study:
        return jsonify({"message": "Study not found"}), 404

    if current_user.role != 'admin' and study.created_by != user_id:
        return jsonify({"message": "Access denied"}), 403

    study_site = StudySite.query.filter_by(study_id=data['study_id'], site_id=data['site_id']).first()
    if not study_site:
        return jsonify({"message": "Site not assigned to study"}), 404

    db.session.delete(study_site)
    db.session.commit()

    return jsonify({"message": "Site unassigned from study"}), 200

@studies_bp.route('/assign-user', methods=['POST'])
@jwt_required()
def assign_user_to_study():
    data = request.get_json()
    user_id = get_jwt_identity()
    study_id = data.get('study_id')
    target_user_id = data.get('user_id')

    existing = StudyUser.query.filter_by(study_id=study_id, user_id=target_user_id).first()
    if existing:
        return jsonify({"message": "User already assigned"}), 400

    link = StudyUser(
        study_id=study_id,
        user_id=target_user_id,
        created_by=user_id
    )
    db.session.add(link)
    db.session.commit()
    return jsonify({"message": "User assigned to study"}), 201

@studies_bp.route('/unassign-user', methods=['POST'])
@jwt_required()
def unassign_user_from_study():
    data = request.get_json()
    study_id = data.get('study_id')
    target_user_id = data.get('user_id')

    link = StudyUser.query.filter_by(study_id=study_id, user_id=target_user_id).first()
    if not link:
        return jsonify({"error": "User is not assigned to this study"}), 404

    db.session.delete(link)
    db.session.commit()
    return jsonify({"message": "User unassigned from study"}), 200

@studies_bp.route('/assigned-studies', methods=['GET'])
@jwt_required()
def get_assigned_studies():
    try:
        from datetime import date
        today = date.today()

        user_id = get_jwt_identity()
        user = Users.query.get(user_id)

        if user.role == 'admin':
            query = Study.query
        else:
            query = Study.query.join(StudyUser).filter(StudyUser.user_id == user_id)

        query = query.filter((Study.end_date == None) | (Study.end_date >= today))

        studies = query.all()

        results = []
        for s in studies:
            results.append({
                "id": s.id,
                "name": s.name,
                "protocol_number": s.protocol_number,
                "end_date": s.end_date.isoformat() if s.end_date else None,
                "sites": [
                    {
                        "id": ss.site.id,
                        "name": ss.site.name
                    }
                    for ss in s.study_sites
                ]
            })

        return jsonify(results), 200
    except Exception as e:
        import traceback
        print("🔥 Error in /assigned-studies:\n", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@studies_bp.route('/<int:study_id>/arms', methods=['POST'])
@jwt_required()
def add_treatment_arm(study_id):
    data = request.get_json()
    arm = TreatmentArm(
        study_id=study_id,
        name=data['name'],
        description=data.get('description'),
        allocation_ratio=data.get('allocation_ratio', 1)
    )
    db.session.add(arm)
    db.session.commit()
    return jsonify({"message": "Treatment arm added"}), 201

