import logging
import json
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# Pydantic model for a single red interval
class RedInterval(BaseModel):
    start: datetime = Field(..., description="ISO 8601 start timestamp")
    end: datetime = Field(..., description="ISO 8601 end timestamp")

# Pydantic model for the entire signal timestamps file
class SignalTimestamps(BaseModel):
    red_intervals: List[RedInterval] = Field(..., description="List of red light intervals.")

def load_signal_intervals(json_path: str) -> List[Dict[str, datetime]]:
    """
    Loads and validates the red light signal timestamps from a JSON file.
    
    Args:
        json_path: Path to the signal_timestamps.json file.
        
    Returns:
        A list of dictionaries, each containing 'start' and 'end' datetime objects.
    """
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        # Use Pydantic for validation and type conversion
        validated_data = SignalTimestamps(**data)
        
        intervals = []
        for interval in validated_data.red_intervals:
            intervals.append({
                'start': interval.start,
                'end': interval.end
            })
            
        logger.info(f"Loaded {len(intervals)} red light intervals from {json_path}.")
        return intervals
        
    except FileNotFoundError:
        logger.error(f"Signal timestamps file not found at: {json_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding signal timestamps JSON: {e}")
        return []
    except ValidationError as e:
        logger.error(f"Signal timestamps JSON failed validation: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred loading signal data: {e}")
        return []