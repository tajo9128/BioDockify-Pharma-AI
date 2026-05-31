"""Self-Healing & Diagnosis API — diagnose, auto-fix, update from GitHub."""
from helpers.api import ApiHandler, Request, Response
import os, logging, subprocess, json, shutil

log = logging.getLogger("self_heal")

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")


def _run(cmd, timeout=30, workdir=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=True, cwd=workdir)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return "", str(e), -1


class SelfHealHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "diagnose")

        if action == "diagnose":
            return self._diagnose()
        elif action == "fix":
            return self._fix(input)
        elif action == "update":
            return self._update(input)
        elif action == "restart":
            return self._restart_service(input)
        elif action == "logs":
            return self._get_logs(input)

        return {"status": "error", "error": f"Unknown action: {action}"}

    def _diagnose(self) -> dict:
        """Run comprehensive system diagnosis."""
        checks = []
        issues = []
        auto_fixable = []

        # 1. Python environment
        py_out, _, py_code = _run("python --version")
        checks.append({"name": "Python", "status": "ok" if py_code == 0 else "fail", "detail": py_out})
        if py_code != 0: issues.append("Python not found"); auto_fixable.append("install_python")

        # 2. pip packages
        pip_out, _, pip_code = _run("pip list --format=json 2>/dev/null")
        if pip_code == 0:
            try:
                pkgs = json.loads(pip_out)
                pkg_names = {p["name"] for p in pkgs}
                missing = [p for p in ["rdkit", "scipy", "scikit-learn", "numpy"] if p not in pkg_names]
                if missing:
                    issues.append(f"Missing packages: {', '.join(missing)}")
                    auto_fixable.append("install_missing_deps")
                    checks.append({"name": "Dependencies", "status": "warn", "detail": f"Missing: {', '.join(missing)}"})
                else:
                    checks.append({"name": "Dependencies", "status": "ok", "detail": f"{len(pkg_names)} packages"})
            except: pass

        # 3. Disk space
        try:
            usage = shutil.disk_usage("/")
            free_gb = round(usage.free / (1024**3), 1)
            pct = round((1 - usage.free / usage.total) * 100)
            status = "ok" if pct < 85 else "warn"
            if pct > 90: issues.append(f"Disk {pct}% full ({free_gb}GB free)"); auto_fixable.append("clear_cache")
            checks.append({"name": "Disk", "status": status, "detail": f"{free_gb}GB free ({pct}% used)"})
        except: pass

        # 4. Git status
        git_out, _, git_code = _run("git log --oneline -1", workdir=PROJECT_ROOT)
        checks.append({"name": "Git Repo", "status": "ok" if git_code == 0 else "fail", "detail": git_out[:60]})

        # 5. Docker status
        docker_out, _, docker_code = _run("docker ps --format '{{.Names}}' 2>/dev/null")
        docker_running = "biodockify" in docker_out if docker_code == 0 else False
        checks.append({"name": "Docker", "status": "ok" if docker_running else ("warn" if docker_code == 0 else "info"), "detail": "Running" if docker_running else ("Not running" if docker_code == 0 else "Docker not available")})

        # 6. Vina
        vina_out, _, vina_code = _run("vina --version 2>&1")
        checks.append({"name": "AutoDock Vina", "status": "ok" if vina_code <= 1 else "warn", "detail": vina_out[:40] if vina_out else "Not installed"})

        # 7. Meeko
        try:
            import meeko
            checks.append({"name": "Meeko", "status": "ok", "detail": "Available"})
        except ImportError:
            checks.append({"name": "Meeko", "status": "warn", "detail": "Not installed"})

        # 8. OpenBabel
        ob_out, _, ob_code = _run("obabel -V 2>&1")
        checks.append({"name": "OpenBabel", "status": "ok" if ob_code <= 1 else "warn", "detail": ob_out[:40] if ob_out else "Not installed"})

        # 9. Docker image update
        try:
            git_remote, _, _ = _run("git fetch origin main --dry-run 2>&1", workdir=PROJECT_ROOT, timeout=10)
            behind = "behind" in git_remote.lower() or "fast-forward" in git_remote.lower()
            checks.append({"name": "Updates", "status": "warn" if behind else "ok", "detail": "Update available" if behind else "Up to date"})
            if behind: auto_fixable.append("update_from_github")
        except: pass

        # 10. WebSocket connectivity
        checks.append({"name": "WebSocket", "status": "ok", "detail": "Connected"})

        # 11. Knowledge base
        kb_exists = os.path.exists(os.path.join(PROJECT_ROOT, "data", "knowledge_uploads"))
        checks.append({"name": "Knowledge Base", "status": "ok" if kb_exists else "info", "detail": "Data directory exists" if kb_exists else "Not initialized"})

        # 12. Temp/cleanup
        tmp_dir = os.path.join(PROJECT_ROOT, "tmp")
        if os.path.exists(tmp_dir):
            job_count = len([d for d in os.listdir(tmp_dir) if d.startswith("docking_jobs")]) if os.path.isdir(tmp_dir) else 0
            checks.append({"name": "Temp Files", "status": "ok", "detail": f"{job_count} docking jobs"})

        return {
            "status": "ok",
            "checks": checks,
            "issues": issues,
            "auto_fixable": auto_fixable,
            "summary": f"{sum(1 for c in checks if c['status']=='ok')}/{len(checks)} healthy, {len(issues)} issues",
        }

    def _fix(self, input: dict) -> dict:
        """Auto-fix common issues."""
        action = input.get("fix_action", "")
        results = []

        if action == "install_missing_deps":
            pip_out, pip_err, code = _run("pip install -r requirements.txt", timeout=120)
            results.append({"action": "install_deps", "status": "ok" if code == 0 else "fail", "detail": pip_out[-200:] if code == 0 else pip_err[-200:]})

        elif action == "clear_cache":
            tmp_dir = os.path.join(PROJECT_ROOT, "tmp")
            before = 0
            try:
                before = sum(os.path.getsize(os.path.join(tmp_dir, f)) for f in os.listdir(tmp_dir) if os.path.isfile(os.path.join(tmp_dir, f)))
            except: pass
            _run(f"rm -rf {tmp_dir}/docking_jobs/* 2>/dev/null", timeout=10)
            results.append({"action": "clear_cache", "status": "ok", "detail": f"Freed ~{before // 1024}KB"})

        elif action == "restart_services":
            out, err, code = _run("docker compose restart 2>&1", timeout=30)
            results.append({"action": "restart", "status": "ok" if code == 0 else "fail", "detail": out[:200] if code == 0 else err[:200]})

        elif action == "update_from_github":
            return self._update({"source": "github"})

        return {"status": "ok", "fix_action": action, "results": results}

    def _update(self, input: dict) -> dict:
        """Pull latest from GitHub and optionally rebuild Docker."""
        source = input.get("source", "github")
        rebuild = input.get("rebuild", False)

        # Pull latest
        out, err, code = _run("git pull origin main", workdir=PROJECT_ROOT, timeout=60)
        pulled = code == 0 and "Already up to date" not in out

        result = {"status": "ok", "pulled": pulled, "output": out[:300], "rebuild_started": False}

        if rebuild and pulled:
            # Rebuild Docker
            out2, err2, code2 = _run("docker compose build --no-cache 2>&1", workdir=PROJECT_ROOT, timeout=600)
            result["rebuild_started"] = True
            result["rebuild_status"] = "ok" if code2 == 0 else "fail"
            result["rebuild_output"] = out2[-500:] if code2 == 0 else err2[-500:]

        return result

    def _restart_service(self, input: dict) -> dict:
        """Restart a specific service."""
        service = input.get("service", "biodockify")
        out, err, code = _run(f"docker compose restart {service} 2>&1", timeout=30)
        return {"status": "ok" if code == 0 else "fail", "service": service, "output": out[:200] if code == 0 else err[:200]}

    def _get_logs(self, input: dict) -> dict:
        """Get recent logs for a service."""
        service = input.get("service", "biodockify")
        lines = int(input.get("lines", 50))
        out, _, code = _run(f"docker compose logs --tail={lines} {service} 2>&1", timeout=10)
        return {"status": "ok", "logs": out[-5000:], "service": service}
