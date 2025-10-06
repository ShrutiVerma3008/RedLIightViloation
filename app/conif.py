import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Base configuration class for the Flask application.
    Loads settings from environment variables.
    """
    # Core Flask Configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'default_insecure_secret_key')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'

    # Database Configuration (SQLAlchemy)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False # Set to True to see SQL queries

    # System Configuration
    LOCATION_ID = os.getenv('LOCATION_ID', 'DEFAULT_LOCATION_000')
    OCR_BACKEND = os.getenv('OCR_BACKEND', 'easyocr').lower()
    YOLO_WEIGHTS_PATH = os.getenv('YOLO_WEIGHTS_PATH', 'yolov8n.pt')

    # Fine Calculation Parameters (Used by profiler.py)
    BASE_FINE = float(os.getenv('BASE_FINE', 100.0))
    REPEAT_OFFENDER_MULTIPLIER = float(os.getenv('REPEAT_OFFENDER_MULTIPLIER', 1.5))
    SCHOOL_ZONE_FACTOR = float(os.getenv('SCHOOL_ZONE_FACTOR', 2.0))
    NIGHT_HOUR_START = int(os.getenv('NIGHT_HOUR_START', 22))
    NIGHT_HOUR_END = int(os.getenv('NIGHT_HOUR_END', 6))
    NIGHT_FACTOR = float(os.getenv('NIGHT_FACTOR', 1.2))