import os
import yfinance as yf
import requests
import chromadb
from chromadb.utils import embedding_functions
from langchain_core.tools import tool

# --- TOOL 1: MARKET DATA (Improved Logic) ---
@tool
def get_market_data(query: str):
    """Fetches real-time market data.
    IMPORTANT: Send ONLY the specific name of the asset.
    Example: 'steel', 'copper', 'gold', 'USD', 'Tesla'.
    Do not send phrases like 'price of copper'.
    """
    # 1. Define the Map
    symbol_map = {
        "steel": "HRC=F", "copper": "HG=F", "aluminum": "ALI=F",
        "gold": "GC=F", "oil": "CL=F", "silver": "SI=F",
        "inr": "INR=X", "usd": "INR=X", "euro": "EURINR=X",
        "tesla": "TSLA", "tata": "TATASTEEL.NS", "google": "GOOGL"
    }
    
    # 2. Smart Cleaning (The Fix)
    # If the user sends "Price of Copper", we want to find "copper" in that string.
    query_clean = query.lower()
    ticker = None
    
    # Check if any key in our map exists inside the query string
    for key, val in symbol_map.items():
        if key in query_clean:
            ticker = val
            break
            
    # If no keyword found, assume the user sent a direct ticker (e.g. "AAPL")
    if not ticker:
        ticker = query.upper()

    # 3. Fetch Data
    try:
        t = yf.Ticker(ticker)
        # fast_info is the most reliable method
        price = t.fast_info.last_price
        currency = t.fast_info.currency
        
        # Validation
        if price is None:
            return f"❌ Could not find market data for '{query}' (Tried ticker: {ticker})."
            
        return f"✅ {ticker} Price: {price:,.2f} {currency}"
        
    except Exception as e:
        return f"Market Error: {str(e)}"

# --- TOOL 2: NEWS ---
@tool
def get_global_news(topic: str):
    """Fetches top 3 latest news headlines for a given topic or industry."""
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key: return "NewsAPI Key missing."
    
    url = f"https://newsapi.org/v2/everything?q={topic}&sortBy=publishedAt&pageSize=3&language=en&apiKey={api_key}"
    try:
        data = requests.get(url, timeout=5).json()
        articles = data.get("articles", [])
        if not articles: return f"No news found for '{topic}'."
        
        results = [f"--- NEWS: {topic.upper()} ---"]
        for a in articles:
            results.append(f"• {a['title']} ({a['source']['name']})")
        return "\n".join(results)
    except Exception as e:
        return f"News Error: {str(e)}"

# --- TOOL 3: INTERNAL SOPs ---
@tool
def query_internal_sops(query: str):
    """Searches the internal Foundry Knowledge Base for SOPs, safety rules, and maintenance procedures."""
    if not os.path.exists("./chroma_db"):
        return "Memory empty. Run 'ingest.py'."
    
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        collection = client.get_collection(name="foundry_knowledge", embedding_function=ef)
        
        results = collection.query(query_texts=[query], n_results=3)
        
        if not results['documents'][0]: return "No relevant SOPs found."
        return "\n".join([f"📄 {doc}" for doc in results['documents'][0]])
    except Exception as e:
        return f"Memory Error: {str(e)}"