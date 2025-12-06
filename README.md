# Lendwise - Credit Score Prediction System

A comprehensive web-based application that predicts company credit scores using advanced machine learning models with explainable AI (SHAP) integration.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Machine Learning Model](#machine-learning-model)
- [SHAP Explainability](#shap-explainability)
- [Frontend](#frontend)
- [Installation & Setup](#installation--setup)
- [How It Works](#how-it-works)
- [File Descriptions](#file-descriptions)
- [Usage](#usage)
- [Configuration](#configuration)

---

## 🎯 Project Overview

**Lendwise** is a credit score prediction platform designed for companies to assess their creditworthiness. The system analyzes financial data through machine learning models to predict credit scores (ranging from 300-900) and categorize companies into risk levels (High, Medium, or Low Risk). The application features explainable AI using SHAP values to provide transparent insights into model predictions.

### Key Capabilities
- ✅ Real-time credit score prediction
- ✅ Risk categorization (High/Medium/Low)
- ✅ Interactive SHAP visualizations
- ✅ Prediction history tracking
- ✅ Analytics dashboard
- ✅ PDF report generation
- ✅ Admin panel for system management

---

## ✨ Features

### For Companies
- **User Registration & Authentication**: Secure login system for companies
- **Credit Score Prediction**: Input financial data and get instant predictions
- **Risk Assessment**: Automatic categorization into risk levels
- **Explainable Predictions**: SHAP waterfall and force plots showing feature contributions
- **Prediction History**: Track all past predictions
- **Analytics Dashboard**: Visualize score trends over time
- **Downloadable Reports**: Export prediction results as PDF

### For Administrators
- **Admin Dashboard**: System-wide statistics and analytics
- **Company Management**: View all registered companies
- **Prediction Monitoring**: Access all company predictions
- **System Analytics**: Aggregate insights across all users

---

## 🛠 Tech Stack

### Backend
- **Flask** - Python web framework for building the application
- **SQLAlchemy** - ORM for database operations
- **Flask-Login** - User session management and authentication
- **Werkzeug** - Password hashing and security utilities

### Machine Learning & Data Science
- **scikit-learn** - Machine learning library (model training/inference)
- **pandas** - Data manipulation and analysis
- **numpy** - Numerical computing
- **joblib** - Model serialization and loading
- **SHAP** (SHapley Additive exPlanations) - Model explainability and interpretability
- **matplotlib** - Plotting and visualization (for SHAP plots)

### Frontend
- **HTML5** - Structure and markup
- **CSS3** - Styling with modern neon-themed design
- **JavaScript** - Interactive functionality and animations
- **Bootstrap** - Responsive UI framework
- **Chart.js** - Data visualization (for analytics)
- **jsPDF** - PDF generation for reports

### Database
- **SQLite** - Lightweight relational database (stored in `instance/credit_predictor.db`)

### Additional Libraries
- **jinja2** - Template engine (bundled with Flask)

---

## 📁 Project Structure

```
TPS01-cibil=100/
│
├── app.py                      # Main Flask application file
├── config.py                   # Configuration settings
├── run.py                      # Application entry point
├── req.txt                     # Python dependencies list
├── README.md                   # This file
│
├── models/                     # Database models
│   ├── __init__.py            # Database initialization
│   ├── user.py                # User model (companies)
│   └── prediction.py          # Prediction model
│
├── ml_models/                  # Machine Learning models
│   ├── best_cibil_model1.pkl  # Trained credit score prediction model
│   └── encoder1.pkl           # Label encoder for categorical features
│
├── templates/                  # HTML templates (Jinja2)
│   ├── base.html              # Base template with navigation
│   ├── index.html             # Landing page / dashboard
│   ├── login.html             # User login page
│   ├── register.html          # User registration page
│   ├── predict.html           # Credit score prediction form
│   ├── prediction_result.html # Prediction results display
│   ├── history.html           # Prediction history page
│   ├── analytics.html         # Analytics dashboard
│   ├── admin_login.html       # Admin login page
│   ├── admin_dashboard.html   # Admin main dashboard
│   ├── admin_companies.html   # Admin company list
│   └── admin_company_predictions.html  # Admin view of company predictions
│
├── static/                     # Static assets
│   ├── css/
│   │   ├── style.css          # Main stylesheet
│   │   └── speedometer.css    # Speedometer animation styles
│   ├── js/
│   │   ├── main.js            # Main JavaScript functionality
│   │   └── speedometer.js     # Speedometer visualization script
│   ├── images/                # Images and logos
│   │   ├── bg.jpg
│   │   ├── logo.png
│   │   └── lendwise-logo.svg
│   └── shap/                  # Generated SHAP visualizations
│       ├── pred_*.html        # Interactive SHAP force plots
│       └── pred_*.png         # SHAP waterfall plots
│
├── instance/                   # Application instance folder
│   └── credit_predictor.db    # SQLite database file
│
└── __pycache__/               # Python bytecode cache

```

---

## 🤖 Machine Learning Model

### Model Type
The application uses a **tree-based machine learning model** (likely Random Forest, Gradient Boosting, or XGBoost) trained on company financial data. The model is stored as a serialized pickle file.

### Model Files
- **`ml_models/best_cibil_model1.pkl`**: The trained credit score prediction model
- **`ml_models/encoder1.pkl`**: Label encoder for the categorical feature `Business_size`

### Input Features (11 Features)
The model accepts the following financial inputs:

1. **Monthly_Inflow** (float) - Monthly cash inflow in currency units
2. **Monthly_Outflow** (float) - Monthly cash outflow in currency units
3. **Gst_compliance_score** (float) - GST compliance rating
4. **Ecommerce_sales** (float) - E-commerce sales revenue
5. **Supplier_payments** (float) - Payments made to suppliers
6. **Invoice_issued** (int) - Number of invoices issued
7. **Invoice_amount** (float) - Total invoice amount
8. **Employee_count** (int) - Number of employees
9. **Asset_value** (float) - Total asset value
10. **Business_age** (float) - Age of the business in years
11. **Business_size** (categorical) - Business size category (encoded)

### Output
- **Credit Score**: Integer value ranging from 300 to 900
- **Risk Category**: 
  - **High Risk**: Score ≤ 600
  - **Medium Risk**: 601 ≤ Score ≤ 750
  - **Low Risk**: Score > 750

### Model Loading
The model and encoder are loaded once at application startup from the `ml_models/` directory. If loading fails, the application logs an error but continues to run (predictions will be unavailable).

---

## 🔍 SHAP Explainability

### What is SHAP?
SHAP (SHapley Additive exPlanations) is a framework that explains the output of machine learning models by quantifying the contribution of each feature to the prediction.

### SHAP Integration in This Project

The application uses **SHAP TreeExplainer** (optimized for tree-based models) to generate explanations for each prediction:

1. **Background Dataset**: 
   - Automatically searches for training datasets in the project root
   - Uses a sample (200 instances) as background for SHAP calculations
   - Falls back to model-only explainer if no dataset is found

2. **Generated Visualizations**:
   - **Waterfall Plot** (PNG): Shows how each feature contributes to the final prediction score
   - **Force Plot** (Interactive HTML): Interactive visualization showing feature impacts

3. **File Storage**:
   - SHAP visualizations are saved in `static/shap/`
   - Files are named as `pred_{prediction_id}_waterfall.png` and `pred_{prediction_id}_force.html`
   - Visualizations are generated on-demand when viewing prediction results

4. **Display**:
   - SHAP plots are embedded in the prediction result page
   - Waterfall plot shown as an image
   - Force plot displayed in an interactive iframe

### SHAP Features Explained
- **Positive contributions** (green/blue): Features that increase the credit score
- **Negative contributions** (red/pink): Features that decrease the credit score
- **Magnitude**: The size of the contribution indicates importance

---

## 🎨 Frontend

### Design Theme
The frontend features a modern **neon cyberpunk-inspired** design with:
- Dark theme with neon accents (cyan, pink, green)
- Smooth animations and transitions
- Responsive Bootstrap-based layout
- Interactive speedometer for credit score display

### Key Frontend Components

#### 1. **Speedometer Visualization**
- Custom animated speedometer showing credit score (300-900 range)
- Visual representation of risk level
- Located in `static/js/speedometer.js` and `static/css/speedometer.css`

#### 2. **Prediction Form** (`predict.html`)
- Interactive sliders and input fields for all 11 features
- Real-time value updates
- Form validation before submission

#### 3. **Prediction Results** (`prediction_result.html`)
- Speedometer display of credit score
- Risk category badge with color coding
- SHAP visualizations (waterfall and force plots)
- Input feature summary cards
- Explanation and recommendations sections
- PDF download functionality

#### 4. **Analytics Dashboard** (`analytics.html`)
- Line chart showing score trends over time
- Statistics: Highest, lowest, average, and latest scores
- Visual trend analysis

#### 5. **Admin Dashboard** (`admin_dashboard.html`)
- System-wide statistics
- Charts for company types, countries, and risk distributions
- Quick navigation to company and prediction management

### JavaScript Libraries Used
- **Chart.js** - For analytics charts
- **jsPDF** - For PDF report generation
- **Font Awesome** - For icons (via CDN)
- **Bootstrap** - For responsive UI components

---

## 🚀 Installation & Setup

### Prerequisites
- **Python 3.11+** installed and added to system PATH
- **pip** (Python package manager)
- **Code Editor** (VS Code recommended)

### Step-by-Step Installation

1. **Extract and Navigate**
   ```bash
   cd "C:\Users\Adhib\Downloads\TPS01-cibil=100"
   ```

2. **Create Virtual Environment**
   
   **Option A: Using VS Code**
   - Open folder in VS Code
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type: `Python: Select Interpreter`
   - Choose: `Create Virtual Environment`
   - Select Python version 3.11+
   
   **Option B: Using Command Line**
   ```bash
   python -m venv venv
   ```

3. **Activate Virtual Environment**
   
   **Windows (PowerShell):**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   
   **Windows (Command Prompt):**
   ```cmd
   venv\Scripts\activate.bat
   ```
   
   **Mac/Linux:**
   ```bash
   source venv/bin/activate
   ```
   
   You should see `(venv)` in your terminal prompt.

4. **Install Dependencies**
   ```bash
   pip install -r req.txt
   ```

5. **Verify Model Files**
   Ensure these files exist:
   - `ml_models/best_cibil_model1.pkl`
   - `ml_models/encoder1.pkl`

6. **Run the Application**
   ```bash
   python app.py
   ```
   Or:
   ```bash
   python run.py
   ```

7. **Access the Application**
   - Open your browser and navigate to: `http://127.0.0.1:5000` or `http://localhost:5000`

### First-Time Setup Notes
- The database (`instance/credit_predictor.db`) will be created automatically on first run
- Admin credentials (default):
  - Username: `admin`
  - Password: `admin123`
  - **⚠️ Change these in production!**

---

## 🔄 How It Works

### User Flow

1. **Registration/Login**
   - New companies register with company details
   - Existing users log in with email and password

2. **Making a Prediction**
   - User navigates to "Predict Credit Score" page
   - Fills in 11 financial features via form
   - Form submits POST request to `/predict` route

3. **Prediction Processing**
   - Flask receives form data
   - Data is converted to pandas DataFrame
   - Categorical feature (`Business_size`) is encoded using saved encoder
   - ML model predicts credit score
   - Risk category is determined based on score thresholds
   - Prediction is saved to database

4. **Result Display**
   - User is redirected to prediction result page
   - Credit score displayed on animated speedometer
   - Risk category shown with color-coded badge
   - SHAP explainer generates feature contribution plots
   - Input features, explanations, and recommendations are displayed
   - User can download PDF report

5. **History & Analytics**
   - User can view all past predictions
   - Analytics dashboard shows trends and statistics

### Admin Flow

1. **Admin Login**
   - Access `/admin/login`
   - Enter admin credentials

2. **Dashboard Access**
   - View system-wide statistics
   - See company distributions
   - Monitor risk categories

3. **Company Management**
   - View all registered companies
   - Access individual company prediction histories

### Technical Flow Diagram

```
User Input (Form)
    ↓
Flask Route (/predict)
    ↓
Data Preprocessing (Encoding)
    ↓
ML Model Prediction
    ↓
Risk Category Classification
    ↓
Database Storage
    ↓
SHAP Explanation Generation
    ↓
Result Page Rendering
```

---

## 📄 File Descriptions

### Core Application Files

#### `app.py`
**Role**: Main Flask application file containing all routes, business logic, and ML model integration.
- Initializes Flask app and extensions
- Loads ML models and SHAP explainer
- Defines all web routes (user auth, prediction, admin, etc.)
- Handles prediction processing and SHAP visualization generation
- Manages database operations

#### `config.py`
**Role**: Application configuration settings.
- Secret key for session management
- Database URI (SQLite path)
- Admin credentials
- Risk category thresholds (HIGH_RISK_MAX, MEDIUM_RISK_MAX, LOW_RISK_MAX)

#### `run.py`
**Role**: Application entry point for running the server.
- Simple wrapper to start the Flask development server
- Can be used as an alternative to `python app.py`

### Database Models

#### `models/__init__.py`
**Role**: Database initialization and model imports.
- Creates SQLAlchemy database instance
- Imports all model classes

#### `models/user.py`
**Role**: User/Company database model.
- Stores company information (name, email, company_type, country)
- Handles password hashing
- One-to-many relationship with Prediction model

#### `models/prediction.py`
**Role**: Prediction database model.
- Stores credit score, risk category, prediction date
- Links to user via foreign key
- Stores input features as JSON for explainability

### Template Files (HTML)

#### `templates/base.html`
**Role**: Base template with common layout (navigation, footer, includes).
- Contains navigation bar
- Loads common CSS/JS libraries
- Other templates extend this file

#### `templates/index.html`
**Role**: Landing page and authenticated user dashboard.
- Shows different content for guests, users, and admins
- Displays feature cards explaining the platform
- Entry point for authenticated users

#### `templates/predict.html`
**Role**: Credit score prediction form.
- Contains form with 11 input fields
- Interactive sliders for numeric inputs
- Dropdown for Business_size selection
- Form validation before submission

#### `templates/prediction_result.html`
**Role**: Display prediction results with SHAP explanations.
- Animated speedometer showing credit score
- Risk category display
- SHAP waterfall and force plots
- Input features summary
- Explanations and recommendations
- PDF download functionality

#### `templates/history.html`
**Role**: List of all user predictions.
- Table showing prediction history
- Links to individual prediction results

#### `templates/analytics.html`
**Role**: Analytics dashboard with charts.
- Line chart of score trends
- Statistics display (highest, lowest, average, latest)
- Visual trend analysis

#### `templates/admin_*.html`
**Role**: Admin interface templates.
- Login page, dashboard, company management
- System-wide analytics and monitoring

### Static Assets

#### `static/css/style.css`
**Role**: Main stylesheet with neon-themed styling.
- Dark theme colors
- Neon accent colors (cyan, pink, green)
- Responsive design rules
- Animation definitions

#### `static/css/speedometer.css`
**Role**: Speedometer visualization styles.
- Needle animation
- Gauge face styling
- Label positioning

#### `static/js/main.js`
**Role**: Main JavaScript functionality.
- Form interactions
- UI enhancements
- Client-side validations

#### `static/js/speedometer.js`
**Role**: Speedometer animation logic.
- Calculates needle rotation based on score
- Animates needle movement
- Updates display values

### Configuration Files

#### `req.txt`
**Role**: Python package dependencies list.
- Lists all required packages with versions (if specified)
- Used by `pip install -r req.txt`

### Data Files

#### `ml_models/best_cibil_model1.pkl`
**Role**: Trained machine learning model (serialized).
- Contains the trained tree-based model
- Loaded at application startup
- Used for all predictions

#### `ml_models/encoder1.pkl`
**Role**: Label encoder for categorical features.
- Encodes `Business_size` categorical values to numeric
- Must match training-time encoding

#### `instance/credit_predictor.db`
**Role**: SQLite database file.
- Stores all user accounts
- Stores all prediction records
- Created automatically on first run

---

## 💻 Usage

### For Regular Users

1. **Register an Account**
   - Click "Register" on the homepage
   - Fill in company details
   - Create password

2. **Login**
   - Enter email and password
   - Access dashboard

3. **Make a Prediction**
   - Click "Predict Credit Score"
   - Fill in all financial fields
   - Submit form
   - View results with SHAP explanations

4. **View History**
   - Navigate to "Prediction History"
   - Click on any prediction to view details

5. **View Analytics**
   - Access "Analytics" page
   - Review score trends and statistics

### For Administrators

1. **Admin Login**
   - Navigate to `/admin/login`
   - Use admin credentials

2. **View Dashboard**
   - See system statistics
   - Monitor company distributions

3. **Manage Companies**
   - View all registered companies
   - Access company prediction histories

4. **Monitor System**
   - Track total predictions
   - Analyze risk category distributions

---

## ⚙️ Configuration

### Changing Admin Credentials

Edit `config.py`:
```python
ADMIN_USERNAME = 'your_new_username'
ADMIN_PASSWORD = 'your_new_password'
```

### Modifying Risk Thresholds

Edit `config.py`:
```python
HIGH_RISK_MAX = 600      # Scores ≤ 600 are High Risk
MEDIUM_RISK_MAX = 750    # Scores 601-750 are Medium Risk
# Scores > 750 are Low Risk
```

### Changing Database Location

Edit `config.py`:
```python
SQLALCHEMY_DATABASE_URI = 'sqlite:///path/to/your/database.db'
```

### Environment Variables (Optional)

You can use environment variables for sensitive configuration:
- `SECRET_KEY` - Flask session secret key
- `DATABASE_URL` - Database connection string

---

## 🔒 Security Notes

- ⚠️ **Change default admin credentials** before deploying
- ⚠️ **Use environment variables** for sensitive configuration in production
- ⚠️ **Enable HTTPS** in production environments
- ⚠️ **Keep dependencies updated** for security patches
- ⚠️ **Validate all user inputs** (currently implemented)

---

## 📝 Notes

- The application uses **development mode** (`debug=True`) - disable for production
- SHAP explanations require the model to be tree-based (TreeExplainer)
- Database is created automatically on first run
- SHAP visualizations are generated on-demand and stored in `static/shap/`

---

## 🐛 Troubleshooting

### Model Not Loading
- Check if `ml_models/best_cibil_model1.pkl` exists
- Verify model file is not corrupted
- Check application logs for detailed error messages

### SHAP Not Working
- Ensure model is tree-based (TreeExplainer requirement)
- Check if background dataset exists in project root (optional)
- Review logs for SHAP generation errors

### Database Errors
- Ensure `instance/` directory exists and is writable
- Delete `credit_predictor.db` to reset database (⚠️ loses all data)

### Port Already in Use
- Change port in `app.py`: `app.run(debug=True, port=5001)`

---

## 📧 Support

For issues or questions:
1. Check the logs in the terminal/console
2. Verify all dependencies are installed correctly
3. Ensure Python version is 3.11 or higher
4. Check file permissions for database and model files

---

## 📄 License

This project is proprietary software. All rights reserved.

---

**Built with ❤️ using Flask, scikit-learn, and SHAP**

