# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Users(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    title = db.Column(db.String(100))

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
    end_date = db.Column(db.Date, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    timestamp_created = db.Column(db.DateTime, default=datetime.utcnow)
    timestamp_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_randomized = db.Column(db.Boolean, default=False)
    randomization_type = db.Column(db.String(50))  # 'block', 'simple', etc.
    block_size = db.Column(db.Integer)
    stratification_factors = db.Column(db.Text)  # JSON string
    treatment_arms = db.relationship('TreatmentArm', backref='study', cascade="all, delete", lazy=True)
    # ➕ Relationship to StudySite
    study_sites = db.relationship('StudySite', backref='study', lazy='joined')
    users = db.relationship(
        'Users',
        secondary='study_users',
        primaryjoin='Study.id == StudyUser.study_id',
        secondaryjoin='Users.id == StudyUser.user_id',
        backref='assigned_studies',
        foreign_keys='[StudyUser.study_id, StudyUser.user_id]'
    )

class StudySite(db.Model):
    __tablename__ = 'study_site'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp_created = db.Column(db.DateTime, default=datetime.utcnow)
    timestamp_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ➕ Relationship to Site
    site = db.relationship('Site', backref='study_sites')

# (include Patient, Site, Study, etc. if needed)

class StudyUser(db.Model):
    __tablename__ = 'study_users'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp_created = db.Column(db.DateTime, default=datetime.utcnow)

class TreatmentArm(db.Model):
    __tablename__ = 'treatment_arm'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    allocation_ratio = db.Column(db.Integer, default=1)
    timestamp_created = db.Column(db.DateTime, default=datetime.utcnow)

