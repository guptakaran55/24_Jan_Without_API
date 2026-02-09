# utils/json_extractor.py - SUPPORTS MULTIPLE JSONs + HANDLES LLM QUIRKS
# Replace your current json_extractor.py

import json
import re
from typing import Optional, List

# Import Pydantic models if available
try:
    from models.appliance import ApplianceExtracted
    USE_PYDANTIC = True
except ImportError:
    USE_PYDANTIC = False


def clean_json_string(raw):
    """
    Clean up common LLM mistakes that produce invalid JSON.
    
    LLMs often:
    1. Wrap JSON in markdown ```json ... ``` blocks
    2. Use single quotes instead of double quotes
    3. Add trailing commas before closing braces/brackets
    4. Use True/False (Python) instead of true/false (JSON)
    5. Add comments
    """
    
    cleaned = raw.strip()
    
    # 1. Remove markdown code block wrappers (```json ... ``` or ``` ... ```)
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    cleaned = cleaned.strip()
    
    # 2. Replace single quotes with double quotes
    #    Only do this if the JSON doesn't already have double quotes for keys
    if cleaned.startswith("{") and '"' not in cleaned[:20]:
        # Likely using single quotes throughout — safe to replace
        cleaned = cleaned.replace("'", '"')
    
    # 3. Remove trailing commas before } or ]
    #    e.g., {"a": 1, "b": 2,} -> {"a": 1, "b": 2}
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    
    # 4. Remove inline comments (// ...)
    cleaned = re.sub(r'//.*?$', '', cleaned, flags=re.MULTILINE)
    
    # 5. Replace Python-style booleans with JSON-style
    cleaned = re.sub(r'\bTrue\b', 'true', cleaned)
    cleaned = re.sub(r'\bFalse\b', 'false', cleaned)
    cleaned = re.sub(r'\bNone\b', 'null', cleaned)
    
    return cleaned


def try_fix_truncated_json(raw):
    """
    Attempt to fix JSON that was truncated (cut off mid-way).
    
    This happens when the LLM hits max_output_tokens before finishing.
    Example: {"name": "TV", "power": 150, "data_complete   <-- cut off here
    
    Strategy: find the last complete key-value pair and close the object.
    """
    cleaned = clean_json_string(raw)
    
    if not cleaned.startswith("{"):
        return None
    
    # Count braces to see if it's incomplete
    open_braces = cleaned.count("{") - cleaned.count("}")
    open_brackets = cleaned.count("[") - cleaned.count("]")
    
    if open_braces == 0 and open_brackets == 0:
        # Already balanced — not truncated, but maybe other issue
        return None
    
    attempt = cleaned
    
    # Remove any trailing partial value (everything after the last comma)
    last_comma = attempt.rfind(",")
    
    if last_comma > 0:
        after_comma = attempt[last_comma + 1:].strip()
        
        # If what's after the last comma doesn't look complete, cut it off
        if not (after_comma.endswith("}") or after_comma.endswith("]") or 
                after_comma.endswith('"') or 
                (len(after_comma) > 0 and after_comma[-1:].isdigit()) or
                after_comma.endswith("true") or after_comma.endswith("false")):
            attempt = attempt[:last_comma]
    
    # Close any open brackets and braces
    attempt += "]" * open_brackets
    attempt += "}" * open_braces
    
    # Remove trailing commas that might now be before closing braces
    attempt = re.sub(r',\s*([}\]])', r'\1', attempt)
    
    try:
        parsed = json.loads(attempt)
        print(f"   ✓ Fixed truncated JSON successfully")
        return parsed
    except json.JSONDecodeError:
        return None


def try_manual_extraction(raw_text):
    """
    Last-resort extraction: use regex to pull out key fields
    even if JSON is badly malformed.
    """
    try:
        result = {}
        
        # Extract name
        name_match = re.search(r'["\']name["\']\s*:\s*["\']([^"\']+)["\']', raw_text)
        if name_match:
            result['name'] = name_match.group(1)
        else:
            return None  # Can't even find a name — give up
        
        # Extract numeric fields
        for field in ['number', 'power', 'func_time', 'num_windows', 'func_cycle', 'wd_we_type']:
            match = re.search(rf'["\']?{field}["\']?\s*:\s*(\d+)', raw_text)
            if match:
                result[field] = int(match.group(1))
        
        # Extract float fields
        for field in ['occasional_use', 'random_var_w']:
            match = re.search(rf'["\']?{field}["\']?\s*:\s*([\d.]+)', raw_text)
            if match:
                result[field] = float(match.group(1))
        
        # Extract string fields
        for field in ['fixed']:
            match = re.search(rf'["\']?{field}["\']?\s*:\s*["\']([^"\']+)["\']', raw_text)
            if match:
                result[field] = match.group(1)
        
        # Extract window arrays like [540, 1020]
        for field in ['window_1', 'window_2', 'window_3']:
            match = re.search(rf'["\']?{field}["\']?\s*:\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]', raw_text)
            if match:
                result[field] = [int(match.group(1)), int(match.group(2))]
        
        # Extract data_complete
        dc_match = re.search(r'["\']?data_complete["\']?\s*:\s*(true|false|True|False)', raw_text)
        if dc_match:
            result['data_complete'] = dc_match.group(1).lower() == 'true'
        
        # Check we have minimum required fields
        if result.get('name') and result.get('power') and result.get('func_time'):
            # Set defaults for missing fields
            result.setdefault('number', 1)
            result.setdefault('num_windows', 1)
            result.setdefault('func_cycle', 1)
            result.setdefault('fixed', 'no')
            result.setdefault('occasional_use', 1.0)
            result.setdefault('wd_we_type', 2)
            result.setdefault('data_complete', True)
            return result
        
        return None
        
    except Exception:
        return None


