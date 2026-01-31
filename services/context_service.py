# services/context_service.py
# Smart context builder with time window awareness

from database import queries as db

def build_smart_context(session_id, user_id, family_id):
    """
    Build context that shows:
    1. What appliances have been saved (summary only, not full conversation)
    2. What time windows are occupied
    3. What time windows are still available
    """
    
    # Get all saved appliances
    appliances = db.get_session_appliances(session_id)
    
    # Analyze time windows
    time_windows = analyze_time_windows(appliances)
    
    context = {
        'session_id': session_id,
        'user_id': user_id,
        'family_id': family_id,
        'saved_appliances_summary': [
            {
                'name': a['name'],
                'number': a['number'],
                'power': a['power'],
                'func_time': a['func_time'],
                'windows': extract_windows(a)
            }
            for a in appliances
        ],
        'occupied_windows': time_windows['occupied'],
        'available_windows': time_windows['available'],
        'total_appliances': len(appliances)
    }
    
    return context

def extract_windows(appliance):
    """Extract time windows from an appliance"""
    windows = []
    for i in range(1, 4):
        start = appliance.get(f'window_{i}_start')
        end = appliance.get(f'window_{i}_end')
        if start is not None and end is not None:
            windows.append({
                'start': start,
                'end': end,
                'start_time': minutes_to_time(start),
                'end_time': minutes_to_time(end)
            })
    return windows

def analyze_time_windows(appliances):
    """
    Analyze which time windows are occupied and which are free
    Returns occupied windows and suggests available windows
    """
    
    # Create 24-hour timeline (in 30-minute blocks)
    timeline = [{'occupied': False, 'appliances': []} for _ in range(48)]  # 48 blocks of 30 min
    
    # Mark occupied blocks
    for appliance in appliances:
        for i in range(1, 4):
            start = appliance.get(f'window_{i}_start')
            end = appliance.get(f'window_{i}_end')
            if start is not None and end is not None:
                # Mark blocks as occupied
                start_block = start // 30
                end_block = end // 30
                for block in range(start_block, min(end_block + 1, 48)):
                    timeline[block]['occupied'] = True
                    timeline[block]['appliances'].append(appliance['name'])
    
    # Find occupied periods
    occupied = []
    current_period = None
    
    for i, block in enumerate(timeline):
        if block['occupied']:
            if current_period is None:
                current_period = {
                    'start': i * 30,
                    'end': (i + 1) * 30,
                    'appliances': set(block['appliances'])
                }
            else:
                current_period['end'] = (i + 1) * 30
                current_period['appliances'].update(block['appliances'])
        else:
            if current_period:
                occupied.append({
                    'start': current_period['start'],
                    'end': current_period['end'],
                    'start_time': minutes_to_time(current_period['start']),
                    'end_time': minutes_to_time(current_period['end']),
                    'appliances': list(current_period['appliances'])
                })
                current_period = None
    
    # Add last period if exists
    if current_period:
        occupied.append({
            'start': current_period['start'],
            'end': current_period['end'],
            'start_time': minutes_to_time(current_period['start']),
            'end_time': minutes_to_time(current_period['end']),
            'appliances': list(current_period['appliances'])
        })
    
    # Find available windows (gaps > 1 hour)
    available = []
    for i in range(len(occupied) - 1):
        gap_start = occupied[i]['end']
        gap_end = occupied[i + 1]['start']
        gap_duration = gap_end - gap_start
        
        if gap_duration >= 60:  # At least 1 hour gap
            available.append({
                'start': gap_start,
                'end': gap_end,
                'start_time': minutes_to_time(gap_start),
                'end_time': minutes_to_time(gap_end),
                'duration_hours': gap_duration / 60
            })
    
    # Check for gaps at start and end of day
    if not occupied or occupied[0]['start'] > 60:
        start = 0 if not occupied else 0
        end = occupied[0]['start'] if occupied else 1440
        if end - start >= 60:
            available.insert(0, {
                'start': start,
                'end': end,
                'start_time': minutes_to_time(start),
                'end_time': minutes_to_time(end),
                'duration_hours': (end - start) / 60
            })
    
    if not occupied or occupied[-1]['end'] < 1380:
        start = occupied[-1]['end'] if occupied else 0
        end = 1440
        if end - start >= 60:
            available.append({
                'start': start,
                'end': end,
                'start_time': minutes_to_time(start),
                'end_time': minutes_to_time(end),
                'duration_hours': (end - start) / 60
            })
    
    return {
        'occupied': occupied,
        'available': available
    }

def minutes_to_time(minutes):
    """Convert minutes from midnight to HH:MM format"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"

def format_context_for_prompt(context):
    """Format context into a readable string for the LLM prompt"""
    
    output = []
    
    # Summary of saved appliances
    if context['total_appliances'] > 0:
        output.append(f"✓ {context['total_appliances']} appliances saved so far:")
        for app in context['saved_appliances_summary'][-5:]:  # Show last 5
            windows_str = ', '.join([f"{w['start_time']}-{w['end_time']}" for w in app['windows']])
            output.append(f"  • {app['name']} ({app['number']}x, {app['power']}W) - used during: {windows_str}")
    else:
        output.append("No appliances saved yet.")
    
    # Time window status
    output.append("\n📅 TIME WINDOW STATUS:")
    
    if context['occupied_windows']:
        output.append("⏰ Already covered time periods:")
        for window in context['occupied_windows'][:5]:  # Show first 5
            appliances_str = ', '.join(window['appliances'][:3])  # Show max 3 appliances
            output.append(f"  • {window['start_time']}-{window['end_time']}: {appliances_str}")
    
    if context['available_windows']:
        output.append("\n⏳ Available time periods (ask about these):")
        for window in context['available_windows'][:3]:  # Show first 3
            output.append(f"  • {window['start_time']}-{window['end_time']} ({window['duration_hours']:.1f}h available)")
    else:
        output.append("\n✓ Full 24-hour schedule covered!")
    
    return '\n'.join(output)