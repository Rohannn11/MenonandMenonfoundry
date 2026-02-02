import psycopg2
import pandas as pd
import random
import time
import re
from datetime import datetime, timedelta

# --- CONFIGURATION ---
DB_CONFIG = {
    "dbname": "foundry_db",
    "user": "postgres",
    "password": "Rohan$1105",  # <--- UPDATE THIS
    "host": "localhost",
    "port": "5432"
}

# Update path to your actual CSV file
CSV_FILE = r"C:\Users\rohan\Downloads\09_Inventory_Movements.csv"

# --- PART A: LEARN CONSTRAINTS ---
print("📊 Reading Inventory CSV to learn rules...")
try:
    df = pd.read_csv(CSV_FILE)
    
    # Extract valid options
    VALID_MATERIALS = df['Material_Number'].dropna().unique().tolist()
    VALID_MAT_TYPES = df['Material_Type'].dropna().unique().tolist()
    VALID_PLANTS = df['Plant'].dropna().unique().tolist()
    VALID_LOCATIONS = df['Storage_Location'].dropna().unique().tolist()
    VALID_USERS = df['User_ID'].dropna().unique().tolist()
    VALID_COST_CENTERS = df['Cost_Center'].dropna().unique().tolist()
    
    # Map Movement Types to their Codes
    # GI_PRODUCTION -> 261, GR_PO -> 101, etc.
    MOVEMENT_MAP = df[['Movement_Type', 'Movement_Type_Code']].drop_duplicates().set_index('Movement_Type').to_dict()['Movement_Type_Code']
    MOVEMENT_TYPES = list(MOVEMENT_MAP.keys())
    
    print("✅ Constraints Learned!")

except Exception as e:
    print(f"❌ Error reading CSV: {e}")
    exit()

# --- PART B: DYNAMIC ID FETCHER ---
def get_next_doc_number(cur):
    """Fetches MAX Document_Number (MD12...) and increments it."""
    # We strip 'MD' to handle the number math
    cur.execute("SELECT MAX(document_number) FROM inventory_movements")
    last_id = cur.fetchone()[0]

    if last_id:
        match = re.search(r'MD(\d+)', last_id)
        if match:
            number_part = int(match.group(1))
            next_number = number_part + 1
            return f"MD{str(next_number)}" # Returns MD12100000
    
    return "MD12100000" # Fallback if table empty

# --- PART C: GENERATOR ---
def generate_inventory_row(next_id):
    today = datetime.now()
    move_type = random.choice(MOVEMENT_TYPES)
    move_code = MOVEMENT_MAP[move_type]
    
    qty = round(random.uniform(10, 1000), 2)
    amount = round(random.uniform(100, 50000), 2)
    stock_pre = round(random.uniform(1000, 9000), 2)
    
    # Initialize all conditional fields as None
    prod_order, reserv_num = None, None
    vendor, po = None, None
    from_loc, to_loc = None, None
    
    # --- CONDITIONAL LOGIC ENFORCEMENT ---
    if move_type == 'GI_PRODUCTION':
        prod_order = f"MO{random.randint(7000000, 7999999)}"
        reserv_num = f"RS{random.randint(8000000, 9999999)}"
        stock_post = stock_pre - qty
        
    elif move_type == 'GR_PO':
        vendor = f"VEN{random.randint(10000, 99999)}"
        po = f"PO{random.randint(4000000, 4999999)}"
        stock_post = stock_pre + qty
        
    elif move_type == 'TRANSFER':
        from_loc = random.choice(VALID_LOCATIONS)
        to_loc = random.choice(VALID_LOCATIONS)
        while to_loc == from_loc: # Ensure we don't transfer to same location
            to_loc = random.choice(VALID_LOCATIONS)
        stock_post = stock_pre 
        
    else: # SCRAP, RETURN, ADJUSTMENT
        stock_post = stock_pre - qty

    return {
        "document_number": next_id,
        "document_date": today.strftime('%Y-%m-%d'),
        "posting_date": today.strftime('%Y-%m-%d'),
        "movement_type": move_type,
        "movement_type_code": move_code,
        "material_number": random.choice(VALID_MATERIALS),
        "material_type": random.choice(VALID_MAT_TYPES),
        "plant": random.choice(VALID_PLANTS),
        "storage_location": random.choice(VALID_LOCATIONS),
        "from_location": from_loc,
        "to_location": to_loc,
        "quantity": qty,
        "unit": "KG",
        "batch_number": f"BTH{random.randint(1000000, 9999999)}",
        "vendor_number": vendor,
        "purchase_order": po,
        "production_order": prod_order,
        "reservation_number": reserv_num,
        "cost_center": random.choice(VALID_COST_CENTERS),
        "amount_usd": amount,
        "currency": "USD",
        "user_id": random.choice(VALID_USERS),
        "reason_code": random.choice(["PRODUCTION", "QUALITY", "MAINTENANCE", None]),
        "reference_document": f"REF{random.randint(1000000, 9999999)}",
        "stock_before": stock_pre,
        "stock_after": round(stock_post, 2),
        "valuation_type": random.choice(["STANDARD", "MOVING_AVG", None])
    }

# --- PART D: SIMULATION LOOP ---
def run_simulation():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("\n🚀 Inventory Simulation Started... (Ctrl+C to Stop)\n")

        while True:
            # 1. Get Next ID
            next_id = get_next_doc_number(cur)
            
            # 2. Generate Data
            row = generate_inventory_row(next_id)
            
            # 3. Insert
            sql = """
            INSERT INTO inventory_movements (
                document_number, document_date, posting_date, movement_type, movement_type_code,
                material_number, material_type, plant, storage_location, from_location, to_location,
                quantity, unit, batch_number, vendor_number, purchase_order, production_order,
                reservation_number, cost_center, amount_usd, currency, user_id, reason_code,
                reference_document, stock_before, stock_after, valuation_type
            ) VALUES (
                %(document_number)s, %(document_date)s, %(posting_date)s, %(movement_type)s, %(movement_type_code)s,
                %(material_number)s, %(material_type)s, %(plant)s, %(storage_location)s, %(from_location)s, %(to_location)s,
                %(quantity)s, %(unit)s, %(batch_number)s, %(vendor_number)s, %(purchase_order)s, %(production_order)s,
                %(reservation_number)s, %(cost_center)s, %(amount_usd)s, %(currency)s, %(user_id)s, %(reason_code)s,
                %(reference_document)s, %(stock_before)s, %(stock_after)s, %(valuation_type)s
            );
            """
            
            cur.execute(sql, row)
            conn.commit()
            
            # 4. Log
            t = datetime.now().strftime("%H:%M:%S")
            print(f"[{t}] 📦 New Move: {row['document_number']} | Type: {row['movement_type']} | Qty: {row['quantity']}")
            
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n🛑 Simulation Stopped.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    run_simulation()