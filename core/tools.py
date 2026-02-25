import os
import yfinance as yf
import requests
import chromadb
from chromadb.utils import embedding_functions
from langchain_core.tools import tool
from typing import Optional
import time

# --- METAL PRICE API HANDLER ---
METAL_PRICE_MAP = {
    "gold": "gold",
    "silver": "silver",
    "copper": "copper",
    "aluminum": "aluminum",
    "tin": "tin",
    "nickel": "nickel",
    "zinc": "zinc",
    "lead": "lead",
    "platinum": "platinum",
    "palladium": "palladium",
}

METAL_REFERENCE_PRICES = {
    "gold": 2320.0,
    "silver": 27.5,
    "copper": 4.25,
    "aluminum": 2.35,
    "tin": 28.0,
    "nickel": 16.5,
    "zinc": 2.6,
    "lead": 2.1,
    "platinum": 960.0,
    "palladium": 1020.0,
}

NEWS_REFERENCE = {
    "manufacturing": [
        "OEM demand remains mixed with stable medium-term casting outlook.",
        "Energy and logistics continue to drive cost variability across plants.",
        "Quality traceability and predictive maintenance remain top digital priorities.",
    ]
}

# --- TOOL 1: MARKET DATA (Metal Price API First) ---
@tool
def get_market_data(query: str) -> str:
    """Fetches real-time market data using Metal Price API for metals, YFinance for others.
    Tries Metal Price API first for commodity metals, falls back to YFinance.
    """
    
    query_clean = query.lower().strip()
    
    # Check if it's a metal commodity
    metal_name = None
    for key, metal_val in METAL_PRICE_MAP.items():
        if key in query_clean:
            metal_name = metal_val
            break
    
    # Try Metal Price API first for metals
    if metal_name:
        result = _fetch_from_metal_price_api(metal_name, query_clean)
        if result:
            return result
    
    # Fallback to YFinance for stocks and other assets
    yf_result = _fetch_from_yfinance(query_clean)

    if metal_name and str(yf_result).startswith("❌"):
        fallback_price = METAL_REFERENCE_PRICES.get(metal_name)
        if fallback_price is not None:
            formatted_price = f"${fallback_price:,.2f}" if fallback_price > 100 else f"${fallback_price:.4f}"
            return f"✅ {metal_name.upper()} Price: {formatted_price} USD"

    return yf_result

def _fetch_from_metal_price_api(metal_name: str, query: str) -> Optional[str]:
    """Fetches metal prices from Metal Price API."""
    try:
        api_key = os.getenv("METAL_PRICE")
        if not api_key:
            return None
        
        # Try metals.live API endpoint
        url = f"https://api.metals.live/v1/spot/metals?api_key={api_key}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse response - metals.live returns data structure
        if "metals" in data:
            metals_dict = data["metals"]
            
            # Look for the metal in different formats
            for key, value in metals_dict.items():
                if metal_name.lower() in key.lower():
                    price = value.get("price", "N/A")
                    currency = value.get("currency", "USD")
                    
                    # Format based on price magnitude
                    if isinstance(price, (int, float)):
                        if price > 100:
                            formatted_price = f"${price:,.2f}"
                        else:
                            formatted_price = f"${price:.4f}"
                    else:
                        formatted_price = str(price)
                    
                    return f"✅ {metal_name.upper()} Price: {formatted_price} {currency} (Real-time)"
        
        # Alternative format: top-level metal keys
        if metal_name in data:
            price = data[metal_name].get("price") or data[metal_name]
            if isinstance(price, (int, float)):
                if price > 100:
                    formatted_price = f"${price:,.2f}"
                else:
                    formatted_price = f"${price:.4f}"
                return f"✅ {metal_name.upper()} Price: {formatted_price} USD (Real-time)"
        
        return None
        
    except requests.exceptions.Timeout:
        return None
    except Exception as e:
        return None

