import logging
from flask import Flask
from .config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    """
    Factory function to create the Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    from .models.db import db
    db.init_app(app)

    # Register Blueprints
    from .api.routes import api_bp
    app.register_blueprint(api_bp)

    logger.info(f"Flask App created with environment: {app.config.get('FLASK_ENV')}")

    return app