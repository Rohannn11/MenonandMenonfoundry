import os
from dotenv import load_dotenv
from typing import List, Dict
import re
import time

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import Tool

# Import Tools and Router
from core.tools import get_market_data, get_global_news, query_internal_sops
from core.intent_router import IntentRouter, QueryIntent

load_dotenv()

class AgentBrain:
    def __init__(self):
        # 1. Initialize LLM
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.3,  # Slightly higher for better reasoning
            api_key=os.getenv("GROQ_API_KEY")
        )
        
        # 2. Initialize Router
        self.router = IntentRouter()
        
        # 3. Define Available Tools
        self.tools = {
            "get_market_data": get_market_data,
            "get_global_news": get_global_news,
            "query_internal_sops": query_internal_sops,
        }

        self.intent_confidence_threshold = 0.18
        self.max_tool_retries = 2
        
        # 4. System Prompt for Reasoning
        self.system_prompt = """You are an Industrial AI Assistant for Menon & Menon Foundry.

Your role is to:
1. Analyze user queries and understand their intent
2. Provide accurate information from multiple sources
3. Handle complex, multi-part queries by breaking them down
4. Give professional, concise responses

Available Information Sources:
- Market Data: Real-time commodity, metal, and stock prices
- Industry News: Latest news on metals, manufacturing, energy
- Internal Procedures: Foundry SOPs, safety protocols, maintenance guidelines

When you need to fetch data:
- For price queries: Use get_market_data
- For industry trends: Use get_global_news
- For procedures/safety: Use query_internal_sops

Always explain your reasoning and cite your sources."""

    def ask(self, user_query: str) -> str:
        """
        Main entry point for answering questions.
        Implements step-by-step reasoning and multi-tool invocation.
        """
        
        # STEP 1: Analyze Intent
        primary_intent, secondary_intents, scores = self.router.analyze(user_query)
        entities = self.router.extract_entities(user_query)
        top_score = max(scores.values()) if scores else 0.0

        if primary_intent == QueryIntent.GENERAL_CHAT and top_score < self.intent_confidence_threshold:
            return self._handle_low_confidence(user_query)
        
        # STEP 2: Route Based on Intent
        if primary_intent == QueryIntent.PRICE_QUERY:
            return self._handle_price_query(user_query, entities)
        
        elif primary_intent == QueryIntent.NEWS_QUERY:
            return self._handle_news_query(user_query, entities)
        
        elif primary_intent == QueryIntent.SOP_QUERY:
            return self._handle_sop_query(user_query, entities)
        
        elif primary_intent == QueryIntent.COMBINED_QUERY:
            return self._handle_combined_query(user_query, entities, secondary_intents, scores)
        
        else:
            return self._handle_general_chat(user_query)
    
    def _handle_price_query(self, query: str, entities: dict) -> str:
        """Handles pure price queries."""
        
        asset = entities.get("asset_name") or self._extract_asset(query)
        
        if not asset:
            return "❌ Could not identify what commodity or stock you're asking about. Please specify (e.g., 'steel', 'copper', 'gold')."
        
        # Fetch price data
        price_data = self._run_tool_with_retries("get_market_data", asset)
        
        # Enhance with context
        response = f"**Market Data Request: {asset.upper()}**\n\n{price_data}"
        
        # Try to add related news if requested
        if "and news" in query.lower() or "and trends" in query.lower():
            news_data = self._run_tool_with_retries("get_global_news", asset)
            response += f"\n\n**Related News:**\n{news_data}"
        
        return response
    
    def _handle_news_query(self, query: str, entities: dict) -> str:
        """Handles pure news queries."""
        
        topic = entities.get("topic") or self._extract_topic(query) or "manufacturing"
        
        news_data = self._run_tool_with_retries("get_global_news", topic)
        
        return f"**Industry News: {topic.upper()}**\n\n{news_data}"
    
    def _handle_sop_query(self, query: str, entities: dict) -> str:
        """Handles SOP/procedure queries."""
        
        sop_data = self._run_tool_with_retries("query_internal_sops", query)
        
        return f"**Foundry Procedures & Guidelines**\n\n{sop_data}"
    
    def _handle_combined_query(self, query: str, entities: dict, secondary_intents: List[QueryIntent], scores: dict) -> str:
        """Handles queries that span multiple data sources."""
        
        results = []
        
        # Collect data from all relevant sources based on scores
        if scores.get(QueryIntent.PRICE_QUERY, 0) > self.intent_confidence_threshold or "price" in query.lower():
            asset = entities.get("asset_name") or self._extract_asset(query)
            if asset:
                price_data = self._run_tool_with_retries("get_market_data", asset)
                results.append(f"**💰 Pricing Information:**\n{price_data}")
        
        if scores.get(QueryIntent.NEWS_QUERY, 0) > self.intent_confidence_threshold or "news" in query.lower():
            topic = entities.get("topic") or self._extract_topic(query) or "manufacturing"
            news_data = self._run_tool_with_retries("get_global_news", topic)
            results.append(f"**📰 Recent News:**\n{news_data}")
        
        if scores.get(QueryIntent.SOP_QUERY, 0) > self.intent_confidence_threshold or any(kw in query.lower() for kw in ["procedure", "safety", "maintain", "how to"]):
            sop_data = self._run_tool_with_retries("query_internal_sops", query)
            results.append(f"**📋 Related Procedures:**\n{sop_data}")
        
        if not results:
            return self._handle_general_chat(query)
        
        combined = "\n\n---\n\n".join(results)
        
        # Use LLM to synthesize
        synthesis_prompt = f"""The user asked: "{query}"

Here is the collected information:

{combined}

Please provide a clear, concise answer that combines this information to address the user's question."""
        
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=synthesis_prompt)
            ]
            response = self.llm.invoke(messages)
            return response.content
        except:
            return combined
    
    def _handle_general_chat(self, query: str) -> str:
        """Handles general knowledge questions."""
        
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"User Query: {query}")
            ]
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"❌ Error processing query: {str(e)}"

    def _handle_low_confidence(self, query: str) -> str:
        return (
            "I can support this best if you choose one of these request types:\n\n"
            "1) Market pricing (e.g., copper, steel, gold)\n"
            "2) Industry news/trends (e.g., mining, manufacturing)\n"
            "3) Internal procedures/SOP guidance\n"
            "4) Combined request (price + news + SOP)\n\n"
            f"Your query: \"{query}\"\n"
            "Try: 'Give me copper price and latest mining news'."
        )

    def _run_tool_with_retries(self, tool_name: str, tool_input: str) -> str:
        tool = self.tools.get(tool_name)
        if not tool:
            return "⚠️ Tool unavailable."

        last_output = "⚠️ Data temporarily unavailable."
        for attempt in range(self.max_tool_retries + 1):
            try:
                output = tool.run(tool_input)
                if output and not self._is_tool_failure(output):
                    return output
                last_output = output or last_output
            except Exception as exc:
                last_output = f"⚠️ Tool execution issue: {str(exc)[:60]}"

            if attempt < self.max_tool_retries:
                time.sleep(0.4)

        return last_output

    def _is_tool_failure(self, output: str) -> bool:
        low = str(output).lower()
        return low.startswith("❌") or "timeout" in low or "unavailable" in low
    
    # --- HELPER METHODS ---
    
    def _extract_asset(self, query: str) -> str:
        """Extracts commodity/stock name from query."""
        assets = ["steel", "copper", "gold", "aluminum", "oil", "silver", "iron", "tin", "nickel", "zinc", "lead"]
        query_lower = query.lower()
        for asset in assets:
            if asset in query_lower:
                return asset
        return None
    
    def _extract_topic(self, query: str) -> str:
        """Extracts industry topic from query."""
        topics = ["auto", "automotive", "renewable", "energy", "manufacturing", "mining", "construction", "tech"]
        query_lower = query.lower()
        for topic in topics:
            if topic in query_lower:
                return topic
        return None