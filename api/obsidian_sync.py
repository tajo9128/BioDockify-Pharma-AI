"""
BioDockify ↔ Obsidian Sync API

Provides 4 actions:
  - status   : get vault info (exists, file count, categories, last modified)
  - export   : send selected/all KB entries to Obsidian vault
  - import   : pull .md files from Obsidian vault into KB
  - configure: set vault path (default or custom)

Auth required (faculty-only). No Agent Zero changes.
"""

import asyncio
import logging
from helpers.api import ApiHandler, Request, Response

log = logging.getLogger("api.obsidian_sync")


class ObsidianSyncHandler(ApiHandler):

    @classmethod
    def requires_auth(cls) -> bool:
        return True

    async def process(self, input, request: Request) -> Response:
        action = (input or {}).get("action", "status")

        if action == "status":
            return await self._status(input)
        if action == "export":
            return await self._export(input)
        if action == "import":
            return await self._import(input)
        if action == "configure":
            return await self._configure(input)

        return {
            "status": "error",
            "error": f"Unknown action '{action}'. Valid: status, export, import, configure.",
        }

    async def _status(self, input) -> Response:
        from modules.obsidian.sync import get_vault_status
        vault_path = (input or {}).get("vault_path")
        result = await asyncio.to_thread(get_vault_status, vault_path)
        return {"status": "ok", **result}

    async def _export(self, input) -> Response:
        """Export KB entries to Obsidian vault.

        Accepts:
          entry_ids: list of KB entry IDs to export (optional — exports all if empty)
          vault_path: custom vault path (optional)
          category: export only this category (optional)
        """
        import os
        import json
        from modules.obsidian.sync import export_to_vault, DEFAULT_VAULT_PATH

        entry_ids = (input or {}).get("entry_ids", [])
        vault_path = (input or {}).get("vault_path") or DEFAULT_VAULT_PATH
        category_filter = (input or {}).get("category")

        # Load KB index to get entry metadata
        index_path = "/a0/data/knowledge_base/index.json"
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
        except FileNotFoundError:
            return {"status": "error", "error": "Knowledge Base index not found. No entries to export."}
        except Exception as e:
            return {"status": "error", "error": f"Failed to load KB index: {e}"}

        entries = index.get("entries", [])

        # Filter entries
        if entry_ids:
            entries = [e for e in entries if e.get("id") in entry_ids]
        if category_filter:
            entries = [e for e in entries if e.get("category") == category_filter]

        if not entries:
            return {"status": "ok", "exported": 0, "skipped": 0, "errors": [],
                    "message": "No entries to export."}

        # Export (blocking — run in thread)
        result = await asyncio.to_thread(export_to_vault, entries, vault_path)
        result["status"] = "ok"
        result["vault_path"] = vault_path
        result["message"] = (
            f"Exported {result['exported']} entries to Obsidian vault. "
            f"{result['skipped']} skipped."
        )
        return result

    async def _import(self, input) -> Response:
        """Import .md files from Obsidian vault into BioDockify KB.

        Accepts:
          vault_path: custom vault path (optional)
        """
        from modules.obsidian.sync import import_from_vault, DEFAULT_VAULT_PATH

        vault_path = (input or {}).get("vault_path") or DEFAULT_VAULT_PATH

        result = await asyncio.to_thread(import_from_vault, vault_path)
        result["status"] = "ok"
        result["vault_path"] = vault_path
        result["message"] = (
            f"Imported {result['imported']} new, {result['updated']} updated. "
            f"{result['skipped']} skipped."
        )
        return result

    async def _configure(self, input) -> Response:
        """Set the Obsidian vault path.

        Accepts:
          vault_path: new vault path
        """
        from modules.obsidian.sync import get_vault_status, DEFAULT_VAULT_PATH

        vault_path = (input or {}).get("vault_path")
        if not vault_path:
            return {
                "status": "ok",
                "vault_path": DEFAULT_VAULT_PATH,
                "message": f"Default vault path: {DEFAULT_VAULT_PATH}",
            }

        # Validate path exists or can be created
        import os
        try:
            os.makedirs(vault_path, exist_ok=True)
        except Exception as e:
            return {"status": "error", "error": f"Cannot create vault directory: {e}"}

        status = get_vault_status(vault_path)
        return {
            "status": "ok",
            "vault_path": vault_path,
            "vault_status": status,
            "message": f"Vault path set to: {vault_path}",
        }
