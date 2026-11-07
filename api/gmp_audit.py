"""GMP & Quality Audit Suite API — additive module (QA/Regulatory)."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("gmp_audit")


class GmpAuditHandler(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "")
        if action == "checklists":
            return {"success": True, "standards": {k: len(v) for k, v in __import__("modules.gmp_audit", fromlist=["CHECKLISTS"]).CHECKLISTS.items()}}
        elif action == "checklist":
            return self._checklist(input)
        elif action == "em_limits":
            from modules.gmp_audit import EM_LIMITS
            return {"success": True, "limits": EM_LIMITS, "note": "EU GMP Annex 1 (2022 rev) / ISO 14644 grades."}
        elif action == "water_limits":
            from modules.gmp_audit import WATER_LIMITS
            return {"success": True, "limits": WATER_LIMITS}
        elif action == "add_record":
            from modules.gmp_audit import add_record
            kind = str(input.get("kind", "deviation"))
            if kind not in ("deviation", "capa"):
                return {"error": "kind must be deviation or capa"}
            if not str(input.get("title", "")).strip():
                return {"error": "title required"}
            return add_record(kind, input)
        elif action == "update_record":
            from modules.gmp_audit import update_record
            rid = str(input.get("id", "")).strip()
            if not rid:
                return {"error": "id required"}
            status = input.get("status")
            if status and str(status) not in ("open", "in_progress", "closed"):
                return {"error": "status: open | in_progress | closed"}
            return update_record(rid, status, input.get("action"))
        elif action == "dashboard":
            from modules.gmp_audit import dashboard
            return {"success": True, **dashboard()}
        elif action == "inspection_plan":
            from modules.gmp_audit import self_inspection_plan
            return {"success": True, **self_inspection_plan(input.get("last_audit") or {},
                                                            int(input.get("interval_months", 12) or 12))}

        return {"actions": ["checklists", "checklist", "em_limits", "water_limits", "add_record",
                            "update_record", "dashboard", "inspection_plan"],
                "hint": "GMP Audit — WHO/EU/CFR/PIC-S checklists, EM & water limits, deviation-CAPA tracker, self-inspection planner."}

    @staticmethod
    def _checklist(input: dict) -> dict:
        from modules.gmp_audit import CHECKLISTS
        std = str(input.get("standard", ""))
        for name in CHECKLISTS:
            if std.lower() in name.lower():
                return {"success": True, "standard": name,
                        "items": [{"ref": i["ref"], "item": i["item"], "checked": False} for i in CHECKLISTS[name]]}
        return {"error": f"standard not found — options: {list(CHECKLISTS)}"}
