from __future__ import annotations

from typing import Any

from helpers import plugins as plugin_helpers
from plugins._model_config.helpers import model_config


MODEL_PRESET_KEY = "model_preset"


def get_browser_model_preset_name(agent=None) -> str:
    config = plugin_helpers.get_plugin_config("_browser_agent", agent=agent) or {}
    return str(config.get(MODEL_PRESET_KEY, "") or "").strip()


def get_browser_model_preset_options(agent=None) -> list[dict[str, Any]]:
    selected_name = get_browser_model_preset_name(agent)
    options: list[dict[str, Any]] = []
    found_selected = False

    for preset in model_config.get_presets():
        name = str(preset.get("name", "") or "").strip()
        if not name:
            continue
        if name == selected_name:
            found_selected = True
        chat_cfg = preset.get("chat", {}) if isinstance(preset, dict) else {}
        if not isinstance(chat_cfg, dict):
            chat_cfg = {}
        provider = str(chat_cfg.get("provider", "") or "").strip()
        model_name = str(chat_cfg.get("name", "") or "").strip()
        summary = " / ".join(part for part in (provider, model_name) if part)
        options.append(
            {
                "name": name,
                "label": name,
                "missing": False,
                "summary": summary,
            }
        )

    if selected_name and not found_selected:
        options.append(
            {
                "name": selected_name,
                "label": f"{selected_name} (missing)",
                "missing": True,
                "summary": "",
            }
        )

    return options


def resolve_browser_model_selection(agent=None) -> dict[str, Any]:
    preset_name = get_browser_model_preset_name(agent)
    if preset_name:
        preset = model_config.get_preset_by_name(preset_name)
        if isinstance(preset, dict):
            chat_cfg = preset.get("chat", {})
            if isinstance(chat_cfg, dict) and (
                str(chat_cfg.get("provider", "") or "").strip()
                or str(chat_cfg.get("name", "") or "").strip()
            ):
                return {
                    "config": chat_cfg,
                    "source_kind": "preset",
                    "source_label": f"Preset '{preset_name}' via _model_config",
                    "selected_preset_name": preset_name,
                    "preset_status": "active",
                    "warning": "",
                }
            return {
                "config": model_config.get_chat_model_config(agent),
                "source_kind": "main",
                "source_label": "Main Model via _model_config",
                "selected_preset_name": preset_name,
                "preset_status": "invalid",
                "warning": (
                    f"Configured browser preset '{preset_name}' does not define a chat model. "
                    "Falling back to the Main Model."
                ),
            }

        return {
            "config": model_config.get_chat_model_config(agent),
            "source_kind": "main",
            "source_label": "Main Model via _model_config",
            "selected_preset_name": preset_name,
            "preset_status": "missing",
            "warning": (
                f"Configured browser preset '{preset_name}' was not found. "
                "Falling back to the Main Model."
            ),
        }

    return {
        "config": model_config.get_chat_model_config(agent),
        "source_kind": "main",
        "source_label": "Main Model via _model_config",
        "selected_preset_name": "",
        "preset_status": "none",
        "warning": "",
    }


def save_browser_model_preset_name(preset_name: str) -> None:
    normalized = str(preset_name or "").strip()
    config = plugin_helpers.get_plugin_config("_browser_agent") or {}

    if normalized:
        config[MODEL_PRESET_KEY] = normalized
    else:
        config.pop(MODEL_PRESET_KEY, None)

    plugin_helpers.save_plugin_config(
        "_browser_agent",
        project_name="",
        agent_profile="",
        settings=config,
    )
