import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # SQLite default, easily swappable to PostgreSQL or MySQL
    _database_url = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{BASE_DIR / 'instance' / 'database.db'}"
    )
    # Render/Postgres commonly supplies postgresql://. With psycopg v3,
    # explicitly select the psycopg SQLAlchemy driver.
    if _database_url.startswith('postgres://'):
        _database_url = 'postgresql+psycopg://' + _database_url[len('postgres://'):]
    elif _database_url.startswith('postgresql://'):
        _database_url = 'postgresql+psycopg://' + _database_url[len('postgresql://'):]
    SQLALCHEMY_DATABASE_URI = _database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Uploads directory for Excel/CSV imports
    UPLOAD_FOLDER = str(BASE_DIR / 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    ALLOWED_EXTENSIONS = {'xlsx', 'csv'}
    
    # Admin Credentials
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
    
    # AI Question Generation Configuration (Optional)
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'template')  # 'openai', 'gemini', 'template'
    AI_API_KEY = os.environ.get('AI_API_KEY', '')
    AI_MODEL = os.environ.get('AI_MODEL', '')
    
    # Proctoring Defaults
    DEFAULT_MAX_VIOLATIONS = 3
    VIOLATION_WARNING_SECONDS = 20
    POLL_INTERVAL_MS = 2500
