# utils/json_extractor.py - SUPPORTS MULTIPLE JSONs
# Replace your current json_extractor.py

import json
import re
from typing import Optional, List
from pydantic import ValidationError

# Import Pydantic models if available
try:
    from models.appliance import ApplianceExtracted
    USE_PYDANTIC = True
except ImportError:
    USE_PYDANTIC = False

def extract_json(text):
    """
    Extract FIRST JSON block (legacy function - kept for compatibility)
    """
    all_jsons = extract_all_json(text)
    return all_jsons[0] if all_jsons else None

def extract_all_json(text):
    """
    Extract ALL JSON blocks from LLM response
    
    Returns:
        list: List of appliance dicts (empty list if none found)
    """
    if not text:
        return []
    
    # Find ALL JSON blocks between markers
    pattern = r'\[JSON_DATA_START\](.*?)\[JSON_DATA_END\]'
    matches = re.findall(pattern, text, re.DOTALL)
    
    if not matches:
        return []
    
    appliances = []
    
    for i, match in enumerate(matches, 1):
        try:
            # Parse JSON string
            json_str = match.strip()
            data_dict = json.loads(json_str)
            
            if USE_PYDANTIC:
                # Validate with Pydantic
                try:
                    validated = ApplianceExtracted(**data_dict)
                    print(f"✓ Pydantic validation passed (appliance {i}/{len(matches)})")
                    appliances.append(validated.model_dump())
                    
                except ValidationError as e:
                    print(f"⚠️  Pydantic validation errors (appliance {i}):")
                    for error in e.errors():
                        field = '.'.join(str(x) for x in error['loc'])
                        msg = error['msg']
                        print(f"   • {field}: {msg}")
                    
                    # Still include it (lenient mode)
                    print("   Continuing with unvalidated data...")
                    appliances.append(data_dict)
            else:
                # No Pydantic - return raw dict
                appliances.append(data_dict)
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parse error (block {i}): {e}")
            continue
        except Exception as e:
            print(f"⚠️  Unexpected error (block {i}): {e}")
            continue
    
    return appliances