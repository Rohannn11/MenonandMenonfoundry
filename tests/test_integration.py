"""
Menon & Menon Foundry OS — PostgreSQL ↔ Streamlit Integration Tests
====================================================================

Validates the full data path between the PostgreSQL backend and the
Streamlit dashboard layer, without launching a browser or importing
streamlit itself.

Coverage
--------
Suite 1  – DB Connectivity                    (can we even connect?)
Suite 2  – Schema Integrity                   (all 11 tables + expected cols present)
Suite 3  – Dashboard Helper Functions          (return-type & key contracts)
Suite 4  – KPI Query Accuracy                 (numeric sanity of live values)
Suite 5  – Pipeline Row Presence              (every PIPELINE table has at least 1 row)
Suite 6  – Data Freshness Layer               (freshness snapshot structure)
Suite 7  – Production Flow Integrity          (cross-table FK / ordering checks)
Suite 8  – Inventory & Reorder Snapshot       (column shapes, non-negative values)
Suite 9  – Control-Tower & Scheduling         (stage-mix totals, queue key existence)
Suite 10 – Traceability Chains                (chain structure, valid status values)
Suite 11 – Read-Only Enforcement              (query_foundry_db blocks writes)
Suite 12 – Agent Tool → DB Round-trip         (chatbot tool returns real rows)

Run
---
    # from project root (venv activated):
    python -m pytest tests/test_integration.py -v
    # or
    python tests/test_integration.py
"""

from __future__ import annotations

import os
import sys
import time
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

import psycopg2

# ---------------------------------------------------------------------------
# Shared DB helper
# ---------------------------------------------------------------------------

def _get_conn():
    cfg = {
        "host":     os.getenv("DB_HOST", "localhost"),
        "database": os.getenv("DB_NAME"),
        "user":     os.getenv("DB_USER"),
        "password": os.getenv("DB_PASS"),
        "port":     os.getenv("DB_PORT", "5432"),
    }
    if not cfg["database"]:
        return None
    try:
        return psycopg2.connect(**cfg)
    except Exception:
        return None


def _skip_if_no_db(test_case):
    """Skip test class if the database is unreachable."""
    conn = _get_conn()
    if conn is None:
        raise unittest.SkipTest(
            "PostgreSQL not reachable — set DB_NAME/DB_USER/DB_PASS/DB_HOST in .env"
        )
    conn.close()


# ---------------------------------------------------------------------------
# All 11 production tables with a representative subset of columns
# ---------------------------------------------------------------------------

EXPECTED_TABLES = {
    "material_master": [
        "material_number", "material_type", "description", "base_unit",
        "standard_price_usd", "safety_stock", "lead_time_days",
    ],
    "bill_of_materials": [
        "bom_number", "parent_material", "component_material",
        "component_quantity", "bom_status",
    ],
    "production_orders": [
        "production_order", "product_type", "alloy_grade",
        "order_quantity", "confirmed_quantity", "scrap_quantity",
        "order_status", "planned_end_date",
    ],
    "melting_heat_records": [
        "heat_number", "melt_date", "furnace_id", "tap_temperature_c",
        "pour_temperature_c", "quality_status", "yield_pct", "energy_kwh",
    ],
    "molding_records": [
        "mold_batch", "production_order", "molding_type",
        "planned_quantity", "actual_quantity", "quality_check",
    ],
    "casting_records": [
        "casting_batch", "heat_number", "production_order",
        "casting_date", "good_castings", "scrap_castings",
        "yield_pct", "quality_grade",
    ],
    "heat_treatment": [
        "ht_batch_number", "casting_batch", "treatment_type",
        "target_temperature_c", "actual_temperature_c", "quality_status",
    ],
    "machining_operations": [
        "operation_id", "production_order", "machine_type",
        "operation_type", "quality_status", "power_consumption_kw",
        "quantity_processed",
    ],
    "quality_inspections": [
        "inspection_lot", "inspection_date", "inspection_stage",
        "defect_count", "overall_decision", "material_number",
    ],
    "inventory_movements": [
        "document_number", "posting_date", "movement_type",
        "material_number", "quantity", "stock_before", "stock_after", "amount_usd",
    ],
    "equipment_maintenance": [
        "maintenance_order", "equipment_number", "maintenance_type",
        "status", "planned_start", "planned_end", "downtime_hours",
    ],
}

# Dashboard PIPELINES config (mirrors dashboard.py)
PIPELINES = [
    {"name": "01 MATERIALS",  "table": "material_master"},
    {"name": "02 BOMs",       "table": "bill_of_materials"},
    {"name": "03 MELTING",    "table": "melting_heat_records"},
    {"name": "04 MOLDING",    "table": "molding_records"},
    {"name": "05 CASTING",    "table": "casting_records"},
    {"name": "06 HEAT TREAT", "table": "heat_treatment"},
    {"name": "07 MACHINING",  "table": "machining_operations"},
    {"name": "08 QUALITY QC", "table": "quality_inspections"},
    {"name": "09 INVENTORY",  "table": "inventory_movements"},
    {"name": "10 PRODUCTION", "table": "production_orders"},
    {"name": "11 MAINTENANCE","table": "equipment_maintenance"},
]


