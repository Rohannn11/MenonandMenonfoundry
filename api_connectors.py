import yfinance as yf
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_metal_prices():
    """
    Fetches live market data. 
    Returns a CLEAN string to save LLM tokens.
    """
    tickers = {
        "Steel": "STL=F",
        "Iron Ore": "IO=F",
        "Copper": "HG=F",
        "Aluminum": "ALI=F", 
        "Crude Oil": "CL=F",
        "INR/USD": "INR=X"
    }
    
    output = ["MARKET DATA:"]
    try:
        for name, sym in tickers.items():
            try:
                ticker = yf.Ticker(sym)
                # fast_info is much faster/cheaper than .history()
                price = ticker.fast_info.last_price
                output.append(f"{name}: {price:.2f}")
            except:
                output.append(f"{name}: N/A")
        return "\n".join(output)
    except Exception as e:
        return f"Market Error: {str(e)}"

def get_foundry_news():
    """
    Fetches top 3 relevant headlines.
    Limits to 3 to prevent Token Overflow.
    """
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key: return "NewsAPI Key Missing"

    url = f"https://newsapi.org/v2/everything?q=foundry+steel+price&sortBy=publishedAt&pageSize=3&apiKey={api_key}"
    
    try:
        data = requests.get(url).json()
        if data.get("status") == "ok":
            articles = [f"- {a['title']} ({a['source']['name']})" for a in data.get("articles", [])]
            return "\n".join(articles)
        return "No news found."
    except:
        return "News Connection Failed."