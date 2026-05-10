import requests
import json

BASE_URL = "http://localhost:8234/api"

def test_settings_route():
    print("Testing Settings Route...")
    
    # Test 1: Invalid Service Type
    payload = {
        "service_type": "invalid_type"
    }
    try:
        resp = requests.post(f"{BASE_URL}/settings/test", json=payload)
        print(f"Test 1 (Invalid Type): {resp.status_code}")
        if resp.status_code == 200:
            print("Response:", resp.json())
    except Exception as e:
        print(f"Test 1 Failed: {e}")

    # Test 2: LLM Connection (Free/Public test if possible, or mock)
    # We'll use a public endpoint or just check if it tries
    payload = {
        "service_type": "llm",
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "key": "sk-fake-key"
    }
    try:
        resp = requests.post(f"{BASE_URL}/settings/test", json=payload)
        print(f"Test 2 (LLM Mock): {resp.status_code}")
        if resp.status_code == 200:
            print("Response:", resp.json())
    except Exception as e:
        print(f"Test 2 Failed: {e}")

    # Test 3: Brave (Missing Key)
    payload = {
        "service_type": "brave"
    }
    try:
        resp = requests.post(f"{BASE_URL}/settings/test", json=payload)
        print(f"Test 3 (Brave No Key): {resp.status_code}")
        if resp.status_code == 200:
            print("Response:", resp.json())
    except Exception as e:
        print(f"Test 3 Failed: {e}")

if __name__ == "__main__":
    test_settings_route()
