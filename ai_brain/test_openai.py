"""Test OpenAI LLM integration"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from rag.llm_engine import LLMEngine

# Test data
question = "What is the project name?"
chunks = [
    "WELCOME TO GODREJ EMERALD WATERS. Located in Pimpri, Pune, this uptown lifestyle project offers luxury living.",
    "The project features 50 luxury apartments across 15 floors with amenities including rooftop pool and fitness center.",
    "Godrej Emerald Waters is developed by Godrej Properties, a leading real estate developer in India."
]

print("🧪 Testing OpenAI LLM Integration\n")
print(f"Question: {question}\n")

try:
    llm = LLMEngine()
    print(f"✅ LLM initialized: {llm.model_name}\n")
    
    print("Generating answer...\n")
    answer = llm.generate_answer(question, chunks)
    
    print("="*70)
    print("ANSWER:")
    print("="*70)
    print(answer)
    print()
    
    if "Error" not in answer:
        print("✅ SUCCESS: OpenAI LLM is working!")
    else:
        print("❌ FAILED: Check error message above")
        print("\nTroubleshooting:")
        print("1. Get API key from: https://platform.openai.com/api-keys")
        print("2. Add to .env file: OPENAI_API_KEY=sk-proj-your-key")
        print("3. Make sure you have billing set up")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    print("\nMake sure:")
    print("1. OpenAI library is installed: pip install openai")
    print("2. API key is set in .env file")
    print("3. Settings.py has openai_api_key field")
