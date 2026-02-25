"""
foundry_feeders.py
==================
All feeder scripts for Menon & Menon Foundry database.
Each feeder:
  1. Pulls ONLY valid FK values from the DB before generating a row.
  2. Uses CONSTRAINTS from foundry_config.py (finite, physically meaningful).
  3. Maintains chronological ordering (casting happens after melt, etc.).
  4. Ensures mathematical consistency (good+scrap=expected, total=parts+labor, etc.).

Run individual feeders:
    python foundry_feeders.py material      # material_master
    python foundry_feeders.py bom           # bill_of_materials
    python foundry_feeders.py production    # production_orders
    python foundry_feeders.py melting       # melting_heat_records
    python foundry_feeders.py molding       # molding_records
    python foundry_feeders.py casting       # casting_records
    python foundry_feeders.py heattreatment # heat_treatment
    python foundry_feeders.py machining     # machining_operations
    python foundry_feeders.py quality       # quality_inspections
    python foundry_feeders.py inventory     # inventory_movements
    python foundry_feeders.py maintenance   # equipment_maintenance
"""

import sys
import time
import random
import psycopg2
from datetime import datetime, timedelta, date
from foundry_config import (
    DB_CONFIG, SHIFTS, OPERATORS, SUPERVISORS, INSPECTORS, TECHNICIANS,
    USERS, CUSTOMERS, VENDORS, RAW_MATERIALS, FINISHED_GOODS, TOOL_MATERIALS,
    SPARE_MATERIALS, EQUIPMENT, MELT_FURNACES, HT_FURNACES, ALLOY_SPEC,
    MACHINING_OPS, BOM_COMPONENTS, UNIT_WEIGHT,
)

FEEDER_INTERVAL = 10  # seconds between inserts

# ─────────────────────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────────────────────
def connect():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"[DB ERROR] {e}")
        sys.exit(1)

def fetch_one(cursor, sql, params=()):
    cursor.execute(sql, params)
    r = cursor.fetchone()
    return r[0] if r else None

def fetch_all(cursor, sql, params=()):
    cursor.execute(sql, params)
    return [r[0] for r in cursor.fetchall()]

def next_id(cursor, table, id_col, prefix, width=6):
    """Read the highest ID in table, increment, return next formatted ID."""
    sql = f"SELECT {id_col} FROM {table} ORDER BY {id_col} DESC LIMIT 1"
    last = fetch_one(cursor, sql)
    if last:
        n = int(last.replace(prefix, "")) + 1
    else:
        n = 1
    return f"{prefix}{n:0{width}d}"

def insert(conn, cursor, table, data):
    cols = list(data.keys())
    vals = list(data.values())
    ph   = ", ".join(["%s"] * len(vals))
    sql  = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({ph})"
    cursor.execute(sql, vals)
    conn.commit()


# ─────────────────────────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────────────────────────
def rnum(lo, hi, dec=2):
    return round(random.uniform(lo, hi), dec)

def rdate_near(base: date, days_min=0, days_max=5) -> date:
    return base + timedelta(days=random.randint(days_min, days_max))


# ═════════════════════════════════════════════════════════════
# 01  MATERIAL MASTER FEEDER
# ─────────────────────────────────────────────────────────────
# The real material_master is STATIC (42 known materials).
# The feeder only inserts NEW consumables or spare parts as
# they are purchased/introduced – it never duplicates existing ones.
# ═════════════════════════════════════════════════════════════
CONSUMABLE_POOL = [
    # (mat_id, description, unit, price, mat_group, storage)
    ("MAT043","Drill Bit HSS 12mm",         "EA", 5.50, "CONS-TOOL","SL-30"),
    ("MAT044","Drill Bit Carbide 16mm",      "EA", 18.0, "CONS-TOOL","SL-30"),
    ("MAT045","End Mill 25mm Carbide",       "EA", 42.0, "CONS-TOOL","SL-30"),
    ("MAT046","Turning Insert CNMG",         "EA", 12.0, "CONS-TOOL","SL-30"),
    ("MAT047","Thread Tap M10",              "EA",  8.0, "CONS-TOOL","SL-30"),
    ("MAT048","Lathe Collet ER40",           "EA", 65.0, "CONS-TOOL","SL-30"),
    ("MAT049","Anti-seize Compound 500g",    "KG",  9.0, "CONS-COOL","SL-31"),
    ("MAT050","Hydraulic Oil ISO 68 20L",    "L",   4.2, "CONS-COOL","SL-31"),
    ("MAT051","Refractory Cement 25kg",      "KG",  2.8, "MAINT",    "SL-50"),
    ("MAT052","Thermocouple Type-K 300mm",   "EA", 22.0, "MAINT",    "SL-50"),
    ("MAT053","Gasket Sheet Graphite 1m²",   "EA", 35.0, "MAINT",    "SL-50"),
    ("MAT054","Safety Gloves Foundry Grade", "EA",  6.5, "SAFETY",   "SL-60"),
    ("MAT055","Grinding Disc 125mm",         "EA",  3.2, "CONS-TOOL","SL-30"),
]

def feed_material_master(conn, cursor):
    """
    Insert a new consumable/spare that does not yet exist in the DB.
    If all known extras are already in the DB, do nothing this cycle.
    """
    existing = fetch_all(cursor, "SELECT Material_Number FROM material_master")
    new_mats = [m for m in CONSUMABLE_POOL if m[0] not in existing]

    if not new_mats:
        print("[material_master] All consumables already present – nothing to insert.")
        return

    mat = random.choice(new_mats)
    mat_id, desc, unit, price, grp, sloc = mat

    net_wt = rnum(0.05, 5.0)
    data = {
        "Material_Number":    mat_id,
        "Material_Type":      "CONSUMABLE",
        "Description":        desc,
        "Base_Unit":          unit,
        "Material_Group":     grp,
        "Net_Weight_KG":      net_wt,
        "Gross_Weight_KG":    round(net_wt * 1.08, 3),
        "Standard_Price_USD": price,
        "Valuation_Class":    "VC-CO",
        "Plant":              "PLT002",
        "Storage_Location":   sloc,
        "ABC_Indicator":      "C",
        "MRP_Type":           "PD",
        "Safety_Stock":       50,
        "Lot_Size":           200,
        "Procurement_Type":   "F",
        "Created_Date":       date.today(),
        "Quality_Inspection": "N",
        "Lead_Time_Days":     21,
    }
    insert(conn, cursor, "material_master", data)
    print(f"[material_master] +{mat_id} | {desc}")


