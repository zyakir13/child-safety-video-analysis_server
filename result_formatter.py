import json
import os
from datetime import datetime
from config import OUTPUT_DIR

class ResultFormatter:
    def __init__(self):
        self.results = {
            "analysis_metadata": {
                "timestamp": datetime.now().isoformat(),
                "video_path": "",
                "total_sequences_analyzed": 0,
                "violence_incidents_found": 0
            },
            "incidents": [],
            "summary": {
                "violence_detected": False,
                "highest_confidence": 0,
                "time_ranges_with_violence": []
            }
        }
    
    def add_analysis_result(self, frame_sequence, api_response, composite_image_path=None):
        start_time = frame_sequence['start_time']
        end_time = frame_sequence['end_time']
        
        incident = {
            "time_range": {
                "start_seconds": start_time,
                "end_seconds": end_time,
                "start_formatted": f"{int(start_time//60)}:{int(start_time%60):02d}",
                "end_formatted": f"{int(end_time//60)}:{int(end_time%60):02d}"
            },
            "inappropriate_behavior_detected": api_response.get("inappropriate_behavior_detected", False),
            "confidence_percentage": api_response.get("confidence", 0),
            "description": api_response.get("description", "No description provided"),
            "scene_context": api_response.get("scene_context", "No scene context provided"),
            "frames_of_concern": api_response.get("frames_of_concern", []),
            "composite_image_path": composite_image_path,
            "frames_analyzed": len(frame_sequence['frames']),
            "full_api_response": api_response
        }
        
        self.results["incidents"].append(incident)
        self.results["analysis_metadata"]["total_sequences_analyzed"] += 1
        
        if api_response.get("inappropriate_behavior_detected", False):
            self.results["analysis_metadata"]["violence_incidents_found"] += 1
            self.results["summary"]["violence_detected"] = True
            
            time_range = f"{incident['time_range']['start_formatted']}-{incident['time_range']['end_formatted']}"
            self.results["summary"]["time_ranges_with_violence"].append(time_range)
        
        confidence = api_response.get("confidence", 0)
        if confidence > self.results["summary"]["highest_confidence"]:
            self.results["summary"]["highest_confidence"] = confidence
    
    def set_video_metadata(self, video_path):
        self.results["analysis_metadata"]["video_path"] = os.path.basename(video_path)
    
    def get_json_output(self):
        return json.dumps(self.results, indent=2)
    
    def save_results(self, output_path=None):
        if output_path is None:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(OUTPUT_DIR, f"analysis_results_{timestamp}.json")
        
        with open(output_path, 'w') as f:
            f.write(self.get_json_output())
        
        return output_path
    
    def get_summary_text(self):
        summary = self.results["summary"]
        metadata = self.results["analysis_metadata"]
        
        if summary["violence_detected"]:
            text = f"⚠️ VIOLENCE DETECTED in {metadata['violence_incidents_found']} out of {metadata['total_sequences_analyzed']} analyzed sequences.\n"
            text += f"Highest confidence: {summary['highest_confidence']}%\n"
            text += f"Time ranges with violence: {', '.join(summary['time_ranges_with_violence'])}"
        else:
            text = f"✅ No violence detected in {metadata['total_sequences_analyzed']} analyzed sequences."
        
        return text

if __name__ == "__main__":
    formatter = ResultFormatter()
    formatter.set_video_metadata("test_video.mp4")
    
    # Test with dummy data
    test_sequence = {
        'start_time': 10.5,
        'end_time': 14.5,
        'frames': [{}] * 8
    }
    
    test_response = {
        "violence_detected": True,
        "confidence": 85,
        "description": "Test incident",
        "frames_of_concern": [3, 4]
    }
    
    formatter.add_analysis_result(test_sequence, test_response)
    print(formatter.get_summary_text())
    print("\nFull JSON:")
    print(formatter.get_json_output())