import os
import sys
import logging

# Ensure the app package is accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.process_video import process_video, parse_stop_line

logger = logging.getLogger("AnnotateSampleScript")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def run_sample_annotation():
    """
    Runs process_video.py with default sample settings for a quick demo.
    """
    SAMPLE_VIDEO = "sample_data/sample_video.mp4"
    SIGNAL_JSON = "sample_data/signal_timestamps.json"
    OUTPUT_VIDEO = "output/annotated_demo.mp4"
    
    # Example coordinates for a stop line near the bottom-center of a 1280x720 video
    # Adjust this based on your sample_video.mp4
    DEFAULT_STOP_LINE = "300,600,980,600" # x1, y1, x2, y2
    
    if not os.path.exists(SAMPLE_VIDEO):
        logger.error(f"Sample video not found at: {SAMPLE_VIDEO}. Please add your video file.")
        return
        
    logger.info(f"Starting sample annotation of {SAMPLE_VIDEO}...")
    
    stop_line_tuple = parse_stop_line(DEFAULT_STOP_LINE)
    
    process_video(
        video_path=SAMPLE_VIDEO,
        signal_json_path=SIGNAL_JSON,
        stop_line_coords=stop_line_tuple,
        output_path=OUTPUT_VIDEO,
        force_red=False # Use signal file
    )
    
    logger.info(f"Sample annotation complete. Check {OUTPUT_VIDEO} and the DB for results.")

if __name__ == '__main__':
    # Ensure output directory exists before running
    os.makedirs('output', exist_ok=True)
    run_sample_annotation()