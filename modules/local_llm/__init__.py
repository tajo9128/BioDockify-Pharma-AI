"""
BioDockify AI Engine — Local LLM runtime layer.

This module provides a provider-agnostic local LLM runtime for pharmaceutical
research workflows where cloud LLMs are unsuitable:

  - **Private inference**: literature on unpublished compounds, internal assay
    data, and PHI in case reports stay on-device. No egress.
  - **Air-gapped labs**: regulatory / GxP environments with no internet can
    still run AI-assisted claim verification, citation checks, and literature
    synthesis.
  - **Offline reproducibility**: thesis work and systematic reviews remain
    reproducible years later without depending on a cloud model's availability.

Design principles:
  - **Provider-agnostic**: the sidecar exposes an OpenAI-compatible /v1
    endpoint, so llama.cpp / Ollama / LM Studio / vLLM / mlx_lm.server are
    interchangeable with zero changes to Brain.
  - **Agent Zero untouched**: this package sits in BioDockify's own modules/
    tree and injects into Agent Zero via data-only files (presets.yaml) and
    BioDockify-only API handlers. No Agent Zero core file is modified.
  - **Model-agnostic**: the model catalog (models.json) is data; adding Gemma,
    Phi, Qwen, or a future pharma-tuned 8B requires zero code changes.

Public API:
    LocalLLMManager     — high-level status, probe, and install-check operations
    PharmaPromptLibrary — pharma-specific prompt templates for small local models
    detect_hardware     — RAM / VRAM / OS detection used for preset recommendation
    load_catalog        — read the model catalog (models.json)
"""

from .manager import LocalLLMManager, load_catalog
from .hardware import detect_hardware, recommend_model
from .pharma_prompts import PharmaPromptLibrary

__all__ = [
    "LocalLLMManager",
    "PharmaPromptLibrary",
    "detect_hardware",
    "recommend_model",
    "load_catalog",
]

__version__ = "1.0.0"
