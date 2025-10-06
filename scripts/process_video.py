import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

import cv2
import numpy as np
import requests
from dotenv import load_dotenv

# Ensure the app package is accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.detection import RedLightDetector
from app.models.ocr import LicensePlateOCR
from app.models.profiler import calculate_smart_fine
from app.utils.config_utils import load_signal_intervals
from app.utils.video_utils import create_video_writer, save_frame_snapshot

# Load environment variables (for Config access)
load_dotenv()

# Set up logging for the script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/process_video.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ProcessVideoScript")

# --- Configuration Constants (Read from .env via Config, but defined here for clarity)
from app.config import Config
API_BASE_URL = "http://127.0.0.1:5000/api/v1/violations"
FRAME_RATE_FOR_CLIP = 8 # Frames before/after violation to save in clip
CLIP_DURATION_SECONDS = 3 # Total duration of the clip (e.g., 3 seconds)

def parse_stop_line(line_str: str) -> Tuple[int, int, int, int]:
    """Converts a comma-separated string to a stop line coordinate tuple."""
    try:
        coords = [int(c.strip()) for c in line_str.split(',')]
        if len(coords) != 4:
            raise ValueError("Stop line must have 4 coordinates (x1,y1,x2,y2).")
        return tuple(coords)
    except Exception as e:
        logger.error(f"Invalid stop line format: {e}")
        sys.exit(1)

def is_within_red_interval(current_time: datetime, intervals: List[Dict[str, datetime]]) -> bool:
    """Checks if the current time falls within any of the red light intervals."""
    for interval in intervals:
        if interval['start'] <= current_time <= interval['end']:
            return True
    return False

