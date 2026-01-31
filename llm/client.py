# llm/client.py - FIXED with longer timeout
# Replace your current llm/client.py with this

import requests
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama2')

def call_ollama(messages, system_prompt):
    try:
        full_prompt = ''
        if system_prompt:
            full_prompt += f"SYSTEM: {system_prompt}\n\n"
        
        for msg in messages:
            role = 'USER' if msg['role'] == 'user' else 'ASSISTANT'
            full_prompt += f"{role}: {msg['content']}\n\n"
        
        full_prompt += 'ASSISTANT: '
        
        print(f"[Ollama] Calling model: {OLLAMA_MODEL}")
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                'model': OLLAMA_MODEL,
                'prompt': full_prompt,
                'stream': False,
                'options': {
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'num_predict': 500,  # Limit response length
                }
            },
            timeout=180  # INCREASED TO 3 MINUTES
        )
        
        if response.status_code == 200:
            return {'success': True, 'text': response.json().get('response', '')}
        else:
            return {'success': False, 'error': f"Ollama returned status {response.status_code}"}
            
    except requests.exceptions.ConnectionError:
        return {'success': False, 'error': 'Cannot connect to Ollama. Is it running?'}
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Ollama timed out (took longer than 3 minutes)'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def chat(user_message, system_prompt=''):
    messages = [{'role': 'user', 'content': user_message}]
    response = call_ollama(messages, system_prompt)
    if not response['success']:
        raise Exception(response['error'])
    return response['text']

def test_connection():
    print("Testing Ollama...")
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/version", timeout=5)
        if response.status_code == 200:
            print("✓ Ollama is running!")
            return True
    except:
        print("✗ Ollama is not running. Start it with: ollama serve")
        return False