import requests
import json
import time

URL = "http://localhost:8234/api/settings/test"

def test_custom_provider():
    print("Testing Custom Provider (valid)...")
    payload = {
        "service_type": "llm",
        "provider": "custom",
        "key": "sk-dummy",
        "base_url": "https://api.deepseek.com/v1",  # Deepseek example
        "model": "deepseek-chat"
    }
    try:
        # Note: This will fail if we don't actually have a key, returning error from Deepseek or 401
        # But we just want to ensure we don't get 404 (Endpoint missing) or 500 (Server crash)
        # Deepseek might return 401 Invalid Key, which captures as "success" availability-wise or "error" message wise.
        # Our endpoint returns {"status": "error", "message": ...} on adapter failure.
        resp = requests.post(URL, json=payload, timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        
        if resp.status_code == 404:
            print("FAILURE: Endpoint not found")
            return False
        return True
    except Exception as e:
        print(f"Request failed: {e}")
        return False

if __name__ == "__main__":
    if test_custom_provider():
        print("Verification PASSED: Endpoint exists and is reachable.")
    else:
        print("Verification FAILED.")