# ═════════════════════════════════════════════════════════════
# 02  BILL OF MATERIALS FEEDER
# ─────────────────────────────────────────────────────────────
# BOMs are also mostly static.  The feeder simulates Engineering
# Change Notices (ECNs) by updating a Scrap_Percentage on an
# existing BOM line, or adding a brand-new BOM component when a
# new material is introduced.
# ═════════════════════════════════════════════════════════════

def feed_bill_of_materials(conn, cursor):
    """
    Simulate an ECN: pick a random ACTIVE BOM row and adjust its Scrap_Percentage,
    OR insert a new BOM component for a consumable that was recently added to material_master.
    """
    # Check if there are new consumables not yet on any BOM
    all_mats = fetch_all(cursor, "SELECT Material_Number FROM material_master WHERE Material_Type='CONSUMABLE'")
    bom_comps = fetch_all(cursor, "SELECT DISTINCT Component_Material FROM bill_of_materials")
    new_consumables = [m for m in all_mats if m not in bom_comps]

    if new_consumables:
        # Add the new consumable as a component under BOM001 (sample linkage)
        comp_mat = new_consumables[0]
        parent_mat = "MAT022"  # Engine Block GG25 – a reasonable owner
        bom_num    = "BOM001"
        item_n = (fetch_one(cursor,
            "SELECT MAX(Item_Number) FROM bill_of_materials WHERE BOM_Number=%s", (bom_num,)) or 100) + 10
        data = {
            "BOM_Number":           bom_num,
            "Parent_Material":      parent_mat,
            "Parent_Description":   "Engine Block FG - GG25 Type A",
            "Component_Material":   comp_mat,
            "Component_Description":"New component via ECN",
            "Component_Type":       "CONSUMABLE",
            "Component_Quantity":   round(random.uniform(1, 5), 2),
            "Component_Unit":       "EA",
            "Item_Number":          item_n,
            "BOM_Level":            1,
            "Valid_From":           date.today(),
            "Valid_To":             date(2027, 12, 31),
            "BOM_Status":           "PENDING",
            "Scrap_Percentage":     round(random.uniform(2.0, 6.0), 2),
            "Plant":                "PLT001",
            "Component_Criticality":"LOW",
        }
        insert(conn, cursor, "bill_of_materials", data)
        print(f"[bill_of_materials] +BOM ECN | parent={parent_mat} comp={comp_mat}")
    else:
        # Update Scrap_Percentage on a random existing BOM line
        bom_id = fetch_one(cursor, "SELECT id FROM bill_of_materials ORDER BY RANDOM() LIMIT 1")
        if bom_id:
            new_scrap = round(random.uniform(1.5, 8.0), 2)
            cursor.execute(
                "UPDATE bill_of_materials SET Scrap_Percentage=%s WHERE id=%s",
                (new_scrap, bom_id)
            )
            conn.commit()
            print(f"[bill_of_materials] ECN update | id={bom_id} scrap={new_scrap}%")


# ═════════════════════════════════════════════════════════════
# 10  PRODUCTION ORDERS FEEDER
# ═════════════════════════════════════════════════════════════

def feed_production_orders(conn, cursor):
    new_id = next_id(cursor, "production_orders", "Production_Order", "PO", 4)

    fg_mat_id  = random.choice(list(FINISHED_GOODS.keys()))
    fg         = FINISHED_GOODS[fg_mat_id]
    desc, unit, price, prod_type, alloy, bom_num = fg

    qty       = random.randint(10, 120)
    std_cost  = round(price * qty * 0.72, 2)
    plan_cost = round(std_cost * 1.05, 2)
    cycle_d   = {"ENGINE_BLOCK": 18, "CYLINDER_HEAD": 12, "CYLINDER_LINER": 8}[prod_type]

    plan_start = date.today() + timedelta(days=random.randint(1, 30))
    plan_end   = plan_start + timedelta(days=cycle_d + random.randint(-2, 4))

    customer = random.choice(CUSTOMERS) if random.random() > 0.4 else ""
    so       = f"SO{random.randint(10000,99999)}" if customer else ""

    data = {
        "Production_Order":     new_id,
        "Order_Type":           "YP01",
        "Material_Number":      fg_mat_id,
        "Product_Type":         prod_type,
        "Alloy_Grade":          alloy,
        "Plant":                "PLT001",
        "Order_Quantity":       qty,
        "Confirmed_Quantity":   0,
        "Scrap_Quantity":       0,
        "Unit":                 "EA",
        "Planned_Start_Date":   plan_start,
        "Planned_End_Date":     plan_end,
        "Actual_Start_Date":    None,
        "Actual_End_Date":      None,
        "Order_Status":         "CREATED",
        "Priority":             random.randint(1, 5),
        "Production_Supervisor":random.choice(SUPERVISORS),
        "BOM_Number":           bom_num,
        "Sales_Order":          so,
        "Customer":             customer,
        "Planned_Costs_USD":    plan_cost,
        "Actual_Costs_USD":     0.0,
        "Standard_Cost_USD":    std_cost,
        "Cost_Variance_USD":    0.0,
        "Created_By":           random.choice(USERS),
        "Created_Date":         date.today(),
    }
    insert(conn, cursor, "production_orders", data)
    print(f"[production_orders] +{new_id} | {prod_type} {alloy} qty={qty}")


# ═════════════════════════════════════════════════════════════
# 03  MELTING HEAT RECORDS FEEDER
# ═════════════════════════════════════════════════════════════

def _chemistry(alloy):
    """Return chemically valid composition for the given alloy."""
    spec = ALLOY_SPEC[alloy]  # (C_lo,C_hi,Si_lo,Si_hi,Mn_lo,Mn_hi,P_max,S_max,Cr_max,...)
    c   = rnum(spec[0], spec[1], 3)
    si  = rnum(spec[2], spec[3], 3)
    mn  = rnum(spec[4], spec[5], 3)
    p   = rnum(0.04, spec[6], 4)
    s   = rnum(0.02, spec[7], 4)
    cr  = rnum(0.0, spec[8], 3)
    ni  = rnum(0.0, 0.10, 3)
    mo  = rnum(0.0, 0.05, 3)
    cu  = rnum(0.0, 0.10, 3)
    return c, si, mn, p, s, cr, ni, mo, cu

