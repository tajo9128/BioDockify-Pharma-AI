"""
Hardware detection for the BioDockify AI Engine.

Used by:
  - the install script (to recommend a model variant before download)
  - the /api/local_llm 'hardware' action (so the UI can show readiness)
  - the status API (so users see whether their machine is suitable)

Pharma relevance: many pharma research machines are shared lab workstations
or older student laptops. Detecting capability BEFORE attempting to load a
multi-GB model prevents frustrating failures during a thesis deadline.
"""

import os
import platform
import shutil
import subprocess
import logging
from typing import Dict, Any

log = logging.getLogger("local_llm.hardware")


def detect_hardware() -> Dict[str, Any]:
    """Detect RAM, VRAM (if NVIDIA present), OS, and CPU info.

    Returns a dict with:
        os, cpu_count, ram_total_gb, ram_available_gb,
        gpu_present, gpu_name, vram_total_gb (None if unavailable),
        apple_silicon (bool)
    All probes are wrapped so a missing tool never breaks the call.
    """
    info: Dict[str, Any] = {
        "os": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count() or 0,
        "ram_total_gb": None,
        "ram_available_gb": None,
        "gpu_present": False,
        "gpu_name": None,
        "vram_total_gb": None,
        "apple_silicon": False,
    }

    # --- RAM (psutil is already a BioDockify requirement) ---
    try:
        import psutil
        vm = psutil.virtual_memory()
        info["ram_total_gb"] = round(vm.total / (1024 ** 3), 1)
        info["ram_available_gb"] = round(vm.available / (1024 ** 3), 1)
    except Exception as e:
        log.debug(f"psutil probe failed: {e}")

    # --- Apple Silicon detection (MLX runtime candidate) ---
    try:
        if platform.system() == "Darwin":
            if platform.machine() in ("arm64", "aarch64") or "Apple" in platform.processor():
                info["apple_silicon"] = True
                info["gpu_present"] = True
                info["gpu_name"] = "Apple Silicon (Unified Memory)"
    except Exception:
        pass

    # --- NVIDIA GPU detection via nvidia-smi ---
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi and not info["apple_silicon"]:
        try:
            out = subprocess.check_output(
                [nvidia_smi,
                 "--query-gpu=name,memory.total",
                 "--format=csv,noheader,nounits"],
                stderr=subprocess.STDOUT, timeout=5,
            ).decode("utf-8", errors="ignore").strip()
            if out:
                first = out.splitlines()[0]
                parts = [p.strip() for p in first.split(",")]
                if len(parts) >= 2:
                    info["gpu_present"] = True
                    info["gpu_name"] = parts[0]
                    try:
                        info["vram_total_gb"] = round(float(parts[1]) / 1024.0, 1)
                    except ValueError:
                        pass
        except Exception as e:
            log.debug(f"nvidia-smi probe failed: {e}")

    # --- Container note: this probes the CONTAINER's view, not the host. ---
    # When BioDockify runs in Docker with the default CPU-only llama.cpp
    # sidecar, gpu_present will be False here even if the host has a GPU.
    # GPU passthrough requires nvidia-container-toolkit; the install script
    # warns about this on Windows Docker Desktop / WSL2.
    if os.path.exists("/.dockerenv"):
        info["probe_scope"] = "container"
    else:
        info["probe_scope"] = "host"

    return info


def recommend_model(hardware: Dict[str, Any], catalog: Dict[str, Any]) -> Dict[str, Any]:
    """Given detected hardware and a model catalog, recommend a model id.

    Returns: {"recommended": "<model_id>", "reason": "...", "warnings": [...]}
    """
    warnings = []
    ram = hardware.get("ram_total_gb") or 0
    vram = hardware.get("vram_total_gb") or 0
    models = catalog.get("models", {})
    default_id = catalog.get("_meta", {}).get("default_model", "bonsai-8b")

    chosen = models.get(default_id)
    if not chosen:
        return {"recommended": None, "reason": "No models in catalog", "warnings": warnings}

    req = chosen.get("requirements", {})
    min_ram = req.get("min_ram_gb", 0)
    rec_ram = req.get("recommended_ram_gb", min_ram)

    reason_parts = [f"Default model '{default_id}'"]
    if ram and ram < min_ram:
        warnings.append(
            f"RAM {ram}GB is below minimum {min_ram}GB for {default_id}. "
            "Expect slow CPU inference or failures."
        )
    elif ram and ram < rec_ram:
        warnings.append(
            f"RAM {ram}GB meets minimum {min_ram}GB but below recommended {rec_ram}GB. "
            "Performance may be limited."
        )
    else:
        reason_parts.append(f"RAM {ram}GB OK")

    if vram:
        reason_parts.append(f"GPU {vram}GB VRAM detected")
    elif not hardware.get("apple_silicon"):
        warnings.append(
            "No NVIDIA GPU detected via nvidia-smi. CPU-only inference will be slow. "
            "For acceptable speed, install Ollama on the host and use the Ollama preset instead."
        )

    return {
        "recommended": default_id,
        "reason": "; ".join(reason_parts),
        "warnings": warnings,
    }
