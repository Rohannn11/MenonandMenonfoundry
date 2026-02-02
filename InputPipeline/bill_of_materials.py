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
    "Parent_Desc": ['ENGINE_BLOCK Assembly', 'CYLINDER_HEAD Assembly'],
    "Component_Types": ['SAND', 'RAW_STEEL', 'BINDER', 'ALLOY', 'RAW_IRON'],
    "Component_Units": {'SAND': 'KG', 'RAW_STEEL': 'KG', 'BINDER': 'L', 'ALLOY': 'KG'},
    "BOM_Status": ['ACTIVE', 'PENDING', 'INACTIVE'],
    "Plants": ['P1000', 'P1001'],
    "Criticality": ['LOW', 'MEDIUM', 'HIGH']
}

def get_db_connection():
    try: return psycopg2.connect(**DB_CONFIG)
    except Exception as e: print(f"DB Error: {e}"); return None

def get_last_bom_number(cursor):
    """Fetches the last ID to continue sequence BOM05xxxxxx"""
    cursor.execute("SELECT BOM_Number FROM bill_of_materials ORDER BY BOM_Number DESC LIMIT 1;")
    result = cursor.fetchone()
    return result[0] if result else "BOM05000000"

def generate_next_id(last_id):
    prefix = "BOM"
    try:
        numeric_part = int(last_id.replace(prefix, ""))
        return f"{prefix}{numeric_part + 1:08d}"
    except: return f"{prefix}{int(time.time())}"

def generate_random_row(bom_id):
    today = datetime.now()
    valid_from = (today - timedelta(days=random.randint(0, 100))).date()
    valid_to = (valid_from + timedelta(days=random.randint(365, 1000)))
    
    comp_type = random.choice(CONSTRAINTS["Component_Types"])
    # Default to KG if unit not found
    unit = CONSTRAINTS["Component_Units"].get(comp_type, 'KG')
    
    status = random.choice(CONSTRAINTS["BOM_Status"])
    # If pending, assign a Change Number (ECN)
    change_num = f"ECN{random.randint(100000, 999999)}" if status == 'PENDING' else None

    return {
        "BOM_Number": bom_id,
        "Parent_Material": f"MAT{random.randint(1000000, 1005000)}",
        "Parent_Description": random.choice(CONSTRAINTS["Parent_Desc"]),
        "Component_Material": f"MAT{random.randint(1050000, 1099999)}",
        "Component_Type": comp_type,
        "Component_Quantity": round(random.uniform(0.1, 500), 3),
        "Component_Unit": unit,
        "Item_Number": random.randint(100, 200),
        "BOM_Level": random.randint(1, 4),
        "Valid_From": valid_from,
        "Valid_To": valid_to,
        "BOM_Status": status,
        "Change_Number": change_num,
        "Scrap_Percentage": round(random.uniform(0, 15), 2),
        "Plant": random.choice(CONSTRAINTS["Plants"]),
        "Alternative_BOM": random.choice([1, 2]) if random.random() > 0.8 else None,
        "Component_Criticality": random.choice(CONSTRAINTS["Criticality"])
    }

def main():
    print("Starting BOM Feeder...")
    conn = get_db_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        while True:
            last_id = get_last_bom_number(cursor)
            new_id = generate_next_id(last_id)
            data = generate_random_row(new_id)
            
            cols = list(data.keys())
            vals = list(data.values())
            placeholders = ", ".join(["%s"] * len(vals))
            cursor.execute(f"INSERT INTO bill_of_materials ({', '.join(cols)}) VALUES ({placeholders})", vals)
            conn.commit()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Inserted: {new_id} | Status: {data['BOM_Status']}")
            time.sleep(10)
    except KeyboardInterrupt: print("Stopping...")
    finally: conn.close()

if __name__ == "__main__":
    main()