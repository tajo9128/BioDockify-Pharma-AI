"""Test Research module (deep_research + literature) and Toolkit (docking + mol_optimizer)"""
import json, urllib.request, time, http.cookiejar

BASE = "http://localhost"
ORIGIN = "http://localhost"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

req = urllib.request.Request(f"{BASE}/api/csrf_token", headers={"Origin": ORIGIN})
resp = opener.open(req)
csrf_data = json.loads(resp.read())
csrf = csrf_data["token"]
print(f"CSRF OK")

headers = {"Content-Type": "application/json", "Origin": ORIGIN, "X-CSRF-Token": csrf}

def call(endpoint, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(f"{BASE}/api/{endpoint}", data=body, headers=headers)
    resp = opener.open(req)
    return json.loads(resp.read())

# ═══════════════════════════════════════════
print("\n" + "="*50)
print("MODULE 1: RESEARCH (Deep Research + Literature)")
print("="*50)

# 1a. Deep Research — collect
print("\n--- 1a. Deep Research: collect ---")
r = call("deep_research", {
    "action": "collect",
    "topic": "curcumin anticancer",
    "databases": ["pubmed", "europe_pmc"],
    "max_sources": 10,
    "max_store": 5
})
print(f"Status: {r.get('status')}")
print(f"Session: {r.get('session_id', 'N/A')}")
print(f"Sources found: {r.get('total_found', r.get('total', 0))}")
print(f"Full text retrieved: {r.get('full_text_count', 0)}")
print(f"KB stored: {r.get('kb_stored', 0)}")

session_id = r.get("session_id", "")

# 1b. Deep Research — scan
if session_id:
    print("\n--- 1b. Deep Research: scan ---")
    r = call("deep_research", {
        "action": "scan",
        "session_id": session_id,
        "keywords": ["curcumin", "cancer", "apoptosis"]
    })
    print(f"Scanned: {r.get('scanned', 0)}")
    top = r.get("top_sources", [])
    if top:
        print(f"Top result: {top[0].get('title','')[:70]}")

# 1c. Deep Research — screen
if session_id:
    print("\n--- 1c. Deep Research: screen ---")
    r = call("deep_research", {"action": "screen", "session_id": session_id})
    print(f"Screen workspace: {r.get('total', 0)} papers")
    print(f"Counts: {r.get('counts', {})}")

# 1d. Deep Research — literature_map (OpenAlex)
print("\n--- 1d. Deep Research: literature_map ---")
r = call("deep_research", {
    "action": "literature_map",
    "seed_query": "curcumin anticancer activity",
    "direction": "cited_by",
    "limit": 5
})
print(f"Status: {r.get('status')}")
if r.get("seed"):
    seed = r["seed"]
    print(f"Seed: {seed.get('title','')[:60]} ({seed.get('year','')}) cited by {seed.get('cited_by_count',0)}")
    print(f"Similar: {r.get('counts',{}).get('similar',0)}, Cited by: {r.get('counts',{}).get('cited_by',0)}, References: {r.get('counts',{}).get('references',0)}")
else:
    print(f"Error: {r.get('error','unknown')[:80]}")

# 1e. Literature search
print("\n--- 1e. Literature search ---")
r = call("literature_search", {
    "query": "aspirin mechanism of action",
    "database": "pubmed",
    "max_results": 3
})
print(f"Papers found: {r.get('total', 0)}")
papers = r.get("papers", [])
if papers:
    print(f"Top: {papers[0].get('title','')[:70]}")

# ═══════════════════════════════════════════
print("\n" + "="*50)
print("MODULE 2: TOOLKIT (Mol Optimizer + Docking)")
print("="*50)

# 2a. Mol Optimizer — generate mutants
print("\n--- 2a. Mol Optimizer: generate mutants ---")
r = call("mol_optimizer", {
    "action": "optimize",
    "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",  # aspirin
    "strategies": ["bioisostere", "add_hydroxyl", "add_fluorine"]
})
print(f"Status: {r.get('status', r.get('success', 'N/A'))}")
mutants = r.get("mutants", r.get("results", []))
print(f"Mutants generated: {len(mutants)}")
for m in mutants[:3]:
    if isinstance(m, dict):
        print(f"  - {m.get('smiles','?')} ({m.get('strategy','?')})")
    else:
        print(f"  - {m}")

# 2b. Docking — list actions
print("\n--- 2b. Docking: status ---")
r = call("docking_upload", {"action": "status"})
print(f"Status: {json.dumps(r, indent=2)[:200]}")

# 2c. Docking analysis — empty job (should handle gracefully)
print("\n--- 2c. Docking analysis: graceful empty job ---")
r = call("docking_analysis", {"action": "interactions", "job_id": "nonexistent_job"})
print(f"Response: {json.dumps(r, indent=2)[:200]}")

# 2d. Job ID validation (security fix check)
print("\n--- 2d. Docking: job_id validation (path traversal check) ---")
r = call("docking_analysis", {"action": "interactions", "job_id": "../../../etc/passwd"})
if "Invalid" in str(r.get("error", "")) or "invalid" in str(r.get("error", "")).lower():
    print(f"BLOCKED: {r.get('error')}")
else:
    print(f"WARNING - not blocked: {json.dumps(r)[:150]}")

print("\n" + "="*50)
print("ALL TESTS COMPLETE")
print("="*50)
