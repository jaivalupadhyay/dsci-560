import sys
import time
import subprocess
import schedule

def run_script(script_name):
    try:
        print(f"\n[INFO] Running {script_name}...")
        result = subprocess.run(["python", script_name], capture_output=True, text=True, check=False)

        if result.returncode == 0:
            print(f"[SUCCESS] {script_name} completed successfully.")
            print(result.stdout)  # Print script output
        else:
            print(f"[ERROR] {script_name} encountered an error.")
            print(result.stderr)  # Print error messages

    except Exception as e:
        print(f"[ERROR] Unexpected error while running {script_name}: {e}")

def automate_process():
    run_script("scraper.py")  # Run scraper
    run_script("clustering.py")  # Run clustering

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("[USAGE] python automate.py <interval_in_minutes>")
        sys.exit(1)
    
    try:
        interval = int(sys.argv[1])
        print(f"[INFO] Scheduling automation every {interval} minutes.")

        schedule.every(interval).minutes.do(automate_process)

        while True:
            schedule.run_pending()
            print(f"[INFO] Waiting... Next execution in {interval} minutes.", end="\r")  # Status update
            time.sleep(1)

    except ValueError:
        print("[ERROR] Invalid interval. Please provide an integer.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Script terminated by user.")
        sys.exit(0)
