import cv2
import numpy as np
from config import MOTION_THRESHOLD

class MotionDetector:
    def __init__(self, threshold=MOTION_THRESHOLD):
        self.threshold = threshold
        self.prev_frame = None
    
    def detect_motion(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self.prev_frame is None:
            self.prev_frame = gray
            return False
        
        frame_diff = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        motion_area = cv2.countNonZero(thresh)
        total_pixels = frame.shape[0] * frame.shape[1]
        motion_percentage = (motion_area / total_pixels) * 100
        
        motion_detected = motion_percentage > self.threshold
        
        self.prev_frame = gray
        
        return motion_detected

def analyze_video_for_motion(video_path):
    cap = cv2.VideoCapture(video_path)
    detector = MotionDetector()
    
    motion_periods = []
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"   Analyzing {total_frames} frames at {fps:.1f} FPS (threshold: {detector.threshold}%)")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        timestamp = frame_count / fps
        
        # Show progress every 150 frames (about 5 seconds)
        if frame_count % 150 == 0:
            print(f"   Processing... {frame_count}/{total_frames} frames ({timestamp:.1f}s)")
        
        has_motion = detector.detect_motion(frame)
        
        if has_motion:
            motion_periods.append(timestamp)
        
        frame_count += 1
    
    cap.release()
    
    print(f"    Total motion events found: {len(motion_periods)}")
    print(f"    First 10 timestamps: {motion_periods[:10]}{'...' if len(motion_periods) > 10 else ''}")
    
    return motion_periods, fps

if __name__ == "__main__":
    video_path = input("Enter video file path: ")
    periods, fps = analyze_video_for_motion(video_path)
    print(f"Motion detected at timestamps: {periods[:10]}...")  # Show first 10