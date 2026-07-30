"""System Health API - Wires connection_doctor + system_doctor + security guardian."""
from helpers.api import ApiHandler, Request
import asyncio, os
import sys
import platform
import logging

logger = logging.getLogger("system_health")


async def _async_urlopen(req, timeout=5):
    """Non-blocking urlopen with proper resource cleanup."""
    import urllib.request
    def _fetch():
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    return await asyncio.to_thread(_fetch)


class SystemHealth(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = (input.get("action", "status") or "status").strip()
        if action == "diagnose":
            return await self._full_diagnose()
        return self._quick_status()

    def _quick_status(self) -> dict:
        result = {
            "status": "healthy",
            "checks": [],
            "timestamp": None,
        }
        try:
            from datetime import datetime
            result["timestamp"] = datetime.now().isoformat()
        except Exception:
            pass

        # Internet connectivity
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            result["checks"].append({"name": "Internet", "status": "ok", "detail": "Connected"})
        except Exception:
            result["status"] = "degraded"
            result["checks"].append({"name": "Internet", "status": "fail", "detail": "No connectivity"})

        # ChromeDB / Knowledge Base
        try:
            from modules.rag.vector_store import get_vector_store
            vs = get_vector_store()
            result["checks"].append({"name": "ChromaDB", "status": "ok", "detail": "Vector store available"})
        except Exception:
            result["checks"].append({"name": "ChromaDB", "status": "warn", "detail": "Unavailable"})

        # RDKit — try multiple import paths
        rdkit_ok = False
        try:
            from rdkit import Chem
            rdkit_ok = Chem.MolFromSmiles("CCO") is not None
        except Exception:
            try:
                import sys, site
                sys.path.insert(0, site.getsitepackages()[0])
                from rdkit import Chem
                rdkit_ok = Chem.MolFromSmiles("CCO") is not None
            except Exception:
                pass
        result["checks"].append({"name": "RDKit", "status": "ok" if rdkit_ok else "warn", "detail": "Docking available (RDKit)" if rdkit_ok else "Docking disabled"})

        # Docking dependencies
        import subprocess
        def _check_binary(bin_name):
            r = subprocess.run([bin_name, "--help"], capture_output=True, text=True, timeout=5)
            if r.returncode <= 1:
                return True
            r = subprocess.run([bin_name, "--version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return True
            r = subprocess.run([bin_name], capture_output=True, text=True, timeout=5)
            return r.returncode <= 1
        for bin_name, label, critical in [
            ("vina", "AutoDock Vina", True),
        ]:
            try:
                ok = await asyncio.to_thread(_check_binary, bin_name)
                detail = "Available" if ok else "Not found"
                status = "ok" if ok else ("fail" if critical else "warn")
            except FileNotFoundError:
                detail = "Missing — docking unavailable" if critical else "Not installed"
                status = "fail" if critical else "warn"
            except Exception:
                detail = "Missing — docking unavailable" if critical else "Not available"
                status = "fail" if critical else "warn"
            result["checks"].append({"name": label, "status": status, "detail": detail})

        # MM-GBSA scoring
        try:
            from api.docking_mmgbsa import mmgbsa_score
            result["checks"].append({"name": "MM-GBSA Scoring", "status": "ok", "detail": "Available (CPU-only)"})
        except ImportError:
            result["checks"].append({"name": "MM-GBSA Scoring", "status": "warn", "detail": "Module not loaded"})

        # Backend APIs - check via file existence
        api_checks = [
            ("Statistics", "modules/statistics/orchestrator.py"),
            ("Thesis", "modules/thesis/engine.py"),
            ("Research Mgmt", "modules/research_persistence.py"),
            ("Backup", "modules/backup/manager.py"),
            ("Faculty Tools", "api/faculty_tools.py"),
            ("Journal Finder", "modules/journal_intel/__init__.py"),
            ("Bio NER", "api/bio_ner.py"),
            ("Regulatory", "api/regulatory.py"),
            ("Docking", "api/docking_run.py"),
            ("MM-GBSA", "api/docking_mmgbsa.py"),
        ]
        for name, file_path in api_checks:
            full_docker = os.path.join("/a0", file_path)
            full_local = os.path.join(os.path.dirname(__file__), "..", file_path)
            exists = os.path.exists(full_docker) or os.path.exists(os.path.normpath(full_local))
            result["checks"].append({"name": name, "status": "ok" if exists else "warn",
                "detail": "Available" if exists else "Missing"})

        # TTS fallback status
        tts = {"status": "ok", "engine": "browser"}
        try:
            from kokoro_onnx import Kokoro
            tts = {"status": "ok", "engine": "kokoro"}
        except Exception:
            try:
                import edge_tts
                tts = {"status": "ok", "engine": "edge-tts"}
            except Exception:
                pass
        result["checks"].append({"name": "TTS", "status": tts["status"], "detail": f"Using: {tts['engine']}"})

        # Drug Properties fallback
        drug_ok = False
        try:
            from rdkit import Chem
            Chem.MolFromSmiles("C")
            drug_ok = True
        except Exception:
            try:
                import sys, site
                sys.path.insert(0, site.getsitepackages()[0])
                from rdkit import Chem
                Chem.MolFromSmiles("C")
                drug_ok = True
            except Exception:
                pass
        result["checks"].append({"name": "Drug Properties", "status": "ok" if drug_ok else "warn", "detail": "ok (RDKit)" if drug_ok else "fallback (approximate)"})

        # Literature search — check PubMed API
        lit_status = "ok"
        lit_detail = "PubMed + Semantic Scholar + 10 databases"
        try:
            import urllib.request
            req = urllib.request.Request("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi", headers={"User-Agent": "BioDockify/6.4"})
            await _async_urlopen(req, timeout=5)
        except Exception:
            lit_status = "warn"
            lit_detail = "PubMed API unreachable — search may be limited"
        result["checks"].append({"name": "Literature Search", "status": lit_status, "detail": lit_detail})

        # Disk usage
        try:
            import shutil
            usage = shutil.disk_usage("/")
            free_gb = round(usage.free / (1024**3), 1)
            total_gb = round(usage.total / (1024**3), 1)
            pct = round((1 - usage.free / usage.total) * 100)
            detail = f"{free_gb}GB free / {total_gb}GB total"
            disk_status = "warn" if pct > 85 else "ok"
            result["checks"].append({"name": "Disk", "status": disk_status, "detail": detail, "percent": pct})
        except Exception:
            result["checks"].append({"name": "Disk", "status": "warn", "detail": "Cannot check"})

        # Memory
        try:
            import psutil
            mem = psutil.virtual_memory()
            used_gb = round(mem.used / (1024**3), 1)
            total_gb = round(mem.total / (1024**3), 1)
            result["checks"].append({"name": "Memory", "status": "ok", "detail": f"{used_gb}GB / {total_gb}GB"})
        except Exception:
            pass

        # Overall
        fails = sum(1 for c in result["checks"] if c["status"] == "fail")
        warns = sum(1 for c in result["checks"] if c["status"] == "warn")
        if fails > 0:
            result["status"] = "degraded"
        elif warns > 2:
            result["status"] = "degraded"

        return result

    async def _full_diagnose(self) -> dict:
        result = self._quick_status()
        result["diagnosis"] = []
        try:
            from modules.system.doctor import SystemDoctor
            from modules.system.connection_doctor import ConnectionDoctor
            try:
                doc = SystemDoctor({})
                diag = doc.run_diagnosis()
                result["diagnosis"].append({"source": "system_doctor", "report": diag})
            except Exception:
                result["diagnosis"].append({"source": "system_doctor", "error": "Failed"})
            try:
                conn = ConnectionDoctor()
                report = await conn.run_full_check()
                result["diagnosis"].append({"source": "connection_doctor", "report": str(report)[:1000]})
            except Exception:
                result["diagnosis"].append({"source": "connection_doctor", "error": "Failed"})
        except Exception:
            pass

        # Security scan
        try:
            from modules.security.guardian import Guardian
            g = Guardian()
            secrets = g.scan_code("api/")
            result["security"] = {"secrets_found": len(secrets.get("secrets", []))}
        except Exception:
            result["security"] = {"error": "Scan unavailable"}

        return result
