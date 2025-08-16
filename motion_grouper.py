from config import (
    ANALYSIS_WINDOW_SECONDS, MOTION_GAP_THRESHOLD, MINIMUM_MOTION_DENSITY,
    HIGH_MOTION_THRESHOLD, HIGH_MOTION_SPLIT_WINDOW_SIZE, HIGH_MOTION_SPLIT_FPS,
    FRAMES_PER_SECOND
)

class MotionGrouper:
    def __init__(self, gap_threshold=MOTION_GAP_THRESHOLD, window_seconds=ANALYSIS_WINDOW_SECONDS, min_motion_density=MINIMUM_MOTION_DENSITY):
        self.gap_threshold = gap_threshold
        self.window_seconds = window_seconds
        self.min_motion_density = min_motion_density
        self.min_motion_seconds = window_seconds * min_motion_density
        
        # High-motion splitting configuration
        self.high_motion_threshold = HIGH_MOTION_THRESHOLD
        self.split_window_size = HIGH_MOTION_SPLIT_WINDOW_SIZE
        self.split_fps = HIGH_MOTION_SPLIT_FPS
    
    def group_motion_timestamps(self, motion_timestamps):
        if not motion_timestamps:
            return []
        
        print(f"   Grouping {len(motion_timestamps)} motion timestamps...")
        print(f"   Gap threshold: {self.gap_threshold}s, Window size: {self.window_seconds}s")
        
        # Sort timestamps
        timestamps = sorted(motion_timestamps)
        
        # Group consecutive timestamps into segments
        segments = []
        current_segment_start = timestamps[0]
        current_segment_end = timestamps[0]
        
        for timestamp in timestamps[1:]:
            if timestamp - current_segment_end <= self.gap_threshold:
                # Extend current segment
                current_segment_end = timestamp
            else:
                # Start new segment
                segments.append((current_segment_start, current_segment_end))
                current_segment_start = timestamp
                current_segment_end = timestamp
        
        # Add the last segment
        segments.append((current_segment_start, current_segment_end))
        
        print(f"    Motion segments found: {len(segments)}")
        for i, (start, end) in enumerate(segments):
            duration = end - start
            print(f"      Segment {i+1}: {start:.2f}s to {end:.2f}s (duration: {duration:.2f}s)")
        
        return segments
    
    def create_analysis_windows(self, motion_segments, video_duration, motion_timestamps=None):
        """Create non-overlapping analysis windows based on motion density"""
        analysis_windows = []
        
        print(f"   🪟 Creating {self.window_seconds}s windows (need {self.min_motion_seconds:.1f}s motion each)...")
        
        if motion_timestamps is None:
            print("   ⚠️ No motion timestamps provided, falling back to segment-based analysis")
            return self._create_windows_from_segments(motion_segments, video_duration)
        
        motion_timestamps = sorted(motion_timestamps)
        
        # Create candidate windows across entire video timeline
        processed_time = 0.0
        window_id = 1
        
        while processed_time + self.window_seconds <= video_duration:
            window_start = processed_time
            window_end = window_start + self.window_seconds
            
            # Calculate motion density in this window
            motion_in_window = [
                t for t in motion_timestamps 
                if window_start <= t <= window_end
            ]
            
            # Each motion timestamp represents a detected motion event
            # Estimate motion duration based on motion event count
            motion_count = len(motion_in_window)
            estimated_motion_duration = min(motion_count * 0.1, self.window_seconds)  # ~0.1s per motion event
            motion_density = estimated_motion_duration / self.window_seconds
            
            # Calculate motion intensity (events per second)
            motion_intensity = motion_count / self.window_seconds
            
            print(f"   Window {window_id}: {window_start:.2f}s-{window_end:.2f}s")
            print(f"      Motion: {estimated_motion_duration:.2f}s/{self.window_seconds}s ({motion_density:.1%}) [{motion_count} events]")
            print(f"      Intensity: {motion_intensity:.1f} events/sec (threshold: {self.high_motion_threshold})")
            
            if motion_density >= self.min_motion_density:
                # Check if this window needs high-motion splitting
                if motion_intensity >= self.high_motion_threshold:
                    print(f"      🔥 HIGH MOTION DETECTED - Splitting into {self.split_window_size}s sub-windows")
                    split_windows = self._create_split_windows(window_start, window_end, motion_timestamps)
                    analysis_windows.extend(split_windows)
                    print(f"      ⚡ Created {len(split_windows)} high-resolution sub-windows")
                else:
                    # Normal window
                    analysis_windows.append({
                        'start_time': window_start,
                        'end_time': window_end,
                        'motion_density': motion_density,
                        'motion_duration': estimated_motion_duration,
                        'motion_count': motion_count,
                        'motion_intensity': motion_intensity,
                        'is_split_window': False,
                        'sampling_fps': FRAMES_PER_SECOND  # Use config value instead of hardcoded 4
                    })
                    print(f"      ✅ Added - normal window")
            else:
                print(f"      ⏭️ Skipped - insufficient motion ({motion_density:.1%} < {self.min_motion_density:.1%})")
            
            # Advance by full window (non-overlapping)
            processed_time += self.window_seconds
            window_id += 1
        
        print(f"    Created {len(analysis_windows)} analysis windows")
        
        # Summary statistics
        normal_windows = len([w for w in analysis_windows if not w.get('is_split_window', False)])
        split_windows = len([w for w in analysis_windows if w.get('is_split_window', False)])
        
        if split_windows > 0:
            print(f"    Window breakdown: {normal_windows} normal + {split_windows} high-motion split windows")
        
        return analysis_windows
    
    def _create_split_windows(self, window_start, window_end, motion_timestamps):
        """Split a high-motion window into smaller sub-windows with higher FPS"""
        split_windows = []
        
        # Calculate number of sub-windows needed
        total_duration = window_end - window_start
        num_splits = int(total_duration / self.split_window_size)
        
        print(f"         Splitting {total_duration}s window into {num_splits} × {self.split_window_size}s sub-windows")
        
        for i in range(num_splits):
            sub_start = window_start + (i * self.split_window_size)
            sub_end = min(sub_start + self.split_window_size, window_end)
            
            # Calculate motion density for this sub-window
            sub_motion = [
                t for t in motion_timestamps 
                if sub_start <= t <= sub_end
            ]
            
            sub_motion_count = len(sub_motion)
            sub_motion_duration = min(sub_motion_count * 0.1, self.split_window_size)
            sub_motion_density = sub_motion_duration / self.split_window_size
            sub_motion_intensity = sub_motion_count / self.split_window_size
            
            split_windows.append({
                'start_time': sub_start,
                'end_time': sub_end,
                'motion_density': sub_motion_density,
                'motion_duration': sub_motion_duration,
                'motion_count': sub_motion_count,
                'motion_intensity': sub_motion_intensity,
                'is_split_window': True,
                'sampling_fps': self.split_fps,  # Higher FPS for split windows
                'parent_window': f"{window_start:.2f}s-{window_end:.2f}s"
            })
            
            print(f"         Sub-window {i+1}: {sub_start:.2f}s-{sub_end:.2f}s ({sub_motion_count} events, {self.split_fps} FPS)")
        
        return split_windows
    
    def _create_windows_from_segments(self, motion_segments, video_duration):
        """Fallback method for segment-based analysis"""
        analysis_windows = []
        
        print("   🔄 Using fallback segment-based window creation...")
        
        for i, (segment_start, segment_end) in enumerate(motion_segments):
            segment_duration = segment_end - segment_start
            
            print(f"   Processing segment {i+1}: {segment_start:.2f}s to {segment_end:.2f}s")
            
            # Skip very short segments
            if segment_duration < self.min_motion_seconds:
                print(f"      ⏭️ Skipping - too short ({segment_duration:.2f}s < {self.min_motion_seconds:.2f}s)")
                continue
            
            # Create windows within this segment
            window_start = segment_start
            segment_windows = 0
            
            while window_start + self.window_seconds <= segment_end and window_start + self.window_seconds <= video_duration:
                window_end = window_start + self.window_seconds
                
                analysis_windows.append({
                    'start_time': window_start,
                    'end_time': window_end,
                    'segment_id': i + 1,
                    'motion_density': 1.0,  # Assume full density for segments
                    'motion_duration': self.window_seconds
                })
                
                print(f"      ✅ Window: {window_start:.2f}s to {window_end:.2f}s")
                
                window_start = window_end
                segment_windows += 1
            
            print(f"       Created {segment_windows} windows for this segment")
        
        return analysis_windows

if __name__ == "__main__":
    # Test with sample data
    test_timestamps = [0.1, 0.2, 0.3, 0.5, 1.0, 1.2, 1.5, 8.0, 8.2, 8.5, 15.0, 15.3]
    test_duration = 20.0
    
    grouper = MotionGrouper()
    segments = grouper.group_motion_timestamps(test_timestamps)
    windows = grouper.create_analysis_windows(segments, test_duration)
    
    print("\nFinal analysis windows:")
    for window in windows:
        print(f"  {window['start_time']:.2f}s - {window['end_time']:.2f}s (segment {window['segment_id']})")