def feed_melting_heat_records(conn, cursor):
    new_id = next_id(cursor, "melting_heat_records", "Heat_Number", "HT", 4)

    fur_id   = random.choice(list(MELT_FURNACES.keys()))
    fur_type, capacity = MELT_FURNACES[fur_id]
    alloy    = random.choices(["GG25","GG30","GG40"], weights=[20,55,25])[0]

    charge   = random.randint(int(capacity * 0.70), int(capacity * 0.95))
    pig_frac = rnum(0.55, 0.70)
    scrap_frac = rnum(0.20, 0.35)
    ret_frac = round(1 - pig_frac - scrap_frac, 4)

    tap_temp  = rnum(1462, 1518, 1)
    pour_temp = round(tap_temp - rnum(30, 52), 1)

    c, si, mn, p, s, cr, ni, mo, cu = _chemistry(alloy)
    spec = ALLOY_SPEC[alloy]

    # Determine quality – all values must be within spec
    approved = (
        spec[0] <= c  <= spec[1] and
        spec[2] <= si <= spec[3] and
        p <= spec[6] and
        s <= spec[7] and
        tap_temp >= 1460
    )
    rej_reason = None
    if not approved:
        if not (spec[0] <= c <= spec[1]): rej_reason = "CARBON_OOB"
        elif p > spec[6]:                 rej_reason = "CHEMISTRY_OOB"
        elif tap_temp < 1460:             rej_reason = "LOW_TAP_TEMPERATURE"
        else:                             rej_reason = "CHEMISTRY_OOB"

    inoc_type = random.choice(["FeSi75","FeSi75+Sr","Bi-based"])
    duration  = random.randint(75, 210)
    energy    = round(charge * rnum(0.30, 0.44), 1)

    data = {
        "Heat_Number":          new_id,
        "Furnace_ID":           fur_id,
        "Furnace_Type":         fur_type,
        "Plant":                "PLT001",
        "Melt_Date":            date.today(),
        "Shift":                random.choice(SHIFTS),
        "Operator_ID":          random.choice(OPERATORS),
        "Target_Alloy":         alloy,
        "Charge_Weight_KG":     charge,
        "Pig_Iron_KG":          round(charge * pig_frac),
        "Scrap_Steel_KG":       round(charge * scrap_frac),
        "Returns_KG":           round(charge * ret_frac),
        "Alloy_Additions_KG":   round(charge * rnum(0.008, 0.015), 1),
        "Carbon_Pct":           c,
        "Silicon_Pct":          si,
        "Manganese_Pct":        mn,
        "Phosphorus_Pct":       p,
        "Sulfur_Pct":           s,
        "Chromium_Pct":         cr,
        "Nickel_Pct":           ni,
        "Molybdenum_Pct":       mo,
        "Copper_Pct":           cu,
        "Tap_Temperature_C":    tap_temp,
        "Pour_Temperature_C":   pour_temp,
        "Holding_Time_Min":     random.randint(20, 90),
        "Inoculation_Type":     inoc_type,
        "Inoculation_KG":       round(charge * rnum(0.001, 0.003), 2),
        "Spectro_Test_ID":      f"SPT{random.randint(10000,99999)}",
        "Quality_Status":       "APPROVED" if approved else "REJECTED",
        "Rejection_Reason":     rej_reason,
        "Yield_Pct":            rnum(78, 88),
        "Energy_KWH":           energy,
        "Melting_Duration_Min": duration,
    }
    insert(conn, cursor, "melting_heat_records", data)
    print(f"[melting_heat_records] +{new_id} | {alloy} {fur_id} {'✓' if approved else '✗'}")


# ═════════════════════════════════════════════════════════════
# 04  MOLDING RECORDS FEEDER
# Requires: production_orders (with status CREATED/RELEASED/IN_PROCESS)
# ═════════════════════════════════════════════════════════════

MOLDING_LINES = {
    "ENGINE_BLOCK":   ["ML-01","ML-02"],
    "CYLINDER_HEAD":  ["ML-02","ML-03"],
    "CYLINDER_LINER": ["ML-03","ML-04"],
}
MOLDING_TYPE_MAP = {
    "ENGINE_BLOCK":   "GREEN_SAND",
    "CYLINDER_HEAD":  "GREEN_SAND",
    "CYLINDER_LINER": "RESIN_SAND",
}
SAND_BINDER_MAP = {
    "GREEN_SAND":  ("SILICA",    "BENTONITE"),
    "RESIN_SAND":  ("CHROMITE",  "ALKALINE_PHENOLIC"),
}

def feed_molding_records(conn, cursor):
    # Pick a PO that does NOT yet have a mold batch
    po_id = fetch_one(cursor, """
        SELECT po.Production_Order
        FROM production_orders po
        LEFT JOIN molding_records mr ON mr.Production_Order = po.Production_Order
        WHERE po.Order_Status IN ('CREATED','RELEASED','IN_PROCESS')
          AND mr.Mold_Batch IS NULL
        ORDER BY po.Planned_Start_Date
        LIMIT 1
    """)
    if not po_id:
        print("[molding_records] No eligible PO without a mold batch – skipping.")
        return

    # Fetch PO details
    cursor.execute("""
        SELECT Product_Type, Alloy_Grade, Order_Quantity, Planned_Start_Date
        FROM production_orders WHERE Production_Order = %s
    """, (po_id,))
    row = cursor.fetchone()
    prod_type, alloy, qty, plan_start = row
    plan_start = plan_start if isinstance(plan_start, date) else plan_start.date()

    new_id       = f"MB{po_id}"
    mold_type    = MOLDING_TYPE_MAP[prod_type]
    sand_type, binder = SAND_BINDER_MAP[mold_type]
    mold_line    = random.choice(MOLDING_LINES[prod_type])

    defect_type  = random.choice(["BLOW_HOLE","SAND_DROP","COLD_SHUT"]) if random.random() < 0.08 else "NONE"
    quality      = "FAIL" if defect_type != "NONE" else "PASS"

    core_map = {"ENGINE_BLOCK":6,"CYLINDER_HEAD":4,"CYLINDER_LINER":1}
    mold_wt_map = {"ENGINE_BLOCK":(800,1200),"CYLINDER_HEAD":(300,600),"CYLINDER_LINER":(80,150)}

    data = {
        "Mold_Batch":              new_id,
        "Production_Order":        po_id,
        "Molding_Line":            mold_line,
        "Molding_Type":            mold_type,
        "Product_Type":            prod_type,
        "Alloy_Grade":             alloy,
        "Mold_Date":               rdate_near(plan_start, 1, 3),
        "Shift":                   random.choice(SHIFTS),
        "Operator_ID":             random.choice(OPERATORS),
        "Planned_Quantity":        qty,
        "Actual_Quantity":         max(1, qty + random.randint(-5, 5)),
        "Sand_Type":               sand_type,
        "Binder_Type":             binder,
        "Binder_Percentage":       rnum(3.5,5.5) if mold_type=="GREEN_SAND" else rnum(1.2,2.0),
        "Moisture_Content_Pct":    rnum(3.0,4.5) if mold_type=="GREEN_SAND" else rnum(0.0,0.5),
        "Compressive_Strength_KPA":rnum(22,35),
        "Permeability":            rnum(120,200) if mold_type=="GREEN_SAND" else rnum(80,140),
        "Mold_Hardness":           random.randint(65,90),
        "Core_Count":              core_map.get(prod_type,2),
        "Cycle_Time_Seconds":      random.randint(60,200),
        "Sand_Temperature_C":      rnum(22,35),
        "Ambient_Humidity_Pct":    rnum(40,75),
        "Quality_Check":           quality,
        "Defect_Type":             defect_type,
        "Mold_Weight_KG":          rnum(*mold_wt_map[prod_type]),
        "Setup_Time_Min":          random.randint(30,120),
        "Pattern_Number":          f"PTN{random.randint(10000,99999)}",
        "Sand_Mix_Batch":          f"SMX{random.randint(10000,99999)}",
    }
    insert(conn, cursor, "molding_records", data)

    # Update PO status to IN_PROCESS
    cursor.execute("UPDATE production_orders SET Order_Status='IN_PROCESS', Actual_Start_Date=%s WHERE Production_Order=%s",
                   (date.today(), po_id))
    conn.commit()
    print(f"[molding_records] +{new_id} | PO={po_id} {prod_type} {mold_type}")


