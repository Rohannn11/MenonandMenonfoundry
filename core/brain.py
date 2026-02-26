import os
import json
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
            model="llama-3.1-8b-instant",
            temperature=0.0,
            api_key=os.getenv("GROQ_API_KEY")
        )
        
        # 2. Initialize Router
        self.router = IntentRouter()
        
        # 3. Define Available Tools
        self.tools = {
            "get_market_data": get_market_data,
            "get_global_news": get_global_news,
            "query_internal_sops": query_internal_sops,
            "query_foundry_db": None,  # bound lazily below
        }

        # Late bind to avoid import cycle
        try:
            from core.tools import query_foundry_db
            self.tools["query_foundry_db"] = query_foundry_db
        except Exception:
            pass

        self.intent_confidence_threshold = 0.10
        self.max_tool_retries = 2
        self.history: List[Dict[str, str]] = []  # conversational memory
        
        # 4. System Prompt for Reasoning
        self.system_prompt = """You are an Industrial AI Assistant for Menon & Menon Foundry.

    Tools you can call (choose only one per turn unless strictly necessary):
    - get_market_data: real-time commodity/metal/stock prices
    - get_global_news: industry/foundry news via GNews
    - query_internal_sops: internal SOP knowledge base
    - query_foundry_db: read-only Postgres SELECT (ensure LIMIT 50)

    DB schema cheat sheet:
    - material_master(material_number, material_type, description, base_unit, plant, safety_stock, standard_price_usd)
    - bill_of_materials(bom_number, parent_material, component_material, component_quantity, component_type)
    - production_orders(production_order, product_type, alloy_grade, order_quantity, confirmed_quantity, scrap_quantity, order_status, planned_end_date)
    - melting_heat_records(heat_number, melt_date, furnace_id, tap_temperature_c, pour_temperature_c, quality_status, yield_pct, energy_kwh)
    - molding_records(mold_batch, production_order, molding_type, planned_quantity, actual_quantity, quality_check, defect_type)
    - casting_records(casting_batch, heat_number, production_order, casting_date, good_castings, scrap_castings, yield_pct, quality_grade)
    - heat_treatment(ht_batch_number, casting_batch, treatment_type, target_temperature_c, actual_temperature_c, quality_status)
    - machining_operations(operation_id, production_order, machine_type, operation_type, quality_status, power_consumption_kw, quantity_processed)
    - quality_inspections(inspection_lot, inspection_date, inspection_stage, defect_count, overall_decision, material_number)
    - inventory_movements(document_number, posting_date, movement_type, material_number, quantity, stock_before, stock_after, amount_usd)
    - equipment_maintenance(maintenance_order, equipment_number, maintenance_type, status, planned_start, planned_end, downtime_hours, total_cost_usd)

    SQL tips:
    - Use AVG(), SUM(), COUNT(), MIN(), MAX() for aggregates.
    - Use GROUP BY for breakdowns (e.g., by product_type, quality_grade).
    - Use WHERE for filtering (e.g., quality_status = 'REJECTED').
    - Always include LIMIT 50.

    Rules:
    - Prefer live data; if a tool returns a reference fallback, state it clearly.
    - Only SELECT SQL is allowed for the DB tool; include LIMIT 50.
    - Be concise and avoid mentioning tool names.
    - Format numeric answers clearly (e.g., "Average: 1425.3°C").
    """

    def ask(self, user_query: str) -> str:
        """Main entry point: LLM chooses a tool (or none), tool runs, LLM summarizes."""

        action = self._decide_action(user_query)

        if action.get("action") == "final":
            final_resp = action.get("input") or ""
            self._remember(user_query, final_resp)
            return final_resp

        tool_name = action.get("action")
        tool_input = action.get("input") or user_query

        tool = self.tools.get(tool_name)
        if not tool:
            fallback = f"⚠️ Tool '{tool_name}' unavailable."
            self._remember(user_query, fallback)
            return fallback

        tool_output = self._run_tool_with_retries(tool_name, tool_input)

        summary = self._summarize_response(user_query, tool_name, tool_input, tool_output)
        self._remember(user_query, summary)
        return summary

    # --- Tool-Orchestrated Flow ---
    def _decide_action(self, user_query: str) -> Dict[str, str]:
        """Fast-path heuristics, then LLM JSON decision."""

        ql = user_query.lower()
        # Hard heuristics to avoid bad tool choices
        if any(w in ql for w in ["news", "headline", "latest", "update", "trending"]):
            return {"action": "get_global_news", "input": user_query}
        if any(w in ql for w in ["price", "cost", "rate", "quote"]):
            return {"action": "get_market_data", "input": user_query}
        if any(w in ql for w in ["procedure", "sop", "safety", "guideline", "how to"]):
            return {"action": "query_internal_sops", "input": user_query}
        if any(w in ql for w in [
            "sql", "select", "average", "sum", "count", "tap temperature", "heat", "casting", "yield",
            "rejection", "inspection", "inventory", "stock", "movement", "maintenance", "downtime", "machine",
            "production order", "bom"
        ]):
            return {"action": "query_foundry_db", "input": self._default_db_query(ql)}

        tools_manifest = (
            "- get_market_data: live metals/stocks\n"
            "- get_global_news: industry/foundry news\n"
            "- query_internal_sops: internal SOP KB\n"
            "- query_foundry_db: SQL SELECT only; include LIMIT 50 (tables: material_master, bill_of_materials, production_orders, melting_heat_records, molding_records, casting_records, heat_treatment, machining_operations, quality_inspections, inventory_movements, equipment_maintenance)"
        )

        history_text = self._format_history()

        prompt = f"""
You must choose exactly one action for the user request.
Respond ONLY with a JSON object like {{"action": "get_market_data", "input": "copper"}}.
Valid actions: get_market_data, get_global_news, query_internal_sops, query_foundry_db, final.
If using query_foundry_db, craft a safe SELECT with LIMIT 50. Use real tables: melting_heat_records, casting_records, heat_treatment, quality_inspections, production_orders, material_master.

History (last turns):
{history_text}

User: {user_query}

Tools:
{tools_manifest}
"""

        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ]
            resp = self.llm.invoke(messages)
            raw = resp.content.strip()

            json_str = raw
            if "{" in raw and "}" in raw:
                json_str = raw[raw.index("{"):raw.rindex("}")+1]
            parsed = json.loads(json_str)
            if "action" not in parsed:
                raise ValueError("no action key")
            return parsed
        except Exception:
            return {"action": "final", "input": "Sorry, I could not decide how to help with that."}

    def _summarize_response(self, user_query: str, tool_name: str, tool_input: str, tool_output: str) -> str:
        """Ask LLM to craft a concise answer, without exposing tool names."""
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=(
                    f"User asked: {user_query}\n"
                    f"Supporting data:\n{tool_output}\n"
                    "Provide a concise, user-facing answer following these rules:\n"
                    "- Do not mention function or tool names.\n"
                    "- For single values, state clearly (e.g., 'Average tap temperature: 1425.3°C').\n"
                    "- For lists, use bullet points.\n"
                    "- For tables, summarize key insights rather than repeating raw data.\n"
                    "- Highlight any warnings or anomalies.\n"
                )),
            ]
            resp = self.llm.invoke(messages)
            return resp.content
        except Exception as exc:
            return f"⚠️ Could not summarize. Raw data: {tool_output} (error: {str(exc)[:60]})"

    def _default_db_query(self, ql: str) -> str:
        # Aggregate queries (average, total, count)
        if "average" in ql or "avg" in ql:
            if "tap" in ql or "temperature" in ql:
                return "SELECT ROUND(AVG(tap_temperature_c)::numeric, 1) AS avg_tap_temp_c FROM melting_heat_records"
            if "yield" in ql:
                return "SELECT ROUND(AVG(yield_pct)::numeric, 2) AS avg_yield_pct FROM casting_records"
            if "downtime" in ql:
                return "SELECT ROUND(AVG(downtime_hours)::numeric, 1) AS avg_downtime_hrs FROM equipment_maintenance"
            if "energy" in ql:
                return "SELECT ROUND(AVG(energy_kwh)::numeric, 1) AS avg_energy_kwh FROM melting_heat_records"
        if "total" in ql or "sum" in ql:
            if "scrap" in ql:
                return "SELECT SUM(scrap_castings) AS total_scrap FROM casting_records"
            if "downtime" in ql:
                return "SELECT SUM(downtime_hours) AS total_downtime_hrs FROM equipment_maintenance"
            if "cost" in ql:
                return "SELECT SUM(total_cost_usd) AS total_maintenance_cost FROM equipment_maintenance"
        if "count" in ql or "how many" in ql:
            if "rejected" in ql or "rejection" in ql:
                return "SELECT COUNT(*) AS rejected_heats FROM melting_heat_records WHERE quality_status = 'REJECTED'"
            if "inspection" in ql:
                return "SELECT overall_decision, COUNT(*) AS cnt FROM quality_inspections GROUP BY overall_decision"
            if "maintenance" in ql:
                return "SELECT maintenance_type, COUNT(*) AS cnt FROM equipment_maintenance GROUP BY maintenance_type"
            if "order" in ql or "production" in ql:
                return "SELECT order_status, COUNT(*) AS cnt FROM production_orders GROUP BY order_status"
        # Breakdown queries
        if "by product" in ql or "per product" in ql:
            if "yield" in ql:
                return "SELECT product_type, ROUND(AVG(yield_pct)::numeric, 2) AS avg_yield FROM casting_records GROUP BY product_type"
            if "scrap" in ql:
                return "SELECT product_type, SUM(scrap_castings) AS total_scrap FROM casting_records GROUP BY product_type"
        if "by grade" in ql or "per grade" in ql:
            return "SELECT quality_grade, COUNT(*) AS cnt FROM casting_records GROUP BY quality_grade"
        # Detail queries
        if "tap" in ql and "temperature" in ql:
            return "SELECT heat_number, melt_date, tap_temperature_c FROM melting_heat_records ORDER BY melt_date DESC LIMIT 10"
        if "yield" in ql:
            return "SELECT casting_batch, casting_date, yield_pct, quality_grade FROM casting_records ORDER BY casting_date DESC LIMIT 10"
        if "scrap" in ql or "rejection" in ql:
            return "SELECT casting_batch, scrap_castings, good_castings, quality_grade FROM casting_records ORDER BY casting_date DESC LIMIT 10"
        if "inspection" in ql or "defect" in ql:
            return "SELECT inspection_lot, inspection_date, inspection_stage, defect_count, overall_decision FROM quality_inspections ORDER BY inspection_date DESC LIMIT 10"
        if "inventory" in ql or "stock" in ql or "movement" in ql:
            return "SELECT posting_date, material_number, movement_type, quantity, stock_after FROM inventory_movements ORDER BY posting_date DESC LIMIT 15"
        if "maintenance" in ql or "downtime" in ql:
            return "SELECT maintenance_order, equipment_number, maintenance_type, status, downtime_hours, total_cost_usd FROM equipment_maintenance ORDER BY planned_start DESC LIMIT 15"
        if "machine" in ql or "machining" in ql:
            return "SELECT operation_id, machine_type, operation_type, quality_status, quantity_processed FROM machining_operations ORDER BY operation_date DESC LIMIT 15"
        if "production" in ql or "order" in ql:
            return "SELECT production_order, product_type, order_status, order_quantity, confirmed_quantity, planned_end_date FROM production_orders ORDER BY planned_end_date ASC LIMIT 15"
        if "bom" in ql or "bill of material" in ql or "component" in ql:
            return "SELECT bom_number, parent_material, component_material, component_quantity, component_type FROM bill_of_materials LIMIT 20"
        if "energy" in ql:
            return "SELECT heat_number, melt_date, energy_kwh FROM melting_heat_records ORDER BY melt_date DESC LIMIT 10"
        return "SELECT heat_number, melt_date, tap_temperature_c, quality_status FROM melting_heat_records ORDER BY melt_date DESC LIMIT 10"

    def _remember(self, user_query: str, answer: str) -> None:
        self.history.append({"user": user_query, "assistant": answer})
        self.history = self.history[-5:]

    def _format_history(self) -> str:
        if not self.history:
            return "(no prior history)"
        parts = []
        for turn in self.history:
            parts.append(f"User: {turn['user']}")
            parts.append(f"Assistant: {turn['assistant']}")
        return "\n".join(parts)
    
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