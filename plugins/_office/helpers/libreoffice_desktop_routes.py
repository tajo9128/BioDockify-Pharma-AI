from __future__ import annotations

from helpers.virtual_desktop_routes import (
    VirtualDesktopGateway as LibreOfficeDesktopGateway,
    install_route_hooks,
    is_installed,
)


__all__ = [
    "LibreOfficeDesktopGateway",
    "install_route_hooks",
    "is_installed",
]