# ═════════════════════════════════════════════════════════════
# 05  CASTING RECORDS FEEDER
# Requires: approved heat, molding record + linked PO
# ═════════════════════════════════════════════════════════════

LADLES = [f"LAD{i:02d}" for i in range(1, 13)]

def feed_casting_records(conn, cursor):
    # Find a PO with a mold batch but no casting batch yet
    row = fetch_one(cursor, """
        SELECT mr.Mold_Batch
        FROM molding_records mr
        LEFT JOIN casting_records cr ON cr.Mold_Batch = mr.Mold_Batch
        WHERE cr.Casting_Batch IS NULL
          AND mr.Quality_Check = 'PASS'
        ORDER BY mr.Mold_Date
        LIMIT 1
    """)
    if not row:
        print("[casting_records] No eligible mold batch – skipping.")
        return

    mold_id = row
    cursor.execute("""
        SELECT mr.Production_Order, mr.Product_Type, mr.Alloy_Grade, mr.Actual_Quantity, mr.Mold_Date
        FROM molding_records mr WHERE mr.Mold_Batch = %s
    """, (mold_id,))
    po_id, prod_type, alloy, qty, mold_date = cursor.fetchone()

    # Pick an approved heat with matching alloy
    heat_id = fetch_one(cursor, """
        SELECT Heat_Number FROM melting_heat_records
        WHERE Quality_Status='APPROVED' AND Target_Alloy=%s
        ORDER BY Melt_Date DESC LIMIT 10
    """, (alloy,))
    # randomly select from top 10 (fetch all)
    cursor.execute("""
        SELECT Heat_Number FROM melting_heat_records
        WHERE Quality_Status='APPROVED' AND Target_Alloy=%s
        ORDER BY Melt_Date DESC LIMIT 10
    """, (alloy,))
    heat_rows = cursor.fetchall()
    if not heat_rows:
        print(f"[casting_records] No approved {alloy} heat available – skipping.")
        return
    heat_id = random.choice(heat_rows)[0]

    # Fetch pour temp from heat
    pour_temp_base = fetch_one(cursor,
        "SELECT Pour_Temperature_C FROM melting_heat_records WHERE Heat_Number=%s", (heat_id,))
    pour_temp = round(float(pour_temp_base) - rnum(0, 12), 1)

    expected  = qty
    scrap_pct = rnum(3, 11) / 100
    scrap_n   = max(1, int(expected * scrap_pct))
    good_n    = expected - scrap_n
    yield_pct = round(good_n / expected * 100, 2)
    grade     = "A" if scrap_pct < 0.05 else ("B" if scrap_pct < 0.08 else "C")

    unit_wt   = UNIT_WEIGHT[prod_type]
    metal_poured = round(unit_wt * expected * rnum(1.15, 1.35), 1)
    defect    = random.choice(["NONE","SHRINKAGE","POROSITY","COLD_SHUT","MISRUN"]) if scrap_n > 0 else "NONE"
    cast_date = mold_date + timedelta(days=1) if isinstance(mold_date, date) else date.today()

    new_id = next_id(cursor, "casting_records", "Casting_Batch", "CB", 4)

    data = {
        "Casting_Batch":           new_id,
        "Heat_Number":             heat_id,
        "Production_Order":        po_id,
        "Mold_Batch":              mold_id,
        "Casting_Date":            cast_date,
        "Shift":                   random.choice(SHIFTS),
        "Operator_ID":             random.choice(OPERATORS),
        "Product_Type":            prod_type,
        "Alloy_Grade":             alloy,
        "Ladle_Number":            random.choice(LADLES),
        "Ladle_Capacity_KG":       1500 if prod_type == "ENGINE_BLOCK" else 800,
        "Metal_Weight_Poured_KG":  metal_poured,
        "Pouring_Temperature_C":   pour_temp,
        "Pouring_Rate_KG_MIN":     rnum(30, 120),
        "Molds_Poured":            expected,
        "Expected_Castings":       expected,
        "Good_Castings":           good_n,
        "Scrap_Castings":          scrap_n,
        "Yield_Pct":               yield_pct,
        "Gating_System":           random.choice(["TOP","SIDE","BOTTOM","MULTI"]),
        "Riser_Type":              random.choice(["OPEN","BLIND","INSULATED"]),
        "Cooling_Time_Hours":      rnum(4, 24),
        "Ambient_Temperature_C":   rnum(18, 38),
        "Pouring_Height_MM":       random.randint(100, 350),
        "Filter_Used":             "YES" if random.random() > 0.3 else "NO",
        "Filter_Type":             random.choice(["CERAMIC_FOAM","PRESSED_CERAMIC","NONE"]),
        "Inoculation_In_Ladle":    "YES" if random.random() > 0.2 else "NO",
        "Defects_Detected":        defect,
        "Quality_Grade":           grade,
    }
    insert(conn, cursor, "casting_records", data)
    print(f"[casting_records] +{new_id} | PO={po_id} heat={heat_id} yield={yield_pct}% grade={grade}")


