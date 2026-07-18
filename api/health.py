from helpers.api import ApiHandler, Request, Response
from helpers import errors, git
import os, logging

log = logging.getLogger("health")

_BACKUP_DONE_TODAY = False


def _get_agent_root():
    """Get agent root directory — works both in Docker and local dev."""
    return os.environ.get("AGENT_ROOT", "/a0") if os.path.exists("/a0") else os.path.dirname(os.path.abspath(__file__))


def _auto_backup_if_needed():
    """Run auto-backup once per container start."""
    global _BACKUP_DONE_TODAY
    if _BACKUP_DONE_TODAY:
        return
    _BACKUP_DONE_TODAY = True
    try:
        import shutil
        from datetime import datetime
        agent_root = _get_agent_root()
        backup_dir = os.path.join(agent_root, "usr", "backups")
        data_dir = os.path.join(agent_root, "usr")
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"auto_backup_{ts}")
        critical = ["data", "knowledge", "memory", "projects", "agents", "skills", "prompts"]
        files = ["settings.json", "identity.md"]
        backed = []
        for d in critical:
            src = os.path.join(data_dir, d)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(backup_path, d), dirs_exist_ok=True)
                backed.append(d)
        for f in files:
            src = os.path.join(data_dir, f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(backup_path, f))
                backed.append(f)
        # Clean old backups (keep 7)
        all_backups = sorted([d for d in os.listdir(backup_dir) if d.startswith("auto_backup_")])
        for old in all_backups[:-7]:
            shutil.rmtree(os.path.join(backup_dir, old), ignore_errors=True)
        log.info(f"[Auto-Backup] Created: {backup_path} ({len(backed)} items)")
    except Exception as e:
        log.warning(f"[Auto-Backup] Failed: {e}")


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

            # MM-GBSA Free Energy Scoring (CPU-only, no MD)
            mmgbsa_ok = True
            try:
                from api.docking_mmgbsa import mmgbsa_score
                mmgbsa_detail = "Available (simplified MM-GBSA)"
            except ImportError:
                mmgbsa_ok = False
                mmgbsa_detail = "Module not loaded"
            health["checks"].append({"name": "MM-GBSA Scoring", "status": "ok" if mmgbsa_ok else "warn", "detail": mmgbsa_detail})

            # Meeko (PDBQT conversion)
            meeko_ok = False
            try:
                import meeko
                meeko_ok = True
                meeko_detail = "Available"
            except ImportError:
                meeko_detail = "Not installed"
            health["checks"].append({"name": "Meeko", "status": "ok" if meeko_ok else "warn", "detail": meeko_detail})

            # Vector Store (Knowledge Base)
            vs_ok = False
            vs_detail = ""
            try:
                import chromadb
                vs_ok = True
                vs_detail = "ChromaDB available"
            except ImportError:
                try:
                    import faiss
                    vs_ok = True
                    vs_detail = "FAISS available"
                except ImportError:
                    vs_detail = "No vector store (pip install chromadb)"
            health["checks"].append({"name": "Vector Store", "status": "ok" if vs_ok else "warn", "detail": vs_detail})

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
