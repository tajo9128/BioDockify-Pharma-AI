from helpers.api import ApiHandler, Request, Response
from helpers import errors, git


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

        health = {"status": "ok", "checks": []}
        try:
            import subprocess, os, shutil
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

            # GNINA
            gnina_detail = ""
            try:
                import platform
                r = subprocess.run(["gnina", "--help"], capture_output=True, timeout=5)
                gnina_ok = r.returncode <= 1
                gnina_detail = "Available" if gnina_ok else "Binary exists but returned error"
            except FileNotFoundError:
                gnina_ok = False
                gnina_detail = "Docker only — run with Docker for GNINA CNN scoring"
                if platform.system() == "Windows":
                    gnina_detail = "Docker only — GNINA requires Linux (use: docker compose up)"
            except Exception:
                gnina_ok = False
                gnina_detail = "Not available — install via Docker"
            health["checks"].append({"name": "GNINA CNN", "status": "ok" if gnina_ok else "fail", "detail": gnina_detail})

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
