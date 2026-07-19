"""
BioDockify AI Engine — local LLM runtime manager.

This module never imports Agent Zero internals and never modifies Agent Zero
state. It only:
  - probes the optional llama.cpp sidecar
  - reads the model catalog (models.json)
  - reports rich status for the Settings UI and health endpoints
  - prepares install commands (execution happens in install_bonsai.sh/.bat)

The actual model lives in a Docker named volume (`biodockify_models`), not in
the image — so image updates never re-download the model.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional

log = logging.getLogger("local_llm.manager")

# --- Constants (also referenced by docs/install scripts) -------------------
SIDECAR_HOST = os.environ.get("LOCAL_LLM_HOST", "llama-server")
SIDECAR_PORT = int(os.environ.get("LOCAL_LLM_PORT", "8080"))
SIDECAR_HEALTH_PATH = "/health"
SIDECAR_V1_BASE = f"http://{SIDECAR_HOST}:{SIDECAR_PORT}/v1"
SIDECAR_HEALTH_URL = f"http://{SIDECAR_HOST}:{SIDECAR_PORT}{SIDECAR_HEALTH_PATH}"

# Where the GGUF must be inside the sidecar container
SIDECAR_MODEL_PATH = "/models"

_CATALOG_CACHE: Optional[Dict[str, Any]] = None


def _catalog_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "models.json")


def load_catalog(force: bool = False) -> Dict[str, Any]:
    """Load the model catalog (modules/local_llm/models.json)."""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None and not force:
        return _CATALOG_CACHE
    try:
        with open(_catalog_path(), "r", encoding="utf-8") as f:
            _CATALOG_CACHE = json.load(f)
        return _CATALOG_CACHE
    except Exception as e:
        log.warning(f"Failed to load model catalog: {e}")
        return {"_meta": {"default_model": "bonsai-8b"}, "models": {}}


def get_model_info(model_id: str) -> Optional[Dict[str, Any]]:
    """Return one model entry from the catalog, or None."""
    return load_catalog().get("models", {}).get(model_id)


class LocalLLMManager:
    """High-level status and probe operations for the local LLM runtime.

    All methods are safe to call from async API handlers. Blocking probes use
    asyncio.to_thread so they never stall the event loop.
    """

    def __init__(self) -> None:
        self.catalog = load_catalog()

    # --- Sidecar probes -----------------------------------------------------
    async def probe_sidecar(self) -> Dict[str, Any]:
        """Probe the llama.cpp sidecar /health endpoint.

        Returns {reachable, latency_ms, error?}.
        """
        def _do() -> Dict[str, Any]:
            import time
            import urllib.request
            import urllib.error
            t0 = time.time()
            try:
                req = urllib.request.Request(SIDECAR_HEALTH_URL, method="GET")
                with urllib.request.urlopen(req, timeout=3) as r:
                    latency = int((time.time() - t0) * 1000)
                    return {"reachable": 200 <= r.status < 300, "latency_ms": latency}
            except urllib.error.URLError as e:
                return {"reachable": False, "latency_ms": None, "error": f"connection: {e.reason}"}
            except Exception as e:
                return {"reachable": False, "latency_ms": None, "error": str(e)}

        return await asyncio.to_thread(_do)

    async def list_sidecar_models(self) -> Dict[str, Any]:
        """Call GET /v1/models on the sidecar (OpenAI-compatible)."""
        def _do() -> Dict[str, Any]:
            import urllib.request
            import urllib.error
            url = f"{SIDECAR_V1_BASE}/models"
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=5) as r:
                    data = json.loads(r.read().decode("utf-8"))
                    ids = [m.get("id") for m in data.get("data", []) if m.get("id")]
                    return {"reachable": True, "models": ids}
            except Exception as e:
                return {"reachable": False, "models": [], "error": str(e)}

        return await asyncio.to_thread(_do)

    # --- Composite status (rich, for Settings UI) --------------------------
    async def get_model_status(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Rich status combining catalog + sidecar + hardware.

        Returns a dict suitable for the /api/local_llm 'status' action and the
        Settings UI badge:
            {
              "engine_name": "BioDockify AI Engine",
              "default_model": "bonsai-8b",
              "model": {...catalog entry...},
              "sidecar": {"running": bool, "latency_ms": int, "loaded_models": [...]},
              "endpoint": "http://llama-server:8080/v1",
              "preset_name": "BioDockify AI Engine — Local (Bonsai-8B)",
              "hardware_ok": bool,
              "notes": [...]
            }
        """
        from .hardware import detect_hardware, recommend_model

        catalog = self.catalog
        mid = model_id or catalog.get("_meta", {}).get("default_model", "bonsai-8b")
        model = catalog.get("models", {}).get(mid)

        sidecar_health = await self.probe_sidecar()
        sidecar_models = await self.list_sidecar_models()

        hw = await asyncio.to_thread(detect_hardware)
        rec = recommend_model(hw, catalog)

        notes = []
        if not sidecar_health.get("reachable"):
            notes.append(
                "Sidecar not reachable. Enable it with: "
                "`docker compose --profile local-llm up -d`, then run "
                "`scripts/install_bonsai.sh` (or .bat) once to download the model."
            )
        else:
            notes.append("Sidecar is healthy.")

        if not sidecar_models.get("models"):
            notes.append(
                "Sidecar is up but no model is loaded. Run the install script to "
                "download the GGUF into the biodockify_models volume, then restart "
                "the sidecar."
            )

        loaded_match = (mid in (sidecar_models.get("models") or []))

        return {
            "engine_name": "BioDockify AI Engine",
            "default_model": catalog.get("_meta", {}).get("default_model"),
            "model_id": mid,
            "model": {
                "display_name": model.get("display_name") if model else None,
                "size_gb": (model or {}).get("gguf", {}).get("size_gb"),
                "context_length": (model or {}).get("runtime", {}).get("ctx_length"),
                "supports_gpu": (model or {}).get("runtime", {}).get("supports_gpu", True),
                "supports_cpu": (model or {}).get("runtime", {}).get("supports_cpu", True),
            } if model else None,
            "sidecar": {
                "running": bool(sidecar_health.get("reachable")),
                "latency_ms": sidecar_health.get("latency_ms"),
                "loaded_models": sidecar_models.get("models") or [],
                "model_loaded": loaded_match,
                "endpoint": SIDECAR_V1_BASE,
            },
            "hardware": {
                "ram_total_gb": hw.get("ram_total_gb"),
                "vram_total_gb": hw.get("vram_total_gb"),
                "gpu_present": hw.get("gpu_present"),
                "gpu_name": hw.get("gpu_name"),
                "apple_silicon": hw.get("apple_silicon"),
                "probe_scope": hw.get("probe_scope"),
            },
            "recommendation": rec,
            "preset_name": "BioDockify AI Engine — Local (Bonsai-8B)",
            "notes": notes,
        }

    # --- Install readiness check (does NOT execute install) ----------------
    def install_readiness(self) -> Dict[str, Any]:
        """Pre-flight checks the install script also performs.

        Returns {ready, docker_available, volume_exists, model_present,
                 model_path_inside_volume, warnings, instructions}.
        """
        from .hardware import detect_hardware

        warnings = []
        docker_ok = shutil_which("docker") is not None
        if not docker_ok:
            warnings.append("docker CLI not found on PATH inside container.")

        # Inside the biodockify container, the named volume is mounted at /models?
        # No — the model volume is mounted INSIDE the sidecar, not biodockify.
        # The biodockify container reaches the model only via HTTP /v1.
        # So we cannot directly stat the GGUF from here; we infer from sidecar.
        volume_info = {
            "name": "biodockify_models",
            "mounted_in": "llama-server sidecar at /models",
            "note": "Model files are owned by the sidecar; biodockify reaches them via HTTP."
        }

        hw = detect_hardware()
        mid = self.catalog.get("_meta", {}).get("default_model", "bonsai-8b")
        model = self.catalog.get("models", {}).get(mid, {})
        req = model.get("requirements", {})
        if hw.get("ram_total_gb") and hw["ram_total_gb"] < req.get("min_ram_gb", 0):
            warnings.append(
                f"Container RAM {hw['ram_total_gb']}GB is below "
                f"{req.get('min_ram_gb')}GB minimum for {mid}."
            )

        return {
            "ready": docker_ok,
            "docker_available": docker_ok,
            "volume": volume_info,
            "default_model_id": mid,
            "model_size_gb": model.get("gguf", {}).get("size_gb"),
            "instructions": (
                "1) Run scripts/install_bonsai.sh (Linux/macOS) or "
                "scripts/install_bonsai.bat (Windows) on the HOST. "
                "2) Restart BioDockify. "
                "3) In Settings → Models, choose preset "
                "'BioDockify AI Engine — Local (Bonsai-8B)'."
            ),
            "warnings": warnings,
        }


def shutil_which(cmd: str) -> Optional[str]:
    import shutil as _s
    return _s.which(cmd)
