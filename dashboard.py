import streamlit as st
import psycopg2
import os
import time
import requests
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

def _safe_scalar(cursor, query, default=0.0):
    try:
        cursor.execute(query)
        row = cursor.fetchone()
        if not row or row[0] is None:
            return default
        return float(row[0])
    except:
        return default

@st.cache_data(ttl=45)
def get_metal_price_usd(metal_name):
    try:
        api_key = os.getenv("METAL_PRICE")
        if not api_key:
            return None

        url = f"https://api.metals.live/v1/spot/metals?api_key={api_key}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "metals" in data and isinstance(data["metals"], dict):
            for key, value in data["metals"].items():
                if metal_name.lower() in str(key).lower():
                    if isinstance(value, dict):
                        price = value.get("price")
                    else:
                        price = value
                    return float(price) if price is not None else None

        if isinstance(data, dict) and metal_name in data:
            value = data[metal_name]
            if isinstance(value, dict):
                value = value.get("price")
            return float(value) if value is not None else None

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if metal_name.lower() in str(key).lower():
                            return float(value)
        return None
    except:
        return None

def get_kpi_snapshot(conn):
    kpi = {
        "yield_24h": 0.0,
        "scrap_pct": 0.0,
        "energy_kwh_ton": 0.0,
        "avg_pour_temp": 0.0,
        "good_castings_today": 0.0,
        "profit_margin": 0.0,
        "metal_price": None,
    }

    try:
        cursor = conn.cursor()

        kpi["yield_24h"] = _safe_scalar(
            cursor,
            'SELECT COALESCE(AVG("Yield_Percentage"), 0) FROM casting_records WHERE "Casting_Date" >= NOW() - INTERVAL \'24 hours\''
        )

        kpi["scrap_pct"] = _safe_scalar(
            cursor,
            'SELECT COALESCE(SUM("Scrap_Castings") * 100.0 / NULLIF(SUM("Expected_Castings"), 0), 0) FROM casting_records WHERE "Casting_Date" >= NOW() - INTERVAL \'24 hours\''
        )

        kpi["energy_kwh_ton"] = _safe_scalar(
            cursor,
            'SELECT COALESCE(SUM("Energy_Consumed_KWH") / NULLIF(SUM("Charge_Weight_KG") / 1000.0, 0), 0) FROM melting_heat_records WHERE "Melt_Date"::timestamp >= NOW() - INTERVAL \'24 hours\''
        )

        kpi["avg_pour_temp"] = _safe_scalar(
            cursor,
            'SELECT COALESCE(AVG("Pouring_Temperature_C"), 0) FROM casting_records WHERE "Casting_Date" >= NOW() - INTERVAL \'24 hours\''
        )

        kpi["good_castings_today"] = _safe_scalar(
            cursor,
            'SELECT COALESCE(SUM("Good_Castings"), 0) FROM casting_records WHERE DATE("Casting_Date") = CURRENT_DATE'
        )

        total_qty_24h = _safe_scalar(
            cursor,
            'SELECT COALESCE(SUM("Order_Quantity"), 0) FROM production_orders WHERE "Created_Date" >= CURRENT_DATE - INTERVAL \'1 day\''
        )
        total_cost_24h = _safe_scalar(
            cursor,
            'SELECT COALESCE(SUM("Actual_Costs_USD"), 0) FROM production_orders WHERE "Created_Date" >= CURRENT_DATE - INTERVAL \'1 day\''
        )

        kpi_metal = os.getenv("KPI_METAL", "copper").lower()
        metal_price = get_metal_price_usd(kpi_metal)
        kpi["metal_price"] = metal_price

        selling_multiplier = float(os.getenv("KPI_SELLING_MULTIPLIER", "1.35"))
        if metal_price and total_qty_24h > 0:
            estimated_revenue = total_qty_24h * metal_price * selling_multiplier
            if estimated_revenue > 0:
                kpi["profit_margin"] = ((estimated_revenue - total_cost_24h) / estimated_revenue) * 100.0

    except:
        pass

    return kpi

def _kpi_state(value, good_cond, warn_cond=None):
    if good_cond(value):
        return "🟢"
    if warn_cond and warn_cond(value):
        return "🟡"
    return "🔴"

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
        kpi_state = get_kpi_snapshot(conn)
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

            st.markdown("---")
            st.markdown("### 📈 KPI Snapshot (Separate Section)")

            yield_state = _kpi_state(kpi_state["yield_24h"], lambda v: v > 88, lambda v: 82 <= v <= 88)
            scrap_state = _kpi_state(kpi_state["scrap_pct"], lambda v: v < 6, lambda v: 6 <= v <= 10)
            energy_state = _kpi_state(kpi_state["energy_kwh_ton"], lambda v: v < 420, lambda v: 420 <= v <= 520)
            temp_state = _kpi_state(kpi_state["avg_pour_temp"], lambda v: 1380 <= v <= 1450, lambda v: (1360 <= v < 1380) or (1450 < v <= 1470))
            good_state = _kpi_state(kpi_state["good_castings_today"], lambda v: v > 120, lambda v: 80 <= v <= 120)
            margin_state = _kpi_state(kpi_state["profit_margin"], lambda v: v > 15, lambda v: 8 <= v <= 15)

            k1, k2, k3 = st.columns(3)
            k1.metric(f"{yield_state} Current Yield % (24h)", f"{kpi_state['yield_24h']:.2f}%")
            k2.metric(f"{scrap_state} Scrap % (24h)", f"{kpi_state['scrap_pct']:.2f}%")
            k3.metric(f"{energy_state} Energy kWh/ton (24h)", f"{kpi_state['energy_kwh_ton']:.2f}")

            k4, k5, k6 = st.columns(3)
            k4.metric(f"{temp_state} Avg Pour Temperature (24h)", f"{kpi_state['avg_pour_temp']:.1f} °C")
            k5.metric(f"{good_state} Good Castings Today", f"{int(kpi_state['good_castings_today'])}")
            k6.metric(f"{margin_state} Profit Margin (Metal API)", f"{kpi_state['profit_margin']:.2f}%")

            if kpi_state["metal_price"]:
                st.caption(f"Metal Price Source: API | Metal: {os.getenv('KPI_METAL', 'copper').upper()} | Price: ${kpi_state['metal_price']:.4f}")
            else:
                st.caption("Metal Price Source: API unavailable (METAL_PRICE key missing/unreachable); Profit Margin may show 0.00%.")

            st.caption("More KPI ideas: OEE, furnace utilization %, downtime minutes/shift, defect ppm, on-time production orders.")

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