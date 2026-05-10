import psutil
import time
import sys

def restart_server():
    print("Stopping server.py instances...")
    count = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline'] or []
            if 'server.py' in ' '.join(cmdline):
                print(f"Killing PID {proc.info['pid']}")
                proc.kill() # Aggressive kill to ensure it dies
                count += 1
        except Exception as e:
            print(f"Error killing process: {e}")

    if count > 0:
        print(f"Killed {count} instances. Launcher should restart one soon.")
        # Wait for restart
        sys.stdout.flush()
        for i in range(10):
            time.sleep(1)
            found = False
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    if 'server.py' in ' '.join(proc.info['cmdline'] or []):
                        found = True
                        break
                except:
                    pass
            if found:
                print("Server restarted successfully!")
                return
            print(".", end="")
        print("Server did not restart within 10s. Check launcher.")
    else:
        print("No server.py found running.")

if __name__ == "__main__":
    restart_server()
