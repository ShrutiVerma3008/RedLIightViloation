import logging
from typing import Dict, Any, Optional
from datetime import datetime, time
from sqlalchemy import func
from app.models.db import db, DriverProfile, Violation
from app.config import Config

logger = logging.getLogger(__name__)

# --- Smart Fine Calculation ---

def is_night_hour(dt: datetime) -> bool:
    """Checks if the given time is within the configured night hours."""
    current_time = dt.time()
    start = time(Config.NIGHT_HOUR_START)
    end = time(Config.NIGHT_HOUR_END)
    
    if start <= end:
        # e.g., 6am to 10pm (day)
        return not (start <= current_time < end)
    else:
        # e.g., 10pm to 6am (night, crosses midnight)
        return start <= current_time or current_time < end

def calculate_smart_fine(plate: str, location_factors: Dict[str, float] = None) -> float:
    """
    Calculates the fine amount based on the violation, driver profile, and location/time.
    
    Formula: Base Fine * Repeat Offender Multiplier * Location Factor * Time Factor
    
    Args:
        plate: The vehicle license plate string.
        location_factors: A dictionary of {factor_name: multiplier} for the location.
        
    Returns:
        The calculated fine amount (float).
    """
    # 1. Base Fine
    fine = Config.BASE_FINE
    
    # 2. Repeat Offender Multiplier
    profile = db.session.get(DriverProfile, plate)
    if profile and profile.total_violations > 0:
        # Simple multiplier: 1.0 + (N_violations * (Multiplier - 1.0))
        # Ensure it's at least the BASE_FINE
        multiplier = 1.0 + (profile.total_violations * (Config.REPEAT_OFFENDER_MULTIPLIER - 1.0))
        fine *= max(1.0, multiplier)
        logger.debug(f"Fine for {plate} adjusted by repeat offender factor ({multiplier:.2f})")

    # 3. Location Factor (Placeholder - requires location data)
    # Example: If location is a school zone, apply factor
    if location_factors and location_factors.get('is_school_zone', 0):
        fine *= Config.SCHOOL_ZONE_FACTOR
        logger.debug(f"Fine for {plate} adjusted by School Zone factor ({Config.SCHOOL_ZONE_FACTOR:.2f})")

    # 4. Time Factor (Night/Peak Hours)
    current_dt = datetime.now()
    if is_night_hour(current_dt):
        fine *= Config.NIGHT_FACTOR
        logger.debug(f"Fine for {plate} adjusted by Night Hour factor ({Config.NIGHT_FACTOR:.2f})")
    
    return round(fine, 2)


# --- Driver Profile Management ---

def get_driver_profile(plate: str) -> Optional[DriverProfile]:
    """Retrieves a driver profile by plate."""
    return db.session.get(DriverProfile, plate)

def upsert_driver_profile(plate: str, violation_id: int) -> DriverProfile:
    """
    Creates or updates a driver's profile after a violation is logged.
    
    Args:
        plate: The vehicle license plate.
        violation_id: The ID of the newly created violation record.
        
    Returns:
        The updated or new DriverProfile object.
    """
    profile = db.session.get(DriverProfile, plate)
    
    if not profile:
        # Create new profile
        profile = DriverProfile(
            vehicle_plate=plate,
            total_violations=1,
            last_violation_ts=datetime.utcnow(),
            points=3, # Initial point deduction
            risk_score=1.5, # Initial risk score
            history=[violation_id]
        )
        db.session.add(profile)
        logger.info(f"New driver profile created for {plate}.")
    else:
        # Update existing profile
        profile.total_violations = DriverProfile.total_violations + 1
        profile.last_violation_ts = datetime.utcnow()
        profile.points = DriverProfile.points + 3
        # Simple risk score increase: (current * 1.1)
        profile.risk_score = min(5.0, profile.risk_score * 1.1)
        
        # Append violation to history list (handle potential None/empty array)
        if profile.history is None:
            profile.history = []
        profile.history.append(violation_id)
        
        logger.info(f"Driver profile updated for {plate}. Total violations: {profile.total_violations}")
        
    db.session.commit()
    return profile