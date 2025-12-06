# app.py (patched with SHAP explainability)
import os
import json
import pandas as pd
import joblib
import numpy as np
import shap     # for SHAP explainability
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to avoid GUI issues
from matplotlib import pyplot as plt

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import db, User, Prediction, CompanyProfile
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
from functools import wraps
from werkzeug.utils import secure_filename
from utils.pdf_extractor import extract_from_pdf
from utils.diff_checker import compare_profiles

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- Load ML models ---
model_path = os.path.join(os.path.dirname(__file__), 'ml_models', 'best_cibil_model1.pkl')
encoder_path = os.path.join(os.path.dirname(__file__), 'ml_models', 'encoder1.pkl')

try:
    model = joblib.load(model_path)
    encoder = joblib.load(encoder_path)
    app.logger.info("Models loaded successfully.")
except Exception as e:
    app.logger.exception(f"Error loading ML models: {e}")
    model = None
    encoder = None

# Create static shap folder if not exists
SHAP_STATIC_DIR = os.path.join(app.static_folder, "shap")
os.makedirs(SHAP_STATIC_DIR, exist_ok=True)

# Create uploads directory if not exists
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), Config.UPLOAD_FOLDER)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Helper utilities for SHAP ---
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def get_shap_background(n_sample=200):
    """
    Attempt to get a background sample for SHAP explainer.
    Checks common dataset filenames in project root.
    Returns a DataFrame of inputs (no target) or None.
    """
    candidate_paths = [
        os.path.join(os.path.dirname(__file__), "cibil_synthetic_10000_balanced_v2.csv"),
        os.path.join(os.path.dirname(__file__), "cibil_synthetic_10000_balanced.csv"),
        os.path.join(os.path.dirname(__file__), "cibil_synthetic_5000_highcorr.csv"),
        os.path.join(os.path.dirname(__file__), "cibil_data1.csv"),
        os.path.join(os.path.dirname(__file__), "data.csv")
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            try:
                bg = pd.read_csv(p)
                # drop target if exists
                for col in ["credit_score", "Credit_score", "risk_category", "Risk category"]:
                    if col in bg.columns:
                        bg = bg.drop(columns=[col])
                # Keep columns that the model expects if possible (best-effort)
                bg = bg.reset_index(drop=True)
                return bg.sample(n=min(n_sample, len(bg)), random_state=42).reset_index(drop=True)
            except Exception as e:
                app.logger.warning("Failed to load background from %s: %s", p, e)
    return None

# --- Build SHAP explainer once (on app start) ---
explainer = None
shap_background_df = None
try:
    if model is not None:
        shap_background_df = get_shap_background()
        # If background contains 'Business_size' as strings, try to encode with the saved encoder
        if shap_background_df is not None and "business_size" in shap_background_df.columns:
            try:
                # encoder may be sklearn LabelEncoder saved as 'encoder'
                shap_background_df["business_size"] = encoder.transform(shap_background_df["business_size"])
            except Exception as e:
                # if encoding fails, drop that column from background (explainer still okay)
                app.logger.warning("Could not encode business_size in SHAP background: %s. Dropping column.", e)
                shap_background_df = shap_background_df.drop(columns=["business_size"], errors='ignore')

        # For tree based models prefer TreeExplainer with background
        try:
            if shap_background_df is not None:
                explainer = shap.TreeExplainer(model, data=shap_background_df)
            else:
                explainer = shap.TreeExplainer(model)
            app.logger.info("SHAP TreeExplainer created.")
        except Exception as e:
            app.logger.warning("TreeExplainer failed, trying generic Explainer: %s", e)
            try:
                if shap_background_df is not None:
                    explainer = shap.Explainer(model, shap_background_df)
                else:
                    explainer = shap.Explainer(model)
                app.logger.info("SHAP Explainer created.")
            except Exception as e2:
                app.logger.exception("Failed to create SHAP explainer: %s", e2)
                explainer = None
except Exception as e:
    app.logger.exception("Unexpected error creating SHAP explainer: %s", e)
    explainer = None

# --- Flask/Login setup ---
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create tables and run migrations
def run_migrations():
    """Add new columns to existing tables if they don't exist"""
    with app.app_context():
        db.create_all()  # Create all tables first
        
        # Check and add new columns to existing tables
        from sqlalchemy import inspect, text
        
        inspector = inspect(db.engine)
        
        # Check Prediction table
        if 'prediction' in [t.lower() for t in inspector.get_table_names()]:
            pred_columns = [col['name'].lower() for col in inspector.get_columns('prediction')]
            
            # Add company_profile_id if it doesn't exist
            if 'company_profile_id' not in pred_columns:
                try:
                    db.session.execute(text('ALTER TABLE prediction ADD COLUMN company_profile_id INTEGER'))
                    db.session.commit()
                    app.logger.info("Added company_profile_id column to prediction table")
                except Exception as e:
                    app.logger.warning(f"Could not add company_profile_id: {e}")
                    db.session.rollback()
            
            # Add extracted_company_name if it doesn't exist
            if 'extracted_company_name' not in pred_columns:
                try:
                    db.session.execute(text('ALTER TABLE prediction ADD COLUMN extracted_company_name VARCHAR(100)'))
                    db.session.commit()
                    app.logger.info("Added extracted_company_name column to prediction table")
                except Exception as e:
                    app.logger.warning(f"Could not add extracted_company_name: {e}")
                    db.session.rollback()
            
            # Make user_id nullable if it's not already
            # SQLite doesn't support modifying column constraints easily, so we'll skip this
            # The model already has nullable=True, so new records will work
        
        # Check CompanyProfile table
        if 'company_profile' in [t.lower() for t in inspector.get_table_names()]:
            cp_columns = [col['name'].lower() for col in inspector.get_columns('company_profile')]
            
            # Add extracted_company_name if it doesn't exist
            if 'extracted_company_name' not in cp_columns:
                try:
                    db.session.execute(text('ALTER TABLE company_profile ADD COLUMN extracted_company_name VARCHAR(100)'))
                    db.session.commit()
                    app.logger.info("Added extracted_company_name column to company_profile table")
                except Exception as e:
                    app.logger.warning(f"Could not add extracted_company_name to company_profile: {e}")
                    db.session.rollback()

with app.app_context():
    run_migrations()

# Admin decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('You need to be logged in as an admin to access this page.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes (original app logic retained) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated or session.get('admin_logged_in'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        email = request.form.get('email')
        company_type = request.form.get('company_type')
        country = request.form.get('country')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists. Please use a different email.', 'danger')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(company_name=company_name, email=email, company_type=company_type, country=country, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated or session.get('admin_logged_in'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')

