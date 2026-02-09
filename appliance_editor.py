# appliance_editor.py
# Handles user commands to edit, delete, or modify saved appliances
# Works interactively in the terminal

from database.connection import query
from database import queries as db


def delete_appliance_by_id(appliance_id):
    """Delete a single appliance by its database ID"""
    sql = "DELETE FROM appliances WHERE appliance_id = %s RETURNING appliance_id, name"
    result = query(sql, (appliance_id,))
    return result[0] if result and isinstance(result, list) else None


def update_appliance_field(appliance_id, field, value):
    """
    Update a single field of an appliance.
    
    Supported fields and their types:
      name         -> str
      number       -> int
      power        -> int (watts)
      func_time    -> int (minutes)
      num_windows  -> int
      window_1_start, window_1_end -> int (minutes from midnight)
      window_2_start, window_2_end -> int (minutes from midnight)
      window_3_start, window_3_end -> int (minutes from midnight)
      func_cycle   -> int
      fixed        -> str ('yes' or 'no')
      occasional_use -> float (0.0 to 1.0)
      wd_we_type   -> int (0, 1, or 2)
    """
    
    # Whitelist of editable fields to prevent SQL injection
    allowed_fields = {
        'name', 'number', 'power', 'func_time', 'num_windows',
        'window_1_start', 'window_1_end',
        'window_2_start', 'window_2_end',
        'window_3_start', 'window_3_end',
        'func_cycle', 'fixed', 'occasional_use', 'wd_we_type'
    }
    
    if field not in allowed_fields:
        return None, f"Field '{field}' is not editable. Editable fields: {', '.join(sorted(allowed_fields))}"
    
    # Use parameterized query (field name is whitelisted, value is parameterized)
    sql = f"UPDATE appliances SET {field} = %s WHERE appliance_id = %s RETURNING appliance_id, name, {field}"
    try:
        result = query(sql, (value, appliance_id))
        return result[0] if result and isinstance(result, list) else None, None
    except Exception as e:
        return None, str(e)


def parse_time_input(time_str):
    """
    Parse a user-friendly time string into minutes from midnight.
    
    Accepts:
      "9am", "9:00", "9:30am", "21:00", "9pm", "14:30", "2:30pm", "1400"
    
    Returns:
      int (minutes from midnight) or None if invalid
    """
    time_str = time_str.strip().lower().replace(' ', '')
    
    # Handle "9am", "10pm", "9:30am", "10:30pm"
    is_pm = 'pm' in time_str
    is_am = 'am' in time_str
    time_str = time_str.replace('am', '').replace('pm', '')
    
    try:
        if ':' in time_str:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
        elif len(time_str) == 4 and time_str.isdigit():
            # Military time like "1400"
            hours = int(time_str[:2])
            minutes = int(time_str[2:])
        else:
            hours = int(time_str)
            minutes = 0
        
        if is_pm and hours < 12:
            hours += 12
        if is_am and hours == 12:
            hours = 0
        
        if 0 <= hours <= 24 and 0 <= minutes < 60:
            return hours * 60 + minutes
        return None
    except (ValueError, IndexError):
        return None


def format_time_from_minutes(mins):
    """Convert minutes from midnight to readable time"""
    if mins is None:
        return "?"
    h = mins // 60
    m = mins % 60
    return f"{h:02d}:{m:02d}"


def show_appliance_detail(appliance):
    """Show all fields of a single appliance"""
    print(f"\n   {'Field':<20} {'Value':<30}")
    print(f"   {'-'*50}")
    print(f"   {'Name':<20} {appliance['name']}")
    print(f"   {'Quantity':<20} {appliance['number']}")
    print(f"   {'Power':<20} {appliance['power']}W")
    print(f"   {'Usage/day':<20} {appliance['func_time']/60:.1f}h ({appliance['func_time']} min)")
    
    w1s = appliance.get('window_1_start')
    w1e = appliance.get('window_1_end')
    if w1s is not None:
        print(f"   {'Window 1':<20} {format_time_from_minutes(w1s)} - {format_time_from_minutes(w1e)}")
    
    w2s = appliance.get('window_2_start')
    w2e = appliance.get('window_2_end')
    if w2s is not None:
        print(f"   {'Window 2':<20} {format_time_from_minutes(w2s)} - {format_time_from_minutes(w2e)}")
    
    w3s = appliance.get('window_3_start')
    w3e = appliance.get('window_3_end')
    if w3s is not None:
        print(f"   {'Window 3':<20} {format_time_from_minutes(w3s)} - {format_time_from_minutes(w3e)}")
    
    print(f"   {'Cycle time':<20} {appliance.get('func_cycle', 1)} min")
    print(f"   {'Fixed':<20} {appliance.get('fixed', 'no')}")
    print(f"   {'Occasional use':<20} {appliance.get('occasional_use', 1.0)}")
    
    wd_we = appliance.get('wd_we_type', 2)
    wd_we_str = {0: 'Weekdays only', 1: 'Weekends only', 2: 'Whole week'}.get(wd_we, '?')
    print(f"   {'Schedule':<20} {wd_we_str}")
    print()


