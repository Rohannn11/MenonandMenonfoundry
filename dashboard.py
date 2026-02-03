import streamlit as st
import psycopg2
import pandas as pd
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="Factory Command Center",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. THEME & STYLING ---
st.markdown("""
    <style>
    /* Global Background & Text */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Metrics Styling */
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #00FF00;
        font-family: 'Courier New', monospace;
    }
    
    /* Custom Card */
    .pipeline-card {
        background-color: #1a1c24;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.5);
        transition: transform 0.1s;
    }
    .pipeline-card:hover {
        border-color: #00FF00;
    }
    
    /* Status Dots */
    .status-dot {
        height: 12px;
        width: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }
    .active { background-color: #00FF00; box-shadow: 0 0 8px #00FF00; }
    .idle { background-color: #555; }
    .crit { background-color: #FF0044; box-shadow: 0 0 8px #FF0044; }

    /* Code/Data Text in Card */
    .data-text {
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 11px;
        color: #A0A0A0;
        background-color: #111;
        padding: 8px;
        border-radius: 4px;
        margin-top: 8px;
        white-space: pre-wrap;
    }

    /* --- ENHANCED LOG SECTION STYLES --- */
    .log-wrapper {
        display: flex;
        gap: 15px;
        height: 300px;
    }
    
    .log-container {
        flex: 2;
        background-color: #111;
        border: 1px solid #333;
        border-radius: 8px;
        overflow-y: auto;
        font-family: 'Consolas', monospace;
        font-size: 12px;
        padding: 0;
    }
    
    .log-row {
        display: flex;
        padding: 8px 12px;
        border-bottom: 1px solid #222;
        align-items: center;
    }
    
    .context-panel {
        flex: 1;
        background-color: #1a1c24;
        border: 1px solid #444;
        border-radius: 8px;
        padding: 15px;
        font-family: 'Segoe UI', sans-serif;
    }
    
    .col-time { width: 90px; color: #666; }
    .col-src { width: 140px; color: #AAA; font-weight: bold; }
    .col-msg { flex: 1; color: #DDD; }
    
    .badge { padding: 2px 6px; border-radius: 3px; font-size: 10px; margin-right: 10px; min-width: 60px; text-align: center; }
    .badge-info { background: #1e3a8a; color: #60a5fa; border: 1px solid #60a5fa; }
    .badge-crit { background: #450a0a; color: #f87171; border: 1px solid #f87171; }
    .badge-sys { background: #333; color: #888; border: 1px solid #555; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Database & Config ---
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "port": os.getenv("DB_PORT")
}

PIPELINES = [
    {"name": "01 Materials", "table": "material_master", "pk": "Material_Number", "cols": ["Material_Type", "Base_Unit"], "status_col": "Procurement_Type", "crit_vals": []},
    {"name": "02 BOMs", "table": "bill_of_materials", "pk": "BOM_Number", "cols": ["Parent_Material", "Component_Type"], "status_col": "BOM_Status", "crit_vals": ["INACTIVE"]},
    {"name": "03 Melting", "table": "melting_heat_records", "pk": "Heat_Number", "cols": ["Target_Alloy", "Tap_Temperature_C"], "status_col": "Quality_Status", "crit_vals": ["REJECTED"]},
    {"name": "04 Molding", "table": "molding_records", "pk": "Production_Order", "cols": ["Molding_Type", "Defect_Type"], "status_col": "Quality_Check", "crit_vals": ["FAIL"]},
    {"name": "05 Casting", "table": "casting_records", "pk": "Casting_Batch", "cols": ["Product_Type", "Quality_Grade"], "status_col": "Quality_Grade", "crit_vals": ["SCRAP"]},
    {"name": "06 Heat Treat", "table": "heat_treatments", "pk": "HT_Batch_Number", "cols": ["Treatment_Type", "Quality_Status"], "status_col": "Quality_Status", "crit_vals": ["REJECTED"]},
    {"name": "07 Machining", "table": "machining_operations", "pk": "Operation_ID", "cols": ["Machine_Type", "Quality_Status"], "status_col": "Quality_Status", "crit_vals": ["FAIL"]},
    {"name": "08 Quality QC", "table": "quality_inspections", "pk": "Inspection_Lot", "cols": ["Defect_Count", "Overall_Decision"], "status_col": "Overall_Decision", "crit_vals": ["REJECT"]},
    {"name": "09 Inventory", "table": "inventory_movements", "pk": "Document_Number", "cols": ["Movement_Type", "Quantity"], "status_col": "Movement_Type", "crit_vals": ["SCRAP"]},
    {"name": "10 Production", "table": "production_orders", "pk": "Production_Order", "cols": ["Order_Status", "Planned_Costs_USD"], "status_col": "Order_Status", "crit_vals": ["CLOSED"]},
    {"name": "11 Maintenance", "table": "equipment_maintenance", "pk": "Maintenance_Order", "cols": ["Equipment_Type", "Status"], "status_col": "Maintenance_Type", "crit_vals": ["BREAKDOWN"]},
]

@st.cache_resource
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def fetch_system_state(conn):
    state = {}
    try:
        cursor = conn.cursor()
        total_rows = 0
        for p in PIPELINES:
            cursor.execute(f"SELECT COUNT(*) FROM {p['table']}")
            count = cursor.fetchone()[0]
            total_rows += count
            
            cols = ", ".join([p['pk']] + p['cols'] + ([p['status_col']] if p['status_col'] not in p['cols'] else []))
            cursor.execute(f"SELECT {cols} FROM {p['table']} ORDER BY {p['pk']} DESC LIMIT 1")
            last_row = cursor.fetchone()
            
            keys = [p['pk']] + p['cols'] + ([p['status_col']] if p['status_col'] not in p['cols'] else [])
            
            state[p['name']] = {
                "count": count,
                "data": last_row,
                "keys": keys,
                "status_check": (p['status_col'], p['crit_vals'])
            }
        return state, total_rows
    except Exception:
        return None, 0

# --- Helper: Log Logic with "Explain" ---
def generate_explanation(source, msg, level):
    if level == "CRITICAL":
        if "REJECTED" in msg: return f"QC Failure: Material from {source} failed analysis and must be scrapped."
        if "FAIL" in msg: return f"Process Defect: {source} detected a critical flaw. Rework or scrap required."
        if "SCRAP" in msg: return f"Write-off: {source} generated scrap material. Cost impact likely."
        return f"Critical alert from {source}. Check physical equipment."
    elif level == "INFO":
        if "SYSTEM" in source: return "Normal Operation: Ingestion pipeline running smoothly."
        return "Standard event recorded."
    return "Log entry."

def add_log(logs, source, level, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    explanation = generate_explanation(source, msg, level)
    new_entry = {"ts": ts, "src": source, "lvl": level, "msg": msg, "explain": explanation}
    if not logs or logs[0]["msg"] != msg:
        logs.insert(0, new_entry)
    return logs[:50]

# --- 4. Main Execution ---

st.title("🏭 Factory Command Center")

# --- TAB SETUP ---
tab_live, tab_chat = st.tabs(["🚀 Live Operations", "🤖 Sahayak AI"])

# ==========================================
# TAB 1: LIVE DASHBOARD
# ==========================================
with tab_live:
    # Top Metrics
    col1, col2, col3 = st.columns(3)
    metric_total = col1.empty()
    metric_velocity = col2.empty()
    metric_status = col3.empty()

    # The Live Grid
    grid_placeholder = st.empty()

    # The Enhanced Log Section
    st.markdown("### 📋 Event Logs & Diagnostics")
    log_layout_placeholder = st.empty()

# ==========================================
# TAB 2: SAHAYAK AI
# ==========================================
with tab_chat:
    col_input, col_res = st.columns([1, 2])
    
    with col_input:
        st.markdown("### 💬 Ask Sahayak")
        st.caption("Capabilities: Live SQL Data, Technical SOPs, Market Prices, Weather, News.")
        
        lang_mode = st.toggle("Marathi Mode (मराठी)", value=False)
        target_lang = "Marathi" if lang_mode else "English"
        
        query = st.text_area("Question / प्रश्न:", height=100, placeholder="e.g., 'Latest steel news?' or 'Furnace temperature SOP?'")
        ask_btn = st.button("🚀 Send Query", use_container_width=True)
    
    with col_res:
        st.markdown("### 💡 AI Analysis")
        
        # Placeholder for AI Response
        ai_response_container = st.empty()

        if ask_btn and query:
            # Lazy Import to avoid startup lag
            from foundry_brain import FoundrySahayak
            
            # Initialize Bot in Session State
            if "ai_bot" not in st.session_state:
                st.session_state["ai_bot"] = FoundrySahayak()
            
            with st.spinner(f"Consulting Neural Engine ({target_lang})..."):
                answer, source, intent = st.session_state["ai_bot"].ask(query, target_lang)
                
                # Dynamic Styling based on Intent
                colors = {"DATABASE": "#00FF00", "KNOWLEDGE": "#00CCFF", "EXTERNAL": "#FFA500"}
                badge_color = colors.get(intent, "#888")
                
                ai_response_container.markdown(f"""
                <div style="background:#1a1a1a; padding:20px; border-radius:10px; border-left: 5px solid {badge_color}; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <div style="margin-bottom:15px; display:flex; align-items:center;">
                        <span style="background:{badge_color}33; color:{badge_color}; padding:4px 10px; border-radius:4px; font-weight:bold; font-size:12px; border:1px solid {badge_color}; letter-spacing: 1px;">{intent}</span>
                        <span style="color:#888; font-size:12px; margin-left:15px; font-family: monospace;">SOURCE: {source}</span>
                    </div>
                    <div style="font-size:16px; line-height:1.6; color:#EEE; font-family: 'Segoe UI', sans-serif;">
                        {answer}
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ==========================================
# MAIN LOOP (Updates Live Ops)
# ==========================================

# Session State for Logs & Velocity
if "prev_total" not in st.session_state:
    st.session_state["prev_total"] = 0
if "logs" not in st.session_state:
    st.session_state["logs"] = []

while True:
    # Only update Live Ops if that tab is active (Streamlit doesn't natively support checking active tab easily, 
    # so we run the background logic but only render to placeholders)
    
    conn = get_connection()
    current_state, total_rows = fetch_system_state(conn)
    
    if current_state:
        # 1. Metrics Logic
        prev_total = st.session_state["prev_total"]
        velocity = total_rows - prev_total
        st.session_state["prev_total"] = total_rows
        
        metric_total.metric("Total Records", f"{total_rows:,}")
        metric_velocity.metric("Current Velocity", f"{velocity} rows/sec")
        
        if velocity > 0:
            metric_status.success("🟢 SYSTEM ONLINE")
        else:
            metric_status.info("⚪ SYSTEM IDLE")

        # 2. Build Grid
        with grid_placeholder.container():
            cols = st.columns(4)
            for i, p in enumerate(PIPELINES):
                name = p['name']
                info = current_state[name]
                
                count = info['count']
                row_data = info['data']
                keys = info['keys']
                status_col, crit_vals = info['status_check']
                
                pk_val = "WAITING"
                detail_text = "..."
                dot_class = "idle"
                
                if row_data:
                    data_dict = dict(zip(keys, row_data))
                    pk_val = data_dict.get(p['pk'])
                    display_dict = {k: v for k, v in data_dict.items() if k != p['pk'] and k != status_col}
                    detail_text = "\n".join([f"{k}: {v}" for k, v in display_dict.items()])
                    
                    val_check = str(data_dict.get(status_col, ""))
                    if val_check in crit_vals:
                        dot_class = "crit"
                        msg = f"{pk_val}: {status_col} = {val_check}"
                        st.session_state["logs"] = add_log(st.session_state["logs"], name, "CRITICAL", msg)
                    elif velocity > 0:
                        dot_class = "active"
                
                with cols[i % 4]:
                    st.markdown(f"""
                    <div class="pipeline-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:bold; color:#EEE;">{name}</span>
                            <span class="status-dot {dot_class}"></span>
                        </div>
                        <h2 style="margin:5px 0; color:#FFF;">{count:,}</h2>
                        <div class="data-text"><strong>{pk_val}</strong><br>{detail_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # 3. Add Heartbeat Log
        if velocity > 0:
            st.session_state["logs"] = add_log(st.session_state["logs"], "SYSTEM", "INFO", f"Ingested {velocity} new records.")

        # 4. Render Split Log View
        latest_log = st.session_state["logs"][0] if st.session_state["logs"] else {"src": "N/A", "msg": "No events yet.", "explain": "Waiting for system activity..."}
        
        log_rows_html = ""
        for log in st.session_state["logs"]:
            lvl = log['lvl']
            badge_cls = "badge-crit" if lvl == "CRITICAL" else "badge-info" if lvl == "INFO" else "badge-sys"
            log_rows_html += f"""
            <div class="log-row">
                <div class="col-time">{log['ts']}</div>
                <div class="col-src"><span class="badge {badge_cls}">{lvl}</span> {log['src']}</div>
                <div class="col-msg">{log['msg']}</div>
            </div>
            """
            
        full_html = f"""
        <div class="log-wrapper">
            <div class="log-container">{log_rows_html}</div>
            <div class="context-panel">
                <div style="color:#888; font-size:10px; margin-bottom:5px;">LATEST EVENT ANALYSIS</div>
                <div style="color:#fff; font-weight:bold; margin-bottom:10px; border-left:3px solid #00FF00; padding-left:10px;">{latest_log['src']}: {latest_log['msg']}</div>
                <div style="color:#ccc; font-size:13px; line-height:1.5;">{latest_log['explain']}</div>
            </div>
        </div>
        """
        log_layout_placeholder.markdown(full_html, unsafe_allow_html=True)

    time.sleep(1)