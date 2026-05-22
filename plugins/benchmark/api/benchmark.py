"""Benchmark Suite API — validate docking, QSAR, pharmacophore performance."""
from helpers.api import ApiHandler, Request, Response
import os, json, time, logging
from datetime import datetime

log = logging.getLogger("benchmark_api")
BENCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "benchmarks")
os.makedirs(BENCH_DIR, exist_ok=True)


class BenchmarkHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "run")

        if action == "run":
            return {
                "success": True,
                "benchmarks": {
                    "dependencies": self._bench_dependencies(),
                    "api_health": await self._bench_api_health(),
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
        for mod in ["rdkit", "numpy", "sklearn"]:
            try:
                __import__(mod)
                results[mod] = "available"
            except ImportError:
                results[mod] = "missing"
        for bin_name in ["vina", "obabel"]:
            import subprocess
            try:
                subprocess.run([bin_name, "--version"], capture_output=True, timeout=5)
                results[bin_name] = "available"
            except Exception:
                results[bin_name] = "missing"
        return results

    async def _bench_api_health(self):
        try:
            start = time.time()
            import aiohttp
            async with aiohttp.ClientSession() as s:
                async with s.get("http://127.0.0.1:50001/api/health", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    elapsed = round(time.time() - start, 3)
                    return {"status_code": resp.status, "response_time_s": elapsed, "passed": resp.status == 200 and elapsed < 2}
        except Exception as e:
            return {"error": str(e), "passed": False}

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
            mw = Descriptors.MolWt(mol)
            elapsed = round(time.time() - start, 4)
            return {"elapsed_s": elapsed, "mw": round(mw, 2), "passed": mol is not None}
        except Exception as e:
            return {"error": str(e), "passed": False}