# ═════════════════════════════════════════════════════════════
# 06  HEAT TREATMENT FEEDER
# Requires: casting_records (no HT yet)
# ═════════════════════════════════════════════════════════════

TREATMENT_PARAMS = {
    "STRESS_RELIEF": (540, 620, 3.0, 6.0, "FURNACE_COOL"),
    "ANNEALING":     (780, 870, 4.0, 8.0, "FURNACE_COOL"),
    "NORMALIZING":   (880, 920, 2.0, 4.0, "AIR_COOL"),
}

def feed_heat_treatment(conn, cursor):
    row = fetch_one(cursor, """
        SELECT cr.Casting_Batch
        FROM casting_records cr
        LEFT JOIN heat_treatment ht ON ht.Casting_Batch = cr.Casting_Batch
        WHERE ht.HT_Batch_Number IS NULL
          AND cr.Quality_Grade IN ('A','B')
        ORDER BY cr.Casting_Date
        LIMIT 1
    """)
    if not row:
        print("[heat_treatment] No eligible casting batch – skipping.")
        return

    cb_id = row
    cursor.execute("""
        SELECT cr.Production_Order, cr.Product_Type, cr.Alloy_Grade,
               cr.Expected_Castings, cr.Casting_Date
        FROM casting_records cr WHERE cr.Casting_Batch = %s
    """, (cb_id,))
    po_id, prod_type, alloy, qty, cast_date = cursor.fetchone()

    if prod_type == "ENGINE_BLOCK":
        treat_type = random.choice(["STRESS_RELIEF","STRESS_RELIEF","ANNEALING"])
    elif prod_type == "CYLINDER_HEAD":
        treat_type = random.choice(["STRESS_RELIEF","ANNEALING"])
    else:
        treat_type = "STRESS_RELIEF"

    p         = TREATMENT_PARAMS[treat_type]
    target_t  = rnum(p[0], p[1])
    actual_t  = target_t + rnum(-12, 12)
    hold_hrs  = rnum(p[2], p[3])

    spec      = ALLOY_SPEC[alloy]
    pre_hard  = random.randint(spec[9], spec[10])
    post_hard = pre_hard - random.randint(5, 25) if treat_type == "ANNEALING" else pre_hard + random.randint(-8, 12)
    post_hard = max(130, min(280, post_hard))

    in_spec   = (p[0] - 20) <= actual_t <= (p[1] + 20)
    load_wt   = round(qty * UNIT_WEIGHT[prod_type], 1)
    energy    = round(load_wt * rnum(0.18, 0.30), 1)
    new_id    = next_id(cursor, "heat_treatment", "HT_Batch_Number", "HTB", 4)
    fur_id    = random.choice(list(HT_FURNACES.keys()))
    treat_date = (cast_date + timedelta(days=1)) if isinstance(cast_date, date) else date.today()

    data = {
        "HT_Batch_Number":      new_id,
        "Casting_Batch":        cb_id,
        "Production_Order":     po_id,
        "Furnace_ID":           fur_id,
        "Furnace_Type":         HT_FURNACES[fur_id],
        "Treatment_Date":       treat_date,
        "Shift":                random.choice(SHIFTS),
        "Operator_ID":          random.choice(OPERATORS),
        "Treatment_Type":       treat_type,
        "Product_Type":         prod_type,
        "Parts_Count":          qty,
        "Total_Load_Weight_KG": load_wt,
        "Target_Temperature_C": round(target_t, 1),
        "Actual_Temperature_C": round(actual_t, 1),
        "Heating_Rate_C_HR":    rnum(80, 150),
        "Holding_Time_Hours":   round(hold_hrs, 2),
        "Cooling_Method":       p[4],
        "Cooling_Rate_C_HR":    rnum(25, 180),
        "Atmosphere":           "AIR",
        "Pre_HT_Hardness_HB":   pre_hard,
        "Post_HT_Hardness_HB":  post_hard,
        "Hardness_Test_Location":random.choice(["TOP","MIDDLE","BOTTOM","MULTIPLE"]),
        "Microstructure":       random.choice(["PEARLITE","PEARLITE_FERRITE","LAMELLAR_GRAPHITE"]),
        "Quality_Status":       "APPROVED" if in_spec else "REWORK",
        "Rejection_Reason":     None if in_spec else "TEMPERATURE_OOB",
        "Energy_Consumed_KWH":  energy,
        "Cycle_Time_Hours":     round(hold_hrs + rnum(2, 5), 1),
    }
    insert(conn, cursor, "heat_treatment", data)
    print(f"[heat_treatment] +{new_id} | CB={cb_id} {treat_type} {'✓' if in_spec else 'REWORK'}")


# ═════════════════════════════════════════════════════════════
# 07  MACHINING OPERATIONS FEEDER
# Requires: casting + heat treatment complete for a PO
# ═════════════════════════════════════════════════════════════

