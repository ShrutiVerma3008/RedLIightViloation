import logging
from flask import Blueprint, jsonify, render_template, request, current_app
from sqlalchemy import func, desc, text
from marshmallow import Schema, fields, validate
from app.models.db import db, Violation, DriverProfile, log_violation

logger = logging.getLogger(__name__)

# Flask Blueprint for API and Web routes
api_bp = Blueprint('api', __name__)

# --- Marshmallow Schemas for API Validation/Serialization ---

class ViolationSchema(Schema):
    """Schema for validating and serializing Violation data."""
    vehicle_plate = fields.Str(required=True, validate=validate.Length(min=2, max=10))
    fine_amount = fields.Float(required=True, validate=validate.Range(min=0))
    image_path = fields.Str(required=True)
    video_clip_path = fields.Str(required=True)
    ocr_confidence = fields.Float(required=False, default=0.0)

# --- API Endpoints (Used by process_video.py) ---

@api_bp.route('/api/v1/violations', methods=['POST'])
def create_violation():
    """Endpoint to log a new red-light violation."""
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({"message": "No input data provided"}), 400
        
        # Validate input data
        schema = ViolationSchema()
        errors = schema.validate(json_data)
        if errors:
            return jsonify({"message": "Validation error", "errors": errors}), 422
        
        data = schema.load(json_data)
        
        # Log the violation using the DB helper function
        with current_app.app_context():
            violation_record = log_violation(
                plate=data['vehicle_plate'],
                fine_amount=data['fine_amount'],
                image_path=data['image_path'],
                video_clip_path=data['video_clip_path'],
                confidence=data.get('ocr_confidence', 0.0)
            )
            
            if violation_record:
                logger.info(f"API: New violation created for {data['vehicle_plate']}")
                return jsonify({"message": "Violation logged successfully", "violation_id": violation_record.id}), 201
            else:
                return jsonify({"message": "Failed to log violation in database"}), 500

    except Exception as e:
        logger.error(f"Error in /api/v1/violations POST: {e}")
        return jsonify({"message": "Internal Server Error"}), 500

# --- Web Dashboard Routes ---

@api_bp.route('/')
def dashboard():
    """Dashboard route showing overall stats."""
    with current_app.app_context():
        # Total Violations
        total_violations = db.session.query(func.count(Violation.id)).scalar()
        
        # Total Unique Offenders
        unique_offenders = db.session.query(func.count(DriverProfile.vehicle_plate)).scalar()

        # Top 5 Offenders
        top_offenders = db.session.query(DriverProfile) \
            .order_by(desc(DriverProfile.total_violations), desc(DriverProfile.risk_score)) \
            .limit(5).all()

        # Violation Trend (Simple count by day for a basic chart)
        # Note: This is simplified for SQLite compatibility in testing; a real DB query would group by date
        # Example for PostgreSQL:
        # daily_trend = db.session.query(func.date_trunc('day', Violation.timestamp).label('date'), func.count(Violation.id))
        #                .group_by(text('date')).order_by(text('date')).limit(7).all()
        
        # Using a simple aggregation for compatibility
        daily_trend = db.session.query(
            func.strftime('%Y-%m-%d', Violation.timestamp).label('date'),
            func.count(Violation.id)
        ).group_by(text('date')).order_by(text('date')).limit(7).all()
        
        # Convert results for Chart.js
        trend_data = [{'date': date_str, 'count': count} for date_str, count in daily_trend]
        
        context = {
            'total_violations': total_violations,
            'unique_offenders': unique_offenders,
            'top_offenders': top_offenders,
            'trend_data_json': trend_data,
        }
        return render_template('index.html', **context)

@api_bp.route('/offenders')
def offender_list():
    """Paginated list of all driver profiles."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    with current_app.app_context():
        pagination = db.session.query(DriverProfile) \
            .order_by(desc(DriverProfile.total_violations)) \
            .paginate(page=page, per_page=per_page, error_out=False)
        
        context = {
            'pagination': pagination,
            'offenders': pagination.items
        }
        return render_template('offender_list.html', **context)

@api_bp.route('/violation/<int:violation_id>')
def violation_detail(violation_id: int):
    """Detail page for a specific violation."""
    with current_app.app_context():
        violation = db.session.get(Violation, violation_id)
        if not violation:
            return render_template('404.html'), 404 # Assuming a basic 404 is available
            
        driver_profile = db.session.get(DriverProfile, violation.vehicle_plate)
        
        context = {
            'violation': violation,
            'profile': driver_profile,
            'plate': violation.vehicle_plate,
            'timestamp': violation.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
        }
        return render_template('violation_detail.html', **context)