# Child Safety Video Analysis - Web Application

A professional web interface for analyzing video footage to detect concerning behavior in childcare environments.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd webapp
pip install -r requirements.txt
```

### 2. Start the Server
```bash
python run.py
```

### 3. Access the Application
Open your browser and go to: **http://localhost:5000**

## 📋 How to Use

### 1. **Upload Video**
- Drag & drop or select an MP4 video file (max 1 minute)
- Enter your OpenAI API key
- Click "Start Analysis"

### 2. **Monitor Progress**
- Real-time progress tracking with percentage
- Step-by-step processing indicators
- Estimated processing time

### 3. **View Results**
- Clear safety assessment (Safe/Warning/Concerning)
- Detailed incident reports with timestamps
- Evidence frames showing motion detection
- Confidence scores for each finding

## ✨ Features

- **Professional UI**: Clean, medical/security themed design
- **Real-time Processing**: Live progress updates during analysis
- **Secure Upload**: Files are processed and automatically cleaned up
- **Mobile Responsive**: Works on desktop, tablet, and mobile devices
- **Evidence Display**: Visual frames with motion highlighting
- **Detailed Reports**: Timestamp-accurate incident detection

## 🔧 Technical Details

### Backend (Flask)
- **File Upload**: Validates MP4 format and duration limits
- **Async Processing**: Background video analysis with progress tracking
- **API Integration**: Uses existing video analysis codebase
- **Auto Cleanup**: Temporary files are automatically removed

### Frontend (HTML/CSS/JS)
- **Drag & Drop**: Intuitive file upload interface
- **Progress Tracking**: Real-time status updates via polling
- **Results Display**: Professional incident reporting
- **Error Handling**: User-friendly error messages

### Integration
- **Existing Codebase**: Seamlessly integrates with the command-line analysis tools
- **GPT-4.1 API**: Latest AI model for enhanced detection
- **Motion Enhancement**: Red bounding rectangles around motion areas
- **Context Chaining**: Scene context passed between frame sequences

## 📁 File Structure

```
webapp/
├── app.py              # Flask server with API endpoints
├── run.py              # Easy startup script
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Single-page application
├── static/
│   ├── css/style.css   # Professional styling
│   ├── js/main.js      # Frontend functionality
│   ├── uploads/        # Temporary video storage
│   └── results/        # Generated evidence images
└── README.md           # This file
```

## 🛡️ Security Features

- **API Key Security**: Keys are not stored, only used for processing
- **File Validation**: Only MP4 files under 1 minute accepted
- **Auto Cleanup**: All uploaded files and results are automatically removed
- **No Data Persistence**: No video content is permanently stored

## 💰 Cost Estimation

- **Per 1-minute video**: ~$0.20-0.40 depending on motion complexity
- **Processing time**: 2-5 minutes depending on video content
- **API usage**: Transparent OpenAI API costs passed through

## 🔍 Troubleshooting

### Server Won't Start
- Check Python dependencies: `pip install -r requirements.txt`
- Ensure no other service is using port 5000
- Try different port: modify `port=5000` in `run.py`

### Upload Fails
- Verify file is MP4 format
- Check file is under 1 minute duration
- Ensure OpenAI API key is valid
- Check internet connection

### Analysis Errors
- Verify OpenAI API key has sufficient credits
- Check video file isn't corrupted
- Ensure video contains actual motion/content

## 📞 Support

For technical issues or questions about the video analysis system, refer to the main project documentation in the parent directory.