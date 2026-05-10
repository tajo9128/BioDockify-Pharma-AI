from __future__ import annotations

import threading
from typing import Any

from helpers.extension import Extension
from helpers.print_style import PrintStyle
from plugins._office import hooks
from plugins._office.helpers import libreoffice_desktop_routes


_startup_preparation_thread: threading.Thread | None = None


class OfficeStartupCleanup(Extension):
    def execute(self, **kwargs):
        libreoffice_desktop_routes.install_route_hooks()
        _start_background_runtime_preparation()


def _start_background_runtime_preparation() -> threading.Thread:
    global _startup_preparation_thread

    if _startup_preparation_thread and _startup_preparation_thread.is_alive():
        return _startup_preparation_thread

    _startup_preparation_thread = threading.Thread(
        target=_prepare_runtime_safely,
        name="a0-office-runtime-preparation",
        daemon=True,
    )
    _startup_preparation_thread.start()
    return _startup_preparation_thread


def _prepare_runtime_safely() -> None:
    try:
        _log_runtime_preparation_result(hooks.cleanup_stale_runtime_state())
    except Exception as exc:
        PrintStyle.warning("Office runtime preparation failed:", exc)


def _log_runtime_preparation_result(result: dict[str, Any]) -> None:
    if result.get("errors"):
        PrintStyle.warning("Office runtime preparation reported errors:", result["errors"])
    elif result.get("installed") or result.get("removed"):
        PrintStyle.info("Office runtime prepared:", result)