# ===========================================================================
# Suite 1 – DB Connectivity
# ===========================================================================

class TestDBConnectivity(unittest.TestCase):
    """Verify PostgreSQL connection is reachable and basic operations work."""

    @classmethod
    def setUpClass(cls):
        _skip_if_no_db(cls)

    def test_env_vars_are_set(self):
        for var in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASS"):
            self.assertIsNotNone(os.getenv(var), f"Missing env var: {var}")

    def test_connection_opens_and_closes(self):
        conn = _get_conn()
        self.assertIsNotNone(conn, "psycopg2.connect() returned None")
        conn.close()

    def test_connection_is_not_read_only(self):
        """Dashboard writes (e.g. CAPA) require a writable default session."""
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SHOW transaction_read_only")
        val = cur.fetchone()[0]
        conn.close()
        # Default session should be writable ('off')
        self.assertEqual(val.strip(), "off", "Default session must be writable (tools.py enforces read-only per-query)")

    def test_server_version_is_accessible(self):
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        row = cur.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertIn("PostgreSQL", row[0])

    def test_current_database_matches_env(self):
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT current_database()")
        db_name = cur.fetchone()[0]
        conn.close()
        self.assertEqual(db_name, os.getenv("DB_NAME"))


# ===========================================================================
# Suite 2 – Schema Integrity
# ===========================================================================

