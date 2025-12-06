from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models to make them available to the package
from .user import User
from .prediction import Prediction
from .company_profile import CompanyProfile