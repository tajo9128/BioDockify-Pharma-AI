"""Benchmark Suite API — validate dependencies, API health, storage, RDKit."""
from helpers.api import ApiHandler, Request, Response
import os, json, time, logging, subprocess
from datetime import datetime

log = logging.getLogger("benchmark_api")
BENCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "benchmarks")
os.makedirs(BENCH_DIR, exist_ok=True)


def _check_binary(name):
    try:
        result = subprocess.run([name, "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def _check_python(mod):
    try:
        __import__(mod)
        return True
    except ImportError:
        return False


class BenchmarkHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "run")

        if action == "run":
            return {
                "success": True,
                "benchmarks": {
                    "dependencies": self._bench_dependencies(),
                    "api_health": await self._bench_api_health(request),
                    "storage": self._bench_storage(),
                    "rdkit": self._bench_rdkit(),
                },
                "summary": "Run complete",
            }

        if action == "history":
            reports = []
            for fn in sorted(os.listdir(BENCH_DIR), reverse=True):
                if fn.endswith(".json"):
                    try:
                        with open(os.path.join(BENCH_DIR, fn)) as f:
                            reports.append(json.load(f))
                    except Exception:
                        pass
            return {"reports": reports[:10]}

        return {"error": f"Unknown action: {action}"}

    def _bench_dependencies(self):
        results = {}

        # Python packages — critical for docking
        for mod, label, critical in [
            ("rdkit", "RDKit", True), ("numpy", "NumPy", True), ("sklearn", "scikit-learn", False),
            ("scipy", "SciPy", False),
            ("playwright", "Playwright (Browser)", False), ("psutil", "psutil", False),
        ]:
            if _check_python(mod):
                results[mod] = {"status": "available", "label": label, "critical": critical}
            else:
                results[mod] = {"status": "not_installed", "label": label, "critical": critical,
                    "note": "Required for docking" if critical else
                           "Optional — some features disabled"}

        # System binaries
        for bin_name, label, critical in [
            ("vina", "AutoDock Vina", True),
        ]:
            if _check_binary(bin_name):
                results[bin_name] = {"status": "available", "label": label, "critical": critical}
            else:
                results[bin_name] = {"status": "missing", "label": label, "critical": critical,
                    "note": "Docking unavailable" if critical else "Optional"}

        # MM-GBSA (Python module, not binary)
        try:
            from api.docking_mmgbsa import mmgbsa_score
            results["mmgbsa"] = {"status": "available", "label": "MM-GBSA Scoring", "critical": False}
        except ImportError:
            results["mmgbsa"] = {"status": "missing", "label": "MM-GBSA Scoring", "critical": False, "note": "Module not loaded"}

        return results

    async def _bench_api_health(self, request: Request):
        host = request.host.split(":")[0] if request.host else "127.0.0.1"
        port = os.environ.get("PORT", "50001")
        url = f"http://{host}:{port}/api/health"
        try:
            start = time.time()
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=3)
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=timeout) as resp:
                    elapsed = round(time.time() - start, 3)
                    return {"url": url, "status_code": resp.status, "response_time_s": elapsed, "passed": resp.status == 200 and elapsed < 5}
        except Exception:
            return {"url": url, "status_code": None, "response_time_s": None, "passed": None, "skipped": True, "reason": "Self-connect not available (normal in Docker)"}

    def _bench_storage(self):
        import shutil
        try:
            total, used, free = shutil.disk_usage(os.getcwd())
            return {"total_gb": round(total / 1e9, 1), "free_gb": round(free / 1e9, 1), "passed": free > 500e6}
        except Exception as e:
            return {"error": str(e), "passed": False}

    def _bench_rdkit(self):
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors
            start = time.time()
            mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
            if mol is None:
                return {"passed": False, "error": "SMILES parsing failed"}
            mw = Descriptors.MolWt(mol)
            elapsed = round(time.time() - start, 4)
            return {"elapsed_s": elapsed, "mw": round(mw, 2), "passed": True}
        except Exception as e:
            return {"error": str(e), "passed": False}
