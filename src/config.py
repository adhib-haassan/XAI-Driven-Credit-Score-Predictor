import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///credit_predictor.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Admin credentials
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin123'
    
    # Risk categories
    HIGH_RISK_MAX = 600
    MEDIUM_RISK_MAX = 750
    LOW_RISK_MAX = 900
    
    # File upload settings
    UPLOAD_FOLDER = 'uploads'
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB