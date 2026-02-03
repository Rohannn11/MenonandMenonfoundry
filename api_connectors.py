import yfinance as yf
import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

# --- IN-MEMORY TTL CACHE ---
_CACHE = {
    "weather": {"data": None, "ts": 0, "ttl": 300},  # 5 min
    "market": {"data": None, "ts": 0, "ttl": 180},   # 3 min
    "news": {"data": None, "ts": 0, "ttl": 600}      # 10 min
}

def _get_from_cache(key):
    entry = _CACHE.get(key)
    if entry["data"] and (time.time() - entry["ts"] < entry["ttl"]):
        return entry["data"]
    return None

def _set_cache(key, data):
    _CACHE[key]["data"] = data
    _CACHE[key]["ts"] = time.time()
    return data

def format_for_llm(data_dict, title="DATA"):
    """Helper to convert dicts to clean, tagged text for the LLM."""
    if not isinstance(data_dict, dict) and not isinstance(data_dict, list):
        return str(data_dict)
    
    output = [f"--- {title} ---"]
    if isinstance(data_dict, dict):
        for k, v in data_dict.items():
            output.append(f"{k}: {v}")
    elif isinstance(data_dict, list):
        for item in data_dict:
            output.append(f"- {item}")
    return "\n".join(output)

def get_metal_prices():
    """Returns structured dict of relevant market prices."""
    cached = _get_from_cache("market")
    if cached: return cached

    # Valid Yahoo Finance Tickers for Metal/Energy/Currency
    tickers = {
        "Copper_Futures": "HG=F",
        "Aluminum_Futures": "ALI=F",
        "Crude_Oil": "CL=F",
        "USD_INR": "INR=X"
    }
    
    result = {}
    try:
        for name, sym in tickers.items():
            try:
                t = yf.Ticker(sym)
                # fast_info is reliable
                price = t.fast_info.last_price
                result[name] = round(price, 2) if price else "N/A"
            except:
                result[name] = "N/A"
    except Exception as e:
        result = {"Error": str(e)}

    return _set_cache("market", result)

def get_pune_weather():
    """Returns structured dict of Pune weather."""
    cached = _get_from_cache("weather")
    if cached: return cached

    # Open-Meteo (Free, No Key)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 18.5204,
        "longitude": 73.8567,
        "current": ["temperature_2m", "relative_humidity_2m", "weather_code"]
    }
    
    try:
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        if "current" in data:
            curr = data["current"]
            code = curr.get("weather_code", 0)
            
            # Simple WMO code map
            condition = "Clear"
            if code > 3: condition = "Cloudy"
            if code > 50: condition = "Rainy/Drizzle"
            if code > 80: condition = "Storm/Heavy Rain"

            result = {
                "Location": "Pune, IN",
                "Temperature_C": curr.get("temperature_2m"),
                "Humidity_Pct": curr.get("relative_humidity_2m"),
                "Condition": condition
            }
            return _set_cache("weather", result)
    except Exception as e:
        return {"Error": str(e)}
    
    return {"Status": "Unavailable"}

def get_foundry_news():
    """Returns list of news summaries."""
    cached = _get_from_cache("news")
    if cached: return cached

    api_key = os.getenv("NEWS_API_KEY")
    if not api_key: return ["Error: NewsAPI Key Missing in .env"]

    # Fetch 8 articles
    url = f"https://newsapi.org/v2/everything?q=foundry+steel+price+metal+manufacturing&sortBy=publishedAt&pageSize=8&language=en&apiKey={api_key}"
    
    articles_out = []
    try:
        res = requests.get(url, timeout=5).json()
        if res.get("status") == "ok":
            for a in res.get("articles", []):
                title = a.get("title", "No Title")
                desc = a.get("description", "No Description")
                src = a.get("source", {}).get("name", "Unknown")
                # Clean format
                articles_out.append(f"{title} - {desc} ({src})")
            
            if not articles_out: articles_out = ["No recent news found."]
            return _set_cache("news", articles_out)
        else:
            return [f"API Error: {res.get('message')}"]
    except Exception as e:
        return [f"Connection Error: {str(e)}"]

if __name__ == "__main__":
    # Quick Test
    print(format_for_llm(get_metal_prices(), "MARKETS"))
    print(format_for_llm(get_pune_weather(), "WEATHER"))
    print(format_for_llm(get_foundry_news(), "NEWS"))