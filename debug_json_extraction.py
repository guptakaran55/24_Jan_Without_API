# debug_json_extraction.py
# Run this to see what JSON the LLM is generating

from database.connection import init_pool, close_pool, query
from utils.json_extractor import extract_json
import json

def debug_extractions():
    """Check all messages with JSON data"""
    
    print("="*60)
    print("DEBUG: Checking JSON Extraction from Conversations")
    print("="*60)
    
    # Get all assistant messages
    sql = """
        SELECT 
            context_id,
            session_id,
            message_order,
            message_text,
            extracted_data,
            timestamp
        FROM conversation_context
        WHERE role = 'assistant'
        AND message_text LIKE '%JSON_DATA_START%'
        ORDER BY timestamp DESC
        LIMIT 10
    """
    
    messages = query(sql)
    
    if not messages:
        print("\n❌ No messages with [JSON_DATA_START] found!")
        print("The LLM is not generating JSON markers at all.")
        return
    
    print(f"\n✓ Found {len(messages)} messages with JSON markers\n")
    
    for i, msg in enumerate(messages, 1):
        print(f"\n{'='*60}")
        print(f"Message #{i} (Order: {msg['message_order']}, {msg['timestamp']})")
        print(f"{'='*60}")
        
        # Try to extract JSON
        extracted = extract_json(msg['message_text'])
        
        if extracted:
            print("\n✓ JSON EXTRACTED SUCCESSFULLY:")
            print(json.dumps(extracted, indent=2))
            
            # Check data_complete
            if extracted.get('data_complete'):
                print("\n✓ data_complete = TRUE")
                print("This SHOULD have been saved to appliances table!")
                
                # Check if it was actually saved
                check_sql = """
                    SELECT name, power, func_time 
                    FROM appliances 
                    WHERE session_id = %s
                    AND name = %s
                """
                saved = query(check_sql, (msg['session_id'], extracted.get('name')))
                
                if saved:
                    print(f"✓ CONFIRMED: Found in appliances table: {saved}")
                else:
                    print("❌ NOT FOUND in appliances table!")
                    print("Something failed during validation or saving!")
            else:
                print("\n❌ data_complete = FALSE or missing")
                print("This is why it wasn't saved!")
        else:
            print("\n❌ JSON EXTRACTION FAILED!")
            print("Raw message text (first 500 chars):")
            print(msg['message_text'][:500])
            print("\n[...truncated...]")
        
        print()

if __name__ == "__main__":
    init_pool()
    try:
        debug_extractions()
    finally:
        close_pool()