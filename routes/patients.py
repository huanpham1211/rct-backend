from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Patient, PatientVariable
from datetime import datetime

patients_bp = Blueprint("patients", __name__, url_prefix="/api/patients")

@patients_bp.route("", methods=["POST"])
@jwt_required()
def create_patient():
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        now = datetime.utcnow()

        # ✅ Create patient (basic info)
        patient = Patient(
            name=data.get("name"),
            dob=data.get("dob"),
            sex=data.get("sex"),
            para=data.get("para"),
            phone=data.get("phone"),
            email=data.get("email"),
            ethnicity=data.get("ethnicity"),
            pregnancy_status=data.get("pregnancy_status"),
            notes=data.get("notes"),
            consent_date=data.get("consent_date"),
            enrollment_status=data.get("enrollment_status"),
            is_active=data.get("is_active", True),
            study_id=data.get("study_id"),
            site_id=data.get("site_id"),
            entered_by=user_id,
            updated_by=user_id,
            timestamp_created=now,
            timestamp_updated=now
        )
        db.session.add(patient)
        db.session.flush()  # Important: get patient.id now without committing yet

        # ✅ Insert study variables
        study_vars = data.get("study_variables", [])  # list of dicts

        for var in study_vars:
            variable_id = var.get("variable_id")
            value = var.get("value")

            # 🔥 Check if multiselect
            if isinstance(value, list):
                for v in value:
                    patient_var = PatientVariable(
                        patient_id=patient.id,
                        variable_id=variable_id,
                        value=v,
                        created_by=user_id,
                        updated_by=user_id,
                        timestamp_created=now,
                        timestamp_updated=now
                    )
                    db.session.add(patient_var)
            else:
                # Single value
                patient_var = PatientVariable(
                    patient_id=patient.id,
                    variable_id=variable_id,
                    value=value,
                    created_by=user_id,
                    updated_by=user_id,
                    timestamp_created=now,
                    timestamp_updated=now
                )
                db.session.add(patient_var)

        db.session.commit()
        return jsonify({"message": "✅ Patient and variables saved"}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@patients_bp.route("/<int:patient_id>", methods=["GET"])
@jwt_required()
def get_patient(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)

        # Core patient info
        patient_data = {
            "id": patient.id,
            "name": patient.name,
            "dob": patient.dob.isoformat() if patient.dob else None,
            "sex": patient.sex,
            "para": patient.para,
            "phone": patient.phone,
            "email": patient.email,
            "ethnicity": patient.ethnicity,
            "pregnancy_status": patient.pregnancy_status,
            "notes": patient.notes,
            "consent_date": patient.consent_date.isoformat() if patient.consent_date else None,
            "enrollment_status": patient.enrollment_status,
            "is_active": patient.is_active,
            "study_id": patient.study_id,
            "site_id": patient.site_id,
        }

        # Study variables
        variable_data = []
        for pv in patient.patient_variables:
            variable_data.append({
                "variable_id": pv.variable_id,
                "variable_name": pv.study_variable.name,
                "variable_description": pv.study_variable.description,
                "value": pv.value,
                "type": pv.study_variable.variable_type,
                "required": pv.study_variable.required
            })

        return jsonify({
            "patient": patient_data,
            "variables": variable_data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
