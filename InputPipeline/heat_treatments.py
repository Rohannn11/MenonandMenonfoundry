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
    "Furnace_ID_Prefix": "HTFUR",
    "Furnace_Range": (1, 15),
    "Furnace_Types": ['CAR_BOTTOM', 'PIT', 'BOX', 'CONTINUOUS'],
    "Treatment_Types": ['ANNEALING', 'STRESS_RELIEF', 'HARDENING', 'NORMALIZING', 'AGING'],
    "Cooling_Methods": ['FURNACE_COOL', 'FORCED_AIR', 'AIR_COOL', 'WATER_QUENCH', 'OIL_QUENCH'],
    "Atmospheres": ['EXOTHERMIC', 'AIR', 'NITROGEN', 'ENDOTHERMIC'],
    "Microstructures": ['BAINITE', 'PEARLITE', 'MARTENSITE', 'FERRITE_PEARLITE'],
    "Rejection_Reasons": ['LOW_HARDNESS', 'DISTORTION', 'CRACKS', 'HIGH_HARDNESS', None],
    "Product_Types": ['ENGINE_BLOCK', 'CYLINDER_HEAD', 'CYLINDER_LINER']
}

def get_db_connection():
    try: return psycopg2.connect(**DB_CONFIG)
    except Exception as e: print(f"DB Error: {e}"); return None

def get_last_ht_batch(cursor):
    cursor.execute("SELECT HT_Batch_Number FROM heat_treatments ORDER BY HT_Batch_Number DESC LIMIT 1;")
    result = cursor.fetchone()
    return result[0] if result else "HT09000000"

def generate_next_id(last_id):
    prefix = "HT"
    try:
        numeric_part = int(last_id.replace(prefix, ""))
        return f"{prefix}{numeric_part + 1:08d}"
    except: return f"{prefix}{int(time.time())}"

def generate_random_row(batch_id):
    today = datetime.now()
    treat_date = (today + timedelta(days=random.randint(1, 30))).date()
    
    parts = random.randint(5, 200)
    weight = round(random.uniform(500, 5000), 1)
    target_temp = random.randint(150, 950)
    
    # Logic: High temp treatments consume more energy
    energy = round(target_temp * random.uniform(0.8, 2.5), 1)
    
    # Logic: Status based on random failure chance
    if random.random() > 0.9:
        status = 'REJECTED'
        reason = random.choice([r for r in CONSTRAINTS["Rejection_Reasons"] if r])
    elif random.random() > 0.8:
        status = 'REWORK'
        reason = random.choice([r for r in CONSTRAINTS["Rejection_Reasons"] if r])
    else:
        status = 'APPROVED'
        reason = None

    return {
        "HT_Batch_Number": batch_id,
        "Casting_Batch": f"CB{random.randint(8000000, 8099999)}",
        "Furnace_ID": f"HTFUR{random.randint(1, 15)}",
        "Furnace_Type": random.choice(CONSTRAINTS["Furnace_Types"]),
        "Treatment_Date": treat_date,
        "Shift": random.choice(['A', 'B', 'C']),
        "Operator_ID": f"OPR{random.randint(1000, 1200)}",
        "Treatment_Type": random.choice(CONSTRAINTS["Treatment_Types"]),
        "Product_Type": random.choice(CONSTRAINTS["Product_Types"]),
        "Parts_Count": parts,
        "Total_Load_Weight_KG": weight,
        "Target_Temperature_C": target_temp,
        "Actual_Temperature_C": round(target_temp * random.uniform(0.95, 1.05), 1),
        "Heating_Rate_C_HR": round(random.uniform(50, 150), 1),
        "Holding_Time_Hours": round(random.uniform(1, 24), 1),
        "Cooling_Method": random.choice(CONSTRAINTS["Cooling_Methods"]),
        "Cooling_Rate_C_HR": round(random.uniform(10, 200), 1),
        "Atmosphere": random.choice(CONSTRAINTS["Atmospheres"]),
        "Atmosphere_Flow_CFH": round(random.uniform(0, 500), 1),
        "Carbon_Potential_Pct": round(random.uniform(0, 1), 2),
        "Pre_HT_Hardness_HB": random.randint(140, 220),
        "Post_HT_Hardness_HB": random.randint(160, 280),
        "Hardness_Test_Location": random.choice(['MIDDLE', 'BOTTOM', 'TOP', 'MULTIPLE']),
        "Microstructure": random.choice(CONSTRAINTS["Microstructures"]),
        "Quality_Status": status,
        "Rejection_Reason": reason,
        "Energy_Consumed_KWH": energy,
        "Cycle_Time_Hours": round(random.uniform(8, 36), 1)
    }

def main():
    print("Starting Heat Treatment Feeder...")
    conn = get_db_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        while True:
            last_id = get_last_ht_batch(cursor)
            new_id = generate_next_id(last_id)
            data = generate_random_row(new_id)
            
            cols = list(data.keys())
            vals = list(data.values())
            placeholders = ", ".join(["%s"] * len(vals))
            cursor.execute(f"INSERT INTO heat_treatments ({', '.join(cols)}) VALUES ({placeholders})", vals)
            conn.commit()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Inserted: {new_id}")
            time.sleep(10)
    except KeyboardInterrupt: print("Stopping...")
    finally: conn.close()

if __name__ == "__main__":
    main()