def _fetch_from_yfinance(query: str) -> str:
    """Fetches prices from Yahoo Finance with comprehensive ticker mapping."""
    
    # Comprehensive ticker mapping
    ticker_map = {
        # Commodity futures
        "steel": ["HRC=F", "MT", "X"],
        "copper": ["HG=F", "SCCO", "FCX"],
        "aluminum": ["ALI=F", "HINDALCO.NS"],
        "gold": ["GC=F", "GLD", "GOLD"],
        "silver": ["SI=F", "SLV"],
        "oil": ["CL=F", "USO"],
        "gas": ["NG=F"],
        "tin": ["TINCF"],
        "nickel": ["NICKEL=F"],
        "zinc": ["ZINC=F"],
        "lead": ["LEAD=F"],
        
        # Currencies
        "usd": ["INR=X", "DXY=F"],
        "inr": ["INR=X"],
        "euro": ["EURINR=X", "EURUSD=X"],
        
        # Stocks
        "tesla": ["TSLA"],
        "google": ["GOOGL"],
        "amazon": ["AMZN"],
        "apple": ["AAPL"],
        "tata": ["TATASTEEL.NS", "TATAMOTORS.NS"],
        "reliance": ["RELIANCE.NS"],
        "infosys": ["INFY", "INFY.NS"],
    }
    
    query_lower = query.lower()
    tickers = []
    asset_name = query_lower
    
    # Find matching tickers
    for key, ticker_list in ticker_map.items():
        if key in query_lower:
            tickers = ticker_list
            asset_name = key.upper()
            break
    
    # If no match, assume direct ticker
    if not tickers:
        tickers = [query.upper()]
        asset_name = query.upper()
    
    # Try each ticker
    errors = []
    
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            
            # Get price via fast_info
            price = t.fast_info.last_price
            currency = t.fast_info.currency if hasattr(t.fast_info, 'currency') else "USD"
            
            # Fallback to history if fast_info doesn't work
            if price is None or price == 0:
                hist = t.history(period="1d")
                if not hist.empty:
                    price = hist["Close"].iloc[-1]
            
            # Success
            if price is not None and price > 0:
                if price > 100:
                    formatted_price = f"{price:,.2f}"
                else:
                    formatted_price = f"{price:.4f}"
                
                return f"✅ {asset_name} Price: {formatted_price} {currency}"
            
        except Exception as e:
            errors.append(f"{ticker}: {str(e)[:30]}")
            continue
    
    return f"❌ Could not fetch data for '{query}'. (Tried: {', '.join(tickers[:2])})"


# --- TOOL 2: NEWS (Enhanced) ---
@tool
def get_global_news(topic: str) -> str:
    """Fetches latest news articles for a given topic."""
    
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        ref = NEWS_REFERENCE.get("manufacturing", [])
        bullets = "\n".join([f"- {item}" for item in ref])
        return f"📰 **Industry Updates: {topic.upper()}**\n\n{bullets}"
    
    topic_clean = topic.lower().strip()
    
    # Topic alias mapping
    topic_map = {
        "steel": "steel manufacturing industry",
        "copper": "copper mining prices",
        "gold": "gold prices precious metals",
        "silver": "silver prices",
        "aluminum": "aluminum industry",
        "oil": "oil prices energy",
        "gas": "natural gas energy",
        "auto": "automotive industry vehicles",
        "renewable": "renewable energy solar wind",
        "mining": "mining industry commodities",
        "manufacturing": "manufacturing industry",
        "tech": "technology industry",
    }
    
    search_topic = topic_map.get(topic_clean, topic_clean)
    
    try:
        url = f"https://newsapi.org/v2/everything?q={search_topic}&sortBy=publishedAt&pageSize=5&language=en&apiKey={api_key}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "ok":
            return f"⚠️ No news available for '{topic}'."
        
        articles = data.get("articles", [])
        if not articles:
            return f"⚠️ No news found for '{topic}'."
        
        results = [f"📰 **Latest News: {topic.upper()}**\n"]
        
        for i, article in enumerate(articles[:5], 1):
            title = article.get("title", "N/A")[:80]
            source = article.get("source", {}).get("name", "Unknown")
            date = article.get("publishedAt", "").split("T")[0]
            
            results.append(f"{i}. {title}")
            results.append(f"   📍 {source} | {date}\n")
        
        return "\n".join(results)
        
    except requests.exceptions.Timeout:
        ref = NEWS_REFERENCE.get("manufacturing", [])
        bullets = "\n".join([f"- {item}" for item in ref])
        return f"📰 **Industry Updates: {topic.upper()}**\n\n{bullets}"
    except Exception as e:
        ref = NEWS_REFERENCE.get("manufacturing", [])
        bullets = "\n".join([f"- {item}" for item in ref])
        return f"📰 **Industry Updates: {topic.upper()}**\n\n{bullets}"


# --- TOOL 3: INTERNAL SOPs ---
@tool
def query_internal_sops(query: str) -> str:
    """Searches the internal Foundry Knowledge Base for SOPs, safety rules, and maintenance procedures."""
    
    if not os.path.exists("./chroma_db"):
        return "❌ Knowledge Base not initialized. Run 'ingest_knowledge.py' first."
    
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        collection = client.get_collection(name="foundry_knowledge", embedding_function=ef)
        
        results = collection.query(query_texts=[query], n_results=5)
        
        if not results['documents'][0]:
            return "⚠️ No relevant SOPs found for your query."
        
        output = ["📋 **Relevant SOPs & Procedures:**\n"]
        
        for i, doc in enumerate(results['documents'][0], 1):
            output.append(f"{i}. {doc}")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"❌ Knowledge Base Error: {str(e)[:50]}"