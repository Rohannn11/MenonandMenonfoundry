import os
from foundry_brain import FoundryBrain

def run_test():
    print("=== 🧪 TESTING NEW GROQ PIPELINE ===")
    
    # 1. Init
    try:
        print("[1] Initializing Brain (Groq + HF Embeddings)...")
        brain = FoundryBrain()
        print("    ✅ Success.")
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        return

    # 2. Test Market Data (Latency check)
    print("\n[2] Testing Market Data (External)...")
    ans, src, intent = brain.ask("What is the copper price?")
    print(f"    Intent: {intent}")
    print(f"    Source: {src}")
    print(f"    Answer: {ans[:100]}...")

    # 3. Test SQL (Relational Context check)
    print("\n[3] Testing SQL Generation (Database)...")
    ans, src, intent = brain.ask("Count total rows in material_master")
    print(f"    Intent: {intent}")
    print(f"    Source: {src}")
    print(f"    Answer: {ans[:100]}...")

if __name__ == "__main__":
    run_test()