class TestSchemaIntegrity(unittest.TestCase):
    """All 11 production tables must exist with their expected columns."""

    @classmethod
    def setUpClass(cls):
        _skip_if_no_db(cls)
        cls.conn = _get_conn()
        cls.cur = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.cur.close()
        cls.conn.close()

    def _get_columns(self, table_name: str) -> set:
        self.cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            """,
            (table_name,),
        )
        return {row[0].lower() for row in self.cur.fetchall()}

    def test_all_tables_exist(self):
        self.cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        )
        existing = {row[0].lower() for row in self.cur.fetchall()}
        for table in EXPECTED_TABLES:
            with self.subTest(table=table):
                self.assertIn(table, existing, f"Table '{table}' is missing from the database")

    def test_all_expected_columns_present(self):
        for table, cols in EXPECTED_TABLES.items():
            actual_cols = self._get_columns(table)
            for col in cols:
                with self.subTest(table=table, column=col):
                    self.assertIn(
                        col.lower(), actual_cols,
                        f"Column '{col}' missing from table '{table}'"
                    )

    def test_primary_keys_are_unique(self):
        pk_map = {
            "material_master":    "material_number",
            "production_orders":  "production_order",
            "melting_heat_records": "heat_number",
            "casting_records":    "casting_batch",
            "quality_inspections": "inspection_lot",
            "inventory_movements": "document_number",
            "equipment_maintenance": "maintenance_order",
        }
        for table, pk in pk_map.items():
            with self.subTest(table=table):
                self.cur.execute(
                    f'SELECT COUNT(*), COUNT(DISTINCT "{pk}") FROM {table}'
                )
                total, distinct = self.cur.fetchone()
                self.assertEqual(
                    total, distinct,
                    f"Duplicate PKs detected in {table}.{pk}"
                )


# ===========================================================================
# Suite 3 – Dashboard Helper Functions
# ===========================================================================

class TestDashboardHelpers(unittest.TestCase):
    """
    Validate every dashboard snapshot's SQL contract directly.

    dashboard.py is a Streamlit app-script: it executes top-level UI calls
    (st.tabs, st.columns, get_capa_snapshot …) on import, making it impossible
    to import as a plain Python module in a test environment.  Instead we run
    the exact SQL that each snapshot function uses and assert on the shape and
    domain validity of the results – which is the meaningful integration check.
    """

    @classmethod
    def setUpClass(cls):
        _skip_if_no_db(cls)
        cls.conn = _get_conn()
        if cls.conn is None:
            raise unittest.SkipTest("DB not reachable")
        cls.cur = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.cur.close()
        cls.conn.close()

    def tearDown(self):
        # Roll back any aborted transaction so the next test gets a clean state
        self.conn.rollback()

    # ------------------------------------------------------------------
    # Freshness snapshot  (get_freshness_snapshot)
    # ------------------------------------------------------------------
    FRESHNESS_SOURCES = [
        ("melting_heat_records",  "melt_date"),
        ("casting_records",       "casting_date"),
        ("heat_treatment",        "treatment_date"),
        ("quality_inspections",   "inspection_date"),
        ("inventory_movements",   "posting_date"),
        ("equipment_maintenance", "planned_start"),
    ]

    def test_freshness_max_timestamp_queryable(self):
        """MAX(timestamp) must execute without error for all 6 freshness sources."""
        for table, col in self.FRESHNESS_SOURCES:
            with self.subTest(table=table):
                self.cur.execute(f'SELECT MAX("{col}") FROM {table}')
                row = self.cur.fetchone()
                self.assertIsNotNone(row)

    def test_freshness_covers_exactly_six_streams(self):
        """Dashboard FRESHNESS_CONFIG always has exactly 6 entries."""
        self.assertEqual(len(self.FRESHNESS_SOURCES), 6)

    def test_freshness_latest_timestamps_are_not_none(self):
        """Every freshness table must have at least one row (feeder has run)."""
        for table, col in self.FRESHNESS_SOURCES:
            with self.subTest(table=table):
                self.cur.execute(f'SELECT MAX("{col}") FROM {table}')
                val = self.cur.fetchone()[0]
                self.assertIsNotNone(val, f"{table}.{col} is NULL — feeder may not have run")

    # ------------------------------------------------------------------
    # Trend snapshot  (get_trend_snapshot)
    # ------------------------------------------------------------------
    def test_trend_yield_delta_query_executes(self):
        self.cur.execute(
            "SELECT COALESCE(AVG(yield_pct), 0) FROM casting_records "
            "WHERE casting_date >= NOW() - INTERVAL '24 hours'"
        )
        val = self.cur.fetchone()[0]
        self.assertIsNotNone(val)

    def test_trend_reject_delta_query_executes(self):
        self.cur.execute(
            """
            SELECT COALESCE(
                SUM(CASE WHEN overall_decision = 'REJECT' THEN 1 ELSE 0 END)
                * 100.0 / NULLIF(COUNT(*), 0), 0)
            FROM quality_inspections
            WHERE inspection_date >= NOW() - INTERVAL '7 days'
            """
        )
        val = self.cur.fetchone()[0]
        self.assertIsNotNone(val)

    def test_trend_energy_query_executes(self):
        # energy_kwh and charge_weight_kg are the actual column names in schema.sql
        self.cur.execute(
            """
            SELECT COALESCE(
                SUM(energy_kwh) / NULLIF(SUM(charge_weight_kg) / 1000.0, 0), 0)
            FROM melting_heat_records
            WHERE melt_date >= NOW() - INTERVAL '24 hours'
            """
        )
        val = self.cur.fetchone()[0]
        self.assertIsNotNone(val)

    # ------------------------------------------------------------------
    # Control-tower snapshot  (get_control_tower_snapshot)
    # ------------------------------------------------------------------
    def test_control_tower_wip_query(self):
        self.cur.execute(
            "SELECT COUNT(*) FROM production_orders "
            "WHERE order_status IN ('CREATED','RELEASED','IN_PROCESS')"
        )
        wip = self.cur.fetchone()[0]
        self.assertIsInstance(wip, int)
        self.assertGreaterEqual(wip, 0)

    def test_control_tower_stage_mix_query(self):
        self.cur.execute(
            "SELECT order_status, COUNT(*) FROM production_orders GROUP BY order_status"
        )
        rows = self.cur.fetchall()
        statuses = {r[0] for r in rows}
        known = {"CREATED", "RELEASED", "IN_PROCESS", "COMPLETED", "CLOSED"}
        self.assertFalse(statuses - known, f"Unexpected statuses: {statuses - known}")

    def test_control_tower_risk_orders_columns(self):
        self.cur.execute(
            """
            SELECT production_order, order_status, planned_end_date,
                   order_quantity, priority
            FROM production_orders
            WHERE order_status IN ('CREATED','RELEASED','IN_PROCESS')
            ORDER BY priority ASC LIMIT 8
            """
        )
        rows = self.cur.fetchall()
        if rows:
            self.assertEqual(len(rows[0]), 5)

    # ------------------------------------------------------------------
    # Scheduling snapshot  (get_scheduling_snapshot)
    # ------------------------------------------------------------------
    def test_scheduling_due_today_query(self):
        self.cur.execute(
            "SELECT COUNT(*) FROM production_orders "
            "WHERE planned_end_date = CURRENT_DATE "
            "AND order_status NOT IN ('COMPLETED','CLOSED')"
        )
        self.assertGreaterEqual(self.cur.fetchone()[0], 0)

    def test_scheduling_capacity_utilization_query(self):
        self.cur.execute(
            """
            SELECT COALESCE(SUM(order_quantity), 0)
            FROM production_orders
            WHERE planned_start_date <= CURRENT_DATE + INTERVAL '7 days'
              AND planned_end_date   >= CURRENT_DATE
              AND order_status NOT IN ('COMPLETED','CLOSED')
            """
        )
        val = float(self.cur.fetchone()[0] or 0)
        self.assertGreaterEqual(val, 0.0)

    def test_scheduling_queue_query(self):
        self.cur.execute(
            """
            SELECT production_order, material_number, order_quantity,
                   planned_start_date, planned_end_date, order_status, priority
            FROM production_orders
            WHERE order_status NOT IN ('COMPLETED','CLOSED')
            ORDER BY priority ASC, planned_end_date ASC
            LIMIT 15
            """
        )
        rows = self.cur.fetchall()
        if rows:
            self.assertEqual(len(rows[0]), 7, "Queue row should have 7 columns")

    # ------------------------------------------------------------------
    # Inventory reorder snapshot  (get_inventory_reorder_snapshot)
    # ------------------------------------------------------------------
    def test_inventory_latest_stock_query(self):
        self.cur.execute(
            """
            SELECT DISTINCT ON (material_number)
                material_number, stock_after::numeric
            FROM inventory_movements
            ORDER BY material_number, posting_date DESC, document_number DESC
            LIMIT 10
            """
        )
        rows = self.cur.fetchall()
        self.assertIsInstance(rows, list)

    def test_inventory_reorder_suggestion_non_negative(self):
        self.cur.execute(
            """
            WITH ls AS (
                SELECT DISTINCT ON (material_number)
                    material_number, stock_after::numeric AS current_stock
                FROM inventory_movements
                ORDER BY material_number, posting_date DESC, document_number DESC
            )
            SELECT mm.material_number,
                GREATEST(0, mm.safety_stock - COALESCE(ls.current_stock, 0)) AS reorder_qty
            FROM material_master mm
            LEFT JOIN ls ON ls.material_number = mm.material_number
            WHERE mm.safety_stock > 0
            LIMIT 15
            """
        )
        for mat, qty in self.cur.fetchall():
            self.assertGreaterEqual(float(qty or 0), 0.0, f"Negative reorder for {mat}")

    # ------------------------------------------------------------------
    # Traceability snapshot  (get_traceability_snapshot)
    # ------------------------------------------------------------------
    def test_traceability_chain_query_columns(self):
        self.cur.execute(
            """
            SELECT po.production_order,
                   COALESCE(cr.heat_number, '-'),
                   COALESCE(cr.casting_batch, '-'),
                   COALESCE(ht.ht_batch_number, '-'),
                   po.order_status
            FROM production_orders po
            LEFT JOIN casting_records cr ON cr.production_order = po.production_order
            LEFT JOIN heat_treatment  ht ON ht.production_order = po.production_order
            ORDER BY po.created_date DESC LIMIT 10
            """
        )
        rows = self.cur.fetchall()
        if rows:
            self.assertEqual(len(rows[0]), 5)

    def test_traceability_coverage_pct_bounded(self):
        self.cur.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN cr.casting_batch IS NOT NULL THEN 1 ELSE 0 END) AS linked
            FROM production_orders po
            LEFT JOIN casting_records cr ON cr.production_order = po.production_order
            """
        )
        total, linked = self.cur.fetchone()
        if total and total > 0:
            pct = (linked or 0) * 100.0 / total
            self.assertGreaterEqual(pct, 0.0)
            self.assertLessEqual(pct, 100.0)