def feed_machining_operations(conn, cursor):
    # Find a PO with HT done but missing at least one machining op
    row = fetch_one(cursor, """
        SELECT ht.Production_Order
        FROM heat_treatment ht
        JOIN production_orders po ON po.Production_Order = ht.Production_Order
        WHERE ht.Quality_Status = 'APPROVED'
          AND po.Order_Status = 'IN_PROCESS'
        ORDER BY ht.Treatment_Date
        LIMIT 1
    """)
    if not row:
        print("[machining_operations] No eligible PO – skipping.")
        return

    po_id = row
    cursor.execute("SELECT Product_Type, Order_Quantity FROM production_orders WHERE Production_Order=%s", (po_id,))
    prod_type, qty = cursor.fetchone()

    # Which ops already exist for this PO?
    cursor.execute("SELECT Operation_Type FROM machining_operations WHERE Production_Order=%s", (po_id,))
    done_ops = {r[0] for r in cursor.fetchall()}

    all_ops = MACHINING_OPS[prod_type]
    pending = [(seq+1, op) for seq, op in enumerate(all_ops) if op[0] not in done_ops]

    if not pending:
        # All ops done – mark PO completed
        cursor.execute("""
            UPDATE production_orders
            SET Order_Status='COMPLETED', Actual_End_Date=%s,
                Confirmed_Quantity=Order_Quantity - Scrap_Quantity
            WHERE Production_Order=%s
        """, (date.today(), po_id))
        conn.commit()
        print(f"[machining_operations] PO {po_id} all ops done → COMPLETED")
        return

    seq_n, op = pending[0]
    op_type, mach_id, mach_type, work_ctr, tool_mat = op

    # Machining parameters based on operation family
    if "BORING" in op_type or "HONING" in op_type:
        spindle = random.randint(200, 800)
        feed    = rnum(30, 150)
        doc     = rnum(0.05, 0.5)
    elif "TURNING" in op_type or "MILLING" in op_type:
        spindle = random.randint(500, 2500)
        feed    = rnum(100, 600)
        doc     = rnum(0.5, 5.0)
    else:
        spindle = random.randint(300, 1500)
        feed    = rnum(50, 300)
        doc     = rnum(0.1, 2.0)

    tol_hi  = rnum(0.02, 0.10, 3)
    tol_lo  = -rnum(0.02, 0.10, 3)
    deviat  = rnum(tol_lo * 0.9, tol_hi * 0.9, 3)
    in_tol  = tol_lo <= deviat <= tol_hi
    defect  = "" if in_tol else random.choice(["OVERSIZE","UNDERSIZE","TOOL_CHATTER"])
    new_id  = next_id(cursor, "machining_operations", "Operation_ID", "MOP", 5)

    # Fetch HT date for operation_date ordering
    ht_date = fetch_one(cursor,
        "SELECT Treatment_Date FROM heat_treatment WHERE Production_Order=%s ORDER BY Treatment_Date LIMIT 1",
        (po_id,))
    op_date = rdate_near(ht_date if isinstance(ht_date, date) else date.today(), seq_n, seq_n + 1)

    data = {
        "Operation_ID":          new_id,
        "Production_Order":      po_id,
        "Operation_Date":        op_date,
        "Work_Center":           work_ctr,
        "Machine_ID":            mach_id,
        "Machine_Type":          mach_type,
        "Operation_Type":        op_type,
        "Operator_ID":           random.choice(OPERATORS),
        "Shift":                 random.choice(SHIFTS),
        "Product_Type":          prod_type,
        "Operation_Sequence":    seq_n * 10,
        "Tool_Material_Number":  tool_mat,
        "Tool_Description":      f"{op_type} tool",
        "Tool_Life_Used_Pct":    rnum(5, 95),
        "Spindle_Speed_RPM":     spindle,
        "Feed_Rate_MM_MIN":      round(feed, 1),
        "Depth_Of_Cut_MM":       round(doc, 3),
        "Coolant_Type":          random.choice(["SYNTHETIC","SOLUBLE_OIL","SEMI_SYNTHETIC","DRY"]),
        "Cycle_Time_Seconds":    random.randint(45, 600),
        "Setup_Time_Minutes":    random.randint(15, 90),
        "Tolerance_Upper_MM":    round(tol_hi, 3),
        "Tolerance_Lower_MM":    round(tol_lo, 3),
        "Measured_Deviation_MM": round(deviat, 3),
        "Surface_Roughness_RA":  rnum(0.4, 6.3),
        "Quality_Status":        "PASS" if in_tol else "FAIL",
        "Defect_Type":           defect if defect else None,
        "Power_Consumption_KW":  rnum(5, 40),
        "Quantity_Processed":    qty,
    }
    insert(conn, cursor, "machining_operations", data)
    print(f"[machining_operations] +{new_id} | PO={po_id} {op_type} seq={seq_n*10} {'✓' if in_tol else '✗'}")


# ═════════════════════════════════════════════════════════════
# 08  QUALITY INSPECTIONS FEEDER
# Requires: casting_records (and PO)
# ═════════════════════════════════════════════════════════════

