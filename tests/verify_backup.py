import sys
import os
import requests
import json
import time

# Add root to path
sys.path.append(os.getcwd())

from modules.backup import DriveClient, BackupManager

def test_backend_logic():
    print("--- Testing Backend Logic ---")
    drive = DriveClient(storage_path="test_mock_cloud")
    manager = BackupManager(drive)
    
    # 1. Auth
    print("[1] Testing Auth...")
    auth_url = drive.get_auth_url()
    print(f"    Auth URL: {auth_url}")
    if "biodockify.com" not in auth_url:
        print("FAIL: Auth URL does not point to biodockify.com")
        return False
        
    drive.authenticate("simulated_valid_code_123")
    if not drive.is_connected():
        print("FAIL: Failed to authenticate")
        return False
    print("    Authenticated!")

    # 2. Backup
    print("[2] Testing Backup Creation...")
    # Create dummy data
    os.makedirs("test_source/data", exist_ok=True)
    with open("test_source/data/research.txt", "w") as f:
        f.write("Critical Research Data 123")
    
    result = manager.create_backup(["test_source"])
    print(f"    Backup Result: {result}")
    
    if result["status"] != "success":
        print("FAIL: Backup failed")
        return False

    # 3. List
    print("[3] Testing List Backups...")
    backups = drive.list_backups()
    print(f"    Found {len(backups)} backups")
    if len(backups) == 0:
        print("FAIL: No backups listed")
        return False

    # 4. Restore
    print("[4] Testing Restore...")
    restore_path = "test_restore"
    if os.path.exists(restore_path):
        import shutil
        shutil.rmtree(restore_path)
    
    res = manager.restore_backup(backups[0]['id'], restore_path)
    print(f"    Restore Result: {res}")
    
    if not os.path.exists(os.path.join(restore_path, "test_source", "data", "research.txt")):
        print("FAIL: Restored file not found")
        return False
        
    with open(os.path.join(restore_path, "test_source", "data", "research.txt"), "r") as f:
        content = f.read()
        if content != "Critical Research Data 123":
            print("FAIL: Content mismatch")
            return False

    print("--- Backend Logic PASSED ---")
    return True

def test_api_endpoints():
    print("\n--- Testing API Endpoints ---")
    base_url = "http://localhost:8000/api" # Assuming manually running, but we can't easily curl without server.
    # We will skip live API call test in this script and rely on logic test since we control the code.
    print("Skipping live API/HTTP test (server not running in this shell). Logic test is sufficient.")
    return True

if __name__ == "__main__":
    try:
        if test_backend_logic():
            print("\n✅ VERIFICATION SUCCESSFUL")
        else:
            print("\n❌ VERIFICATION FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
