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
    "Ladle_Numbers": ['LAD1', 'LAD5', 'LAD10', 'LAD11', 'LAD13'],
    "Gating_Systems": ['TOP', 'SIDE', 'MULTI', 'BOTTOM'],
    "Riser_Types": ['OPEN', 'BLIND', 'INSULATED'],
    "Filter_Types": ['CERAMIC_FOAM', 'PRESSED_CERAMIC', 'EXTRUDED', 'NONE'],
    "Defects": ['SHRINKAGE', 'POROSITY', 'COLD_SHUT', 'INCLUSION', 'NONE'],
    "Quality_Grades": ['A', 'B', 'C', 'SCRAP'],
    "Product_Types": ['ENGINE_BLOCK', 'CYLINDER_HEAD', 'CYLINDER_LINER']
}

def get_db_connection():
    try: return psycopg2.connect(**DB_CONFIG)
    except Exception as e: print(f"DB Error: {e}"); return None

def get_last_casting_batch(cursor):
    """Fetches the last ID to continue sequence CB08xxxxxx"""
    cursor.execute("SELECT Casting_Batch FROM casting_records ORDER BY Casting_Batch DESC LIMIT 1;")
    result = cursor.fetchone()
    return result[0] if result else "CB08000000"

def generate_next_id(last_id):
    prefix = "CB"
    try:
        numeric_part = int(last_id.replace(prefix, ""))
        return f"{prefix}{numeric_part + 1:08d}"
    except: return f"{prefix}{int(time.time())}"

def generate_random_row(batch_id):
    today = datetime.now()
    
    # Time logic
    pour_start = today
    pour_duration = random.randint(10, 60) # minutes
    pour_end = pour_start + timedelta(minutes=pour_duration)
    
    # Metal stats
    poured_weight = round(random.uniform(300, 1800), 1)
    exp_castings = random.randint(10, 150)
    
    # Quality Logic
    if random.random() > 0.9: # 10% chance of major issues
        grade = 'SCRAP'
        defect = random.choice([d for d in CONSTRAINTS["Defects"] if d != 'NONE'])
        scrap = random.randint(5, int(exp_castings * 0.5))
    else:
        grade = random.choice(['A', 'B', 'C'])
        defect = 'NONE'
        scrap = random.randint(0, 3)
    
    good = max(0, exp_castings - scrap)
    
    # Derived Yield
    yield_pct = round((good / exp_castings) * 100, 2) if exp_castings > 0 else 0

    return {
        "Casting_Batch": batch_id,
        "Heat_Number": f"HT{random.randint(2000000000, 2099999999)}",
        "Production_Order": f"MO{random.randint(7000000, 7099999)}", # Random reference
        "Casting_Date": today,
        "Pour_Start_Time": pour_start.time(),
        "Pour_End_Time": pour_end.time(),
        "Shift": random.choice(['A', 'B', 'C']),
        "Operator_ID": f"OPR{random.randint(1050, 1150)}",
        "Product_Type": random.choice(CONSTRAINTS["Product_Types"]),
        "Ladle_Number": random.choice(CONSTRAINTS["Ladle_Numbers"]),
        "Ladle_Capacity_KG": random.choice([1000, 1500, 2000]),
        "Metal_Weight_Poured_KG": poured_weight,
        "Pouring_Temperature_C": round(random.uniform(1350, 1450), 1),
        "Pouring_Rate_KG_MIN": round(random.uniform(50, 200), 1),
        "Molds_Poured": random.randint(10, 50),
        "Expected_Castings": exp_castings,
        "Good_Castings": good,
        "Scrap_Castings": scrap,
        "Yield_Percentage": yield_pct,
        "Gating_System_Type": random.choice(CONSTRAINTS["Gating_Systems"]),
        "Riser_Type": random.choice(CONSTRAINTS["Riser_Types"]),
        "Cooling_Time_Hours": round(random.uniform(4, 24), 1),
        "Ambient_Temperature_C": round(random.uniform(18, 32), 1),
        "Pouring_Height_MM": random.randint(100, 400),
        "Filter_Used": 'YES' if random.random() > 0.2 else 'NO',
        "Filter_Type": random.choice(CONSTRAINTS["Filter_Types"]),
        "Inoculation_In_Ladle": 'YES' if random.random() > 0.1 else 'NO',
        "Defects_Detected": defect,
        "Quality_Grade": grade
    }

def main():
    print("Starting Casting Records Feeder...")
    conn = get_db_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        while True:
            last_id = get_last_casting_batch(cursor)
            new_id = generate_next_id(last_id)
            data = generate_random_row(new_id)
            
            cols = list(data.keys())
            vals = list(data.values())
            # Convert Time objects to string for PostgreSQL if needed, 
            # but psycopg2 handles datetime.time usually.
            placeholders = ", ".join(["%s"] * len(vals))
            cursor.execute(f"INSERT INTO casting_records ({', '.join(cols)}) VALUES ({placeholders})", vals)
            conn.commit()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Inserted: {new_id} | Grade: {data['Quality_Grade']}")
            time.sleep(10)
    except KeyboardInterrupt: print("Stopping...")
    finally: conn.close()

if __name__ == "__main__":
    main()