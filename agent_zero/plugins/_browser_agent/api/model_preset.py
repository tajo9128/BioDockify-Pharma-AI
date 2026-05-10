from helpers.api import ApiHandler, Request, Response

from plugins._browser_agent.helpers.model_preset import (
    get_browser_model_preset_name,
    save_browser_model_preset_name,
)
from plugins._model_config.helpers import model_config


class ModelPreset(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = str(input.get("action", "get") or "get").strip().lower()

        if action == "get":
            return {
                "ok": True,
                "preset_name": get_browser_model_preset_name(),
            }

        if action not in {"set", "clear"}:
            return Response(status=400, response=f"Unknown action: {action}")

        preset_name = ""
        if action == "set":
            preset_name = str(input.get("preset_name", "") or "").strip()
            if not preset_name:
                return Response(status=400, response="Missing preset_name")
            if not model_config.get_preset_by_name(preset_name):
                return Response(status=404, response=f"Preset '{preset_name}' not found")

        save_browser_model_preset_name(preset_name)
        return {
            "ok": True,
            "preset_name": preset_name,
        }
