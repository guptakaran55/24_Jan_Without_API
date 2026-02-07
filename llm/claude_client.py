# llm/claude_client.py
# Anthropic Claude API client - WITH CONFIGURABLE MODEL

import os
import anthropic

def call_claude(messages, system_prompt):
    """
    Call Anthropic Claude API
    
    Args:
        messages: List of {'role': 'user'|'assistant', 'content': str}
        system_prompt: System instructions
    
    Returns:
        dict: {'success': bool, 'text': str, 'error': str}
    """
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        return {
            'success': False,
            'text': '',
            'error': 'ANTHROPIC_API_KEY not found in environment'
        }
    
    # Get model from env or use default
    model = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
    
    try:
        # Initialize Claude client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Call Claude API
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system=system_prompt,
            messages=messages
        )
        
        # Extract text from response
        text = response.content[0].text
        
        return {
            'success': True,
            'text': text,
            'error': None
        }
        
    except anthropic.APIError as e:
        return {
            'success': False,
            'text': '',
            'error': f'Claude API error: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'text': '',
            'error': f'Claude error: {str(e)}'
        }

# Test function
if __name__ == "__main__":
    print("Testing Claude API...")
    
    model = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
    print(f"Using model: {model}")
    
    messages = [{"role": "user", "content": "Say hello!"}]
    system_prompt = "You are a helpful assistant."
    
    result = call_claude(messages, system_prompt)
    
    if result['success']:
        print(f"✓ Success!\nResponse: {result['text']}")
    else:
        print(f"❌ Error: {result['error']}")