def handle_edit_command(session_id):
    """
    Interactive editor for saved appliances.
    
    Commands:
      delete <#>              - Delete appliance by list number
      edit <#>                - Show all fields and edit interactively
      edit <#> power <value>  - Quick edit: change power of appliance #
      edit <#> time <start>-<end>  - Quick edit: change time window
      edit <#> hours <value>  - Quick edit: change usage hours per day
      edit <#> qty <value>    - Quick edit: change quantity
      edit <#> name <value>   - Quick edit: change name
      edit <#> schedule <weekdays|weekends|both> - Change schedule type
    """
    
    appliances = db.get_session_appliances(session_id)
    
    if not appliances:
        print("\n📊 No appliances to edit. Start chatting to add some!\n")
        return
    
    # Show current list
    print("\n" + "="*80)
    print("✏️  EDIT MODE — Modify your saved appliances")
    print("="*80)
    print(f"\n{'#':<3} {'Name':<20} {'Qty':<4} {'Power':<8} {'Hours/Day':<10} {'Time Window':<15}")
    print("-"*70)
    
    for i, a in enumerate(appliances, 1):
        name = a['name'][:19]
        qty = a['number']
        power = f"{a['power']}W"
        hours = f"{a['func_time']/60:.1f}h"
        w1s = a.get('window_1_start')
        w1e = a.get('window_1_end')
        time_win = f"{format_time_from_minutes(w1s)}-{format_time_from_minutes(w1e)}" if w1s is not None else "anytime"
        print(f"{i:<3} {name:<20} {qty:<4} {power:<8} {hours:<10} {time_win:<15}")
    
    print("-"*70)
    print("\nCommands:")
    print("  delete <#>                    — Remove an appliance")
    print("  edit <#>                      — View all fields & edit interactively")
    print("  edit <#> power <watts>        — Change power (e.g., edit 3 power 200)")
    print("  edit <#> time <start>-<end>   — Change time (e.g., edit 3 time 9am-6pm)")
    print("  edit <#> hours <hours>        — Change daily usage (e.g., edit 3 hours 4.5)")
    print("  edit <#> qty <number>         — Change quantity (e.g., edit 3 qty 2)")
    print("  edit <#> name <new name>      — Rename (e.g., edit 3 name LED Light)")
    print("  edit <#> schedule <type>      — weekdays / weekends / both")
    print("  done                          — Exit edit mode")
    print()
    
    while True:
        cmd = input("Edit> ").strip()
        
        if not cmd:
            continue
        
        if cmd.lower() == 'done':
            print("✓ Exiting edit mode.\n")
            break
        
        parts = cmd.split(None, 2)  # Split into max 3 parts
        action = parts[0].lower()
        
        # ===== DELETE =====
        if action == 'delete' and len(parts) >= 2:
            try:
                idx = int(parts[1]) - 1
                if 0 <= idx < len(appliances):
                    target = appliances[idx]
                    confirm = input(f"   Delete '{target['name']}'? (yes/no): ").strip().lower()
                    if confirm in ('yes', 'y'):
                        result = delete_appliance_by_id(target['appliance_id'])
                        if result:
                            print(f"   ✅ Deleted '{result['name']}'")
                            appliances.pop(idx)
                        else:
                            print("   ❌ Delete failed")
                    else:
                        print("   Cancelled.")
                else:
                    print(f"   ❌ Invalid number. Use 1-{len(appliances)}")
            except ValueError:
                print("   ❌ Usage: delete <number>")
        
        # ===== EDIT =====
        elif action == 'edit' and len(parts) >= 2:
            try:
                idx = int(parts[1]) - 1
                if not (0 <= idx < len(appliances)):
                    print(f"   ❌ Invalid number. Use 1-{len(appliances)}")
                    continue
                
                target = appliances[idx]
                
                if len(parts) == 2:
                    # Interactive edit — show all fields
                    show_appliance_detail(target)
                    print("   Enter field to edit (or 'back' to return):")
                    print("   Options: name, qty, power, hours, time, schedule")
                    
                    field_cmd = input("   Edit field> ").strip().lower()
                    if field_cmd == 'back':
                        continue
                    # Process as if they typed "edit <#> <field> ..."
                    parts = ['edit', parts[1], field_cmd]
                
                if len(parts) >= 3:
                    field = parts[2].split()[0].lower()
                    value_str = parts[2][len(field):].strip() if len(parts[2]) > len(field) else ''
                    
                    # If no value given, ask for it
                    if not value_str:
                        value_str = input(f"   New value for {field}: ").strip()
                    
                    if not value_str:
                        print("   Cancelled.")
                        continue
                    
                    # Parse based on field type
                    if field == 'power':
                        try:
                            value = int(value_str.replace('w', '').replace('W', ''))
                            result, err = update_appliance_field(target['appliance_id'], 'power', value)
                            if result:
                                target['power'] = value
                                print(f"   ✅ Power updated to {value}W")
                            else:
                                print(f"   ❌ Error: {err}")
                        except ValueError:
                            print("   ❌ Power must be a number (e.g., 200)")
                    
                    elif field in ('qty', 'quantity', 'number'):
                        try:
                            value = int(value_str)
                            result, err = update_appliance_field(target['appliance_id'], 'number', value)
                            if result:
                                target['number'] = value
                                print(f"   ✅ Quantity updated to {value}")
                            else:
                                print(f"   ❌ Error: {err}")
                        except ValueError:
                            print("   ❌ Quantity must be a number (e.g., 2)")
                    
                    elif field == 'name':
                        result, err = update_appliance_field(target['appliance_id'], 'name', value_str)
                        if result:
                            target['name'] = value_str
                            print(f"   ✅ Name updated to '{value_str}'")
                        else:
                            print(f"   ❌ Error: {err}")
                    
                    elif field in ('hours', 'usage'):
                        try:
                            hours = float(value_str.replace('h', ''))
                            minutes = int(hours * 60)
                            result, err = update_appliance_field(target['appliance_id'], 'func_time', minutes)
                            if result:
                                target['func_time'] = minutes
                                print(f"   ✅ Usage updated to {hours}h/day ({minutes} min)")
                            else:
                                print(f"   ❌ Error: {err}")
                        except ValueError:
                            print("   ❌ Hours must be a number (e.g., 4.5)")
                    
                    elif field == 'time':
                        # Parse "9am-6pm" or "09:00-18:00"
                        time_parts = value_str.replace(' ', '').split('-')
                        if len(time_parts) == 2:
                            start = parse_time_input(time_parts[0])
                            end = parse_time_input(time_parts[1])
                            if start is not None and end is not None:
                                update_appliance_field(target['appliance_id'], 'window_1_start', start)
                                result, err = update_appliance_field(target['appliance_id'], 'window_1_end', end)
                                if result:
                                    target['window_1_start'] = start
                                    target['window_1_end'] = end
                                    print(f"   ✅ Time updated to {format_time_from_minutes(start)}-{format_time_from_minutes(end)}")
                                else:
                                    print(f"   ❌ Error: {err}")
                            else:
                                print("   ❌ Could not parse times. Try: 9am-6pm or 09:00-18:00")
                        else:
                            print("   ❌ Format: <start>-<end> (e.g., 9am-6pm)")
                    
                    elif field == 'schedule':
                        schedule_map = {
                            'weekdays': 0, 'weekday': 0, 'wd': 0,
                            'weekends': 1, 'weekend': 1, 'we': 1,
                            'both': 2, 'all': 2, 'whole': 2, 'daily': 2,
                        }
                        val = schedule_map.get(value_str.lower())
                        if val is not None:
                            result, err = update_appliance_field(target['appliance_id'], 'wd_we_type', val)
                            if result:
                                target['wd_we_type'] = val
                                labels = {0: 'Weekdays only', 1: 'Weekends only', 2: 'Whole week'}
                                print(f"   ✅ Schedule updated to {labels[val]}")
                            else:
                                print(f"   ❌ Error: {err}")
                        else:
                            print("   ❌ Options: weekdays, weekends, both")
                    
                    elif field in ('cycle', 'func_cycle'):
                        try:
                            value = int(value_str)
                            result, err = update_appliance_field(target['appliance_id'], 'func_cycle', value)
                            if result:
                                target['func_cycle'] = value
                                print(f"   ✅ Cycle time updated to {value} min")
                            else:
                                print(f"   ❌ Error: {err}")
                        except ValueError:
                            print("   ❌ Cycle must be a number in minutes")
                    
                    elif field in ('occasional', 'occasional_use', 'frequency'):
                        try:
                            value = float(value_str)
                            if 0 <= value <= 1:
                                result, err = update_appliance_field(target['appliance_id'], 'occasional_use', value)
                                if result:
                                    target['occasional_use'] = value
                                    print(f"   ✅ Occasional use updated to {value}")
                                else:
                                    print(f"   ❌ Error: {err}")
                            else:
                                print("   ❌ Must be between 0.0 and 1.0")
                        except ValueError:
                            print("   ❌ Must be a decimal (e.g., 0.5)")
                    
                    else:
                        print(f"   ❌ Unknown field '{field}'")
                        print("   Options: name, qty, power, hours, time, schedule, cycle, occasional")
                
            except ValueError:
                print("   ❌ Usage: edit <number> [field] [value]")
        
        else:
            print("   ❌ Commands: delete <#>, edit <#>, edit <#> <field> <value>, done")