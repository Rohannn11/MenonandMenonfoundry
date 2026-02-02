import os
import time
import random
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "port": os.getenv("DB_PORT")
}

# --- Learned Constraints ---
CONSTRAINTS = {
    "Machine_Types": ['GRINDER', 'DRILL_PRESS', 'CNC_LATHE', 'BORING_MILL', 'HONING_MACHINE'],
    "Operation_Types": ['BORING', 'REAMING', 'DRILLING', 'ROUGH_MILLING', 'GRINDING'],
    "Tool_Types": ['CERAMIC', 'CARBIDE_INSERT', 'HSS', 'DIAMOND', 'CBN'],
    "Coolant_Types": ['SYNTHETIC', 'SOLUBLE_OIL', 'SEMI_SYNTHETIC', 'NEAT_OIL', 'DRY'],
    "Defect_Types": ['SURFACE_FINISH', 'DIMENSION_OUT', 'TOOL_MARK', 'CHATTER', None],
    "Product_Types": ['ENGINE_BLOCK', 'CYLINDER_HEAD', 'CYLINDER_LINER']
}

def get_db_connection():
    try: return psycopg2.connect(**DB_CONFIG)
    except Exception as e: print(f"DB Error: {e}"); return None

def get_last_op_id(cursor):
    cursor.execute("SELECT Operation_ID FROM machining_operations ORDER BY Operation_ID DESC LIMIT 1;")
    result = cursor.fetchone()
    return result[0] if result else "OP10000000"

def generate_next_id(last_id):
    prefix = "OP"
    try:
        numeric_part = int(last_id.replace(prefix, ""))
        return f"{prefix}{numeric_part + 1:08d}"
    except: return f"{prefix}{int(time.time())}"

def generate_random_row(op_id):
    today = datetime.now()
    
    # Logic: Deviation determines status
    deviation = round(random.uniform(-0.3, 0.3), 3)
    if abs(deviation) > 0.2:
        status = 'FAIL'
        defect = random.choice([d for d in CONSTRAINTS["Defect_Types"] if d])
    elif abs(deviation) > 0.15:
        status = 'REWORK'
        defect = random.choice([d for d in CONSTRAINTS["Defect_Types"] if d])
    else:
        status = 'PASS'
        defect = None

    return {
        "Operation_ID": op_id,
        "Production_Order": f"MO{random.randint(7000000, 7099999)}",
        "Serial_Number": f"SN{random.randint(2000000000, 2099999999)}",
        "Operation_Date": today,
        "Work_Center": f"WC{random.randint(1000, 1050)}",
        "Machine_ID": f"MCH{random.randint(100, 400)}",
        "Machine_Type": random.choice(CONSTRAINTS["Machine_Types"]),
        "Operation_Type": random.choice(CONSTRAINTS["Operation_Types"]),
        "Operator_ID": f"OPR{random.randint(1000, 1150)}",
        "Shift": random.choice(['A', 'B', 'C']),
        "Product_Type": random.choice(CONSTRAINTS["Product_Types"]),
        "Operation_Sequence": random.randint(10, 900),
        "Tool_Number": f"TL{random.randint(10000, 99999)}",
        "Tool_Type": random.choice(CONSTRAINTS["Tool_Types"]),
        "Tool_Life_Used_Pct": round(random.uniform(0, 100), 1),
        "Spindle_Speed_RPM": random.randint(100, 4000),
        "Feed_Rate_MM_MIN": round(random.uniform(10, 800), 2),
        "Depth_Of_Cut_MM": round(random.uniform(0.01, 50), 2),
        "Coolant_Type": random.choice(CONSTRAINTS["Coolant_Types"]),
        "Coolant_Flow_LPM": round(random.uniform(0, 40), 1),
        "Cycle_Time_Seconds": round(random.uniform(30, 600), 1),
        "Setup_Time_Minutes": random.randint(5, 120),
        "Actual_Dimension_MM": round(random.uniform(50, 500), 3),
        "Tolerance_Upper_MM": round(random.uniform(0.01, 0.5), 3),
        "Tolerance_Lower_MM": round(random.uniform(-0.5, -0.01), 3),
        "Measured_Deviation_MM": deviation,
        "Surface_Roughness_RA": round(random.uniform(0.4, 6.3), 2),
        "Quality_Status": status,
        "Defect_Type": defect,
        "Power_Consumption_KW": round(random.uniform(5, 50), 2),
        "Vibration_Level_MM_S": round(random.uniform(0.5, 5.0), 2)
    }

def main():
    print("Starting Machining Feeder...")
    conn = get_db_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        while True:
            last_id = get_last_op_id(cursor)
            new_id = generate_next_id(last_id)
            data = generate_random_row(new_id)
            
            cols = list(data.keys())
            vals = list(data.values())
            placeholders = ", ".join(["%s"] * len(vals))
            cursor.execute(f"INSERT INTO machining_operations ({', '.join(cols)}) VALUES ({placeholders})", vals)
            conn.commit()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Inserted: {new_id} | Status: {data['Quality_Status']}")
            time.sleep(10)
    except KeyboardInterrupt: print("Stopping...")
    finally: conn.close()

if __name__ == "__main__":
    main()