from datetime import datetime
import pytest
from app.models.db import Violation, DriverProfile, log_violation
from app.models.profiler import get_driver_profile

def test_violation_model_creation(db_session):
    """Test creating and retrieving a Violation record."""
    v = Violation(
        vehicle_plate='TEST1234',
        location_id='TEST_LOC',
        image_path='/test/path.jpg',
        fine_amount=100.0,
        video_clip_path='/test/clip.mp4'
    )
    db_session.add(v)
    db_session.commit()
    
    retrieved = db_session.get(Violation, v.id)
    assert retrieved is not None
    assert retrieved.vehicle_plate == 'TEST1234'
    assert isinstance(retrieved.timestamp, datetime)

def test_driver_profile_model_creation(db_session):
    """Test creating and retrieving a DriverProfile record."""
    p = DriverProfile(
        vehicle_plate='TEST1234',
        total_violations=5,
        risk_score=2.5,
        history=[1, 2, 3]
    )
    db_session.add(p)
    db_session.commit()
    
    retrieved = db_session.get(DriverProfile, 'TEST1234')
    assert retrieved is not None
    assert retrieved.total_violations == 5
    assert retrieved.risk_score == 2.5
    assert isinstance(retrieved.history, list)
    assert 3 in retrieved.history

def test_log_violation_and_upsert_profile(flask_app, db_session, mock_violation_data):
    """
    Test the integration of logging a violation and updating/creating the profile.
    
    Note: Must use the app context for the Flask-SQLAlchemy-integrated helper.
    """
    plate = mock_violation_data['plate']
    
    with flask_app.app_context():
        # 1. First violation (creates profile)
        v1 = log_violation(**mock_violation_data)
        assert v1 is not None
        assert v1.vehicle_plate == plate
        
        p1 = get_driver_profile(plate)
        assert p1.total_violations == 1
        assert p1.risk_score == pytest.approx(1.5) # Initial score
        assert p1.history == [v1.id]
        
        # 2. Second violation (updates profile)
        mock_violation_data['fine_amount'] = 200.0 # Fine might be higher for repeat
        v2 = log_violation(**mock_violation_data)
        assert v2 is not None
        
        p2 = get_driver_profile(plate)
        assert p2.total_violations == 2
        assert p2.risk_score == pytest.approx(1.65) # 1.5 * 1.1 = 1.65
        assert v2.id in p2.history
        assert len(p2.history) == 2