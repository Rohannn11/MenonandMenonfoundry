import streamlit as st
import psycopg2
import os
import time
from dotenv import load_dotenv
from foundry_brain import FoundryBrain

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Foundry OS Final",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)
load_dotenv()

# --- 2. CSS STYLING (Dark Industrial Theme) ---
st.markdown("""
<style>
    /* Main Background */
    .stApp { background-color: #0f1215; color: #e0e6ed; }
    
    /* Metrics Cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 35, 40, 0.9), rgba(20, 25, 30, 0.9));
        border: 1px solid #333;
        border-left: 5px solid #00ccff;
        padding: 15px;
        border-radius: 6px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 15px;
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-2px); border-left-color: #00ff99; }
    
    /* Text Styles */
    .card-label { font-size: 12px; text-transform: uppercase; color: #8899a6; letter-spacing: 1px; }
    .card-value { font-size: 28px; font-weight: 700; color: #ffffff; font-family: 'Courier New', monospace; }
    .card-meta { font-size: 11px; color: #555; text-align: right; margin-top: 5px; }
    
    /* Chat Interface */
    .stChatMessage { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; }
    .stChatInput { background-color: #0d1117; }
</style>
""", unsafe_allow_html=True)

# --- 3. INITIALIZATION (Cached) ---
@st.cache_resource
def get_brain():
    """Load the Agent (Llama 3 + Tools). Runs once."""
    return FoundryBrain()

@st.cache_resource
def get_db_connection():
    """Connect to Postgres. Cached to prevent reconnection loops."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT")
    )

try:
    brain = get_brain()
    # Test DB connection briefly
    conn = get_db_connection()
    conn.close()
    db_status = "ONLINE"
except Exception as e:
    db_status = "OFFLINE"
    st.error(f"System Startup Error: {e}")

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🏭 FOUNDRY OS")
    st.caption(f"System Status: {db_status}")
    st.markdown("---")
    
    st.subheader("Agent Capabilities")
    st.info("🧠 **Model:** Llama 3.3 (70B)")
    st.success("🔌 **Connected Tools:**\n- PostgreSQL (Live Data)\n- ChromaDB (SOPs)\n- NewsAPI (Global)\n- OpenMeteo (Weather)\n- Yahoo Finance (Markets)")
    
    st.markdown("---")
    if st.button("🗑️ Clear Chat Memory"):
        st.session_state.messages = []
        st.rerun()

# --- 5. MAIN TABS ---
tab_live, tab_agent = st.tabs(["🚀 LIVE OPERATIONS", "🌐 OMNI-AGENT"])

# ==================================================
# TAB 1: LIVE OPERATIONS (The Command Center)
# ==================================================
with tab_live:
    col_header, col_btn = st.columns([4,1])
    with col_header:
        st.markdown("### 📊 PRODUCTION METRICS")
    with col_btn:
        if st.button("🔄 Refresh Data"):
            st.rerun()

    # Define the Pipelines we want to monitor
    PIPELINES = [
        {"name": "01 Raw Materials", "table": "material_master", "pk": "material_number"},
        {"name": "03 Melting Furnaces", "table": "melting_heat_records", "pk": "heat_number"},
        {"name": "04 Molding Lines", "table": "molding_records", "pk": "production_order"},
        {"name": "05 Casting Batches", "table": "casting_records", "pk": "casting_batch"},
        {"name": "09 Inventory Ops", "table": "inventory_movements", "pk": "document_number"},
        {"name": "11 Maintenance Orders", "table": "equipment_maintenance", "pk": "maintenance_order"}
    ]

    try:
        # Fetch Data
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create a Grid Layout
        cols = st.columns(3)
        
        for i, p in enumerate(PIPELINES):
            # Get Total Count
            cur.execute(f"SELECT COUNT(*) FROM {p['table']}")
            count = cur.fetchone()[0]
            
            # Get Latest ID
            cur.execute(f"SELECT {p['pk']} FROM {p['table']} ORDER BY {p['pk']} DESC LIMIT 1")
            last_id = cur.fetchone()
            last_id_str = str(last_id[0]) if last_id else "N/A"
            
            # Render Card
            with cols[i % 3]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="card-label">{p['name']}</div>
                    <div class="card-value">{count:,}</div>
                    <div class="card-meta">LATEST ID: {last_id_str}</div>
                </div>
                """, unsafe_allow_html=True)
        
        cur.close()
        
    except Exception as e:
        st.error(f"Live Data Error: {e}")

# ==================================================
# TAB 2: OMNI-AGENT (The Flexible Chat)
# ==================================================
with tab_agent:
    st.markdown("### 💬 CONTEXTUAL INTERFACE")
    
    # Initialize Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant", 
            "content": "I am online. I can access factory databases, SOPs, and live global market data. How can I assist?"
        }]

    # Display History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input("Ask anything (e.g., 'Compare our scrap inventory with global steel prices')..."):
        # 1. User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Agent Response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # The Brain handles the routing dynamically
                    answer, src, intent = brain.ask(prompt)
                    
                    st.markdown(answer)
                    
                    # Optional: Add technical details in an expander
                    with st.expander("🔍 View Process Details"):
                        st.markdown(f"**Intent:** {intent}")
                        st.markdown(f"**Source:** {src}")
                    
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                except Exception as e:
                    st.error(f"Agent Failure: {e}")