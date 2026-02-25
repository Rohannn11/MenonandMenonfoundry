import streamlit as st
import psycopg2
import os
import time
import requests
from datetime import datetime, date, timedelta
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
        color: #eaeaea;
    }

    /* Bright, readable text on dark background (avoid forcing ALL divs) */
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF !important;
    }
    .stMarkdown, .stMarkdown p, .stMarkdown span {
        color: #eaeaea !important;
    }
    label, [data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] {
        color: #FFFFFF !important;
    }
    
    /* Captions remain subtle but visible */
    .stCaption, [data-testid="stCaption"] {
        color: #a0a0a0 !important;
    }

    /* === TAB STYLING === */
    .stTabs [data-baseweb="tab-list"] {
        gap: 16px;
        background-color: #1f2833;
        padding: 10px 20px;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #BBBBBB !important;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        color: #66fcf1 !important;
        border-bottom-color: #66fcf1 !important;
    }

    /* === SUB-TAB (within SCADA) === */
    .sub-tab-row {
        display: flex;
        gap: 8px;
        margin-bottom: 10px;
    }

    /* === SCADA CARD STYLES (TAB 1) === */
    div[data-testid="stMetricValue"] {
        font-family: 'Consolas', monospace;
        color: #66fcf1 !important;
    }

    /* Inputs: dark background + bright text */
    .stTextInput input, .stDateInput input {
        background-color: #1f2833 !important;
        color: #FFFFFF !important;
        border: 1px solid #45a29e !important;
    }
    .stTextInput input::placeholder, .stDateInput input::placeholder {
        color: #9aa0a6 !important;
    }

    /* Selects */
    [data-baseweb="select"] > div {
        background-color: #1f2833 !important;
        border: 1px solid #45a29e !important;
    }
    [data-baseweb="select"] span, [data-baseweb="select"] div {
        color: #FFFFFF !important;
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
    
    .card-title { font-size: 14px; font-weight: bold; color: #FFFFFF; text-transform: uppercase; }
    .card-value { font-size: 24px; font-family: 'Consolas', monospace; color: #66fcf1; font-weight: bold; }
    .data-row { font-family: 'Courier New', monospace; font-size: 11px; color: #DDDDDD; margin-top: 5px; border-top: 1px solid #444; padding-top: 5px; }
    .highlight-val { color: #FFFFFF; font-weight: bold; }
    
    .console-box { 
        background-color: #0d0d0d; color: #00FF00; 
        font-family: 'Courier New', monospace; 
        padding: 10px; height: 200px; 
        overflow-y: scroll; border: 1px solid #333; 
        font-size: 12px; 
    }

    /* DataFrame: keep contrast reasonable (Streamlit may override parts) */
    [data-testid="stDataFrame"] {
        background-color: #1f2833 !important;
        border: 1px solid #333 !important;
    }

    /* === CHATBOT THEME (TAB 2) - Light Purple & Black === */
    /* User Message */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #E0E0E0 !important;
        border: 1px solid #ccc;
        color: #000000 !important;
    }
    /* Assistant Message */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #E6E6FA !important;
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
    {"name": "01 MATERIALS", "table": "material_master", "pk": "material_number", "cols": ["material_type", "base_unit", "procurement_type"], "status_col": "procurement_type", "crit_vals": []},
    {"name": "02 BOMs", "table": "bill_of_materials", "pk": "bom_number", "cols": ["parent_material", "component_type", "bom_status"], "status_col": "bom_status", "crit_vals": ["INACTIVE", "PENDING"]},
    {"name": "03 MELTING", "table": "melting_heat_records", "pk": "heat_number", "cols": ["target_alloy", "tap_temperature_c", "quality_status"], "status_col": "quality_status", "crit_vals": ["REJECTED"]},
    {"name": "04 MOLDING", "table": "molding_records", "pk": "production_order", "cols": ["molding_type", "defect_type", "quality_check"], "status_col": "quality_check", "crit_vals": ["FAIL", "REWORK"]},
    {"name": "05 CASTING", "table": "casting_records", "pk": "casting_batch", "cols": ["product_type", "defects_detected", "quality_grade"], "status_col": "quality_grade", "crit_vals": ["SCRAP", "C"]},
    {"name": "06 HEAT TREAT", "table": "heat_treatment", "pk": "ht_batch_number", "cols": ["treatment_type", "rejection_reason", "quality_status"], "status_col": "quality_status", "crit_vals": ["REJECTED", "REWORK"]},
    {"name": "07 MACHINING", "table": "machining_operations", "pk": "operation_id", "cols": ["machine_type", "defect_type", "quality_status"], "status_col": "quality_status", "crit_vals": ["FAIL", "REWORK"]},
    {"name": "08 QUALITY QC", "table": "quality_inspections", "pk": "inspection_lot", "cols": ["inspection_stage", "defect_count", "overall_decision"], "status_col": "overall_decision", "crit_vals": ["REJECT", "CONDITIONAL"]},
    {"name": "09 INVENTORY", "table": "inventory_movements", "pk": "document_number", "cols": ["movement_type", "quantity", "material_number"], "status_col": "movement_type", "crit_vals": ["SCRAP", "RETURN"]},
    {"name": "10 PRODUCTION", "table": "production_orders", "pk": "production_order", "cols": ["order_status", "priority", "product_type"], "status_col": "order_status", "crit_vals": ["CLOSED"]},
    {"name": "11 MAINTENANCE", "table": "equipment_maintenance", "pk": "maintenance_order", "cols": ["equipment_type", "maintenance_type", "status"], "status_col": "maintenance_type", "crit_vals": ["BREAKDOWN", "CORRECTIVE"]},
]

TABLE_FALLBACKS = {
    "heat_treatment": ["heat_treatment", "heat_treatments"]
}

KPI_BASELINES = {
    "yield_24h": 86.5,
    "scrap_pct": 6.8,
    "energy_kwh_ton": 455.0,
    "avg_pour_temp": 1410.0,
    "good_castings_today": 120.0,
    "profit_margin": 12.0,
    "melt_approval_pct": 93.5,
    "active_orders": 45.0,
    "inventory_issue_qty_24h": 1800.0,
    "rejection_rate": 4.5,
    "breakdown_events_7d": 3.0,
}

CONTROL_TOWER_BASELINES = {
    "wip_orders": 42,
    "delayed_orders": 6,
    "completed_today": 12,
    "bottleneck_stage": "IN_PROCESS",
    "bottleneck_load": 24,
    "stage_mix": {
        "CREATED": 12,
        "RELEASED": 8,
        "IN_PROCESS": 24,
        "COMPLETED": 16,
        "CLOSED": 10,
    },
    "risk_orders": [
        {"production_order": "PO1042", "order_status": "IN_PROCESS", "planned_end_date": "2026-02-20", "order_quantity": 95, "priority": 1, "age_days": 11, "delay_days": 5},
        {"production_order": "PO1043", "order_status": "RELEASED", "planned_end_date": "2026-02-21", "order_quantity": 60, "priority": 2, "age_days": 10, "delay_days": 4},
        {"production_order": "PO1044", "order_status": "CREATED", "planned_end_date": "2026-02-22", "order_quantity": 72, "priority": 2, "age_days": 9, "delay_days": 3},
    ],
}

SCHEDULING_BASELINES = {
    "due_today": 9,
    "due_next_3d": 18,
    "overdue_open": 5,
    "planned_qty_7d": 860,
    "high_priority_open": 7,
    "capacity_utilization_pct": 74.0,
    "queue": [
        {"production_order": "PO1051", "planned_start_date": "2026-02-25", "planned_end_date": "2026-02-28", "order_status": "RELEASED", "priority": 1, "order_quantity": 110, "slack_days": 0},
        {"production_order": "PO1052", "planned_start_date": "2026-02-25", "planned_end_date": "2026-03-01", "order_status": "IN_PROCESS", "priority": 1, "order_quantity": 95, "slack_days": 1},
        {"production_order": "PO1053", "planned_start_date": "2026-02-26", "planned_end_date": "2026-03-02", "order_status": "CREATED", "priority": 2, "order_quantity": 80, "slack_days": 2},
    ],
}

INVENTORY_REORDER_BASELINES = {
    "reorder_items": 6,
    "critical_items": 2,
    "total_candidates": 12,
    "use_reference": False,
    "reorder_list": [
        {
            "material_number": "MAT-1001",
            "material_type": "RAW",
            "base_unit": "KG",
            "plant": "P01",
            "current_stock": 120.0,
            "safety_stock": 250,
            "lead_time_days": 14,
            "issued_30d": 900.0,
            "avg_daily_issue": 30.0,
            "suggested_reorder_qty": 550.0,
        },
        {
            "material_number": "MAT-2002",
            "material_type": "CONSUMABLE",
            "base_unit": "EA",
            "plant": "P01",
            "current_stock": 8.0,
            "safety_stock": 20,
            "lead_time_days": 10,
            "issued_30d": 45.0,
            "avg_daily_issue": 1.5,
            "suggested_reorder_qty": 27.0,
        },
    ],
}

TRACEABILITY_BASELINES = {
    "coverage_pct": 78.0,
    "linked_orders": 9,
    "missing_links": 3,
    "quality_holds": 2,
    "chains": [
        {
            "production_order": "PO1051",
            "heat_number": "HT00921",
            "casting_batch": "CB00432",
            "ht_batch_number": "HTB00311",
            "operation_id": "OP00871",
            "inspection_lot": "IL00455",
            "order_status": "IN_PROCESS",
            "machining_status": "PASS",
            "qc_decision": "ACCEPT",
            "chain_state": "COMPLETE",
        },
        {
            "production_order": "PO1052",
            "heat_number": "HT00922",
            "casting_batch": "CB00433",
            "ht_batch_number": "-",
            "operation_id": "OP00872",
            "inspection_lot": "-",
            "order_status": "RELEASED",
            "machining_status": "PENDING",
            "qc_decision": "PENDING",
            "chain_state": "MISSING_LINKS",
        },
    ],
}

MAINTENANCE_BASELINES = {
    "overdue_pm": 4,
    "upcoming_pm_7d": 9,
    "open_work_orders": 11,
    "breakdown_open": 2,
    "breakdown_mttr_hrs": 6.2,
    "total_downtime_7d_hrs": 41.0,
    "use_reference": False,
    "work_orders": [
        {"maintenance_order": "M10091", "equipment_type": "FURNACE", "maintenance_type": "PREVENTIVE", "status": "OPEN", "planned_start": "2026-02-25", "planned_end": "2026-02-26", "downtime_hours": 4.0, "technician_id": "T001"},
        {"maintenance_order": "M10092", "equipment_type": "CRANE", "maintenance_type": "BREAKDOWN", "status": "IN_PROCESS", "planned_start": "2026-02-24", "planned_end": "2026-02-25", "downtime_hours": 8.0, "technician_id": "T002"},
        {"maintenance_order": "M10093", "equipment_type": "LATHE", "maintenance_type": "CORRECTIVE", "status": "OPEN", "planned_start": "2026-02-26", "planned_end": "2026-02-27", "downtime_hours": 3.5, "technician_id": "T003"},
    ],
}

OTIF_BASELINES = {
    "otif_pct": 81.0,
    "on_time_pct": 85.0,
    "in_full_pct": 92.0,
    "completed_30d": 56,
    "late_30d": 11,
    "under_fill_30d": 5,
    "use_reference": False,
    "recent_completions": [
        {"production_order": "PO1045", "product_type": "ENGINE_BLOCK", "order_quantity": 100, "confirmed_quantity": 98, "planned_end_date": "2026-02-20", "actual_end_date": "2026-02-20", "on_time": True, "in_full": True},
        {"production_order": "PO1046", "product_type": "CYLINDER_HEAD", "order_quantity": 80, "confirmed_quantity": 75, "planned_end_date": "2026-02-18", "actual_end_date": "2026-02-21", "on_time": False, "in_full": True},
    ],
}

FRESHNESS_CONFIG = [
    {"label": "Melting", "table": "melting_heat_records", "time_col": "melt_date"},
    {"label": "Casting", "table": "casting_records", "time_col": "casting_date"},
    {"label": "Heat Treat", "table": "heat_treatment", "time_col": "treatment_date"},
    {"label": "Quality", "table": "quality_inspections", "time_col": "inspection_date"},
    {"label": "Inventory", "table": "inventory_movements", "time_col": "posting_date"},
    {"label": "Maintenance", "table": "equipment_maintenance", "time_col": "created_date"},
]

FRESHNESS_SLA_HOURS = {
    "Melting": (24, 48),
    "Casting": (24, 48),
    "Heat Treat": (24, 48),
    "Quality": (24, 48),
    "Inventory": (24, 48),
    "Maintenance": (48, 96),
}

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

def _safe_count(cursor, query):
    try:
        cursor.execute(query)
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except:
        return 0

def _resolve_kpi_value(cursor, value_query, presence_query, fallback_value):
    has_data = _safe_count(cursor, presence_query) > 0
    if not has_data:
        return float(fallback_value), True
    return _safe_scalar(cursor, value_query, float(fallback_value)), False

def _safe_resolve_table(cursor, preferred_table):
    table_candidates = TABLE_FALLBACKS.get(preferred_table, [preferred_table])
    for tbl in table_candidates:
        try:
            cursor.execute("SELECT to_regclass(%s)", (f"public.{tbl}",))
            found = cursor.fetchone()
            if found and found[0]:
                return tbl
        except:
            continue
    return preferred_table

def _q(identifier):
    return f'"{identifier}"'

def _safe_latest_timestamp(cursor, table_name, time_col):
    try:
        cursor.execute(f"SELECT MAX({_q(time_col)}) FROM {table_name}")
        return cursor.fetchone()[0]
    except:
        return None

def _format_ts(value):
    if not value:
        return "NO DATA"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)

def _age_hours(value):
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            ts = value
        elif isinstance(value, date):
            ts = datetime.combine(value, datetime.min.time())
        else:
            return None
        return (datetime.now() - ts).total_seconds() / 3600.0
    except:
        return None

def _freshness_state(label, age_hours):
    if age_hours is None:
        return "missing"
    green_h, warn_h = FRESHNESS_SLA_HOURS.get(label, (24, 48))
    if age_hours <= green_h:
        return "fresh"
    if age_hours <= warn_h:
        return "warn"
    return "stale"

def _freshness_icon(state):
    if state == "fresh":
        return "🟢"
    if state == "warn":
        return "🟡"
    return "🔴"

def get_freshness_snapshot(conn):
    freshness = {"fresh": 0, "total": 0, "details": []}
    try:
        cursor = conn.cursor()
        for item in FRESHNESS_CONFIG:
            table_name = _safe_resolve_table(cursor, item["table"])
            latest_ts = None
            try:
                cursor.execute(f"SELECT MAX({_q(item['time_col'])}) FROM {table_name}")
                latest_ts = cursor.fetchone()[0]
            except:
                latest_ts = None

            is_fresh = latest_ts is not None
            age_hours = _age_hours(latest_ts)
            sla_state = _freshness_state(item["label"], age_hours)
            freshness["total"] += 1
            if sla_state == "fresh":
                freshness["fresh"] += 1
            freshness["details"].append(
                {
                    "label": item["label"],
                    "latest": latest_ts,
                    "is_fresh": is_fresh,
                    "age_hours": age_hours,
                    "sla_state": sla_state,
                }
            )
    except:
        pass
    return freshness

def get_trend_snapshot(conn):
    trend = {
        "yield_delta": 0.0,
        "scrap_delta": 0.0,
        "energy_delta": 0.0,
        "reject_delta": 0.0,
    }
    try:
        cursor = conn.cursor()
        current_yield = _safe_scalar(cursor, 'SELECT COALESCE(AVG("yield_pct"), 0) FROM casting_records WHERE "casting_date" >= NOW() - INTERVAL \'24 hours\'')
        previous_yield = _safe_scalar(cursor, 'SELECT COALESCE(AVG("yield_pct"), 0) FROM casting_records WHERE "casting_date" >= NOW() - INTERVAL \'48 hours\' AND "casting_date" < NOW() - INTERVAL \'24 hours\'')
        trend["yield_delta"] = current_yield - previous_yield

        current_scrap = _safe_scalar(cursor, 'SELECT COALESCE(SUM("scrap_castings") * 100.0 / NULLIF(SUM("expected_castings"), 0), 0) FROM casting_records WHERE "casting_date" >= NOW() - INTERVAL \'24 hours\'')
        previous_scrap = _safe_scalar(cursor, 'SELECT COALESCE(SUM("scrap_castings") * 100.0 / NULLIF(SUM("expected_castings"), 0), 0) FROM casting_records WHERE "casting_date" >= NOW() - INTERVAL \'48 hours\' AND "casting_date" < NOW() - INTERVAL \'24 hours\'')
        trend["scrap_delta"] = current_scrap - previous_scrap

        current_energy = _safe_scalar(cursor, 'SELECT COALESCE(SUM("energy_kwh") / NULLIF(SUM("charge_weight_kg") / 1000.0, 0), 0) FROM melting_heat_records WHERE "melt_date" >= NOW() - INTERVAL \'24 hours\'')
        previous_energy = _safe_scalar(cursor, 'SELECT COALESCE(SUM("energy_kwh") / NULLIF(SUM("charge_weight_kg") / 1000.0, 0), 0) FROM melting_heat_records WHERE "melt_date" >= NOW() - INTERVAL \'48 hours\' AND "melt_date" < NOW() - INTERVAL \'24 hours\'')
        trend["energy_delta"] = current_energy - previous_energy

        current_reject = _safe_scalar(cursor, '''
            SELECT COALESCE(
                SUM(CASE WHEN "overall_decision" = 'REJECT' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0),
                0
            )
            FROM quality_inspections
            WHERE "inspection_date" >= NOW() - INTERVAL '7 days'
        ''')
        previous_reject = _safe_scalar(cursor, '''
            SELECT COALESCE(
                SUM(CASE WHEN "overall_decision" = 'REJECT' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0),
                0
            )
            FROM quality_inspections
            WHERE "inspection_date" >= NOW() - INTERVAL '14 days'
              AND "inspection_date" < NOW() - INTERVAL '7 days'
        ''')
        trend["reject_delta"] = current_reject - previous_reject
    except:
        pass
    return trend

def get_control_tower_snapshot(conn):
    snapshot = {
        "wip_orders": 0,
        "delayed_orders": 0,
        "completed_today": 0,
        "bottleneck_stage": "IN_PROCESS",
        "bottleneck_load": 0,
        "stage_mix": {
            "CREATED": 0,
            "RELEASED": 0,
            "IN_PROCESS": 0,
            "COMPLETED": 0,
            "CLOSED": 0,
        },
        "risk_orders": [],
        "use_reference": False,
    }

    try:
        cursor = conn.cursor()
        total_orders = _safe_count(cursor, 'SELECT COUNT(*) FROM production_orders')
        if total_orders <= 0:
            snapshot.update(CONTROL_TOWER_BASELINES)
            snapshot["use_reference"] = True
            return snapshot

        snapshot["wip_orders"] = _safe_count(
            cursor,
            '''
            SELECT COUNT(*)
            FROM production_orders
            WHERE "order_status" IN ('CREATED', 'RELEASED', 'IN_PROCESS')
            '''
        )

        snapshot["delayed_orders"] = _safe_count(
            cursor,
            '''
            SELECT COUNT(*)
            FROM production_orders
            WHERE "planned_end_date" < CURRENT_DATE
              AND "order_status" NOT IN ('COMPLETED', 'CLOSED')
            '''
        )

        snapshot["completed_today"] = _safe_count(
            cursor,
            '''
            SELECT COUNT(*)
            FROM production_orders
            WHERE "actual_end_date" = CURRENT_DATE
              AND "order_status" IN ('COMPLETED', 'CLOSED')
            '''
        )

        try:
            cursor.execute(
                '''
                SELECT "order_status", COUNT(*)
                FROM production_orders
                GROUP BY "order_status"
                '''
            )
            for status, count in cursor.fetchall():
                status_key = str(status).upper() if status else ""
                if status_key in snapshot["stage_mix"]:
                    snapshot["stage_mix"][status_key] = int(count)
        except:
            pass

        bottleneck_candidates = {
            "CREATED": snapshot["stage_mix"].get("CREATED", 0),
            "RELEASED": snapshot["stage_mix"].get("RELEASED", 0),
            "IN_PROCESS": snapshot["stage_mix"].get("IN_PROCESS", 0),
        }
        snapshot["bottleneck_stage"], snapshot["bottleneck_load"] = max(
            bottleneck_candidates.items(), key=lambda item: item[1]
        )

        try:
            cursor.execute(
                '''
                SELECT
                    "production_order",
                    "order_status",
                    "planned_end_date",
                    "order_quantity",
                    "priority",
                    CASE WHEN "created_date" IS NOT NULL THEN (CURRENT_DATE - "created_date") ELSE NULL END AS age_days,
                    CASE WHEN "planned_end_date" IS NOT NULL THEN GREATEST((CURRENT_DATE - "planned_end_date"), 0) ELSE 0 END AS delay_days
                FROM production_orders
                WHERE "order_status" IN ('CREATED', 'RELEASED', 'IN_PROCESS')
                ORDER BY
                    CASE WHEN "planned_end_date" IS NOT NULL THEN (CURRENT_DATE - "planned_end_date") ELSE -99999 END DESC,
                    "priority" ASC
                LIMIT 8
                '''
            )
            rows = cursor.fetchall()
            snapshot["risk_orders"] = [
                {
                    "production_order": row[0],
                    "order_status": row[1],
                    "planned_end_date": _format_ts(row[2]),
                    "order_quantity": int(row[3]) if row[3] is not None else 0,
                    "priority": int(row[4]) if row[4] is not None else 0,
                    "age_days": int(row[5]) if row[5] is not None else 0,
                    "delay_days": int(row[6]) if row[6] is not None else 0,
                }
                for row in rows
            ]
        except:
            snapshot["risk_orders"] = []

        if not snapshot["risk_orders"]:
            snapshot["risk_orders"] = CONTROL_TOWER_BASELINES["risk_orders"]
            snapshot["use_reference"] = True
    except:
        snapshot.update(CONTROL_TOWER_BASELINES)
        snapshot["use_reference"] = True

    return snapshot

def get_scheduling_snapshot(conn):
    snapshot = {
        "due_today": 0,
        "due_next_3d": 0,
        "overdue_open": 0,
        "planned_qty_7d": 0.0,
        "high_priority_open": 0,
        "capacity_utilization_pct": 0.0,
        "queue": [],
        "use_reference": False,
    }
    try:
        cursor = conn.cursor()
        total_orders = _safe_count(cursor, 'SELECT COUNT(*) FROM production_orders')
        if total_orders <= 0:
            snapshot.update(SCHEDULING_BASELINES)
            snapshot["use_reference"] = True
            return snapshot

        snapshot["due_today"] = _safe_count(
            cursor,
            '''
            SELECT COUNT(*)
            FROM production_orders
            WHERE "planned_end_date" = CURRENT_DATE
              AND "order_status" NOT IN ('COMPLETED', 'CLOSED')
            '''
        )

        snapshot["due_next_3d"] = _safe_count(
            cursor,
            '''
            SELECT COUNT(*)
            FROM production_orders
            WHERE "planned_end_date" > CURRENT_DATE
              AND "planned_end_date" <= CURRENT_DATE + INTERVAL '3 days'
              AND "order_status" NOT IN ('COMPLETED', 'CLOSED')
            '''
        )

        snapshot["overdue_open"] = _safe_count(
            cursor,
            '''
            SELECT COUNT(*)
            FROM production_orders
            WHERE "planned_end_date" < CURRENT_DATE
              AND "order_status" NOT IN ('COMPLETED', 'CLOSED')
            '''
        )

        snapshot["planned_qty_7d"] = _safe_scalar(
            cursor,
            '''
            SELECT COALESCE(SUM("order_quantity"), 0)
            FROM production_orders
            WHERE "planned_start_date" <= CURRENT_DATE + INTERVAL '7 days'
              AND "planned_end_date" >= CURRENT_DATE
              AND "order_status" NOT IN ('COMPLETED', 'CLOSED')
            ''',
            0.0,
        )

        snapshot["high_priority_open"] = _safe_count(
            cursor,
            '''
            SELECT COUNT(*)
            FROM production_orders
            WHERE "priority" <= 2
              AND "order_status" IN ('CREATED', 'RELEASED', 'IN_PROCESS')
            '''
        )

        weekly_capacity = float(os.getenv("WEEKLY_ORDER_CAPACITY", "1200"))
        if weekly_capacity > 0:
            snapshot["capacity_utilization_pct"] = min(180.0, (snapshot["planned_qty_7d"] / weekly_capacity) * 100.0)

        try:
            cursor.execute(
                '''
                SELECT
                    "production_order",
                    "planned_start_date",
                    "planned_end_date",
                    "order_status",
                    "priority",
                    "order_quantity",
                    CASE WHEN "planned_end_date" IS NOT NULL THEN ("planned_end_date" - CURRENT_DATE) ELSE NULL END AS slack_days
                FROM production_orders
                WHERE "order_status" IN ('CREATED', 'RELEASED', 'IN_PROCESS')
                ORDER BY
                    "priority" ASC,
                    "planned_end_date" ASC,
                    "planned_start_date" ASC
                LIMIT 12
                '''
            )
            rows = cursor.fetchall()
            snapshot["queue"] = [
                {
                    "production_order": row[0],
                    "planned_start_date": _format_ts(row[1]),
                    "planned_end_date": _format_ts(row[2]),
                    "order_status": row[3],
                    "priority": int(row[4]) if row[4] is not None else 0,
                    "order_quantity": int(row[5]) if row[5] is not None else 0,
                    "slack_days": int(row[6]) if row[6] is not None else 0,
                }
                for row in rows
            ]
        except:
            snapshot["queue"] = []

        if not snapshot["queue"]:
            snapshot["queue"] = SCHEDULING_BASELINES["queue"]
            snapshot["use_reference"] = True
    except:
        snapshot.update(SCHEDULING_BASELINES)
        snapshot["use_reference"] = True

    return snapshot

def get_operational_alerts(kpi, freshness, control_tower, scheduling):
    alerts = []

    def add_alert(severity, title, detail):
        alerts.append({"severity": severity, "title": title, "detail": detail})

    if kpi.get("scrap_pct", 0) >= 10:
        add_alert("CRITICAL", "High Scrap", f"Scrap rate is {kpi['scrap_pct']:.2f}% in the last 24h.")
    elif kpi.get("scrap_pct", 0) >= 8:
        add_alert("WARN", "Scrap Rising", f"Scrap rate is {kpi['scrap_pct']:.2f}% in the last 24h.")

    if kpi.get("rejection_rate", 0) >= 8:
        add_alert("CRITICAL", "Quality Reject Risk", f"QC reject rate is {kpi['rejection_rate']:.2f}% over 7d.")
    elif kpi.get("rejection_rate", 0) >= 5:
        add_alert("WARN", "Quality Drift", f"QC reject rate is {kpi['rejection_rate']:.2f}% over 7d.")

    if kpi.get("melt_approval_pct", 100) < 90:
        add_alert("WARN", "Melt Approval Low", f"Melt approval is {kpi['melt_approval_pct']:.2f}% in 24h.")

    if control_tower.get("delayed_orders", 0) > 0:
        add_alert("WARN", "Delayed Orders", f"{control_tower['delayed_orders']} open orders are past planned end date.")

    if int(kpi.get("breakdown_events_7d", 0)) >= 6:
        add_alert("CRITICAL", "Maintenance Breakdown Spike", f"{int(kpi['breakdown_events_7d'])} breakdown events in 7d.")
    elif int(kpi.get("breakdown_events_7d", 0)) >= 4:
        add_alert("WARN", "Maintenance Watch", f"{int(kpi['breakdown_events_7d'])} breakdown events in 7d.")

    cap_util = float(scheduling.get("capacity_utilization_pct", 0.0))
    if cap_util > 100:
        add_alert("CRITICAL", "Capacity Overload", f"Planned utilization is {cap_util:.1f}% for the next 7 days.")
    elif cap_util > 85:
        add_alert("WARN", "Capacity Tight", f"Planned utilization is {cap_util:.1f}% for the next 7 days.")

    stale_streams = [d["label"] for d in freshness.get("details", []) if d.get("sla_state") == "stale"]
    missing_streams = [d["label"] for d in freshness.get("details", []) if d.get("sla_state") == "missing"]
    if stale_streams:
        add_alert("WARN", "Stale Feeds", f"Stale ingestion detected for: {', '.join(stale_streams)}.")
    if missing_streams:
        add_alert("CRITICAL", "Missing Feeds", f"No ingestion data for: {', '.join(missing_streams)}.")

    severity_rank = {"CRITICAL": 0, "WARN": 1, "INFO": 2}
    alerts.sort(key=lambda a: severity_rank.get(a["severity"], 9))
    return alerts

def get_traceability_snapshot(conn):
    snapshot = {
        "coverage_pct": 0.0,
        "linked_orders": 0,
        "missing_links": 0,
        "quality_holds": 0,
        "chains": [],
        "use_reference": False,
    }

    try:
        cursor = conn.cursor()

        cursor.execute(
            '''
            WITH latest_mach AS (
                SELECT DISTINCT ON ("production_order")
                    "production_order",
                    "operation_id",
                    "operation_date",
                    "quality_status"
                FROM machining_operations
                ORDER BY "production_order", "operation_date" DESC, "operation_id" DESC
            ),
            latest_qc AS (
                SELECT DISTINCT ON ("production_order")
                    "production_order",
                    "inspection_lot",
                    "inspection_date",
                    "overall_decision"
                FROM quality_inspections
                ORDER BY "production_order", "inspection_date" DESC, "inspection_lot" DESC
            )
            SELECT
                po."production_order",
                COALESCE(cr."heat_number", '-') AS heat_number,
                COALESCE(cr."casting_batch", '-') AS casting_batch,
                COALESCE(ht."ht_batch_number", '-') AS ht_batch_number,
                COALESCE(lm."operation_id", '-') AS operation_id,
                COALESCE(lq."inspection_lot", '-') AS inspection_lot,
                po."order_status",
                COALESCE(lm."quality_status", 'PENDING') AS machining_status,
                COALESCE(lq."overall_decision", 'PENDING') AS qc_decision
            FROM production_orders po
            LEFT JOIN casting_records cr
                ON cr."production_order" = po."production_order"
            LEFT JOIN heat_treatment ht
                ON ht."production_order" = po."production_order"
            LEFT JOIN latest_mach lm
                ON lm."production_order" = po."production_order"
            LEFT JOIN latest_qc lq
                ON lq."production_order" = po."production_order"
            ORDER BY po."created_date" DESC, po."production_order" DESC
            LIMIT 15
            '''
        )
        rows = cursor.fetchall()

        chains = []
        linked_orders = 0
        quality_holds = 0

        for row in rows:
            chain_complete = all(v not in (None, "-") for v in [row[1], row[2], row[3], row[4], row[5]])
            if chain_complete:
                linked_orders += 1

            qc_decision = str(row[8]).upper() if row[8] is not None else "PENDING"
            machining_status = str(row[7]).upper() if row[7] is not None else "PENDING"
            if qc_decision in ("REJECT", "CONDITIONAL") or machining_status in ("FAIL", "REWORK"):
                quality_holds += 1

            chains.append(
                {
                    "production_order": row[0],
                    "heat_number": row[1],
                    "casting_batch": row[2],
                    "ht_batch_number": row[3],
                    "operation_id": row[4],
                    "inspection_lot": row[5],
                    "order_status": row[6],
                    "machining_status": row[7],
                    "qc_decision": row[8],
                    "chain_state": "COMPLETE" if chain_complete else "MISSING_LINKS",
                }
            )

        total = len(chains)
        snapshot["chains"] = chains
        snapshot["linked_orders"] = linked_orders
        snapshot["missing_links"] = max(0, total - linked_orders)
        snapshot["quality_holds"] = quality_holds
        snapshot["coverage_pct"] = (linked_orders * 100.0 / total) if total > 0 else 0.0

        if total == 0:
            snapshot.update(TRACEABILITY_BASELINES)
            snapshot["use_reference"] = True
    except:
        snapshot.update(TRACEABILITY_BASELINES)
        snapshot["use_reference"] = True

    return snapshot

def get_inventory_reorder_snapshot(conn):
    snapshot = {
        "reorder_items": 0,
        "critical_items": 0,
        "total_candidates": 0,
        "use_reference": False,
        "reorder_list": [],
    }
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            WITH latest_stock AS (
                SELECT DISTINCT ON ("material_number")
                    "material_number",
                    "plant",
                    "storage_location",
                    "stock_after"::numeric AS stock_after,
                    "posting_date",
                    "document_number"
                FROM inventory_movements
                ORDER BY "material_number", "posting_date" DESC, "document_number" DESC
            ),
            issue_30d AS (
                SELECT
                    "material_number",
                    COALESCE(SUM("quantity"), 0)::numeric AS issued_30d
                FROM inventory_movements
                WHERE "posting_date" >= CURRENT_DATE - INTERVAL '30 days'
                  AND (
                        "movement_type" ILIKE 'GI%'
                     OR "movement_type" ILIKE '%ISSUE%'
                     OR "movement_type" ILIKE '%SCRAP%'
                  )
                GROUP BY "material_number"
            )
            SELECT
                mm."material_number",
                mm."material_type",
                mm."base_unit",
                mm."plant",
                COALESCE(ls.stock_after, 0) AS current_stock,
                mm."safety_stock",
                mm."lead_time_days",
                COALESCE(i.issued_30d, 0) AS issued_30d,
                (COALESCE(i.issued_30d, 0) / 30.0) AS avg_daily_issue,
                GREATEST(
                    0,
                    (mm."safety_stock" + (COALESCE(i.issued_30d, 0) / 30.0) * mm."lead_time_days") - COALESCE(ls.stock_after, 0)
                ) AS suggested_reorder_qty
            FROM material_master mm
            LEFT JOIN latest_stock ls
                ON ls."material_number" = mm."material_number"
            LEFT JOIN issue_30d i
                ON i."material_number" = mm."material_number"
            ORDER BY suggested_reorder_qty DESC, mm."material_number" ASC
            LIMIT 15
            '''
        )
        rows = cursor.fetchall()
        reorder_list = []
        reorder_items = 0
        critical_items = 0
        for r in rows:
            current_stock = float(r[4] or 0.0)
            safety_stock = int(r[5] or 0)
            suggested = float(r[9] or 0.0)
            if suggested > 0:
                reorder_items += 1
            if safety_stock > 0 and current_stock < (0.5 * safety_stock):
                critical_items += 1
            reorder_list.append(
                {
                    "material_number": r[0],
                    "material_type": r[1],
                    "base_unit": r[2],
                    "plant": r[3],
                    "current_stock": current_stock,
                    "safety_stock": safety_stock,
                    "lead_time_days": int(r[6] or 0),
                    "issued_30d": float(r[7] or 0.0),
                    "avg_daily_issue": float(r[8] or 0.0),
                    "suggested_reorder_qty": suggested,
                }
            )

        snapshot["reorder_list"] = reorder_list
        snapshot["reorder_items"] = reorder_items
        snapshot["critical_items"] = critical_items
        snapshot["total_candidates"] = len(reorder_list)

        if not reorder_list:
            snapshot.update(INVENTORY_REORDER_BASELINES)
            snapshot["use_reference"] = True
    except:
        snapshot.update(INVENTORY_REORDER_BASELINES)
        snapshot["use_reference"] = True

    return snapshot

def _init_capa_state():
    """Seed session_state keys that do not yet exist. Never mutates widget-bound keys."""
    defaults = {
        "capa_register": [],
        "capa_seq": 1,
        "capa_prev_source": None,
        "capa_prev_edit": None,
        "capa_reset_fields": False,
        "capa_issue": "",
        "capa_owner": "",
        "capa_priority": "MEDIUM",
        "capa_source": "MANUAL",
        "capa_due_date": date.today() + timedelta(days=7),
        "capa_status_update": "OPEN",
        "capa_closure_notes": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def _flush_capa_reset():
    """Apply a pending create-form reset. MUST be called before any CAPA widgets render."""
    if st.session_state.get("capa_reset_fields"):
        st.session_state["capa_reset_fields"] = False
        st.session_state["capa_issue"] = ""
        st.session_state["capa_owner"] = ""
        st.session_state["capa_priority"] = "MEDIUM"
        st.session_state["capa_source"] = "MANUAL"
        st.session_state["capa_due_date"] = date.today() + timedelta(days=7)

def _get_capa_snapshot():
    # Read only – do NOT call _init_capa_state() here; widgets may already be instantiated.
    register = st.session_state.get("capa_register", [])
    today = date.today()

    open_items = [i for i in register if i.get("status") in ("OPEN", "IN_PROGRESS", "VERIFICATION")]
    overdue_items = [
        i for i in open_items
        if i.get("due_date") and datetime.fromisoformat(i["due_date"]).date() < today
    ]
    due_7d = [
        i for i in open_items
        if i.get("due_date") and 0 <= (datetime.fromisoformat(i["due_date"]).date() - today).days <= 7
    ]

    return {
        "total": len(register),
        "open": len(open_items),
        "overdue": len(overdue_items),
        "due_7d": len(due_7d),
        "register": sorted(register, key=lambda x: (x.get("status") == "CLOSED", x.get("due_date", "9999-12-31"))),
    }

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
        "melt_approval_pct": 0.0,
        "active_orders": 0.0,
        "inventory_issue_qty_24h": 0.0,
        "rejection_rate": 0.0,
        "breakdown_events_7d": 0.0,
        "metal_price": None,
    }
    kpi_meta = {
        "fallback_keys": [],
        "metal_source": "LIVE",
        "last_success": {},
    }

    try:
        cursor = conn.cursor()

        kpi["yield_24h"], used_fallback = _resolve_kpi_value(
            cursor,
            'SELECT COALESCE(AVG("yield_pct"), 0) FROM casting_records WHERE "casting_date" >= NOW() - INTERVAL \'24 hours\'',
            'SELECT COUNT(*) FROM casting_records WHERE "casting_date" >= NOW() - INTERVAL \'24 hours\'',
            KPI_BASELINES["yield_24h"],
        )
        if used_fallback:
            kpi_meta["fallback_keys"].append("yield_24h")
        else:
            kpi_meta["last_success"]["yield_24h"] = _safe_latest_timestamp(cursor, "casting_records", "casting_date")

        kpi["scrap_pct"], used_fallback = _resolve_kpi_value(
            cursor,
            'SELECT COALESCE(SUM("scrap_castings") * 100.0 / NULLIF(SUM("expected_castings"), 0), 0) FROM casting_records WHERE "casting_date" >= NOW() - INTERVAL \'24 hours\'',
            'SELECT COUNT(*) FROM casting_records WHERE "casting_date" >= NOW() - INTERVAL \'24 hours\'',
            KPI_BASELINES["scrap_pct"],
        )
        if used_fallback:
            kpi_meta["fallback_keys"].append("scrap_pct")
        else:
            kpi_meta["last_success"]["scrap_pct"] = _safe_latest_timestamp(cursor, "casting_records", "casting_date")

        kpi["energy_kwh_ton"], used_fallback = _resolve_kpi_value(
            cursor,
            'SELECT COALESCE(SUM("energy_kwh") / NULLIF(SUM("charge_weight_kg") / 1000.0, 0), 0) FROM melting_heat_records WHERE "melt_date"::timestamp >= NOW() - INTERVAL \'24 hours\'',
            'SELECT COUNT(*) FROM melting_heat_records WHERE "melt_date"::timestamp >= NOW() - INTERVAL \'24 hours\'',
            KPI_BASELINES["energy_kwh_ton"],
        )
        if used_fallback:
            kpi_meta["fallback_keys"].append("energy_kwh_ton")
        else:
            kpi_meta["last_success"]["energy_kwh_ton"] = _safe_latest_timestamp(cursor, "melting_heat_records", "melt_date")

        kpi["avg_pour_temp"], used_fallback = _resolve_kpi_value(
            cursor,
            'SELECT COALESCE(AVG("pouring_temperature_c"), 0) FROM casting_records WHERE "casting_date" >= NOW() - INTERVAL \'24 hours\'',
            'SELECT COUNT(*) FROM casting_records WHERE "casting_date" >= NOW() - INTERVAL \'24 hours\'',
            KPI_BASELINES["avg_pour_temp"],
        )
        if used_fallback:
            kpi_meta["fallback_keys"].append("avg_pour_temp")
        else:
            kpi_meta["last_success"]["avg_pour_temp"] = _safe_latest_timestamp(cursor, "casting_records", "casting_date")

        kpi["good_castings_today"], used_fallback = _resolve_kpi_value(
            cursor,
            'SELECT COALESCE(SUM("good_castings"), 0) FROM casting_records WHERE DATE("casting_date") = CURRENT_DATE',
            'SELECT COUNT(*) FROM casting_records WHERE DATE("casting_date") = CURRENT_DATE',
            KPI_BASELINES["good_castings_today"],
        )
        if used_fallback:
            kpi_meta["fallback_keys"].append("good_castings_today")
        else:
            kpi_meta["last_success"]["good_castings_today"] = _safe_latest_timestamp(cursor, "casting_records", "casting_date")

        kpi["melt_approval_pct"], used_fallback = _resolve_kpi_value(
            cursor,
            '''
            SELECT COALESCE(
                SUM(CASE WHEN "quality_status" = 'APPROVED' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0),
                0
            )
            FROM melting_heat_records
            WHERE "melt_date"::timestamp >= NOW() - INTERVAL '24 hours'
            ''',
            'SELECT COUNT(*) FROM melting_heat_records WHERE "melt_date"::timestamp >= NOW() - INTERVAL \'24 hours\'',
            KPI_BASELINES["melt_approval_pct"],
        )
        if used_fallback:
            kpi_meta["fallback_keys"].append("melt_approval_pct")
        else:
            kpi_meta["last_success"]["melt_approval_pct"] = _safe_latest_timestamp(cursor, "melting_heat_records", "melt_date")

        kpi["active_orders"], used_fallback = _resolve_kpi_value(
            cursor,
            '''
            SELECT COALESCE(COUNT(*), 0)
            FROM production_orders
            WHERE "order_status" IN ('CREATED', 'RELEASED', 'IN_PROCESS')
            ''',
            'SELECT COUNT(*) FROM production_orders',
            KPI_BASELINES["active_orders"],
        )
        if used_fallback:
            kpi_meta["fallback_keys"].append("active_orders")
        else:
            kpi_meta["last_success"]["active_orders"] = _safe_latest_timestamp(cursor, "production_orders", "created_date")

        kpi["inventory_issue_qty_24h"], used_fallback = _resolve_kpi_value(
            cursor,
            '''
            SELECT COALESCE(SUM("quantity"), 0)
            FROM inventory_movements
            WHERE "posting_date"::timestamp >= NOW() - INTERVAL '24 hours'
              AND (
                    "movement_type" ILIKE 'GI%'
                 OR "movement_type" ILIKE '%ISSUE%'
                 OR "movement_type" ILIKE '%SCRAP%'
              )
            ''',
            'SELECT COUNT(*) FROM inventory_movements WHERE "posting_date"::timestamp >= NOW() - INTERVAL \'24 hours\'',
            KPI_BASELINES["inventory_issue_qty_24h"],
        )
        if used_fallback:
            kpi_meta["fallback_keys"].append("inventory_issue_qty_24h")
        else:
            kpi_meta["last_success"]["inventory_issue_qty_24h"] = _safe_latest_timestamp(cursor, "inventory_movements", "posting_date")

        kpi["rejection_rate"], used_fallback = _resolve_kpi_value(
            cursor,
            '''
            SELECT COALESCE(
                SUM(CASE WHEN "overall_decision" = 'REJECT' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0),
                0
            )
            FROM quality_inspections
            WHERE "inspection_date"::timestamp >= NOW() - INTERVAL '7 days'
            ''',
            'SELECT COUNT(*) FROM quality_inspections WHERE "inspection_date"::timestamp >= NOW() - INTERVAL \'7 days\'',
            KPI_BASELINES["rejection_rate"],
        )
        if used_fallback:
            kpi_meta["fallback_keys"].append("rejection_rate")
        else:
            kpi_meta["last_success"]["rejection_rate"] = _safe_latest_timestamp(cursor, "quality_inspections", "inspection_date")

        kpi["breakdown_events_7d"], used_fallback = _resolve_kpi_value(
            cursor,
            '''
            SELECT COALESCE(COUNT(*), 0)
            FROM equipment_maintenance
            WHERE "created_date"::timestamp >= NOW() - INTERVAL '7 days'
              AND "maintenance_type" = 'BREAKDOWN'
            ''',
            'SELECT COUNT(*) FROM equipment_maintenance WHERE "created_date"::timestamp >= NOW() - INTERVAL \'7 days\'',
            KPI_BASELINES["breakdown_events_7d"],
        )
        if used_fallback:
            kpi_meta["fallback_keys"].append("breakdown_events_7d")
        else:
            kpi_meta["last_success"]["breakdown_events_7d"] = _safe_latest_timestamp(cursor, "equipment_maintenance", "created_date")

        total_qty_24h, qty_fallback = _resolve_kpi_value(
            cursor,
            'SELECT COALESCE(SUM("order_quantity"), 0) FROM production_orders WHERE "created_date" >= CURRENT_DATE - INTERVAL \'1 day\'',
            'SELECT COUNT(*) FROM production_orders WHERE "created_date" >= CURRENT_DATE - INTERVAL \'1 day\'',
            0.0,
        )
        total_cost_24h, _ = _resolve_kpi_value(
            cursor,
            'SELECT COALESCE(SUM("actual_costs_usd"), 0) FROM production_orders WHERE "created_date" >= CURRENT_DATE - INTERVAL \'1 day\'',
            'SELECT COUNT(*) FROM production_orders WHERE "created_date" >= CURRENT_DATE - INTERVAL \'1 day\'',
            0.0,
        )

        kpi_metal = os.getenv("KPI_METAL", "copper").lower()
        metal_price = get_metal_price_usd(kpi_metal)
        if metal_price is None:
            metal_price = float(os.getenv("KPI_METAL_BASELINE", "4.25"))
            kpi_meta["metal_source"] = "BASELINE"
        kpi["metal_price"] = metal_price

        selling_multiplier = float(os.getenv("KPI_SELLING_MULTIPLIER", "1.35"))
        if not qty_fallback and metal_price and total_qty_24h > 0:
            estimated_revenue = total_qty_24h * metal_price * selling_multiplier
            if estimated_revenue > 0:
                kpi["profit_margin"] = ((estimated_revenue - total_cost_24h) / estimated_revenue) * 100.0
                kpi_meta["last_success"]["profit_margin"] = _safe_latest_timestamp(cursor, "production_orders", "created_date")
        else:
            kpi["profit_margin"] = KPI_BASELINES["profit_margin"]
            kpi_meta["fallback_keys"].append("profit_margin")

    except:
        for k, v in KPI_BASELINES.items():
            kpi[k] = v
        kpi["metal_price"] = float(os.getenv("KPI_METAL_BASELINE", "4.25"))
        kpi_meta["fallback_keys"] = list(KPI_BASELINES.keys())
        kpi_meta["metal_source"] = "BASELINE"

    return kpi, kpi_meta

def _kpi_state(value, good_cond, warn_cond=None):
    if good_cond(value):
        return "🟢"
    if warn_cond and warn_cond(value):
        return "🟡"
    return "🔴"

def get_maintenance_snapshot(conn):
    snapshot = {
        "overdue_pm": 0,
        "upcoming_pm_7d": 0,
        "open_work_orders": 0,
        "breakdown_open": 0,
        "breakdown_mttr_hrs": 0.0,
        "total_downtime_7d_hrs": 0.0,
        "use_reference": False,
        "work_orders": [],
    }
    try:
        cursor = conn.cursor()

        snapshot["open_work_orders"] = _safe_count(
            cursor,
            '''SELECT COUNT(*) FROM equipment_maintenance
               WHERE "status" NOT IN ('COMPLETED', 'CLOSED')'''
        )
        snapshot["overdue_pm"] = _safe_count(
            cursor,
            '''SELECT COUNT(*) FROM equipment_maintenance
               WHERE "maintenance_type" = 'PREVENTIVE'
                 AND "planned_end" < NOW()
                 AND "status" NOT IN ('COMPLETED', 'CLOSED')'''
        )
        snapshot["upcoming_pm_7d"] = _safe_count(
            cursor,
            '''SELECT COUNT(*) FROM equipment_maintenance
               WHERE "maintenance_type" = 'PREVENTIVE'
                 AND "planned_start" >= NOW()
                 AND "planned_start" <= NOW() + INTERVAL '7 days'
                 AND "status" NOT IN ('COMPLETED', 'CLOSED')'''
        )
        snapshot["breakdown_open"] = _safe_count(
            cursor,
            '''SELECT COUNT(*) FROM equipment_maintenance
               WHERE "maintenance_type" = 'BREAKDOWN'
                 AND "status" NOT IN ('COMPLETED', 'CLOSED')'''
        )
        snapshot["breakdown_mttr_hrs"] = _safe_scalar(
            cursor,
            '''SELECT COALESCE(AVG("downtime_hours"), 0)
               FROM equipment_maintenance
               WHERE "maintenance_type" = 'BREAKDOWN'
                 AND "created_date" >= CURRENT_DATE - INTERVAL '30 days'
                 AND "status" IN ('COMPLETED', 'CLOSED')''',
            0.0
        )
        snapshot["total_downtime_7d_hrs"] = _safe_scalar(
            cursor,
            '''SELECT COALESCE(SUM("downtime_hours"), 0)
               FROM equipment_maintenance
               WHERE "created_date" >= CURRENT_DATE - INTERVAL '7 days'
                 AND "maintenance_type" IN ('BREAKDOWN', 'CORRECTIVE')''',
            0.0
        )
        try:
            cursor.execute(
                '''SELECT
                    "maintenance_order",
                    "equipment_type",
                    "maintenance_type",
                    "status",
                    "planned_start"::text,
                    "planned_end"::text,
                    "downtime_hours",
                    "technician_id"
                   FROM equipment_maintenance
                   WHERE "status" NOT IN ('COMPLETED', 'CLOSED')
                   ORDER BY
                     CASE "maintenance_type" WHEN 'BREAKDOWN' THEN 0 WHEN 'CORRECTIVE' THEN 1 ELSE 2 END,
                     "planned_end" ASC
                   LIMIT 12'''
            )
            rows = cursor.fetchall()
            snapshot["work_orders"] = [
                {
                    "maintenance_order": r[0], "equipment_type": r[1],
                    "maintenance_type": r[2], "status": r[3],
                    "planned_start": _format_ts(r[4]), "planned_end": _format_ts(r[5]),
                    "downtime_hours": float(r[6]) if r[6] is not None else 0.0,
                    "technician_id": r[7],
                }
                for r in rows
            ]
        except:
            snapshot["work_orders"] = []

        if snapshot["open_work_orders"] == 0 and not snapshot["work_orders"]:
            snapshot.update(MAINTENANCE_BASELINES)
            snapshot["use_reference"] = True
    except:
        snapshot.update(MAINTENANCE_BASELINES)
        snapshot["use_reference"] = True
    return snapshot


def get_otif_snapshot(conn):
    snapshot = {
        "otif_pct": 0.0,
        "on_time_pct": 0.0,
        "in_full_pct": 0.0,
        "completed_30d": 0,
        "late_30d": 0,
        "under_fill_30d": 0,
        "use_reference": False,
        "recent_completions": [],
    }
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN "actual_end_date" <= "planned_end_date" THEN 1 ELSE 0 END) AS on_time,
                SUM(CASE WHEN "confirmed_quantity" * 1.0 / NULLIF("order_quantity", 0) >= 0.95 THEN 1 ELSE 0 END) AS in_full,
                SUM(CASE WHEN "actual_end_date" > "planned_end_date" THEN 1 ELSE 0 END) AS late,
                SUM(CASE WHEN "confirmed_quantity" * 1.0 / NULLIF("order_quantity", 0) < 0.95 THEN 1 ELSE 0 END) AS under_fill
            FROM production_orders
            WHERE "order_status" IN ('COMPLETED', 'CLOSED')
              AND "actual_end_date" IS NOT NULL
              AND "actual_end_date" >= CURRENT_DATE - INTERVAL '30 days'
            '''
        )
        row = cursor.fetchone()
        if row and row[0] and int(row[0]) > 0:
            total = int(row[0])
            on_time = int(row[1] or 0)
            in_full = int(row[2] or 0)
            late = int(row[3] or 0)
            under_fill = int(row[4] or 0)
            on_time_pct = on_time * 100.0 / total
            in_full_pct = in_full * 100.0 / total
            snapshot["otif_pct"] = round((on_time + in_full - total + max(0, total - late - under_fill)) * 100.0 / total, 2)
            snapshot["otif_pct"] = max(0.0, round(on_time_pct * in_full_pct / 100.0, 2))
            snapshot["on_time_pct"] = round(on_time_pct, 2)
            snapshot["in_full_pct"] = round(in_full_pct, 2)
            snapshot["completed_30d"] = total
            snapshot["late_30d"] = late
            snapshot["under_fill_30d"] = under_fill
        else:
            snapshot.update(OTIF_BASELINES)
            snapshot["use_reference"] = True
            return snapshot

        try:
            cursor.execute(
                '''
                SELECT
                    "production_order", "product_type",
                    "order_quantity", "confirmed_quantity",
                    "planned_end_date"::text, "actual_end_date"::text,
                    CASE WHEN "actual_end_date" <= "planned_end_date" THEN true ELSE false END AS on_time,
                    CASE WHEN "confirmed_quantity" * 1.0 / NULLIF("order_quantity",0) >= 0.95 THEN true ELSE false END AS in_full
                FROM production_orders
                WHERE "order_status" IN ('COMPLETED', 'CLOSED')
                  AND "actual_end_date" IS NOT NULL
                ORDER BY "actual_end_date" DESC
                LIMIT 12
                '''
            )
            rows = cursor.fetchall()
            snapshot["recent_completions"] = [
                {
                    "production_order": r[0], "product_type": r[1],
                    "order_quantity": int(r[2]) if r[2] else 0,
                    "confirmed_quantity": int(r[3]) if r[3] else 0,
                    "planned_end_date": _format_ts(r[4]),
                    "actual_end_date": _format_ts(r[5]),
                    "on_time": bool(r[6]), "in_full": bool(r[7]),
                }
                for r in rows
            ]
        except:
            snapshot["recent_completions"] = OTIF_BASELINES["recent_completions"]
    except:
        snapshot.update(OTIF_BASELINES)
        snapshot["use_reference"] = True
    return snapshot


def get_analytics_snapshot(conn):
    kpi, meta = get_kpi_snapshot(conn)
    freshness = get_freshness_snapshot(conn)
    trend = get_trend_snapshot(conn)
    control_tower = get_control_tower_snapshot(conn)
    scheduling = get_scheduling_snapshot(conn)
    traceability = get_traceability_snapshot(conn)
    maintenance = get_maintenance_snapshot(conn)
    otif = get_otif_snapshot(conn)
    inventory = get_inventory_reorder_snapshot(conn)
    alerts = get_operational_alerts(kpi, freshness, control_tower, scheduling)

    fallback_count = len(set(meta.get("fallback_keys", [])))
    total_kpis = len(KPI_BASELINES)
    fallback_ratio = (fallback_count / total_kpis) if total_kpis else 0
    stale_count = len([d for d in freshness.get("details", []) if d.get("sla_state") in ("stale", "missing")])
    freshness_total = freshness.get("total", 1) or 1
    stale_ratio = stale_count / freshness_total
    quality_score = max(0, min(100, int(round(100 - (fallback_ratio * 60 + stale_ratio * 40) * 100))))

    return {
        "kpi": kpi,
        "meta": meta,
        "freshness": freshness,
        "trend": trend,
        "control_tower": control_tower,
        "scheduling": scheduling,
        "traceability": traceability,
        "maintenance": maintenance,
        "otif": otif,
        "inventory": inventory,
        "alerts": alerts,
        "quality_score": quality_score,
    }

@st.cache_resource
def get_agent():
    return AgentBrain()

def fetch_live_data(conn):
    state = {}
    total_rows = 0
    try:
        cursor = conn.cursor()
        for p in PIPELINES:
            table_name = _safe_resolve_table(cursor, p["table"])
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                total_rows += count

                cols_query = ", ".join([_q(col) for col in [p['pk']] + p['cols']])
                cursor.execute(
                    f"SELECT {cols_query} FROM {table_name} ORDER BY {_q(p['pk'])} DESC LIMIT 1"
                )
                last_row = cursor.fetchone()
            except:
                count = 0
                last_row = None

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

    if "auto_refresh" not in st.session_state:
        st.session_state["auto_refresh"] = True
    auto_refresh = c2.toggle("⏱️ AUTO REFRESH", value=st.session_state["auto_refresh"], key="toggle_auto_refresh")
    st.session_state["auto_refresh"] = auto_refresh

    # Init State
    if "prev_total" not in st.session_state: st.session_state["prev_total"] = 0
    if "console_logs" not in st.session_state: st.session_state["console_logs"] = []

    # Data Fetch
    conn = get_db_connection()
    if conn:
        current_state, total_rows = fetch_live_data(conn)
        analytics = get_analytics_snapshot(conn)
        kpi_state = analytics["kpi"]
        kpi_meta = analytics["meta"]
        freshness_state = analytics["freshness"]
        trend_state = analytics["trend"]
        control_tower = analytics["control_tower"]
        scheduling_state = analytics["scheduling"]
        traceability_state = analytics["traceability"]
        maintenance_state = analytics["maintenance"]
        otif_state = analytics["otif"]
        inventory_state = analytics["inventory"]
        alerts_state = analytics["alerts"]
        conn.close()

        if current_state:
            # Metrics
            velocity = total_rows - st.session_state["prev_total"]
            st.session_state["prev_total"] = total_rows

            # Header metrics row (always visible)
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Records", f"{total_rows:,}")
            m2.metric("System Velocity", f"{velocity} events/sec")
            if velocity > 0: m3.success("SYSTEM ONLINE")
            else: m3.info("SYSTEM IDLE")

            # Sub-tabs within SCADA
            scada_tabs = st.tabs([
                "📈 KPI & Overview",
                "🧭 Control Tower & Scheduling",
                "🔗 Traceability & CAPA",
                "🔧 Maintenance & OTIF",
                "📦 Inventory Reorder",
                "🏭 Pipeline Grid & Logs"
            ])

            # ----------------------------------------
            # SUB-TAB 1: KPI & OVERVIEW
            # ----------------------------------------
            with scada_tabs[0]:
                h1, h2, h3, h4 = st.columns(4)
                h1.metric("Database", "ONLINE")
                h2.metric("Metal Source", kpi_meta["metal_source"])
                h3.metric("Feed Freshness", f"{freshness_state['fresh']}/{freshness_state['total']}")
                h4.metric("Data Quality Score", f"{analytics['quality_score']}/100")

                st.markdown("### 📈 KPI Snapshot")

                yield_state = _kpi_state(kpi_state["yield_24h"], lambda v: v > 88, lambda v: 82 <= v <= 88)
                scrap_state = _kpi_state(kpi_state["scrap_pct"], lambda v: v < 6, lambda v: 6 <= v <= 10)
                energy_state = _kpi_state(kpi_state["energy_kwh_ton"], lambda v: v < 420, lambda v: 420 <= v <= 520)
                temp_state = _kpi_state(kpi_state["avg_pour_temp"], lambda v: 1380 <= v <= 1450, lambda v: (1360 <= v < 1380) or (1450 < v <= 1470))
                good_state = _kpi_state(kpi_state["good_castings_today"], lambda v: v > 120, lambda v: 80 <= v <= 120)
                margin_state = _kpi_state(kpi_state["profit_margin"], lambda v: v > 15, lambda v: 8 <= v <= 15)
                melt_state = _kpi_state(kpi_state["melt_approval_pct"], lambda v: v >= 95, lambda v: 90 <= v < 95)
                order_state = _kpi_state(kpi_state["active_orders"], lambda v: 10 <= v <= 120, lambda v: 3 <= v < 10)
                reject_state = _kpi_state(kpi_state["rejection_rate"], lambda v: v < 4, lambda v: 4 <= v <= 8)
                breakdown_state = _kpi_state(kpi_state["breakdown_events_7d"], lambda v: v <= 2, lambda v: 3 <= v <= 5)

                k1, k2, k3 = st.columns(3)
                k1.metric(f"{yield_state} Current Yield % (24h)", f"{kpi_state['yield_24h']:.2f}%")
                k2.metric(f"{scrap_state} Scrap % (24h)", f"{kpi_state['scrap_pct']:.2f}%")
                k3.metric(f"{energy_state} Energy kWh/ton (24h)", f"{kpi_state['energy_kwh_ton']:.2f}")

                k4, k5, k6 = st.columns(3)
                k4.metric(f"{temp_state} Avg Pour Temperature (24h)", f"{kpi_state['avg_pour_temp']:.1f} °C")
                k5.metric(f"{good_state} Good Castings Today", f"{int(kpi_state['good_castings_today'])}")
                k6.metric(f"{margin_state} Profit Margin (Metal API)", f"{kpi_state['profit_margin']:.2f}%")

                k7, k8, k9, k10 = st.columns(4)
                k7.metric(f"{melt_state} Melt Approval % (24h)", f"{kpi_state['melt_approval_pct']:.2f}%")
                k8.metric(f"{order_state} Active Orders", f"{int(kpi_state['active_orders'])}")
                k9.metric(f"{reject_state} QC Reject Rate (7d)", f"{kpi_state['rejection_rate']:.2f}%")
                k10.metric(f"{breakdown_state} Breakdowns (7d)", f"{int(kpi_state['breakdown_events_7d'])}")

                st.markdown("#### Trends")
                t1, t2, t3, t4 = st.columns(4)
                t1.metric("Yield Trend (24h vs prev)", f"{trend_state['yield_delta']:+.2f} pp")
                t2.metric("Scrap Trend (24h vs prev)", f"{trend_state['scrap_delta']:+.2f} pp")
                t3.metric("Energy Trend (24h vs prev)", f"{trend_state['energy_delta']:+.2f}")
                t4.metric("Reject Trend (7d vs prev)", f"{trend_state['reject_delta']:+.2f} pp")

                st.caption(f"Inventory issue quantity (24h): {kpi_state['inventory_issue_qty_24h']:.2f}")

                if kpi_meta["fallback_keys"]:
                    fallback_list = ", ".join(sorted(set(kpi_meta["fallback_keys"])))
                    st.caption(f"Using reference values for: {fallback_list}")

                if kpi_meta.get("last_success"):
                    last_success_text = " | ".join(
                        [f"{k}: {_format_ts(v)}" for k, v in kpi_meta["last_success"].items()]
                    )
                    st.caption(f"KPI last successful updates → {last_success_text}")

                if kpi_state["metal_price"]:
                    st.caption(
                        f"Metal Price Source: {kpi_meta['metal_source']} | Metal: {os.getenv('KPI_METAL', 'copper').upper()} | Price: ${kpi_state['metal_price']:.4f}"
                    )
                else:
                    st.caption("Metal Price unavailable.")

                if freshness_state["details"]:
                    freshness_text = " | ".join(
                        [
                            f"{_freshness_icon(item['sla_state'])} {item['label']}: {_format_ts(item['latest'])}"
                            for item in freshness_state["details"]
                        ]
                    )
                    st.caption(f"Latest ingestion timestamps → {freshness_text}")

            # ----------------------------------------
            # SUB-TAB 2: CONTROL TOWER & SCHEDULING
            # ----------------------------------------
            with scada_tabs[1]:
                st.markdown("### 🧭 Production Control Tower")

                ct1, ct2, ct3, ct4, ct5 = st.columns(5)
                ct1.metric("WIP Orders", f"{int(control_tower['wip_orders'])}")
                ct2.metric("Delayed Orders", f"{int(control_tower['delayed_orders'])}")
                ct3.metric("Completed Today", f"{int(control_tower['completed_today'])}")
                ct4.metric("Bottleneck Stage", str(control_tower["bottleneck_stage"]))
                ct5.metric("Bottleneck Load", f"{int(control_tower['bottleneck_load'])}")

                mix = control_tower["stage_mix"]
                st.caption(
                    f"Stage mix → CREATED: {mix.get('CREATED', 0)} | RELEASED: {mix.get('RELEASED', 0)} | "
                    f"IN_PROCESS: {mix.get('IN_PROCESS', 0)} | COMPLETED: {mix.get('COMPLETED', 0)} | CLOSED: {mix.get('CLOSED', 0)}"
                )

                if control_tower["use_reference"]:
                    st.caption("Production control view is currently using reference values for missing fields.")

                st.markdown("**At-Risk Orders (By Delay/Priority)**")
                st.dataframe(control_tower["risk_orders"], width='stretch', hide_index=True)

                st.markdown("---")
                st.markdown("### 🗓️ Order Scheduling Board")

                s1, s2, s3, s4, s5 = st.columns(5)
                s1.metric("Due Today", f"{int(scheduling_state['due_today'])}")
                s2.metric("Due in 3 Days", f"{int(scheduling_state['due_next_3d'])}")
                s3.metric("Overdue Open", f"{int(scheduling_state['overdue_open'])}")
                s4.metric("Planned Qty (7d)", f"{int(scheduling_state['planned_qty_7d'])}")
                s5.metric("High Priority Open", f"{int(scheduling_state['high_priority_open'])}")

                util = float(scheduling_state["capacity_utilization_pct"])
                util_state = "🟢" if util <= 85 else ("🟡" if util <= 100 else "🔴")
                st.caption(f"{util_state} Capacity utilization (7d plan): {util:.1f}%")

                if scheduling_state["use_reference"]:
                    st.caption("Scheduling board is currently using reference values for missing fields.")

                st.markdown("**Dispatch-Priority Queue (Open Orders)**")
                st.dataframe(scheduling_state["queue"], width='stretch', hide_index=True)

                st.markdown("---")
                st.markdown("### 🚨 Operational Alerts")

                if alerts_state:
                    for alert in alerts_state[:8]:
                        if alert["severity"] == "CRITICAL":
                            st.error(f"[CRITICAL] {alert['title']} — {alert['detail']}")
                        elif alert["severity"] == "WARN":
                            st.warning(f"[WARN] {alert['title']} — {alert['detail']}")
                        else:
                            st.info(f"[INFO] {alert['title']} — {alert['detail']}")
                else:
                    st.success("No active operational alerts.")

            # ----------------------------------------
            # SUB-TAB 3: TRACEABILITY & CAPA
            # ----------------------------------------
            with scada_tabs[2]:
                st.markdown("### 🔗 End-to-End Traceability")

                tr1, tr2, tr3, tr4 = st.columns(4)
                tr1.metric("Trace Coverage", f"{traceability_state['coverage_pct']:.1f}%")
                tr2.metric("Linked Orders", f"{int(traceability_state['linked_orders'])}")
                tr3.metric("Missing Links", f"{int(traceability_state['missing_links'])}")
                tr4.metric("Quality Holds", f"{int(traceability_state['quality_holds'])}")

                if traceability_state.get("use_reference"):
                    st.caption("Traceability view is currently using reference values for missing source data.")

                st.dataframe(traceability_state["chains"], width='stretch', hide_index=True)

                st.markdown("---")
                st.markdown("### 🧪 CAPA Workflow")

                # 1. Seed any missing keys (safe — only writes if key absent)
                _init_capa_state()
                # 2. Apply any pending create-form reset BEFORE widgets render
                _flush_capa_reset()

                alert_options = ["Manual Entry"] + [f"{a['severity']} | {a['title']}" for a in alerts_state]
                # NOTE: capa_alert_source selectbox must render before we read its value
                selected_source = st.selectbox("Create CAPA from", alert_options, key="capa_alert_source")

                linked_alert = ""
                if selected_source != "Manual Entry":
                    parts = selected_source.split(" | ", 1)
                    linked_alert = parts[1] if len(parts) > 1 else selected_source

                with st.form("capa_create_form", clear_on_submit=False):
                    c_form_1, c_form_2, c_form_3 = st.columns(3)
                    issue = c_form_1.text_input("Issue", key="capa_issue")
                    owner = c_form_2.text_input("Owner", key="capa_owner")
                    due_date = c_form_3.date_input("Due Date", key="capa_due_date")

                    c_form_4, c_form_5 = st.columns(2)
                    priority = c_form_4.selectbox("Priority", ["LOW", "MEDIUM", "HIGH", "CRITICAL"], key="capa_priority")
                    source = c_form_5.selectbox("Source", ["ALERT", "MANUAL", "AUDIT", "CUSTOMER"], key="capa_source")

                    submitted = st.form_submit_button("Create CAPA")
                    if submitted and issue.strip() and owner.strip():
                        capa_id = f"CAPA-{st.session_state['capa_seq']:04d}"
                        st.session_state["capa_seq"] += 1
                        st.session_state["capa_register"].append(
                            {
                                "capa_id": capa_id,
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "source": source,
                                "issue": issue.strip(),
                                "linked_alert": linked_alert,
                                "owner": owner.strip(),
                                "priority": priority,
                                "status": "OPEN",
                                "due_date": due_date.isoformat(),
                                "closure_notes": "",
                            }
                        )
                        st.success(f"Created {capa_id}")

                        # Flag to clear fields before the next render cycle
                        st.session_state["capa_reset_fields"] = True

                capa_state = _get_capa_snapshot()
                cp1, cp2, cp3, cp4 = st.columns(4)
                cp1.metric("CAPA Total", f"{capa_state['total']}")
                cp2.metric("Open", f"{capa_state['open']}")
                cp3.metric("Overdue", f"{capa_state['overdue']}")
                cp4.metric("Due in 7 Days", f"{capa_state['due_7d']}")

                if capa_state["register"]:
                    capa_ids = [row["capa_id"] for row in capa_state["register"]]
                    edit_id = st.selectbox("Update CAPA", capa_ids, key="capa_edit_id")
                    current = next((row for row in st.session_state["capa_register"] if row["capa_id"] == edit_id), None)

                    if current:
                        if edit_id != st.session_state.get("capa_prev_edit"):
                            st.session_state["capa_status_update"] = current["status"]
                            st.session_state["capa_closure_notes"] = current.get("closure_notes", "")
                            st.session_state["capa_prev_edit"] = edit_id

                        with st.form("capa_update_form", clear_on_submit=False):
                            u1, u2 = st.columns(2)
                            status = u1.selectbox("Status", ["OPEN", "IN_PROGRESS", "VERIFICATION", "CLOSED"], key="capa_status_update")
                            closure_notes = u2.text_input("Closure Notes", key="capa_closure_notes")
                            if st.form_submit_button("Save CAPA Update"):
                                current["status"] = status
                                current["closure_notes"] = closure_notes.strip()
                                st.success(f"Updated {edit_id}")

                st.dataframe(capa_state["register"], width='stretch', hide_index=True)

            # ----------------------------------------
            # SUB-TAB 4: MAINTENANCE & OTIF
            # ----------------------------------------
            with scada_tabs[3]:
                st.markdown("### 🔧 Maintenance Planner")

                ma1, ma2, ma3, ma4, ma5 = st.columns(5)
                ma1.metric("Open Work Orders", f"{int(maintenance_state['open_work_orders'])}")
                ma2.metric("Overdue PM", f"{int(maintenance_state['overdue_pm'])}")
                ma3.metric("Upcoming PM (7d)", f"{int(maintenance_state['upcoming_pm_7d'])}")
                ma4.metric("Breakdowns Open", f"{int(maintenance_state['breakdown_open'])}")
                ma5.metric("Avg MTTR (30d)", f"{maintenance_state['breakdown_mttr_hrs']:.1f} h")

                downtime_state = "🟢" if maintenance_state["total_downtime_7d_hrs"] <= 20 else ("🟡" if maintenance_state["total_downtime_7d_hrs"] <= 48 else "🔴")
                st.caption(f"{downtime_state} Total unplanned downtime (7d): {maintenance_state['total_downtime_7d_hrs']:.1f} hrs")
                if maintenance_state.get("use_reference"):
                    st.caption("Maintenance view is using reference values — no open work orders found in DB.")

                st.markdown("**Open Work Orders (Breakdown/Corrective First)**")
                st.dataframe(maintenance_state["work_orders"], width='stretch', hide_index=True)

                st.markdown("---")
                st.markdown("### 📦 Dispatch & OTIF Tracking (Last 30 Days)")

                otif_state_icon = "🟢" if otif_state["otif_pct"] >= 90 else ("🟡" if otif_state["otif_pct"] >= 75 else "🔴")
                ot_icon = "🟢" if otif_state["on_time_pct"] >= 90 else ("🟡" if otif_state["on_time_pct"] >= 75 else "🔴")
                if_icon = "🟢" if otif_state["in_full_pct"] >= 95 else ("🟡" if otif_state["in_full_pct"] >= 85 else "🔴")

                ot1, ot2, ot3, ot4, ot5, ot6 = st.columns(6)
                ot1.metric(f"{otif_state_icon} OTIF %", f"{otif_state['otif_pct']:.1f}%")
                ot2.metric(f"{ot_icon} On-Time %", f"{otif_state['on_time_pct']:.1f}%")
                ot3.metric(f"{if_icon} In-Full %", f"{otif_state['in_full_pct']:.1f}%")
                ot4.metric("Completed (30d)", f"{int(otif_state['completed_30d'])}")
                ot5.metric("Late (30d)", f"{int(otif_state['late_30d'])}")
                ot6.metric("Under-Fill (30d)", f"{int(otif_state['under_fill_30d'])}")

                if otif_state.get("use_reference"):
                    st.caption("OTIF view is using reference values — no completed orders with actual end dates found in DB.")

                st.markdown("**Recent Completed Orders**")
                st.dataframe(otif_state["recent_completions"], width='stretch', hide_index=True)

            # ----------------------------------------
            # SUB-TAB 5: INVENTORY REORDER
            # ----------------------------------------
            with scada_tabs[4]:
                st.markdown("### 📦 Inventory Reorder Intelligence")

                i1, i2, i3 = st.columns(3)
                i1.metric("Reorder Items", f"{int(inventory_state['reorder_items'])}")
                i2.metric("Critical Items", f"{int(inventory_state['critical_items'])}")
                i3.metric("Candidates Shown", f"{int(inventory_state['total_candidates'])}")

                if inventory_state.get("use_reference"):
                    st.caption("Inventory reorder view is using reference values — insufficient inventory movement/stock data found.")
                st.caption("Suggested reorder quantity uses: Safety Stock + (Avg Daily Issue × Lead Time) − Current Stock")

                st.dataframe(inventory_state["reorder_list"], width='stretch', hide_index=True)

            # ----------------------------------------
            # SUB-TAB 6: PIPELINE GRID & LOGS
            # ----------------------------------------
            with scada_tabs[5]:
                # Logging
                if velocity > 0:
                    ts = datetime.now().strftime("%H:%M:%S")
                    st.session_state["console_logs"].append(f"[{ts}] [INFO] Processed {velocity} new records.")

                st.markdown("### 🏭 Pipeline Status Grid")
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
        st.error("❌ DB Connection Failed. Is `InputPipeline/run_all_feeders.py` running?")


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
    if st.session_state.get("auto_refresh", True):
        refresh_seconds = float(os.getenv("SCADA_REFRESH_SECONDS", "5"))
        time.sleep(max(1.0, refresh_seconds))
        st.rerun()