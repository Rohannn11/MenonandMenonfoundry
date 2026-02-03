import streamlit as st
import psycopg2
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Import the AI Brain
from core.brain import AgentBrain

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Menon Foundry OS",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

load_dotenv()

# --- 2. CSS STYLING (Dual Theme) ---
st.markdown("""
    <style>
    /* === GLOBAL DARK THEME (SCADA) === */
    .stApp {
        background-color: #0b0c10;
        color: #c5c6c7;
    }
    
    /* === TAB STYLING === */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: #1f2833;
        padding: 10px 20px;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #c5c6c7;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        color: #66fcf1 !important;
        border-bottom-color: #66fcf1 !important;
    }

    /* === SCADA CARD STYLES (TAB 1) === */
    div[data-testid="stMetricValue"] {
        font-family: 'Consolas', monospace;
        color: #66fcf1 !important;
    }
    .scada-card {
        background-color: #1f2833;
        border: 1px solid #45a29e;
        border-radius: 4px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .status-ok { border-left: 5px solid #00FF00; }
    .status-warn { border-left: 5px solid #FFA500; }
    .status-crit { border-left: 5px solid #FF0000; }
    .status-idle { border-left: 5px solid #555; }
    
    .card-title { font-size: 14px; font-weight: bold; color: #fff; text-transform: uppercase; }
    .card-value { font-size: 24px; font-family: 'Consolas', monospace; color: #66fcf1; font-weight: bold; }
    .data-row { font-family: 'Courier New', monospace; font-size: 11px; color: #c5c6c7; margin-top: 5px; border-top: 1px solid #333; padding-top: 5px; }
    .highlight-val { color: #fff; font-weight: bold; }
    
    .console-box { 
        background-color: #000; color: #00FF00; 
        font-family: 'Courier New', monospace; 
        padding: 10px; height: 200px; 
        overflow-y: scroll; border: 1px solid #333; 
        font-size: 12px; 
    }

    /* === CHATBOT THEME (TAB 2) - Light Purple & Black === */
    /* This targets the specific chat message containers */
    
    /* User Message */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #E0E0E0 !important; /* Light Grey */
        border: 1px solid #ccc;
        color: #000000 !important;
    }
    
    /* Assistant Message */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #E6E6FA !important; /* Lavender / Light Purple */
        border: 1px solid #9370DB;
        color: #000000 !important;
    }
    
    /* Force text inside chat bubbles to be black for visibility */
    .stChatMessage p {
        color: #000000 !important;
        font-weight: 500;
    }
    
    /* Chat Input Area */
    .stChatInputContainer {
        padding-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONFIG & CONNECTIONS ---

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "port": os.getenv("DB_PORT", "5432")
}

PIPELINES = [
    {"name": "01 MATERIALS", "table": "material_master", "pk": "Material_Number", "cols": ["Material_Type", "Base_Unit", "Procurement_Type"], "status_col": "Procurement_Type", "crit_vals": []},
    {"name": "02 BOMs", "table": "bill_of_materials", "pk": "BOM_Number", "cols": ["Parent_Material", "Component_Type", "BOM_Status"], "status_col": "BOM_Status", "crit_vals": ["INACTIVE", "PENDING"]},
    {"name": "03 MELTING", "table": "melting_heat_records", "pk": "Heat_Number", "cols": ["Target_Alloy", "Tap_Temperature_C", "Quality_Status"], "status_col": "Quality_Status", "crit_vals": ["REJECTED"]},
    {"name": "04 MOLDING", "table": "molding_records", "pk": "Production_Order", "cols": ["Molding_Type", "Defect_Type", "Quality_Check"], "status_col": "Quality_Check", "crit_vals": ["FAIL", "REWORK"]},
    {"name": "05 CASTING", "table": "casting_records", "pk": "Casting_Batch", "cols": ["Product_Type", "Defects_Detected", "Quality_Grade"], "status_col": "Quality_Grade", "crit_vals": ["SCRAP", "C"]},
    {"name": "06 HEAT TREAT", "table": "heat_treatments", "pk": "HT_Batch_Number", "cols": ["Treatment_Type", "Rejection_Reason", "Quality_Status"], "status_col": "Quality_Status", "crit_vals": ["REJECTED", "REWORK"]},
    {"name": "07 MACHINING", "table": "machining_operations", "pk": "Operation_ID", "cols": ["Machine_Type", "Defect_Type", "Quality_Status"], "status_col": "Quality_Status", "crit_vals": ["FAIL", "REWORK"]},
    {"name": "08 QUALITY QC", "table": "quality_inspections", "pk": "Inspection_Lot", "cols": ["Inspection_Stage", "Defect_Count", "Overall_Decision"], "status_col": "Overall_Decision", "crit_vals": ["REJECT", "CONDITIONAL"]},
    {"name": "09 INVENTORY", "table": "inventory_movements", "pk": "Document_Number", "cols": ["Movement_Type", "Quantity", "Material_Number"], "status_col": "Movement_Type", "crit_vals": ["SCRAP", "RETURN"]},
    {"name": "10 PRODUCTION", "table": "production_orders", "pk": "Production_Order", "cols": ["Order_Status", "Priority", "Product_Type"], "status_col": "Order_Status", "crit_vals": ["CLOSED"]},
    {"name": "11 MAINTENANCE", "table": "equipment_maintenance", "pk": "Maintenance_Order", "cols": ["Equipment_Type", "Maintenance_Type", "Status"], "status_col": "Maintenance_Type", "crit_vals": ["BREAKDOWN", "CORRECTIVE"]},
]

def get_db_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except: return None

@st.cache_resource
def get_agent():
    return AgentBrain()

def fetch_live_data(conn):
    state = {}
    total_rows = 0
    try:
        cursor = conn.cursor()
        for p in PIPELINES:
            cursor.execute(f"SELECT COUNT(*) FROM {p['table']}")
            count = cursor.fetchone()[0]
            total_rows += count
            
            cols_query = ", ".join([p['pk']] + p['cols'])
            cursor.execute(f"SELECT {cols_query} FROM {p['table']} ORDER BY {p['pk']} DESC LIMIT 1")
            last_row = cursor.fetchone()
            
            state[p['name']] = {
                "count": count, "data": last_row,
                "keys": [p['pk']] + p['cols'],
                "status_check": (p['status_col'], p['crit_vals'])
            }
        return state, total_rows
    except: return None, 0

# --- 4. LAYOUT SETUP ---
st.title("🏭 Menon & Menon Foundry OS")
tab1, tab2 = st.tabs(["📊 LIVE OPERATIONS (SCADA)", "🤖 INTELLIGENCE AGENT"])

# ==========================================
# TAB 1: LIVE SCADA (Unchanged Logic)
# ==========================================
with tab1:
    c1, c2 = st.columns([3, 1])
    c1.markdown("Monitor real-time ingestion from **11 Parallel Pipelines**.")
    
    # CONTROL: Live Refresh Toggle
    # We store this in session state so it persists
    if "live_mode" not in st.session_state: st.session_state["live_mode"] = True
    
    live_mode = c2.toggle("🔴 LIVE REFRESH", value=st.session_state["live_mode"], key="toggle_live")
    st.session_state["live_mode"] = live_mode # Sync state

    # Init State
    if "prev_total" not in st.session_state: st.session_state["prev_total"] = 0
    if "console_logs" not in st.session_state: st.session_state["console_logs"] = []

    # Data Fetch
    conn = get_db_connection()
    if conn:
        current_state, total_rows = fetch_live_data(conn)
        conn.close()

        if current_state:
            # Metrics
            velocity = total_rows - st.session_state["prev_total"]
            st.session_state["prev_total"] = total_rows
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Records", f"{total_rows:,}")
            m2.metric("System Velocity", f"{velocity} events/sec")
            if velocity > 0: m3.success("SYSTEM ONLINE")
            else: m3.info("SYSTEM IDLE")

            # Logging
            if velocity > 0:
                ts = datetime.now().strftime("%H:%M:%S")
                st.session_state["console_logs"].append(f"[{ts}] [INFO] Processed {velocity} new records.")

            # Grid
            grid_placeholder = st.empty()
            with grid_placeholder.container():
                cols = st.columns(4)
                for i, p in enumerate(PIPELINES):
                    info = current_state[p['name']]
                    count = info['count']
                    row_data = info['data']
                    
                    pk_val = "WAITING"
                    details = {}
                    is_crit = False
                    
                    if row_data:
                        data_dict = dict(zip(info['keys'], row_data))
                        pk_val = data_dict.pop(p['pk'])
                        details = data_dict
                        
                        stat_col, crit_vals = info['status_check']
                        val = str(data_dict.get(stat_col, ""))
                        if val in crit_vals:
                            is_crit = True
                            ts = datetime.now().strftime("%H:%M:%S")
                            log_msg = f"[{ts}] [ALERT] {p['name']}: {pk_val} -> {stat_col}={val}"
                            if not st.session_state["console_logs"] or st.session_state["console_logs"][-1] != log_msg:
                                st.session_state["console_logs"].append(log_msg)

                    if is_crit: css_class = "status-crit"
                    elif velocity > 0: css_class = "status-ok"
                    else: css_class = "status-idle"

                    detail_html = "".join([f"<div><span style='color:#66fcf1'>{k}:</span> <span class='highlight-val'>{v}</span></div>" for k, v in details.items()])
                    
                    with cols[i % 4]:
                        st.markdown(f"""
                        <div class="scada-card {css_class}">
                            <div class="card-title">{p['name']} <span class="card-delta">{pk_val}</span></div>
                            <div class="card-value">{count:,}</div>
                            <div class="data-row">{detail_html}</div>
                        </div>
                        """, unsafe_allow_html=True)

            # Console Log
            st.markdown("### 📟 SYSTEM EVENT LOG")
            if len(st.session_state["console_logs"]) > 15:
                st.session_state["console_logs"] = st.session_state["console_logs"][-15:]
            logs_html = "<br>".join(reversed(st.session_state["console_logs"]))
            st.markdown(f'<div class="console-box">{logs_html}</div>', unsafe_allow_html=True)

    else:
        st.error("❌ DB Connection Failed. Is 'executor.py' running?")


# ==========================================
# TAB 2: AI AGENT (Light Purple Theme + Processing States)
# ==========================================
with tab2:
    st.markdown("### 🤖 Industrial Intelligence Agent")
    st.caption("Ask about prices, news, procedures, or combine multiple queries.")
    
    # Initialize Agent
    try:
        agent = get_agent()
        status_color = "🟢"
    except:
        agent = None
        status_color = "🔴"

    with st.sidebar:
        st.markdown(f"**Agent Status:** {status_color}")
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []

    # Chat Logic
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I'm the Foundry Intelligence Agent. I can help you with:\n\n📊 **Market Prices** - Ask about steel, copper, gold, oil, stocks\n📰 **Industry News** - Get latest trends and announcements\n📋 **SOPs & Procedures** - Foundry safety rules, maintenance guidelines\n🔀 **Combined Queries** - Mix multiple questions together\n\n*Example: \"What's the current steel price and any recent mining news?\"*"},
        ]

    # Render History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input("Ask about prices, news, SOPs, or combine them..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if agent:
                # Show processing state with spinner
                with st.spinner("🔄 Analyzing query... Routing to appropriate sources..."):
                    response = agent.ask(prompt)
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                st.error("❌ Agent is unavailable. Check GROQ_API_KEY in .env")

# ==========================================
# 5. GLOBAL EXECUTION CONTROL
# ==========================================
# This logic is placed at the end so BOTH tabs render first.
if live_mode:
    time.sleep(1)
    st.rerun()