# ===========================================================================
# Suite 4 – KPI Query Accuracy
# ===========================================================================

class TestKPIQueryAccuracy(unittest.TestCase):
    """Run the exact KPI SQL statements the dashboard uses and validate results."""

    @classmethod
    def setUpClass(cls):
        _skip_if_no_db(cls)
        cls.conn = _get_conn()
        cls.cur = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.cur.close()
        cls.conn.close()

    def _scalar(self, sql, default=0.0):
        try:
            self.cur.execute(sql)
            row = self.cur.fetchone()
            return float(row[0]) if row and row[0] is not None else default
        except Exception:
            return default

    def test_avg_tap_temperature_is_physically_valid(self):
        val = self._scalar(
            "SELECT AVG(tap_temperature_c) FROM melting_heat_records"
        )
        # Castings are typically between 1350–1600°C
        self.assertGreater(val, 1000, "Avg tap temp < 1000°C — likely wrong data")
        self.assertLess(val, 1700, "Avg tap temp > 1700°C — physically unrealistic")

    def test_avg_casting_yield_is_percentage(self):
        val = self._scalar("SELECT AVG(yield_pct) FROM casting_records")
        self.assertGreaterEqual(val, 0.0)
        self.assertLessEqual(val, 100.0)

    def test_scrap_castings_never_exceed_expected(self):
        self.cur.execute(
            "SELECT COUNT(*) FROM casting_records WHERE scrap_castings > expected_castings"
        )
        count = self.cur.fetchone()[0]
        self.assertEqual(count, 0, "scrap_castings > expected_castings in some rows")

    def test_good_plus_scrap_equals_molds_poured(self):
        """good_castings + scrap_castings should equal molds_poured for every row."""
        self.cur.execute(
            """
            SELECT COUNT(*)
            FROM casting_records
            WHERE (good_castings + scrap_castings) <> molds_poured
            """
        )
        mismatches = self.cur.fetchone()[0]
        self.assertEqual(mismatches, 0, f"{mismatches} casting rows where good+scrap ≠ molds_poured")

    def test_melt_rejection_rate_is_bounded(self):
        self.cur.execute(
            """
            SELECT
                COUNT(CASE WHEN quality_status = 'REJECTED' THEN 1 END) * 100.0
                / NULLIF(COUNT(*), 0) AS rejection_pct
            FROM melting_heat_records
            """
        )
        pct = float(self.cur.fetchone()[0] or 0.0)
        self.assertGreaterEqual(pct, 0.0)
        self.assertLessEqual(pct, 100.0)

    def test_energy_per_ton_is_reasonable(self):
        val = self._scalar(
            """
            SELECT SUM(energy_kwh) / NULLIF(SUM(charge_weight_kg) / 1000.0, 0)
            FROM melting_heat_records
            """
        )
        # Typical EAF/induction: 350–700 kWh/ton
        if val > 0:
            self.assertGreater(val, 100, "Energy/ton looks suspiciously low")
            self.assertLess(val, 2000, "Energy/ton looks suspiciously high")

    def test_inventory_stock_after_is_non_negative(self):
        self.cur.execute(
            "SELECT COUNT(*) FROM inventory_movements WHERE stock_after < 0"
        )
        negatives = self.cur.fetchone()[0]
        self.assertEqual(negatives, 0, "Negative stock_after values detected")

    def test_quality_inspection_decisions_are_valid(self):
        valid = {"ACCEPT", "REJECT", "CONDITIONAL", "REWORK", "HOLD"}
        self.cur.execute("SELECT DISTINCT overall_decision FROM quality_inspections")
        found = {row[0] for row in self.cur.fetchall() if row[0]}
        invalid = found - valid
        self.assertEqual(len(invalid), 0, f"Unexpected QC decisions: {invalid}")

    def test_defect_count_non_negative(self):
        self.cur.execute(
            "SELECT COUNT(*) FROM quality_inspections WHERE defect_count < 0"
        )
        bad = self.cur.fetchone()[0]
        self.assertEqual(bad, 0, "Negative defect_count detected")


