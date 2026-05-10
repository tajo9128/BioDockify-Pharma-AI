from helpers.api import ApiHandler, Request
from plugins._browser.helpers.config import build_browser_launch_config, get_browser_config
from plugins._browser.helpers.playwright import (
    get_playwright_binary,
    get_playwright_cache_dir,
    get_playwright_cache_dirs,
)
from plugins._browser.helpers.runtime import known_context_ids


class Status(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        browser_config = get_browser_config()
        launch_config = build_browser_launch_config(browser_config)
        runtime_binary = get_playwright_binary(
            full_browser=launch_config["requires_full_browser"]
        )
        chromium_binary = get_playwright_binary(full_browser=True)
        return {
            "plugin": "_browser",
            "playwright": {
                "cache_dir": get_playwright_cache_dir(),
                "cache_dirs": [str(path) for path in get_playwright_cache_dirs()],
                "binary_found": bool(runtime_binary),
                "install_required": not bool(runtime_binary),
                "binary_path": str(runtime_binary) if runtime_binary else "",
                "chromium_binary_path": str(chromium_binary) if chromium_binary else "",
                "launch_mode": launch_config["browser_mode"],
            },
            "extensions": {
                **launch_config["extensions"],
                "launch_mode": launch_config["browser_mode"],
                "requires_full_browser": launch_config["requires_full_browser"],
            },
            "contexts": known_context_ids(),
        }
