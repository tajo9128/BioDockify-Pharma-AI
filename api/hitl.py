"""Human-in-the-Loop Intervention — 8 modes, gate approval, collaboration."""
from helpers.api import ApiHandler, Request, Response
import os, json, logging
from datetime import datetime

log = logging.getLogger("hitl")
HITL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hitl")
os.makedirs(HITL_DIR, exist_ok=True)

MODES = {
    "full_auto":    {"pauses": 0,  "desc": "No human intervention — fully autonomous"},
    "gate_only":    {"pauses": 3,  "desc": "Pause at 3 quality gates only"},
    "checkpoint":   {"pauses": 9,  "desc": "Pause at each phase boundary (9 checkpoints)"},
    "co_pilot":     {"pauses": 5,  "desc": "Deep collaboration at hypothesis, method, results, writing"},
    "step_by_step": {"pauses": 25, "desc": "Pause after every stage"},
    "express":      {"pauses": 3,  "desc": "Quick review — only 3 most critical gates"},
    "regulatory":   {"pauses": 5,  "desc": "FDA/EMA compliance check at each gate + ICH E9 validation"},
    "custom":       {"pauses": 0,  "desc": "User-defined per-stage policies"},
}

INTERVENTIONS = ["approve", "reject", "edit", "collaborate", "inject_guidance", "view_output", "abort"]


def _load(pipeline_id):
    path = os.path.join(HITL_DIR, f"{pipeline_id}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _save(pipeline_id, data):
    path = os.path.join(HITL_DIR, f"{pipeline_id}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _init_hitl(pipeline_id, mode="co_pilot"):
    data = {
        "pipeline_id": pipeline_id,
        "mode": mode,
        "gates": {
            "5":  {"status": "pending", "interventions": [], "approved": False},
            "11": {"status": "pending", "interventions": [], "approved": False},
            "23": {"status": "pending", "interventions": [], "approved": False},
        },
        "history": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    _save(pipeline_id, data)
    return data


class HitlHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "init")

        if action == "init":
            pid = input.get("pipeline_id", "")
            mode = input.get("mode", "co_pilot")
            if not pid:
                return {"error": "pipeline_id required"}
            data = _init_hitl(pid, mode)
            return {"success": True, "hitl": data}

        if action == "status":
            pid = input.get("pipeline_id", "")
            data = _load(pid)
            if not data:
                return {"error": f"No HITL data for pipeline {pid}"}
            return {"success": True, "hitl": data}

        if action == "approve":
            pid = input.get("pipeline_id", "")
            gate_id = str(input.get("gate_id", ""))
            comment = input.get("comment", "")
            data = _load(pid)
            if not data:
                return {"error": f"No HITL data for pipeline {pid}"}
            if gate_id not in data["gates"]:
                return {"error": f"Invalid gate_id: {gate_id}"}
            data["gates"][gate_id]["approved"] = True
            data["gates"][gate_id]["status"] = "approved"
            data["gates"][gate_id]["interventions"].append({
                "action": "approve", "comment": comment, "ts": datetime.now().isoformat(),
            })
            data["history"].append(f"Gate {gate_id} approved: {comment}")
            data["updated_at"] = datetime.now().isoformat()
            _save(pid, data)
            return {"success": True, "approved": True}

        if action == "reject":
            pid = input.get("pipeline_id", "")
            gate_id = str(input.get("gate_id", ""))
            reason = input.get("reason", "")
            data = _load(pid)
            if not data:
                return {"error": f"No HITL data for pipeline {pid}"}
            data["gates"][gate_id]["status"] = "rejected"
            data["gates"][gate_id]["interventions"].append({
                "action": "reject", "reason": reason, "ts": datetime.now().isoformat(),
            })
            data["history"].append(f"Gate {gate_id} REJECTED: {reason}")
            data["updated_at"] = datetime.now().isoformat()
            _save(pid, data)
            return {"success": True, "rejected": True, "reason": reason}

        if action == "modes":
            return {"success": True, "modes": MODES, "interventions": INTERVENTIONS}

        if action == "collaborate":
            pid = input.get("pipeline_id", "")
            gate_id = str(input.get("gate_id", ""))
            user_input = input.get("input", "")
            data = _load(pid)
            if not data:
                return {"error": f"No HITL data for pipeline {pid}"}
            data["gates"][gate_id]["interventions"].append({
                "action": "collaborate", "input": user_input, "ts": datetime.now().isoformat(),
            })
            data["history"].append(f"Gate {gate_id} collaboration: {user_input[:100]}")
            data["updated_at"] = datetime.now().isoformat()
            _save(pid, data)
            return {"success": True, "collaboration_recorded": True}

        if action == "inject_guidance":
            pid = input.get("pipeline_id", "")
            stage = input.get("stage", "")
            guidance = input.get("guidance", "")
            data = _load(pid)
            if not data:
                data = _init_hitl(pid, "co_pilot")
            data["injected_guidance"] = data.get("injected_guidance", {})
            data["injected_guidance"][str(stage)] = guidance
            data["history"].append(f"Stage {stage} guidance injected: {guidance[:100]}")
            data["updated_at"] = datetime.now().isoformat()
            _save(pid, data)
            return {"success": True, "guidance_injected": True, "stage": stage}

        return {"error": f"Unknown action: {action}"}
