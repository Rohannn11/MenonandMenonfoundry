# test_brain.py
from dotenv import load_dotenv
from core.brain import AgentBrain

load_dotenv()

print("--- 🧠 DIAGNOSTIC TEST: BRAIN LAYER ---")

try:
    print("1. Initializing Llama 3 Agent...")
    bot = AgentBrain()
    
    query = "What is the current price of Copper?"
    print(f"\n2. Asking: '{query}'")
    
    response = bot.ask(query)
    print(f"   🤖 Agent Answer: {response}")
    
    print("\n✅ Brain is HEALTHY.")
except Exception as e:
    print(f"\n❌ Brain FAILED: {e}")