import subprocess
import sys
import time
import os
import signal

# --- Configuration ---
SCRIPTS_FOLDER = "InputPipeline"

# Scripts EXACTLY as they exist on disk
SCRIPTS = [
    "material_master.py",
    "bill_of_materials.py",
    "melting_heat_records.py",
    "molding_records.py",
    "casting_records.py",
    "heat_treatments.py",
    "machining_operations.py",
    "quality_inspections.py",
    "inventory_movements.py",
    "production_data.py",
    "equipment_maintenance.py"
]

processes = []

def graceful_shutdown(signum, frame):
    """
    Handles Ctrl+C to terminate all child processes.
    """
    print("\n\n[MASTER] Stopping all data pipelines...")
    for p in processes:
        try:
            if p.poll() is None:
                p.terminate()
        except Exception as e:
            print(f"[MASTER] Error stopping process: {e}")

    print("[MASTER] All pipelines stopped. Exiting.")
    sys.exit(0)

# Listen for Ctrl+C
signal.signal(signal.SIGINT, graceful_shutdown)

def main():
    print(f"[MASTER] Initializing Master Runner for {len(SCRIPTS)} pipelines...")
    print(f"[MASTER] Target Folder: ./{SCRIPTS_FOLDER}")
    print("[MASTER] Press Ctrl+C to stop all scripts at any time.\n")
    print("-" * 60)

    for script_name in SCRIPTS:
        script_path = os.path.join(SCRIPTS_FOLDER, script_name)

        if os.path.exists(script_path):
            try:
                p = subprocess.Popen([sys.executable, script_path])
                processes.append(p)
                print(f"[MASTER] >> Started: {script_name}")

                # Delay to avoid DB locks / CPU spikes
                time.sleep(1)
            except Exception as e:
                print(f"[MASTER] !! FAILED to start {script_name}: {e}")
        else:
            print(f"[MASTER] !! ERROR: File not found: {script_path}")

    print("-" * 60)
    print(f"[MASTER] All {len(processes)} scripts are running.")
    print("[MASTER] Real-time logs from individual scripts will appear below:\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        graceful_shutdown(None, None)

if __name__ == "__main__":
    main()
