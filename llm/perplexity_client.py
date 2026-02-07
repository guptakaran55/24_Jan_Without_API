# llm/perplexity_client.py - FIXED message format
# Perplexity requires strict user/assistant alternation

import os
import requests

def call_perplexity(messages, system_prompt):
    """
    Call Perplexity API with proper message alternation
    """
    
    api_key = os.getenv('PERPLEXITY_API_KEY')
    
    if not api_key:
        return {
            'success': False,
            'text': '',
            'error': 'PERPLEXITY_API_KEY not found in environment'
        }
    
    # Get model from env or use default
    model = os.getenv('PERPLEXITY_MODEL', 'sonar-pro')
    
    # Perplexity API endpoint
    url = "https://api.perplexity.ai/chat/completions"
    
    # Format messages - Perplexity requires strict alternation
    formatted_messages = []
    
    # Add user messages only (skip assistant messages that aren't responses)
    last_role = None
    for msg in messages:
        role = msg['role']
        content = msg['content']
        
        # Skip consecutive messages with same role
        if role == last_role:
            # Merge content if same role appears twice
            if formatted_messages:
                formatted_messages[-1]['content'] += f"\n{content}"
            continue
        
        formatted_messages.append({
            "role": role,
            "content": content
        })
        last_role = role
    
    # Ensure last message is from user
    if formatted_messages and formatted_messages[-1]['role'] != 'user':
        # Add a dummy user message
        formatted_messages.append({
            "role": "user",
            "content": "Please respond."
        })
    
    # API request payload
    payload = {
        "model": model,
        "messages": formatted_messages,
        "max_tokens": 2000,
        "temperature": 0.7,
        "top_p": 0.9,
        "stream": False
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        text = data['choices'][0]['message']['content']
        
        return {
            'success': True,
            'text': text,
            'error': None
        }
        
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'text': '',
            'error': 'Perplexity API timeout (30s exceeded)'
        }
    except requests.exceptions.HTTPError as e:
        error_msg = f"Perplexity API error: {e.response.status_code}"
        try:
            error_detail = e.response.json()
            error_msg += f" - {error_detail.get('error', {}).get('message', '')}"
        except:
            pass
        return {
            'success': False,
            'text': '',
            'error': error_msg
        }
    except Exception as e:
        return {
            'success': False,
            'text': '',
            'error': f'Perplexity error: {str(e)}'
        }