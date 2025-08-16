#!/usr/bin/env python3
"""
Child Safety Video Analysis Web Application
Run this script to start the web server
"""

import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

if __name__ == '__main__':
    print("Child Safety Video Analysis Web Application")
    print("=" * 50)
    print("Starting web server...")
    print("Access the application at: http://localhost:5000")
    print("Upload MP4 videos up to 1 minute in length")
    print("Ready for analysis - no API key required!")
    print("=" * 50)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Error starting server: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")