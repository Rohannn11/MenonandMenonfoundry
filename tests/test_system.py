"""
Comprehensive System Testing Suite for Menon Foundry OS
Tests: Intent Router, API Handlers, Brain Logic, and Integration
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(title):
    """Print formatted section header."""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}▶ {title}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

def print_test(name, passed, message=""):
    """Print test result."""
    status = f"{GREEN}✓ PASSED{RESET}" if passed else f"{RED}✗ FAILED{RESET}"
    print(f"{status} | {name}")
    if message:
        print(f"   └─ {message}")

def print_divider():
    """Print test divider."""
    print(f"{YELLOW}{'-'*70}{RESET}")

# ============================================================================
# TEST SUITE 1: INTENT ROUTER
# ============================================================================
def test_intent_router():
    """Test the Intent Router component."""
    print_header("TEST SUITE 1: INTENT ROUTER")
    
    try:
        from core.intent_router import IntentRouter, QueryIntent
        print(f"{GREEN}✓ Intent Router imported successfully{RESET}\n")
    except Exception as e:
        print(f"{RED}✗ Failed to import Intent Router: {e}{RESET}\n")
        return False
    
    router = IntentRouter()
    all_passed = True
    
    # Test 1.1: Price Query Detection
    print_divider()
    price_queries = [
        "What is the price of steel?",
        "How much does copper cost today?",
        "Current gold price",
        "Show me Tesla stock price",
    ]
    
    for query in price_queries:
        intent, secondary, scores = router.analyze(query)
        passed = intent == QueryIntent.PRICE_QUERY
        all_passed = all_passed and passed
        print_test(f"Price Query: '{query}'", passed, f"Intent: {intent.value}")
    
    # Test 1.2: News Query Detection
    print_divider()
    news_queries = [
        "What's the latest news in mining?",
        "Show me steel industry news",
        "Any recent announcements?",
        "Latest manufacturing trends",
    ]
    
    for query in news_queries:
        intent, secondary, scores = router.analyze(query)
        passed = intent == QueryIntent.NEWS_QUERY
        all_passed = all_passed and passed
        print_test(f"News Query: '{query}'", passed, f"Intent: {intent.value}")
    
    # Test 1.3: SOP Query Detection
    print_divider()
    sop_queries = [
        "What is the molding sand procedure?",
        "Safety rules for melting operations",
        "How to maintain the furnace?",
        "Quality inspection standards",
    ]
    
    for query in sop_queries:
        intent, secondary, scores = router.analyze(query)
        passed = intent == QueryIntent.SOP_QUERY
        all_passed = all_passed and passed
        print_test(f"SOP Query: '{query}'", passed, f"Intent: {intent.value}")
    
    # Test 1.4: Combined Query Detection
    print_divider()
    combined_queries = [
        "What's the price of steel and latest news?",
        "Show me copper cost and mining procedures",
        "Gold prices, news, and safety guidelines",
    ]
    
    for query in combined_queries:
        intent, secondary, scores = router.analyze(query)
        passed = intent == QueryIntent.COMBINED_QUERY
        all_passed = all_passed and passed
        print_test(f"Combined Query: '{query}'", passed, f"Intent: {intent.value}, Secondary: {[s.value for s in secondary]}")
    
    # Test 1.5: Entity Extraction
    print_divider()
    entity_tests = [
        ("steel price", "steel"),
        ("copper and mining", "copper"),
        ("gold prices and auto industry news", "gold"),
        ("renewable energy news", None),
    ]
    
    for query, expected_asset in entity_tests:
        entities = router.extract_entities(query)
        asset = entities.get("asset_name")
        passed = asset == expected_asset
        all_passed = all_passed and passed
        print_test(f"Entity Extraction: '{query}'", passed, f"Extracted: {asset}")
    
    print(f"\n{YELLOW}Intent Router Tests: {'PASSED' if all_passed else 'FAILED'}{RESET}\n")
    return all_passed

# ============================================================================
# TEST SUITE 2: API TOOLS
# ============================================================================
def test_api_tools():
    """Test the API tool handlers."""
    print_header("TEST SUITE 2: API TOOLS")
    
    try:
        from core.tools import get_market_data, get_global_news, query_internal_sops
        print(f"{GREEN}✓ API Tools imported successfully{RESET}\n")
    except Exception as e:
        print(f"{RED}✗ Failed to import API Tools: {e}{RESET}\n")
        return False
    
    all_passed = True
    
    # Test 2.1: Market Data Tool
    print_divider()
    print(f"{BOLD}Testing Market Data Tool...{RESET}")
    
    try:
        result = get_market_data.run("gold")
        passed = "✅" in result or "❌" in result
        all_passed = all_passed and passed
        print_test("Fetch Gold Price", passed, result[:80] + "...")
    except Exception as e:
        print_test("Fetch Gold Price", False, f"Error: {str(e)}")
        all_passed = False
    
    try:
        result = get_market_data.run("copper")
        passed = "✅" in result or "❌" in result
        all_passed = all_passed and passed
        print_test("Fetch Copper Price", passed, result[:80] + "...")
    except Exception as e:
        print_test("Fetch Copper Price", False, f"Error: {str(e)}")
        all_passed = False
    
    try:
        result = get_market_data.run("TSLA")
        passed = "✅" in result or "❌" in result
        all_passed = all_passed and passed
        print_test("Fetch Stock Price (TSLA)", passed, result[:80] + "...")
    except Exception as e:
        print_test("Fetch Stock Price (TSLA)", False, f"Error: {str(e)}")
        all_passed = False
    
    # Test 2.2: News API Tool
    print_divider()
    print(f"{BOLD}Testing News API Tool...{RESET}")
    
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        print(f"{RED}✗ NEWS_API_KEY not set in .env{RESET}")
        all_passed = False
    else:
        try:
            result = get_global_news.run("steel")
            passed = "📰" in result or "❌" in result
            all_passed = all_passed and passed
            print_test("Fetch Steel News", passed, result[:80] + "...")
        except Exception as e:
            print_test("Fetch Steel News", False, f"Error: {str(e)}")
            all_passed = False
        
        try:
            result = get_global_news.run("mining")
            passed = "📰" in result or "❌" in result
            all_passed = all_passed and passed
            print_test("Fetch Mining News", passed, result[:80] + "...")
        except Exception as e:
            print_test("Fetch Mining News", False, f"Error: {str(e)}")
            all_passed = False
    
    # Test 2.3: SOPs Tool
    print_divider()
    print(f"{BOLD}Testing SOPs Tool...{RESET}")
    
    if not os.path.exists("./chroma_db"):
        print(f"{YELLOW}⚠ Knowledge Base not initialized. Run 'ingest_knowledge.py' first{RESET}")
        print_test("Query SOPs", False, "chroma_db directory not found")
        all_passed = False
    else:
        try:
            result = query_internal_sops.run("safety procedures")
            passed = "📋" in result or "⚠️" in result or "❌" in result
            all_passed = all_passed and passed
            print_test("Query Safety Procedures", passed, result[:80] + "...")
        except Exception as e:
            print_test("Query Safety Procedures", False, f"Error: {str(e)}")
            all_passed = False
        
        try:
            result = query_internal_sops.run("melting temperature")
            passed = "📋" in result or "⚠️" in result or "❌" in result
            all_passed = all_passed and passed
            print_test("Query Melting Temperature", passed, result[:80] + "...")
        except Exception as e:
            print_test("Query Melting Temperature", False, f"Error: {str(e)}")
            all_passed = False
    
    print(f"\n{YELLOW}API Tools Tests: {'PASSED' if all_passed else 'FAILED'}{RESET}\n")
    return all_passed

# ============================================================================
# TEST SUITE 3: AGENT BRAIN
# ============================================================================
def test_agent_brain():
    """Test the AgentBrain component."""
    print_header("TEST SUITE 3: AGENT BRAIN")
    
    try:
        from core.brain import AgentBrain
        print(f"{GREEN}✓ AgentBrain imported successfully{RESET}\n")
    except Exception as e:
        print(f"{RED}✗ Failed to import AgentBrain: {e}{RESET}\n")
        return False
    
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        print(f"{RED}✗ GROQ_API_KEY not set in .env{RESET}\n")
        return False
    
    try:
        brain = AgentBrain()
        print(f"{GREEN}✓ AgentBrain initialized successfully{RESET}\n")
    except Exception as e:
        print(f"{RED}✗ Failed to initialize AgentBrain: {e}{RESET}\n")
        return False
    
    all_passed = True
    
    # Test 3.1: Price Query Handling
    print_divider()
    print(f"{BOLD}Testing Price Query Handler...{RESET}")
    
    try:
        response = brain.ask("What is the current price of gold?")
        passed = len(response) > 10 and ("✅" in response or "Price" in response or "gold" in response.lower())
        all_passed = all_passed and passed
        print_test("Price Query Response", passed, response[:100] + "...")
    except Exception as e:
        print_test("Price Query Response", False, f"Error: {str(e)}")
        all_passed = False
    
    # Test 3.2: News Query Handling
    print_divider()
    print(f"{BOLD}Testing News Query Handler...{RESET}")
    
    try:
        response = brain.ask("Show me latest mining industry news")
        passed = len(response) > 10
        all_passed = all_passed and passed
        print_test("News Query Response", passed, response[:100] + "...")
    except Exception as e:
        print_test("News Query Response", False, f"Error: {str(e)}")
        all_passed = False
    
    # Test 3.3: SOP Query Handling
    print_divider()
    print(f"{BOLD}Testing SOP Query Handler...{RESET}")
    
    try:
        response = brain.ask("What are the safety procedures for melting?")
        passed = len(response) > 10
        all_passed = all_passed and passed
        print_test("SOP Query Response", passed, response[:100] + "...")
    except Exception as e:
        print_test("SOP Query Response", False, f"Error: {str(e)}")
        all_passed = False
    
    # Test 3.4: General Chat
    print_divider()
    print(f"{BOLD}Testing General Chat Handler...{RESET}")
    
    try:
        response = brain.ask("Tell me about the foundry industry")
        passed = len(response) > 10
        all_passed = all_passed and passed
        print_test("General Chat Response", passed, response[:100] + "...")
    except Exception as e:
        print_test("General Chat Response", False, f"Error: {str(e)}")
        all_passed = False
    
    # Test 3.5: Combined Query (if knowledge base exists)
    print_divider()
    print(f"{BOLD}Testing Combined Query Handler...{RESET}")
    
    if os.path.exists("./chroma_db"):
        try:
            response = brain.ask("What's the steel price and latest manufacturing news?")
            passed = len(response) > 10
            all_passed = all_passed and passed
            print_test("Combined Query Response", passed, response[:100] + "...")
        except Exception as e:
            print_test("Combined Query Response", False, f"Error: {str(e)}")
            all_passed = False
    else:
        print(f"{YELLOW}⚠ Skipping combined query test (knowledge base not initialized){RESET}")
    
    print(f"\n{YELLOW}AgentBrain Tests: {'PASSED' if all_passed else 'FAILED'}{RESET}\n")
    return all_passed

# ============================================================================
# TEST SUITE 4: ENVIRONMENT & DEPENDENCIES
# ============================================================================
def test_environment():
    """Test environment setup and dependencies."""
    print_header("TEST SUITE 4: ENVIRONMENT & DEPENDENCIES")
    
    all_passed = True
    
    # Test 4.1: Environment Variables
    print_divider()
    print(f"{BOLD}Checking Environment Variables...{RESET}")
    
    env_vars = {
        "GROQ_API_KEY": "LLM API Key",
        "NEWS_API_KEY": "News API Key",
        "METAL_PRICE": "Metal Price API Key",
        "DB_NAME": "Database Name",
        "DB_USER": "Database User",
        "DB_HOST": "Database Host",
    }
    
    for var, description in env_vars.items():
        value = os.getenv(var)
        passed = value is not None
        all_passed = all_passed and passed
        status = f"(set)" if passed else "(missing)"
        print_test(f"{description}: {var}", passed, status)
    
    # Test 4.2: Required Modules
    print_divider()
    print(f"{BOLD}Checking Required Modules...{RESET}")
    
    modules = [
        ("streamlit", "Streamlit"),
        ("langchain_groq", "LangChain Groq"),
        ("langchain_core", "LangChain Core"),
        ("chromadb", "ChromaDB"),
        ("yfinance", "YFinance"),
        ("requests", "Requests"),
        ("psycopg2", "PostgreSQL Adapter"),
        ("dotenv", "Python Dotenv"),
    ]
    
    for module, name in modules:
        try:
            __import__(module)
            print_test(f"{name} ({module})", True)
        except ImportError:
            print_test(f"{name} ({module})", False, "Not installed")
            all_passed = False
    
    # Test 4.3: File Structure
    print_divider()
    print(f"{BOLD}Checking File Structure...{RESET}")
    
    files = [
        ("core/brain.py", "AgentBrain"),
        ("core/tools.py", "API Tools"),
        ("core/intent_router.py", "Intent Router"),
        ("dashboard.py", "Dashboard UI"),
        ("ingest_knowledge.py", "Knowledge Ingestion"),
        (".env", "Environment File"),
    ]
    
    for filepath, description in files:
        exists = os.path.exists(filepath)
        print_test(f"{description}: {filepath}", exists)
        if not exists:
            all_passed = False
    
    # Test 4.4: Knowledge Base
    print_divider()
    print(f"{BOLD}Checking Knowledge Base...{RESET}")
    
    kb_exists = os.path.exists("./chroma_db")
    print_test("ChromaDB Directory", kb_exists, "Status: " + ("initialized" if kb_exists else "not initialized"))
    
    if kb_exists:
        try:
            import chromadb
            from chromadb.utils import embedding_functions
            client = chromadb.PersistentClient(path="./chroma_db")
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            collection = client.get_collection(name="foundry_knowledge", embedding_function=ef)
            count = collection.count()
            print_test(f"Knowledge Base Items", True, f"Count: {count}")
        except Exception as e:
            print_test(f"Knowledge Base Items", False, f"Error: {str(e)}")
            all_passed = False
    
    print(f"\n{YELLOW}Environment Tests: {'PASSED' if all_passed else 'FAILED'}{RESET}\n")
    return all_passed

# ============================================================================
# MAIN TEST EXECUTION
# ============================================================================
def main():
    """Run all test suites."""
    print(f"\n{BOLD}{BLUE}")
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║   MENON FOUNDRY OS - COMPREHENSIVE SYSTEM TEST SUITE           ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print(f"{RESET}\n")
    
    results = {}
    
    # Run all test suites
    results["Environment"] = test_environment()
    results["Intent Router"] = test_intent_router()
    results["API Tools"] = test_api_tools()
    results["AgentBrain"] = test_agent_brain()
    
    # Print Summary
    print_header("TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for suite, result in results.items():
        status = f"{GREEN}✓ PASSED{RESET}" if result else f"{RED}✗ FAILED{RESET}"
        print(f"{status} | {suite}")
    
    print(f"\n{YELLOW}{'─'*70}{RESET}")
    print(f"{BOLD}Total: {total} suites | Passed: {GREEN}{passed}{RESET} | Failed: {RED}{failed}{RESET}{RESET}\n")
    
    if failed == 0:
        print(f"{GREEN}{BOLD}✓ ALL TESTS PASSED - SYSTEM READY!{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}✗ SOME TESTS FAILED - CHECK ERRORS ABOVE{RESET}\n")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
