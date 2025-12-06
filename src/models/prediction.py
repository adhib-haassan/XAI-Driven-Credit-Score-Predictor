from . import db
from datetime import datetime, timezone

def utc_now():
    """Helper function to get current UTC datetime"""
    return datetime.now(timezone.utc)

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credit_score = db.Column(db.Integer, nullable=False)
    risk_category = db.Column(db.String(50), nullable=False)
    prediction_date = db.Column(db.DateTime, default=utc_now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Made nullable for backward compatibility
    
    # Link to CompanyProfile (the actual company being predicted)
    company_profile_id = db.Column(db.Integer, db.ForeignKey('company_profile.id'), nullable=True)
    
    # Store extracted company name from PDF
    extracted_company_name = db.Column(db.String(100), nullable=True)
    
    # Store input features for explanation
    input_features = db.Column(db.Text)  # JSON string of input features
    
    def __repr__(self):
        return f"Prediction('{self.credit_score}', '{self.risk_category}', '{self.prediction_date}', Company: '{self.extracted_company_name}')"