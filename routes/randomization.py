# routes/randomization.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Study, TreatmentArm, Randomization
from datetime import datetime
import random, json

randomization_bp = Blueprint("randomization", __name__, url_prefix="/api")

@randomization_bp.route('/randomize', methods=['POST'])
@jwt_required()
def randomize_patient():
    try:
        data = request.get_json()
        user_id = get_jwt_identity()

        study_id = data['study_id']
        patient_id = data['patient_id']
        site_id = data.get('site_id')
        stratification_values = data.get('stratification_values', {})

        study = Study.query.get(study_id)
        if not study or not study.is_randomized:
            return jsonify({"message": "Study not found or not randomized"}), 400

        arms = TreatmentArm.query.filter_by(study_id=study_id).all()
        if not arms:
            return jsonify({"message": "No treatment arms defined"}), 400

        # --- RANDOMIZATION STRATEGIES ---
        selected_arm = None

        if study.randomization_type == 'simple':
            # Simple randomization (equal probability)
            selected_arm = random.choice(arms)

        elif study.randomization_type == 'block':
            # Block randomization using allocation ratios
            weighted_arms = []
            for arm in arms:
                weighted_arms.extend([arm] * arm.allocation_ratio)
            random.shuffle(weighted_arms)
            # Optional: future enhancement to manage block state
            selected_arm = weighted_arms[0]

        elif study.randomization_type == 'stratified':
            # Placeholder: stratified randomization based on values
            # Future: Group patients by stratification variables
            weighted_arms = []
            for arm in arms:
                weighted_arms.extend([arm] * arm.allocation_ratio)
            selected_arm = random.choice(weighted_arms)

        elif study.randomization_type == 'cluster':
            # Cluster randomization by site_id
            if not site_id:
                return jsonify({"message": "Site ID required for cluster randomization"}), 400
            assigned_arm = Randomization.query.filter_by(site_id=site_id).first()
            if assigned_arm:
                selected_arm_name = assigned_arm.treatment_arm
                selected_arm = next((a for a in arms if a.name == selected_arm_name), None)
            else:
                selected_arm = random.choice(arms)

        else:
            return jsonify({"message": f"Unsupported randomization type: {study.randomization_type}"}), 400

        if not selected_arm:
            return jsonify({"message": "Unable to assign treatment arm"}), 500

        # Save result
        new_randomization = Randomization(
            patient_id=patient_id,
            treatment_arm=selected_arm.name,
            randomization_date=datetime.utcnow(),
            stratification_factors=json.dumps(stratification_values),
            entered_by=user_id,
            site_id=site_id
        )
        db.session.add(new_randomization)
        db.session.commit()

        return jsonify({
            "assigned_arm": selected_arm.name,
            "treatment_arm_id": selected_arm.id
        }), 201

    except Exception as e:
        import traceback
        print("🔥 Randomization Error:\n", traceback.format_exc())
        return jsonify({"error": str(e)}), 500
