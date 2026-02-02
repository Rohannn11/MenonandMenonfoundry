import os
import time
import random
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

# Database Connection Config
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "port": os.getenv("DB_PORT")
}

# 2. Constraints & Learned Patterns
CONSTRAINTS = {
    "Inspector_ID_Prefix": "INS",
    "Inspector_ID_Range": (2000, 2050),
    "Inspection_Stage": ['IN_PROCESS', 'PATROL', 'INCOMING', 'FINAL'],
    "Sampling_Plan": ['NORMAL', 'TIGHTENED', 'REDUCED', '100_PCT'],
    "AQL_Level": [0.65, 1.0, 1.5, 2.5, 4.0],
    "Visual_Inspection": ['PASS', 'FAIL'],
    "NDT_Type": ['ULTRASONIC', 'MAGNETIC_PARTICLE', 'XRAY', 'DYE_PENETRANT', None],
    "Porosity_Level": ['NONE', 'ACCEPTABLE', 'REJECT', None],
    "Overall_Decision": ['ACCEPT', 'REWORK', 'REJECT', 'CONDITIONAL'],
    "Rejection_Code": ['POR003', 'SUR002', 'INC005', 'DIM001', None]
}

def get_db_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        return None

def get_last_inspection_lot(cursor):
    """Fetches the last sequential ID from the DB."""
    query = "SELECT Inspection_Lot FROM quality_inspections ORDER BY Inspection_Lot DESC LIMIT 1;"
    cursor.execute(query)
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return "IL11000000"  # Default start if table is empty

def generate_next_id(last_id):
    """Increments IL11099999 -> IL11100000"""
    prefix = "IL"
    try:
        numeric_part = int(last_id.replace(prefix, ""))
        new_numeric = numeric_part + 1
        return f"{prefix}{new_numeric:08d}"
    except ValueError:
        return f"{prefix}{int(time.time())}"

def generate_random_row(lot_id):
    """Generates a row with logical consistency (e.g. Defects lead to Rejection)"""
    
    today = datetime.now()
    stage = random.choice(CONSTRAINTS["Inspection_Stage"])
    
    # Conditional Logic: Incoming material has 'GR' batch, others have 'CB'
    if stage == 'INCOMING':
        batch_num = f"GR{random.randint(8000000, 8999999)}"
    else:
        batch_num = f"CB{random.randint(8000000, 8999999)}"

    # Defect Logic
    if random.random() > 0.85: # 15% chance of issues
        defects = random.randint(1, 5)
        decision = random.choice(['REWORK', 'REJECT', 'CONDITIONAL'])
        visual = random.choice(['PASS', 'FAIL'])
        rej_code = random.choice(CONSTRAINTS["Rejection_Code"]) if decision == 'REJECT' else None
    else:
        defects = 0
        decision = 'ACCEPT'
        visual = 'PASS'
        rej_code = None

    ndt_type = random.choice(CONSTRAINTS["NDT_Type"])
    
    return {
        "Inspection_Lot": lot_id,
        "Inspection_Date": today,
        "Inspector_ID": f"INS{random.randint(2000, 2050)}",
        "Inspection_Stage": stage,
        "Material_Number": f"MAT{random.randint(1000000, 1099999)}",
        "Batch_Number": batch_num,
        "Quantity_Inspected": random.randint(10, 500),
        "Sampling_Plan": random.choice(CONSTRAINTS["Sampling_Plan"]),
        "AQL_Level": random.choice(CONSTRAINTS["AQL_Level"]),
        "Visual_Inspection": visual,
        "Dimensional_Check": 'PASS' if random.random() > 0.1 else 'FAIL',
        "CMM_Measurement": 'PASS' if random.random() > 0.1 else 'FAIL',
        "Hardness_Test_HB": round(random.uniform(150, 300), 1) if random.random() > 0.5 else None,
        "Tensile_Strength_MPA": round(random.uniform(200, 500), 1) if random.random() > 0.5 else None,
        "Elongation_Percentage": round(random.uniform(2, 20), 1) if random.random() > 0.5 else None,
        "NDT_Type": ndt_type,
        "NDT_Result": ('PASS' if random.random() > 0.1 else 'FAIL') if ndt_type else None,
        "Pressure_Test_Result": 'PASS' if random.random() > 0.1 else 'FAIL',
        "Pressure_Test_Value_BAR": round(random.uniform(2, 20), 1),
        "Leak_Test_Result": 'PASS' if random.random() > 0.1 else 'FAIL',
        "Surface_Finish_RA": round(random.uniform(0.8, 12.5), 2),
        "Porosity_Level": random.choice(CONSTRAINTS["Porosity_Level"]),
        "Defect_Count": defects,
        "Major_Defects": 0 if defects == 0 else random.randint(0, defects),
        "Minor_Defects": 0 if defects == 0 else random.randint(0, defects),
        "Critical_Defects": 0 if defects == 0 else random.randint(0, 1),
        "Overall_Decision": decision,
        "Rejection_Code": rej_code,
        "Certificate_Number": f"COC{random.randint(1000000, 9999999)}" if decision == 'ACCEPT' else None,
        "Calibration_Due_Date": (today + timedelta(days=random.randint(100, 700))).date(),
        "Inspection_Duration_Min": random.randint(5, 120)
    }

def main():
    print("Starting Quality Inspection Feeder...")
    conn = get_db_connection()
    if not conn: return

    try:
        cursor = conn.cursor()
        while True:
            # 1. Dynamic ID Fetch
            last_id = get_last_inspection_lot(cursor)
            new_id = generate_next_id(last_id)
            
            # 2. Generate Data
            data = generate_random_row(new_id)
            
            # 3. Insert Data
            cols = list(data.keys())
            vals = list(data.values())
            placeholders = ", ".join(["%s"] * len(vals))
            stmt = f"INSERT INTO quality_inspections ({', '.join(cols)}) VALUES ({placeholders})"
            
            cursor.execute(stmt, vals)
            conn.commit()
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Inserted: {new_id} | Result: {data['Overall_Decision']}")
            time.sleep(10)

    except KeyboardInterrupt:
        print("\nStopping Feeder...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()