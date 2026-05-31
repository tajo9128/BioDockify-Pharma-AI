"""DEPRECATED — GNINA CNN scoring removed in v6.8.5.
Use MM-GBSA (api/docking_mmgbsa.py) for CPU-only free energy scoring.
This file is kept as a stub for backward compatibility."""
from helpers.api import ApiHandler, Request, Response

class DockingGnina(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        return {"success": False, "error": "GNINA removed. Use MM-GBSA scoring via docking_run.", "deprecated": True}
