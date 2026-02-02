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
    "Equipment_Types": ['BORING_MILL', 'MOLDING_LINE', 'CNC_MACHINE', 'CONVEYOR', 'HT_FURNACE'],
    "Maintenance_Types": ['BREAKDOWN', 'PREVENTIVE', 'PREDICTIVE', 'CORRECTIVE'],
    "Order_Types": {'BREAKDOWN': 'PM02', 'PREVENTIVE': 'PM01', 'PREDICTIVE': 'PM01', 'CORRECTIVE': 'PM03'},
    "Status": ['CLOSED', 'COMPLETED', 'CREATED', 'IN_PROGRESS', 'RELEASED'],
    "Failure_Codes": ['HYDR', 'MECH', 'SOFT', 'ELEC', 'PNEU', None],
    "Damage_Codes": ['DEFORM', 'WEAR', 'LEAK', 'BREAK', 'CORR', None],
    "Cause_Codes": ['AGE', 'OVERLOAD', 'DEFECT', 'IMPROPER_USE', 'EXTERNAL', None],
    "Plants": ['P1000', 'P1001']
}

def get_db_connection():
    try: return psycopg2.connect(**DB_CONFIG)
    except Exception as e: print(f"DB Error: {e}"); return None

def get_last_maintenance_order(cursor):
    """Fetches the last ID to continue sequence PM13xxxxxx"""
    cursor.execute("SELECT Maintenance_Order FROM equipment_maintenance ORDER BY Maintenance_Order DESC LIMIT 1;")
    result = cursor.fetchone()
    return result[0] if result else "PM13000000"

def generate_next_id(last_id):
    prefix = "PM"
    try:
        numeric_part = int(last_id.replace(prefix, ""))
        return f"{prefix}{numeric_part + 1:08d}"
    except: return f"{prefix}{int(time.time())}"

def generate_random_row(order_id):
    today = datetime.now()
    maint_type = random.choice(CONSTRAINTS["Maintenance_Types"])
    order_type = CONSTRAINTS["Order_Types"].get(maint_type, 'PM01')
    
    # Logic: Breakdowns have failure codes, Preventive usually don't
    if maint_type in ['BREAKDOWN', 'CORRECTIVE']:
        failure = random.choice([c for c in CONSTRAINTS["Failure_Codes"] if c])
        damage = random.choice([c for c in CONSTRAINTS["Damage_Codes"] if c])
        cause = random.choice([c for c in CONSTRAINTS["Cause_Codes"] if c])
        priority = random.choice([1, 2]) # High priority
    else:
        failure, damage, cause = None, None, None
        priority = random.choice([3, 4]) # Lower priority

    downtime = round(random.uniform(0, 48), 1)
    labor_hrs = round(random.uniform(0.5, 24), 1)
    
    # Cost Logic
    parts_cost = round(random.uniform(0, 5000), 2)
    labor_rate = 85 # USD/hr assumption
    labor_cost = round(labor_hrs * labor_rate, 2)
    total_cost = parts_cost + labor_cost

    return {
        "Maintenance_Order": order_id,
        "Equipment_Number": f"EQ{random.randint(100000, 999999)}",
        "Equipment_Type": random.choice(CONSTRAINTS["Equipment_Types"]),
        "Equipment_Description": f"Unit {random.randint(1, 100)}", # Simplified
        "Functional_Location": f"FL-{random.randint(1000, 9999)}",
        "Plant": random.choice(CONSTRAINTS["Plants"]),
        "Work_Center": f"WC{random.randint(1000, 1099)}",
        "Maintenance_Type": maint_type,
        "Order_Type": order_type,
        "Priority": priority,
        "Planned_Start": today,
        "Planned_End": today + timedelta(hours=random.randint(4, 48)),
        "Actual_Start": today + timedelta(minutes=random.randint(0, 60)),
        "Actual_End": None, # Assuming live ongoing or recently finished
        "Status": random.choice(CONSTRAINTS["Status"]),
        "Planner_Group": f"PG{random.randint(100, 999)}",
        "Main_Work_Center": f"WC{random.randint(1000, 1099)}",
        "Technician_ID": f"TECH{random.randint(5000, 5099)}",
        "Downtime_Hours": downtime,
        "Labor_Hours": labor_hrs,
        "Parts_Cost_USD": parts_cost,
        "Labor_Cost_USD": labor_cost,
        "Total_Cost_USD": total_cost,
        "Failure_Code": failure,
        "Damage_Code": damage,
        "Cause_Code": cause,
        "Spare_Parts_Used": random.randint(0, 10),
        "Next_Maintenance_Due": (today + timedelta(days=random.randint(30, 365))).date(),
        "Maintenance_Plan": f"MP{random.randint(100000, 999999)}" if maint_type == 'PREVENTIVE' else None,
        "Notification_Number": f"NOT{random.randint(1000000, 9999999)}",
        "Created_By": f"USR{random.randint(3000, 3100)}",
        "Created_Date": today.date()
    }

def main():
    print("Starting Maintenance Feeder...")
    conn = get_db_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        while True:
            last_id = get_last_maintenance_order(cursor)
            new_id = generate_next_id(last_id)
            data = generate_random_row(new_id)
            
            cols = list(data.keys())
            vals = list(data.values())
            placeholders = ", ".join(["%s"] * len(vals))
            cursor.execute(f"INSERT INTO equipment_maintenance ({', '.join(cols)}) VALUES ({placeholders})", vals)
            conn.commit()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Inserted: {new_id} | Type: {data['Maintenance_Type']}")
            time.sleep(10)
    except KeyboardInterrupt: print("Stopping...")
    finally: conn.close()

if __name__ == "__main__":
    main()