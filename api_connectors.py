import yfinance as yf
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# --- DYNAMIC MARKET TOOL ---
def get_market_data(query: str):
    """
    Fetches market data for ANY ticker symbol or search term.
    The LLM provides the 'query' (e.g., 'AAPL', 'Steel', 'INR=X').
    """
    try:
        # 1. Try direct ticker first
        ticker = yf.Ticker(query)
        info = ticker.fast_info
        
        # Check if valid data exists
        if hasattr(info, 'last_price') and info.last_price is not None:
            return f"Market Data for {query.upper()}: Current Price = {info.last_price:.2f} {info.currency}"
            
        # 2. If direct fail, try searching (naive mapping for common terms)
        # In a real app, we'd use a search API to find the ticker, but here we map common ones
        common_map = {
            "steel": "HRC=F", "copper": "HG=F", "gold": "GC=F", "oil": "CL=F",
            "google": "GOOGL", "tesla": "TSLA", "apple": "AAPL", "bitcoin": "BTC-USD"
        }
        
        sym = common_map.get(query.lower())
        if sym:
            t = yf.Ticker(sym)
            return f"Market Data for {query} ({sym}): {t.fast_info.last_price:.2f}"
            
        return f"Could not find market data for '{query}'. Try a specific ticker symbol."
        
    except Exception as e:
        return f"Market Tool Error: {e}"

# --- DYNAMIC NEWS TOOL ---
def get_news(topic: str):
    """
    Fetches news on ANY topic the user asks about.
    """
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key: return "NewsAPI Key Missing."
    
    # Dynamic URL based on input topic
    url = f"https://newsapi.org/v2/everything?q={topic}&sortBy=publishedAt&pageSize=3&language=en&apiKey={api_key}"
    
    try:
        data = requests.get(url, timeout=5).json()
        articles = data.get("articles", [])
        if not articles:
            return f"No news found for '{topic}'."
            
        results = [f"--- News for '{topic}' ---"]
        for a in articles:
            results.append(f"• {a['title']} (Source: {a['source']['name']})")
        
        return "\n".join(results)
    except Exception as e:
        return f"News Tool Error: {e}"

# --- WEATHER TOOL ---
def get_weather(location: str = "Pune"):
    """
    Fetches weather. Defaults to Pune but LLM can request others.
    """
    # Simple geocoding mapping for demo (expandable)
    loc_map = {"pune": (18.52, 73.85), "mumbai": (19.07, 72.87), "delhi": (28.61, 77.20), "london": (51.50, -0.12)}
    
    lat, lon = loc_map.get(location.lower(), (18.52, 73.85)) # Default Pune
    
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m"
    try:
        data = requests.get(url, timeout=5).json()
        curr = data.get("current", {})
        return f"Weather in {location}: {curr.get('temperature_2m')}°C, Humidity {curr.get('relative_humidity_2m')}%"
    except:
        return "Weather unavailable."