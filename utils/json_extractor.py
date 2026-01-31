# utils/json_extractor.py - WITH PYDANTIC
# Replace your current json_extractor.py

import json
import re
from typing import Optional
from pydantic import ValidationError

# Import Pydantic models
try:
    from models.appliance import ApplianceExtracted
    USE_PYDANTIC = True
except ImportError:
    USE_PYDANTIC = False
    print("⚠️  Pydantic models not found, using dict validation")

def extract_json(text):
    """
    Extract JSON data from LLM response between markers
    
    With Pydantic: Returns validated ApplianceExtracted object or None
    Without Pydantic: Returns dict or None
    """
    if not text:
        return None
    
    # Find JSON between markers
    pattern = r'\[JSON_DATA_START\](.*?)\[JSON_DATA_END\]'
    matches = re.findall(pattern, text, re.DOTALL)
    
    if not matches:
        return None
    
    try:
        # Parse JSON string
        json_str = matches[0].strip()
        data_dict = json.loads(json_str)
        
        if USE_PYDANTIC:
            # Validate with Pydantic
            try:
                validated = ApplianceExtracted(**data_dict)
                print("✓ Pydantic validation passed")
                return validated.model_dump()  # Return as dict for compatibility
                
            except ValidationError as e:
                print(f"⚠️  Pydantic validation errors:")
                for error in e.errors():
                    field = '.'.join(str(x) for x in error['loc'])
                    msg = error['msg']
                    print(f"   • {field}: {msg}")
                
                # Return dict anyway (lenient mode)
                print("   Continuing with unvalidated data...")
                return data_dict
        else:
            # No Pydantic - return raw dict
            return data_dict
        
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        return None

def extract_json_strict(text):
    """
    Strict version - raises exception if validation fails
    Use this when you want to reject invalid data
    """
    if not text:
        raise ValueError("No text provided")
    
    pattern = r'\[JSON_DATA_START\](.*?)\[JSON_DATA_END\]'
    matches = re.findall(pattern, text, re.DOTALL)
    
    if not matches:
        raise ValueError("No JSON markers found")
    
    json_str = matches[0].strip()
    data_dict = json.loads(json_str)
    
    if USE_PYDANTIC:
        # Validate and return Pydantic object
        validated = ApplianceExtracted(**data_dict)
        return validated.model_dump()
    else:
        return data_dict