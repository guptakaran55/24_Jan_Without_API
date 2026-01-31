# database/queries.py - FINAL FIX
# Replace your current database/queries.py with this

from database.connection import query

def create_family(family_id, household_size, location):
    """Create a new family"""
    sql = """
        INSERT INTO families (family_id, household_size, location)
        VALUES (%s, %s, %s)
        RETURNING family_id, household_size, location
    """
    results = query(sql, (family_id, household_size, location))
    return results[0] if results and isinstance(results, list) else None

def create_user(user_id, family_id, age_group, interests):
    """Create a new user"""
    sql = """
        INSERT INTO users (user_id, family_id, age_group, interests)
        VALUES (%s, %s, %s, %s)
        RETURNING user_id, family_id, age_group
    """
    results = query(sql, (user_id, family_id, age_group, interests))
    return results[0] if results and isinstance(results, list) else None

def create_session(session_id, user_id, family_id):
    """Create a new survey session"""
    sql = """
        INSERT INTO survey_sessions (session_id, user_id, family_id, status)
        VALUES (%s, %s, %s, 'in_progress')
        RETURNING session_id, user_id, family_id, status
    """
    results = query(sql, (session_id, user_id, family_id))
    return results[0] if results and isinstance(results, list) else None

def save_message(session_id, user_id, role, message_text, extracted_data=None):
    """Save a conversation message with auto-incrementing message_order"""
    import json
    
    # Convert extracted_data to JSON string if present
    extracted_json = json.dumps(extracted_data) if extracted_data else None
    
    # Get next message_order for this session
    order_sql = """
        SELECT COALESCE(MAX(message_order), 0) + 1 as next_order
        FROM conversation_context 
        WHERE session_id = %s
    """
    order_result = query(order_sql, (session_id,))
    
    # Extract the order value safely
    if order_result and len(order_result) > 0:
        # Try different possible keys
        first_row = order_result[0]
        message_order = first_row.get('next_order') or first_row.get('?column?') or 1
    else:
        message_order = 1
    
    # Insert with message_order
    sql = """
        INSERT INTO conversation_context 
        (session_id, user_id, message_order, role, message_text, extracted_data)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING context_id, message_order
    """
    results = query(sql, (session_id, user_id, message_order, role, message_text, extracted_json))
    return results[0] if results and isinstance(results, list) else None

def save_appliance(data):
    """
    Save appliance data to database
    
    Args:
        data: dict with appliance information
    
    Returns:
        Saved appliance record or None
    """
    
    # Extract window data safely
    window_1 = data.get('window_1')
    window_1_start = window_1[0] if window_1 and len(window_1) >= 2 else None
    window_1_end = window_1[1] if window_1 and len(window_1) >= 2 else None
    
    window_2 = data.get('window_2')
    window_2_start = window_2[0] if window_2 and len(window_2) >= 2 else None
    window_2_end = window_2[1] if window_2 and len(window_2) >= 2 else None
    
    window_3 = data.get('window_3')
    window_3_start = window_3[0] if window_3 and len(window_3) >= 2 else None
    window_3_end = window_3[1] if window_3 and len(window_3) >= 2 else None
    
    sql = """
        INSERT INTO appliances (
            session_id, user_id, family_id,
            name, number, power, func_time,
            num_windows,
            window_1_start, window_1_end,
            window_2_start, window_2_end,
            window_3_start, window_3_end,
            func_cycle, fixed, occasional_use, wd_we_type
        ) VALUES (
            %s, %s, %s,
            %s, %s, %s, %s,
            %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s, %s, %s
        )
        RETURNING appliance_id, name, number, power
    """
    
    params = (
        data.get('session_id'),
        data.get('user_id'),
        data.get('family_id'),
        data.get('name'),
        data.get('number', 1),
        data.get('power'),
        data.get('func_time'),
        data.get('num_windows', 1),
        window_1_start,
        window_1_end,
        window_2_start,
        window_2_end,
        window_3_start,
        window_3_end,
        data.get('func_cycle', 1),
        data.get('fixed', 'no'),
        data.get('occasional_use', 1.0),
        data.get('wd_we_type', 2)
    )
    
    try:
        results = query(sql, params)
        return results[0] if results and isinstance(results, list) else None
    except Exception as e:
        print(f"Database error in save_appliance: {e}")
        raise

def get_session_appliances(session_id):
    """Get all appliances for a session"""
    sql = """
        SELECT * FROM appliances
        WHERE session_id = %s
        ORDER BY created_at ASC
    """
    results = query(sql, (session_id,))
    return results if results else []

def get_conversation_history(session_id, limit=20):
    """Get conversation history for a session"""
    sql = """
        SELECT 
            context_id, session_id, user_id, message_order,
            role, message_text, extracted_data, timestamp
        FROM conversation_context
        WHERE session_id = %s
        ORDER BY message_order ASC
        LIMIT %s
    """
    results = query(sql, (session_id, limit))
    return results if results else []

def get_all_appliance_defaults():
    """Get all appliance default values"""
    sql = "SELECT * FROM appliance_defaults ORDER BY appliance_type"
    results = query(sql)
    return results if results else []

def appliance_exists(session_id, name, window_1_start=None):
    """Check if appliance already exists to prevent duplicates"""
    if window_1_start is not None:
        sql = """
            SELECT COUNT(*) as count FROM appliances 
            WHERE session_id = %s 
            AND LOWER(TRIM(name)) = LOWER(TRIM(%s))
            AND window_1_start = %s
        """
        result = query(sql, (session_id, name, window_1_start))
    else:
        sql = """
            SELECT COUNT(*) as count FROM appliances 
            WHERE session_id = %s 
            AND LOWER(TRIM(name)) = LOWER(TRIM(%s))
        """
        result = query(sql, (session_id, name))
    
    if result and len(result) > 0:
        count = result[0].get('count', 0)
        return count > 0
    return False

def get_appliance_default(appliance_type):
    """Get default values for a specific appliance type"""
    sql = """
        SELECT * FROM appliance_defaults
        WHERE LOWER(appliance_type) = LOWER(%s)
        LIMIT 1
    """
    results = query(sql, (appliance_type,))
    return results[0] if results and isinstance(results, list) and len(results) > 0 else None