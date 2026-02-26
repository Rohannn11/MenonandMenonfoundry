# Menon & Menon Foundry Management System

An intelligent AI-powered platform for foundry operations — combining a conversational chatbot, real-time market data, production analytics, and knowledge base access in a single unified interface.

---

## Overview

The Menon & Menon Foundry OS allows operators and managers to ask questions about their production in plain English and receive instant, data-driven answers. No SQL knowledge or technical expertise required.

**Core capabilities:**
- Natural language querying of production databases (PostgreSQL)
- Real-time metal and commodity price tracking
- Curated foundry industry news
- Standard Operating Procedure (SOP) lookup via semantic search
- Interactive analytics dashboard (Streamlit)
- Conversational memory across a session (5-turn context)

---

## Architecture

```
User Query → Streamlit Dashboard (dashboard.py)
                    ↓
           AgentBrain (core/brain.py)
                    ↓
         LLM-Driven Tool Selection (Groq / LLaMA 3.1)
                    ↓
         Tool Execution (core/tools.py)
           ├─ get_market_data     → metals.live API + YFinance
           ├─ get_global_news     → GNews API
           ├─ query_internal_sops → ChromaDB (vector search)
           └─ query_foundry_db    → PostgreSQL
                    ↓
         Response Summarization (LLM)
                    ↓
         Formatted Output → User
```

**Tech Stack:**

| Layer | Technology |
|---|---|
| LLM | Groq Cloud (`llama-3.1-8b-instant`) |
| Orchestration | LangChain |
| Vector Store | ChromaDB + SentenceTransformers |
| Database | PostgreSQL (`foundry_db`) |
| UI | Streamlit |
| Market Data | metals.live, YFinance |
| News | GNews API |

---

## Project Structure

```
├── dashboard.py            # Streamlit UI — main entry point
├── executer.py             # CLI query runner
├── ingest_knowledge.py     # Ingests SOPs into ChromaDB
├── setup_env.py            # Guided environment setup
├── schema.sql              # PostgreSQL schema definition
├── requirements.txt        # Python dependencies
│
├── core/
│   ├── brain.py            # AgentBrain — central orchestrator
│   ├── tools.py            # Tool implementations (market, news, DB, SOPs)
│   └── intent_router.py    # Heuristic + LLM-based intent routing
│
├── InputPipeline/
│   ├── foundry_feeder.py   # Feeds production data into the DB
│   ├── foundry_config.py   # Pipeline configuration
│   └── run_all_feeders.py  # Runs all data feeders
│
├── chroma_db/              # Persisted vector store for SOPs
└── tests/
    └── test_system.py      # System-level tests
```

---

## Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL (running locally or remote)

### 1. Install Dependencies

```bash
# Recommended: guided setup
python setup_env.py

# Or manually
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
NEWS_API_KEY=your_gnews_api_key
METAL_PRICE=your_metals_live_api_key
DB_NAME=foundry_db
DB_USER=postgres
DB_PASS=your_password
DB_HOST=localhost
```

### 3. Set Up the Database

```bash
psql -U postgres -f schema.sql
```

### 4. Ingest the Knowledge Base (SOPs)

```bash
python ingest_knowledge.py
```

### 5. (Optional) Run Data Feeders

```bash
python InputPipeline/run_all_feeders.py
```

### 6. Launch the Dashboard

```bash
streamlit run dashboard.py
```

---

## Usage

### Dashboard Tabs

| Tab | Description |
|---|---|
| **Overview** | KPI dashboard — yield, defects, temperatures, orders |
| **Chat** | AI assistant — ask anything in plain English |
| **Analytics** | Charts and production visualizations |
| **Reports** | Pre-built report templates |

### Example Queries

```
"What is the copper price today?"
"Show me the latest steel industry news."
"What is the average tap temperature this month?"
"How many rejected heats do we have?"
"What is our current inventory level?"
"How do I line a furnace?" (SOP lookup)
```

---

## Key Components

### `core/brain.py` — AgentBrain
The central orchestrator. Receives a user query, routes it to the correct tool via heuristic keyword matching or LLM decision-making, executes the tool, and returns a summarized natural language response. Maintains a 5-turn conversational memory.

### `core/tools.py` — Tools
Implements the four primary tools:
- **Market Data:** Fetches live metal prices (copper, aluminum, nickel, zinc, lead, tin, iron ore, scrap steel) and stock data.
- **News:** Retrieves curated foundry and steel industry news via GNews.
- **SOP Search:** Semantic search over ingested procedures stored in ChromaDB.
- **DB Query:** Converts natural language to SQL and queries PostgreSQL for production records.

### `core/intent_router.py` — Intent Router
Two-stage routing: fast heuristic keyword matching first, followed by LLM-based JSON intent classification for ambiguous queries.

### `InputPipeline/` — Data Ingestion
Feeds raw production data (orders, heats, quality records, inventory, maintenance) into the PostgreSQL database.

---

## Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq Cloud API key for LLM inference |
| `NEWS_API_KEY` | GNews API key for industry news |
| `METAL_PRICE` | metals.live API key for commodity prices |
| `DB_NAME` | PostgreSQL database name (default: `foundry_db`) |
| `DB_USER` | PostgreSQL username |
| `DB_PASS` | PostgreSQL password |
| `DB_HOST` | PostgreSQL host (default: `localhost`) |

---

## License

See [LICENSE](LICENSE) for details.