def extract_json(text):
    """
    Extract FIRST JSON block (legacy function - kept for compatibility)
    """
    all_jsons = extract_all_json(text)
    return all_jsons[0] if all_jsons else None


def extract_all_json(text):
    """
    Extract ALL JSON blocks from LLM response.
    
    Handles:
    - Complete JSON between [JSON_DATA_START] and [JSON_DATA_END] markers
    - Truncated JSON where [JSON_DATA_END] is missing (LLM hit token limit)
    - Markdown-wrapped JSON
    - Single quotes, trailing commas, Python booleans
    - Last-resort regex extraction from badly malformed JSON
    
    Returns:
        list: List of appliance dicts (empty list if none found)
    """
    if not text:
        return []
    
    appliances = []
    
    # ===== Strategy 1: Complete JSON blocks between markers =====
    pattern = r'\[JSON_DATA_START\](.*?)\[JSON_DATA_END\]'
    matches = re.findall(pattern, text, re.DOTALL)
    
    # ===== Strategy 2: Truncated JSON (has START marker but no END marker) =====
    if not matches:
        truncated_pattern = r'\[JSON_DATA_START\](.*?)$'
        truncated_matches = re.findall(truncated_pattern, text, re.DOTALL)
        if truncated_matches:
            print("⚠️  JSON block appears truncated (no [JSON_DATA_END] found)")
            for raw in truncated_matches:
                raw = raw.strip()
                if raw:
                    # Try to fix and parse the truncated JSON
                    fixed = try_fix_truncated_json(raw)
                    if fixed:
                        appliances.append(fixed)
                    else:
                        # Fall back to manual extraction
                        manual = try_manual_extraction(raw)
                        if manual:
                            print(f"   ✓ Manual extraction recovered: {manual.get('name', '?')}")
                            appliances.append(manual)
    
    # ===== Strategy 3: No markers at all — look for raw JSON with appliance keys =====
    if not matches and not appliances:
        json_pattern = r'\{[^{}]*"name"[^{}]*"power"[^{}]*\}'
        raw_matches = re.findall(json_pattern, text, re.DOTALL)
        if raw_matches:
            matches = raw_matches
    
    if not matches and not appliances:
        return []
    
    # ===== Parse all found matches =====
    for i, match in enumerate(matches, 1):
        try:
            # Clean the raw JSON string before parsing
            json_str = clean_json_string(match)
            
            # Try to parse
            data_dict = json.loads(json_str)
            
            if USE_PYDANTIC:
                # Validate with Pydantic
                try:
                    validated = ApplianceExtracted(**data_dict)
                    print(f"✓ Pydantic validation passed (appliance {i}/{len(matches)})")
                    appliances.append(validated.model_dump())
                    
                except Exception as e:
                    print(f"⚠️  Pydantic validation errors (appliance {i}): {e}")
                    # Still include it (lenient mode)
                    print("   Continuing with unvalidated data...")
                    appliances.append(data_dict)
            else:
                # No Pydantic - return raw dict
                appliances.append(data_dict)
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parse error (block {i}): {e}")
            print(f"   Raw content preview: {match.strip()[:150]}...")
            
            # Try to fix truncated JSON
            fixed = try_fix_truncated_json(match)
            if fixed:
                appliances.append(fixed)
                continue
            
            # Last resort: manual extraction
            fallback = try_manual_extraction(match)
            if fallback:
                print(f"   ✓ Manual extraction recovered: {fallback.get('name', '?')}")
                appliances.append(fallback)
            
            continue
        except Exception as e:
            print(f"⚠️  Unexpected error (block {i}): {e}")
            continue
    
    return appliances