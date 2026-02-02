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
    "Movement_Data": [
        {"Type": "GI_PRODUCTION", "Code": 261},
        {"Type": "TRANSFER", "Code": 311},
        {"Type": "SCRAP", "Code": 551},
        {"Type": "GR_PO", "Code": 101},
        {"Type": "GR_PRODUCTION", "Code": 101},
        {"Type": "RETURN", "Code": 122}
    ],
    "Material_Type": ['BINDER', 'SAND', 'ENGINE_BLOCK', 'CYLINDER_LINER', 'ALLOY', 'CYLINDER_HEAD'],
    "Plant": ['P1000', 'P1001'],
    "Unit": "KG",
    "Currency": "USD",
    "Valuation_Type": ['STANDARD', 'MOVING_AVG', None],
    "Reason_Code": ['PRODUCTION', 'QUALITY', 'DAMAGED', None]
}

def get_db_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        return None

def get_last_document_number(cursor):
    """Fetches the last sequential ID from the DB to ensure continuity."""
    query = "SELECT Document_Number FROM inventory_movements ORDER BY Document_Number DESC LIMIT 1;"
    cursor.execute(query)
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return "MD12000000"  # Default start if table is empty

def generate_next_id(last_id):
    """Increments the ID: MD12099999 -> MD12100000"""
    prefix = "MD"
    try:
        # Remove prefix, convert to int, add 1, format back
        numeric_part = int(last_id.replace(prefix, ""))
        new_numeric = numeric_part + 1
        return f"{prefix}{new_numeric:08d}"
    except ValueError:
        return f"{prefix}{int(time.time())}"

def generate_random_row(doc_id):
    """Generates a row preserving business logic (e.g. Movement Code matches Type)"""
    
    # Pick a movement type and its code together so they match
    move_info = random.choice(CONSTRAINTS["Movement_Data"])
    
    today = datetime.now()
    doc_date = today - timedelta(days=random.randint(0, 5))
    
    # Quantities
    qty = round(random.uniform(1.0, 1000.0), 2)
    stock_before = round(random.uniform(0, 10000), 2)
    
    # Simple logic: POs increase stock, others decrease (for simulation)
    if move_info["Type"] in ["GR_PO", "GR_PRODUCTION", "RETURN"]:
        stock_after = stock_before + qty
    else:
        stock_after = max(0, stock_before - qty)

    # Contextual Nulls (e.g., Vendor is only for POs)
    is_po = move_info["Type"] in ["GR_PO", "RETURN"]
    is_prod = move_info["Type"] in ["GI_PRODUCTION", "GR_PRODUCTION"]
    is_transfer = move_info["Type"] == "TRANSFER"
    
    return {
        "Document_Number": doc_id,
        "Document_Date": doc_date.date(),
        "Posting_Date": today.date(),
        "Movement_Type": move_info["Type"],
        "Movement_Type_Code": move_info["Code"],
        "Material_Number": f"MAT{random.randint(1000000, 1099999)}",
        "Material_Type": random.choice(CONSTRAINTS["Material_Type"]),
        "Plant": random.choice(CONSTRAINTS["Plant"]),
        "Storage_Location": f"SL{random.randint(100, 999)}",
        "From_Location": f"SL{random.randint(100, 999)}" if is_transfer else None,
        "To_Location": f"SL{random.randint(100, 999)}" if is_transfer else None,
        "Quantity": qty,
        "Unit": "KG",
        "Batch_Number": f"BTH{random.randint(1000000, 9999999)}",
        "Vendor_Number": f"VEND{random.randint(1000, 9999)}" if is_po else None,
        "Purchase_Order": f"PO{random.randint(45000000, 45999999)}" if is_po else None,
        "Production_Order": f"MO{random.randint(7000000, 7999999)}" if is_prod else None,
        "Reservation_Number": f"RS{random.randint(1000000, 9999999)}" if is_prod else None,
        "Cost_Center": f"CC{random.randint(1000, 9999)}",
        "Amount_USD": round(random.uniform(10, 50000), 2),
        "Currency": "USD",
        "User_ID": f"USR{random.randint(3000, 3200)}",
        "Reason_Code": random.choice(CONSTRAINTS["Reason_Code"]),
        "Reference_Document": f"REF{random.randint(1000000, 9999999)}" if random.random() > 0.5 else None,
        "Stock_Before": stock_before,
        "Stock_After": stock_after,
        "Valuation_Type": random.choice(CONSTRAINTS["Valuation_Type"])
    }

def main():
    print("Starting Inventory Movement Feeder...")
    conn = get_db_connection()
    if not conn: return

    try:
        cursor = conn.cursor()
        while True:
            # 1. Dynamic ID Fetch
            last_id = get_last_document_number(cursor)
            new_id = generate_next_id(last_id)
            
            # 2. Generate Data
            data = generate_random_row(new_id)
            
            # 3. Insert Data
            cols = list(data.keys())
            vals = list(data.values())
            placeholders = ", ".join(["%s"] * len(vals))
            stmt = f"INSERT INTO inventory_movements ({', '.join(cols)}) VALUES ({placeholders})"
            
            cursor.execute(stmt, vals)
            conn.commit()
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Inserted: {new_id} | Type: {data['Movement_Type']}")
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