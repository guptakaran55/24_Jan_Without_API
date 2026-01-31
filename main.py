# main.py - SUPPORTS BOTH OLLAMA AND GOOGLE GEMINI
# Replace your current main.py with this

import uuid
import os
import re
from dotenv import load_dotenv

from database.connection import init_pool, close_pool
from database import queries as db
from services.context_service import build_smart_context, format_context_for_prompt
from utils.json_extractor import extract_json
from services.validation_service import validate_appliance

load_dotenv()

# Choose LLM provider
USE_GOOGLE = os.getenv('GOOGLE_API_KEY') is not None

if USE_GOOGLE:
    from llm.google_client import call_google_gemini as call_llm
    print("🌐 Using Google Gemini API")
else:
    from llm.client import call_ollama as call_llm
    print("🏠 Using Ollama (local)")

from llm.prompts import build_system_prompt

def start_new_session():
    """Start a new survey session"""
    user_id = str(uuid.uuid4())
    family_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    db.create_family(family_id, 1, 'Home')
    db.create_user(user_id, family_id, 'adult', '[]')
    db.create_session(session_id, user_id, family_id)
    
    return {
        'session_id': session_id,
        'user_id': user_id,
        'family_id': family_id
    }

def format_time_window(start, end):
    """Format time window for display"""
    if start is None or end is None:
        return "anytime"
    start_h, start_m = start // 60, start % 60
    end_h, end_m = end // 60, end % 60
    return f"{start_h:02d}:{start_m:02d}-{end_h:02d}:{end_m:02d}"

def show_saved_appliances(session_id):
    """Display all saved appliances in a nice table"""
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
    
    # Calculate total energy
    total_kwh = sum(
        a['power'] * a['number'] * a['func_time'] / 60.0 / 1000.0
        for a in appliances
    )
    print("-"*80)
    print(f"{'TOTAL DAILY ENERGY:':<48} {total_kwh:.2f} kWh/day")
    print("="*80 + "\n")

def chat_loop(session):
    """Main chat loop"""
    session_id = session['session_id']
    user_id = session['user_id']
    family_id = session['family_id']
    
    provider = "Google Gemini" if USE_GOOGLE else "Ollama"
    
    print("\n" + "="*80)
    print(f"⚡ ENERGY SURVEY CHATBOT (Powered by {provider})")
    print("="*80)
    print("\nI'll save appliances as we talk and show you what's stored!")
    print("\nCommands:")
    print("  'quit'     - Exit")
    print("  'list'     - Show all saved appliances")
    print("  'schedule' - Show time window analysis")
    print("="*80 + "\n")
    
    # Initial greeting
    greeting = "Hi! Tell me about your daily routine and the appliances you use!"
    print(f"Assistant: {greeting}\n")
    db.save_message(session_id, user_id, 'assistant', greeting)
    
    appliance_count = 0
    
    while True:
        user_message = input("You: ").strip()
        
        if user_message.lower() in ['quit', 'exit', 'bye']:
            show_saved_appliances(session_id)
            print(f"\n✓ Session complete! Collected {appliance_count} appliances.\n")
            break
        
        if user_message.lower() == 'list':
            show_saved_appliances(session_id)
            continue
        
        if user_message.lower() == 'schedule':
            context = build_smart_context(session_id, user_id, family_id)
            print("\n" + format_context_for_prompt(context) + "\n")
            continue
        
        if not user_message:
            continue
        
        # Save user message
        db.save_message(session_id, user_id, 'user', user_message)
        
        # Build context
        context = build_smart_context(session_id, user_id, family_id)
        context_summary = format_context_for_prompt(context)
        
        # Get conversation history (15 messages)
        recent_history = db.get_conversation_history(session_id, limit=15)
        
        # Get reference data
        defaults = db.get_all_appliance_defaults()
        reference_data = {
            d['appliance_type']: {'power': d['typical_power_watts']}
            for d in defaults
        }
        
        # Build system prompt
        system_prompt = build_system_prompt(context_summary, reference_data)
        
        # Format messages
        messages = []
        for msg in recent_history:
            clean_msg = re.sub(r'\[JSON_DATA_START\].*?\[JSON_DATA_END\]', '', 
                             msg['message_text'], flags=re.DOTALL).strip()
            if clean_msg:
                messages.append({
                    'role': msg['role'],
                    'content': clean_msg
                })
        
        # Call LLM (Google or Ollama)
        print("\n[Assistant is thinking...]")
        response = call_llm(messages, system_prompt)
        
        if not response['success']:
            print(f"\n❌ Error: {response['error']}\n")
            continue
        
        # Extract JSON if present
        extracted_data = extract_json(response['text'])
        
        # Save appliance if JSON found
        if extracted_data:
            print(f"\n💾 [Extracting appliance data...]")
            print(f"   Name: {extracted_data.get('name', 'Unknown')}")
            print(f"   Quantity: {extracted_data.get('number', 1)}")
            print(f"   Power: {extracted_data.get('power', '?')}W")
            print(f"   Usage: {extracted_data.get('func_time', 0)/60:.1f} hours/day")
            
            window_1 = extracted_data.get('window_1', [])
            if len(window_1) == 2:
                print(f"   Time: {format_time_window(window_1[0], window_1[1])}")
            
            # Validate
            validation = validate_appliance(extracted_data)
            
            if validation['valid'] or len(validation['errors']) <= 1:
                extracted_data['session_id'] = session_id
                extracted_data['user_id'] = user_id
                extracted_data['family_id'] = family_id
                
                # ========== DUPLICATE CHECK ADDED HERE ==========
                # Check if this appliance already exists
                window_start = window_1[0] if len(window_1) >= 2 else None
                appliance_name = extracted_data.get('name', '')
                
                if db.appliance_exists(session_id, appliance_name, window_start):
                    print(f"\n⚠️  DUPLICATE DETECTED!")
                    print(f"   '{appliance_name}' with same time window already saved.")
                    print(f"   Skipping duplicate entry.")
                else:
                    # Not a duplicate - save it
                    try:
                        saved = db.save_appliance(extracted_data)
                        if saved:
                            appliance_count += 1
                            print(f"\n✅ SAVED to database! (Total: {appliance_count} appliances)")
                            show_saved_appliances(session_id)
                        else:
                            print("\n⚠️  Save returned None")
                    except Exception as e:
                        print(f"\n❌ Save failed: {e}")
                # ================================================
            else:
                print(f"\n⚠️  Validation failed: {validation['errors']}")
        
        # Clean and show response
        clean_response = re.sub(r'\[JSON_DATA_START\].*?\[JSON_DATA_END\]', '', 
                               response['text'], flags=re.DOTALL).strip()
        clean_response = re.sub(r'\{[^}]*"name"[^}]*\}', '', clean_response).strip()
        
        if clean_response:
            print(f"\nAssistant: {clean_response}\n")
        
        # Save assistant response
        db.save_message(session_id, user_id, 'assistant', response['text'], extracted_data)

        
def main():
    """Main entry point"""
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