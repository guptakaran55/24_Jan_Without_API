# main.py - MULTI-LLM SUPPORT + CONVERSATION MODE + JSON EXPORT + EDIT MODE
# Supported: Google Gemini, Claude (Anthropic), Ollama (local)

import uuid
import os
import re
import json
from datetime import datetime
from dotenv import load_dotenv

from database.connection import init_pool, close_pool
from database import queries as db
from services.context_service import build_smart_context, format_context_for_prompt
from utils.json_extractor import extract_all_json
from services.validation_service import validate_appliance
from conversation_mode import select_conversation_mode
from appliance_editor import handle_edit_command

load_dotenv()


def select_llm_provider():
    """Let user choose which LLM to use"""
    print("\n" + "="*80)
    print("🤖 SELECT YOUR LLM PROVIDER")
    print("="*80)
    
    providers = []
    if os.getenv('GOOGLE_API_KEY'):
        providers.append(('google', '🌐 Google Gemini (Fast, Free tier)'))
    if os.getenv('ANTHROPIC_API_KEY'):
        providers.append(('claude', '🧠 Claude (Anthropic, High quality)'))
    providers.append(('ollama', '🏠 Ollama (Local, Free, Private)'))
    
    if len(providers) == 1:
        print(f"\nOnly one provider available: {providers[0][1]}")
        return providers[0][0]
    
    print("\nAvailable providers:")
    for i, (key, name) in enumerate(providers, 1):
        print(f"  {i}. {name}")
    
    while True:
        try:
            choice = input(f"\nSelect provider (1-{len(providers)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(providers):
                selected = providers[idx][0]
                print(f"✓ Selected: {providers[idx][1]}\n")
                return selected
            else:
                print(f"❌ Please enter a number between 1 and {len(providers)}")
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\n👋 Exiting...\n")
            exit(0)


# Select LLM provider
SELECTED_LLM = select_llm_provider()

# Select conversation mode
CONV_MODE = select_conversation_mode()

# Import the appropriate client
if SELECTED_LLM == 'google':
    from llm.google_client import call_google_gemini as call_llm, set_max_output_tokens
    set_max_output_tokens(CONV_MODE['max_output_tokens'])
    PROVIDER_NAME = "Google Gemini"
elif SELECTED_LLM == 'claude':
    from llm.claude_client import call_claude as call_llm
    PROVIDER_NAME = "Claude (Anthropic)"
else:
    from llm.client import call_ollama as call_llm
    PROVIDER_NAME = "Ollama (local)"

from llm.prompts import build_system_prompt


def start_new_session():
    user_id = str(uuid.uuid4())
    family_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    db.create_family(family_id, 1, 'Home')
    db.create_user(user_id, family_id, 'adult', '[]')
    db.create_session(session_id, user_id, family_id)
    return {'session_id': session_id, 'user_id': user_id, 'family_id': family_id}


def format_time_window(start, end):
    if start is None or end is None:
        return "anytime"
    return f"{start//60:02d}:{start%60:02d}-{end//60:02d}:{end%60:02d}"


def show_saved_appliances(session_id):
    appliances = db.get_session_appliances(session_id)
    if not appliances:
        print("\n📊 No appliances saved yet")
        return
    
    print("\n" + "="*80)
    print(f"📊 SAVED APPLIANCES ({len(appliances)} total)")
    print("="*80)
    print(f"{'#':<3} {'Name':<20} {'Qty':<4} {'Power':<8} {'Hours/Day':<10} {'Time Window':<15}")
    print("-"*80)
    
    for i, a in enumerate(appliances, 1):
        name = a['name'][:19]
        qty = a['number']
        power = f"{a['power']}W"
        hours = f"{a['func_time']/60:.1f}h"
        time_win = format_time_window(a.get('window_1_start'), a.get('window_1_end'))
        print(f"{i:<3} {name:<20} {qty:<4} {power:<8} {hours:<10} {time_win:<15}")
    
    total_kwh = sum(a['power'] * a['number'] * a['func_time'] / 60.0 / 1000.0 for a in appliances)
    print("-"*80)
    print(f"{'TOTAL DAILY ENERGY:':<48} {total_kwh:.2f} kWh/day")
    print("="*80 + "\n")


def export_session_json(session_id, user_id, family_id):
    appliances = db.get_session_appliances(session_id)
    if not appliances:
        print("\n📄 No appliances to export.")
        return None
    
    appliance_list = []
    for a in appliances:
        entry = {
            "name": a['name'], "number": a['number'], "power": a['power'],
            "func_time": a['func_time'], "num_windows": a.get('num_windows', 1),
            "window_1": [a['window_1_start'], a['window_1_end']] if a.get('window_1_start') is not None else None,
        }
        if a.get('window_2_start') is not None:
            entry["window_2"] = [a['window_2_start'], a['window_2_end']]
        if a.get('window_3_start') is not None:
            entry["window_3"] = [a['window_3_start'], a['window_3_end']]
        entry.update({
            "func_cycle": a.get('func_cycle', 1), "fixed": a.get('fixed', 'no'),
            "occasional_use": float(a.get('occasional_use', 1.0)), "wd_we_type": a.get('wd_we_type', 2),
        })
        appliance_list.append(entry)
    
    export_data = {
        "survey_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "User_ID": user_id, "Family_ID": family_id, "session_id": session_id,
        "random_var_w": 0.2, "total_appliances": len(appliance_list),
        "total_daily_energy_kwh": round(sum(
            a['power'] * a['number'] * a['func_time'] / 60.0 / 1000.0 for a in appliances
        ), 2),
        "appliances": appliance_list
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"survey_{session_id[:8]}_{timestamp}.json"
    filepath = os.path.join(os.getcwd(), filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        print("\n" + "="*80)
        print("📄 EXPORTED JSON")
        print("="*80)
        print(json.dumps(export_data, indent=2, ensure_ascii=False))
        print("="*80)
        print(f"\n✅ Saved to: {filepath}")
        print(f"   Appliances: {len(appliance_list)}")
        print(f"   Daily energy: {export_data['total_daily_energy_kwh']} kWh/day\n")
        return filepath
    except Exception as e:
        print(f"\n❌ Failed to save file: {e}")
        print("\n" + json.dumps(export_data, indent=2, ensure_ascii=False))
        return None


def replace_json_with_summary(message_text):
    import json as json_module
    
    def json_to_summary(match):
        raw = match.group(1).strip()
        try:
            cleaned = raw
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
            cleaned = re.sub(r'\bTrue\b', 'true', cleaned)
            cleaned = re.sub(r'\bFalse\b', 'false', cleaned)
            data = json_module.loads(cleaned)
            name = data.get('name', '?')
            power = data.get('power', '?')
            ft = data.get('func_time', 0)
            hours = f"{ft/60:.1f}h" if ft else '?'
            w = data.get('window_1', [])
            w_str = format_time_window(w[0], w[1]) if len(w) == 2 else '?'
            upd = " (UPDATE)" if data.get('update') else ""
            return f"[SAVED: {name}, {power}W, {hours}/day, {w_str}{upd}]"
        except Exception:
            return "[SAVED: appliance data extracted]"
    
    result = re.sub(r'\[JSON_DATA_START\](.*?)\[JSON_DATA_END\]', json_to_summary, message_text, flags=re.DOTALL)
    result = re.sub(r'\[JSON_DATA_START\](.*?)$', json_to_summary, result, flags=re.DOTALL)
    return result.strip()


def ensure_alternating_messages(messages):
    if not messages:
        return messages
    messages = [m for m in messages if m.get('content', '').strip()]
    if not messages:
        return messages
    while messages and messages[0]['role'] == 'assistant':
        messages.pop(0)
    if not messages:
        return messages
    merged = [messages[0]]
    for msg in messages[1:]:
        if msg['role'] == merged[-1]['role']:
            merged[-1]['content'] += "\n" + msg['content']
        else:
            merged.append(msg)
    while merged and merged[-1]['role'] == 'assistant':
        merged.pop()
    fixed = []
    expected_role = 'user'
    for msg in merged:
        if msg['role'] == expected_role:
            fixed.append(msg)
            expected_role = 'assistant' if expected_role == 'user' else 'user'
        elif msg['role'] == 'user' and expected_role == 'assistant':
            fixed.append({'role': 'assistant', 'content': 'Okay, noted.'})
            fixed.append(msg)
            expected_role = 'assistant'
        elif msg['role'] == 'assistant' and expected_role == 'user':
            fixed.append({'role': 'user', 'content': 'Continue.'})
            fixed.append(msg)
            expected_role = 'user'
    return fixed


def update_appliance(session_id, extracted_data):
    """Update an existing appliance (delete old, insert new)."""
    from database.connection import query as db_query
    name = extracted_data.get('name', '')
    find_sql = """
        SELECT appliance_id, name FROM appliances
        WHERE session_id = %s AND LOWER(TRIM(name)) = LOWER(TRIM(%s))
        ORDER BY created_at DESC LIMIT 1
    """
    existing = db_query(find_sql, (session_id, name))
    if existing and len(existing) > 0:
        old_id = existing[0]['appliance_id']
        old_name = existing[0]['name']
        db_query("DELETE FROM appliances WHERE appliance_id = %s", (old_id,))
        extracted_data.pop('update', None)
        saved = db.save_appliance(extracted_data)
        if saved:
            print(f"   🔄 UPDATED '{old_name}' with new data")
            return True
    return False


def chat_loop(session):
    """Main chat loop"""
    session_id = session['session_id']
    user_id = session['user_id']
    family_id = session['family_id']
    
    history_limit = CONV_MODE['history_limit']
    mode_style = CONV_MODE['prompt_style']
    
    print("\n" + "="*80)
    print(f"⚡ ENERGY SURVEY CHATBOT (Powered by {PROVIDER_NAME})")
    print(f"   Mode: {CONV_MODE['label']}")
    print("="*80)
    print("\nI'll save appliances as we talk and show you what's stored!")
    print("\nCommands:")
    print("  'quit'     - Exit and export JSON")
    print("  'list'     - Show all saved appliances")
    print("  'edit'     - Edit, delete, or modify saved appliances")
    print("  'export'   - Export JSON now (without quitting)")
    print("  'schedule' - Show time window analysis")
    print("="*80 + "\n")
    
    greeting = "Hi! Tell me about your daily routine and the appliances you use!"
    print(f"Assistant: {greeting}\n")
    db.save_message(session_id, user_id, 'assistant', greeting)
    
    appliance_count = 0
    last_response = None
    consecutive_duplicates = 0
    MAX_DUPLICATES = 5
    last_questions_asked = []
    
    while True:
        user_message = input("You: ").strip()
        
        if not user_message:
            continue
        
        # Exit keywords
        exit_keywords = ['quit', 'exit', 'bye', 'goodbye', "that's it", 'thats it', 'nothing else', 'no more']
        if any(keyword in user_message.lower() for keyword in exit_keywords):
            show_saved_appliances(session_id)
            export_session_json(session_id, user_id, family_id)
            # Recount appliances from DB after possible edits
            final_count = len(db.get_session_appliances(session_id))
            print(f"\n✓ Session complete! {final_count} appliances saved. Thank you!\n")
            break
        
        # Special commands
        if user_message.lower() == 'list':
            show_saved_appliances(session_id)
            continue
        
        if user_message.lower() == 'edit':
            handle_edit_command(session_id)
            # Recount after edits
            appliance_count = len(db.get_session_appliances(session_id))
            continue
        
        if user_message.lower() == 'export':
            export_session_json(session_id, user_id, family_id)
            continue
        
        if user_message.lower() == 'schedule':
            context = build_smart_context(session_id, user_id, family_id)
            print("\n" + format_context_for_prompt(context) + "\n")
            continue
        
        # Save user message
        db.save_message(session_id, user_id, 'user', user_message)
        
        # Build context
        context = build_smart_context(session_id, user_id, family_id)
        context_summary = format_context_for_prompt(context)
        
        recent_history = db.get_conversation_history(session_id, limit=history_limit)
        
        defaults = db.get_all_appliance_defaults()
        reference_data = {d['appliance_type']: {'power': d['typical_power_watts']} for d in defaults}
        
        system_prompt = build_system_prompt(context_summary, reference_data, mode_style)
        
        # Format messages
        messages = []
        for msg in recent_history:
            clean_msg = replace_json_with_summary(msg['message_text']) if msg['role'] == 'assistant' else msg['message_text']
            if clean_msg:
                messages.append({'role': msg['role'], 'content': clean_msg})
        
        messages = ensure_alternating_messages(messages)
        if not messages:
            messages = [{'role': 'user', 'content': user_message}]
        
        # Call LLM
        print("\n[Assistant is thinking...]")
        response = call_llm(messages, system_prompt)
        
        if not response['success']:
            print(f"\n❌ Error: {response['error']}\n")
            continue
        
        # ========== EXTRACT JSON BLOCKS ==========
        extracted_appliances = extract_all_json(response['text'])
        
        if extracted_appliances:
            print(f"\n💾 [Found {len(extracted_appliances)} appliance(s) in response...]")
            
            for idx, extracted_data in enumerate(extracted_appliances, 1):
                print(f"\n📋 Appliance {idx}/{len(extracted_appliances)}:")
                print(f"   Name: {extracted_data.get('name', 'Unknown')}")
                print(f"   Quantity: {extracted_data.get('number', 1)}")
                print(f"   Power: {extracted_data.get('power', '?')}W")
                print(f"   Usage: {extracted_data.get('func_time', 0)/60:.1f} hours/day")
                
                window_1 = extracted_data.get('window_1', [])
                if len(window_1) == 2:
                    print(f"   Time: {format_time_window(window_1[0], window_1[1])}")
                
                is_update = extracted_data.get('update', False)
                if is_update:
                    print(f"   🔄 Update requested for existing appliance")
                
                validation = validate_appliance(extracted_data)
                
                if validation['valid'] or len(validation['errors']) <= 1:
                    extracted_data['session_id'] = session_id
                    extracted_data['user_id'] = user_id
                    extracted_data['family_id'] = family_id
                    
                    window_start = window_1[0] if len(window_1) >= 2 else None
                    appliance_name = extracted_data.get('name', '')
                    
                    if is_update:
                        updated = update_appliance(session_id, extracted_data)
                        if not updated:
                            extracted_data.pop('update', None)
                            saved = db.save_appliance(extracted_data)
                            if saved:
                                appliance_count += 1
                                print(f"\n   ✅ SAVED as new! (Total: {appliance_count})")
                    elif db.appliance_exists(session_id, appliance_name, window_start):
                        consecutive_duplicates += 1
                        print(f"\n   ⚠️  DUPLICATE ({consecutive_duplicates}/{MAX_DUPLICATES}) — skipping")
                        if consecutive_duplicates >= MAX_DUPLICATES:
                            print(f"\n⚠️  Too many duplicates. Ending conversation.\n")
                            show_saved_appliances(session_id)
                            export_session_json(session_id, user_id, family_id)
                            break
                    else:
                        consecutive_duplicates = 0
                        extracted_data.pop('update', None)
                        try:
                            saved = db.save_appliance(extracted_data)
                            if saved:
                                appliance_count += 1
                                print(f"\n   ✅ SAVED! (Total: {appliance_count} appliances)")
                        except Exception as e:
                            print(f"\n   ❌ Save failed: {e}")
                else:
                    print(f"\n   ⚠️  Validation failed: {validation['errors']}")
            
            if appliance_count > 0:
                show_saved_appliances(session_id)
        
        # Clean response for display
        clean_response = re.sub(r'\[JSON_DATA_START\].*?\[JSON_DATA_END\]', '', response['text'], flags=re.DOTALL).strip()
        clean_response = re.sub(r'\[JSON_DATA_START\].*$', '', clean_response, flags=re.DOTALL).strip()
        clean_response = re.sub(r'\{[^}]*"name"[^}]*\}', '', clean_response).strip()
        
        # Loop detection
        if clean_response:
            if clean_response == last_response:
                print("\n⚠️  [Loop detected] Try different info, 'list', 'edit', or 'quit'.\n")
                last_response = None
                continue
            
            questions = [s.strip() for s in re.split(r'[।??\n]', clean_response) if '?' in s or '?' in s]
            if questions and questions == last_questions_asked:
                print("\n⚠️  [Same questions again] Try different wording, or 'quit'.\n")
                last_questions_asked = []
                continue
            
            last_questions_asked = questions
            print(f"\nAssistant: {clean_response}\n")
            last_response = clean_response
        
        last_extracted = extracted_appliances[-1] if extracted_appliances else None
        db.save_message(session_id, user_id, 'assistant', response['text'], last_extracted)


def main():
    try:
        init_pool()
        session = start_new_session()
        print(f"🆔 Session ID: {session['session_id'][:8]}...")
        chat_loop(session)
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        close_pool()

if __name__ == "__main__":
    main()