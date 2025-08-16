from PIL import Image, ImageDraw, ImageFont
import cv2
import os
from config import OUTPUT_DIR
from motion_enhancer import MotionEnhancer
from context_manager import ContextManager

class ImageCompositor:
    def __init__(self, frame_width=600, frame_height=450):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.text_height = 25
        
        # Horizontal timeline layout - 8 frames max for better quality
        # Total width: 8 * 600px = 4800px (same as before but higher quality)
        self.grid_layouts = {
            8: (8, 1),   # 8 columns, 1 row for 8 frames (2-second windows)
        }
        
        # Initialize motion enhancer and context manager
        self.motion_enhancer = MotionEnhancer()
        self.context_manager = ContextManager()
        
    def create_composite(self, frame_sequence, output_path=None):
        frames_data = frame_sequence['frames']
        num_frames = len(frames_data)
        is_split_window = frame_sequence.get('is_split_window', False)
        sampling_fps = frame_sequence.get('sampling_fps', 4)
        start_time = frame_sequence['start_time']
        end_time = frame_sequence['end_time']
        
        # Apply motion enhancement to frames
        print(f"      Processing {num_frames} frames for motion enhancement...")
        enhanced_frames_data = self.motion_enhancer.enhance_frame_sequence(frames_data)
        
        # Get motion debug info
        motion_info = self.motion_enhancer.create_motion_debug_info(frames_data)
        print(f"      Motion analysis: {motion_info}")
        
        # Always use 8-frame layout with decimation for better image quality
        grid_cols, grid_rows = self.grid_layouts[8]
        target_frames = 8
        
        # Apply frame decimation to get exactly 8 frames
        if num_frames > 8:
            # Use decimation: take every Nth frame to get 8 frames
            decimation_factor = max(1, num_frames // 8)
            decimated_frames = []
            for i in range(0, min(num_frames, decimation_factor * 8), decimation_factor):
                if i < len(enhanced_frames_data):
                    decimated_frames.append(enhanced_frames_data[i])
            enhanced_frames_data = decimated_frames
            
            print(f"      📐 Decimation applied: {num_frames} frames → {len(enhanced_frames_data)} frames (factor: {decimation_factor})")
        
        # Pad with empty frames if needed (for cases with < 8 frames)
        while len(enhanced_frames_data) < target_frames:
            enhanced_frames_data.append(None)
        
        # Ensure exactly 8 frames
        enhanced_frames_data = enhanced_frames_data[:target_frames]
        num_frames = target_frames
        
        composite_width = grid_cols * self.frame_width
        composite_height = grid_rows * (self.frame_height + self.text_height)
        
        # Add space for horizontal timeline header
        timeline_height = 50  # Space for timeline info and frame numbers
        total_height = composite_height + timeline_height
        
        composite = Image.new('RGB', (composite_width, total_height), 'white')
        draw = ImageDraw.Draw(composite)
        
        # Load fonts
        try:
            header_font = ImageFont.truetype("arial.ttf", 16)
            frame_font = ImageFont.truetype("arial.ttf", 12)
            arrow_font = ImageFont.truetype("arial.ttf", 14)
        except:
            header_font = ImageFont.load_default()
            frame_font = ImageFont.load_default()
            arrow_font = ImageFont.load_default()
        
        # Add timeline header
        timeline_text = f"Horizontal Timeline: {start_time:.1f}s → {end_time:.1f}s"
        if is_split_window:
            timeline_text += f" (High-Motion Split)"
        timeline_text += f" | {grid_cols} frames, left-to-right progression"
        
        draw.text((10, 5), timeline_text, fill='blue', font=header_font)
        print(f"      Timeline header: '{timeline_text}'")
        
        # Draw frame numbers and progression arrows in timeline area
        frame_number_y = 25
        arrow_y = 35
        
        print(f"      Creating horizontal timeline progression:")
        print(f"         Layout: {grid_cols} frames in single row")
        print(f"         Total width: {composite_width}px")
        
        for col in range(grid_cols):
            # Calculate center of each frame column
            frame_center_x = col * self.frame_width + (self.frame_width // 2)
            
            # Draw frame number centered above each frame
            frame_label = f"#{col + 1}"
            try:
                bbox = draw.textbbox((0, 0), frame_label, font=frame_font)
                text_width = bbox[2] - bbox[0]
            except:
                text_width = len(frame_label) * 6
            
            label_x = frame_center_x - (text_width // 2)
            draw.text((label_x, frame_number_y), frame_label, fill='black', font=frame_font)
            
            # Draw progression arrow between frames (except after last frame)
            if col < grid_cols - 1:
                # Arrow positioned between current and next frame
                arrow_start_x = col * self.frame_width + self.frame_width - 15
                arrow_end_x = (col + 1) * self.frame_width + 15
                
                # Draw simple arrow line with arrowhead
                draw.line([(arrow_start_x, arrow_y), (arrow_end_x, arrow_y)], fill='red', width=2)
                
                # Draw arrowhead
                arrow_head = [
                    (arrow_end_x, arrow_y),
                    (arrow_end_x - 6, arrow_y - 3),
                    (arrow_end_x - 6, arrow_y + 3)
                ]
                draw.polygon(arrow_head, fill='red')
                
                # print(f"         Arrow {col+1}: ({arrow_start_x}, {arrow_y}) → ({arrow_end_x}, {arrow_y})")
        
        print(f"      ✅ Horizontal timeline: {grid_cols} frames with {grid_cols - 1} progression arrows")
        
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        for i in range(num_frames):
            row = i // grid_cols
            col = i % grid_cols
            
            x = col * self.frame_width
            y = row * (self.frame_height + self.text_height) + timeline_height
            
            # Handle padding (empty frames) - use enhanced frames
            if i < len(enhanced_frames_data) and enhanced_frames_data[i] is not None:
                frame_data = enhanced_frames_data[i]
                frame_cv = frame_data['frame']  # This is now motion-enhanced
                frame_rgb = cv2.cvtColor(frame_cv, cv2.COLOR_BGR2RGB)
                frame_pil = Image.fromarray(frame_rgb)
                frame_resized = frame_pil.resize((self.frame_width, self.frame_height))
                
                composite.paste(frame_resized, (x, y))
                
                # Add motion enhancement indicator to timestamp
                motion_indicator = "[M]" if frame_data.get('motion_enhanced', False) else ""
                timestamp_text = f"Frame {i+1}: {frame_data['timestamp']:.2f}s {motion_indicator}"
            else:
                # Empty frame slot
                empty_frame = Image.new('RGB', (self.frame_width, self.frame_height), 'lightgray')
                composite.paste(empty_frame, (x, y))
                timestamp_text = f"Frame {i+1}: [empty]"
            
            text_y = y + self.frame_height + 2
            draw.text((x + 5, text_y), timestamp_text, fill='black', font=font)
        
        if output_path is None:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            start_time = frame_sequence['start_time']
            end_time = frame_sequence['end_time']
            
            # Create descriptive filename with split window and motion enhancement info
            motion_suffix = "_ENHANCED" if self.motion_enhancer.enable_enhancement else ""
            
            if is_split_window:
                parent_info = frame_sequence.get('parent_window', 'unknown')
                filename = f"composite_SPLIT_{start_time:.2f}s_to_{end_time:.2f}s_from_{parent_info.replace(':', '')}{motion_suffix}.jpg"
            else:
                filename = f"composite_{start_time:.2f}s_to_{end_time:.2f}s{motion_suffix}.jpg"
            
            output_path = os.path.join(OUTPUT_DIR, filename)
        
        # Save the composite image with maximum quality to match what LLM receives
        composite.save(output_path, quality=95, optimize=False)
        
        print(f"      💾 Saved composite (motion-enhanced): {os.path.basename(output_path)}")
        
        return output_path

    def create_analysis_prompt(self, frame_sequence):
        start_time = frame_sequence['start_time']
        end_time = frame_sequence['end_time']
        num_frames = len([f for f in frame_sequence['frames'] if f is not None])
        max_frame_num = 8  # Always 8 frames now
        is_split_window = frame_sequence.get('is_split_window', False)
        sampling_fps = frame_sequence.get('sampling_fps', 4)
        
        # Get previous context for continuity
        context_addition = self.context_manager.get_context_prompt_addition()
        
        # Add context about the analysis type and motion enhancement
        motion_enhancement_note = ""
        if self.motion_enhancer.enable_enhancement:
            motion_enhancement_note = """
MOTION ENHANCEMENT: Frames have been enhanced to highlight moving areas with RED BOUNDING RECTANGLES.
Red rectangles outline areas where significant motion was detected - pay special attention to these areas as they indicate movement and potential interactions. The rectangles are visual indicators only, not actual objects in the scene."""

        analysis_context = ""
        if is_split_window:
            parent_window = frame_sequence.get('parent_window', 'unknown')
            analysis_context = f"""
HIGH-MOTION ANALYSIS: This is a detailed view of a high-motion period from {parent_window}.
This window was automatically selected for closer inspection due to intense movement.
Sampling rate: {sampling_fps} FPS (16 FPS for 1-second high-motion windows).{motion_enhancement_note}"""
        else:
            analysis_context = f"""
STANDARD ANALYSIS: Regular motion window sampled at {sampling_fps} FPS (8 FPS for 2-second windows).{motion_enhancement_note}"""

        prompt = f"""You are analyzing security camera footage from a kindergarten environment. 

{analysis_context}

{context_addition}

IMPORTANT - IMAGE FORMAT: This composite image shows 8 consecutive frames arranged in a HORIZONTAL TIMELINE from {start_time:.2f} to {end_time:.2f} seconds (2-second window for better detail).

HOW TO READ THE IMAGE:
- 8 frames arranged LEFT-TO-RIGHT in chronological order (like a comic strip)
- Frame #1 (leftmost) = earliest time, Frame #8 (rightmost) = latest time
- Each frame is numbered (#1, #2, #3, etc.) above the image
- Red arrows between frames show temporal progression →
- Each frame shows the exact timestamp below the image
- Larger frame size (600×450px) for better detail detection
- Empty/gray frames should be ignored

ANALYSIS TASK:
Examine the SEQUENCE of frames from left to right to understand how the scene develops over time.
Look for inappropriate or concerning behavior toward children across the temporal progression.

Look specifically for:
- Physical aggression or violence between individuals
- Inappropriate touching or contact between children or adults and children
- Inappropriate bodily functions or hygiene-related incidents
- Children in distressing or compromising situations
- Any behavior that would be considered inappropriate in a childcare environment
- Bullying, intimidation, or harmful interactions
- Behavioral escalation or concerning patterns across multiple frames

{"IMPORTANT: This is a high-motion sequence - pay extra attention to rapid movements and interactions between individuals as they progress left-to-right. Look for unusual positioning, gestures, or activities that develop across the timeline." if is_split_window else ""}

RESPONSE FORMAT:
Respond with a JSON object containing:
- "inappropriate_behavior_detected": true/false
- "confidence": score from 0-100
- "description": brief description of what you observed (reference specific frame numbers and timeline progression)
- "scene_context": FACTUAL scene description (2-4 sentences) including: WHO is present (number/types of people), WHAT they are doing, WHERE they are positioned, and any relevant OBJECTS or interactions. Focus on observable facts, NOT safety conclusions.
- "frames_of_concern": list of frame numbers (1-8) where concerning behavior is visible

IMPORTANT: For "scene_context", describe the actual scene content like "2 children and 1 adult near wooden table with toys" rather than conclusions like "no inappropriate behavior observed".

Be thorough but only flag clear instances of inappropriate behavior. Normal play, supervision, or appropriate childcare activities should not be flagged."""

        return prompt
    
    def process_analysis_response(self, api_response, frame_sequence):
        """Process API response and update context manager"""
        start_time = frame_sequence['start_time']
        end_time = frame_sequence['end_time']
        
        # Extract scene context from API response
        scene_context = api_response.get('scene_context', '')
        print(f"         Extracting scene_context from API response:")
        print(f"         scene_context field exists: {'scene_context' in api_response}")
        print(f"         scene_context value: '{scene_context[:100]}{'...' if len(scene_context) > 100 else ''}'" if scene_context else "         scene_context is empty")
        
        if scene_context and scene_context != "No scene context provided":
            timestamp_range = {
                'start': start_time,
                'end': end_time
            }
            self.context_manager.add_scene_context(scene_context, timestamp_range)
            print(f"         ✅ Scene context added to history")
        else:
            print(f"         ⚠️ Scene context not added (empty or default value)")
        
        return api_response
    
    def clear_context_history(self):
        """Clear context history for new video analysis"""
        self.context_manager.clear_context()

if __name__ == "__main__":
    from motion_detector import analyze_video_for_motion
    from frame_sampler import FrameSampler
    
    video_path = input("Enter video path: ")
    motion_times, fps = analyze_video_for_motion(video_path)
    
    sampler = FrameSampler()
    sequences = sampler.extract_frame_sequences(video_path, motion_times[:1])  # Test with first sequence
    
    if sequences:
        compositor = ImageCompositor()
        output_path = compositor.create_composite(sequences[0])
        print(f"Composite saved to: {output_path}")
        
        prompt = compositor.create_analysis_prompt(sequences[0])
        print(f"\nGenerated prompt:\n{prompt}")