# ===========================================================================
# Suite 5 – Pipeline Row Presence
# ===========================================================================

class TestPipelineRowPresence(unittest.TestCase):
    """Every dashboard PIPELINE table must contain at least one row."""

    @classmethod
    def setUpClass(cls):
        _skip_if_no_db(cls)
        cls.conn = _get_conn()
        cls.cur = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.cur.close()
        cls.conn.close()

    def test_all_pipeline_tables_have_data(self):
        for pipeline in PIPELINES:
            table = pipeline["table"]
            with self.subTest(pipeline=pipeline["name"]):
                self.cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = self.cur.fetchone()[0]
                self.assertGreater(
                    count, 0,
                    f"Pipeline table '{table}' ({pipeline['name']}) has no rows — run feeders"
                )


# ===========================================================================
# Suite 6 – Data Freshness Layer
# ===========================================================================

class TestDataFreshness(unittest.TestCase):
    """Check that the freshness configuration columns return recent timestamps."""

    FRESHNESS_CONFIG = [
        {"label": "Melting",    "table": "melting_heat_records",  "time_col": "melt_date"},
        {"label": "Casting",    "table": "casting_records",        "time_col": "casting_date"},
        {"label": "Heat Treat", "table": "heat_treatment",         "time_col": "treatment_date"},
        {"label": "Quality",    "table": "quality_inspections",    "time_col": "inspection_date"},
        {"label": "Inventory",  "table": "inventory_movements",    "time_col": "posting_date"},
        {"label": "Maintenance","table": "equipment_maintenance",  "time_col": "planned_start"},
    ]

    @classmethod
    def setUpClass(cls):
        _skip_if_no_db(cls)
        cls.conn = _get_conn()
        cls.cur = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.cur.close()
        cls.conn.close()

    def test_freshness_columns_are_queryable(self):
        for cfg in self.FRESHNESS_CONFIG:
            with self.subTest(label=cfg["label"]):
                try:
                    self.cur.execute(
                        f'SELECT MAX("{cfg["time_col"]}") FROM {cfg["table"]}'
                    )
                    row = self.cur.fetchone()
                    self.assertIsNotNone(row, f"No rows in {cfg['table']}")
                except Exception as exc:
                    self.fail(f"Freshness query failed for {cfg['label']}: {exc}")

    def test_freshness_timestamps_are_not_future(self):
        """
        Feeder scripts generate simulation data with planned future dates,
        so we allow up to 365 days ahead. This just guards against obviously
        corrupt values (e.g. year 9999).
        """
        from datetime import date, datetime, timedelta
        ceiling = date.today() + timedelta(days=366)
        for cfg in self.FRESHNESS_CONFIG:
            with self.subTest(label=cfg["label"]):
                self.cur.execute(
                    f'SELECT MAX("{cfg["time_col"]}") FROM {cfg["table"]}'
                )
                val = self.cur.fetchone()[0]
                if val is None:
                    continue
                # Normalise to date regardless of date vs datetime column type
                if isinstance(val, datetime):
                    val_date = val.date()
                elif isinstance(val, date):
                    val_date = val
                else:
                    continue
                self.assertLessEqual(
                    val_date, ceiling,
                    f"{cfg['label']}: latest timestamp {val_date} is unrealistically far in the future"
                )


