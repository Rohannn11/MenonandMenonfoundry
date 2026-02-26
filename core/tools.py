import os
import yfinance as yf
import requests
import chromadb
import psycopg2
from chromadb.utils import embedding_functions
from langchain_core.tools import tool
from typing import Optional
import time

try:
    from InputPipeline.foundry_config import DB_CONFIG
except Exception:
    DB_CONFIG = None

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
    "iron": "iron",
    "pig iron": "pig iron",
    "scrap steel": "scrap steel",
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
    "iron": 115.0,
    "pig iron": 480.0,
    "scrap steel": 210.0,
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
    Tries Metal Price API first for commodity metals, falls back to YFinance with clear fallback labeling.
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
        result = _fetch_from_metal_price_api(metal_name)
        if result:
            return result

    # Fallback to YFinance for stocks and other assets
    yf_result = _fetch_from_yfinance(query_clean)

    if metal_name and str(yf_result).startswith("❌"):
        fallback_price = METAL_REFERENCE_PRICES.get(metal_name)
        if fallback_price is not None:
            formatted_price = f"${fallback_price:,.2f}" if fallback_price > 100 else f"${fallback_price:.4f}"
            today = time.strftime("%Y-%m-%d")
            return (
                f"⚠️ Live data unavailable. Reference {metal_name.upper()} price (not live) as of {today}: {formatted_price} USD"
            )

    return yf_result

def _fetch_from_metal_price_api(metal_name: str) -> Optional[str]:
    """Fetches metal prices from metals.live per-metal endpoint."""
    try:
        api_key = os.getenv("METAL_PRICE")
        if not api_key:
            return None

        # metals.live per-metal format: returns a list of dicts like [{"metal": price}, ...]
        url = f"https://api.metals.live/v1/spot/{metal_name}?api_key={api_key}"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        price_val = None
        if isinstance(data, list) and data:
            # Grab the first numeric value we find
            first_entry = data[0]
            if isinstance(first_entry, dict):
                for _, val in first_entry.items():
                    if isinstance(val, (int, float)):
                        price_val = val
                        break
            elif isinstance(first_entry, (int, float)):
                price_val = first_entry

        if price_val is None:
            return None

        formatted_price = f"${price_val:,.2f}" if price_val > 100 else f"${price_val:.4f}"
        return f"✅ {metal_name.upper()} Price: {formatted_price} USD (Real-time)"

    except requests.exceptions.Timeout:
        return None
    except Exception:
        return None

def _fetch_from_yfinance(query: str) -> str:
    """Fetches prices from Yahoo Finance with comprehensive ticker mapping."""
    
    # Comprehensive ticker mapping
    ticker_map = {
        # Commodity proxies (use actively traded equities/ETFs over illiquid futures)
        "steel": ["SAIL.NS", "TATASTEEL.NS"],
        "scrap steel": ["SAIL.NS", "TATASTEEL.NS"],
        "pig iron": ["SAIL.NS", "TATASTEEL.NS"],
        "iron": ["SAIL.NS", "TATASTEEL.NS"],
        "copper": ["HINDCOPPER.NS", "FCX"],
        "aluminum": ["HINDALCO.NS"],
        "gold": ["GLD", "GOLD"],
        "silver": ["SLV"],
        "oil": ["CL=F", "USO"],
        "gas": ["NG=F"],
        "tin": [],
        "nickel": [],
        "zinc": [],
        "lead": [],
        
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
    """Fetches latest news articles for a given topic using GNews (production-safe)."""

    api_key = os.getenv("GNEWS_API_KEY")
    topic_clean = (topic or "").lower().strip()

    # Topic alias mapping (foundry-focused)
    topic_map = {
        "steel": "steel manufacturing",
        "copper": "copper prices mining",
        "gold": "gold prices",
        "silver": "silver prices",
        "aluminum": "aluminum smelting",
        "oil": "oil prices energy",
        "gas": "natural gas energy",
        "auto": "automotive industry",
        "renewable": "renewable energy",
        "mining": "mining industry commodities",
        "manufacturing": "manufacturing industry",
        "tech": "technology industry",
        "pig iron": "pig iron market",
        "scrap metal": "scrap metal prices",
        "scrap steel": "scrap steel prices",
        "ductile iron": "ductile iron foundry",
        "grey iron": "grey iron foundry",
        "casting": "metal casting foundry",
        "foundry": "foundry industry",
        "inoculant": "foundry inoculant",
        "lme": "LME metals prices",
        "mcx": "MCX metals prices",
    }

    search_topic = topic_map.get(topic_clean, topic_clean or "manufacturing")

    if not api_key:
        return f"⚠️ News API key missing. Cannot fetch news for '{search_topic}'."

    try:
        url = (
            "https://gnews.io/api/v4/search"
            f"?q={requests.utils.quote(search_topic)}&lang=en&max=5&sortby=publishedAt&token={api_key}"
        )

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        articles = data.get("articles", [])
        if not articles:
            return f"⚠️ No news found for '{search_topic}'."

        results = []
        for i, article in enumerate(articles[:5], 1):
            title = (article.get("title") or "N/A")[:120]
            source = article.get("source", {}).get("name", "Unknown")
            date = (article.get("publishedAt") or "").split("T")[0]
            url_item = article.get("url", "")
            results.append(f"{i}. {title}\n   {source} | {date} | {url_item}")

        header = f"Latest news for: {search_topic}"
        return "\n".join([header] + results)

    except requests.exceptions.Timeout:
        return f"⚠️ News request timed out for '{search_topic}'."
    except Exception as exc:
        return f"⚠️ News fetch error for '{search_topic}': {str(exc)[:80]}"


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


# --- TOOL 4: READ-ONLY POSTGRES QUERIES ---
@tool
def query_foundry_db(sql: str) -> str:
    """Executes a read-only SQL query against the foundry PostgreSQL DB. ONLY SELECT statements are allowed."""

    if not DB_CONFIG:
        return "❌ Database config not available. Check environment variables."

    sql_clean = (sql or "").strip().rstrip(";")
    lowered = sql_clean.lower()
    forbidden = ["update", "delete", "insert", "drop", "alter", "truncate"]
    if any(f" {kw} " in f" {lowered} " for kw in forbidden) or not lowered.startswith("select"):
        return "❌ Only SELECT queries are allowed."

    # Enforce a hard LIMIT to avoid large result sets
    if " limit " not in lowered:
        sql_clean += " LIMIT 50"

    try:
        conn = psycopg2.connect(
            **DB_CONFIG,
            options="-c default_transaction_read_only=on -c statement_timeout=5000",
        )
        cur = conn.cursor()
        cur.execute(sql_clean)
        rows = cur.fetchall()
        headers = [desc[0] for desc in cur.description]
    except Exception as exc:
        return f"❌ DB query failed: {str(exc)[:120]}"
    finally:
        try:
            if cur:
                cur.close()
            if conn:
                conn.close()
        except Exception:
            pass

    if not rows:
        return "⚠️ Query returned no rows."

    # Format as a compact markdown table (max 50 rows enforced above)
    def fmt(val):
        return "" if val is None else str(val)

    header_line = " | ".join(headers)
    divider = " | ".join(["---"] * len(headers))
    body_lines = []
    for r in rows:
        body_lines.append(" | ".join(fmt(v) for v in r))

    table = "\n".join([header_line, divider] + body_lines)
    return f"✅ Query OK (max 50 rows)\n\n{table}"