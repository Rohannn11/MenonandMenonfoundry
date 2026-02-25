"""
foundry_config.py  –  Shared constants for all feeder scripts.
Every feeder imports from here so a single source of truth is maintained.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── PostgreSQL Connection ────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "foundry"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS", ""),
    "port":     int(os.getenv("DB_PORT", 5432)),
}

# ─── Plants & fixed reference data ───────────────────────────
PLANTS              = ["PLT001", "PLT002"]
SHIFTS              = ["A", "B", "C"]
OPERATORS           = [f"OPR{i:03d}" for i in range(1, 31)]
SUPERVISORS         = [f"SUP{i:02d}" for i in range(1, 8)]
INSPECTORS          = [f"INS{i:03d}" for i in range(1, 11)]
TECHNICIANS         = [f"TECH{i:03d}" for i in range(1, 16)]
USERS               = [f"USR{i:03d}" for i in range(1, 16)]
CUSTOMERS           = [f"CUST{i:03d}" for i in range(1, 21)]
VENDORS             = [f"VND{i:03d}" for i in range(1, 11)]

# ─── Material Master (finite, known set) ─────────────────────
# Raw materials
RAW_MATERIALS = {
    "MAT001": ("Pig Iron Grade P1",          "KG",  0.42,  "RM-IRON",  "SL-01"),
    "MAT002": ("Steel Scrap Grade 1",        "KG",  0.18,  "RM-SCRAP", "SL-01"),
    "MAT003": ("Steel Scrap Grade 2",        "KG",  0.12,  "RM-SCRAP", "SL-01"),
    "MAT004": ("Cast Iron Returns",          "KG",  0.05,  "RM-IRON",  "SL-02"),
    "MAT005": ("Carbon Raiser",              "KG",  1.20,  "RM-ADD",   "SL-02"),
    "MAT006": ("Ferrosilicon FeSi75",        "KG",  1.85,  "RM-ADD",   "SL-02"),
    "MAT007": ("Ferromanganese FeMn78",      "KG",  2.10,  "RM-ADD",   "SL-02"),
    "MAT008": ("Inoculant FeSi75+Sr",        "KG",  4.50,  "RM-INOC",  "SL-03"),
    "MAT009": ("Inoculant Bi-based",         "KG",  6.80,  "RM-INOC",  "SL-03"),
    "MAT010": ("Silica Sand AFS55",          "KG",  0.08,  "RM-SAND",  "SL-04"),
    "MAT011": ("Chromite Sand",              "KG",  0.28,  "RM-SAND",  "SL-04"),
    "MAT012": ("Bentonite Binder",           "KG",  0.35,  "RM-BIND",  "SL-04"),
    "MAT013": ("Alkaline Phenolic Resin",    "KG",  2.20,  "RM-BIND",  "SL-04"),
    "MAT014": ("Coal Dust Additive",         "KG",  0.15,  "RM-ADD",   "SL-04"),
    "MAT015": ("Chromium Additive",          "KG",  8.50,  "RM-ADD",   "SL-02"),
}

# Finished goods (and their properties)
FINISHED_GOODS = {
    #  mat_id: (description, unit, price, product_type, alloy, bom_number)
    "MAT022": ("Engine Block FG - GG25 Type A", "EA", 420.0, "ENGINE_BLOCK",   "GG25", "BOM001"),
    "MAT023": ("Engine Block FG - GG30 Type B", "EA", 465.0, "ENGINE_BLOCK",   "GG30", "BOM002"),
    "MAT024": ("Engine Block FG - GG30 Type C", "EA", 490.0, "ENGINE_BLOCK",   "GG30", "BOM003"),
    "MAT025": ("Cylinder Head FG - GG25 4-Cyl", "EA", 210.0, "CYLINDER_HEAD",  "GG25", "BOM004"),
    "MAT026": ("Cylinder Head FG - GG30 6-Cyl", "EA", 285.0, "CYLINDER_HEAD",  "GG30", "BOM005"),
    "MAT027": ("Cylinder Liner FG - GG30 78mm", "EA",  95.0, "CYLINDER_LINER", "GG30", "BOM006"),
    "MAT028": ("Cylinder Liner FG - GG40 82mm", "EA", 110.0, "CYLINDER_LINER", "GG40", "BOM007"),
}

# Consumable / spare part materials referenced in machining & maintenance
TOOL_MATERIALS  = ["MAT029","MAT030","MAT031","MAT032","MAT033"]
SPARE_MATERIALS = ["MAT038","MAT039","MAT040","MAT041","MAT042"]

# ─── Equipment (finite, fixed set) ───────────────────────────
EQUIPMENT = {
    "EQ-IF01":  ("INDUCTION_FURNACE",       "Induction Furnace 10T",       "PLT001","WC-MELT", "PM02"),
    "EQ-IF02":  ("INDUCTION_FURNACE",       "Induction Furnace 12T",       "PLT001","WC-MELT", "PM02"),
    "EQ-CUP1":  ("CUPOLA_FURNACE",          "Cupola Furnace 8T/hr",        "PLT001","WC-MELT", "PM02"),
    "EQ-ML01":  ("MOLDING_LINE",            "Green Sand Molding Line 1",   "PLT001","WC-MOLD", "PM01"),
    "EQ-ML02":  ("MOLDING_LINE",            "Green Sand Molding Line 2",   "PLT001","WC-MOLD", "PM01"),
    "EQ-ML03":  ("MOLDING_LINE",            "Resin Sand Molding Line",     "PLT001","WC-MOLD", "PM01"),
    "EQ-HT01":  ("HEAT_TREAT_FURNACE",      "Car Bottom Furnace 1",        "PLT001","WC-HT",   "PM01"),
    "EQ-HT02":  ("HEAT_TREAT_FURNACE",      "Car Bottom Furnace 2",        "PLT001","WC-HT",   "PM01"),
    "EQ-BM01":  ("BORING_MILL",             "Horizontal Boring Mill 1",    "PLT002","WC-BM",   "PM02"),
    "EQ-BM02":  ("BORING_MILL",             "Horizontal Boring Mill 2",    "PLT002","WC-BM",   "PM02"),
    "EQ-CNC01": ("CNC_MACHINING_CENTER",    "CNC Machining Center 1",      "PLT002","WC-CNC",  "PM01"),
    "EQ-CNC02": ("CNC_MACHINING_CENTER",    "CNC Machining Center 2",      "PLT002","WC-CNC",  "PM01"),
    "EQ-TN01":  ("CNC_LATHE",              "CNC Lathe 1",                  "PLT002","WC-TN",   "PM01"),
    "EQ-TN02":  ("CNC_LATHE",              "CNC Lathe 2",                  "PLT002","WC-TN",   "PM01"),
    "EQ-HN01":  ("HONING_MACHINE",          "Sunnen Honing Machine 1",     "PLT002","WC-HN",   "PM01"),
    "EQ-HN02":  ("HONING_MACHINE",          "Sunnen Honing Machine 2",     "PLT002","WC-HN",   "PM01"),
    "EQ-GR01":  ("SURFACE_GRINDER",         "Surface Grinder",             "PLT002","WC-GR",   "PM01"),
    "EQ-GR02":  ("CYLINDRICAL_GRINDER",     "Cylindrical Grinder",         "PLT002","WC-GR",   "PM01"),
    "EQ-CR01":  ("OVERHEAD_CRANE",          "30T Overhead Crane",          "PLT001","WC-CAST",  "PM03"),
    "EQ-SP01":  ("SHOT_BLAST",              "Shot Blast Machine",          "PLT001","WC-CLEAN", "PM01"),
}

# ─── Furnaces ─────────────────────────────────────────────────
MELT_FURNACES = {
    "FUR-IF01": ("INDUCTION", 10000),
    "FUR-IF02": ("INDUCTION", 12000),
    "FUR-CUP1": ("CUPOLA",     8000),
}
HT_FURNACES = {
    "HTFUR-01": "CAR_BOTTOM",
    "HTFUR-02": "CAR_BOTTOM",
    "HTFUR-03": "PIT",
}

# ─── Alloy chemistry windows ──────────────────────────────────
ALLOY_SPEC = {
    # alloy → (C_lo, C_hi, Si_lo, Si_hi, Mn_lo, Mn_hi, P_max, S_max, Cr_max, HB_lo, HB_hi, UTS_lo, UTS_hi)
    "GG25": (3.25, 3.55, 1.80, 2.40, 0.50, 0.80, 0.15, 0.10, 0.05, 160, 210, 220, 280),
    "GG30": (3.10, 3.40, 1.80, 2.30, 0.60, 0.90, 0.12, 0.10, 0.25, 180, 230, 270, 330),
    "GG40": (3.00, 3.30, 1.70, 2.20, 0.70, 1.00, 0.10, 0.08, 0.35, 210, 260, 320, 400),
}

# ─── Product → machining ops + machines ──────────────────────
MACHINING_OPS = {
    "ENGINE_BLOCK": [
        ("ROUGH_MILLING",     "MCH-BM01","BORING_MILL",            "WC-BM",  "MAT030"),
        ("BORING",            "MCH-BM02","BORING_MILL",            "WC-BM",  "MAT029"),
        ("DRILLING",          "MCH-DR01","DRILL_PRESS",            "WC-DR",  "MAT029"),
        ("REAMING",           "MCH-DR01","DRILL_PRESS",            "WC-DR",  "MAT031"),
        ("HONING",            "MCH-HN01","HONING_MACHINE",         "WC-HN",  "MAT032"),
        ("FINISH_MILLING",    "MCH-FL01","FACE_MILL",              "WC-FM",  "MAT031"),
    ],
    "CYLINDER_HEAD": [
        ("FACE_MILLING",      "MCH-CNC01","CNC_MACHINING_CENTER",  "WC-CNC", "MAT030"),
        ("DRILLING",          "MCH-DR02", "DRILL_PRESS",           "WC-DR",  "MAT029"),
        ("REAMING",           "MCH-CNC01","CNC_MACHINING_CENTER",  "WC-CNC", "MAT031"),
        ("VALVE_SEAT_BORING", "MCH-CNC02","CNC_MACHINING_CENTER",  "WC-CNC", "MAT031"),
        ("SURFACE_GRINDING",  "MCH-GR01", "SURFACE_GRINDER",       "WC-GR",  "MAT033"),
    ],
    "CYLINDER_LINER": [
        ("ROUGH_TURNING",     "MCH-TN01","CNC_LATHE",              "WC-TN",  "MAT030"),
        ("FINISH_TURNING",    "MCH-TN02","CNC_LATHE",              "WC-TN",  "MAT031"),
        ("HONING",            "MCH-HN02","HONING_MACHINE",         "WC-HN",  "MAT032"),
        ("OD_GRINDING",       "MCH-GR02","CYLINDRICAL_GRINDER",    "WC-GR",  "MAT033"),
    ],
}

# ─── BOM components per finished good ────────────────────────
BOM_COMPONENTS = {
    "BOM001": [  # ENGINE_BLOCK GG25
        ("MAT001",28.0,"KG"), ("MAT002",8.0,"KG"), ("MAT004",4.0,"KG"),
        ("MAT005",0.4,"KG"),  ("MAT006",0.6,"KG"), ("MAT007",0.3,"KG"),
        ("MAT008",0.08,"KG"), ("MAT010",12.0,"KG"),("MAT012",0.8,"KG"),
        ("MAT014",0.4,"KG"),  ("MAT035",0.15,"KG"),
    ],
    "BOM002": [  # ENGINE_BLOCK GG30
        ("MAT001",26.0,"KG"), ("MAT002",9.0,"KG"), ("MAT003",3.0,"KG"),
        ("MAT004",4.5,"KG"),  ("MAT005",0.5,"KG"), ("MAT006",0.5,"KG"),
        ("MAT007",0.4,"KG"),  ("MAT015",0.1,"KG"), ("MAT008",0.09,"KG"),
        ("MAT010",13.0,"KG"), ("MAT012",0.85,"KG"),("MAT014",0.45,"KG"),
    ],
    "BOM003": [  # ENGINE_BLOCK GG30 Type C
        ("MAT001",27.0,"KG"), ("MAT002",8.5,"KG"), ("MAT003",3.5,"KG"),
        ("MAT004",4.0,"KG"),  ("MAT005",0.5,"KG"), ("MAT006",0.55,"KG"),
        ("MAT007",0.38,"KG"), ("MAT015",0.12,"KG"),("MAT009",0.10,"KG"),
        ("MAT010",12.5,"KG"), ("MAT011",1.5,"KG"), ("MAT013",0.6,"KG"),
    ],
    "BOM004": [  # CYLINDER_HEAD GG25
        ("MAT001",9.0,"KG"),  ("MAT002",3.5,"KG"), ("MAT004",2.0,"KG"),
        ("MAT005",0.15,"KG"), ("MAT006",0.20,"KG"),("MAT007",0.10,"KG"),
        ("MAT008",0.03,"KG"), ("MAT010",5.0,"KG"), ("MAT012",0.35,"KG"),
        ("MAT014",0.18,"KG"),
    ],
    "BOM005": [  # CYLINDER_HEAD GG30
        ("MAT001",10.0,"KG"), ("MAT002",3.5,"KG"), ("MAT003",1.0,"KG"),
        ("MAT004",2.0,"KG"),  ("MAT005",0.18,"KG"),("MAT006",0.22,"KG"),
        ("MAT007",0.12,"KG"), ("MAT015",0.04,"KG"),("MAT009",0.04,"KG"),
        ("MAT010",6.0,"KG"),  ("MAT012",0.40,"KG"),("MAT014",0.20,"KG"),
    ],
    "BOM006": [  # CYLINDER_LINER GG30
        ("MAT001",3.0,"KG"),  ("MAT002",1.0,"KG"), ("MAT004",0.8,"KG"),
        ("MAT006",0.06,"KG"), ("MAT007",0.04,"KG"),("MAT008",0.01,"KG"),
        ("MAT010",1.8,"KG"),  ("MAT012",0.12,"KG"),
    ],
    "BOM007": [  # CYLINDER_LINER GG40
        ("MAT001",3.2,"KG"),  ("MAT002",1.2,"KG"), ("MAT004",0.8,"KG"),
        ("MAT005",0.05,"KG"), ("MAT006",0.05,"KG"),("MAT007",0.05,"KG"),
        ("MAT015",0.02,"KG"), ("MAT009",0.015,"KG"),
        ("MAT010",2.0,"KG"),  ("MAT011",0.3,"KG"), ("MAT013",0.08,"KG"),
    ],
}

# Approximate unit weight per product type (kg per casting)
UNIT_WEIGHT = {
    "ENGINE_BLOCK":   38.0,
    "CYLINDER_HEAD":  14.0,
    "CYLINDER_LINER":  4.5,
}