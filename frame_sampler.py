import cv2
import os
from config import FRAMES_PER_SECOND, ANALYSIS_WINDOW_SECONDS, TEMP_DIR

class FrameSampler:
    def __init__(self, frames_per_second=FRAMES_PER_SECOND, window_seconds=ANALYSIS_WINDOW_SECONDS):
        self.default_frames_per_second = frames_per_second
        self.window_seconds = window_seconds
    
    def extract_frame_sequences(self, video_path, analysis_windows):
        """Extract frame sequences from analysis windows with dynamic FPS support"""
        cap = cv2.VideoCapture(video_path)
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration = total_frames / video_fps
        
        print(f"   Video info: {video_fps} FPS, {total_frames} frames, {video_duration:.2f}s duration")
        
        frame_sequences = []
        windows_processed = 0
        windows_skipped_duration = 0
        windows_skipped_frames = 0
        
        print(f"    Processing {len(analysis_windows)} analysis windows from motion grouper...")
        
        for idx, window in enumerate(analysis_windows):
            sequence_start = window['start_time']
            sequence_end = window['end_time']
            window_duration = sequence_end - sequence_start
            
            # Get FPS for this window (normal or high-motion split)
            sampling_fps = window.get('sampling_fps', self.default_frames_per_second)
            frames_per_window = int(sampling_fps * window_duration)
            
            window_type = "SPLIT" if window.get('is_split_window', False) else "NORMAL"
            print(f"   Processing {window_type} window {idx+1}: {sequence_start:.2f}s to {sequence_end:.2f}s")
            print(f"      Sampling: {sampling_fps} FPS → {frames_per_window} frames")
            
            # Skip if sequence would go beyond video duration
            if sequence_end > video_duration:
                print(f"      ❌ WINDOW DROPPED: extends beyond video duration ({video_duration:.2f}s)")
                print(f"         Window: {sequence_start:.2f}s-{sequence_end:.2f}s, Video ends: {video_duration:.2f}s")
                windows_skipped_duration += 1
                continue
            
            frames = []
            
            for i in range(frames_per_window):
                timestamp = sequence_start + (i / sampling_fps)
                
                if timestamp > sequence_end:
                    break
                
                frame_number = int(timestamp * video_fps)
                
                # Check if frame number is valid
                if frame_number >= total_frames:
                    print(f"      Frame {frame_number} exceeds total frames ({total_frames})")
                    break
                
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                
                ret, frame = cap.read()
                if ret:
                    frames.append({
                        'frame': frame,
                        'timestamp': timestamp,
                        'frame_number': i
                    })
                else:
                    print(f"      Failed to read frame {frame_number} at timestamp {timestamp:.2f}s")
            
            print(f"      Extracted {len(frames)} frames (target: {frames_per_window})")
            
            # Allow tolerance for frame extraction
            min_required_frames = max(8, int(frames_per_window * 0.9))
            if len(frames) >= min_required_frames:
                # Copy window metadata to frame sequence
                frame_sequence = {
                    'start_time': sequence_start,
                    'end_time': sequence_end,
                    'frames': frames,
                    'sampling_fps': sampling_fps,
                    'is_split_window': window.get('is_split_window', False),
                    'motion_intensity': window.get('motion_intensity', 0),
                    'parent_window': window.get('parent_window', None)
                }
                frame_sequences.append(frame_sequence)
                windows_processed += 1
                print(f"      ✅ WINDOW ACCEPTED: Valid sequence created ({len(frames)} frames)")
            else:
                print(f"      ❌ WINDOW DROPPED: Insufficient frames extracted")
                print(f"         Got: {len(frames)}/{frames_per_window} frames, Required: {min_required_frames}+ frames")
                print(f"         Sampling: {sampling_fps} FPS over {window_duration:.2f}s window")
                print(f"         Window: {sequence_start:.2f}s-{sequence_end:.2f}s")
                windows_skipped_frames += 1
        
        cap.release()
        
        # Comprehensive window tracking summary
        total_windows = len(analysis_windows)
        print(f"    FRAME SAMPLER SUMMARY:")
        print(f"      Input windows from motion grouper: {total_windows}")
        print(f"      ✅ Windows successfully processed: {windows_processed}")
        print(f"      ❌ Windows dropped (duration): {windows_skipped_duration}")
        print(f"      ❌ Windows dropped (frames): {windows_skipped_frames}")
        print(f"       Success rate: {windows_processed}/{total_windows} ({100*windows_processed/max(1,total_windows):.1f}%)")
        
        if windows_skipped_duration > 0 or windows_skipped_frames > 0:
            print(f"      ⚠️ WARNING: {windows_skipped_duration + windows_skipped_frames} windows were dropped!")
        
        return frame_sequences

    def save_frames(self, frame_sequence, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
        start_time = frame_sequence['start_time']
        saved_paths = []
        
        for frame_data in frame_sequence['frames']:
            filename = f"frame_{start_time:.2f}_{frame_data['frame_number']}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            cv2.imwrite(filepath, frame_data['frame'])
            saved_paths.append(filepath)
        
        return saved_paths

if __name__ == "__main__":
    from motion_detector import analyze_video_for_motion
    
    video_path = input("Enter video path: ")
    motion_times, fps = analyze_video_for_motion(video_path)
    
    sampler = FrameSampler()
    sequences = sampler.extract_frame_sequences(video_path, motion_times[:5])  # Test with first 5
    
    for i, seq in enumerate(sequences):
        print(f"Sequence {i+1}: {len(seq['frames'])} frames from {seq['start_time']:.2f}s")