# test_ollama.py
from llm.client import test_connection

if __name__ == "__main__":
    if test_connection():
        print("\n✓ Ollama is ready!")
    else:
        print("\n✗ Please start Ollama: ollama serve")
