from . import db
from datetime import datetime, timezone

def utc_now():
    """Helper function to get current UTC datetime"""
    return datetime.now(timezone.utc)

class CompanyProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Identity fields
    extracted_company_name = db.Column(db.String(100), nullable=True)  # Company name extracted from PDF
    owner_name = db.Column(db.String(100), nullable=True)

    # Financial parameters
    monthly_inflow = db.Column(db.Float, nullable=True)
    monthly_outflow = db.Column(db.Float, nullable=True)
    gst_compliance_score = db.Column(db.Float, nullable=True)
    ecommerce_sales = db.Column(db.Float, nullable=True)
    supplier_payments = db.Column(db.Float, nullable=True)
    invoice_issued = db.Column(db.Integer, nullable=True)
    invoice_amount = db.Column(db.Float, nullable=True)
    employee_count = db.Column(db.Integer, nullable=True)
    asset_value = db.Column(db.Float, nullable=True)
    business_age = db.Column(db.Float, nullable=True)
    business_size = db.Column(db.String(50), nullable=True)

    # Metadata
    document_path = db.Column(db.String(500), nullable=True)
    extraction_status = db.Column(db.String(50), default="pending")
    extraction_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = db.relationship('User', backref='company_profiles', lazy=True)
    predictions = db.relationship('Prediction', backref='company_profile', lazy=True)

    def to_dict(self):
        """Return all fields as a dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'extracted_company_name': self.extracted_company_name,
            'owner_name': self.owner_name,
            'monthly_inflow': self.monthly_inflow,
            'monthly_outflow': self.monthly_outflow,
            'gst_compliance_score': self.gst_compliance_score,
            'ecommerce_sales': self.ecommerce_sales,
            'supplier_payments': self.supplier_payments,
            'invoice_issued': self.invoice_issued,
            'invoice_amount': self.invoice_amount,
            'employee_count': self.employee_count,
            'asset_value': self.asset_value,
            'business_age': self.business_age,
            'business_size': self.business_size,
            'document_path': self.document_path,
            'extraction_status': self.extraction_status,
            'extraction_date': self.extraction_date.isoformat() if self.extraction_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"CompanyProfile('{self.owner_name}', User ID: {self.user_id}, Status: {self.extraction_status})"
