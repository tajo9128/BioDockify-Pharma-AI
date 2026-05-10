import os
import subprocess
from pathlib import Path

from helpers import files

FULL_CHROMIUM_PATTERNS = (
    "chromium-*/chrome-linux/chrome",
    "chromium-*/chrome-win/chrome.exe",
)
PLAYWRIGHT_CACHE_ENV = "A0_BROWSER_PLAYWRIGHT_CACHE_DIR"
PLAYWRIGHT_CACHE_DIR = ("usr", "plugins", "_browser", "playwright")
PREVIOUS_PLAYWRIGHT_CACHE_DIR = ("usr", "browser", "playwright")
LEGACY_PLAYWRIGHT_CACHE_DIR = ("tmp", "playwright")


def _primary_cache_dir() -> Path:
    override = os.environ.get(PLAYWRIGHT_CACHE_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return Path(files.get_abs_path(*PLAYWRIGHT_CACHE_DIR))


def get_playwright_cache_dir() -> str:
    return str(_primary_cache_dir())


def get_playwright_cache_dirs() -> list[Path]:
    primary = _primary_cache_dir()
    candidates = [
        primary,
        Path(files.get_abs_path(*PREVIOUS_PLAYWRIGHT_CACHE_DIR)),
        Path(files.get_abs_path(*LEGACY_PLAYWRIGHT_CACHE_DIR)),
    ]
    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def configure_playwright_env() -> str:
    cache_dir = get_playwright_cache_dir()
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = cache_dir
    return cache_dir


def get_playwright_binary(*, full_browser: bool = False) -> Path | None:
    for cache_dir in get_playwright_cache_dirs():
        for pattern in FULL_CHROMIUM_PATTERNS:
            binary = next(cache_dir.glob(pattern), None)
            if binary and binary.exists():
                return binary
    return None


def ensure_playwright_binary(*, full_browser: bool = False) -> Path:
    binary = get_playwright_binary(full_browser=full_browser)
    if binary:
        return binary

    cache_dir = configure_playwright_env()
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = cache_dir
    install_command = ["playwright", "install", "chromium"]
    subprocess.check_call(
        install_command,
        env=env,
    )

    binary = get_playwright_binary(full_browser=full_browser)
    if not binary:
        raise RuntimeError("Playwright Chromium binary not found after installation")
    return binary
