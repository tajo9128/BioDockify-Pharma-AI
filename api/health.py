from helpers.api import ApiHandler, Request, Response
from helpers import errors, git
import os


class HealthCheck(ApiHandler):

    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        gitinfo = None
        error = None
        try:
            gitinfo = git.get_git_info()
        except Exception as e:
            error = errors.error_text(e)

        # Auto-backup on first health check (once per day)
        _auto_backup_if_needed()

        health = {"status": "ok", "checks": []}
        try:
            import subprocess, shutil
            import socket

            # Internet
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                health["checks"].append({"name": "Internet", "status": "ok"})
            except:
                health["checks"].append({"name": "Internet", "status": "fail"})

            # Vina
            try:
                r = subprocess.run(["vina", "--help"], capture_output=True, timeout=5)
                health["checks"].append({"name": "AutoDock Vina", "status": "ok" if r.returncode <= 1 else "fail"})
            except:
                health["checks"].append({"name": "AutoDock Vina", "status": "fail", "detail": "Not installed"})

            # ODDT ML Scoring (RF-Score + NNScore) — CPU-only, cross-platform
            oddt_detail = ""
            try:
                import oddt
                oddt_detail = "Available (RF-Score + NNScore)"
                oddt_ok = True
            except ImportError:
                oddt_ok = False
                oddt_detail = "Not installed (pip install oddt)"
            health["checks"].append({"name": "ML Scoring (ODDT)", "status": "ok" if oddt_ok else "warn", "detail": oddt_detail})

            # RDKit
            try:
                from rdkit import Chem
                ok = Chem.MolFromSmiles("CCO") is not None
                health["checks"].append({"name": "RDKit", "status": "ok" if ok else "fail"})
            except:
                health["checks"].append({"name": "RDKit", "status": "fail"})

            # Disk
            usage = shutil.disk_usage("/")
            free_gb = round(usage.free / (1024**3), 1)
            health["checks"].append({"name": "Disk", "status": "ok", "detail": f"{free_gb}GB free"})

            # Overall
            fails = [c for c in health["checks"] if c["status"] == "fail"]
            health["status"] = "healthy" if not fails else "degraded"

        except Exception as e:
            health["status"] = "error"
            health["error"] = str(e)

        return {"status": "ok", "gitinfo": gitinfo, "health": health, "error": error}
