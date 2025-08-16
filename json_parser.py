import json
import re

class RobustJSONParser:
    """Handles various JSON response formats from ChatGPT API"""
    
    @staticmethod
    def extract_and_parse_json(response_text):
        """Extract JSON from markdown code blocks and parse it"""
        
        if not response_text or not isinstance(response_text, str):
            return None
        
        # Clean the response text
        cleaned_text = response_text.strip()
        
        # Method 1: Try direct JSON parsing first
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            pass
        
        # Method 2: Extract from markdown code blocks
        # Pattern for ```json ... ``` blocks
        json_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        matches = re.findall(json_block_pattern, cleaned_text, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            try:
                cleaned_json = match.strip()
                return json.loads(cleaned_json)
            except json.JSONDecodeError:
                continue
        
        # Method 3: Look for JSON-like structure without code blocks
        # Find content between first { and last }
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, cleaned_text, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Method 4: Extract key-value pairs manually as fallback
        fallback_result = RobustJSONParser._extract_fallback_fields(cleaned_text)
        if fallback_result:
            return fallback_result
        
        return None
    
    @staticmethod
    def _extract_fallback_fields(text):
        """Extract key fields using regex as last resort"""
        
        # Default structure
        result = {
            "violence_detected": False,
            "confidence": 0,
            "description": "Failed to parse response",
            "frames_of_concern": []
        }
        
        # Try to extract violence_detected
        violence_match = re.search(r'"violence_detected"?\s*:\s*(true|false)', text, re.IGNORECASE)
        if violence_match:
            result["violence_detected"] = violence_match.group(1).lower() == "true"
        
        # Try to extract confidence
        confidence_match = re.search(r'"confidence"?\s*:\s*(\d+)', text)
        if confidence_match:
            result["confidence"] = int(confidence_match.group(1))
        
        # Try to extract description
        desc_match = re.search(r'"description"?\s*:\s*"([^"]*)"', text, re.DOTALL)
        if desc_match:
            result["description"] = desc_match.group(1)
        
        # Try to extract frames_of_concern
        frames_match = re.search(r'"frames_of_concern"?\s*:\s*\[([\d,\s]*)\]', text)
        if frames_match:
            try:
                frames_str = frames_match.group(1).strip()
                if frames_str:
                    result["frames_of_concern"] = [int(x.strip()) for x in frames_str.split(',') if x.strip()]
            except:
                pass
        
        return result

if __name__ == "__main__":
    # Test cases
    test_cases = [
        # Case 1: Clean JSON
        '{"violence_detected": true, "confidence": 85, "description": "Test", "frames_of_concern": [1,2]}',
        
        # Case 2: Markdown wrapped
        '```json\n{"violence_detected": false, "confidence": 95, "description": "No violence", "frames_of_concern": []}\n```',
        
        # Case 3: Your problematic case
        '```json\n{\n  "violence_detected": false,\n  "confidence": 95,\n  "description": "The frames show an adult near a dog, not children.",\n  "frames_of_concern": []\n}\n```',
        
        # Case 4: Broken JSON
        'The analysis shows: violence_detected: false, confidence: 90'
    ]
    
    parser = RobustJSONParser()
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}:")
        print(f"Input: {test[:50]}...")
        result = parser.extract_and_parse_json(test)
        print(f"Output: {result}")