# ===========================================================================
# Suite 7 – Production Flow Integrity
# ===========================================================================

class TestProductionFlowIntegrity(unittest.TestCase):
    """Cross-table checks: downstream records must reference valid upstream ones."""

    @classmethod
    def setUpClass(cls):
        _skip_if_no_db(cls)
        cls.conn = _get_conn()
        cls.cur = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.cur.close()
        cls.conn.close()

    def test_casting_heat_numbers_exist_in_melting(self):
        self.cur.execute(
            """
            SELECT COUNT(*)
            FROM casting_records cr
            WHERE cr.heat_number IS NOT NULL
              AND cr.heat_number NOT IN (
                  SELECT heat_number FROM melting_heat_records
              )
            """
        )
        orphans = self.cur.fetchone()[0]
        self.assertEqual(
            orphans, 0,
            f"{orphans} casting_records reference non-existent heat_number in melting_heat_records"
        )

    def test_machining_production_orders_exist(self):
        self.cur.execute(
            """
            SELECT COUNT(*)
            FROM machining_operations mo
            WHERE mo.production_order IS NOT NULL
              AND mo.production_order NOT IN (
                  SELECT production_order FROM production_orders
              )
            """
        )
        orphans = self.cur.fetchone()[0]
        self.assertEqual(
            orphans, 0,
            f"{orphans} machining_operations reference non-existent production_order"
        )

    def test_quality_inspections_reference_valid_materials(self):
        self.cur.execute(
            """
            SELECT COUNT(*)
            FROM quality_inspections qi
            WHERE qi.material_number IS NOT NULL
              AND qi.material_number NOT IN (
                  SELECT material_number FROM material_master
              )
            """
        )
        orphans = self.cur.fetchone()[0]
        self.assertEqual(
            orphans, 0,
            f"{orphans} quality_inspections reference unknown material_number"
        )

    def test_heat_treatment_references_valid_casting_batch(self):
        self.cur.execute(
            """
            SELECT COUNT(*)
            FROM heat_treatment ht
            WHERE ht.casting_batch IS NOT NULL
              AND ht.casting_batch NOT IN (
                  SELECT casting_batch FROM casting_records
              )
            """
        )
        orphans = self.cur.fetchone()[0]
        self.assertEqual(
            orphans, 0,
            f"{orphans} heat_treatment rows reference non-existent casting_batch"
        )

    def test_pour_temperature_never_exceeds_tap_temperature(self):
        """Pour temp must always be <= tap temp (physics)."""
        self.cur.execute(
            """
            SELECT COUNT(*)
            FROM melting_heat_records
            WHERE pour_temperature_c > tap_temperature_c
            """
        )
        bad = self.cur.fetchone()[0]
        self.assertEqual(bad, 0, f"{bad} heats where pour_temp > tap_temp")

    def test_production_order_dates_are_logical(self):
        """planned_end_date must not precede planned_start_date."""
        self.cur.execute(
            """
            SELECT COUNT(*)
            FROM production_orders
            WHERE planned_end_date < planned_start_date
            """
        )
        bad = self.cur.fetchone()[0]
        self.assertEqual(bad, 0, f"{bad} production orders where end < start")

    def test_order_quantities_are_positive(self):
        self.cur.execute(
            "SELECT COUNT(*) FROM production_orders WHERE order_quantity <= 0"
        )
        bad = self.cur.fetchone()[0]
        self.assertEqual(bad, 0, f"{bad} orders with non-positive order_quantity")


# ===========================================================================
# Suite 8 – Inventory & Reorder Snapshot
# ===========================================================================

