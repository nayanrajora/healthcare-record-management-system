import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory: HealthcareBlockchain directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env if present
env_file = BASE_DIR / '.env'
if env_file.exists():
    load_dotenv(env_file)


class Config:
    """Base application configuration with secure, beginner-friendly defaults."""
    SECRET_KEY = os.environ.get(
        'SECRET_KEY', 
        'college-major-project-healthcare-blockchain-secret-key-2026'
    )
    
    # Instance folder for local SQLite database
    INSTANCE_PATH = BASE_DIR / 'instance'
    INSTANCE_PATH.mkdir(exist_ok=True)
    
    DATABASE_PATH = os.environ.get(
        'DATABASE_PATH', 
        str(INSTANCE_PATH / 'healthcare.db')
    )
    
    # Flask Session Security for local development
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True only if running over HTTPS
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # WTForms CSRF protection enabled
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600


class TestConfig(Config):
    """Configuration for automated test execution using an isolated in-memory or temp SQLite db."""
    TESTING = True
    WTF_CSRF_ENABLED = False  # Disabled during automated unit tests to simplify form testing
    DATABASE_PATH = ':memory:'
