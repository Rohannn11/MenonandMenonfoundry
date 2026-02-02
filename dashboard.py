import streamlit as st
import psycopg2
import pandas as pd
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# --- Page Config ---
st.set_page_config(
    page_title="Factory Simulation Live",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS Styling for "Code-like" Terminal Look ---
st.markdown("""
    <style>
    .stMetric {
        background-color: #0E1117;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #303030;
    }
    .metric-card {
        background-color: #1e1e1e;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 5px solid #00FF00;
        font-family: 'Courier New', monospace;
    }
    .status-badge {
        font-size: 12px;
        font-weight: bold;
        padding: 2px 6px;
        border-radius: 4px;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Load Database ---
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "port": os.getenv("DB_PORT")
}

# --- Pipeline Configuration ---
# Map display names to SQL table names and Primary Keys
PIPELINES = [
    {"name": "01 Material Master", "table": "material_master", "pk": "Material_Number", "cols": ["Description", "Material_Type", "Net_Weight_KG"]},
    {"name": "02 Bill of Materials", "table": "bill_of_materials", "pk": "BOM_Number", "cols": ["Parent_Material", "Component_Type", "Component_Quantity"]},
    {"name": "03 Melting Heat", "table": "melting_heat_records", "pk": "Heat_Number", "cols": ["Target_Alloy", "Tap_Temperature_C", "Quality_Status"]},
    {"name": "04 Molding Records", "table": "molding_records", "pk": "Production_Order", "cols": ["Molding_Type", "Sand_Type", "Quality_Check"]},
    {"name": "05 Casting Records", "table": "casting_records", "pk": "Casting_Batch", "cols": ["Product_Type", "Pouring_Temperature_C", "Quality_Grade"]},
    {"name": "06 Heat Treatment", "table": "heat_treatments", "pk": "HT_Batch_Number", "cols": ["Treatment_Type", "Actual_Temperature_C", "Cooling_Method"]},
    {"name": "07 Machining Ops", "table": "machining_operations", "pk": "Operation_ID", "cols": ["Machine_Type", "Operation_Type", "Quality_Status"]},
    {"name": "08 Quality QC", "table": "quality_inspections", "pk": "Inspection_Lot", "cols": ["Inspection_Stage", "Defect_Count", "Overall_Decision"]},
    {"name": "09 Inventory", "table": "inventory_movements", "pk": "Document_Number", "cols": ["Movement_Type", "Quantity", "Material_Number"]},
    {"name": "10 Production", "table": "production_orders", "pk": "Production_Order", "cols": ["Order_Status", "Planned_Costs_USD", "Product_Type"]},
    {"name": "11 Maintenance", "table": "equipment_maintenance", "pk": "Maintenance_Order", "cols": ["Equipment_Type", "Maintenance_Type", "Status"]},
]

@st.cache_resource
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def fetch_live_data(conn):
    data = {}
    try:
        cursor = conn.cursor()
        for p in PIPELINES:
            # Get total count and the very last row inserted
            # We select specific columns to keep the display clean
            cols_to_fetch = ", ".join([p['pk']] + p['cols'])
            query = f"""
                SELECT {cols_to_fetch} 
                FROM {p['table']} 
                ORDER BY {p['pk']} DESC 
                LIMIT 1;
            """
            cursor.execute(query)
            last_row = cursor.fetchone()

            # Get Count separately to ensure accuracy
            cursor.execute(f"SELECT COUNT(*) FROM {p['table']}")
            count = cursor.fetchone()[0]

            data[p['name']] = {
                "count": count,
                "last_data": last_row, # Tuple of (PK, Col1, Col2, Col3)
                "columns": [p['pk']] + p['cols']
            }
        return data
    except Exception as e:
        st.error(f"DB Error: {e}")
        return None

# --- Main Dashboard ---
st.title("🏭 Factory Simulation: Live Executor View")
st.markdown("Running `executor.py` triggers these pipelines. This view refreshes every **1 second**.")

# Containers for layout
top_row = st.container()
grid_row = st.container()

# Initialize Session State for 'Delta' (Velocity calculation)
if "prev_counts" not in st.session_state:
    st.session_state["prev_counts"] = {p['name']: 0 for p in PIPELINES}

# Auto-Refresh Logic
placeholder = st.empty()

while True:
    try:
        conn = get_connection()
        live_data = fetch_live_data(conn)
        
        with placeholder.container():
            # Create a 3-column grid for the 11 pipelines
            cols = st.columns(3)
            
            for i, p in enumerate(PIPELINES):
                name = p['name']
                stats = live_data.get(name)
                
                if stats:
                    current_count = stats['count']
                    prev_count = st.session_state["prev_counts"].get(name, 0)
                    delta = current_count - prev_count
                    
                    # Status Indicator
                    is_active = delta > 0
                    status_color = "#00FF00" if is_active else "#555"
                    border_style = f"2px solid {status_color}"
                    
                    # Formatting the last record data
                    last_record = stats['last_data']
                    if last_record:
                        # Create a dictionary of Col Name -> Value
                        record_dict = dict(zip(stats['columns'], last_record))
                        pk_val = record_dict.pop(p['pk']) # Extract PK to show separately
                        details = "\n".join([f"{k}: {v}" for k,v in record_dict.items()])
                    else:
                        pk_val = "WAITING..."
                        details = "No data yet"

                    # Display in Grid Column
                    col_index = i % 3
                    with cols[col_index]:
                        st.markdown(f"""
                        <div style="background-color: #262730; padding: 15px; border-radius: 10px; border-left: {border_style}; margin-bottom: 20px;">
                            <h4 style="margin:0; color: white;">{name}</h4>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                                <span style="font-size: 24px; font-weight: bold; color: white;">{current_count:,}</span>
                                <span style="color: {status_color}; font-weight: bold;">{f'+{delta} new' if delta > 0 else 'Idle'}</span>
                            </div>
                            <div style="background-color: #0E1117; padding: 8px; margin-top: 10px; border-radius: 5px; font-family: monospace; font-size: 12px; color: #00FF00;">
                                <strong>ID: {pk_val}</strong><br>
                                <span style="color: #cccccc;">{details}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            
            # Update Session State
            st.session_state["prev_counts"] = {p['name']: live_data[p['name']]['count'] for p in PIPELINES}

        time.sleep(1) # Refresh Rate
        
    except Exception as e:
        st.error(f"Connection Lost: {e}")
        time.sleep(5)