class TestInventorySnapshot(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _skip_if_no_db(cls)
        cls.conn = _get_conn()
        cls.cur = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.cur.close()
        cls.conn.close()

    def test_latest_stock_query_executes(self):
        self.cur.execute(
            """
            SELECT DISTINCT ON (material_number)
                material_number,
                stock_after,
                posting_date
            FROM inventory_movements
            ORDER BY material_number, posting_date DESC, document_number DESC
            LIMIT 10
            """
        )
        rows = self.cur.fetchall()
        self.assertIsInstance(rows, list)

    def test_reorder_calculation_produces_non_negative_values(self):
        self.cur.execute(
            """
            WITH latest_stock AS (
                SELECT DISTINCT ON (material_number)
                    material_number,
                    stock_after::numeric AS current_stock
                FROM inventory_movements
                ORDER BY material_number, posting_date DESC, document_number DESC
            )
            SELECT
                mm.material_number,
                GREATEST(
                    0,
                    (mm.safety_stock) - COALESCE(ls.current_stock, 0)
                ) AS reorder_qty
            FROM material_master mm
            LEFT JOIN latest_stock ls ON ls.material_number = mm.material_number
            WHERE mm.safety_stock > 0
            LIMIT 20
            """
        )
        rows = self.cur.fetchall()
        for row in rows:
            self.assertGreaterEqual(
                float(row[1] or 0), 0.0,
                f"Negative reorder qty for {row[0]}"
            )

    def test_material_master_safety_stock_non_negative(self):
        self.cur.execute(
            "SELECT COUNT(*) FROM material_master WHERE safety_stock < 0"
        )
        bad = self.cur.fetchone()[0]
        self.assertEqual(bad, 0, "Negative safety_stock found in material_master")

    def test_standard_price_usd_positive(self):
        self.cur.execute(
            "SELECT COUNT(*) FROM material_master WHERE standard_price_usd <= 0"
        )
        bad = self.cur.fetchone()[0]
        self.assertEqual(bad, 0, "Non-positive standard_price_usd in material_master")


# ===========================================================================
# Suite 9 – Control-Tower & Scheduling
# ===========================================================================

class TestControlTowerAndScheduling(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _skip_if_no_db(cls)
        cls.conn = _get_conn()
        cls.cur = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.cur.close()
        cls.conn.close()

    def test_stage_mix_sql_returns_all_statuses(self):
        self.cur.execute(
            """
            SELECT order_status, COUNT(*)
            FROM production_orders
            GROUP BY order_status
            ORDER BY order_status
            """
        )
        rows = self.cur.fetchall()
        statuses = {r[0] for r in rows}
        known = {"CREATED", "RELEASED", "IN_PROCESS", "COMPLETED", "CLOSED"}
        unexpected = statuses - known
        self.assertEqual(
            len(unexpected), 0,
            f"Unexpected order_status values in production_orders: {unexpected}"
        )

    def test_wip_count_query(self):
        self.cur.execute(
            """
            SELECT COUNT(*)
            FROM production_orders
            WHERE order_status IN ('CREATED', 'RELEASED', 'IN_PROCESS')
            """
        )
        wip = self.cur.fetchone()[0]
        self.assertIsInstance(wip, int)
        self.assertGreaterEqual(wip, 0)

    def test_delayed_orders_query(self):
        self.cur.execute(
            """
            SELECT COUNT(*)
            FROM production_orders
            WHERE planned_end_date < CURRENT_DATE
              AND order_status NOT IN ('COMPLETED', 'CLOSED')
            """
        )
        delayed = self.cur.fetchone()[0]
        self.assertGreaterEqual(delayed, 0)

    def test_scheduling_queue_rows_have_expected_columns(self):
        self.cur.execute(
            """
            SELECT
                production_order,
                planned_start_date,
                planned_end_date,
                order_status,
                priority,
                order_quantity,
                (planned_end_date - CURRENT_DATE) AS slack_days
            FROM production_orders
            WHERE order_status IN ('CREATED', 'RELEASED', 'IN_PROCESS')
            ORDER BY priority ASC, planned_end_date ASC
            LIMIT 12
            """
        )
        rows = self.cur.fetchall()
        self.assertIsInstance(rows, list)
        if rows:
            self.assertEqual(len(rows[0]), 7, "Scheduling queue row should have 7 columns")


# ===========================================================================
# Suite 10 – Traceability Chains
# ===========================================================================

class TestTraceabilityChains(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _skip_if_no_db(cls)
        cls.conn = _get_conn()
        cls.cur = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.cur.close()
        cls.conn.close()

    def test_traceability_query_executes(self):
        self.cur.execute(
            """
            SELECT
                po.production_order,
                COALESCE(cr.heat_number, '-'),
                COALESCE(cr.casting_batch, '-'),
                COALESCE(ht.ht_batch_number, '-'),
                po.order_status
            FROM production_orders po
            LEFT JOIN casting_records cr
                ON cr.production_order = po.production_order
            LEFT JOIN heat_treatment ht
                ON ht.production_order = po.production_order
            ORDER BY po.created_date DESC
            LIMIT 15
            """
        )
        rows = self.cur.fetchall()
        self.assertIsInstance(rows, list)

    def test_all_qc_decisions_in_valid_set(self):
        valid = {"ACCEPT", "REJECT", "CONDITIONAL", "REWORK", "HOLD", "PENDING"}
        self.cur.execute(
            "SELECT DISTINCT overall_decision FROM quality_inspections"
        )
        found = {row[0] for row in self.cur.fetchall() if row[0]}
        invalid = found - valid
        self.assertEqual(len(invalid), 0, f"Invalid QC decisions: {invalid}")

    def test_machining_quality_status_valid(self):
        valid = {"PASS", "FAIL", "REWORK", "PENDING", "IN_PROCESS"}
        self.cur.execute(
            "SELECT DISTINCT quality_status FROM machining_operations"
        )
        found = {row[0] for row in self.cur.fetchall() if row[0]}
        invalid = found - valid
        self.assertEqual(len(invalid), 0, f"Invalid machining quality_status: {invalid}")

    def test_heat_treatment_quality_status_valid(self):
        valid = {"APPROVED", "REJECTED", "REWORK", "PENDING", "IN_PROCESS"}
        self.cur.execute(
            "SELECT DISTINCT quality_status FROM heat_treatment"
        )
        found = {row[0] for row in self.cur.fetchall() if row[0]}
        invalid = found - valid
        self.assertEqual(len(invalid), 0, f"Invalid HT quality_status: {invalid}")


# ===========================================================================
# Suite 11 – Read-Only Enforcement (query_foundry_db tool)
# ===========================================================================

class TestReadOnlyEnforcement(unittest.TestCase):
    """The chatbot's query_foundry_db tool must reject write statements."""

    @classmethod
    def setUpClass(cls):
        _skip_if_no_db(cls)
        try:
            from core.tools import query_foundry_db
            cls.tool = query_foundry_db
        except ImportError as exc:
            raise unittest.SkipTest(f"Cannot import query_foundry_db: {exc}")

    def _run(self, sql: str) -> str:
        return self.tool.run(sql)

    def test_select_is_allowed(self):
        result = self._run("SELECT COUNT(*) FROM production_orders LIMIT 1")
        self.assertNotIn("Only SELECT", result)
        self.assertNotIn("❌", result[:10])

    def test_update_is_blocked(self):
        result = self._run(
            "UPDATE production_orders SET order_status = 'CLOSED' WHERE 1=1"
        )
        self.assertIn("❌", result)

    def test_delete_is_blocked(self):
        result = self._run("DELETE FROM casting_records WHERE 1=1")
        self.assertIn("❌", result)

    def test_insert_is_blocked(self):
        result = self._run(
            "INSERT INTO production_orders (production_order) VALUES ('TEST')"
        )
        self.assertIn("❌", result)

    def test_drop_is_blocked(self):
        result = self._run("DROP TABLE casting_records")
        self.assertIn("❌", result)

    def test_truncate_is_blocked(self):
        result = self._run("TRUNCATE TABLE equipment_maintenance")
        self.assertIn("❌", result)

    def test_select_without_limit_gets_limit_appended(self):
        result = self._run("SELECT heat_number FROM melting_heat_records")
        # Should succeed (not blocked) — tool auto-appends LIMIT 50
        self.assertNotIn("❌ Only SELECT", result)

    def test_result_is_formatted_table(self):
        result = self._run("SELECT heat_number FROM melting_heat_records LIMIT 3")
        self.assertIn("heat_number", result.lower())


# ===========================================================================
# Suite 12 – Agent Tool → DB Round-trip
# ===========================================================================

class TestAgentToolRoundTrip(unittest.TestCase):
    """Verify chatbot natural-language queries actually return DB data end-to-end."""

    @classmethod
    def setUpClass(cls):
        _skip_if_no_db(cls)
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise unittest.SkipTest("GROQ_API_KEY not set — skipping live brain tests")
        try:
            from core.brain import AgentBrain
            cls.brain = AgentBrain()
        except Exception as exc:
            raise unittest.SkipTest(f"AgentBrain init failed: {exc}")

    def _ask(self, query: str) -> str:
        start = time.time()
        result = self.brain.ask(query)
        elapsed = time.time() - start
        self.assertLess(elapsed, 30, f"Query took > 30s: {query!r}")
        return result

    def test_average_tap_temperature_query(self):
        result = self._ask("What is the average tap temperature?")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 5)
        # The answer should contain a temperature-like number
        import re
        temps = re.findall(r'\d{3,4}(?:\.\d+)?', result)
        self.assertTrue(
            len(temps) > 0,
            f"No temperature value found in response: {result[:200]}"
        )

    def test_production_order_count_query(self):
        result = self._ask("How many production orders are there?")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 5)

    def test_rejected_heats_query(self):
        result = self._ask("How many rejected heats do we have?")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 5)

    def test_latest_inventory_movements_query(self):
        result = self._ask("Show me the latest inventory movements")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 5)

    def test_db_result_does_not_contain_sql_error(self):
        result = self._ask("What is the average casting yield?")
        self.assertNotIn("DB query failed", result)
        self.assertNotIn("syntax error", result.lower())


# ===========================================================================
# Runner
# ===========================================================================

def main():
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    for cls in [
        TestDBConnectivity,
        TestSchemaIntegrity,
        TestDashboardHelpers,
        TestKPIQueryAccuracy,
        TestPipelineRowPresence,
        TestDataFreshness,
        TestProductionFlowIntegrity,
        TestInventorySnapshot,
        TestControlTowerAndScheduling,
        TestTraceabilityChains,
        TestReadOnlyEnforcement,
        TestAgentToolRoundTrip,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2, failfast=False)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
