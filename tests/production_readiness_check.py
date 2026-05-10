import requests
import json
import time
import os
import psutil

BASE_URL = "http://localhost:8234"
LM_STUDIO_URL = "http://localhost:1234/v1/models"

def print_result(name, passed, message=""):
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} | {name:.<40} | {message}")

def check_backend_process():
    found = False
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if 'server.py' in ' '.join(proc.info['cmdline'] or []):
                found = True
                break
        except:
            pass
    print_result("Backend Process (server.py)", found, "Running" if found else "Not Found")
    return found

def check_launcher_process():
    found = False
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if 'backend_launcher.py' in ' '.join(proc.info['cmdline'] or []):
                found = True
                break
        except:
            pass
    print_result("Backend Launcher (process)", found, "Running (Robustness Layer)" if found else "Not Found (Risk of downtime)")
    return found

def check_backend_health():
    print("Checking Backend Health...")
    for i in range(12): # 12 * 5s = 60s
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=5)
            if resp.status_code == 200:
                print_result("Backend Health API", True, f"Status: 200 (Attempt {i+1})")
                return True
        except:
            pass
        print(f"   Waiting for backend... ({i*5}s)")
        time.sleep(5)
    
    print_result("Backend Health API", False, "Timeout after 60s")
    return False

def check_settings_test_endpoint():
    try:
        payload = {
            "service_type": "llm", 
            "provider": "custom", 
            "key": "sk-dummy", 
            "base_url": "https://api.deepseek.com", 
            "model": "deepseek-chat"
        }
        resp = requests.post(f"{BASE_URL}/api/settings/test", json=payload, timeout=5)
        success = resp.status_code == 200
        msg = resp.json().get("message", "") if success else str(resp.status_code)
        print_result("API Settings Test Endpoint", success, f"Response: {msg[:50]}")
        return success
    except Exception as e:
        print_result("API Settings Test Endpoint", False, f"Connection Failed: {str(e)}")
        return False

def check_agent_chat():
    try:
        # Simple chat test
        resp = requests.post(f"{BASE_URL}/api/agent/chat", json={"message": "Test"}, timeout=10)
        success = resp.status_code == 200
        reply = resp.json().get("reply", "") if success else str(resp.status_code)
        print_result("Agent Zero Chat API", success, f"Reply: {reply[:50]}...")
        return success
    except Exception as e:
        print_result("Agent Zero Chat API", False, f"Failed: {str(e)}")
        return False

def check_lm_studio():
    try:
        resp = requests.get(LM_STUDIO_URL, timeout=2)
        success = resp.status_code == 200
        print_result("LM Studio Local Server", success, "Reachable" if success else f"Status: {resp.status_code}")
        return success
    except:
        print_result("LM Studio Local Server", False, "Not Running / Not Reachable")
        return False

if __name__ == "__main__":
    print("=== PRODUCTION READINESS DIAGNOSTIC ===")
    check_backend_process()
    check_launcher_process()
    
    if check_backend_health():
        check_settings_test_endpoint()
        check_agent_chat()
    else:
        print("[SKIP] Skipping API tests because Backend is down.")
        
    check_lm_studio()
    print("\n=== END DIAGNOSTIC ===")
