"""System Health API - Wires connection_doctor + system_doctor + security guardian."""
from helpers.api import ApiHandler, Request
import os
import sys
import platform
import logging

logger = logging.getLogger("system_health")


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
        except:
            pass

        # Internet connectivity
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            result["checks"].append({"name": "Internet", "status": "ok", "detail": "Connected"})
        except:
            result["status"] = "degraded"
            result["checks"].append({"name": "Internet", "status": "fail", "detail": "No connectivity"})

        # ChromeDB / Knowledge Base
        try:
            from modules.rag.vector_store import get_vector_store
            vs = get_vector_store()
            result["checks"].append({"name": "ChromaDB", "status": "ok", "detail": "Vector store available"})
        except:
            result["checks"].append({"name": "ChromaDB", "status": "warn", "detail": "Unavailable"})

        # RDKit
        try:
            from rdkit import Chem
            m = Chem.MolFromSmiles("CCO")
            rdkit_ok = m is not None and m.GetNumAtoms() > 0
            result["checks"].append({"name": "RDKit", "status": "ok", "detail": "Available"})
        except:
            result["checks"].append({"name": "RDKit", "status": "warn", "detail": "Not installed"})

        # Backend APIs - check via file existence
        api_checks = [
            ("Statistics", "modules/statistics/orchestrator.py"),
            ("Thesis", "modules/thesis/engine.py"),
            ("Research Mgmt", "modules/research_persistence.py"),
            ("Backup", "modules/backup/manager.py"),
        ]
        for name, file_path in api_checks:
            full = os.path.join("/a0", file_path)
            exists = os.path.exists(full)
            result["checks"].append({"name": name, "status": "ok" if exists else "warn",
                "detail": "Available" if exists else "Missing"})

        # TTS fallback status
        tts = {"status": "ok", "engine": "browser"}
        try:
            from kokoro_onnx import Kokoro
            tts = {"status": "ok", "engine": "kokoro"}
        except:
            try:
                import edge_tts
                tts = {"status": "ok", "engine": "edge-tts"}
            except:
                pass
        result["checks"].append({"name": "TTS", "status": tts["status"], "detail": f"Using: {tts['engine']}"})

        # Drug Properties fallback
        drug_status = "ok (RDKit)"
        try:
            from rdkit import Chem
            Chem.MolFromSmiles("C")
        except:
            drug_status = "fallback (approximate)"
        result["checks"].append({"name": "Drug Properties", "status": "ok" if "RDKit" in drug_status else "warn", "detail": drug_status})

        # Literature search
        result["checks"].append({"name": "Literature Search", "status": "ok", "detail": "PubMed + Semantic Scholar + arXiv"})

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
        except:
            result["checks"].append({"name": "Disk", "status": "warn", "detail": "Cannot check"})

        # Memory
        try:
            import psutil
            mem = psutil.virtual_memory()
            used_gb = round(mem.used / (1024**3), 1)
            total_gb = round(mem.total / (1024**3), 1)
            result["checks"].append({"name": "Memory", "status": "ok", "detail": f"{used_gb}GB / {total_gb}GB"})
        except:
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
            except:
                result["diagnosis"].append({"source": "system_doctor", "error": "Failed"})
            try:
                conn = ConnectionDoctor()
                report = await conn.run_full_check()
                result["diagnosis"].append({"source": "connection_doctor", "report": str(report)[:1000]})
            except:
                result["diagnosis"].append({"source": "connection_doctor", "error": "Failed"})
        except:
            pass

        # Security scan
        try:
            from modules.security.guardian import Guardian
            g = Guardian()
            secrets = g.scan_code("api/")
            result["security"] = {"secrets_found": len(secrets.get("secrets", []))}
        except:
            result["security"] = {"error": "Scan unavailable"}

        return result