@app.route('/predict', methods=['GET'])
@login_required
def predict():
    return render_template('predict.html')

@app.route('/prediction_result/<int:prediction_id>')
@login_required
def prediction_result(prediction_id):
    prediction = Prediction.query.options(joinedload(Prediction.company_profile)).get_or_404(prediction_id)

    # Ownership/admin check
    if not (current_user.is_authenticated and prediction.user_id == current_user.id) and not session.get('admin_logged_in'):
        flash('You do not have permission to view this prediction.', 'danger')
        return redirect(url_for('dashboard'))

    # Load input features
    input_features = json.loads(prediction.input_features)

    # Prepare DataFrame for explainer matching training columns
    input_df = pd.DataFrame([input_features])

    # Encode business_size same as training
    try:
        input_df["Business_size"] = encoder.transform(input_df["Business_size"])
    except Exception as e:
        app.logger.warning("Business_size encoding for SHAP/prediction_result failed: %s", e)
        # try numeric fallback
        try:
            input_df["Business_size"] = input_df["Business_size"].astype(int)
        except Exception:
            # If still failing, leave as-is; model may handle it if it's already encoded
            pass

    shap_image = None   # relative path under static, e.g., 'shap/pred_123_waterfall.png'
    shap_html = None    # relative path under static, e.g., 'shap/pred_123_force.html'

    # Generate SHAP explanations (non-blocking - errors are handled)
    if explainer is not None:
        try:
            # Ensure input_df columns order matches explainer expectations (best-effort)
            # If explainer has feature_names, reorder input_df accordingly
            try:
                feature_names = explainer.feature_names if hasattr(explainer, "feature_names") else None
                if feature_names is not None:
                    # If feature names mismatch or extra columns, try to select common subset
                    common = [c for c in feature_names if c in input_df.columns]
                    if len(common) > 0:
                        ordered_df = input_df[common]
                    else:
                        ordered_df = input_df
                else:
                    ordered_df = input_df
            except Exception:
                ordered_df = input_df

            # Compute SHAP values (returns Explanation object in modern SHAP)
            shap_result = explainer(ordered_df)

            # File names and paths (relative to static)
            pred_prefix = f"pred_{prediction_id}"
            png_filename = f"{pred_prefix}_waterfall.png"
            html_filename = f"{pred_prefix}_force.html"
            png_fullpath = os.path.join(SHAP_STATIC_DIR, png_filename)
            html_fullpath = os.path.join(SHAP_STATIC_DIR, html_filename)

            # Waterfall plot (PNG)
            try:
                plt.clf()
                # shap.plots.waterfall expects a single explanation element for single sample
                shap.plots.waterfall(shap_result[0], show=False)
                plt.savefig(png_fullpath, bbox_inches="tight", dpi=150)
                plt.close()
                shap_image = f"shap/{png_filename}"
            except Exception as e:
                app.logger.warning("SHAP waterfall plot failed: %s", e)
                # fallback bar of absolute shap values
                try:
                    vals = shap_result.values[0]
                    names = shap_result.feature_names if hasattr(shap_result, "feature_names") else ordered_df.columns
                    abs_vals = np.abs(vals)
                    sorted_idx = np.argsort(abs_vals)[::-1][:10]
                    top_names = np.array(names)[sorted_idx]
                    top_vals = abs_vals[sorted_idx]
                    fig, ax = plt.subplots(figsize=(8,5))
                    ax.barh(top_names[::-1], top_vals[::-1])
                    ax.set_xlabel("Absolute SHAP value")
                    fig.savefig(png_fullpath, bbox_inches="tight", dpi=150)
                    plt.close(fig)
                    shap_image = f"shap/{png_filename}"
                except Exception as e2:
                    app.logger.warning("Fallback SHAP bar plot failed: %s", e2)
                    shap_image = None

            # Force plot (interactive HTML)
            try:
                # shap.plots.force returns a JS-enabled plot object; save to HTML
                # Newer SHAP exposes shap.save_html to write output
                force_obj = shap.plots.force(shap_result[0], matplotlib=False, show=False)
                shap.save_html(html_fullpath, force_obj)
                shap_html = f"shap/{html_filename}"
            except Exception as e:
                app.logger.warning("Saving SHAP force plot failed: %s", e)
                # Attempt alternate force_plot creation if above failed
                try:
                    # older API fallback
                    fp = shap.force_plot(explainer.expected_value, shap_result.values[0], ordered_df.iloc[0], matplotlib=False)
                    shap.save_html(html_fullpath, fp)
                    shap_html = f"shap/{html_filename}"
                except Exception as e2:
                    app.logger.warning("Alternate SHAP force_plot save also failed: %s", e2)
                    shap_html = None

        except Exception as e:
            app.logger.exception("Error computing SHAP for prediction %s: %s", prediction_id, e)
            shap_image = None
            shap_html = None
    else:
        app.logger.info("SHAP explainer not available; skipping SHAP generation.")

    # Textual risk guidance (unchanged)
    risk_explanation = ""
    score_explanation = ""
    recommendations = ""

    if prediction.risk_category == "High Risk":
        risk_explanation = "Your company is classified as high risk, which means there's a significant chance of defaulting on financial obligations. Lenders may be hesitant to extend credit or may offer less favorable terms."
        score_explanation = "Your credit score is below 600, which is considered poor. This indicates potential issues with credit management, financial stability, or payment history."
        recommendations = "To improve your credit score: 1) Pay all bills on time, 2) Reduce outstanding debt, 3) Avoid new credit applications, 4) Maintain a positive cash flow, 5) Resolve any legal issues, 6) Improve financial ratios like current ratio and quick ratio."
    elif prediction.risk_category == "Medium Risk":
        risk_explanation = "Your company is classified as medium risk, indicating a moderate chance of default. Lenders may extend credit but with caution and possibly higher interest rates."
        score_explanation = "Your credit score is between 601 and 750, which is considered average. This suggests some strengths in your financial profile but also areas for improvement."
        recommendations = "To improve your credit score: 1) Continue making timely payments, 2) Gradually reduce debt levels, 3) Increase revenue and profitability, 4) Maintain a healthy cash flow, 5) Limit new credit applications, 6) Improve financial ratios."
    else:
        risk_explanation = "Your company is classified as low risk, indicating a low chance of default. Lenders are likely to offer favorable credit terms."
        score_explanation = "Your credit score is above 750, which is considered excellent. This reflects strong financial management, stability, and a positive payment history."
        recommendations = "To maintain your excellent credit score: 1) Continue making all payments on time, 2) Maintain low debt levels, 3) Keep a healthy cash flow, 4) Avoid excessive new credit applications, 5) Monitor your financial ratios regularly, 6) Continue building a positive credit history."

    return render_template(
        'prediction_result.html',
        prediction=prediction,
        input_features=input_features,
        risk_explanation=risk_explanation,
        score_explanation=score_explanation,
        recommendations=recommendations,
        shap_image=shap_image,   # relative static path like 'shap/pred_1_waterfall.png'
        shap_html=shap_html,     # relative static path like 'shap/pred_1_force.html'
        is_admin=session.get('admin_logged_in')
    )

