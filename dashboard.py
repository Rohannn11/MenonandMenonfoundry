import streamlit as st
import time
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
from foundry_brain import FoundryBrain
from api_connectors import get_metal_prices

# --- CONFIG ---
st.set_page_config(page_title="Foundry OS 3.0", page_icon="🏗️", layout="wide")
load_dotenv()

# --- CUSTOM CSS (Industrial Amber + Deep Steel) ---
st.markdown("""
<style>
    /* FONTS */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&family=Share+Tech+Mono&display=swap');

    /* BASE COLORS */
    .stApp { background-color: #0f1215; color: #e0e6ed; }

    /* HEADERS */
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #ffbf00; text-transform: uppercase; letter-spacing: 2px; }
    
    /* CARDS */
    .metric-card {
        background: rgba(30, 35, 40, 0.7);
        border: 1px solid #333;
        border-left: 4px solid #444;
        padding: 15px;
        border-radius: 4px;
        backdrop-filter: blur(5px);
        margin-bottom: 10px;
    }
    .metric-card:hover { border-left: 4px solid #ffbf00; box-shadow: 0 0 10px rgba(255, 191, 0, 0.1); }
    
    /* CRITICAL ALERT PULSE */
    @keyframes pulse { 0% { border-color: #ff0000; } 50% { border-color: #500000; } 100% { border-color: #ff0000; } }
    .card-crit { border-left: 4px solid #ff0000 !important; animation: pulse 2s infinite; }
    
    /* TEXT STYLES */
    .mono-text { font-family: 'Share Tech Mono', monospace; font-size: 14px; color: #a0aab5; }
    .big-num { font-family: 'Orbitron', sans-serif; font-size: 28px; color: #fff; }
    
    /* CHAT STYLES */
    .stChatMessage { background-color: #161b22; border: 1px solid #30363d; }
    .source-badge { font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: bold; text-transform: uppercase; }
    
</style>
""", unsafe_allow_html=True)

# --- INIT BRAIN & DB ---
@st.cache_resource
def get_brain():
    return FoundryBrain()

@st.cache_resource
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASS"), port=os.getenv("DB_PORT")
    )

brain = get_brain()

# --- MARKET TICKER STRIP ---
def render_ticker():
    prices = get_metal_prices() # Returns dict
    if isinstance(prices, dict):
        cols = st.columns(len(prices))
        for i, (k, v) in enumerate(prices.items()):
            cols[i].markdown(f"<div style='text-align:center; color:#ffbf00; font-family:Share Tech Mono;'>{k}<br><span style='color:white'>${v}</span></div>", unsafe_allow_html=True)
    st.markdown("---")

# --- PIPELINE CONFIG ---
PIPELINES = [
    {"name": "01 Materials", "table": "material_master", "pk": "Material_Number"},
    {"name": "03 Melting", "table": "melting_heat_records", "pk": "Heat_Number", "crit_col": "Quality_Status", "crit_val": "REJECTED"},
    {"name": "04 Molding", "table": "molding_records", "pk": "Production_Order", "crit_col": "Quality_Check", "crit_val": "FAIL"},
    {"name": "05 Casting", "table": "casting_records", "pk": "Casting_Batch", "crit_col": "Quality_Grade", "crit_val": "C"},
    {"name": "09 Inventory", "table": "inventory_movements", "pk": "Document_Number"},
    {"name": "11 Maintenance", "table": "equipment_maintenance", "pk": "Maintenance_Order", "crit_col": "Maintenance_Type", "crit_val": "BREAKDOWN"}
]

# --- MAIN UI ---
st.markdown("## 🏭 FOUNDRY OS <span style='font-size:16px; color:#555;'>// v3.0 // ONLINE</span>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🚀 LIVE OPERATIONS", "🤖 SAHAYAK AI"])

# === TAB 1: LIVE OPS ===
with tab1:
    render_ticker()
    
    # Placeholder Grid
    grid = st.container()
    
    # Update Loop (Placeholders)
    # Note: In Streamlit, a while loop blocks other tabs. 
    # For this demo, we run it ONCE per refresh or use st.empty() logic if we want auto-refresh.
    # To keep it simple and responsive, we just render current state.
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cols = st.columns(3)
        for i, p in enumerate(PIPELINES):
            # Fetch Count
            cur.execute(f"SELECT COUNT(*) FROM {p['table']}")
            count = cur.fetchone()[0]
            
            # Fetch Last ID
            cur.execute(f"SELECT {p['pk']} FROM {p['table']} ORDER BY {p['pk']} DESC LIMIT 1")
            last_id = cur.fetchone()
            last_id = last_id[0] if last_id else "N/A"
            
            # Critical Check
            is_crit = False
            if "crit_col" in p:
                cur.execute(f"SELECT {p['crit_col']} FROM {p['table']} ORDER BY {p['pk']} DESC LIMIT 1")
                res = cur.fetchone()
                if res and res[0] == p['crit_val']:
                    is_crit = True
            
            # Render
            css = "metric-card card-crit" if is_crit else "metric-card"
            with cols[i % 3]:
                st.markdown(f"""
                <div class="{css}">
                    <div class="mono-text">{p['name']}</div>
                    <div class="big-num">{count:,}</div>
                    <div class="mono-text" style="text-align:right;">ID: {last_id}</div>
                </div>
                """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"DB Connection Error: {e}")

# === TAB 2: SAHAYAK AI ===
with tab2:
    col_hist, col_chat = st.columns([1, 3])
    
    # Init History
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    with col_hist:
        st.markdown("### 🧠 MEMORY")
        if st.button("Clear History"):
            st.session_state.messages = []
            st.rerun()
        
        st.markdown(f"**Context Entries:** {len(st.session_state.messages)}")
        st.caption("Session persistent.")

    with col_chat:
        st.markdown("### 💬 CONTEXTUAL INTERFACE")
        
        # Display History
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"], unsafe_allow_html=True)
        
        # Input
        if prompt := st.chat_input("Ask about Inventory, SOPs, or Market Prices..."):
            # User Msg
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # AI Msg
            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    answer, src, intent = brain.ask(prompt)
                    
                    # Source Badge Color
                    colors = {"DATABASE": "#00ff00", "KNOWLEDGE": "#00ccff", "EXTERNAL": "#ffa500", "ERROR": "#ff0000"}
                    color = colors.get(intent, "#888")
                    
                    final_html = f"""
                    <div>
                        <span class="source-badge" style="border:1px solid {color}; color:{color}">{intent}</span>
                        <span class="source-badge" style="color:#888">SRC: {src}</span>
                        <br><br>
                        {answer}
                    </div>
                    """
                    st.markdown(final_html, unsafe_allow_html=True)
                    st.session_state.messages.append({"role": "assistant", "content": final_html})