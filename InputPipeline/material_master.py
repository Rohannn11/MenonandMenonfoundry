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
    "Material_Types": ['CYLINDER_LINER', 'COATING', 'ENGINE_BLOCK', 'RAW_STEEL', 'SAND', 'BINDER', 'CORE', 'ALLOY'],
    "Base_Units": {'SAND': 'KG', 'RAW_STEEL': 'KG', 'BINDER': 'KG', 'COATING': 'KG', 'ALLOY': 'KG', 'DEFAULT': 'EA'},
    "Valuation_Classes": ['VC1121', 'VC1021', 'VC2154', 'VC2451', 'VC2886'],
    "Procurement_Types": ['E', 'F'], # E=In-house, F=External
    "ABC_Indicators": ['A', 'B', 'C'],
    "Plants": ['P1000', 'P1001']
}

def get_db_connection():
    try: return psycopg2.connect(**DB_CONFIG)
    except Exception as e: print(f"DB Error: {e}"); return None

def get_last_material_number(cursor):
    """Fetches the last ID to continue sequence MAT01xxxxxx"""
    cursor.execute("SELECT Material_Number FROM material_master ORDER BY Material_Number DESC LIMIT 1;")
    result = cursor.fetchone()
    return result[0] if result else "MAT01000000"

def generate_next_id(last_id):
    prefix = "MAT"
    try:
        numeric_part = int(last_id.replace(prefix, ""))
        return f"{prefix}{numeric_part + 1:08d}"
    except: return f"{prefix}{int(time.time())}"

def generate_random_row(mat_id):
    today = datetime.now()
    mat_type = random.choice(CONSTRAINTS["Material_Types"])
    unit = CONSTRAINTS["Base_Units"].get(mat_type, CONSTRAINTS["Base_Units"]['DEFAULT'])
    
    # Weight Logic: Gross > Net
    net_wt = round(random.uniform(0.1, 500), 2)
    gross_wt = round(net_wt * random.uniform(1.05, 1.2), 2)
    
    # Procurement Logic: Raw materials usually F (External), Finished Goods E (In-house)
    if mat_type in ['RAW_STEEL', 'SAND', 'BINDER', 'ALLOY']:
        proc_type = 'F'
        mrp_type = 'VB' # Reorder point planning
    else:
        proc_type = 'E'
        mrp_type = 'PD' # MRP

    # Generate a variant ID for description
    variant_id = mat_id.replace("MAT01", "").lstrip('0')

    return {
        "Material_Number": mat_id,
        "Material_Type": mat_type,
        "Description": f"{mat_type.replace('_', ' ')} - Variant {variant_id}",
        "Base_Unit": unit,
        "Material_Group": f"MG{random.randint(1000, 5000)}",
        "Net_Weight_KG": net_wt,
        "Gross_Weight_KG": gross_wt,
        "Standard_Price_USD": round(random.uniform(1, 5000), 2),
        "Valuation_Class": random.choice(CONSTRAINTS["Valuation_Classes"]),
        "Created_Date": today.date(),
        "Plant": random.choice(CONSTRAINTS["Plants"]),
        "Storage_Location": f"SL{random.randint(100, 999)}",
        "ABC_Indicator": random.choice(CONSTRAINTS["ABC_Indicators"]),
        "MRP_Type": mrp_type,
        "Lot_Size": random.choice([10, 50, 100, 500]),
        "Safety_Stock": random.randint(0, 1000),
        "Procurement_Type": proc_type,
        "Special_Procurement": random.choice([50, 52, None]),
        "Quality_Inspection": 'Y' if random.random() > 0.3 else 'N'
    }

def main():
    print("Starting Material Master Feeder...")
    conn = get_db_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        while True:
            last_id = get_last_material_number(cursor)
            new_id = generate_next_id(last_id)
            data = generate_random_row(new_id)
            
            cols = list(data.keys())
            vals = list(data.values())
            placeholders = ", ".join(["%s"] * len(vals))
            cursor.execute(f"INSERT INTO material_master ({', '.join(cols)}) VALUES ({placeholders})", vals)
            conn.commit()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Inserted: {new_id} | Type: {data['Material_Type']}")
            time.sleep(10)
    except KeyboardInterrupt: print("Stopping...")
    finally: conn.close()

if __name__ == "__main__":
    main()