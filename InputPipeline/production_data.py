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

# 2. Constraints & Learned Patterns (Hardcoded from analysis)
CONSTRAINTS = {
    "Order_Type": ["YP01"],
    "Product_Type": ["ENGINE_BLOCK", "CYLINDER_HEAD", "CYLINDER_LINER"],
    "Plant": ["P1000", "P1001"],
    "Unit": ["EA"],
    "Order_Status": ["IN_PROCESS", "COMPLETED", "CLOSED", "CREATED", "RELEASED"],
    "Work_Center_Prefix": "WC",
    "Work_Center_Range": (1000, 1100),
    "Users_Prefix": "USR",
    "Users_Range": (3000, 3200),
    "Priority_Range": (1, 5)
}

def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def get_last_production_order(cursor):
    """
    Fetches the highest Production_Order ID from the database 
    to ensure sequential continuity.
    """
    query = "SELECT Production_Order FROM production_orders ORDER BY Production_Order DESC LIMIT 1;"
    cursor.execute(query)
    result = cursor.fetchone()
    
    if result:
        return result[0]
    else:
        # Fallback if table is empty
        return "MO07000000" 

def generate_next_id(last_id):
    """
    Parses 'MO07099999', extracts the number, increments it, 
    and returns the new ID.
    """
    prefix = "MO"
    try:
        # Extract numeric part (everything after MO)
        numeric_part = int(last_id.replace(prefix, ""))
        new_numeric = numeric_part + 1
        # Format back to string with leading zeros (assuming length 8 for digits)
        return f"{prefix}{new_numeric:08d}"
    except ValueError:
        # Fail-safe if format is weird, just add timestamp
        return f"{prefix}{int(time.time())}"

def generate_random_row(next_order_id):
    """Generates a dictionary of values for a new row."""
    
    # Dates
    today = datetime.now()
    planned_start = today + timedelta(days=random.randint(1, 30))
    planned_end = planned_start + timedelta(days=random.randint(10, 100))
    
    # Quantities
    qty = random.randint(10, 500)
    
    # Financials
    std_cost = round(random.uniform(1000, 45000), 2)
    actual_cost = round(std_cost * random.uniform(0.9, 1.1), 2)
    variance = round(actual_cost - std_cost, 2)

    return {
        "Production_Order": next_order_id,
        "Order_Type": random.choice(CONSTRAINTS["Order_Type"]),
        "Material_Number": f"MAT{random.randint(1000000, 1020000)}",
        "Product_Type": random.choice(CONSTRAINTS["Product_Type"]),
        "Plant": random.choice(CONSTRAINTS["Plant"]),
        "Order_Quantity": qty,
        "Confirmed_Quantity": random.randint(0, qty),
        "Scrap_Quantity": random.randint(0, int(qty * 0.1)),
        "Unit": "EA",
        "Planned_Start_Date": planned_start.date(),
        "Planned_End_Date": planned_end.date(),
        "Actual_Start_Date": today.date() if random.random() > 0.2 else None,
        "Actual_End_Date": None,
        "Order_Status": random.choice(CONSTRAINTS["Order_Status"]),
        "Priority": random.randint(1, 5),
        "Production_Scheduler": f"USR{random.randint(3000, 3020)}",
        "Production_Supervisor": f"SUP{random.randint(4000, 4020)}",
        "Work_Center": f"WC{random.randint(1000, 1100)}",
        "Routing_Number": f"RTG{random.randint(100000, 999999)}",
        "BOM_Number": f"BOM{random.randint(5000000, 5099999)}",
        "Sales_Order": f"SO{random.randint(6000000, 6999999)}",
        "Customer": f"CUST{random.randint(10000, 99999)}",
        "Planned_Costs_USD": round(std_cost * 1.05, 2),
        "Actual_Costs_USD": actual_cost,
        "Standard_Cost_USD": std_cost,
        "Variance_USD": variance,
        "Settlement_Rule": f"SET{random.randint(1000, 9999)}",
        "Profit_Center": f"PC{random.randint(1000, 9999)}",
        "Created_By": f"USR{random.randint(3000, 3200)}",
        "Created_Date": today.date(),
        "Changed_By": None,
        "Changed_Date": None
    }

def main():
    print("Starting Live Data Feeder...")
    
    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        
        while True:
            # 1. Fetch the very latest ID from DB (Dynamic Step)
            last_id = get_last_production_order(cursor)
            new_id = generate_next_id(last_id)
            
            # 2. Generate Data
            data = generate_random_row(new_id)
            
            # 3. Construct Insert Query
            cols = list(data.keys())
            vals = list(data.values())
            placeholders = ", ".join(["%s"] * len(vals))
            columns_str = ", ".join(cols)
            
            insert_query = f"INSERT INTO production_orders ({columns_str}) VALUES ({placeholders})"
            
            # 4. Execute
            cursor.execute(insert_query, vals)
            conn.commit()
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Inserted: {new_id} | Status: {data['Order_Status']}")
            
            # 5. Wait
            time.sleep(10)

    except KeyboardInterrupt:
        print("\nStopping Feeder...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()