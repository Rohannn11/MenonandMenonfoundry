# run_all_feeders.py
"""
Runs ALL feeders in parallel threads so the foundry simulation feels alive.
Each feeder runs in its own thread with its own database connection.
"""

import threading
import time
import sys
from foundry_feeder import (
    feed_material_master,
    feed_bill_of_materials,
    feed_production_orders,
    feed_melting_heat_records,
    feed_molding_records,
    feed_casting_records,
    feed_heat_treatment,
    feed_machining_operations,
    feed_quality_inspections,
    feed_inventory_movements,
    feed_equipment_maintenance,
    connect,          # we'll borrow the connect function
    FEEDER_INTERVAL
)

# Map feeder name → function
FEEDER_FUNCTIONS = {
    "material":       feed_material_master,
    "bom":            feed_bill_of_materials,
    "production":     feed_production_orders,
    "melting":        feed_melting_heat_records,
    "molding":        feed_molding_records,
    "casting":        feed_casting_records,
    "heattreatment":  feed_heat_treatment,
    "machining":      feed_machining_operations,
    "quality":        feed_quality_inspections,
    "inventory":      feed_inventory_movements,
    "maintenance":    feed_equipment_maintenance,
}

def feeder_loop(name: str, func):
    print(f"[{name}] thread started")
    conn = connect()
    cursor = conn.cursor()
    try:
        while True:
            try:
                func(conn, cursor)
            except Exception as e:
                print(f"[{name}] ERROR: {e}")
                conn.rollback()
            time.sleep(FEEDER_INTERVAL)
    except KeyboardInterrupt:
        print(f"[{name}] stopping...")
    finally:
        cursor.close()
        conn.close()
        print(f"[{name}] thread stopped")

if __name__ == "__main__":
    print("Starting all foundry feeders in parallel threads...")
    print("Press Ctrl+C to stop all feeders gracefully\n")

    threads = []

    for name, func in FEEDER_FUNCTIONS.items():
        t = threading.Thread(
            target=feeder_loop,
            args=(name, func),
            name=f"Feeder-{name}",
            daemon=True
        )
        t.start()
        threads.append(t)

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down all feeders...")
        # Give threads a moment to finish current iteration
        time.sleep(2)
        print("All feeders stopped.")
        sys.exit(0)