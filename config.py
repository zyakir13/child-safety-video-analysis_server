import os

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Motion Detection Settings
MOTION_THRESHOLD = 1  # Decreased by 50% (from 2 to 1) for higher sensitivity

# Frame Sampling Settings  
FRAMES_PER_SECOND = 8  # Increased from 4 to 8 for better temporal resolution
ANALYSIS_WINDOW_SECONDS = 2  # Reduced from 4 to 2 for higher quality 8-frame analysis

# Motion Grouping Settings
MOTION_GAP_THRESHOLD = 0.3  # Merge motion events within 0.3s
MINIMUM_MOTION_DENSITY = 0.125  # Require 12.5% motion within analysis window (0.25s out of 2s) - decreased by 50%

# High-Motion Window Splitting Settings
HIGH_MOTION_THRESHOLD = 12.0  # Motion events per second to trigger window splitting
HIGH_MOTION_SPLIT_WINDOW_SIZE = 1  # Split high-motion 2s windows into 1s sub-windows
HIGH_MOTION_SPLIT_FPS = 16  # Use higher FPS (16 instead of 8) for split windows

# Motion Enhancement Settings
ENABLE_MOTION_ENHANCEMENT = True  # Apply motion highlighting to composite images
MOTION_HIGHLIGHT_THRESHOLD = 12  # Pixel difference threshold for motion detection (decreased by 50% for higher sensitivity)
MOTION_HIGHLIGHT_COLOR = (0, 255, 0)  # BGR color for motion highlights (green)
MOTION_HIGHLIGHT_INTENSITY = 0.4  # Overlay intensity (0.0-1.0)
MOTION_CONTRAST_BOOST = 1.3  # Contrast multiplier for motion areas

# Motion Filtering Settings
MOTION_MIN_CONTOUR_AREA_RATIO = 0.001  # Minimum contour area as ratio of frame size (0.1%)
MOTION_PERSISTENCE_FRAMES = 2  # Motion must appear in N consecutive frames

# Directory Settings
OUTPUT_DIR = 'output'
TEMP_DIR = 'temp'