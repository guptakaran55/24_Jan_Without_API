# llm/google_client.py - FIXED VERSION
# Replace your current llm/google_client.py with this

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Google AI
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_MODEL = os.getenv('GOOGLE_MODEL', 'gemini-1.5-flash')

# Fix model name if needed
if GOOGLE_MODEL == 'gemini-1.5-flash':
    GOOGLE_MODEL = 'gemini-1.5-flash-latest'
elif GOOGLE_MODEL == 'gemini-1.5-pro':
    GOOGLE_MODEL = 'gemini-1.5-pro-latest'

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

def call_google_gemini(messages, system_prompt):
    """
    Call Google Gemini API
    
    Args:
        messages: List of {role, content} dicts
        system_prompt: System instructions
    
    Returns:
        {'success': True/False, 'text': response or 'error': message}
    """
    try:
        if not GOOGLE_API_KEY:
            return {
                'success': False, 
                'error': 'GOOGLE_API_KEY not set in .env file'
            }
        
        # Initialize model with system instruction
        model = genai.GenerativeModel(
            model_name=GOOGLE_MODEL,
            generation_config={
                'temperature': 0.7,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 2048,
            },
            system_instruction=system_prompt if system_prompt else None
        )
        
        # Build conversation history for Gemini format
        history = []
        
        # Add conversation messages (skip the last one - we'll send it separately)
        for msg in messages[:-1]:
            role = 'model' if msg['role'] == 'assistant' else 'user'
            history.append({
                'role': role,
                'parts': [msg['content']]
            })
        
        # Start chat with history
        chat = model.start_chat(history=history)
        
        # Send last message
        last_message = messages[-1]['content'] if messages else "Hello"
        response = chat.send_message(last_message)
        
        return {
            'success': True,
            'text': response.text
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Handle common errors
        if 'API_KEY' in error_msg.upper() or 'API key' in error_msg:
            return {
                'success': False,
                'error': 'Invalid Google API key. Check your .env file.'
            }
        elif 'QUOTA' in error_msg.upper() or 'quota' in error_msg.lower():
            return {
                'success': False,
                'error': 'Google API quota exceeded. Wait a moment or upgrade plan.'
            }
        elif 'RATE_LIMIT' in error_msg.upper() or 'rate limit' in error_msg.lower():
            return {
                'success': False,
                'error': 'Rate limit exceeded. Slow down your requests.'
            }
        elif '404' in error_msg or 'not found' in error_msg.lower():
            return {
                'success': False,
                'error': f'Model not found. Try: gemini-1.5-flash-latest or gemini-1.5-pro-latest'
            }
        else:
            return {
                'success': False,
                'error': f'Google API error: {error_msg}'
            }

def test_google_connection():
    """Test Google Gemini API connection"""
    print("Testing Google Gemini API...")
    print(f"Model: {GOOGLE_MODEL}")
    
    if not GOOGLE_API_KEY:
        print("✗ GOOGLE_API_KEY not found in .env")
        return False
    
    try:
        # List available models first
        print("\nAvailable models:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"  • {m.name}")
        
        print(f"\nTesting model: {GOOGLE_MODEL}")
        
        model = genai.GenerativeModel(GOOGLE_MODEL)
        response = model.generate_content("Say 'Hello, I am working!' in one sentence.")
        
        if response.text:
            print(f"\n✓ Google Gemini API is working!")
            print(f"✓ Using model: {GOOGLE_MODEL}")
            print(f"✓ Response: {response.text}")
            return True
        else:
            print("✗ No response from Google API")
            return False
            
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nTry updating your .env to:")
        print("GOOGLE_MODEL=gemini-1.5-flash-latest")
        return False

if __name__ == "__main__":
    test_google_connection()