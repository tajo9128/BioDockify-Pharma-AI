
import requests
import sys

BASE_URL = "http://localhost:8000"

def check_health():
    print(f"[*] Checking Health at {BASE_URL}/health ...")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print("   ✅ API is Online")
            
            comps = data.get("components", {})
            
            # Neo4j
            neo = comps.get("neo4j", {})
            if neo.get("status") == "unknown": 
                print("   ⚠️ Neo4j status unknown (Driver installed but unchecked)")
            elif neo.get("status") == "disabled":
                print("   ❌ Neo4j driver missing")
            else:
                print(f"   ✅ Neo4j: {neo}")
                
            # Ollama
            ai = comps.get("ai_core", {})
            print(f"   ℹ️ AI Core: {ai.get('status')} ({ai.get('provider', 'unknown')})")
            
            return True
        else:
            print(f"   ❌ API returned {resp.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

def check_settings():
    print(f"[*] Checking Settings at {BASE_URL}/api/settings ...")
    try:
        resp = requests.get(f"{BASE_URL}/api/settings", timeout=2)
        if resp.status_code == 200:
            cfg = resp.json()
            ai_prov = cfg.get("ai_provider", {})
            print("   ✅ Settings loaded")
            
            # Verify Keys existence (obfuscated)
            gl = ai_prov.get("google_key")
            custom = ai_prov.get("custom_key")
            
            if custom: 
                print("   ✅ Custom/Groq Key configured")
            else:
                print("   ⚠️ Custom/Groq Key MISSING in active config")
                
            return True
    except:
        print("   ❌ Settings unreachable")
        return False

if __name__ == "__main__":
    if check_health() and check_settings():
        print("\n✅ AGENT ZERO READINESS: PASS")
        sys.exit(0)
    else:
        print("\n❌ AGENT ZERO READINESS: FAIL")
        sys.exit(1)
