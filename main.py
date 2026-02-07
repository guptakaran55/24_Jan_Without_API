# main.py - MULTI-LLM SUPPORT: Ollama, Google Gemini, Perplexity, Claude
# Choose your LLM at runtime!

import uuid
import os
import re
from dotenv import load_dotenv

from database.connection import init_pool, close_pool
from database import queries as db
from services.context_service import build_smart_context, format_context_for_prompt
from utils.json_extractor import extract_all_json
from services.validation_service import validate_appliance

load_dotenv()

def select_llm_provider():
    """Let user choose which LLM to use"""
    print("\n" + "="*80)
    print("🤖 SELECT YOUR LLM PROVIDER")
    print("="*80)
    
    # Check which API keys are available
    providers = []
    
    if os.getenv('GOOGLE_API_KEY'):
        providers.append(('google', '🌐 Google Gemini (Fast, Free tier)'))
    
    if os.getenv('PERPLEXITY_API_KEY'):
        providers.append(('perplexity', '🔍 Perplexity (Research-focused)'))
    
    if os.getenv('ANTHROPIC_API_KEY'):
        providers.append(('claude', '🧠 Claude (Anthropic, High quality)'))
    
    # Ollama always available (local)
    providers.append(('ollama', '🏠 Ollama (Local, Free, Private)'))
    
    if len(providers) == 1:
        print(f"\nOnly one provider available: {providers[0][1]}")
        return providers[0][0]
    
    # Show options
    print("\nAvailable providers:")
    for i, (key, name) in enumerate(providers, 1):
        print(f"  {i}. {name}")
    
    # Get user choice
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

# Import the appropriate client
if SELECTED_LLM == 'google':
    from llm.google_client import call_google_gemini as call_llm
    PROVIDER_NAME = "Google Gemini"
elif SELECTED_LLM == 'perplexity':
    from llm.perplexity_client import call_perplexity as call_llm
    PROVIDER_NAME = "Perplexity"
elif SELECTED_LLM == 'claude':
    from llm.claude_client import call_claude as call_llm
    PROVIDER_NAME = "Claude (Anthropic)"
else:  # ollama
    from llm.client import call_ollama as call_llm
    PROVIDER_NAME = "Ollama (local)"

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
    """Main chat loop - WITH LOOP PREVENTION AND MULTIPLE APPLIANCE SUPPORT"""
    session_id = session['session_id']
    user_id = session['user_id']
    family_id = session['family_id']
    
    print("\n" + "="*80)
    print(f"⚡ ENERGY SURVEY CHATBOT (Powered by {PROVIDER_NAME})")
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
    last_response = None
    consecutive_duplicates = 0
    MAX_DUPLICATES = 3
    
    while True:
        user_message = input("You: ").strip()
        
        # Handle empty input - just skip
        if not user_message:
            continue
        
        # Exit keywords - check BEFORE processing
        exit_keywords = ['quit', 'exit', 'bye', 'goodbye', "that's it", 'thats it', 'nothing else', 'no more']
        if any(keyword in user_message.lower() for keyword in exit_keywords):
            show_saved_appliances(session_id)
            print(f"\n✓ Session complete! Collected {appliance_count} appliances. Thank you!\n")
            break
        
        # Special commands
        if user_message.lower() == 'list':
            show_saved_appliances(session_id)
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
        
        # Get conversation history
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
        
        # Call LLM
        print("\n[Assistant is thinking...]")
        response = call_llm(messages, system_prompt)
        
        if not response['success']:
            print(f"\n❌ Error: {response['error']}\n")
            continue
        
        # ========== EXTRACT ALL JSON BLOCKS (SUPPORTS MULTIPLE APPLIANCES) ==========
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
                
                # Validate
                validation = validate_appliance(extracted_data)
                
                if validation['valid'] or len(validation['errors']) <= 1:
                    extracted_data['session_id'] = session_id
                    extracted_data['user_id'] = user_id
                    extracted_data['family_id'] = family_id
                    
                    # Check for duplicate
                    window_start = window_1[0] if len(window_1) >= 2 else None
                    appliance_name = extracted_data.get('name', '')
                    
                    if db.appliance_exists(session_id, appliance_name, window_start):
                        consecutive_duplicates += 1
                        print(f"\n   ⚠️  DUPLICATE! ({consecutive_duplicates}/{MAX_DUPLICATES})")
                        print(f"      '{appliance_name}' with same time window already saved.")
                        
                        if consecutive_duplicates >= MAX_DUPLICATES:
                            print(f"\n⚠️  Too many duplicates detected. Ending conversation.\n")
                            show_saved_appliances(session_id)
                            break  # Exit the for loop
                    else:
                        # Not a duplicate - save it!
                        consecutive_duplicates = 0  # Reset counter
                        try:
                            saved = db.save_appliance(extracted_data)
                            if saved:
                                appliance_count += 1
                                print(f"\n   ✅ SAVED! (Total: {appliance_count} appliances)")
                            else:
                                print("\n   ⚠️  Save returned None")
                        except Exception as e:
                            print(f"\n   ❌ Save failed: {e}")
                else:
                    print(f"\n   ⚠️  Validation failed: {validation['errors']}")
            
            # Show all saved appliances after processing all from this response
            if appliance_count > 0:
                show_saved_appliances(session_id)
        # ==============================================================================
        
        # Clean and show response
        clean_response = re.sub(r'\[JSON_DATA_START\].*?\[JSON_DATA_END\]', '', 
                               response['text'], flags=re.DOTALL).strip()
        clean_response = re.sub(r'\{[^}]*"name"[^}]*\}', '', clean_response).strip()
        
        # LOOP DETECTION - prevent same response twice
        if clean_response and clean_response == last_response:
            print("\n⚠️  [Loop detected - the assistant seems stuck]")
            print("Type 'quit' to exit or ask a different question.\n")
            last_response = None  # Reset
            continue
        
        if clean_response:
            print(f"\nAssistant: {clean_response}\n")
            last_response = clean_response
        
        # Save assistant response (use last extracted data if multiple)
        last_extracted = extracted_appliances[-1] if extracted_appliances else None
        db.save_message(session_id, user_id, 'assistant', response['text'], last_extracted)

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