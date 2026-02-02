import os
import time
import random
import psycopg2
from datetime import datetime, timedelta
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
    "Molding_Lines": ['ML1', 'ML2', 'ML4', 'ML5', 'ML7'],
    "Molding_Types": ['GREEN_SAND', 'RESIN_SAND', 'SHELL_MOLD', 'INVESTMENT'],
    "Product_Types": ['ENGINE_BLOCK', 'CYLINDER_HEAD', 'CYLINDER_LINER'],
    "Sand_Types": ['SILICA', 'CHROMITE', 'ZIRCON', 'OLIVINE'],
    "Binder_Types": ['PHENOLIC', 'BENTONITE', 'ALKALINE_PHENOLIC', 'FURAN'],
    "Defect_Types": ['CRACK', 'SURFACE_ROUGHNESS', 'DIMENSIONAL', 'DEFORMATION', None],
    "Quality_Checks": ['PASS', 'FAIL', 'REWORK']
}

def get_db_connection():
    try: return psycopg2.connect(**DB_CONFIG)
    except Exception as e: print(f"DB Error: {e}"); return None

def get_last_production_order(cursor):
    """Fetches the last ID to continue sequence MO07xxxxxx"""
    cursor.execute("SELECT Production_Order FROM molding_records ORDER BY Production_Order DESC LIMIT 1;")
    result = cursor.fetchone()
    return result[0] if result else "MO07000000"

def generate_next_id(last_id):
    prefix = "MO"
    try:
        numeric_part = int(last_id.replace(prefix, ""))
        return f"{prefix}{numeric_part + 1:08d}"
    except: return f"{prefix}{int(time.time())}"

def generate_random_row(order_id):
    today = datetime.now()
    mold_date = (today - timedelta(days=random.randint(0, 5))).date()
    
    planned = random.randint(10, 500)
    # Actual is usually close to planned, sometimes less, sometimes more (overproduction)
    actual = int(planned * random.uniform(0.8, 1.1))
    
    # Logic: Defect leads to Fail/Rework
    if random.random() > 0.85:
        defect = random.choice([d for d in CONSTRAINTS["Defect_Types"] if d])
        quality = random.choice(['FAIL', 'REWORK'])
    else:
        defect = None
        quality = 'PASS'

    return {
        "Production_Order": order_id,
        "Molding_Line": random.choice(CONSTRAINTS["Molding_Lines"]),
        "Molding_Type": random.choice(CONSTRAINTS["Molding_Types"]),
        "Product_Type": random.choice(CONSTRAINTS["Product_Types"]),
        "Pattern_Number": f"PTN{random.randint(10000, 99999)}",
        "Mold_Date": mold_date,
        "Shift": random.choice(['A', 'B', 'C']),
        "Operator_ID": f"OPR{random.randint(1050, 1150)}",
        "Planned_Quantity": planned,
        "Actual_Quantity": actual,
        "Sand_Mix_Batch": f"SMX{random.randint(100000, 999999)}",
        "Sand_Type": random.choice(CONSTRAINTS["Sand_Types"]),
        "Binder_Type": random.choice(CONSTRAINTS["Binder_Types"]),
        "Binder_Percentage": round(random.uniform(1.0, 3.5), 2),
        "Moisture_Content_Pct": round(random.uniform(2.5, 4.5), 2),
        "Compressive_Strength_PSI": round(random.uniform(10, 25), 1),
        "Permeability": random.randint(80, 200),
        "Green_Compression_KPA": round(random.uniform(80, 150), 1),
        "Mold_Hardness": random.randint(70, 95),
        "Core_Count": random.randint(2, 20),
        "Cycle_Time_Seconds": random.randint(45, 180),
        "Sand_Temperature_C": round(random.uniform(20, 35), 1),
        "Ambient_Humidity_Pct": round(random.uniform(40, 70), 1),
        "Quality_Check": quality,
        "Defect_Type": defect,
        "Mold_Weight_KG": round(random.uniform(500, 2000), 1),
        "Setup_Time_Min": random.randint(30, 120)
    }

def main():
    print("Starting Molding Records Feeder...")
    conn = get_db_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        while True:
            last_id = get_last_production_order(cursor)
            new_id = generate_next_id(last_id)
            data = generate_random_row(new_id)
            
            cols = list(data.keys())
            vals = list(data.values())
            placeholders = ", ".join(["%s"] * len(vals))
            cursor.execute(f"INSERT INTO molding_records ({', '.join(cols)}) VALUES ({placeholders})", vals)
            conn.commit()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Inserted: {new_id} | Status: {data['Quality_Check']}")
            time.sleep(10)
    except KeyboardInterrupt: print("Stopping...")
    finally: conn.close()

if __name__ == "__main__":
    main()