def process_video(
    video_path: str, 
    signal_json_path: str, 
    stop_line_coords: Tuple[int, int, int, int], 
    output_path: str,
    force_red: bool = False
) -> None:
    """
    Main function to process the video, detect violations, and log them.
    """
    logger.info(f"Processing video: {video_path}...")
    
    # 1. Initialization
    detector = RedLightDetector(weights_path=Config.YOLO_WEIGHTS_PATH)
    ocr_service = LicensePlateOCR(backend=Config.OCR_BACKEND)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video file: {video_path}")
        return

    # Video properties
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Time offset for video to real-world time (Placeholder: assume video starts now)
    video_start_time = datetime.now() 
    
    # Load signal intervals
    red_intervals = []
    if not force_red and signal_json_path:
        red_intervals = load_signal_intervals(signal_json_path)

    # Output writer for annotated video
    writer = create_video_writer(output_path, cap)
    if not writer:
        cap.release()
        return
    
    frame_idx = 0
    logged_violations: Dict[int, bool] = {} # {track_id: True} to prevent re-logging same violation
    
    # Frame buffer for saving video clips
    frame_buffer: Dict[int, Dict[str, Any]] = {} # {frame_idx: {'frame': np.ndarray, 'timestamp': datetime}}
    frames_per_clip = int(fps * CLIP_DURATION_SECONDS)
    
    # --- Main Video Processing Loop ---
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        current_time_offset = frame_idx / fps
        current_dt = video_start_time + timedelta(seconds=current_time_offset)
        
        is_red = force_red or is_within_red_interval(current_dt, red_intervals)
        
        # 1. Detect and Check Violation
        annotated_frame, violation_data = detector.process_frame(
            frame, frame_idx, stop_line_coords, is_red
        )
        
        # 2. Add current frame to buffer
        frame_buffer[frame_idx] = {'frame': annotated_frame.copy(), 'timestamp': current_dt}
        # Keep buffer size manageable (max 10 seconds of video)
        if len(frame_buffer) > int(fps * 10):
            oldest_key = min(frame_buffer.keys())
            del frame_buffer[oldest_key]
        
        # 3. Process and Log Violation (if detected and not already logged)
        if violation_data and violation_data['track_id'] not in logged_violations:
            track_id = violation_data['track_id']
            logged_violations[track_id] = True # Mark as processing
            logger.warning(f"Red-Light Violation detected for ID {track_id} at frame {frame_idx}.")
            
            # --- OCR and Fine Calculation ---
            plate_roi = violation_data['roi']
            plate, confidence = ocr_service.run_ocr(plate_roi)
            
            # Placeholder for location factors: assume no extra factor for simplicity
            smart_fine = calculate_smart_fine(plate, location_factors=None) 
            
            # --- Save Artifacts ---
            image_path = save_frame_snapshot(
                annotated_frame, plate, current_dt, output_dir='output/images'
            )
            
            # --- Save Violation Video Clip ---
            clip_start_idx = max(0, frame_idx - int(fps * CLIP_DURATION_SECONDS / 2))
            clip_end_idx = frame_idx + int(fps * CLIP_DURATION_SECONDS / 2)
            
            clip_output_path = os.path.join(
                'output/clips', f'{plate}_{current_dt.strftime("%Y%m%d_%H%M%S")}.mp4'
            )
            clip_writer = create_video_writer(clip_output_path, cap)

            if clip_writer:
                for f_idx in range(clip_start_idx, clip_end_idx + 1):
                    if f_idx in frame_buffer:
                        clip_writer.write(frame_buffer[f_idx]['frame'])
                clip_writer.release()
                logger.info(f"Saved violation clip to: {clip_output_path}")
            else:
                clip_output_path = "Failed to save clip"

            # --- Log to API/DB ---
            violation_data = {
                "vehicle_plate": plate,
                "fine_amount": smart_fine,
                "image_path": image_path,
                "video_clip_path": clip_output_path,
                "ocr_confidence": confidence
            }
            
            try:
                response = requests.post(API_BASE_URL, json=violation_data)
                if response.status_code == 201:
                    logger.info(f"Violation successfully logged to DB via API. Plate: {plate}")
                else:
                    logger.error(f"API logging failed ({response.status_code}): {response.text}")
            except requests.exceptions.ConnectionError:
                logger.error("Could not connect to Flask API. Ensure the Flask server is running on 5000.")

        # 4. Write annotated frame to output video
        writer.write(annotated_frame)
        
        # Progress update
        if frame_idx % 100 == 0:
            sys.stdout.write(f"\rProcessing frame {frame_idx}/{total_frames}...")
            sys.stdout.flush()
        
        frame_idx += 1

    # --- Cleanup ---
    sys.stdout.write(f"\rProcessing complete. Total frames: {frame_idx}. Logged violations: {len(logged_violations)}.\n")
    cap.release()
    writer.release()
    cv2.destroyAllWindows()
    logger.info(f"Annotated video saved to: {output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="AI-Powered Red-Light Violation Detection System")
    parser.add_argument(
        "--video", 
        type=str, 
        required=True, 
        help="Path to the input CCTV video file."
    )
    parser.add_argument(
        "--signal-json", 
        type=str, 
        default="sample_data/signal_timestamps.json", 
        help="Path to the JSON file with red light intervals."
    )
    parser.add_argument(
        "--stop-line", 
        type=str, 
        required=True, 
        help="Stop line coordinates (x1,y1,x2,y2, comma-separated)."
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="output/annotated_video.mp4", 
        help="Path to save the annotated output video."
    )
    parser.add_argument(
        "--force-red", 
        action="store_true", 
        help="Treat the entire video processing time as a red light violation period."
    )
    
    args = parser.parse_args()
    
    # Ensure output directories exist
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    stop_line_tuple = parse_stop_line(args.stop_line)

    # Running the process requires the Flask app/DB to be initialized and possibly running for the API call
    logger.info("Starting video processing. Ensure Flask server is running to log violations via API.")
    process_video(
        video_path=args.video,
        signal_json_path=args.signal_json,
        stop_line_coords=stop_line_tuple,
        output_path=args.output,
        force_red=args.force_red
    )