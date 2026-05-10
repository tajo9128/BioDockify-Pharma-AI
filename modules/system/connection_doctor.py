"""
Connection Doctor - First-Run Self-Healing System
Automatically detects and resolves connectivity issues.
Focused on LM Studio as primary local AI provider with auto-start capability.
"""

import os
import sys
import socket
import asyncio
import logging
import subprocess
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("connection_doctor")


class CheckStatus(Enum):
    """Status of a connectivity check."""
    PENDING = "pending"
    CHECKING = "checking"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class CheckResult:
    """Result of a single connectivity check."""
    name: str
    status: CheckStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    can_auto_repair: bool = False
    repair_action: Optional[str] = None


@dataclass
class DiagnosisReport:
    """Complete diagnosis report."""
    overall_status: str  # healthy | degraded | offline
    checks: List[CheckResult] = field(default_factory=list)
    suggested_repairs: List[str] = field(default_factory=list)
    can_proceed_with_degraded: bool = True


class ConnectionDoctor:
    """
    Progressive self-healing for first-run connectivity.
    Focused on LM Studio as primary local AI provider.
    
    Repair Strategy: Detect → Diagnose → Auto-Start → Guide
    """
    
    # LM Studio common install paths (Windows)
    LM_STUDIO_PATHS = [
        os.path.expandvars(r"%LOCALAPPDATA%\LM Studio\LM Studio.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\LM Studio\LM Studio.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\LM Studio\LM Studio.exe"),
        # Additional common paths
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\LM Studio\LM Studio.exe"),
        r"C:\Program Files\LM Studio\LM Studio.exe",
        r"C:\Program Files (x86)\LM Studio\LM Studio.exe",
    ]
    
    # Ports to scan for LM Studio
    LM_STUDIO_PORTS = [1234, 1235, 8080, 5000, 8000]
    
    # Internet connectivity endpoints (fast, reliable)
    CONNECTIVITY_ENDPOINTS = [
        ("google.com", 443),
        ("cloudflare.com", 443),
        ("github.com", 443),
    ]
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._http_client = None
    
    async def full_diagnosis(self, auto_repair: bool = True) -> DiagnosisReport:
        """
        Run all connectivity checks and return comprehensive report.
        
        Args:
            auto_repair: If True, attempt to auto-start LM Studio if not detected
            
        Returns:
            DiagnosisReport with all check results
        """
        report = DiagnosisReport(overall_status="healthy")
        
        # 1. Internet Connectivity
        logger.info("Checking internet connectivity...")
        internet_result = await self.check_internet()
        report.checks.append(internet_result)
        
        # 2. LM Studio (with auto-start if enabled)
        logger.info("Checking LM Studio...")
        lm_result = await self.check_lm_studio(auto_start=auto_repair)
        report.checks.append(lm_result)
        
        # 3. API Keys (if configured)
        logger.info("Validating API keys...")
        api_result = await self.validate_api_keys()
        report.checks.append(api_result)
        
        # 4. Backend Health
        logger.info("Checking backend health...")
        backend_result = await self.check_backend()
        report.checks.append(backend_result)
        
        # Determine overall status
        has_error = any(c.status == CheckStatus.ERROR for c in report.checks)
        has_warning = any(c.status == CheckStatus.WARNING for c in report.checks)
        
        if has_error:
            # Check if LM Studio or Internet failed (critical)
            lm_failed = lm_result.status == CheckStatus.ERROR
            internet_failed = internet_result.status == CheckStatus.ERROR
            
            if lm_failed and internet_failed:
                report.overall_status = "offline"
                # FIX: Allow user to proceed manually even in offline mode
                report.can_proceed_with_degraded = True
            else:
                report.overall_status = "degraded"
        elif has_warning:
            report.overall_status = "degraded"
        else:
            report.overall_status = "healthy"
        
        # Collect repair suggestions
        for check in report.checks:
            if check.repair_action and check.status != CheckStatus.SUCCESS:
                report.suggested_repairs.append(check.repair_action)
        
        return report
    
    async def check_internet(self, max_retries: int = 3) -> CheckResult:
        """
        Check internet connectivity with multiple endpoints and retries.
        Uses non-blocking asyncio connections.
        """
        for attempt in range(max_retries):
            for host, port in self.CONNECTIVITY_ENDPOINTS:
                try:
                    # Non-blocking connection test
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(host, port),
                        timeout=3.0
                    )
                    writer.close()
                    await writer.wait_closed()
                    
                    return CheckResult(
                        name="Internet Connectivity",
                        status=CheckStatus.SUCCESS,
                        message=f"Connected via {host}",
                        details={"endpoint": host, "attempt": attempt + 1}
                    )
                except Exception as e:
                    logger.debug(f"Connection to {host} failed: {e}")
                    continue
            
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        return CheckResult(
            name="Internet Connectivity",
            status=CheckStatus.ERROR,
            message="No internet connection detected",
            can_auto_repair=True,
            repair_action="Check your network connection and firewall settings"
        )
    
    async def check_lm_studio(self, auto_start: bool = True) -> CheckResult:
        """
        Multi-port scan for LM Studio with auto-start capability.
        
        Detection:
        - Ports: [1234, 1235, 8080, 5000, 8000]
        - Timeout: 10s per port (cold start scenario)
        - Verify model is loaded via /v1/models endpoint
        
        Auto-Start (if enabled and not detected):
        1. Find LM Studio executable
        2. Launch in background
        3. Wait up to 30s for initialization
        4. Retry detection
        """
        # First, try to detect running LM Studio
        result = await self._detect_lm_studio()
        
        if result.status == CheckStatus.SUCCESS:
            return result
        
        # Not detected - try auto-start if enabled
        if auto_start:
            logger.info("LM Studio not detected, attempting auto-start...")
            
            exe_path = self.find_lm_studio_executable()
            if exe_path:
                started = await self.auto_start_lm_studio(exe_path)
                
                if started:
                    # Wait for LM Studio to initialize (up to 30s)
                    logger.info("LM Studio launched, waiting for initialization...")
                    
                    for wait_time in [5, 10, 15]:
                        await asyncio.sleep(wait_time)
                        retry_result = await self._detect_lm_studio()
                        
                        if retry_result.status == CheckStatus.SUCCESS:
                            retry_result.details["auto_started"] = True
                            retry_result.message += " (Auto-started)"
                            return retry_result
                    
                    return CheckResult(
                        name="LM Studio",
                        status=CheckStatus.WARNING,
                        message="LM Studio started but no model loaded",
                        details={"auto_started": True, "exe_path": exe_path},
                        repair_action="Load a model and ensure 'Enable CORS' is ON"
                    )
                else:
                    return CheckResult(
                        name="LM Studio",
                        status=CheckStatus.ERROR,
                        message="Failed to start LM Studio",
                        details={"exe_path": exe_path},
                        repair_action="Start LM Studio, load model, and enable CORS"
                    )
            else:
                return CheckResult(
                    name="LM Studio",
                    status=CheckStatus.ERROR,
                    message="LM Studio not installed or not found",
                    can_auto_repair=False,
                    repair_action="Install LM Studio and enable CORS in settings"
                )
        
        return result
    
    async def _detect_lm_studio(self) -> CheckResult:
        """
        Internal method to detect running LM Studio instance.
        """
        async with aiohttp.ClientSession() as session:
            for port in self.LM_STUDIO_PORTS:
                url = f"http://localhost:{port}/v1/models"
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            data = await response.json()
                            models = data.get("data", [])
                            
                            if models:
                                model_id = models[0].get("id", "unknown")
                                return CheckResult(
                                    name="LM Studio",
                                    status=CheckStatus.SUCCESS,
                                    message=f"Connected on port {port}",
                                    details={
                                        "url": f"http://localhost:{port}/v1",
                                        "port": port,
                                        "model": model_id,
                                        "models_count": len(models)
                                    }
                                )
                            else:
                                # LM Studio running but no model loaded
                                return CheckResult(
                                    name="LM Studio",
                                    status=CheckStatus.WARNING,
                                    message=f"Running on port {port} but no model loaded",
                                    details={"url": f"http://localhost:{port}/v1", "port": port},
                                    repair_action="Please load a model in LM Studio"
                                )
                except Exception as e:
                    logger.debug(f"Port {port} check failed: {e}")
                    continue
        
        return CheckResult(
            name="LM Studio",
            status=CheckStatus.ERROR,
            message="Not detected (CORS might be disabled or app is closed)",
            can_auto_repair=True,
            repair_action="Start LM Studio, load model, and ENSURE 'Enable CORS' is ON"
        )
    
    async def _detect_lm_studio_sync(self) -> CheckResult:
        """Deprecated: Use async version."""
        return await self._detect_lm_studio()
    
    def find_lm_studio_executable(self) -> Optional[str]:
        """
        Locate LM Studio installation on Windows.
        
        Returns:
            Path to LM Studio.exe if found, None otherwise
        """
        for path in self.LM_STUDIO_PATHS:
            expanded_path = os.path.expandvars(path)
            if os.path.exists(expanded_path):
                logger.info(f"Found LM Studio at: {expanded_path}")
                return expanded_path
        
        # Try to find via registry or common locations
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
            )
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                    if "LM Studio" in display_name:
                        install_location, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                        exe_path = os.path.join(install_location, "LM Studio.exe")
                        if os.path.exists(exe_path):
                            return exe_path
                except (WindowsError, FileNotFoundError):
                    continue
        except Exception:
            pass
        
        logger.warning("LM Studio executable not found")
        return None
    
    async def auto_start_lm_studio(self, exe_path: str) -> bool:
        """
        Launch LM Studio in background.
        
        Args:
            exe_path: Path to LM Studio.exe
            
        Returns:
            True if successfully started
        """
        try:
            if sys.platform == "win32":
                # Windows-specific: Start detached process
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                DETACHED_PROCESS = 0x00000008
                
                subprocess.Popen(
                    [exe_path],
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True
                )
            else:
                # Unix-like: Use nohup equivalent
                subprocess.Popen(
                    [exe_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            
            logger.info(f"LM Studio started from: {exe_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start LM Studio: {e}")
            return False
    
    async def validate_api_keys(self) -> CheckResult:
        """
        Validate configured cloud API keys.
        
        Checks:
        - Google Gemini: Quick /models check
        - OpenRouter: Auth header validation
        - HuggingFace: Token verification
        """
        ai_config = self.config.get("ai_provider", {})
        
        keys_found = []
        keys_valid = []
        validation_errors = []
        
        # Check Google Gemini key
        google_key = ai_config.get("google_key")
        if google_key:
            keys_found.append("Google Gemini")
            is_valid, error = await self._validate_google_key(google_key)
            if is_valid:
                keys_valid.append("Google Gemini")
            else:
                validation_errors.append(f"Google: {error}")
        
        # Check OpenRouter key
        openrouter_key = ai_config.get("openrouter_key")
        if openrouter_key:
            keys_found.append("OpenRouter")
            is_valid, error = await self._validate_openrouter_key(openrouter_key)
            if is_valid:
                keys_valid.append("OpenRouter")
            else:
                validation_errors.append(f"OpenRouter: {error}")
        
        # Check HuggingFace key
        huggingface_key = ai_config.get("huggingface_key")
        if huggingface_key:
            keys_found.append("HuggingFace")
            is_valid, error = await self._validate_huggingface_key(huggingface_key)
            if is_valid:
                keys_valid.append("HuggingFace")
            else:
                validation_errors.append(f"HuggingFace: {error}")
        
        if not keys_found:
            return CheckResult(
                name="API Keys",
                status=CheckStatus.WARNING,
                message="No cloud API keys configured",
                details={"keys_found": [], "keys_valid": []},
                repair_action="Add API keys in Settings for cloud AI features"
            )
        
        if keys_valid:
            return CheckResult(
                name="API Keys",
                status=CheckStatus.SUCCESS,
                message=f"Valid: {', '.join(keys_valid)}",
                details={"keys_found": keys_found, "keys_valid": keys_valid}
            )
        else:
            return CheckResult(
                name="API Keys",
                status=CheckStatus.ERROR,
                message=f"All keys invalid: {'; '.join(validation_errors)}",
                details={
                    "keys_found": keys_found,
                    "keys_valid": [],
                    "errors": validation_errors
                },
                repair_action="Check your API keys in Settings"
            )
    
    async def _validate_google_key(self, key: str) -> tuple[bool, str]:
        """Validate Google Gemini API key."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = "https://generativelanguage.googleapis.com/v1/models"
                async with session.get(url, params={"key": key}, timeout=10) as response:
                    if response.status == 200:
                        return True, ""
                    elif response.status == 400:
                        return False, "Invalid key format"
                    elif response.status == 403:
                        return False, "Key expired or disabled"
                    else:
                        return False, f"HTTP {response.status}"
        except Exception as e:
            return False, str(e)
    
    async def _validate_openrouter_key(self, key: str) -> tuple[bool, str]:
        """Validate OpenRouter API key."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = "https://openrouter.ai/api/v1/models"
                headers = {"Authorization": f"Bearer {key}"}
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        return True, ""
                    elif response.status == 401:
                        return False, "Invalid or expired key"
                    else:
                        return False, f"HTTP {response.status}"
        except Exception as e:
            return False, str(e)
    
    async def _validate_huggingface_key(self, key: str) -> tuple[bool, str]:
        """Validate HuggingFace API key."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = "https://huggingface.co/api/whoami"
                headers = {"Authorization": f"Bearer {key}"}
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        return True, ""
                    elif response.status == 401:
                        return False, "Invalid token"
                    else:
                        return False, f"HTTP {response.status}"
        except Exception as e:
            return False, str(e)
    
    async def check_backend(self) -> CheckResult:
        """
        Verify FastAPI backend is responding using non-blocking aiohttp.
        """
        backend_url = self.config.get("backend_url", "http://localhost:8234")
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{backend_url}/api/health", timeout=5) as response:
                    if response.status == 200:
                        return CheckResult(
                            name="Backend API",
                            status=CheckStatus.SUCCESS,
                            message="Backend is running",
                            details={"url": backend_url}
                        )
                    else:
                        return CheckResult(
                            name="Backend API",
                            status=CheckStatus.WARNING,
                            message=f"Backend returned {response.status}",
                            details={"url": backend_url, "status_code": response.status}
                        )
        except Exception as e:
            # Check if it looks like it's not running
            if "Connection refused" in str(e) or "Cannot connect to host" in str(e):
                return CheckResult(
                    name="Backend API",
                    status=CheckStatus.WARNING,
                    message="Backend not running (starting up...)",
                    details={"url": backend_url},
                    repair_action="Backend will start automatically with the app"
                )
            return CheckResult(
                name="Backend API",
                status=CheckStatus.ERROR,
                message=f"Backend check failed: {str(e)}",
                details={"url": backend_url, "error": str(e)}
            )
    
    async def attempt_repair(self, check_id: str) -> CheckResult:
        """
        Attempt to repair a specific check.
        
        Args:
            check_id: Identifier of the check to repair (e.g., 'lm_studio', 'internet')
            
        Returns:
            Updated CheckResult after repair attempt
        """
        if check_id == "lm_studio":
            return await self.check_lm_studio(auto_start=True)
        elif check_id == "internet":
            return await self.check_internet(max_retries=5)
        elif check_id == "api_keys":
            return await self.validate_api_keys()
        elif check_id == "backend":
            return await self.check_backend()
        else:
            return CheckResult(
                name=check_id,
                status=CheckStatus.ERROR,
                message=f"Unknown check: {check_id}"
            )


# Convenience function for quick diagnosis
async def run_diagnosis(config: Dict[str, Any] = None, auto_repair: bool = True) -> DiagnosisReport:
    """
    Run full connectivity diagnosis.
    
    Args:
        config: Configuration dictionary
        auto_repair: If True, attempt auto-repairs
        
    Returns:
        DiagnosisReport with all results
    """
    doctor = ConnectionDoctor(config)
    return await doctor.full_diagnosis(auto_repair=auto_repair)


if __name__ == "__main__":
    # Test run
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        report = await run_diagnosis()
        print(f"\n{'='*50}")
        print(f"Overall Status: {report.overall_status.upper()}")
        print(f"{'='*50}")
        
        for check in report.checks:
            status_icon = "✅" if check.status == CheckStatus.SUCCESS else "⚠️" if check.status == CheckStatus.WARNING else "❌"
            print(f"{status_icon} {check.name}: {check.message}")
            if check.repair_action:
                print(f"   → {check.repair_action}")
        
        if report.suggested_repairs:
            print(f"\nSuggested Repairs:")
            for repair in report.suggested_repairs:
                print(f"  • {repair}")
    
    asyncio.run(main())
