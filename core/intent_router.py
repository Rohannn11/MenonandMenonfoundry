from enum import Enum
from typing import List, Tuple
import re

class QueryIntent(Enum):
    """Categorizes user queries into specific intent types."""
    PRICE_QUERY = "price"           # Market/commodity prices
    NEWS_QUERY = "news"             # Industry news & trends
    SOP_QUERY = "sop"               # Internal procedures & safety
    COMBINED_QUERY = "combined"     # Multiple intents
    GENERAL_CHAT = "general"        # General knowledge/chat

class IntentRouter:
    """Routes queries to appropriate data sources based on intent analysis."""
    
    # Keywords for each intent type (EXPANDED for comprehensive matching)
    PRICE_KEYWORDS = {
        # Direct price/cost terms (HIGH PRIORITY)
        "price", "cost", "rate", "value", "quote", "quotation", "pricing",
        "how much", "what is the price", "current price", "today's price", "price of",
        "trading price", "market price", "spot price", "ask", "bid", "expensive",
        "cheap", "worth", "valuation", "amount", "price tag", "per unit",
        
        # Price-related verbs (HIGH PRIORITY)
        "fetch", "show", "display", "tell me", "quote", "provide",
        
        # Currencies and stocks (ONLY when with price context)
        "usd", "inr", "euro", "forex", "exchange rate", "currency", "dollar",
        "rupee", "pound", "yen", "stock price", "share price",
        "stock", "share", "index", "tsla", "tesla", "google", "googl",
        "apple", "aapl", "tata", "tatasteel", "tatamotors", "reliance",
        "infosys",
    }
    
    NEWS_KEYWORDS = {
        # Direct news terms (HIGH PRIORITY)
        "news", "headline", "report", "article", "announcement", "press release",
        "breaking", "update", "latest", "recent",
        "trend", "industry trend", "market trend", "development", "trends",
        "what's happening", "what happened", "happening", "event",
        "coverage", "industry news", "market news", "breaking news",
        "updates", "announcements", "stories", "reports",
        
        # News-related verbs (HIGH PRIORITY)
        "tell", "show", "give", "fetch", "retrieve", "get", "find",
        "search", "any", "look for",
    }
    
    SOP_KEYWORDS = {
        # Direct procedure/safety terms (HIGH PRIORITY)
        "procedure", "procedures", "process", "rule", "safety", "protocol", "standard",
        "guideline", "guidelines", "requirement", "sop", "standard operating",
        "maintenance", "inspection", "checklist", "manual", "policy",
        "steps", "instructions",
        
        # How-to and instruction terms (HIGH PRIORITY)
        "how to", "how do", "how can", "how should", "method", "approach",
        "way to", "do i", "should i", "can i", "what should",
        "must", "must not", "shall", "prohibited", "allowed",
        "permitted", "what are", "what is", "list of",
        
        # Safety-specific terms (HIGH PRIORITY)
        "safe", "safely", "hazard", "risk", "danger", "warning",
        "precaution", "equipment", "protective", "ppe", "personal protective",
        "health", "accident", "injury", "emergency",
        
        # Foundry-specific terms (MEDIUM PRIORITY)
        "furnace", "melting", "molding", "casting", "sand", "mold",
        "heat treatment", "quality", "defect", "shakeout", "pouring",
        "induction", "crucible", "slag", "inoculant", "temperature",
        "pressure", "maintain", "operating", "run", "operation"
    }
    
    # Commodity names (should NOT trigger price unless with price keywords)
    COMMODITY_ONLY = {
        "steel", "copper", "gold", "aluminum", "oil", "gas", "iron", "tin",
        "nickel", "zinc", "lead", "silver", "coal", "uranium", "metal"
    }
    
    # Connector words that indicate multiple intents
    CONNECTOR_WORDS = {"and", "also", "plus", "with", "including", "along with", "as well as", "plus", ","}
    
    def __init__(self):
        self.primary_intent = None
        self.secondary_intents = []
        self.confidence_scores = {}
        self.matched_keywords = {}
    
    def analyze(self, query: str) -> Tuple[QueryIntent, List[QueryIntent], dict]:
        """
        Analyzes a query and returns:
        - Primary intent (highest confidence)
        - Secondary intents (if multi-intent)
        - Confidence scores for each category
        
        Returns: (primary_intent, secondary_intents, confidence_dict)
        """
        query_lower = query.lower()
        
        # Calculate confidence scores with context awareness
        scores = {
            QueryIntent.PRICE_QUERY: self._score_keywords(query_lower, self.PRICE_KEYWORDS, QueryIntent.PRICE_QUERY),
            QueryIntent.NEWS_QUERY: self._score_keywords(query_lower, self.NEWS_KEYWORDS, QueryIntent.NEWS_QUERY),
            QueryIntent.SOP_QUERY: self._score_keywords(query_lower, self.SOP_KEYWORDS, QueryIntent.SOP_QUERY),
        }
        
        self.confidence_scores = scores
        
        # Determine primary and secondary intents
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Check for combined query patterns FIRST
        is_combined = self._detect_combined_query(query_lower, scores)
        
        if is_combined:
            # Find all significant intents (> 0.15)
            high_scoring = [intent for intent, score in sorted_intents if score > 0.15]
            if len(high_scoring) >= 2:
                primary = QueryIntent.COMBINED_QUERY
                secondary = high_scoring
                self.primary_intent = primary
                self.secondary_intents = secondary
                return primary, secondary, scores
        
        # Primary: highest score (threshold: 0.12)
        if sorted_intents[0][1] > 0.12:
            primary = sorted_intents[0][0]
        else:
            primary = QueryIntent.GENERAL_CHAT
        
        # Secondary: other significant intents (> 0.10 AND significantly lower than primary)
        primary_score = sorted_intents[0][1]
        secondary = [intent for intent, score in sorted_intents 
                    if 0.10 < score < primary_score and (primary_score - score) > 0.15]
        
        self.primary_intent = primary
        self.secondary_intents = secondary
        
        return primary, secondary, scores
    
    def _detect_combined_query(self, query: str, scores: dict) -> bool:
        """
        Detects if query is a combined query by looking for:
        1. Connector words ("and", "also", "with", etc.)
        2. Multiple high-confidence intents (> 0.15)
        3. Query mentions multiple distinct topics
        """
        
        # Check for connector words
        has_connector = any(f" {conn} " in f" {query} " for conn in self.CONNECTOR_WORDS)
        
        if not has_connector:
            return False
        
        # Count how many intents have meaningful scores (> 0.15)
        significant_intents = sum(1 for score in scores.values() if score > 0.15)
        
        # If multiple intents are significant AND there's a connector, it's combined
        if significant_intents >= 2:
            return True
        
        # Additional check: look for explicit multi-part queries
        # e.g., "copper cost and mining procedures"
        query_parts = re.split(r'\s+and\s+|\s+also\s+|\s+with\s+', query)
        
        if len(query_parts) >= 2:
            # Check if different parts trigger different intents
            part_scores = []
            for part in query_parts:
                if part.strip():
                    part_scores.append({
                        "price": self._score_keywords(part, self.PRICE_KEYWORDS, QueryIntent.PRICE_QUERY),
                        "news": self._score_keywords(part, self.NEWS_KEYWORDS, QueryIntent.NEWS_QUERY),
                        "sop": self._score_keywords(part, self.SOP_KEYWORDS, QueryIntent.SOP_QUERY),
                    })
            
            # If different parts have different dominant intents, it's combined
            if len(part_scores) >= 2:
                max_intents = []
                for part_score in part_scores:
                    max_intent = max(part_score.items(), key=lambda x: x[1])
                    if max_intent[1] > 0.12:  # Only if score is significant
                        max_intents.append(max_intent[0])
                
                # If parts trigger different intents
                if len(set(max_intents)) >= 2:
                    return True
        
        return False
    
    def _score_keywords(self, query: str, keywords: set, intent_type: QueryIntent) -> float:
        """
        Scores how well a query matches a set of keywords (0.0 to 1.0).
        Uses context-aware scoring for better intent detection.
        """
        if not keywords:
            return 0.0
        
        matched = []
        
        # Check each keyword with word boundaries
        for kw in keywords:
            escaped_kw = re.escape(kw)
            if re.search(r'\b' + escaped_kw + r'\b', query):
                matched.append(kw)
        
        if not matched:
            return 0.0
        
        # Base score: percentage of keywords matched
        base_score = len(matched) / len(keywords)
        
        # Context-aware boost based on intent type
        boost = 0.0
        
        # === PRICE INTENT BOOST ===
        if intent_type == QueryIntent.PRICE_QUERY:
            # Must have explicit price keywords, not just commodities
            explicit_price_kws = ["price", "cost", "how much", "quote", "value", 
                                 "expensive", "cheap", "rate", "market price", "spot price",
                                 "current price", "today's price"]
            
            if any(kw in matched for kw in explicit_price_kws):
                boost += 0.20  # Strong signal
            else:
                # Commodity names alone don't make it a price query
                boost -= 0.15  # Penalty for commodity-only match
        
        # === NEWS INTENT BOOST ===
        elif intent_type == QueryIntent.NEWS_QUERY:
            explicit_news_kws = ["news", "latest", "announcement", "trend", "trends",
                                "breaking", "update", "what's happening", "report",
                                "headline", "article", "development"]
            
            if any(kw in matched for kw in explicit_news_kws):
                boost += 0.20  # Strong signal
        
        # === SOP INTENT BOOST ===
        elif intent_type == QueryIntent.SOP_QUERY:
            explicit_sop_kws = ["procedure", "procedures", "safety", "how to", 
                               "maintenance", "guideline", "guidelines", "steps",
                               "protocol", "standard", "rule", "requirement"]
            
            if any(kw in matched for kw in explicit_sop_kws):
                boost += 0.20  # Strong signal
        
        # Additional boosts for multiple keyword matches
        if len(matched) >= 2:
            boost += 0.10
        
        if len(matched) >= 3:
            boost += 0.05
        
        final_score = min(max(base_score + boost, 0.0), 1.0)
        
        return final_score
    
    def extract_entities(self, query: str) -> dict:
        """
        Extracts key entities from query:
        - asset_name: 'steel', 'copper', 'gold', etc.
        - topic: 'mining', 'auto', 'renewable', etc.
        
        Returns: {'asset_name': str, 'topic': str}
        """
        query_lower = query.lower()
        
        # Asset extraction (commodities/stocks)
        assets = [
            "steel", "copper", "gold", "aluminum", "oil", "gas", 
            "silver", "iron", "tin", "nickel", "zinc", "lead", "uranium", "coal",
            "usd", "inr", "euro", "gbp", "yen",
            "tesla", "tsla", "google", "googl", "amazon", "apple", "aapl",
            "tata", "tatasteel", "tatamotors", "reliance", "infosys"
        ]
        
        extracted_asset = None
        for asset in assets:
            if re.search(r'\b' + asset + r'\b', query_lower):
                extracted_asset = asset
                break
        
        # Topic extraction (industries/sectors)
        topics = [
            "auto", "automotive", "renewable", "energy", "manufacturing",
            "mining", "construction", "aerospace", "marine", "agriculture",
            "tech", "technology", "finance", "healthcare", "retail", "industrial"
        ]
        
        extracted_topic = None
        for topic in topics:
            if re.search(r'\b' + topic + r'\b', query_lower):
                extracted_topic = topic
                break
        
        return {
            "asset_name": extracted_asset,
            "topic": extracted_topic
        }
    
    def format_for_tools(self, query: str, intent: QueryIntent, entities: dict) -> dict:
        """Formats query context for tool invocation."""
        return {
            "original_query": query,
            "intent": intent.value,
            "asset_name": entities.get("asset_name"),
            "topic": entities.get("topic"),
            "confidence": self.confidence_scores
        }
