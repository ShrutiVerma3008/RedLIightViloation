import logging
import json
import math
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
from ultralytics import YOLO
import cv2
import numpy as np
from app.config import Config
from app.utils.config_utils import load_signal_intervals

logger = logging.getLogger(__name__)

# Vehicle classes in COCO dataset: car (2), motorbike (3), bus (5), truck (7)
VEHICLE_CLASS_IDS = [2, 3, 5, 7] 

class RedLightDetector:
    """
    Handles YOLOv8 detection, object tracking, and stop-line violation logic.
    """
    def __init__(self, weights_path: str = Config.YOLO_WEIGHTS_PATH):
        """Initializes the YOLO model and tracking buffer."""
        try:
            # Load pre-trained YOLOv8 model
            self.model = YOLO(weights_path)
            # Tracking buffer: {track_id: [{'frame_idx': X, 'centroid': (x, y)}]}
            self.tracking_history: Dict[int, List[Dict[str, Any]]] = {}
            logger.info(f"YOLO model loaded from {weights_path}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise

    def process_frame(self, frame: np.ndarray, frame_idx: int, stop_line: Tuple[int, int, int, int], is_red_light: bool) -> Tuple[np.ndarray, Optional[Dict[str, Any]]]:
        """
        Runs detection and tracking on a single frame, checking for a violation.
        
        Args:
            frame: The current video frame (BGR).
            frame_idx: Index of the current frame.
            stop_line: The (x1, y1, x2, y2) coordinates of the stop line.
            is_red_light: True if the traffic light is currently red.
            
        Returns:
            A tuple of (annotated_frame, violation_data).
        """
        # Run tracking (uses YOLOv8's built-in OCSORT/BoT-SORT tracker)
        results = self.model.track(frame, persist=True, classes=VEHICLE_CLASS_IDS, verbose=False)
        annotated_frame = frame.copy()
        
        violation_data = None
        
        if results and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)

            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = box
                centroid = ((x1 + x2) // 2, y2) # Use bottom-center for robust tracking near stop line
                
                # Update tracking history
                if track_id not in self.tracking_history:
                    self.tracking_history[track_id] = []
                self.tracking_history[track_id].append({'frame_idx': frame_idx, 'centroid': centroid})
                
                # Keep history size manageable (e.g., last 5 frames)
                if len(self.tracking_history[track_id]) > 5:
                    self.tracking_history[track_id].pop(0)

                # Check for Violation (only if the light is red)
                if is_red_light:
                    if self._check_violation(track_id, centroid, stop_line):
                        violation_data = {
                            'track_id': track_id,
                            'bbox': box,
                            'centroid': centroid,
                            'frame_idx': frame_idx,
                            'roi': frame[y1:y2, x1:x2], # Region of Interest for potential OCR
                            'timestamp': datetime.now() # Real-time processing timestamp
                        }
                        # Highlight the violation
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 3) # Red box
                        cv2.putText(annotated_frame, f"VIOLATION! ID:{track_id}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                        
                        # Stop checking for this vehicle once a violation is registered
                        break 

                # Draw standard tracking box (green/blue when not a violation)
                color = (0, 255, 0) if is_red_light else (255, 0, 0)
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(annotated_frame, f"ID:{track_id}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Draw the stop line
        x1_line, y1_line, x2_line, y2_line = stop_line
        cv2.line(annotated_frame, (x1_line, y1_line), (x2_line, y2_line), (0, 0, 255) if is_red_light else (0, 255, 255), 3)

        return annotated_frame, violation_data

    def _check_violation(self, track_id: int, current_centroid: Tuple[int, int], stop_line: Tuple[int, int, int, int]) -> bool:
        """
        Checks if a vehicle's centroid crossed the stop-line.
        Uses a simple check: vehicle's y-coordinate is *past* the line and its
        previous y-coordinate was *before* the line.
        
        Args:
            track_id: The ID of the tracked vehicle.
            current_centroid: (x, y) of the current frame's centroid.
            stop_line: (x1, y1, x2, y2) coordinates of the stop line.
            
        Returns:
            True if a crossing violation is detected.
        """
        history = self.tracking_history.get(track_id, [])
        if len(history) < 2:
            return False # Need at least current and previous position

        # Stop line is assumed to be roughly horizontal, use the average Y
        stop_line_y = (stop_line[1] + stop_line[3]) / 2

        # Most stop lines are laid out such that crossing means a vehicle moves
        # from a lower Y (farther away) to a higher Y (closer to the intersection).
        # Violation is detected if:
        # 1. Current centroid's Y is past the stop line (e.g., y > stop_line_y)
        # 2. Previous centroid's Y was before or on the stop line (e.g., y_prev <= stop_line_y)
        
        # Get previous centroid
        prev_centroid = history[-2]['centroid']
        
        # Check if the vehicle *just* crossed the line.
        # This assumes Y-coordinates increase as you move into the intersection.
        crossed_past_line = current_centroid[1] > stop_line_y
        was_before_or_on = prev_centroid[1] <= stop_line_y
        
        # Check if the vehicle has been marked as violating already to prevent duplicate logs in subsequent frames
        # We assume the `process_video.py` script will clear the track history or stop processing once logged.
        
        # Simple crossing logic:
        is_crossing = crossed_past_line and was_before_or_on
        
        # NOTE: For non-horizontal lines, a full line segment intersection check (e.g., using `cv2.ClipLine` or custom math)
        # would be required, but the centroid comparison offers good robustness for common setups.
        
        return is_crossing