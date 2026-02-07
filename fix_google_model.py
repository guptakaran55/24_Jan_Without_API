# discover_all_models.py - FIXED WITH CURRENT MODELS
# Discover available models for Google, Perplexity, and Anthropic

import os
import sys
from dotenv import load_dotenv, set_key

load_dotenv()

def print_header(title):
    """Print a nice header"""
    print("\n" + "="*80)
    print(f"🔍 {title}")
    print("="*80 + "\n")

def discover_google_models():
    """List available Google Gemini models"""
    print_header("GOOGLE GEMINI MODELS")
    
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ GOOGLE_API_KEY not found in .env")
        return None
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        available_models = []
        print("Scanning for models...\n")
        
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                model_name = model.name.replace('models/', '')
                available_models.append(model_name)
                
                # Highlight working models
                if 'flash-latest' in model_name.lower():
                    print(f"✨ {model_name} (RECOMMENDED)")
                elif 'pro-latest' in model_name.lower():
                    print(f"⭐ {model_name}")
                elif model_name in ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest']:
                    print(f"✨ {model_name} (RECOMMENDED)")
                else:
                    print(f"   {model_name}")
        
        if not available_models:
            print("❌ No models found")
            return None
        
        # Try to find a working model
        priority_models = [
            'gemini-flash-latest',
            'gemini-2.5-flash',
            'gemini-2.0-flash',
            'gemini-1.5-flash-latest',
            'gemini-1.5-flash'
        ]
        
        recommended = None
        for candidate in priority_models:
            if candidate in available_models:
                recommended = candidate
                break
        
        if not recommended:
            recommended = available_models[0]
        
        print(f"\n✅ Recommended: {recommended}")
        
        # Test it
        try:
            test_model = genai.GenerativeModel(recommended)
            response = test_model.generate_content("Say hello in one word")
            print(f"✓ Test successful! Response: {response.text.strip()}")
            return recommended
        except Exception as e:
            print(f"⚠️  Test failed: {e}")
            # Try another model
            for candidate in available_models[:5]:
                if candidate != recommended:
                    try:
                        print(f"   Trying {candidate}...")
                        test_model = genai.GenerativeModel(candidate)
                        response = test_model.generate_content("Hi")
                        print(f"   ✓ {candidate} works!")
                        return candidate
                    except:
                        continue
            return recommended
            
    except ImportError:
        print("❌ google-generativeai not installed")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def discover_perplexity_models():
    """List available Perplexity models - UPDATED FOR 2025"""
    print_header("PERPLEXITY AI MODELS")
    
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        print("❌ PERPLEXITY_API_KEY not found in .env")
        return None
    
    # UPDATED models from Perplexity docs (Feb 2025)
    # Source: https://docs.perplexity.ai/guides/model-cards
    models = {
        'sonar-pro': {
            'speed': '⚡⚡',
            'quality': '⭐⭐⭐⭐⭐',
            'cost': '$$',
            'desc': 'Best balance (RECOMMENDED)'
        },
        'sonar': {
            'speed': '⚡⚡⚡',
            'quality': '⭐⭐⭐⭐',
            'cost': '$',
            'desc': 'Fast and affordable'
        },
        'sonar-reasoning': {
            'speed': '⚡',
            'quality': '⭐⭐⭐⭐⭐',
            'cost': '$$$',
            'desc': 'Advanced reasoning'
        }
    }
    
    print("Available models:\n")
    for model_name, info in models.items():
        print(f"{'✨' if 'RECOMMENDED' in info['desc'] else '  '} {model_name}")
        print(f"   Speed: {info['speed']}  Quality: {info['quality']}  Cost: {info['cost']}")
        print(f"   {info['desc']}\n")
    
    recommended = 'sonar-pro'
    print(f"✅ Recommended: {recommended}")
    
    # Test it
    try:
        import requests
        url = "https://api.perplexity.ai/chat/completions"
        
        payload = {
            "model": recommended,
            "messages": [{"role": "user", "content": "Say hi in one word"}],
            "max_tokens": 10
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            text = data['choices'][0]['message']['content']
            print(f"✓ Test successful! Response: {text.strip()}")
            return recommended
        else:
            print(f"⚠️  Test returned status {response.status_code}")
            error = response.json()
            print(f"   {error.get('error', {}).get('message', 'Unknown error')}")
            # Try fallback
            for fallback in ['sonar', 'sonar-reasoning']:
                if fallback != recommended:
                    print(f"   Trying {fallback}...")
                    payload['model'] = fallback
                    try:
                        r = requests.post(url, json=payload, headers=headers, timeout=10)
                        if r.status_code == 200:
                            print(f"   ✓ {fallback} works!")
                            return fallback
                    except:
                        continue
            return 'sonar'  # Default fallback
        
    except ImportError:
        print("❌ requests not installed")
        return recommended
    except Exception as e:
        print(f"⚠️  Test failed: {e}")
        return recommended

def discover_anthropic_models():
    """List available Anthropic Claude models - UPDATED FOR 2025"""
    print_header("ANTHROPIC CLAUDE MODELS")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in .env")
        return None
    
    # UPDATED models (Feb 2025)
    # Source: https://docs.anthropic.com/en/docs/about-claude/models
    models = {
        'claude-3-5-sonnet-20241022': {
            'speed': '⚡⚡',
            'quality': '⭐⭐⭐⭐⭐',
            'cost': '$$',
            'desc': 'Best balance (RECOMMENDED)'
        },
        'claude-3-5-haiku-20241022': {
            'speed': '⚡⚡⚡',
            'quality': '⭐⭐⭐⭐',
            'cost': '$',
            'desc': 'Fastest and cheapest'
        },
        'claude-3-opus-20240229': {
            'speed': '⚡',
            'quality': '⭐⭐⭐⭐⭐',
            'cost': '$$$$',
            'desc': 'Most powerful'
        }
    }
    
    print("Available models:\n")
    for model_name, info in models.items():
        print(f"{'✨' if 'RECOMMENDED' in info['desc'] else '  '} {model_name}")
        print(f"   Speed: {info['speed']}  Quality: {info['quality']}  Cost: {info['cost']}")
        print(f"   {info['desc']}\n")
    
    recommended = 'claude-3-5-sonnet-20241022'
    print(f"✅ Recommended: {recommended}")
    
    # Test it
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model=recommended,
            max_tokens=10,
            messages=[{"role": "user", "content": "Say hi in one word"}]
        )
        
        text = response.content[0].text
        print(f"✓ Test successful! Response: {text.strip()}")
        return recommended
        
    except ImportError:
        print("❌ anthropic not installed")
        return recommended
    except Exception as e:
        error_str = str(e)
        print(f"⚠️  Test failed: {error_str}")
        
        # Try fallback models
        if '404' in error_str or 'not_found' in error_str:
            print("   Model not found, trying alternatives...")
            for fallback in ['claude-3-5-haiku-20241022', 'claude-3-opus-20240229']:
                try:
                    print(f"   Trying {fallback}...")
                    client = anthropic.Anthropic(api_key=api_key)
                    r = client.messages.create(
                        model=fallback,
                        max_tokens=10,
                        messages=[{"role": "user", "content": "Hi"}]
                    )
                    print(f"   ✓ {fallback} works!")
                    return fallback
                except:
                    continue
        
        return 'claude-3-5-haiku-20241022'  # Cheapest fallback

