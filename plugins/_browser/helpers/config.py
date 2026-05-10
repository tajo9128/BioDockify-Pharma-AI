from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import Agent


PLUGIN_NAME = "_browser"
MODEL_PRESET_KEY = "model_preset"
DEFAULT_HOMEPAGE_KEY = "default_homepage"
AUTOFOCUS_ACTIVE_PAGE_KEY = "autofocus_active_page"
BASE_BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
]


def _normalize_extension_paths(value: Any) -> list[str]:
    if isinstance(value, str):
        candidates = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    elif isinstance(value, (list, tuple, set)):
        candidates = list(value)
    else:
        candidates = []

    normalized_paths: list[str] = []
    seen: set[str] = set()
    for entry in candidates:
        raw_path = str(entry or "").strip()
        if not raw_path:
            continue
        normalized = str(Path(raw_path).expanduser())
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_paths.append(normalized)
    return normalized_paths


def _normalize_model_preset(value: Any) -> str:
    return str(value or "").strip()


def _normalize_default_homepage(value: Any) -> str:
    homepage = str(value or "").strip()
    return homepage or "about:blank"


def _normalize_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "off", "disabled"}:
        return False
    return default


def _model_config_summary(config: dict[str, Any] | None) -> str:
    if not isinstance(config, dict):
        return ""
    provider = str(config.get("provider", "") or "").strip()
    model_name = str(config.get("name", "") or "").strip()
    return " / ".join(part for part in (provider, model_name) if part)


def normalize_browser_config(settings: dict[str, Any] | None) -> dict[str, Any]:
    raw = settings if isinstance(settings, dict) else {}
    extension_paths = _normalize_extension_paths(raw.get("extension_paths", []))
    return {
        "extension_paths": extension_paths,
        DEFAULT_HOMEPAGE_KEY: _normalize_default_homepage(
            raw.get(DEFAULT_HOMEPAGE_KEY, raw.get("starting_page", "about:blank"))
        ),
        AUTOFOCUS_ACTIVE_PAGE_KEY: _normalize_bool(
            raw.get(AUTOFOCUS_ACTIVE_PAGE_KEY, True),
            default=True,
        ),
        MODEL_PRESET_KEY: _normalize_model_preset(raw.get(MODEL_PRESET_KEY, "")),
    }


def browser_runtime_config(settings: dict[str, Any] | None) -> dict[str, Any]:
    config = normalize_browser_config(settings)
    return {
        "extension_paths": config["extension_paths"],
    }


def get_browser_config(agent: "Agent | None" = None) -> dict[str, Any]:
    from helpers import plugins

    return normalize_browser_config(plugins.get_plugin_config(PLUGIN_NAME, agent=agent) or {})


def get_browser_model_preset_name(
    agent: "Agent | None" = None,
    settings: dict[str, Any] | None = None,
) -> str:
    config = (
        normalize_browser_config(settings)
        if settings is not None
        else get_browser_config(agent=agent)
    )
    return str(config.get(MODEL_PRESET_KEY, "") or "").strip()


def get_browser_model_preset_options(
    agent: "Agent | None" = None,
    settings: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    from plugins._model_config.helpers import model_config

    selected_name = get_browser_model_preset_name(agent=agent, settings=settings)
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
        summary = _model_config_summary(chat_cfg)
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


def get_browser_main_model_summary(agent: "Agent | None" = None) -> str:
    from plugins._model_config.helpers import model_config

    return _model_config_summary(model_config.get_chat_model_config(agent))


def resolve_browser_model_selection(
    agent: "Agent | None" = None,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from plugins._model_config.helpers import model_config

    preset_name = get_browser_model_preset_name(agent=agent, settings=settings)
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


def resolve_browser_model(agent: "Agent", settings: dict[str, Any] | None = None):
    selection = resolve_browser_model_selection(agent=agent, settings=settings)
    if selection["source_kind"] == "main":
        return agent.get_chat_model()

    import models
    from plugins._model_config.helpers import model_config

    model_config_object = model_config.build_model_config(
        selection["config"],
        models.ModelType.CHAT,
    )
    return models.get_chat_model(
        model_config_object.provider,
        model_config_object.name,
        model_config=model_config_object,
        **model_config_object.build_kwargs(),
    )


def describe_browser_extensions(settings: dict[str, Any] | None) -> dict[str, Any]:
    config = normalize_browser_config(settings)
    path_details: list[dict[str, Any]] = []
    for extension_path in config["extension_paths"]:
        path = Path(extension_path)
        exists = path.exists()
        is_dir = path.is_dir() if exists else False
        path_details.append(
            {
                "path": extension_path,
                "exists": exists,
                "is_dir": is_dir,
                "loadable": exists and is_dir,
            }
        )

    active_paths = [item["path"] for item in path_details if item["loadable"]]
    invalid_paths = [item["path"] for item in path_details if not item["loadable"]]
    active = bool(active_paths)

    warnings: list[str] = []
    if config["extension_paths"] and not active_paths:
        warnings.append(
            "None of the enabled extension directories are readable unpacked folders."
        )
    elif invalid_paths:
        warnings.append(
            "Some configured extension directories are missing or not directories, so they will be skipped."
        )

    return {
        "active": active,
        "configured_paths": config["extension_paths"],
        "active_paths": active_paths,
        "invalid_paths": invalid_paths,
        "path_details": path_details,
        "active_path_count": len(active_paths),
        "warnings": warnings,
    }


def build_browser_launch_config(settings: dict[str, Any] | None) -> dict[str, Any]:
    extensions = describe_browser_extensions(settings)
    args = list(BASE_BROWSER_ARGS)
    channel: str | None = None
    browser_mode = "chromium"

    if extensions["active"]:
        joined_paths = ",".join(extensions["active_paths"])
        args.extend(
            [
                f"--disable-extensions-except={joined_paths}",
                f"--load-extension={joined_paths}",
            ]
        )

    return {
        "args": args,
        "browser_mode": browser_mode,
        "channel": channel,
        "extensions": extensions,
        "requires_full_browser": True,
    }
