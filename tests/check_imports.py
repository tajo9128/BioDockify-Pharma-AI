import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

print("Checking imports...")
try:
    import modules.system.auth_manager
    print("OK: modules.system.auth_manager")
except Exception as e:
    print(f"FAIL: modules.system.auth_manager - {e}")

try:
    import api.main
    print("OK: api.main")
except Exception as e:
    print(f"FAIL: api.main - {e}")

print("Import check complete.")
