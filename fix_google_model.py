# fix_google_model.py
# Run this to see available models and update your .env

import os
import google.generativeai as genai
from dotenv import load_dotenv, set_key

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not GOOGLE_API_KEY:
    print("❌ GOOGLE_API_KEY not found in .env file!")
    print("Please add your Google API key to .env")
    exit(1)

genai.configure(api_key=GOOGLE_API_KEY)

print("="*80)
print("🔍 FINDING AVAILABLE GOOGLE GEMINI MODELS")
print("="*80)

# List all models
available_models = []
print("\nScanning for models that support text generation...\n")

try:
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            # Extract just the model name (remove 'models/' prefix)
            model_name = model.name.replace('models/', '')
            available_models.append(model_name)
            
            # Mark recommended models
            if 'flash' in model_name.lower() and 'latest' in model_name.lower():
                print(f"✨ {model_name} (RECOMMENDED - Fast & Free)")
            elif 'pro' in model_name.lower() and 'latest' in model_name.lower():
                print(f"⭐ {model_name} (Smart but slower)")
            else:
                print(f"   {model_name}")
    
    if not available_models:
        print("❌ No models found! Check your API key.")
        exit(1)
    
    # Recommend best model
    print("\n" + "="*80)
    print("RECOMMENDATION:")
    print("="*80)
    
    recommended = None
    if any('gemini-1.5-flash-latest' in m for m in available_models):
        recommended = 'gemini-1.5-flash-latest'
    elif any('gemini-1.5-flash' in m for m in available_models):
        recommended = [m for m in available_models if 'gemini-1.5-flash' in m][0]
    elif any('gemini-1.5-pro-latest' in m for m in available_models):
        recommended = 'gemini-1.5-pro-latest'
    elif any('gemini-pro' in m for m in available_models):
        recommended = 'gemini-pro'
    else:
        recommended = available_models[0]
    
    print(f"\nBest model for you: {recommended}")
    
    # Test the model
    print(f"\nTesting {recommended}...")
    try:
        test_model = genai.GenerativeModel(recommended)
        response = test_model.generate_content("Say hello in one word")
        print(f"✓ Model works! Response: {response.text}")
        
        # Update .env file
        env_path = os.path.join(os.getcwd(), '.env')
        
        print("\n" + "="*80)
        print("UPDATING YOUR .env FILE")
        print("="*80)
        
        # Check current value
        current_model = os.getenv('GOOGLE_MODEL', 'not set')
        print(f"\nCurrent: GOOGLE_MODEL={current_model}")
        print(f"New:     GOOGLE_MODEL={recommended}")
        
        choice = input("\nUpdate .env file? (yes/no): ").strip().lower()
        
        if choice == 'yes':
            set_key(env_path, 'GOOGLE_MODEL', recommended)
            print(f"\n✅ Updated! Your .env now has:")
            print(f"   GOOGLE_MODEL={recommended}")
            print("\nYou can now run: python main.py")
        else:
            print(f"\n💡 To update manually, change your .env to:")
            print(f"   GOOGLE_MODEL={recommended}")
        
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        print("\nTry the next available model from the list above.")
    
except Exception as e:
    print(f"\n❌ Error listing models: {e}")
    print("\nPossible issues:")
    print("  1. Invalid API key")
    print("  2. No internet connection")
    print("  3. API quota exceeded")

print("\n" + "="*80)