def update_env_file(updates):
    """Update .env file with recommended models"""
    print_header("UPDATE .env FILE")
    
    env_path = os.path.join(os.getcwd(), '.env')
    
    if not updates:
        print("❌ No models to update")
        return
    
    print("Recommended configuration:\n")
    for key, value in updates.items():
        if value:
            current = os.getenv(key, 'not set')
            print(f"  {key}")
            print(f"    Current: {current}")
            print(f"    New:     {value}\n")
    
    choice = input("Update .env with these values? (yes/no): ").strip().lower()
    
    if choice == 'yes':
        for key, value in updates.items():
            if value:
                set_key(env_path, key, value)
        
        print("\n✅ Updated .env file!")
        print("\nYour .env now has:")
        for key, value in updates.items():
            if value:
                print(f"  {key}={value}")
        print("\n🚀 You can now run: python main.py")
    else:
        print("\n💡 To update manually, add these to your .env:")
        for key, value in updates.items():
            if value:
                print(f"  {key}={value}")

def main():
    """Main discovery function"""
    print("="*80)
    print("🤖 MODEL DISCOVERY TOOL (Updated Feb 2025)")
    print("="*80)
    print("\nThis tool will:")
    print("  1. Check which API keys you have")
    print("  2. List CURRENT available models")
    print("  3. Test the models")
    print("  4. Update your .env file")
    
    updates = {}
    
    # Discover Google models
    google_model = discover_google_models()
    if google_model:
        updates['GOOGLE_MODEL'] = google_model
    
    # Discover Perplexity models
    perplexity_model = discover_perplexity_models()
    if perplexity_model:
        updates['PERPLEXITY_MODEL'] = perplexity_model
    
    # Discover Anthropic models
    anthropic_model = discover_anthropic_models()
    if anthropic_model:
        updates['ANTHROPIC_MODEL'] = anthropic_model
    
    # Offer to update .env
    if updates:
        update_env_file(updates)
    else:
        print_header("NO MODELS FOUND")
        print("❌ No API keys or all tests failed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()