@app.route('/history')
@login_required
def history():
    predictions = Prediction.query.options(joinedload(Prediction.company_profile)).filter_by(user_id=current_user.id).order_by(Prediction.prediction_date.desc()).all()
    return render_template('history.html', predictions=predictions)

@app.route('/analytics')
@login_required
def analytics():
    predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.prediction_date.asc()).all()
    dates = [p.prediction_date.strftime('%Y-%m-%d') for p in predictions]
    scores = [p.credit_score for p in predictions]
    if scores:
        highest_score = max(scores)
        lowest_score = min(scores)
        average_score = sum(scores) / len(scores)
        latest_score = scores[-1]
    else:
        highest_score = lowest_score = average_score = latest_score = None
    return render_template(
        'analytics.html',
        dates=dates,
        scores=scores,
        highest_score=highest_score,
        lowest_score=lowest_score,
        average_score=average_score,
        latest_score=latest_score
    )

# Admin routes (unchanged)
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated or session.get('admin_logged_in'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    total_companies = User.query.count()
    total_predictions = Prediction.query.count()
    company_types = db.session.query(User.company_type, db.func.count(User.id)).group_by(User.company_type).all()
    countries = db.session.query(User.country, db.func.count(User.id)).group_by(User.country).all()
    risk_categories = db.session.query(Prediction.risk_category, db.func.count(Prediction.id)).group_by(Prediction.risk_category).all()
    users = User.query.all()
    high_risk_companies = 0
    low_risk_companies = 0
    for user in users:
        latest_prediction = Prediction.query.filter_by(user_id=user.id).order_by(Prediction.prediction_date.desc()).first()
        if latest_prediction:
            if latest_prediction.risk_category == 'High Risk':
                high_risk_companies += 1
            elif latest_prediction.risk_category == 'Low Risk':
                low_risk_companies += 1
    return render_template(
        'admin_dashboard.html',
        total_companies=total_companies,
        total_predictions=total_predictions,
        company_types=company_types,
        countries=countries,
        risk_categories=risk_categories,
        high_risk_companies=high_risk_companies,
        low_risk_companies=low_risk_companies
    )

@app.route('/admin/companies')
@admin_required
def admin_companies():
    companies = User.query.all()
    return render_template('admin_companies.html', companies=companies)

@app.route('/admin/predictions/<int:user_id>')
@admin_required
def admin_predictions(user_id):
    user = User.query.get_or_404(user_id)
    predictions = Prediction.query.filter_by(user_id=user_id).order_by(Prediction.prediction_date.desc()).all()
    return render_template('admin_company_predictions.html', user=user, predictions=predictions)

@app.route('/api/analytics/<int:user_id>')
@login_required
def analytics_data(user_id):
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    predictions = Prediction.query.filter_by(user_id=user_id).order_by(Prediction.prediction_date.asc()).all()
    data = {
        'dates': [p.prediction_date.strftime('%Y-%m-%d') for p in predictions],
        'scores': [p.credit_score for p in predictions]
    }
    return jsonify(data)

# --- New routes for PDF upload and auto-fill ---

@app.route('/upload_pdf', methods=['POST'])
@login_required
def upload_pdf():
    """Handle PDF upload, extract fields, create/update User and CompanyProfile"""
    if 'pdf_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
    
    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'status': 'error', 'message': 'File must be a PDF'}), 400
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > Config.MAX_UPLOAD_SIZE:
        return jsonify({'status': 'error', 'message': 'File too large'}), 400
    
    try:
        # Save file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(file.filename)
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        file.save(filepath)
        
        # Extract fields from PDF
        extracted = extract_from_pdf(filepath)
        if not extracted:
            return jsonify({'status': 'error', 'message': 'Failed to extract data from PDF'}), 400
        
        # Get or create User - use current_user if logged in, otherwise create/find by email
        # Don't update User.company_name - keep User as registered account
        extracted_company_name = extracted.get('company_name') or 'Unknown Company'
        
        if current_user.is_authenticated:
            user = current_user
        else:
            # Try to find user by email first, or create new user
            email = extracted.get('email') or f"{extracted_company_name.lower().replace(' ', '_')}@temp.com"
            user = User.query.filter_by(email=email).first()
            
            if not user:
                # Create new user with a generic company name (registered account)
                company_type = extracted.get('company_type') or 'Unknown'
                country = extracted.get('country') or 'Unknown'
                # Generate temporary password (user will need to set proper password later)
                temp_password = generate_password_hash(f"temp_{timestamp}", method='pbkdf2:sha256')
                user = User(
                    company_name=f"User_{timestamp}",  # Generic name for registered account
                    email=email,
                    company_type=company_type,
                    country=country,
                    password=temp_password
                )
                db.session.add(user)
                db.session.flush()  # Get user.id
        
        # Create CompanyProfile with extracted company name
        company_profile = CompanyProfile(
            user_id=user.id,
            extracted_company_name=extracted_company_name,
            owner_name=extracted.get('owner_name'),
            monthly_inflow=extracted.get('monthly_inflow'),
            monthly_outflow=extracted.get('monthly_outflow'),
            gst_compliance_score=extracted.get('gst_compliance_score'),
            ecommerce_sales=extracted.get('ecommerce_sales'),
            supplier_payments=extracted.get('supplier_payments'),
            invoice_issued=extracted.get('invoice_issued'),
            invoice_amount=extracted.get('invoice_amount'),
            employee_count=extracted.get('employee_count'),
            asset_value=extracted.get('asset_value'),
            business_age=extracted.get('business_age'),
            business_size=extracted.get('business_size'),
            document_path=filepath,
            extraction_status="completed",
            extraction_date=datetime.now(timezone.utc)
        )
        db.session.add(company_profile)
        db.session.commit()
        
        # Prepare response with extracted company name
        identity = {
            'company_name': company_profile.extracted_company_name or extracted_company_name,
            'extracted_company_name': company_profile.extracted_company_name or extracted_company_name,
            'email': user.email,
            'company_type': user.company_type,
            'country': user.country,
            'owner_name': company_profile.owner_name
        }
        
        return jsonify({
            'status': 'success',
            'identity': identity,
            'company_profile': company_profile.to_dict()
        })
        
    except Exception as e:
        app.logger.exception(f"Error processing PDF upload: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/auto_fill_existing', methods=['POST'])
def auto_fill_existing():
    """Search for existing company by extracted_company_name and optionally owner_name across all users"""
    try:
        company_name = request.form.get('company_name', '').strip()
        owner_name = request.form.get('owner_name', '').strip()
        
        if not company_name:
            return jsonify({'status': 'error', 'message': 'Company name is required'}), 400
        
        # Search CompanyProfile directly by extracted_company_name (across all users)
        query = CompanyProfile.query.filter(
            CompanyProfile.extracted_company_name.ilike(f'%{company_name}%')
        )
        
        # If owner_name provided, filter by it
        if owner_name:
            query = query.filter(CompanyProfile.owner_name.ilike(f'%{owner_name}%'))
        
        # Get the latest matching profile
        company_profile = query.order_by(CompanyProfile.created_at.desc()).first()
        
        if not company_profile:
            return jsonify({'status': 'error', 'message': 'Company not found'}), 404
        
        # Get the associated User for context
        user = company_profile.user
        
        # Fetch latest Prediction for this company profile
        last_prediction = Prediction.query.filter_by(
            company_profile_id=company_profile.id
        ).order_by(Prediction.prediction_date.desc()).first()
        
        # If no prediction linked to profile, try to find by user_id for backward compatibility
        if not last_prediction:
            last_prediction = Prediction.query.filter_by(
                user_id=user.id
            ).order_by(Prediction.prediction_date.desc()).first()
        
        identity = {
            'company_name': company_profile.extracted_company_name or company_name,
            'extracted_company_name': company_profile.extracted_company_name or company_name,
            'email': user.email if user else None,
            'company_type': user.company_type if user else None,
            'country': user.country if user else None,
            'owner_name': company_profile.owner_name
        }
        
        response = {
            'status': 'success',
            'identity': identity,
            'company_profile': company_profile.to_dict()
        }
        
        if last_prediction:
            response['last_prediction'] = {
                'id': last_prediction.id,
                'credit_score': last_prediction.credit_score,
                'risk_category': last_prediction.risk_category,
                'prediction_date': last_prediction.prediction_date.isoformat() if last_prediction.prediction_date else None
            }
        else:
            response['last_prediction'] = None
        
        return jsonify(response)
        
    except Exception as e:
        app.logger.exception(f"Error in auto_fill_existing: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/run_prediction', methods=['POST'])
@login_required
def run_prediction():
    """Run prediction without saving to database"""
    if not model or not encoder:
        return jsonify({'status': 'error', 'message': 'ML models are not available'}), 500
    
    try:
        # Get form data
        form_data = {
            "Monthly_Inflow": float(request.form.get('Monthly_Inflow')),
            "Monthly_Outflow": float(request.form.get('Monthly_Outflow')),
            "Gst_compliance_score": float(request.form.get('Gst_compliance_score')),
            "Ecommerce_sales": float(request.form.get('Ecommerce_sales')),
            "Supplier_payments": float(request.form.get('Supplier_payments')),
            "Invoice_issued": int(request.form.get('Invoice_issued')),
            "Invoice_amount": float(request.form.get('Invoice_amount')),
            "Employee_count": int(request.form.get('Employee_count')),
            "Asset_value": float(request.form.get('Asset_value')),
            "Business_age": float(request.form.get('Business_age')),
            "Business_size": request.form.get('Business_size')
        }
        
        # Create DataFrame for prediction
        input_df = pd.DataFrame([form_data])
        
        # Encode categorical variables (Business_size)
        try:
            input_df["Business_size"] = encoder.transform(input_df["Business_size"])
        except Exception as e:
            app.logger.warning("Encoding Business_size failed: %s", e)
            try:
                input_df["Business_size"] = input_df["Business_size"].astype(int)
            except Exception:
                return jsonify({'status': 'error', 'message': 'Business_size encoding failed'}), 400
        
        # Make prediction
        pred_raw = model.predict(input_df)
        credit_score = int(np.round(pred_raw[0]))
        
        # Determine risk category
        if credit_score <= Config.HIGH_RISK_MAX:
            risk_category = "High Risk"
        elif credit_score <= Config.MEDIUM_RISK_MAX:
            risk_category = "Medium Risk"
        else:
            risk_category = "Low Risk"
        
        return jsonify({
            'credit_score': credit_score,
            'risk_category': risk_category,
            'input_features': form_data
        })
        
    except Exception as e:
        app.logger.exception(f"Error in run_prediction: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/save_prediction', methods=['POST'])
@login_required
def save_prediction():
    """Save prediction to database, update CompanyProfile, and check differences if existing company"""
    if not model or not encoder:
        return jsonify({'status': 'error', 'message': 'ML models are not available'}), 500
    
    try:
        mode = request.form.get('mode', 'new_entry')  # 'new_entry' or 'existing_company'
        
        # Get extracted company name and owner name from form
        extracted_company_name = request.form.get('extracted_company_name', '').strip()
        owner_name = request.form.get('owner_name', '').strip()
        
        # Get form data
        form_data = {
            "Monthly_Inflow": float(request.form.get('Monthly_Inflow')),
            "Monthly_Outflow": float(request.form.get('Monthly_Outflow')),
            "Gst_compliance_score": float(request.form.get('Gst_compliance_score')),
            "Ecommerce_sales": float(request.form.get('Ecommerce_sales')),
            "Supplier_payments": float(request.form.get('Supplier_payments')),
            "Invoice_issued": int(request.form.get('Invoice_issued')),
            "Invoice_amount": float(request.form.get('Invoice_amount')),
            "Employee_count": int(request.form.get('Employee_count')),
            "Asset_value": float(request.form.get('Asset_value')),
            "Business_age": float(request.form.get('Business_age')),
            "Business_size": request.form.get('Business_size')
        }
        
        # Create DataFrame for prediction
        input_df = pd.DataFrame([form_data])
        
        # Encode categorical variables (Business_size)
        try:
            input_df["Business_size"] = encoder.transform(input_df["Business_size"])
        except Exception as e:
            app.logger.warning("Encoding Business_size failed: %s", e)
            try:
                input_df["Business_size"] = input_df["Business_size"].astype(int)
            except Exception:
                return jsonify({'status': 'error', 'message': 'Business_size encoding failed'}), 400
        
        # Make prediction
        pred_raw = model.predict(input_df)
        credit_score = int(np.round(pred_raw[0]))
        
        # Determine risk category
        if credit_score <= Config.HIGH_RISK_MAX:
            risk_category = "High Risk"
        elif credit_score <= Config.MEDIUM_RISK_MAX:
            risk_category = "Medium Risk"
        else:
            risk_category = "Low Risk"
        
        # Get or create CompanyProfile with extracted company name
        company_profile = None
        if extracted_company_name or owner_name:
            # Search for existing CompanyProfile by extracted_company_name and owner_name
            query = CompanyProfile.query
            if extracted_company_name:
                query = query.filter(CompanyProfile.extracted_company_name.ilike(f'%{extracted_company_name}%'))
            if owner_name:
                query = query.filter(CompanyProfile.owner_name.ilike(f'%{owner_name}%'))
            
            company_profile = query.order_by(CompanyProfile.created_at.desc()).first()
            
            if not company_profile:
                # Create new CompanyProfile
                company_profile = CompanyProfile(
                    user_id=current_user.id,
                    extracted_company_name=extracted_company_name or None,
                    owner_name=owner_name or None,
                    monthly_inflow=form_data['Monthly_Inflow'],
                    monthly_outflow=form_data['Monthly_Outflow'],
                    gst_compliance_score=form_data['Gst_compliance_score'],
                    ecommerce_sales=form_data['Ecommerce_sales'],
                    supplier_payments=form_data['Supplier_payments'],
                    invoice_issued=form_data['Invoice_issued'],
                    invoice_amount=form_data['Invoice_amount'],
                    employee_count=form_data['Employee_count'],
                    asset_value=form_data['Asset_value'],
                    business_age=form_data['Business_age'],
                    business_size=form_data['Business_size']
                )
                db.session.add(company_profile)
                db.session.flush()  # Get company_profile.id
            else:
                # Update existing profile
                if extracted_company_name:
                    company_profile.extracted_company_name = extracted_company_name
                if owner_name:
                    company_profile.owner_name = owner_name
                company_profile.monthly_inflow = form_data['Monthly_Inflow']
                company_profile.monthly_outflow = form_data['Monthly_Outflow']
                company_profile.gst_compliance_score = form_data['Gst_compliance_score']
                company_profile.ecommerce_sales = form_data['Ecommerce_sales']
                company_profile.supplier_payments = form_data['Supplier_payments']
                company_profile.invoice_issued = form_data['Invoice_issued']
                company_profile.invoice_amount = form_data['Invoice_amount']
                company_profile.employee_count = form_data['Employee_count']
                company_profile.asset_value = form_data['Asset_value']
                company_profile.business_age = form_data['Business_age']
                company_profile.business_size = form_data['Business_size']
                company_profile.updated_at = datetime.now(timezone.utc)
        
        # Check for differences if existing company
        difference_summary = None
        if mode == 'existing_company' and company_profile:
            # Find previous prediction for this company profile
            old_prediction = Prediction.query.filter_by(
                company_profile_id=company_profile.id
            ).order_by(Prediction.prediction_date.desc()).first()
            
            if old_prediction:
                # Create temporary new profile for comparison
                new_profile = CompanyProfile(
                    monthly_inflow=form_data['Monthly_Inflow'],
                    monthly_outflow=form_data['Monthly_Outflow'],
                    gst_compliance_score=form_data['Gst_compliance_score'],
                    ecommerce_sales=form_data['Ecommerce_sales'],
                    supplier_payments=form_data['Supplier_payments'],
                    invoice_issued=form_data['Invoice_issued'],
                    invoice_amount=form_data['Invoice_amount'],
                    employee_count=form_data['Employee_count'],
                    asset_value=form_data['Asset_value'],
                    business_age=form_data['Business_age'],
                    business_size=form_data['Business_size']
                )
                
                difference_summary = compare_profiles(
                    company_profile,
                    new_profile,
                    old_prediction.credit_score,
                    credit_score
                )
        
        # Save prediction linked to CompanyProfile
        new_prediction = Prediction(
            credit_score=credit_score,
            risk_category=risk_category,
            user_id=current_user.id,  # Keep for backward compatibility
            company_profile_id=company_profile.id if company_profile else None,
            extracted_company_name=extracted_company_name or (company_profile.extracted_company_name if company_profile else None),
            input_features=json.dumps(form_data)
        )
        db.session.add(new_prediction)
        
        db.session.commit()
        
        response = {
            'status': 'success',
            'prediction_id': new_prediction.id
        }
        
        if difference_summary:
            response['difference_summary'] = difference_summary
        
        return jsonify(response)
        
    except Exception as e:
        app.logger.exception(f"Error in save_prediction: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
