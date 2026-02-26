# Menon & Menon Foundry - AI Chatbot Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [LLM Configuration](#llm-configuration)
4. [Core Components](#core-components)
5. [Tool Capabilities](#tool-capabilities)
6. [Database Integration](#database-integration)
7. [Agent Intelligence](#agent-intelligence)
8. [User Interface](#user-interface)
9. [System Components](#system-components)
10. [Testing Guide](#testing-guide)

---

## Overview

The Menon & Menon Foundry AI Chatbot is an industrial-grade conversational assistant designed to provide real-time insights for foundry operations. It integrates market data, news intelligence, internal knowledge base access, and direct database querying capabilities to support decision-making in manufacturing environments.

**Key Capabilities:**
- Real-time commodity and metal price tracking
- Curated foundry industry news
- Access to Standard Operating Procedures (SOPs)
- Production data analytics via natural language SQL
- Conversational memory for context-aware interactions

---

## Architecture

### System Design
```
User Query → Dashboard (Streamlit UI)
           ↓
    AgentBrain (core/brain.py)
           ↓
    LLM-Driven Tool Selection
           ↓
    Tool Execution (core/tools.py)
           ├─ get_market_data → metals.live API + YFinance
           ├─ get_global_news → GNews API
           ├─ query_internal_sops → ChromaDB
           └─ query_foundry_db → PostgreSQL
           ↓
    Response Summarization (LLM)
           ↓
    Formatted Output → User
```

### Technology Stack
- **LLM Framework:** LangChain
- **LLM Provider:** Groq (llama-3.1-8b-instant)
- **Database:** PostgreSQL (foundry_db)
- **Vector Store:** ChromaDB with SentenceTransformer embeddings
- **UI Framework:** Streamlit
- **APIs:** metals.live, GNews, YFinance

---

## LLM Configuration

### Primary Model
- **Provider:** Groq Cloud API
- **Model:** `llama-3.1-8b-instant`
- **Temperature:** 0 (deterministic responses)
- **Purpose:** 
  - Tool selection decision-making
  - Response summarization
  - SQL query generation (via heuristics + LLM fallback)

### Key Characteristics
- **Deterministic:** Temperature 0 ensures consistent, repeatable responses for production environments
- **Fast Inference:** Groq's hardware acceleration provides sub-second latency
- **Context Window:** Sufficient for full schema + conversation history (5 turns)
- **Cost-Effective:** Groq's competitive pricing for high-volume queries

### LLM Usage Modes
1. **Tool Selection:** Analyzes user intent and selects appropriate tool via JSON response
2. **Summarization:** Formats raw tool outputs into user-friendly natural language
3. **Fallback Generation:** Handles edge cases and non-tool queries

---

## Core Components

### 1. AgentBrain (`core/brain.py`)
Central orchestrator managing the query-response lifecycle.

**Key Methods:**
- `ask(user_query: str) → str`: Main entry point for user interactions
- `_decide_action(query: str) → dict`: Determines which tool to invoke
- `_summarize_response(...)`: Converts tool outputs to natural language
- `_default_db_query(query: str) → str`: Generates SQL templates for common queries
- `_remember(query: str, response: str)`: Maintains 5-turn conversation memory

**Decision Logic:**
1. **Heuristic Fast-Path:** Keyword matching (e.g., "price" → market data)
2. **LLM Decision:** JSON-structured tool selection for ambiguous queries
3. **Fallback:** Default database query or conversational response

**System Prompt:**
Contains full database schema (11 tables), tool descriptions, SQL best practices, and formatting guidelines. Instructs the LLM to:
- Use aggregates (AVG, SUM, COUNT) for analytics
- Apply GROUP BY for breakdowns
- Include LIMIT 50 for safety
- Format numeric results clearly

### 2. Tool Suite (`core/tools.py`)
Four specialized tools accessible by the agent.

---

## Tool Capabilities

### 1. `get_market_data(query: str) → str`
**Purpose:** Real-time commodity, metal, and stock price tracking

**Data Sources:**
- **Primary:** metals.live API (per-metal endpoint)
  - Copper, Aluminum, Nickel, Zinc, Lead, Tin
  - Iron ore, Pig iron, Scrap steel
- **Fallback:** YFinance for stocks/indices
  - Steel (X), US Steel (X), Copper Miners (FCX), Aluminum (AA)

**Key Features:**
- Multi-metal batch requests
- Explicit fallback labeling (e.g., "Reference: US Steel Corporation stock")
- Error handling with graceful degradation
- Currency normalization (USD per ton/pound)

**Example Queries:**
- "What is the copper price today?"
- "Show me aluminum and nickel prices"
- "Steel stock price" (triggers YFinance fallback)

**Technical Details:**
```python
METAL_PRICE_MAP = {
    "copper": "copper",
    "aluminum": "aluminum", 
    "iron": "iron-ore",
    "pig iron": "pig-iron",
    "scrap steel": "steel-scrap",
    # ... full mapping
}
```

---

### 2. `get_global_news(query: str) → str`
**Purpose:** Curated foundry and manufacturing industry news

**Data Source:**
- **API:** GNews (GNEWS_API_KEY in `.env`)
- **Query Strategy:** Topic mapping to foundry-relevant keywords

**Topic Mapping:**
```python
"steel" → "steel foundry manufacturing"
"foundry" → "foundry casting iron steel"
"scrap" → "scrap metal recycling"
"casting" → "metal casting manufacturing"
"aluminum" → "aluminum industry production"
# ... full mapping
```

**Configuration:**
- **Language:** English
- **Max Results:** 5 articles
- **Sorting:** Relevancy-based
- **Country:** Global (no regional filter)

**Output Format:**
- Title, Source, Published Date, URL
- Markdown formatting for readability

**Example Queries:**
- "Latest steel industry news"
- "News about scrap metal"
- "Foundry news"

---

### 3. `query_internal_sops(query: str) → str`
**Purpose:** Semantic search over Standard Operating Procedures

**Technology:**
- **Vector Store:** ChromaDB (`chroma_db/`)
- **Embeddings:** SentenceTransformer (`all-MiniLM-L6-v2`)
- **Collection:** `foundry_sops`

**Features:**
- Similarity-based retrieval (top-k=3)
- Contextual snippet extraction
- Source document tracking

**Data Ingestion:**
- Managed by `ingest_knowledge.py`
- Supports PDF, TXT, DOCX formats
- Automatic chunking and embedding

**Example Queries:**
- "What is the furnace lining procedure?"
- "Safety procedure for pouring"
- "Heat treatment guidelines"

**Technical Details:**
- **Embedding Dimension:** 384
- **Similarity Metric:** Cosine
- **Retrieval Count:** 3 most relevant chunks

---

### 4. `query_foundry_db(natural_language_query: str) → str`
**Purpose:** Natural language to SQL translation with safety guardrails

**Database Schema (11 Tables):**

#### Production Core
1. **material_master**: Material catalog (types, descriptions, pricing)
2. **bill_of_materials**: Component hierarchies
3. **production_orders**: Order lifecycle tracking

#### Manufacturing Process
4. **melting_heat_records**: Furnace operations (temperature, yield, energy)
5. **molding_records**: Molding quality and defects
6. **casting_records**: Casting yields and grades
7. **heat_treatment**: Post-casting treatments
8. **machining_operations**: Final machining steps

#### Quality & Logistics
9. **quality_inspections**: Inspection results and defect tracking
10. **inventory_movements**: Stock transactions
11. **equipment_maintenance**: Asset maintenance and downtime

**SQL Generation Strategies:**

**A. Template-Based (Default):**
Pre-built query templates triggered by keyword heuristics:
- **Aggregates:** AVG tap temperature, SUM scrap, COUNT rejections
- **Breakdowns:** GROUP BY product_type, quality_grade, order_status
- **Details:** Recent records (ORDER BY date DESC LIMIT 10-15)

**B. LLM-Generated (Fallback):**
When no template matches, LLM constructs SQL using full schema context.

**Safety Guardrails:**
- **Read-Only:** Only SELECT statements allowed
- **Injection Prevention:** Parameterized queries via psycopg2
- **Row Limiting:** Auto-appends LIMIT 50 if missing
- **Validation:** Regex check for forbidden keywords (DROP, DELETE, UPDATE)

**Output Format:**
- Markdown tables for multi-row results
- Single values for aggregates (e.g., "Average: 1425.3°C")
- Error messages for invalid queries

**Example Queries:**
- "What is the average tap temperature?"
- "Total scrap castings"
- "How many rejected heats?"
- "Show recent yield data"
- "Inventory levels"
- "Maintenance status by type"

**Advanced Analytics:**
```sql
-- Average yield by product type
SELECT product_type, ROUND(AVG(yield_pct)::numeric, 2) AS avg_yield 
FROM casting_records 
GROUP BY product_type

-- Inspection decision breakdown
SELECT overall_decision, COUNT(*) AS cnt 
FROM quality_inspections 
GROUP BY overall_decision
```

---

## Database Integration

### Connection Configuration
- **Host:** Loaded from `InputPipeline/foundry_config.py`
- **Database:** `foundry_db`
- **Driver:** psycopg2
- **Connection Pooling:** Per-query connections (no persistent pool)

### Schema Highlights

**Critical Columns for Analytics:**
- `tap_temperature_c`, `pour_temperature_c` (melting_heat_records)
- `yield_pct` (melting_heat_records, casting_records)
- `quality_status`, `quality_grade` (multiple tables)
- `defect_count`, `overall_decision` (quality_inspections)
- `downtime_hours`, `total_cost_usd` (equipment_maintenance)
- `order_status`, `scrap_quantity` (production_orders)

**Relationships:**
- `production_orders` ↔ `melting_heat_records` (via heat_number)
- `casting_records` ↔ `heat_treatment` (via casting_batch)
- `quality_inspections` ↔ `material_master` (via material_number)

### Data Pipeline
Data ingestion handled by `InputPipeline/run_all_feeders.py`:
- CSV → PostgreSQL bulk insert
- Automatic schema validation
- Transaction management

---

## Agent Intelligence

### Conversation Memory
- **Storage:** In-memory deque (5 turns)
- **Format:** List of `{"query": "...", "response": "..."}` dicts
- **Purpose:** Context-aware follow-up queries

**Example Flow:**
```
User: "What is the average tap temperature?"
Bot: "The average tap temperature is 1425.3°C."

User: "Show me the last 5 records"
Bot: [Uses memory to infer "records" = melting_heat_records]
```

### Decision-Making Process

**Step 1: Heuristic Fast-Path**
```python
if "price" in query or "cost" in query:
    return {"tool": "get_market_data", "input": query}
if "news" in query:
    return {"tool": "get_global_news", "input": query}
# ... etc.
```

**Step 2: LLM Decision**
If no heuristic matches:
```python
messages = [
    SystemMessage(system_prompt),
    HumanMessage(f"Which tool for: {query}? Reply JSON only.")
]
response = llm.invoke(messages)
parsed = {"tool": "query_foundry_db", "input": "..."}
```

**Step 3: Tool Execution**
```python
if tool_name == "get_market_data":
    tool_output = get_market_data(tool_input)
elif tool_name == "query_foundry_db":
    tool_output = query_foundry_db(tool_input)
# ... etc.
```

**Step 4: Response Formatting**
```python
final_response = _summarize_response(
    user_query=query,
    tool_name=tool_name,
    tool_input=tool_input,
    tool_output=tool_output
)
```

### Error Handling
- **API Failures:** Graceful degradation with fallback messages
- **SQL Errors:** Returns error message without exposing raw SQL
- **LLM Errors:** Displays raw tool output with truncated error
- **Empty Results:** Informs user politely ("No data found")

---

## User Interface

### Dashboard (`dashboard.py`)
Streamlit-based multi-tab interface.

**Tabs:**
1. **Overview:** System metrics and KPIs
2. **Chat:** Conversational AI interface (primary chatbot UI)
3. **Analytics:** Data visualizations
4. **Reports:** Pre-built report templates

### Chat Tab Features
- **High-Contrast Theme:** Slate background (#1e293b) with teal accents (#06b6d4)
- **Message Bubbles:**
  - User: Right-aligned, teal background (#0891b2)
  - Bot: Left-aligned, slate background (#334155)
- **Avatar Support:** Optional user/bot icons
- **Streaming:** Future-ready for streaming responses

**CSS Styling:**
```css
.stChatMessage[data-testid="user-message"] {
    background-color: #0891b2 !important;
    color: white !important;
}
.stChatMessage[data-testid="assistant-message"] {
    background-color: #334155 !important;
    color: #e2e8f0 !important;
}
```

### Session State Management
- `st.session_state.messages[]`: Chat history persistence
- `st.session_state.agent_brain`: Singleton AgentBrain instance
- Automatic scroll to latest message

---

## System Components

### 1. Input Pipeline (`InputPipeline/`)
**Purpose:** Data ingestion from external sources to PostgreSQL

**Components:**
- `foundry_config.py`: Database credentials (DB_CONFIG)
- `foundry_feeder.py`: Individual table feeders (CSV → SQL)
- `run_all_feeders.py`: Orchestrates bulk ingestion

**Execution:**
```bash
python InputPipeline/run_all_feeders.py
```

**Data Flow:**
```
CSV Files → Pandas DataFrames → psycopg2 Bulk Insert → PostgreSQL
```

### 2. Knowledge Base Ingestion (`ingest_knowledge.py`)
**Purpose:** Load SOPs into ChromaDB

**Process:**
1. Load documents from `knowledge_docs/` folder
2. Split into chunks (500 chars, 100 char overlap)
3. Generate embeddings via SentenceTransformer
4. Store in ChromaDB collection

**Execution:**
```bash
python ingest_knowledge.py
```

### 3. Utilities
- `check.py`: System health checks
- `test.py`: Unit tests for tools and brain
- `executer.py`: Background task executor (if applicable)

### 4. Environment Configuration
**`.env` File:**
```bash
GROQ_API_KEY=gsk_...
GNEWS_API_KEY=...
DB_HOST=localhost
DB_PORT=5432
DB_NAME=foundry_db
DB_USER=...
DB_PASSWORD=...
```

### 5. Dependencies (`requirements.txt`)
Key packages:
- `langchain`, `langchain-groq`: LLM orchestration
- `streamlit`: UI framework
- `psycopg2-binary`: PostgreSQL connector
- `chromadb`: Vector database
- `sentence-transformers`: Embeddings
- `requests`, `yfinance`: API clients
- `pandas`, `numpy`: Data processing

---

## Testing Guide

### Manual Test Queries

#### Market Data (Tool 1)
```
✅ "What is the current copper price?"
✅ "Iron price today"
✅ "Show me aluminum and nickel prices"
✅ "Steel stock price" (triggers YFinance fallback)
```

#### News (Tool 2)
```
✅ "Latest steel industry news"
✅ "News about scrap metal"
✅ "Foundry news"
```

#### SOPs (Tool 3)
```
✅ "What is the furnace lining procedure?"
✅ "Safety procedure for pouring"
✅ "Heat treatment guidelines"
```

#### Database Queries (Tool 4)
**Aggregates:**
```
✅ "What is the average tap temperature?"
✅ "Total scrap castings"
✅ "Average yield percentage"
✅ "Total maintenance costs"
```

**Counts & Breakdowns:**
```
✅ "How many rejected heats?"
✅ "Inspection counts by decision"
✅ "Production order status breakdown"
✅ "Maintenance types summary"
```

**Details:**
```
✅ "Show recent yield data"
✅ "Latest inventory movements"
✅ "Current maintenance status"
✅ "Recent machining operations"
```

**Advanced Analytics:**
```
✅ "Average yield by product type"
✅ "Scrap castings per product"
✅ "Quality grades distribution"
```

#### Edge Cases
```
✅ "Hello" (fallback greeting)
✅ "Tell me about copper prices and latest news" (multi-intent)
✅ "Explain what you can do" (capability overview)
```

### Expected Behavior
- **Response Time:** <3 seconds per query
- **Accuracy:** 95%+ for single-intent queries
- **Formatting:** No tool names exposed; clean, professional output
- **Error Handling:** Polite messages for failures, no raw stack traces

### Running the Chatbot
```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start Streamlit dashboard
streamlit run dashboard.py
```

Navigate to the **Chat** tab and test queries.

---

## Performance Characteristics

### Latency Breakdown
- **Heuristic Tool Selection:** <50ms
- **LLM Tool Selection:** 200-500ms (Groq inference)
- **API Calls:** 500-2000ms (external APIs)
- **Database Queries:** 100-500ms (depends on query complexity)
- **LLM Summarization:** 300-800ms
- **Total End-to-End:** 1-4 seconds (typical)

### Scalability Considerations
- **Concurrent Users:** Streamlit supports ~10-20 users (single process)
- **Database Load:** Read-only queries; no write contention
- **API Rate Limits:** 
  - GNews: 100 requests/day (free tier)
  - metals.live: Unlimited (as of implementation)
  - Groq: 14,400 requests/day (free tier)

### Optimization Opportunities
1. **Caching:** Implement TTL cache for market data (5-minute refresh)
2. **Connection Pooling:** PostgreSQL connection pool for high concurrency
3. **Streaming Responses:** Gradual UI updates for long-running queries
4. **Model Upgrade:** GPT-4 for complex SQL generation (if needed)

---

## Maintenance & Monitoring

### Log Files
- **Streamlit Logs:** Console output (errors, warnings)
- **Database Logs:** PostgreSQL query logs (via pg_stat_statements)
- **API Logs:** Request/response tracking (implement as needed)

### Health Checks
Run `python check.py` to validate:
- Database connectivity
- API key validity
- ChromaDB availability
- Model inference

### Updating Knowledge Base
```bash
# Add new SOP documents to knowledge_docs/
python ingest_knowledge.py
```

### Updating Database Schema
1. Modify PostgreSQL schema
2. Update `DB_CONFIG` in `foundry_config.py`
3. Update system prompt in `brain.py` (schema cheat sheet)
4. Update `_default_db_query()` templates as needed

---

## Security & Compliance

### Data Protection
- **SQL Injection:** Parameterized queries via psycopg2
- **Read-Only Access:** Database user permissions restricted to SELECT
- **API Keys:** Stored in `.env` (excluded from version control)

### Privacy
- **No Personal Data:** System does not store user identities
- **Session Isolation:** Streamlit sessions are user-specific
- **Conversation Retention:** 5-turn memory only (in-memory, not persisted)

### Compliance
- **GDPR:** No PII collection
- **SOC 2:** Groq and GNews are SOC 2 compliant providers
- **Data Residency:** PostgreSQL can be deployed on-premises

---

## Future Enhancements

### Planned Features
1. **Streaming Responses:** Real-time token-by-token output
2. **Multi-Turn SQL:** Follow-up query refinement without re-querying
3. **Voice Interface:** Speech-to-text/text-to-speech integration
4. **Predictive Analytics:** Time-series forecasting for yield trends
5. **Alert System:** Proactive notifications for anomalies

### Model Upgrades
- **GPT-4 Turbo:** For complex multi-table JOIN queries
- **Claude 3 Opus:** For nuanced SOP reasoning
- **Mixtral 8x7B:** Cost-effective alternative with better SQL generation

### Integration Extensions
- **ERP Integration:** SAP/Oracle connectors
- **IoT Sensors:** Real-time equipment telemetry
- **BI Tools:** Tableau/Power BI embedding

---

## Troubleshooting

### Common Issues

**1. "No data found" for DB queries:**
- Check PostgreSQL service status
- Verify DB_CONFIG credentials
- Ensure tables are populated

**2. News API errors:**
- Validate GNEWS_API_KEY in `.env`
- Check daily rate limit (100 requests/day)

**3. Market data fallback:**
- metals.live may be rate-limited; YFinance kicks in
- Verify internet connectivity

**4. LLM timeout:**
- Groq API may be temporarily unavailable
- Check GROQ_API_KEY validity

**5. ChromaDB empty results:**
- Re-run `python ingest_knowledge.py`
- Verify `chroma_db/` directory exists

---

## Conclusion

The Menon & Menon Foundry AI Chatbot represents a production-ready industrial AI assistant, combining:
- **Real-time external data** (market prices, news)
- **Internal knowledge** (SOPs, procedures)
- **Operational analytics** (production metrics, quality tracking)
- **Intelligent orchestration** (LLM-driven tool selection)

The system is designed for:
- **Reliability:** Graceful error handling and fallback mechanisms
- **Performance:** Sub-3-second response times for typical queries
- **Scalability:** Modular architecture for easy extension
- **Usability:** Natural language interface for non-technical users

For questions or support, contact the development team.

---

**Document Version:** 1.0  
**Last Updated:** February 26, 2026  
**Author:** System Documentation Team
