import argparse
import os
import sys
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Ensure the app package is accessible for config access
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
logger = logging.getLogger("MergeClipsScript")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def merge_clips(clip_paths: list[str], output_path: str):
    """
    Merges multiple video clips into a single output file using MoviePy.
    
    Args:
        clip_paths: A list of full paths to the video files to merge.
        output_path: The full path for the final merged video file.
    """
    if not clip_paths:
        logger.error("No clips provided to merge.")
        return
    
    logger.info(f"Attempting to merge {len(clip_paths)} clips...")
    
    # 1. Load clips
    clips = []
    valid_clips = []
    for path in clip_paths:
        if not os.path.exists(path):
            logger.warning(f"Clip file not found, skipping: {path}")
            continue
        try:
            clip = VideoFileClip(path)
            clips.append(clip)
            valid_clips.append(path)
        except Exception as e:
            logger.error(f"Error loading clip {path}: {e}")
            continue

    if not clips:
        logger.error("No valid clips could be loaded for merging.")
        return
        
    # 2. Concatenate
    try:
        final_clip = concatenate_videoclips(clips)
        
        # 3. Write output
        final_clip.write_videofile(
            output_path, 
            codec='libx264', 
            audio_codec='aac', 
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=clips[0].fps # Use the FPS of the first clip
        )
        logger.info(f"Successfully merged clips to: {output_path}")

    except Exception as e:
        logger.error(f"An error occurred during video merging: {e}")
        
    finally:
        # Close all clips to release file handles
        for clip in clips:
            clip.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Utility to merge multiple video clips into one.")
    parser.add_argument(
        "--clip-dir", 
        type=str, 
        default="output/clips", 
        help="Directory where individual clips are stored."
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="output/videos/merged_evidence.mp4", 
        help="Path for the final merged output video."
    )
    parser.add_argument(
        "--clips", 
        nargs='+', 
        required=True, 
        help="List of clip filenames (relative to --clip-dir) to merge."
    )
    
    args = parser.parse_args()
    
    # Construct full paths
    full_clip_paths = [os.path.join(args.clip_dir, filename) for filename in args.clips]
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    merge_clips(full_clip_paths, args.output)