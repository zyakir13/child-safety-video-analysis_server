import cv2
import numpy as np
from config import (
    ENABLE_MOTION_ENHANCEMENT, MOTION_HIGHLIGHT_THRESHOLD, 
    MOTION_HIGHLIGHT_COLOR, MOTION_HIGHLIGHT_INTENSITY, MOTION_CONTRAST_BOOST,
    MOTION_MIN_CONTOUR_AREA_RATIO, MOTION_PERSISTENCE_FRAMES
)

class MotionEnhancer:
    """Enhances frames by highlighting motion areas to improve AI detection of subtle behaviors"""
    
    def __init__(self, enable_enhancement=ENABLE_MOTION_ENHANCEMENT):
        self.enable_enhancement = enable_enhancement
        self.highlight_threshold = MOTION_HIGHLIGHT_THRESHOLD
        self.highlight_color = MOTION_HIGHLIGHT_COLOR
        self.highlight_intensity = MOTION_HIGHLIGHT_INTENSITY
        self.contrast_boost = MOTION_CONTRAST_BOOST
        self.min_contour_area_ratio = MOTION_MIN_CONTOUR_AREA_RATIO
        self.persistence_frames = MOTION_PERSISTENCE_FRAMES
        
        # Track motion history for persistence filtering
        self.motion_history = []
        
        print(f"    Motion Enhancement: {'ENABLED' if self.enable_enhancement else 'DISABLED'}")
        if self.enable_enhancement:
            print(f"      Threshold: {self.highlight_threshold}, Min Area: {self.min_contour_area_ratio:.1%}")
            print(f"      Persistence: {self.persistence_frames} frames required for motion highlighting")
    
    def enhance_frame_sequence(self, frames_data):
        """Apply motion enhancement to a sequence of frames"""
        if not self.enable_enhancement or len(frames_data) < 2:
            return frames_data
        
        # Reset motion history for new sequence
        self.motion_history = []
        
        enhanced_frames = []
        
        print(f"       Applying motion enhancement to {len(frames_data)} frames...")
        
        # First frame has no previous frame for comparison
        enhanced_frames.append(frames_data[0])
        self.motion_history.append(None)  # No motion mask for first frame
        
        for i in range(1, len(frames_data)):
            if frames_data[i] is None:
                enhanced_frames.append(None)
                self.motion_history.append(None)
                continue
                
            current_frame = frames_data[i]['frame']
            prev_frame = frames_data[i-1]['frame'] if frames_data[i-1] is not None else current_frame
            
            # Apply motion enhancement with filtering
            enhanced_frame, motion_mask = self._enhance_single_frame_filtered(current_frame, prev_frame, i)
            
            # Store motion mask for persistence checking
            self.motion_history.append(motion_mask)
            
            # Create enhanced frame data structure
            enhanced_frame_data = frames_data[i].copy()
            enhanced_frame_data['frame'] = enhanced_frame
            enhanced_frame_data['motion_enhanced'] = motion_mask is not None and np.any(motion_mask)
            
            enhanced_frames.append(enhanced_frame_data)
        
        motion_areas_detected = sum(1 for f in enhanced_frames[1:] if f and f.get('motion_enhanced'))
        print(f"      ✨ Enhanced {motion_areas_detected} frames with filtered motion highlighting")
        
        return enhanced_frames
    
    def _enhance_single_frame(self, current_frame, prev_frame):
        """Enhance a single frame by highlighting motion areas"""
        
        # Convert to grayscale for motion detection
        curr_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate frame difference
        frame_diff = cv2.absdiff(curr_gray, prev_gray)
        
        # Apply threshold to get motion mask
        _, motion_mask = cv2.threshold(frame_diff, self.highlight_threshold, 255, cv2.THRESH_BINARY)
        
        # Morphological operations to clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, kernel)
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, kernel)
        
        # Dilate to make motion areas more prominent
        motion_mask = cv2.dilate(motion_mask, kernel, iterations=2)
        
        # Create enhanced frame
        enhanced_frame = current_frame.copy()
        
        # Apply contrast boost to motion areas
        motion_areas = motion_mask > 0
        if np.any(motion_areas):
            # Boost contrast in motion areas
            enhanced_frame[motion_areas] = np.clip(
                enhanced_frame[motion_areas] * self.contrast_boost, 0, 255
            ).astype(np.uint8)
            
            # Create colored overlay for motion areas
            overlay = np.zeros_like(current_frame)
            overlay[motion_areas] = self.highlight_color
            
            # Blend overlay with enhanced frame
            enhanced_frame = cv2.addWeighted(
                enhanced_frame, 1.0,
                overlay, self.highlight_intensity,
                0
            )
            
            # Add subtle border around motion areas
            contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(enhanced_frame, contours, -1, self.highlight_color, 2)
        
        return enhanced_frame
    
    def _enhance_single_frame_filtered(self, current_frame, prev_frame, frame_index):
        """Enhance a single frame with large motion filtering and persistence checking"""
        
        # Convert to grayscale for motion detection
        curr_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate frame difference
        frame_diff = cv2.absdiff(curr_gray, prev_gray)
        
        # Apply threshold to get motion mask
        _, motion_mask = cv2.threshold(frame_diff, self.highlight_threshold, 255, cv2.THRESH_BINARY)
        
        # Morphological operations to clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, kernel)
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, kernel)
        
        # Calculate minimum contour area based on frame size
        frame_area = current_frame.shape[0] * current_frame.shape[1]
        min_contour_area = frame_area * self.min_contour_area_ratio
        
        # Filter contours by size
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filtered_contours = [c for c in contours if cv2.contourArea(c) >= min_contour_area]
        
        # Create filtered motion mask
        filtered_motion_mask = np.zeros_like(motion_mask)
        if filtered_contours:
            cv2.fillPoly(filtered_motion_mask, filtered_contours, 255)
        
        # Apply persistence filtering
        persistent_motion_mask = self._apply_persistence_filter(filtered_motion_mask, frame_index)
        
        # If no significant persistent motion, return original frame
        if persistent_motion_mask is None or not np.any(persistent_motion_mask):
            return current_frame.copy(), None
        
        # Create enhanced frame
        enhanced_frame = current_frame.copy()
        
        # Apply subtle contrast boost to motion areas (keep minimal enhancement)
        motion_areas = persistent_motion_mask > 0
        if np.any(motion_areas):
            # Light contrast boost (reduced from previous version)
            enhanced_frame[motion_areas] = np.clip(
                enhanced_frame[motion_areas] * 1.1, 0, 255
            ).astype(np.uint8)
            
            # Draw red bounding rectangles around motion areas instead of overlays
            filtered_contours_persistent = []
            for contour in filtered_contours:
                # Check if this contour overlaps with persistent motion
                contour_mask = np.zeros_like(persistent_motion_mask)
                cv2.fillPoly(contour_mask, [contour], 255)
                if np.any(contour_mask & persistent_motion_mask):
                    filtered_contours_persistent.append(contour)
            
            # Get all bounding rectangles first
            rectangles = []
            for contour in filtered_contours_persistent:
                x, y, w, h = cv2.boundingRect(contour)
                rectangles.append([x, y, x + w, y + h])  # Store as [x1, y1, x2, y2]
            
            # Merge overlapping rectangles
            merged_rectangles = self._merge_overlapping_rectangles(rectangles)
            
            if len(rectangles) != len(merged_rectangles):
                print(f"         🔄 Rectangle merging: {len(rectangles)} → {len(merged_rectangles)} rectangles")
            
            # Draw merged red rectangles
            for x1, y1, x2, y2 in merged_rectangles:
                cv2.rectangle(enhanced_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Red color, 2px thickness
        
        return enhanced_frame, persistent_motion_mask
    
    def _merge_overlapping_rectangles(self, rectangles):
        """Merge overlapping rectangles into larger bounding boxes using Union-Find"""
        if not rectangles:
            return []
        
        n = len(rectangles)
        if n == 1:
            return rectangles
        
        # Build adjacency list of overlapping rectangles
        overlaps = [[] for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                if self._rectangles_overlap(rectangles[i], rectangles[j]):
                    overlaps[i].append(j)
                    overlaps[j].append(i)
        
        # Find connected components using DFS
        visited = [False] * n
        merged = []
        
        for i in range(n):
            if not visited[i]:
                # Start new component
                component = []
                stack = [i]
                
                while stack:
                    current = stack.pop()
                    if not visited[current]:
                        visited[current] = True
                        component.append(current)
                        
                        # Add all unvisited neighbors to stack
                        for neighbor in overlaps[current]:
                            if not visited[neighbor]:
                                stack.append(neighbor)
                
                # Create bounding box for this component
                component_rects = [rectangles[idx] for idx in component]
                min_x1 = min(rect[0] for rect in component_rects)
                min_y1 = min(rect[1] for rect in component_rects)
                max_x2 = max(rect[2] for rect in component_rects)
                max_y2 = max(rect[3] for rect in component_rects)
                
                merged.append([min_x1, min_y1, max_x2, max_y2])
        
        return merged
    
    def _rectangles_overlap(self, rect1, rect2):
        """Check if two rectangles overlap (format: [x1, y1, x2, y2])"""
        x1_1, y1_1, x2_1, y2_1 = rect1
        x1_2, y1_2, x2_2, y2_2 = rect2
        
        # Rectangles don't overlap if one is completely to the left, right, above, or below the other
        if x2_1 <= x1_2 or x2_2 <= x1_1 or y2_1 <= y1_2 or y2_2 <= y1_1:
            return False
        
        return True
    
    def _apply_persistence_filter(self, motion_mask, frame_index):
        """Apply persistence filtering - motion must appear in consecutive frames"""
        
        if frame_index < self.persistence_frames:
            # Not enough frames for persistence check yet
            return motion_mask
        
        # Check if motion persists across required number of frames
        if len(self.motion_history) < self.persistence_frames:
            return motion_mask
        
        # Look at the last N frames (including current)
        recent_masks = self.motion_history[-(self.persistence_frames-1):] + [motion_mask]
        
        # Motion must appear in all recent frames to be considered persistent
        persistent_mask = np.ones_like(motion_mask) * 255
        
        for mask in recent_masks:
            if mask is None:
                # If any frame has no motion mask, no persistence
                return None
            persistent_mask = cv2.bitwise_and(persistent_mask, mask)
        
        # Only return areas that have persisted across all frames
        return persistent_mask if np.any(persistent_mask) else None
    
    def create_motion_debug_info(self, frames_data):
        """Create debug information about motion detection"""
        if not self.enable_enhancement or len(frames_data) < 2:
            return "Motion enhancement disabled"
        
        motion_frame_count = 0
        total_motion_pixels = 0
        
        for i in range(1, len(frames_data)):
            if frames_data[i] is None or frames_data[i-1] is None:
                continue
                
            current_frame = frames_data[i]['frame']
            prev_frame = frames_data[i-1]['frame']
            
            curr_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            
            frame_diff = cv2.absdiff(curr_gray, prev_gray)
            motion_pixels = np.sum(frame_diff > self.highlight_threshold)
            
            if motion_pixels > 0:
                motion_frame_count += 1
                total_motion_pixels += motion_pixels
        
        avg_motion_pixels = total_motion_pixels / max(1, motion_frame_count)
        motion_percentage = (motion_frame_count / max(1, len(frames_data) - 1)) * 100
        
        return f"Motion in {motion_frame_count}/{len(frames_data)-1} frames ({motion_percentage:.1f}%), avg {avg_motion_pixels:.0f} pixels/frame"

if __name__ == "__main__":
    # Test motion enhancement
    enhancer = MotionEnhancer()
    print("Motion Enhancement Test - Configuration loaded successfully")