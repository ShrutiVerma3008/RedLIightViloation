import logging
import os
import math
from typing import Tuple, Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)

def draw_bounding_box(frame: np.ndarray, bbox: np.ndarray, label: str, color: Tuple[int, int, int] = (0, 255, 0)) -> None:
    """
    Draws a bounding box and label on the frame.
    
    Args:
        frame: The image frame (BGR).
        bbox: The bounding box in [x1, y1, x2, y2] format.
        label: The text label to display above the box.
        color: The color of the box and text.
    """
    x1, y1, x2, y2 = bbox.astype(int)
    
    # Draw rectangle
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    
    # Put label text
    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    
    # Draw background box for text
    cv2.rectangle(frame, (x1, y1 - h - 5), (x1 + w + 5, y1), color, -1)
    
    # Put text
    cv2.putText(frame, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

def save_frame_snapshot(frame: np.ndarray, plate: str, violation_time: datetime, output_dir: str = 'output/images') -> str:
    """
    Saves a snapshot of the frame at the time of violation.
    
    Args:
        frame: The frame to save (BGR).
        plate: License plate for naming the file.
        violation_time: The timestamp of the violation.
        output_dir: The directory to save the image.
        
    Returns:
        The full path to the saved image.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a unique filename
    timestamp_str = violation_time.strftime('%Y%m%d_%H%M%S_%f')[:-3]
    filename = f"{plate}_{timestamp_str}.jpg"
    full_path = os.path.join(output_dir, filename)
    
    cv2.imwrite(full_path, frame)
    logger.info(f"Saved violation snapshot to: {full_path}")
    return full_path

def create_video_writer(output_path: str, cap: cv2.VideoCapture) -> Optional[cv2.VideoWriter]:
    """
    Creates an OpenCV VideoWriter object configured from the input capture object.
    
    Args:
        output_path: Path for the output video file.
        cap: The input video capture object.
        
    Returns:
        The configured VideoWriter object or None on failure.
    """
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0 # Default to 30 FPS if not available
    
    # Use MP4 (H.264) codec
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
    
    writer = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
    
    if not writer.isOpened():
        logger.error(f"Failed to create VideoWriter for path: {output_path}")
        return None
        
    logger.info(f"VideoWriter created: {output_path}, Resolution: {frame_width}x{frame_height}, FPS: {fps:.2f}")
    return writer