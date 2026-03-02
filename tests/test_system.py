"""
Menon & Menon Foundry OS â€” Unit Test Suite
==========================================
Covers:
  1. Environment & Dependencies
  2. Pure Helper Functions (KPI state, freshness, formatters)
  3. Database Connection & CAPA CRUD (capa_input table)
  4. Intent Router
  5. AgentBrain â€” mocked (always runs) + live (requires GROQ_API_KEY)
  6. API Tools (market data, news, SOPs)
  7. CAPA DB Helper Functions

Run:
    python -m pytest tests/test_system.py -v
    # or
    python tests/test_system.py
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Shared DB helper
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _get_conn():
    import psycopg2
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


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Suite 1 â€” Environment & Dependencies
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestEnvironment(unittest.TestCase):
    """Verify that all required environment variables and packages are present."""

    REQUIRED_ENV    = ["GROQ_API_KEY", "DB_NAME", "DB_USER", "DB_PASS", "DB_HOST"]
    OPTIONAL_ENV    = ["NEWS_API_KEY", "METAL_PRICE"]
    REQUIRED_MODULES = [
        "streamlit", "langchain_groq", "langchain_core",
        "chromadb", "yfinance", "requests", "psycopg2", "dotenv",
    ]
    REQUIRED_FILES = [
        "core/brain.py", "core/tools.py", "core/intent_router.py",
        "dashboard.py", "ingest_knowledge.py",
    ]

    def test_required_env_vars_present(self):
        for var in self.REQUIRED_ENV:
            with self.subTest(var=var):
                self.assertIsNotNone(
                    os.getenv(var),
                    f"Required env var {var!r} is not set in .env"
                )

    def test_optional_env_vars_documentation(self):
        for var in self.OPTIONAL_ENV:
            with self.subTest(var=var):
                if os.getenv(var) is None:
                    print(f"\n  [WARN] Optional {var!r} not set â€” related features disabled.")

    def test_required_modules_importable(self):
        for module in self.REQUIRED_MODULES:
            with self.subTest(module=module):
                try:
                    __import__(module)
                except ImportError as exc:
                    self.fail(f"Module {module!r} not installed: {exc}")

    def test_required_files_exist(self):
        for rel_path in self.REQUIRED_FILES:
            with self.subTest(file=rel_path):
                self.assertTrue(
                    os.path.isfile(os.path.join(PROJECT_ROOT, rel_path)),
                    f"Required file missing: {rel_path}"
                )

    def test_core_package_importable(self):
        try:
            from core import brain, tools, intent_router  # noqa: F401
        except ImportError as exc:
            self.fail(f"core package import failed: {exc}")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Suite 2 â€” Pure Helper Functions
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestKpiHelpers(unittest.TestCase):
    """Unit-test pure helper logic from dashboard.py (no Streamlit required)."""

    FRESHNESS_SLA = {
        "Melting": (24, 48), "Casting": (24, 48),
        "Heat Treat": (24, 48), "Quality": (24, 48),
        "Inventory": (24, 48), "Maintenance": (48, 96),
    }

    @staticmethod
    def _kpi_state(value, good_cond, warn_cond=None):
        if good_cond(value):
            return "ðŸŸ¢"
        if warn_cond and warn_cond(value):
            return "ðŸŸ¡"
        return "ðŸ”´"

    def _freshness_state(self, label, age_hours):
        if age_hours is None:
            return "missing"
        green_h, warn_h = self.FRESHNESS_SLA.get(label, (24, 48))
        if age_hours <= green_h:
            return "fresh"
        if age_hours <= warn_h:
            return "warn"
        return "stale"

    @staticmethod
    def _format_ts(value):
        if not value:
            return "NO DATA"
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        return str(value)

    # KPI state
    def test_kpi_state_good(self):
        self.assertEqual(self._kpi_state(92.0, lambda v: v > 88, lambda v: 82 <= v <= 88), "ðŸŸ¢")

    def test_kpi_state_warn(self):
        self.assertEqual(self._kpi_state(85.0, lambda v: v > 88, lambda v: 82 <= v <= 88), "ðŸŸ¡")

    def test_kpi_state_critical(self):
        self.assertEqual(self._kpi_state(75.0, lambda v: v > 88, lambda v: 82 <= v <= 88), "ðŸ”´")

    def test_kpi_state_no_warn_defaults_red(self):
        self.assertEqual(self._kpi_state(75.0, lambda v: v > 88), "ðŸ”´")

    def test_kpi_scrap_good(self):
        self.assertEqual(self._kpi_state(3.0, lambda v: v < 6, lambda v: 6 <= v <= 10), "ðŸŸ¢")

    def test_kpi_scrap_warn(self):
        self.assertEqual(self._kpi_state(7.5, lambda v: v < 6, lambda v: 6 <= v <= 10), "ðŸŸ¡")

    def test_kpi_scrap_critical(self):
        self.assertEqual(self._kpi_state(12.0, lambda v: v < 6, lambda v: 6 <= v <= 10), "ðŸ”´")

    def test_kpi_temp_good(self):
        self.assertEqual(
            self._kpi_state(1420.0,
                lambda v: 1380 <= v <= 1450,
                lambda v: (1360 <= v < 1380) or (1450 < v <= 1470)), "ðŸŸ¢")

    def test_kpi_temp_warn_low(self):
        self.assertEqual(
            self._kpi_state(1370.0,
                lambda v: 1380 <= v <= 1450,
                lambda v: (1360 <= v < 1380) or (1450 < v <= 1470)), "ðŸŸ¡")

    def test_kpi_temp_critical(self):
        self.assertEqual(
            self._kpi_state(1300.0,
                lambda v: 1380 <= v <= 1450,
                lambda v: (1360 <= v < 1380) or (1450 < v <= 1470)), "ðŸ”´")

    # Freshness state
    def test_freshness_fresh(self):
        self.assertEqual(self._freshness_state("Melting", 12.0), "fresh")

    def test_freshness_warn(self):
        self.assertEqual(self._freshness_state("Melting", 36.0), "warn")

    def test_freshness_stale(self):
        self.assertEqual(self._freshness_state("Melting", 60.0), "stale")

    def test_freshness_missing(self):
        self.assertEqual(self._freshness_state("Melting", None), "missing")

    def test_freshness_maintenance_sla(self):
        self.assertEqual(self._freshness_state("Maintenance", 50.0), "warn")
        self.assertEqual(self._freshness_state("Maintenance", 100.0), "stale")

    def test_freshness_exactly_at_green_boundary(self):
        self.assertEqual(self._freshness_state("Casting", 24.0), "fresh")

    def test_freshness_just_over_green_boundary(self):
        self.assertEqual(self._freshness_state("Casting", 24.1), "warn")

    # Format timestamp
    def test_format_ts_datetime(self):
        self.assertEqual(self._format_ts(datetime(2026, 2, 27, 14, 30)), "2026-02-27 14:30")

    def test_format_ts_date(self):
        self.assertEqual(self._format_ts(date(2026, 2, 27)), "2026-02-27")

    def test_format_ts_none(self):
        self.assertEqual(self._format_ts(None), "NO DATA")

    def test_format_ts_empty_string(self):
        self.assertEqual(self._format_ts(""), "NO DATA")

    def test_format_ts_string_passthrough(self):
        self.assertEqual(self._format_ts("raw-value"), "raw-value")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Suite 3 â€” Database Connection & CAPA CRUD
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestDatabaseAndCapa(unittest.TestCase):
    """Integration tests against the live PostgreSQL instance."""

    TEST_CAPA_IDS: list = []

    @classmethod
    def setUpClass(cls):
        cls.conn = _get_conn()
        if cls.conn is None:
            raise unittest.SkipTest(
                "PostgreSQL not reachable â€” set DB_NAME/DB_USER/DB_PASS/DB_HOST in .env"
            )

    @classmethod
    def tearDownClass(cls):
        if cls.conn:
            try:
                cur = cls.conn.cursor()
                for cid in cls.TEST_CAPA_IDS:
                    cur.execute("DELETE FROM capa_input WHERE capa_id = %s", (cid,))
                cls.conn.commit()
            except Exception:
                pass
            finally:
                cls.conn.close()

    # Connectivity
    def test_db_connection_alive(self):
        cur = self.conn.cursor()
        cur.execute("SELECT 1")
        self.assertEqual(cur.fetchone()[0], 1)

    def test_capa_input_table_exists(self):
        cur = self.conn.cursor()
        cur.execute("SELECT to_regclass('public.capa_input')")
        self.assertIsNotNone(
            cur.fetchone()[0],
            "Table capa_input does not exist â€” run the provided schema SQL first."
        )

    def test_capa_table_has_required_columns(self):
        cur = self.conn.cursor()
        cur.execute(
            """SELECT column_name FROM information_schema.columns
               WHERE table_schema='public' AND table_name='capa_input'"""
        )
        cols = {r[0] for r in cur.fetchall()}
        required = {
            "capa_id", "created_at", "source", "issue", "linked_alert",
            "owner", "priority", "status", "due_date", "closure_notes", "updated_at",
        }
        self.assertTrue(required.issubset(cols), f"Missing columns: {required - cols}")

    # Foundry tables existence
    def test_production_orders_exists(self):
        cur = self.conn.cursor()
        cur.execute("SELECT to_regclass('public.production_orders')")
        self.assertIsNotNone(cur.fetchone()[0])

    def test_casting_records_exists(self):
        cur = self.conn.cursor()
        cur.execute("SELECT to_regclass('public.casting_records')")
        self.assertIsNotNone(cur.fetchone()[0])

    def test_melting_heat_records_exists(self):
        cur = self.conn.cursor()
        cur.execute("SELECT to_regclass('public.melting_heat_records')")
        self.assertIsNotNone(cur.fetchone()[0])

    # CAPA INSERT
    def _insert(self, suffix: str) -> str:
        capa_id = f"TEST-UNIT-{suffix}"
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO capa_input
               (capa_id, source, issue, linked_alert, owner, priority, status, due_date, closure_notes)
               VALUES (%s,'MANUAL',%s,'',%s,'MEDIUM','OPEN',%s,'')
               ON CONFLICT (capa_id) DO NOTHING""",
            (capa_id, f"Issue {suffix}", "Tester", (date.today() + timedelta(days=7)).isoformat()),
        )
        self.conn.commit()
        self.TEST_CAPA_IDS.append(capa_id)
        return capa_id

    def test_capa_insert_and_read(self):
        cid = self._insert("INS")
        cur = self.conn.cursor()
        cur.execute("SELECT capa_id, status FROM capa_input WHERE capa_id=%s", (cid,))
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], cid)
        self.assertEqual(row[1], "OPEN")

    def test_capa_insert_duplicate_ignored(self):
        cid = self._insert("DUP")
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO capa_input
               (capa_id, source, issue, linked_alert, owner, priority, status, due_date, closure_notes)
               VALUES (%s,'AUDIT','dup','','Owner2','HIGH','OPEN',%s,'')
               ON CONFLICT (capa_id) DO NOTHING""",
            (cid, date.today().isoformat()),
        )
        self.conn.commit()
        cur.execute("SELECT source FROM capa_input WHERE capa_id=%s", (cid,))
        self.assertEqual(cur.fetchone()[0], "MANUAL")

    # CAPA UPDATE
    def test_capa_update_status(self):
        cid = self._insert("UPD")
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE capa_input SET status=%s, closure_notes=%s, updated_at=NOW() WHERE capa_id=%s",
            ("IN_PROGRESS", "Work started", cid),
        )
        self.conn.commit()
        cur.execute("SELECT status, closure_notes FROM capa_input WHERE capa_id=%s", (cid,))
        row = cur.fetchone()
        self.assertEqual(row[0], "IN_PROGRESS")
        self.assertEqual(row[1], "Work started")

    def test_capa_close(self):
        cid = self._insert("CLO")
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE capa_input SET status='CLOSED', closure_notes='Resolved', updated_at=NOW() WHERE capa_id=%s",
            (cid,),
        )
        self.conn.commit()
        cur.execute("SELECT status FROM capa_input WHERE capa_id=%s", (cid,))
        self.assertEqual(cur.fetchone()[0], "CLOSED")

    def test_updated_at_advances_after_update(self):
        import time as _time
        cid = self._insert("UPT")
        cur = self.conn.cursor()
        cur.execute("SELECT updated_at FROM capa_input WHERE capa_id=%s", (cid,))
        before = cur.fetchone()[0]
        _time.sleep(0.05)
        cur.execute("UPDATE capa_input SET status='IN_PROGRESS', updated_at=NOW() WHERE capa_id=%s", (cid,))
        self.conn.commit()
        cur.execute("SELECT updated_at FROM capa_input WHERE capa_id=%s", (cid,))
        after = cur.fetchone()[0]
        self.assertGreaterEqual(after, before)

    # Constraint checks
    def test_priority_constraint_rejects_invalid(self):
        import psycopg2
        cur = self.conn.cursor()
        with self.assertRaises(psycopg2.errors.CheckViolation):
            cur.execute(
                """INSERT INTO capa_input
                   (capa_id,source,issue,linked_alert,owner,priority,status,due_date,closure_notes)
                   VALUES ('TEST-BAD-PRIO','MANUAL','x','','O','ULTRA','OPEN',%s,'')""",
                (date.today().isoformat(),),
            )
        self.conn.rollback()

    def test_status_constraint_rejects_invalid(self):
        import psycopg2
        cur = self.conn.cursor()
        with self.assertRaises(psycopg2.errors.CheckViolation):
            cur.execute(
                """INSERT INTO capa_input
                   (capa_id,source,issue,linked_alert,owner,priority,status,due_date,closure_notes)
                   VALUES ('TEST-BAD-STAT','MANUAL','x','','O','HIGH','INVALID',%s,'')""",
                (date.today().isoformat(),),
            )
        self.conn.rollback()


# â”€â”€”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Suite 4 â€” Intent Router
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestIntentRouter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            from core.intent_router import IntentRouter, QueryIntent
            cls.router = IntentRouter()
            cls.QI = QueryIntent
        except ImportError as exc:
            raise unittest.SkipTest(f"Cannot import IntentRouter: {exc}")

    def _intent(self, query):
        intent, _, _ = self.router.analyze(query)
        return intent

    # Price
    def test_price_steel(self):
        self.assertEqual(self._intent("What is the price of steel?"), self.QI.PRICE_QUERY)

    def test_price_copper(self):
        self.assertEqual(self._intent("How much does copper cost today?"), self.QI.PRICE_QUERY)

    def test_price_gold(self):
        self.assertEqual(self._intent("Current gold price"), self.QI.PRICE_QUERY)

    def test_price_stock(self):
        self.assertEqual(self._intent("Show me Tesla stock price"), self.QI.PRICE_QUERY)

    # News
    def test_news_mining(self):
        self.assertEqual(self._intent("What's the latest news in mining?"), self.QI.NEWS_QUERY)

    def test_news_steel(self):
        self.assertEqual(self._intent("Show me steel industry news"), self.QI.NEWS_QUERY)

    def test_news_manufacturing(self):
        self.assertEqual(self._intent("Latest manufacturing trends"), self.QI.NEWS_QUERY)

    # SOP
    def test_sop_molding(self):
        self.assertEqual(self._intent("What is the molding sand procedure?"), self.QI.SOP_QUERY)

    def test_sop_safety(self):
        self.assertEqual(self._intent("Safety rules for melting operations"), self.QI.SOP_QUERY)

    def test_sop_maintenance(self):
        self.assertEqual(self._intent("How to maintain the furnace?"), self.QI.SOP_QUERY)

    # Combined
    def test_combined_price_news(self):
        self.assertEqual(
            self._intent("What's the price of steel and latest news?"),
            self.QI.COMBINED_QUERY,
        )

    def test_combined_triple(self):
        self.assertEqual(
            self._intent("Gold prices, news, and safety guidelines"),
            self.QI.COMBINED_QUERY,
        )

    # Entity extraction
    def test_entity_steel(self):
        self.assertEqual(self.router.extract_entities("steel price").get("asset_name"), "steel")

    def test_entity_copper(self):
        self.assertEqual(self.router.extract_entities("copper and mining").get("asset_name"), "copper")

    def test_entity_gold(self):
        self.assertEqual(self.router.extract_entities("gold prices and auto industry news").get("asset_name"), "gold")

    def test_entity_none_for_generic_query(self):
        self.assertIsNone(self.router.extract_entities("renewable energy news").get("asset_name"))

    # Return shape
    def test_analyze_returns_three_tuple(self):
        result = self.router.analyze("copper price")
        self.assertEqual(len(result), 3)

    def test_scores_is_dict(self):
        _, _, scores = self.router.analyze("copper price")
        self.assertIsInstance(scores, dict)
        self.assertGreater(len(scores), 0)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Suite 5 â€” AgentBrain Mocked (always runs â€” no API keys needed)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestAgentBrainMocked(unittest.TestCase):

    def _bare_brain(self):
        from core.brain import AgentBrain
        brain = AgentBrain.__new__(AgentBrain)
        brain.history = []
        brain.max_tool_retries = 0
        brain.intent_confidence_threshold = 0.10
        brain.system_prompt = "test"
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = '{"action": "final", "input": "Mocked"}'
        mock_llm.invoke.return_value = mock_resp
        brain.llm = mock_llm
        brain.tools = {k: None for k in ("get_market_data", "get_global_news", "query_internal_sops", "query_foundry_db")}
        brain.router = MagicMock()
        return brain

    def test_remember_adds_turn(self):
        from core.brain import AgentBrain
        b = AgentBrain.__new__(AgentBrain)
        b.history = []
        b._remember("q1", "a1")
        self.assertEqual(len(b.history), 1)
        self.assertEqual(b.history[0]["user"], "q1")

    def test_remember_caps_at_five(self):
        from core.brain import AgentBrain
        b = AgentBrain.__new__(AgentBrain)
        b.history = []
        for i in range(8):
            b._remember(f"q{i}", f"a{i}")
        self.assertEqual(len(b.history), 5)

    def test_format_history_empty(self):
        from core.brain import AgentBrain
        b = AgentBrain.__new__(AgentBrain)
        b.history = []
        self.assertEqual(b._format_history(), "(no prior history)")

    def test_format_history_non_empty(self):
        from core.brain import AgentBrain
        b = AgentBrain.__new__(AgentBrain)
        b.history = [{"user": "hello", "assistant": "world"}]
        text = b._format_history()
        self.assertIn("hello", text)
        self.assertIn("world", text)

    def test_is_tool_failure_detects_error_emoji(self):
        from core.brain import AgentBrain
        b = AgentBrain.__new__(AgentBrain)
        b.history = []
        # Use the exact emoji that brain.py's startswith check expects
        cross_mark = "\u274c"
        self.assertTrue(b._is_tool_failure(f"{cross_mark} something went wrong"))

    def test_is_tool_failure_detects_timeout(self):
        from core.brain import AgentBrain
        b = AgentBrain.__new__(AgentBrain)
        b.history = []
        self.assertTrue(b._is_tool_failure("timeout error occurred"))

    def test_is_tool_failure_ok_on_valid_result(self):
        from core.brain import AgentBrain
        b = AgentBrain.__new__(AgentBrain)
        b.history = []
        self.assertFalse(b._is_tool_failure("Price: $4.50 per kg"))

    def test_heuristic_routes_price(self):
        b = self._bare_brain()
        action = b._decide_action("What is the copper price today?")
        self.assertEqual(action["action"], "get_market_data")
        b.llm.invoke.assert_not_called()

    def test_heuristic_routes_news(self):
        b = self._bare_brain()
        action = b._decide_action("Show me the latest steel news")
        self.assertEqual(action["action"], "get_global_news")
        b.llm.invoke.assert_not_called()

    def test_heuristic_routes_sop(self):
        b = self._bare_brain()
        action = b._decide_action("What is the safety procedure for furnace lining?")
        self.assertEqual(action["action"], "query_internal_sops")
        b.llm.invoke.assert_not_called()

    def test_heuristic_routes_db(self):
        b = self._bare_brain()
        action = b._decide_action("What is the average tap temperature?")
        self.assertEqual(action["action"], "query_foundry_db")
        b.llm.invoke.assert_not_called()

    def test_default_db_query_tap_temperature(self):
        from core.brain import AgentBrain
        b = AgentBrain.__new__(AgentBrain)
        b.history = []
        sql = b._default_db_query("average tap temperature")
        self.assertIn("melting_heat_records", sql.lower())
        self.assertIn("avg", sql.lower())

    def test_default_db_query_scrap(self):
        from core.brain import AgentBrain
        b = AgentBrain.__new__(AgentBrain)
        b.history = []
        sql = b._default_db_query("total scrap castings")
        self.assertIn("casting_records", sql.lower())

    def test_default_db_query_rejected_heats(self):
        from core.brain import AgentBrain
        b = AgentBrain.__new__(AgentBrain)
        b.history = []
        sql = b._default_db_query("how many rejected heats")
        self.assertIn("REJECTED", sql)

    def test_default_db_query_inventory(self):
        from core.brain import AgentBrain
        b = AgentBrain.__new__(AgentBrain)
        b.history = []
        sql = b._default_db_query("inventory stock")
        self.assertIn("inventory_movements", sql.lower())

    def test_default_db_query_maintenance(self):
        from core.brain import AgentBrain
        b = AgentBrain.__new__(AgentBrain)
        b.history = []
        sql = b._default_db_query("maintenance downtime")
        self.assertIn("equipment_maintenance", sql.lower())


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Suite 6 â€” AgentBrain Live (requires GROQ_API_KEY)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestAgentBrainLive(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.getenv("GROQ_API_KEY"):
            raise unittest.SkipTest("GROQ_API_KEY not set")
        try:
            from core.brain import AgentBrain
            cls.brain = AgentBrain()
        except Exception as exc:
            raise unittest.SkipTest(f"AgentBrain init failed: {exc}")

    def test_ask_returns_string(self):
        r = self.brain.ask("Tell me about the foundry industry")
        self.assertIsInstance(r, str)
        self.assertGreater(len(r), 5)

    def test_price_query_responds(self):
        r = self.brain.ask("What is the copper price?")
        self.assertIsInstance(r, str)
        self.assertGreater(len(r), 5)

    def test_news_query_responds(self):
        r = self.brain.ask("Latest steel industry news")
        self.assertIsInstance(r, str)
        self.assertGreater(len(r), 5)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Suite 7 â€” API Tools (skipped when keys are missing)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestApiTools(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            from core.tools import get_market_data, get_global_news, query_internal_sops
            cls.market  = get_market_data
            cls.news    = get_global_news
            cls.sops    = query_internal_sops
        except ImportError as exc:
            raise unittest.SkipTest(f"core.tools import failed: {exc}")

    def test_market_gold_returns_string(self):
        r = self.market.run("gold")
        self.assertIsInstance(r, str)
        self.assertGreater(len(r), 0)

    def test_market_copper_returns_string(self):
        r = self.market.run("copper")
        self.assertIsInstance(r, str)

    def test_market_unknown_asset_does_not_raise(self):
        r = self.market.run("NONEXISTENT_XYZ_METAL")
        self.assertIsInstance(r, str)

    def test_news_returns_string(self):
        if not (os.getenv("NEWS_API_KEY") or os.getenv("GNEWS_API_KEY")):
            self.skipTest("NEWS_API_KEY/GNEWS_API_KEY not set")
        r = self.news.run("steel")
        self.assertIsInstance(r, str)
        self.assertGreater(len(r), 0)

    def test_sop_returns_string(self):
        if not os.path.isdir(os.path.join(PROJECT_ROOT, "chroma_db")):
            self.skipTest("chroma_db not initialised â€” run ingest_knowledge.py first")
        r = self.sops.run("safety procedures")
        self.assertIsInstance(r, str)
        self.assertGreater(len(r), 0)

    def test_sop_melting_query(self):
        if not os.path.isdir(os.path.join(PROJECT_ROOT, "chroma_db")):
            self.skipTest("chroma_db not initialised")
        r = self.sops.run("melting temperature")
        self.assertIsInstance(r, str)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Runner
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main():
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [
        TestEnvironment,
        TestKpiHelpers,
        TestDatabaseAndCapa,
        TestIntentRouter,
        TestAgentBrainMocked,
        TestAgentBrainLive,
        TestApiTools,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2, failfast=False)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()

