import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import create_app
from app.models.db import db, Base, Violation, DriverProfile

# --- Flask App Context Fixture ---

@pytest.fixture(scope='session')
def flask_app():
    """Create a test Flask application instance."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        # Use an in-memory SQLite database for fast, isolated tests
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False
    })

    with app.app_context():
        # Initialize the database and create tables
        db.create_all()
        
        # Insert sample location metadata if needed for profiler tests
        # Example: db.session.add(Location(id='SITE_001_MAIN_JUNCTION', is_school_zone=0))
        # db.session.commit()
        
        yield app

# --- Database Session Fixture ---

@pytest.fixture(scope='function')
def db_session(flask_app):
    """
    Creates a new database session for a test.
    Rolls back changes after the test is complete.
    """
    connection = db.engine.connect()
    transaction = connection.begin()
    
    # Bind the session to the connection and transaction
    session = db.session
    session.bind = connection
    
    # Begin a test
    yield session
    
    # Teardown: rollback and close
    session.remove()
    transaction.rollback()
    connection.close()

# --- Utility Fixtures ---

@pytest.fixture
def mock_violation_data():
    """Sample data for a violation."""
    return {
        'plate': 'ABC1234',
        'fine_amount': 150.00,
        'image_path': 'output/images/test.jpg',
        'video_clip_path': 'output/clips/test.mp4',
        'confidence': 0.95
    }