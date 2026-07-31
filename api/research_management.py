"""Research Management Flask API — persistence for Research Hub projects.

Replaces unmounted FastAPI routes/research_management.py for the desktop UI,
which calls this via callJsonApi("research_management", {action: ...}).
"""
from helpers.api import ApiHandler, Request
from helpers import files
import logging
import uuid
from datetime import datetime

log = logging.getLogger("research_management")

DEFAULT_TASKS = [
    {"id": "lit_review", "title": "Literature review & full-text collection", "status": "pending", "priority": 3},
    {"id": "gap_analysis", "title": "Identify research gaps", "status": "pending", "priority": 2},
    {"id": "methods", "title": "Design methodology", "status": "pending", "priority": 2},
    {"id": "wetlab", "title": "Wet-lab / experimental work", "status": "pending", "priority": 2},
    {"id": "analysis", "title": "Data analysis & results", "status": "pending", "priority": 2},
    {"id": "writing", "title": "Thesis / manuscript writing", "status": "pending", "priority": 1},
    {"id": "review", "title": "Internal review & revisions", "status": "pending", "priority": 1},
]


def _storage_path() -> str:
    """Prefer durable data dir under the agent root."""
    for candidate in (
        files.get_abs_path("data", "research_state"),
        files.get_abs_path("usr", "data", "research_state"),
        "/a0/data/research_state",
        "/tmp/research_state",
    ):
        try:
            import os
            os.makedirs(candidate, exist_ok=True)
            return candidate
        except OSError:
            continue
    return "/tmp/research_state"


def _manager():
    from modules.research_persistence import ResearchPersistenceManager
    return ResearchPersistenceManager(storage_path=_storage_path())


class ResearchManagement(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = (input.get("action") or "list").strip().lower()

        if action == "list":
            return self._list()
        if action == "dashboard":
            return self._dashboard(input)
        if action in ("create", "save", "start"):
            return self._create(input)
        if action == "load":
            return self._load(input)
        if action == "health":
            return {"status": "ok", "service": "research_management"}

        return {
            "status": "error",
            "error": f"Unknown action: {action}",
            "actions": ["list", "dashboard", "create", "save", "load", "health"],
        }

    def _list(self) -> dict:
        try:
            projects = _manager().list_all_research()
            return {"status": "ok", "projects": projects}
        except Exception as e:
            log.exception("list research failed")
            return {"status": "error", "error": str(e), "projects": []}

    def _load(self, input: dict) -> dict:
        research_id = input.get("research_id") or input.get("id", "")
        if not research_id:
            return {"status": "error", "error": "research_id required"}
        state = _manager().load_research_state(research_id)
        if not state:
            return {"status": "error", "error": "Research not found"}
        return {
            "status": "ok",
            "research_id": state.research_id,
            "topic": state.topic,
            "research_type": state.research_type,
            "current_stage": state.current_stage,
            "progress": state.progress,
            "tasks": state.tasks,
            "created_at": state.created_at,
            "last_updated": state.last_updated,
        }

    def _create(self, input: dict) -> dict:
        topic = (input.get("topic") or "").strip()
        if not topic:
            return {"status": "error", "error": "Topic required"}

        research_id = (input.get("research_id") or "").strip() or f"r_{uuid.uuid4().hex[:10]}"
        research_type = (input.get("research_type") or input.get("type") or "phd").strip()
        department = (input.get("department") or "").strip()
        notes = (input.get("notes") or input.get("comments") or "").strip()

        tasks = input.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            tasks = [dict(t) for t in DEFAULT_TASKS]
            if department:
                tasks[0]["title"] = f"Literature review ({department.replace('_', ' ')})"
            if notes:
                tasks.insert(0, {
                    "id": "brief",
                    "title": f"Brief: {notes[:120]}",
                    "status": "pending",
                    "priority": 3,
                })

        try:
            mgr = _manager()
            filepath = mgr.save_research_state(
                research_id=research_id,
                topic=topic,
                research_type=research_type,
                current_stage=input.get("current_stage") or "literature",
                progress=float(input.get("progress") or 0.05),
                tasks=tasks,
            )
            return {
                "status": "ok",
                "success": True,
                "research_id": research_id,
                "topic": topic,
                "filepath": filepath,
                "message": "Research project saved",
            }
        except Exception as e:
            log.exception("create research failed")
            return {"status": "error", "error": str(e)}

    def _dashboard(self, input: dict) -> dict:
        research_id = input.get("research_id") or input.get("id", "")
        if not research_id:
            return {"status": "error", "error": "research_id required"}

        mgr = _manager()
        state = mgr.load_research_state(research_id)
        if not state:
            return {"status": "error", "error": "Research not found"}

        milestones = []
        wetlab_summary = {"total": 0, "completed": 0, "running": 0, "pending": 0}
        try:
            from modules.thesis_tracker import ThesisMilestoneTracker
            tracker = ThesisMilestoneTracker(research_id)
            raw_ms = getattr(tracker.thesis, "milestones", None) if tracker.thesis else None
            if isinstance(raw_ms, dict):
                for mid, m in raw_ms.items():
                    status = getattr(m, "status", "pending")
                    if hasattr(status, "value"):
                        status = status.value
                    milestones.append({
                        "milestone_id": getattr(m, "milestone_id", mid),
                        "title": getattr(m, "title", str(mid)),
                        "status": status,
                        "progress": getattr(m, "progress", 0) or 0,
                    })
            elif isinstance(raw_ms, list):
                for m in raw_ms:
                    status = getattr(m, "status", "pending")
                    if hasattr(status, "value"):
                        status = status.value
                    milestones.append({
                        "milestone_id": getattr(m, "milestone_id", getattr(m, "id", "")),
                        "title": getattr(m, "title", str(m)),
                        "status": status,
                        "progress": getattr(m, "progress", 0) or 0,
                    })
        except Exception as e:
            log.debug(f"thesis milestones unavailable: {e}")

        try:
            from modules.wetlab_coordinator import WetLabCoordinator
            summary = WetLabCoordinator(research_id).get_experiment_summary()
            if isinstance(summary, dict):
                counts = summary.get("status_counts") or {}
                wetlab_summary = {
                    "total": summary.get("total_experiments", 0),
                    "completed": counts.get("completed", 0),
                    "running": summary.get("in_progress", counts.get("in_progress", 0)),
                    "pending": summary.get("pending_assignments", counts.get("pending", 0)),
                }
        except Exception as e:
            log.debug(f"wetlab summary unavailable: {e}")

        resume = None
        try:
            resume = mgr.get_resume_summary(research_id)
        except Exception:
            pass

        # Shape matches research-dashboard.html (tasks / milestones / wetlab_summary)
        return {
            "status": "ok",
            "research_id": research_id,
            "timestamp": datetime.now().isoformat(),
            "topic": state.topic,
            "research_type": state.research_type,
            "current_stage": state.current_stage,
            "progress": state.progress,
            "tasks": state.tasks or [],
            "milestones": milestones,
            "wetlab_summary": wetlab_summary,
            "resume_summary": resume,
            "research": {
                "topic": state.topic,
                "research_type": state.research_type,
                "current_stage": state.current_stage,
                "progress": state.progress,
                "last_updated": state.last_updated,
            },
        }
