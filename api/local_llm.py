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
        if action == "runtimes":
            return await self._runtimes(input, request)
        if action == "prompts":
            return await self._prompts(input, request)
        if action == "readiness":
            return await self._readiness(input, request)
        if action == "benchmark":
            return await self._benchmark(input, request)

        return {
            "status": "error",
            "error": (
                f"Unknown action '{action}'. Valid: status, hardware, catalog, "
                "runtimes, prompts, readiness, benchmark."
            ),
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

    async def _runtimes(self, input, request) -> Response:
        """List all registered runtimes (llama.cpp sidecar, host Ollama,
        host LM Studio, future vLLM / MLX). Used by the Settings UI to let
        users see and (future) switch runtime backends without code changes.
        """
        from modules.local_llm.manager import load_runtimes, get_default_runtime
        rt = load_runtimes()
        default_id = rt.get("_meta", {}).get("default_runtime")
        return {
            "status": "ok",
            "default_runtime": default_id,
            "active_runtime": get_default_runtime().get("display_name"),
            "runtimes": rt.get("runtimes", {}),
        }

    async def _benchmark(self, input, request) -> Response:
        """Run a 50-token benchmark against the active runtime and report tok/s.

        Generates a small fixed prompt, measures wall-clock time for the
        response, and produces a verdict (Good / OK / Slow) the UI can show.
        Honors a max_tokens cap (default 50) and a timeout (default 30s) to
        keep it cheap and bounded.
        """
        import asyncio
        from modules.local_llm.manager import LocalLLMManager
        mgr = LocalLLMManager()
        urls = mgr._runtime_urls()
        max_tokens = int((input or {}).get("max_tokens", 50))
        timeout_s = float((input or {}).get("timeout", 30))

        # First check the runtime is reachable — fail fast with a clear message.
        health = await mgr.probe_sidecar()
        if not health.get("reachable"):
            return {
                "status": "error",
                "error": "Runtime not reachable. Cannot benchmark.",
                "health": health,
            }

        def _do() -> dict:
            import time
            import urllib.request
            import urllib.error
            url = urls["api_base"].rstrip("/") + "/chat/completions"
            payload = {
                "model": (input or {}).get("model") or mgr.catalog.get("_meta", {}).get("default_model", "bonsai-8b"),
                "messages": [
                    {"role": "system", "content": "You are the BioDockify AI Engine. Reply concisely."},
                    {"role": "user", "content": "List three ICH E6 Good Clinical Practice principles, one short line each."}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.0,
                "stream": False,
            }
            body = __import__("json").dumps(payload).encode("utf-8")
            t0 = time.time()
            try:
                req = urllib.request.Request(
                    url, data=body, method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=timeout_s) as r:
                    data = __import__("json").loads(r.read().decode("utf-8"))
                    elapsed = time.time() - t0
                    usage = data.get("usage", {}) or {}
                    completion_tokens = usage.get("completion_tokens", 0) or 0
                    tok_s = (completion_tokens / elapsed) if elapsed > 0 and completion_tokens else 0
                    if tok_s >= 20:
                        verdict = "Good"
                    elif tok_s >= 8:
                        verdict = "OK"
                    elif tok_s > 0:
                        verdict = "Slow"
                    else:
                        verdict = "No tokens returned"
                    return {
                        "status": "ok",
                        "elapsed_s": round(elapsed, 2),
                        "completion_tokens": completion_tokens,
                        "tokens_per_second": round(tok_s, 1),
                        "verdict": verdict,
                        "max_tokens": max_tokens,
                        "sample": (data.get("choices") or [{}])[0].get("message", {}).get("content", "")[:200],
                    }
            except urllib.error.HTTPError as e:
                return {"status": "error", "error": f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}"}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        return await asyncio.to_thread(_do)

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
