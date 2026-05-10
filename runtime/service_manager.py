import subprocess
import os
import time
import logging
import platform
import signal
import shutil
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("biodockify_services")

class ServiceManager:
    """Manages background services for BioDockify."""
    
    def __init__(self, config: dict):
        self.config = config
        self.processes: List[subprocess.Popen] = []
        self.is_windows = platform.system() == "Windows"
        self._docker_compose_cmd = None

    def _get_startup_flags(self):
        """Returns flags to run subprocess silently (Windows only)."""
        if self.is_windows:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = 0x08000000  # CREATE_NO_WINDOW
            return startupinfo, creationflags
        return None, 0

    def _get_docker_compose_cmd(self) -> Optional[List[str]]:
        """Detects the correct docker compose command (V1 vs V2)."""
        if self._docker_compose_cmd is not None:
            return self._docker_compose_cmd if self._docker_compose_cmd else None
        
        # Docker Compose V2: "docker compose" (plugin)
        if shutil.which("docker"):
            try:
                result = subprocess.run(
                    ["docker", "compose", "version"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0:
                    self._docker_compose_cmd = ["docker", "compose"]
                    logger.debug("Using Docker Compose V2 (docker compose)")
                    return self._docker_compose_cmd
            except Exception:
                pass
        
        # Docker Compose V1: "docker-compose" (standalone)
        # Verify it actually works by running version command
        if shutil.which("docker-compose"):
            try:
                result = subprocess.run(
                    ["docker-compose", "version"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0:
                    self._docker_compose_cmd = ["docker-compose"]
                    logger.debug("Using Docker Compose V1 (docker-compose)")
                    return self._docker_compose_cmd
            except Exception:
                pass
        
        # Neither available
        logger.warning("Docker Compose not found. Install Docker with Compose plugin.")
        self._docker_compose_cmd = []
        return None

    def start_surfsense(self):
        """Starts SurfSense via Docker Compose."""
        try:
            compose_file = Path("modules/surfsense/docker-compose.yml")
            if not compose_file.exists():
                logger.warning("SurfSense docker-compose.yml not found.")
                return

            compose_cmd = self._get_docker_compose_cmd()
            if not compose_cmd:
                logger.warning("Docker Compose not available. Skipping SurfSense startup.")
                return

            # Check if Docker daemon is running
            try:
                result = subprocess.run(
                    ["docker", "info"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode != 0:
                    logger.warning("Docker daemon not running. Skipping SurfSense startup.")
                    return
            except Exception as e:
                logger.warning(f"Docker not available: {e}. Skipping SurfSense startup.")
                return

            cmd = compose_cmd + ["-f", str(compose_file), "up", "-d"]
            logger.info(f"Starting Service: {' '.join(cmd)}")
            
            startupinfo, flags = self._get_startup_flags()
            
            proc = subprocess.Popen(
                cmd,
                shell=False,
                startupinfo=startupinfo,
                creationflags=flags,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = proc.communicate(timeout=60)
            
            if proc.returncode == 0:
                logger.info("SurfSense initiated (Docker).")
            else:
                logger.warning(f"SurfSense startup returned non-zero exit code: {proc.returncode}")
                if stderr:
                    logger.debug(f"Docker stderr: {stderr.decode('utf-8', errors='ignore')[:200]}")
            
        except subprocess.TimeoutExpired:
            logger.warning("SurfSense startup timed out. Continuing without SurfSense.")
        except FileNotFoundError as e:
            logger.warning(f"Docker executable not found: {e}. Skipping SurfSense startup.")
        except Exception as e:
            logger.warning(f"Failed to start SurfSense: {e}")

    def start_ollama(self):
        """Starts Ollama service check."""
        logger.info("BioDockify: Checking for local Ollama instance...")
        try:
            # For now, just logging as Ollama is usually external
            logger.info("Ollama: Please ensure Ollama is running at http://localhost:11434")
        except Exception as e:
            logger.error(f"Failed to initiate Ollama check: {e}")

    def stop_all(self):
        """Terminates all managed subprocesses."""
        logger.info(f"Stopping {len(self.processes)} background services...")
        for proc in self.processes:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception as e:
                logger.error(f"Error stopping process {proc.pid}: {e}")
        self.processes.clear()

    def check_health(self, service_name: str) -> str:
        """Check the health status of a service."""
        import socket
        
        ports = {
            "lm_studio": 1234,
            "surfsense": 3003,
            "ollama": 11434,
            "api": 8234
        }
        
        port = ports.get(service_name)
        if not port:
            return "unknown"
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                result = s.connect_ex(("127.0.0.1", port))
                return "running" if result == 0 else "stopped"
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            return "error"

    def attempt_repair(self, service_name: str) -> dict:
        """Attempt to repair a stopped service."""
        if service_name == "surfsense":
            self.start_surfsense()
            time.sleep(3)
            status = self.check_health("surfsense")
            return {
                "service": service_name,
                "action": "restart_attempted",
                "success": status == "running"
            }
        elif service_name == "lm_studio":
            # LM Studio is user-managed, we just report status
            return {
                "service": service_name,
                "action": "manual_start_required",
                "success": False,
                "message": "Please start LM Studio manually from https://lmstudio.ai"
            }
        else:
            return {
                "service": service_name,
                "action": "unknown_service",
                "success": False
            }

# Global Instance
service_manager = None

def get_service_manager(config: dict):
    global service_manager
    if service_manager is None:
        service_manager = ServiceManager(config)
    return service_manager
