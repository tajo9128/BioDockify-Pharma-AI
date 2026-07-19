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
# llama-server runs INSIDE the BioDockify container (bundled, not a sidecar).
# Model is stored at /a0/usr/ai_models/ in the biodockify_usr volume.
SIDECAR_HOST = os.environ.get("LOCAL_LLM_HOST", "localhost")
SIDECAR_PORT = int(os.environ.get("LOCAL_LLM_PORT", "8080"))
SIDECAR_HEALTH_PATH = "/health"
SIDECAR_V1_BASE = f"http://{SIDECAR_HOST}:{SIDECAR_PORT}/v1"
SIDECAR_HEALTH_URL = f"http://{SIDECAR_HOST}:{SIDECAR_PORT}{SIDECAR_HEALTH_PATH}"

# Where the GGUF lives inside the container (bundled in Docker image)
SIDECAR_MODEL_PATH = "/opt/llama-server/models"

_CATALOG_CACHE: Optional[Dict[str, Any]] = None
_RUNTIMES_CACHE: Optional[Dict[str, Any]] = None


def _catalog_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "models.json")


def _runtimes_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "runtimes.json")


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


def load_runtimes(force: bool = False) -> Dict[str, Any]:
    """Load the runtime registry (modules/local_llm/runtimes.json).

    The Brain stays runtime-agnostic: it always talks to the active runtime's
    OpenAI-compatible api_base. Switching runtimes (llama.cpp → Ollama → MLX
    → vLLM) is a data-only change here + a preset api_base update.
    """
    global _RUNTIMES_CACHE
    if _RUNTIMES_CACHE is not None and not force:
        return _RUNTIMES_CACHE
    try:
        with open(_runtimes_path(), "r", encoding="utf-8") as f:
            _RUNTIMES_CACHE = json.load(f)
        return _RUNTIMES_CACHE
    except Exception as e:
        log.warning(f"Failed to load runtimes registry: {e}")
        return {"_meta": {"default_runtime": "llama_cpp_local"}, "runtimes": {}}


def get_default_runtime() -> Dict[str, Any]:
    """Return the currently-active runtime entry."""
    rt = load_runtimes()
    rid = rt.get("_meta", {}).get("default_runtime", "llama_cpp_local")
    return rt.get("runtimes", {}).get(rid, {})


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
        self.runtimes = load_runtimes()
        self.runtime = get_default_runtime()

    # --- Runtime endpoint helpers (runtime-agnostic) ------------------------
    def _runtime_urls(self) -> Dict[str, str]:
        """Derive health/models/v1 URLs from the active runtime registry entry.

        Falls back to the bundled-sidecar constants if the registry entry is
        missing or malformed — defensive so a bad runtimes.json never crashes
        the API.
        """
        ep = (self.runtime or {}).get("endpoint", {}) or {}
        api_base = ep.get("api_base") or SIDECAR_V1_BASE
        health_path = ep.get("health_path") or SIDECAR_HEALTH_PATH
        models_path = ep.get("models_path") or "/v1/models"
        # health URL = api_base's origin + health_path
        origin = api_base.rstrip("/").rsplit("/v1", 1)[0] if api_base.endswith("/v1") else api_base.rstrip("/")
        # For Ollama-style runtimes, api_base already includes the full origin
        # and health_path is /api/tags. Just concatenate.
        if health_path.startswith("/v1") or health_path.startswith("/api"):
            models_url = f"{origin}{health_path}" if health_path == models_path else f"{origin}{models_path}"
            health_url = f"{origin}{health_path}"
        else:
            health_url = f"{origin}{health_path}"
            models_url = f"{origin}{models_path}"
        return {"api_base": api_base, "health": health_url, "models": models_url}

    async def probe_sidecar(self) -> Dict[str, Any]:
        """Probe the active runtime's health endpoint.

        Runtime-agnostic: works for llama.cpp (/health), Ollama (/api/tags),
        LM Studio (/v1/models), vLLM (/health), MLX (/health).
        Returns {reachable, latency_ms, error?}.
        """
        urls = self._runtime_urls()

        def _do() -> Dict[str, Any]:
            import time
            import urllib.request
            import urllib.error
            t0 = time.time()
            try:
                req = urllib.request.Request(urls["health"], method="GET")
                with urllib.request.urlopen(req, timeout=3) as r:
                    latency = int((time.time() - t0) * 1000)
                    return {"reachable": 200 <= r.status < 300, "latency_ms": latency}
            except urllib.error.URLError as e:
                return {"reachable": False, "latency_ms": None, "error": f"connection: {e.reason}"}
            except Exception as e:
                return {"reachable": False, "latency_ms": None, "error": str(e)}

        return await asyncio.to_thread(_do)

    async def list_sidecar_models(self) -> Dict[str, Any]:
        """Call the active runtime's model-listing endpoint (OpenAI-compatible
        for llama.cpp/LM Studio/vLLM/MLX; /api/tags for Ollama)."""
        urls = self._runtime_urls()
        rid = (self.runtimes.get("_meta") or {}).get("default_runtime", "llama_cpp_local")
        is_ollama = "ollama" in rid

        def _do() -> Dict[str, Any]:
            import urllib.request
            import urllib.error
            try:
                req = urllib.request.Request(urls["models"], method="GET")
                with urllib.request.urlopen(req, timeout=5) as r:
                    data = json.loads(r.read().decode("utf-8"))
                    if is_ollama:
                        # Ollama /api/tags returns {"models": [{"name": "..."}, ...]}
                        ids = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    else:
                        # OpenAI-compatible /v1/models returns {"data": [{"id": "..."}, ...]}
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
        rid = (self.runtimes.get("_meta") or {}).get("default_runtime", "llama_cpp_local")
        rt_info = self.runtimes.get("runtimes", {}).get(rid, {})
        if not sidecar_health.get("reachable"):
            if rt_info.get("kind") == "bundled":
                notes.append(
                    f"Runtime '{rid}' not reachable. Enable it with: "
                    "`docker compose --profile local-llm up -d`, then run "
                    "`scripts/install_bonsai.sh` (or .bat) once to download the model."
                )
            else:
                host_url = (rt_info.get("endpoint") or {}).get("api_base", "the host service")
                notes.append(
                    f"Runtime '{rid}' not reachable at {host_url}. "
                    f"Install it on the host: {rt_info.get('host_install_url', 'see docs')}, "
                    "then ensure BioDockify can reach host.docker.internal."
                )
        else:
            notes.append(f"Runtime '{rid}' is healthy.")

        if not sidecar_models.get("models"):
            notes.append(
                "Runtime is up but no model is loaded. Run the install script to "
                "download the GGUF into the biodockify_models volume, then restart "
                "the sidecar (or pull the model in your host Ollama / LM Studio)."
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
            "runtime": {
                "id": rid,
                "display_name": rt_info.get("display_name"),
                "kind": rt_info.get("kind"),
                "litellm_provider": rt_info.get("litellm_provider"),
                "endpoint": (rt_info.get("endpoint") or {}).get("api_base"),
            },
            "sidecar": {
                "running": bool(sidecar_health.get("reachable")),
                "latency_ms": sidecar_health.get("latency_ms"),
                "loaded_models": sidecar_models.get("models") or [],
                "model_loaded": loaded_match,
                "endpoint": (rt_info.get("endpoint") or {}).get("api_base") or SIDECAR_V1_BASE,
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
