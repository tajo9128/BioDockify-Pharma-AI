"""Test MD Lite workflow: health → prepare → run → status → results"""
import json, urllib.request, time, http.cookiejar

BASE = "http://localhost"
ORIGIN = "http://localhost"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

req = urllib.request.Request(f"{BASE}/api/csrf_token", headers={"Origin": ORIGIN})
resp = opener.open(req)
csrf_data = json.loads(resp.read())
csrf = csrf_data["token"]
runtime_id = csrf_data.get("runtime_id", "")
print(f"CSRF: {csrf[:20]}... runtime: {runtime_id}")

headers = {"Content-Type": "application/json", "Origin": ORIGIN, "X-CSRF-Token": csrf}

def call(action, data=None):
    payload = {"action": action}
    if data:
        payload.update(data)
    body = json.dumps(payload).encode()
    req = urllib.request.Request(f"{BASE}/api/md_lite", data=body, headers=headers)
    resp = opener.open(req)
    return json.loads(resp.read())

# 1. Health
h = call("health")
print(f"\n=== HEALTH ===")
print(f"OpenMM: {h.get('openmm')}, Platform: {h.get('selected_platform')}, GPU: {h.get('gpu_available')}")

# 2. Prepare (small peptide)
MINI_PDB = """REMARK  TEST
ATOM      1  N   ALA A   1       1.000   1.000   1.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       1.500   2.000   1.500  1.00  0.00           C
ATOM      3  C   ALA A   1       2.000   3.000   1.000  1.00  0.00           C
ATOM      4  O   ALA A   1       2.500   3.500   1.500  1.00  0.00           O
ATOM      5  CB  ALA A   1       0.500   2.500   2.000  1.00  0.00           C
ATOM      6  N   GLY A   2       2.500   4.000   0.500  1.00  0.00           N
ATOM      7  CA  GLY A   2       3.000   5.000   0.000  1.00  0.00           C
ATOM      8  C   GLY A   2       3.500   6.000   0.500  1.00  0.00           C
ATOM      9  O   GLY A   2       4.000   6.500   0.000  1.00  0.00           O
ATOM     10  OXT GLY A   2       3.500   6.000   1.500  1.00  0.00           O
TER      11      GLY A   2
END
"""

print(f"\n=== PREPARE ===")
r = call("prepare", {"complex_pdb": MINI_PDB, "job_id": "test001"})
print(json.dumps(r, indent=2)[:500])

if r.get("status") != "ok":
    print("PREPARE FAILED")
    exit(1)

job_id = r.get("job_id", "test001")

# 3. Run MD (0.01 ns = very fast test)
print(f"\n=== RUN (0.01 ns, CPU, fast_mode) ===")
r = call("run", {"job_id": job_id, "total_ns": 0.01, "platform": "CPU", "fast_mode": True, "temperature": 300})
print(json.dumps(r, indent=2)[:500])

if r.get("status") != "ok":
    print("RUN FAILED")
    exit(1)

# 4. Poll status
print(f"\n=== STATUS POLL ===")
for i in range(40):
    time.sleep(3)
    s = call("status", {"job_id": job_id})
    phase = s.get("phase", "unknown")
    status = s.get("status", "unknown")
    progress = s.get("progress_pct", 0)
    error = s.get("error", "")
    print(f"  [{i}] status={status} phase={phase} progress={progress}% {error[:60] if error else ''}")
    if status in ("completed", "error"):
        print(f"\n=== FINAL STATUS ===")
        print(json.dumps(s, indent=2)[:800])
        break
else:
    print("TIMEOUT after 120s")

# 5. Results
print(f"\n=== RESULTS ===")
r = call("results", {"job_id": job_id})
print(json.dumps(r, indent=2)[:800])

print("\n=== MD LITE TEST COMPLETE ===")