def feed_quality_inspections(conn, cursor):
    # Find a PO+casting that has IN_PROCESS stage inspection missing
    row = fetch_one(cursor, """
        SELECT cr.Casting_Batch
        FROM casting_records cr
        JOIN production_orders po ON po.Production_Order = cr.Production_Order
        LEFT JOIN quality_inspections qi
            ON qi.Production_Order = cr.Production_Order
           AND qi.Inspection_Stage = 'IN_PROCESS'
        WHERE qi.Inspection_Lot IS NULL
          AND po.Order_Status = 'IN_PROCESS'
        ORDER BY cr.Casting_Date
        LIMIT 1
    """)

    # If no IN_PROCESS, try FINAL for completed orders
    if not row:
        row = fetch_one(cursor, """
            SELECT cr.Casting_Batch
            FROM casting_records cr
            JOIN production_orders po ON po.Production_Order = cr.Production_Order
            LEFT JOIN quality_inspections qi
                ON qi.Production_Order = cr.Production_Order
               AND qi.Inspection_Stage = 'FINAL'
            WHERE qi.Inspection_Lot IS NULL
              AND po.Order_Status IN ('COMPLETED','CLOSED')
            ORDER BY cr.Casting_Date
            LIMIT 1
        """)
        stage = "FINAL"
    else:
        stage = "IN_PROCESS"

    if not row:
        print("[quality_inspections] No eligible batch – skipping.")
        return

    cb_id = row
    cursor.execute("""
        SELECT cr.Production_Order, cr.Product_Type, cr.Alloy_Grade, cr.Expected_Castings, cr.Casting_Date
        FROM casting_records cr WHERE cr.Casting_Batch = %s
    """, (cb_id,))
    po_id, prod_type, alloy, qty, cast_date = cursor.fetchone()

    # Fetch FG material number
    fg_mat = fetch_one(cursor, "SELECT Material_Number FROM production_orders WHERE Production_Order=%s", (po_id,))

    spec = ALLOY_SPEC[alloy]
    hardness  = random.randint(spec[9], spec[10])
    tensile   = random.randint(spec[11], spec[12])
    elongation= rnum(0.5, 2.0)

    ndt_type   = random.choice(["ULTRASONIC","MAGNETIC_PARTICLE","DYE_PENETRANT",""])
    ndt_result = "PASS" if random.random() > 0.05 else "FAIL"
    defect_cnt = random.randint(1, 4) if random.random() < 0.12 else 0
    major      = min(defect_cnt, random.randint(0, max(1, defect_cnt//2)))
    minor      = defect_cnt - major
    critical   = 1 if defect_cnt > 3 else 0

    decision   = "REJECT" if (critical > 0 or (ndt_type and ndt_result == "FAIL")) else "ACCEPT"
    rej_code   = random.choice(["RC-NDT","RC-DIM","RC-HARD"]) if decision == "REJECT" else None
    cert       = f"COC{random.randint(1000000,9999999)}" if stage == "FINAL" and decision == "ACCEPT" else None

    new_id     = next_id(cursor, "quality_inspections", "Inspection_Lot", "IL", 5)
    insp_date  = rdate_near(cast_date if isinstance(cast_date, date) else date.today(), 1, 3)

    data = {
        "Inspection_Lot":        new_id,
        "Inspection_Date":       insp_date,
        "Inspector_ID":          random.choice(INSPECTORS),
        "Inspection_Stage":      stage,
        "Material_Number":       fg_mat,
        "Production_Order":      po_id,
        "Casting_Batch":         cb_id,
        "Quantity_Inspected":    qty,
        "Sampling_Plan":         random.choice(["NORMAL","TIGHTENED","REDUCED"]),
        "AQL_Level":             random.choice([0.65,1.0,1.5,2.5]),
        "Visual_Inspection":     "PASS" if random.random() > 0.02 else "FAIL",
        "Dimensional_Check":     "PASS" if random.random() > 0.04 else "FAIL",
        "CMM_Measurement":       "PASS" if random.random() > 0.03 else "FAIL",
        "Hardness_HB":           hardness,
        "Tensile_Strength_MPA":  tensile,
        "Elongation_Pct":        elongation,
        "NDT_Type":              ndt_type if ndt_type else None,
        "NDT_Result":            ndt_result if ndt_type else None,
        "Surface_Finish_RA":     rnum(0.8, 6.3) if stage == "FINAL" else None,
        "Defect_Count":          defect_cnt,
        "Major_Defects":         major,
        "Minor_Defects":         minor,
        "Critical_Defects":      critical,
        "Overall_Decision":      decision,
        "Rejection_Code":        rej_code,
        "Certificate_Number":    cert,
        "Inspection_Duration_Min": random.randint(20, 180),
    }
    insert(conn, cursor, "quality_inspections", data)
    print(f"[quality_inspections] +{new_id} | PO={po_id} stage={stage} → {decision}")


# ═════════════════════════════════════════════════════════════
# 09  INVENTORY MOVEMENTS FEEDER
# ═════════════════════════════════════════════════════════════

# Approximate stock levels (seeded; will drift with actual DB state)
_STOCK_CACHE: dict = {}

def _get_stock(cursor, mat_id, sloc):
    key = (mat_id, sloc)
    if key not in _STOCK_CACHE:
        val = fetch_one(cursor,
            "SELECT COALESCE(MAX(Stock_After),0) FROM inventory_movements WHERE Material_Number=%s AND Storage_Location=%s",
            (mat_id, sloc))
        _STOCK_CACHE[key] = float(val or 1000.0)
    return _STOCK_CACHE[key]

def _set_stock(mat_id, sloc, val):
    _STOCK_CACHE[(mat_id, sloc)] = val

def feed_inventory_movements(conn, cursor):
    new_id = next_id(cursor, "inventory_movements", "Document_Number", "IMD", 5)

    # 60% chance GR_PURCHASE for raw materials, 40% GI_PRODUCTION
    if random.random() < 0.60:
        # Goods Receipt from Vendor
        mat_id, mat_info = random.choice(list(RAW_MATERIALS.items()))
        desc, unit, price, grp, sloc = mat_info
        qty    = round(random.uniform(500, 5000) if "Sand" in desc else random.uniform(200, 2000))
        before = _get_stock(cursor, mat_id, sloc)
        after  = before + qty
        _set_stock(mat_id, sloc, after)
        data = {
            "Document_Number": new_id,
            "Document_Date":   date.today(),
            "Posting_Date":    date.today() + timedelta(days=random.randint(0,1)),
            "Movement_Type":   "GR_PURCHASE",
            "Movement_Code":   101,
            "Material_Number": mat_id,
            "Material_Type":   "RAW_MATERIAL",
            "Plant":           "PLT001",
            "Storage_Location": sloc,
            "From_Location":   None,
            "To_Location":     sloc,
            "Quantity":        qty,
            "Unit":            unit,
            "Batch_Number":    f"BTH{random.randint(100000,999999)}",
            "Vendor_Number":   random.choice(VENDORS),
            "Purchase_Order":  f"PUR{random.randint(10000,99999)}",
            "Production_Order":None,
            "Cost_Center":     f"CC{random.randint(1000,9999)}",
            "Amount_USD":      round(qty * price, 2),
            "Currency":        "USD",
            "User_ID":         random.choice(USERS),
            "Stock_Before":    round(before, 3),
            "Stock_After":     round(after, 3),
        }
    else:
        # Goods Issue to Production – pick an IN_PROCESS PO
        po_id = fetch_one(cursor,
            "SELECT Production_Order FROM production_orders WHERE Order_Status='IN_PROCESS' ORDER BY RANDOM() LIMIT 1")
        if not po_id:
            print("[inventory_movements] No IN_PROCESS PO – defaulting to GR_PURCHASE.")
            feed_inventory_movements(conn, cursor)  # fallback
            return

        cursor.execute("SELECT Product_Type, Alloy_Grade, BOM_Number, Order_Quantity FROM production_orders WHERE Production_Order=%s", (po_id,))
        prod_type, alloy, bom_num, qty = cursor.fetchone()

        # Pick a component from this PO's BOM
        comps = BOM_COMPONENTS.get(bom_num, BOM_COMPONENTS["BOM001"])
        mat_id, comp_qty_per_ea, unit = random.choice(comps)

        if mat_id not in RAW_MATERIALS:
            mat_id = random.choice(list(RAW_MATERIALS.keys()))
        mat_info = RAW_MATERIALS[mat_id]
        desc, mat_unit, price, grp, sloc = mat_info

        total_qty = round(comp_qty_per_ea * qty * rnum(1.02, 1.08), 3)
        before    = _get_stock(cursor, mat_id, sloc)
        after     = max(0.0, before - total_qty)
        _set_stock(mat_id, sloc, after)

        data = {
            "Document_Number": new_id,
            "Document_Date":   date.today(),
            "Posting_Date":    date.today(),
            "Movement_Type":   "GI_PRODUCTION",
            "Movement_Code":   261,
            "Material_Number": mat_id,
            "Material_Type":   "RAW_MATERIAL",
            "Plant":           "PLT001",
            "Storage_Location": sloc,
            "From_Location":   sloc,
            "To_Location":     "PRODUCTION",
            "Quantity":        total_qty,
            "Unit":            unit,
            "Batch_Number":    f"BTH{random.randint(100000,999999)}",
            "Vendor_Number":   None,
            "Purchase_Order":  None,
            "Production_Order": po_id,
            "Cost_Center":     f"CC{random.randint(1000,9999)}",
            "Amount_USD":      round(total_qty * price, 2),
            "Currency":        "USD",
            "User_ID":         random.choice(USERS),
            "Stock_Before":    round(before, 3),
            "Stock_After":     round(after, 3),
        }

    insert(conn, cursor, "inventory_movements", data)
    print(f"[inventory_movements] +{new_id} | {data['Movement_Type']} mat={data['Material_Number']} qty={data['Quantity']}")


# ═════════════════════════════════════════════════════════════
# 11  EQUIPMENT MAINTENANCE FEEDER
# ═════════════════════════════════════════════════════════════

def feed_equipment_maintenance(conn, cursor):
    """
    Generates one maintenance event.
    Breakdown events are triggered against equipment that has high
    downtime history.  Preventive events target equipment whose
    Next_Maintenance_Due is today or past.
    """
    new_id = next_id(cursor, "equipment_maintenance", "Maintenance_Order", "PMO", 4)

    # 25% chance BREAKDOWN, 50% PREVENTIVE, 25% INSPECTION
    roll = random.random()
    if roll < 0.25:
        maint_type  = "BREAKDOWN"
        order_type  = "PM02"
        priority    = random.randint(1, 2)
        fail_code   = random.choice(["MECH","ELEC","HYDR","REFR","CTRL","WEAR"])
        spare_mat   = random.choice(SPARE_MATERIALS + [""])
        downtime    = rnum(2, 48)
        labor_h     = rnum(4, 20)
        parts_cost  = rnum(500, 8000)
        # Pick equipment with prior breakdowns if possible
        eq_id = fetch_one(cursor, """
            SELECT Equipment_Number FROM equipment_maintenance
            WHERE Maintenance_Type='BREAKDOWN'
            GROUP BY Equipment_Number ORDER BY COUNT(*) DESC LIMIT 5
        """)
        if not eq_id:
            eq_id = random.choice(list(EQUIPMENT.keys()))
    elif roll < 0.75:
        maint_type  = "PREVENTIVE"
        order_type  = "PM01"
        priority    = random.randint(3, 4)
        fail_code   = None
        spare_mat   = random.choice(SPARE_MATERIALS) if random.random() > 0.5 else ""
        downtime    = rnum(0.5, 8)
        labor_h     = rnum(2, 8)
        parts_cost  = rnum(50, 1500)
        # Pick equipment whose Next_Maintenance_Due <= today
        eq_id = fetch_one(cursor, """
            SELECT Equipment_Number FROM equipment_maintenance
            WHERE Next_Maintenance_Due <= CURRENT_DATE
            ORDER BY Next_Maintenance_Due LIMIT 1
        """)
        if not eq_id:
            eq_id = random.choice(list(EQUIPMENT.keys()))
    else:
        maint_type  = "INSPECTION"
        order_type  = "PM03"
        priority    = random.randint(3, 5)
        fail_code   = None
        spare_mat   = ""
        downtime    = rnum(0.5, 4)
        labor_h     = rnum(1, 6)
        parts_cost  = rnum(0, 300)
        eq_id       = random.choice(list(EQUIPMENT.keys()))

    if eq_id not in EQUIPMENT:
        eq_id = random.choice(list(EQUIPMENT.keys()))

    eq_type, eq_desc, plant, work_ctr, _ = EQUIPMENT[eq_id]
    labor_cost  = round(labor_h * rnum(55, 85), 2)
    parts_cost  = round(parts_cost, 2)
    now         = datetime.now()
    plan_start  = now
    plan_end    = now + timedelta(hours=random.randint(4, 72))
    act_start   = now + timedelta(minutes=random.randint(0, 30))
    act_end     = act_start + timedelta(hours=downtime)
    next_due    = (act_end + timedelta(days={"PREVENTIVE":90,"INSPECTION":180,"BREAKDOWN":30}.get(maint_type,60))).date()

    data = {
        "Maintenance_Order":    new_id,
        "Equipment_Number":     eq_id,
        "Equipment_Type":       eq_type,
        "Equipment_Description":eq_desc,
        "Plant":                plant,
        "Work_Center":          work_ctr,
        "Maintenance_Type":     maint_type,
        "Order_Type":           order_type,
        "Priority":             priority,
        "Planned_Start":        plan_start,
        "Planned_End":          plan_end,
        "Actual_Start":         act_start,
        "Actual_End":           act_end,
        "Status":               "COMPLETED",
        "Technician_ID":        random.choice(TECHNICIANS),
        "Downtime_Hours":       round(downtime, 1),
        "Labor_Hours":          round(labor_h, 1),
        "Parts_Cost_USD":       parts_cost,
        "Labor_Cost_USD":       labor_cost,
        # Total_Cost_USD is a GENERATED column in PG – do NOT include it
        "Failure_Code":         fail_code,
        "Spare_Parts_Material": spare_mat if spare_mat else None,
        "Next_Maintenance_Due": next_due,
        "Maintenance_Plan":     f"MP{random.randint(10000,99999)}" if maint_type == "PREVENTIVE" else None,
        "Notification_Number":  f"NOT{random.randint(1000000,9999999)}",
        "Created_By":           random.choice(USERS),
        "Created_Date":         date.today(),
    }
    insert(conn, cursor, "equipment_maintenance", data)
    print(f"[equipment_maintenance] +{new_id} | {eq_id} {maint_type} downtime={downtime:.1f}h")


# ─────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────

FEEDERS = {
    "material":      ("material_master",        feed_material_master),
    "bom":           ("bill_of_materials",       feed_bill_of_materials),
    "production":    ("production_orders",       feed_production_orders),
    "melting":       ("melting_heat_records",    feed_melting_heat_records),
    "molding":       ("molding_records",         feed_molding_records),
    "casting":       ("casting_records",         feed_casting_records),
    "heattreatment": ("heat_treatment",          feed_heat_treatment),
    "machining":     ("machining_operations",    feed_machining_operations),
    "quality":       ("quality_inspections",     feed_quality_inspections),
    "inventory":     ("inventory_movements",     feed_inventory_movements),
    "maintenance":   ("equipment_maintenance",   feed_equipment_maintenance),
}

def run_feeder(name: str):
    if name not in FEEDERS:
        print(f"Unknown feeder '{name}'. Choices: {list(FEEDERS.keys())}")
        sys.exit(1)
    table, func = FEEDERS[name]
    print(f"Starting {name} feeder → table: {table} (interval={FEEDER_INTERVAL}s)")
    conn   = connect()
    cursor = conn.cursor()
    try:
        while True:
            try:
                func(conn, cursor)
            except Exception as e:
                print(f"[ERROR] {e}")
                conn.rollback()
            time.sleep(FEEDER_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n[{name}] Stopped.")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python foundry_feeders.py <feeder_name>")
        print(f"Available: {list(FEEDERS.keys())}")
        sys.exit(1)
    run_feeder(sys.argv[1])