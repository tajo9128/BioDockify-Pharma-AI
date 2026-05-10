from __future__ import annotations

from helpers import files, plugins, yaml as yaml_helper
from plugins._browser.helpers.config import (
    PLUGIN_NAME,
    browser_runtime_config,
    normalize_browser_config,
)
from plugins._browser.helpers.runtime import close_all_runtimes_sync


def _load_saved_browser_config(project_name: str = "", agent_profile: str = "") -> dict:
    entries = plugins.find_plugin_assets(
        plugins.CONFIG_FILE_NAME,
        plugin_name=PLUGIN_NAME,
        project_name=project_name,
        agent_profile=agent_profile,
        only_first=True,
    )
    path = entries[0].get("path", "") if entries else ""
    if path and files.exists(path):
        return files.read_file_json(path) or {}

    plugin_dir = plugins.find_plugin_dir(PLUGIN_NAME)
    default_path = (
        files.get_abs_path(plugin_dir, plugins.CONFIG_DEFAULT_FILE_NAME)
        if plugin_dir
        else ""
    )
    if default_path and files.exists(default_path):
        return yaml_helper.loads(files.read_file(default_path)) or {}

    return {}


def get_plugin_config(default=None, **kwargs):
    return normalize_browser_config(default)


def save_plugin_config(settings=None, project_name="", agent_profile="", **kwargs):
    normalized = normalize_browser_config(settings)
    current = normalize_browser_config(
        _load_saved_browser_config(project_name=project_name, agent_profile=agent_profile)
    )
    if browser_runtime_config(normalized) != browser_runtime_config(current):
        close_all_runtimes_sync()
    return normalized
