import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, JSON, func
from sqlalchemy.orm import sessionmaker, declarative_base
from flask_sqlalchemy import SQLAlchemy
from app.config import Config

logger = logging.getLogger(__name__)

# Flask-SQLAlchemy integration
db = SQLAlchemy()
Base = db.Model # Use db.Model for Flask-SQLAlchemy ORM base

class Violation(Base):
    """
    SQLAlchemy Model for a detected Red-Light Violation.
    """
    __tablename__ = 'violations'

    id = Column(Integer, primary_key=True)
    vehicle_plate = Column(String(10), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    location_id = Column(String(50), nullable=False)
    video_clip_path = Column(String(255))
    image_path = Column(String(255))
    violation_type = Column(String(50), default='Red_Light_Crossing')
    fine_amount = Column(Float, nullable=False)
    processed_flag = Column(Boolean, default=False)
    ocr_confidence = Column(Float, default=0.0)

    def __repr__(self) -> str:
        return f"<Violation(plate='{self.vehicle_plate}', time='{self.timestamp}')>"

class DriverProfile(Base):
    """
    SQLAlchemy Model for Driver Profiling based on License Plate.
    """
    __tablename__ = 'driver_profiles'

    vehicle_plate = Column(String(10), primary_key=True)
    total_violations = Column(Integer, default=0)
    last_violation_ts = Column(DateTime)
    points = Column(Integer, default=0) # e.g., points deducted
    risk_score = Column(Float, default=1.0) # 1.0 is lowest risk
    history = Column(JSON, default=[]) # Chronological list of violation IDs

    def __repr__(self) -> str:
        return f"<DriverProfile(plate='{self.vehicle_plate}', score={self.risk_score})>"

def init_db(app=None) -> None:
    """Initializes the database engine and creates all tables.
    
    This function is primarily used by the CLI/scripts (like run_local.sh) 
    outside the main Flask request context.
    """
    if app:
        # For use inside Flask context (less common for a simple init)
        with app.app_context():
            db.create_all()
    else:
        # Standalone initialization for scripts/run_local.sh
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        Base.metadata.create_all(engine)
        logger.info("Database tables initialized successfully via standalone mode.")

# --- Helper Functions for scripts/process_video.py ---

def log_violation(plate: str, fine_amount: float, image_path: str, video_clip_path: str, confidence: float) -> Optional[Violation]:
    """Logs a new violation and returns the created Violation object."""
    from app.models.profiler import upsert_driver_profile # Avoid circular import

    try:
        # 1. Create Violation Record
        violation = Violation(
            vehicle_plate=plate,
            location_id=Config.LOCATION_ID,
            image_path=image_path,
            video_clip_path=video_clip_path,
            fine_amount=fine_amount,
            ocr_confidence=confidence
        )
        db.session.add(violation)
        db.session.commit()

        # 2. Update Driver Profile
        upsert_driver_profile(plate, violation.id)

        logger.info(f"Successfully logged violation for plate: {plate} (ID: {violation.id})")
        return violation

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error logging violation for plate {plate}: {e}")
        return None

def get_session():
    """Returns a SQLAlchemy Session for external script use."""
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    return Session()