from . import db
from flask_login import UserMixin
from datetime import datetime, timezone

def utc_now():
    """Helper function to get current UTC datetime"""
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    company_type = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    
    predictions = db.relationship('Prediction', backref='user', lazy=True)
    
    def __repr__(self):
        return f"User('{self.company_name}', '{self.email}', '{self.company_type}')"