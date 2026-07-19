"""
BioDockify AI Engine — Local LLM status API.

Provides:
  - status   : rich health/readiness of the local LLM sidecar + recommended model
  - hardware : detected RAM / VRAM / GPU / OS for install-readiness UI
  - catalog  : list of installable models from the data-driven catalog
  - prompts  : list of available pharma prompt templates + render one for preview

This handler is faculty-only (auth required) because it exposes hardware info
and is intended for the researcher configuring the platform, not the chat
end-user. It does NOT execute installs (the host-side script does that) and
does NOT call the model — preset application routes via LiteLLM as usual.

Agent Zero is NOT modified. This handler follows BioDockify's standard
ApiHandler pattern (see api/health.py).
"""

import logging
from helpers.api import ApiHandler, Request, Response

log = logging.getLogger("api.local_llm")


class LocalLLMHandler(ApiHandler):

    @classmethod
    def requires_auth(cls) -> bool:
        # Faculty-only: exposes hardware info + readiness, not chat.
        return True

    async def process(self, input, request: Request) -> Response:
        action = (input or {}).get("action", "status")

        if action == "status":
            return await self._status(input, request)
        if action == "hardware":
            return await self._hardware(input, request)
        if action == "catalog":
            return await self._catalog(input, request)
        if action == "prompts":
            return await self._prompts(input, request)
        if action == "readiness":
            return await self._readiness(input, request)

        return {
            "status": "error",
            "error": f"Unknown action '{action}'. Valid: status, hardware, catalog, prompts, readiness.",
        }

    # --------------------------------------------------------------- actions
    async def _status(self, input, request) -> Response:
        from modules.local_llm.manager import LocalLLMManager
        mgr = LocalLLMManager()
        model_id = (input or {}).get("model_id")
        return {"status": "ok", **(await mgr.get_model_status(model_id))}

    async def _hardware(self, input, request) -> Response:
        import asyncio
        from modules.local_llm.hardware import detect_hardware, recommend_model
        from modules.local_llm.manager import load_catalog
        hw = await asyncio.to_thread(detect_hardware)
        rec = recommend_model(hw, load_catalog())
        return {"status": "ok", "hardware": hw, "recommendation": rec}

    async def _catalog(self, input, request) -> Response:
        from modules.local_llm.manager import load_catalog
        cat = load_catalog()
        # Strip the placeholder / internal keys before returning
        return {
            "status": "ok",
            "engine_name": "BioDockify AI Engine",
            "default_model": cat.get("_meta", {}).get("default_model"),
            "models": list(cat.get("models", {}).keys()),
            "model_details": cat.get("models", {}),
        }

    async def _prompts(self, input, request) -> Response:
        from modules.local_llm.pharma_prompts import PharmaPromptLibrary
        task = (input or {}).get("task")
        if task:
            kwargs = {}
            if task == "thesis":
                kwargs["section"] = (input or {}).get("section", "methods")
            if task == "ich":
                kwargs["study_type"] = (input or {}).get("study_type", "clinical_trial")
            rendered = PharmaPromptLibrary.for_task(task, **kwargs)
            return {"status": "ok", "task": task, "prompt": rendered}
        return {"status": "ok", "available_tasks": PharmaPromptLibrary.available_tasks()}

    async def _readiness(self, input, request) -> Response:
        from modules.local_llm.manager import LocalLLMManager
        mgr = LocalLLMManager()
        return {"status": "ok", **mgr.install_readiness()}
