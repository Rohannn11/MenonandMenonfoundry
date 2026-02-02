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
    "Furnace_IDs": [f"FUR10{i}" for i in range(1, 9)],
    "Furnace_Types": ['INDUCTION', 'CUPOLA', 'ELECTRIC_ARC'],
    "Target_Alloys": ['GG25', 'GG30', 'GG40', 'GGG60', 'GGG70'],
    "Inoculation_Types": ['FeSi75', 'Bi-based', 'FeSi75+Sr', 'Post-inoculation'],
    "Rejection_Reasons": ['LOW_CARBON', 'HIGH_PHOSPHORUS', 'HIGH_SULFUR', 'TEMPERATURE', None],
    "Quality_Status": ['APPROVED', 'REJECTED', 'CONDITIONAL']
}

def get_db_connection():
    try: return psycopg2.connect(**DB_CONFIG)
    except Exception as e: print(f"DB Error: {e}"); return None

def get_last_heat_number(cursor):
    """Fetches the last ID to continue sequence HT20261xxxxx"""
    cursor.execute("SELECT Heat_Number FROM melting_heat_records ORDER BY Heat_Number DESC LIMIT 1;")
    result = cursor.fetchone()
    return result[0] if result else "HT2026100000"

def generate_next_id(last_id):
    prefix = "HT"
    try:
        numeric_part = int(last_id.replace(prefix, ""))
        return f"{prefix}{numeric_part + 1:010d}"
    except: return f"{prefix}{int(time.time())}"

def generate_random_row(heat_id):
    today = datetime.now()
    
    # Composition Logic: Variations based on random noise
    carbon = round(random.uniform(3.0, 4.0), 3)
    silicon = round(random.uniform(1.8, 2.8), 3)
    
    # Quality Logic
    if carbon < 3.2 or random.random() > 0.9:
        status = 'REJECTED'
        reason = 'LOW_CARBON' if carbon < 3.2 else random.choice(CONSTRAINTS["Rejection_Reasons"])
    else:
        status = 'APPROVED'
        reason = None
        
    tap_temp = round(random.uniform(1380, 1480), 1)
    # Pour temp is always slightly less than Tap temp due to heat loss
    pour_temp = round(tap_temp - random.uniform(10, 50), 1)

    return {
        "Heat_Number": heat_id,
        "Furnace_ID": random.choice(CONSTRAINTS["Furnace_IDs"]),
        "Furnace_Type": random.choice(CONSTRAINTS["Furnace_Types"]),
        "Melt_Date": (today - timedelta(days=random.randint(0, 5))).date(),
        "Shift": random.choice(['A', 'B', 'C']),
        "Operator_ID": f"OPR{random.randint(1000, 1150)}",
        "Target_Alloy": random.choice(CONSTRAINTS["Target_Alloys"]),
        "Charge_Weight_KG": round(random.uniform(8000, 15000), 1),
        "Scrap_Steel_KG": round(random.uniform(3000, 7000), 1),
        "Pig_Iron_KG": round(random.uniform(2000, 5000), 1),
        "Returns_KG": round(random.uniform(500, 2000), 1),
        "Alloy_Additions_KG": round(random.uniform(50, 300), 1),
        "Carbon_Percentage": carbon,
        "Silicon_Percentage": silicon,
        "Manganese_Percentage": round(random.uniform(0.3, 0.8), 3),
        "Phosphorus_Percentage": round(random.uniform(0.02, 0.1), 3),
        "Sulfur_Percentage": round(random.uniform(0.01, 0.08), 3),
        "Chromium_Percentage": round(random.uniform(0.05, 0.3), 3),
        "Nickel_Percentage": round(random.uniform(0.01, 0.2), 3),
        "Molybdenum_Percentage": round(random.uniform(0.01, 0.15), 3),
        "Copper_Percentage": round(random.uniform(0.05, 0.5), 3),
        "Tap_Temperature_C": tap_temp,
        "Pour_Temperature_C": pour_temp,
        "Holding_Time_Min": random.randint(15, 90),
        "Inoculation_Type": random.choice(CONSTRAINTS["Inoculation_Types"]),
        "Inoculation_Amount_KG": round(random.uniform(5, 50), 1),
        "Spectro_Test_ID": f"SPT{random.randint(1000000, 9999999)}",
        "Quality_Status": status,
        "Rejection_Reason": reason,
        "Yield_Percentage": round(random.uniform(75, 92), 2),
        "Energy_Consumed_KWH": round(random.uniform(3000, 6000), 1),
        "Melting_Duration_Min": random.randint(90, 240)
    }

def main():
    print("Starting Melting Heat Feeder...")
    conn = get_db_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        while True:
            last_id = get_last_heat_number(cursor)
            new_id = generate_next_id(last_id)
            data = generate_random_row(new_id)
            
            cols = list(data.keys())
            vals = list(data.values())
            placeholders = ", ".join(["%s"] * len(vals))
            cursor.execute(f"INSERT INTO melting_heat_records ({', '.join(cols)}) VALUES ({placeholders})", vals)
            conn.commit()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Inserted: {new_id} | Alloy: {data['Target_Alloy']}")
            time.sleep(10)
    except KeyboardInterrupt: print("Stopping...")
    finally: conn.close()

if __name__ == "__main__":
    main()