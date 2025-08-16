#!/usr/bin/env python3
import os
import uuid
import json
import time
import threading
import sys
import io
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import cv2

# Fix Unicode encoding issues on Windows
import builtins
# Store original print function
_original_print = builtins.print

def safe_print(*args, **kwargs):
    """Safe print function that handles Unicode encoding errors"""
    try:
        _original_print(*args, **kwargs)
    except UnicodeEncodeError:
        # Replace problematic characters and print without emojis
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                # Remove all emoji/Unicode characters outside basic ASCII
                safe_arg = ''.join(char for char in arg if ord(char) < 127)
                safe_args.append(safe_arg)
            else:
                safe_args.append(arg)
        _original_print(*safe_args, **kwargs)

# Override built-in print function for all imported modules
builtins.print = safe_print

# Import existing analysis modules AFTER print override
from motion_detector import analyze_video_for_motion
from motion_grouper import MotionGrouper
from frame_sampler import FrameSampler
from image_compositor import ImageCompositor
from chatgpt_analyzer import ChatGPTAnalyzer
from result_formatter import ResultFormatter

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024  # 3MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/results', exist_ok=True)

# Global storage for job progress and results
jobs = {}

# Get OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

class VideoAnalysisJob:
    def __init__(self, job_id, video_path):
        self.job_id = job_id
        self.video_path = video_path
        self.api_key = OPENAI_API_KEY
        self.status = 'pending'
        self.progress = 0
        self.current_step = 'Initializing...'
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        
    def update_progress(self, progress, step):
        self.progress = progress
        self.current_step = step
        print(f"Job {self.job_id}: {progress}% - {step}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'mp4'

def get_video_duration(video_path):
    """Get video duration in seconds"""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frame_count / fps
    cap.release()
    return duration

def trim_video_to_duration(input_path, output_path, max_duration=60):
    """Trim video to specified duration using OpenCV"""
    try:
        cap = cv2.VideoCapture(input_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Define codec and create VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        max_frames = int(fps * max_duration)
        frame_count = 0
        
        while frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            out.write(frame)
            frame_count += 1
        
        cap.release()
        out.release()
        
        return True
    except Exception as e:
        _original_print(f"Error trimming video: {str(e)}")
        return False

def process_video_analysis(job):
    """Background video analysis processing"""
    try:
        job.status = 'processing'
        job.update_progress(5, 'Starting motion detection...')
        
        # Step 1: Motion Detection
        motion_timestamps, fps = analyze_video_for_motion(job.video_path)
        job.update_progress(25, f'Found {len(motion_timestamps)} motion events')
        
        if not motion_timestamps:
            job.status = 'completed'
            job.result = {
                'violence_detected': False,
                'message': 'No motion detected in video',
                'incidents': []
            }
            return
        
        # Step 2: Motion Grouping
        job.update_progress(35, 'Grouping motion into analysis windows...')
        
        # Get video duration for window creation
        cap = cv2.VideoCapture(job.video_path)
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration = total_frames / video_fps
        cap.release()
        
        grouper = MotionGrouper()
        motion_segments = grouper.group_motion_timestamps(motion_timestamps)
        analysis_windows = grouper.create_analysis_windows(motion_segments, video_duration, motion_timestamps)
        
        if not analysis_windows:
            job.status = 'completed'
            job.result = {
                'violence_detected': False,
                'message': 'No valid analysis windows found',
                'incidents': []
            }
            return
        
        job.update_progress(45, f'Created {len(analysis_windows)} analysis windows')
        
        # Step 3: Frame Sampling
        job.update_progress(55, 'Extracting frame sequences...')
        sampler = FrameSampler()
        frame_sequences = sampler.extract_frame_sequences(job.video_path, analysis_windows)
        
        if not frame_sequences:
            job.status = 'completed'
            job.result = {
                'violence_detected': False,
                'message': 'No valid frame sequences found',
                'incidents': []
            }
            return
        
        job.update_progress(65, f'Processing {len(frame_sequences)} sequences...')
        
        # Step 4: AI Analysis
        compositor = ImageCompositor()
        analyzer = ChatGPTAnalyzer(job.api_key)
        formatter = ResultFormatter()
        formatter.set_video_metadata(job.video_path)
        
        compositor.clear_context_history()
        
        sequences_processed = 0
        total_sequences = len(frame_sequences)
        
        for i, sequence in enumerate(frame_sequences):
            progress = 65 + (30 * (i + 1) / total_sequences)
            job.update_progress(int(progress), f'Analyzing sequence {i+1}/{total_sequences}...')
            
            try:
                # Create composite image
                composite_path = compositor.create_composite(sequence)
                
                # Generate analysis prompt
                prompt = compositor.create_analysis_prompt(sequence)
                
                # Analyze with ChatGPT
                api_response = analyzer.analyze_composite_image(composite_path, prompt)
                
                # Process response and update context
                api_response = compositor.process_analysis_response(api_response, sequence)
                
                # Add to results
                formatter.add_analysis_result(sequence, api_response, composite_path)
                
                sequences_processed += 1
                
            except Exception as e:
                print(f"Error processing sequence {i+1}: {str(e)}")
                continue
        
        job.update_progress(95, 'Generating final results...')
        
        # Generate results
        results_data = formatter.results
        
        # Copy composite images to web-accessible location
        web_images = []
        for incident in results_data['incidents']:
            if incident.get('composite_image_path'):
                original_path = incident['composite_image_path']
                if os.path.exists(original_path):
                    filename = f"{job.job_id}_{os.path.basename(original_path)}"
                    web_path = os.path.join('static/results', filename)
                    
                    # Copy image to web directory
                    import shutil
                    shutil.copy2(original_path, web_path)
                    
                    # Update path for web access
                    incident['web_image_path'] = f'/static/results/{filename}'
                    web_images.append(web_path)
        
        job.update_progress(100, 'Analysis complete!')
        job.status = 'completed'
        job.result = results_data
        
    except Exception as e:
        job.status = 'error'
        job.error = str(e)
        print(f"Job {job.job_id} failed: {str(e)}")
    
    finally:
        # Cleanup original video file
        try:
            if os.path.exists(job.video_path):
                os.remove(job.video_path)
        except:
            pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only MP4 files are allowed'}), 400
    
    # Check file size (additional validation beyond Flask's MAX_CONTENT_LENGTH)
    file.seek(0, 2)  # Seek to end of file
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if file_size > 3 * 1024 * 1024:  # 3MB
        return jsonify({'error': 'File size must be less than 3MB to prevent memory issues'}), 400
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    filename = f"{job_id}_{secure_filename(file.filename)}"
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Save uploaded file
    file.save(video_path)
    
    # Validate video duration
    try:
        duration = get_video_duration(video_path)
        if duration > 60:  # 1 minute limit
            # Instead of rejecting, offer trimming option
            return jsonify({
                'needs_trimming': True,
                'original_duration': duration,
                'message': f'Video is {duration:.1f} seconds long. Would you like to analyze the first 60 seconds?',
                'temp_video_path': video_path,
                'job_id': job_id
            }), 200
    except Exception as e:
        os.remove(video_path)
        return jsonify({'error': 'Invalid video file'}), 400
    
    # Create job
    job = VideoAnalysisJob(job_id, video_path)
    jobs[job_id] = job
    
    # Start background processing
    thread = threading.Thread(target=process_video_analysis, args=(job,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'message': 'Video uploaded successfully. Processing started.',
        'duration': duration
    })

@app.route('/trim-and-analyze', methods=['POST'])
def trim_and_analyze():
    """Trim video to 60 seconds and start analysis"""
    data = request.get_json()
    
    if not data or 'job_id' not in data or 'temp_video_path' not in data:
        return jsonify({'error': 'Missing required data'}), 400
    
    job_id = data['job_id']
    temp_video_path = data['temp_video_path']
    
    # Verify temp video file exists
    if not os.path.exists(temp_video_path):
        return jsonify({'error': 'Temporary video file not found'}), 400
    
    # Create trimmed video path
    trimmed_filename = f"{job_id}_trimmed.mp4"
    trimmed_video_path = os.path.join(app.config['UPLOAD_FOLDER'], trimmed_filename)
    
    # Trim the video to 60 seconds
    try:
        success = trim_video_to_duration(temp_video_path, trimmed_video_path, 60)
        if not success:
            # Clean up
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
            return jsonify({'error': 'Failed to trim video'}), 500
        
        # Remove original long video
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        
        # Verify trimmed video duration
        trimmed_duration = get_video_duration(trimmed_video_path)
        
        # Create job with trimmed video
        job = VideoAnalysisJob(job_id, trimmed_video_path)
        jobs[job_id] = job
        
        # Start background processing
        thread = threading.Thread(target=process_video_analysis, args=(job,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'message': f'Video trimmed to {trimmed_duration:.1f} seconds. Analysis started.',
            'trimmed_duration': trimmed_duration
        })
        
    except Exception as e:
        # Clean up on error
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if os.path.exists(trimmed_video_path):
            os.remove(trimmed_video_path)
        return jsonify({'error': f'Error processing video: {str(e)}'}), 500

@app.route('/status/<job_id>')
def get_status(job_id):
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    
    response = {
        'job_id': job_id,
        'status': job.status,
        'progress': job.progress,
        'current_step': job.current_step,
        'created_at': job.created_at.isoformat()
    }
    
    if job.status == 'completed' and job.result:
        response['result'] = job.result
    elif job.status == 'error' and job.error:
        response['error'] = job.error
    
    return jsonify(response)

@app.route('/static/results/<filename>')
def serve_result_image(filename):
    return send_from_directory('static/results', filename)

@app.route('/cleanup/<job_id>', methods=['POST'])
def cleanup_job(job_id):
    """Clean up job data and associated files"""
    if job_id in jobs:
        job = jobs[job_id]
        
        # Remove result images
        try:
            if job.result and job.result.get('incidents'):
                for incident in job.result['incidents']:
                    if incident.get('web_image_path'):
                        file_path = incident['web_image_path'].replace('/static/results/', 'static/results/')
                        if os.path.exists(file_path):
                            os.remove(file_path)
        except:
            pass
        
        # Remove job from memory
        del jobs[job_id]
        
        return jsonify({'message': 'Job cleaned up successfully'})
    
    return jsonify({'error': 'Job not found'}), 404

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)