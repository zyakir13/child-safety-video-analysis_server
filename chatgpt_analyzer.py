import base64
import json
import os
from openai import OpenAI
from config import OPENAI_API_KEY
from json_parser import RobustJSONParser

class ChatGPTAnalyzer:
    def __init__(self, api_key=None):
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        self.client = OpenAI(api_key=self.api_key)
    
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def analyze_composite_image(self, image_path, prompt):
        """Analyze composite image with ChatGPT Vision API
        
        Note: The saved image at image_path is EXACTLY what gets sent to the LLM.
        This ensures perfect debugging alignment between local files and API calls.
        """
        try:
            # Encode the exact same image that was saved locally
            base64_image = self.encode_image(image_path)
            
            print(f"         Sending to ChatGPT: {os.path.basename(image_path)}")
            print(f"         Prompt includes scene_context field requirement: {'scene_context' in prompt}")
            
            # Sample logging: Print complete prompt for random API calls to verify context chaining
            # import random
            # if random.random() < 0.3:  # 30% chance to log full prompt
            #     print(f"\n" + "="*80)
            #     print(f"🔍 SAMPLE API CALL - COMPLETE PROMPT TEXT:")
            #     print(f"="*80)
            #     print(prompt)
            #     print(f"="*80)
            #     print(f"END SAMPLE PROMPT\n")
            
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            print(f"         📄 GPT Response length: {len(result_text)} chars")
            
            # Use robust JSON parser to handle markdown code blocks
            parsed_json = RobustJSONParser.extract_and_parse_json(result_text)
            
            if parsed_json:
                print(f"         JSON parsed successfully, fields: {list(parsed_json.keys())}")
                
                # Check for scene_context field specifically
                scene_context_present = "scene_context" in parsed_json
                scene_context_value = parsed_json.get("scene_context", "")
                print(f"         scene_context field present: {scene_context_present}")
                if scene_context_present:
                    print(f"          scene_context value: '{scene_context_value[:100]}{'...' if len(scene_context_value) > 100 else ''}'")
                
                # Ensure all required fields are present with correct field names
                return {
                    "inappropriate_behavior_detected": parsed_json.get("inappropriate_behavior_detected", False),
                    "confidence": parsed_json.get("confidence", 0),
                    "description": parsed_json.get("description", "No description provided"),
                    "scene_context": parsed_json.get("scene_context", "No scene context provided"),
                    "frames_of_concern": parsed_json.get("frames_of_concern", []),
                    "raw_response": result_text
                }
            else:
                print(f"         ❌ JSON parsing failed for response: {result_text[:200]}...")
                return {
                    "inappropriate_behavior_detected": False,
                    "confidence": 0,
                    "description": f"Failed to parse response: {result_text}",
                    "scene_context": "JSON parsing failed",
                    "frames_of_concern": [],
                    "raw_response": result_text,
                    "parsing_error": True
                }
                
        except Exception as e:
            print(f"         ❌ API Error: {str(e)}")
            return {
                "inappropriate_behavior_detected": False,
                "confidence": 0,
                "description": f"API error: {str(e)}",
                "scene_context": "API error occurred",
                "frames_of_concern": [],
                "error": str(e)
            }

if __name__ == "__main__":
    import os
    
    api_key = input("Enter OpenAI API key: ")
    image_path = input("Enter composite image path: ")
    
    if not os.path.exists(image_path):
        print("Image file not found")
        exit()
    
    analyzer = ChatGPTAnalyzer(api_key)
    
    test_prompt = """Analyze this composite image of 8 video frames and look for any violence toward children. 
    Respond with JSON: {"violence_detected": boolean, "confidence": 0-100, "description": "brief text", "frames_of_concern": [frame_numbers]}"""
    
    result = analyzer.analyze_composite_image(image_path, test_prompt)
    print(json.dumps(result, indent=2))