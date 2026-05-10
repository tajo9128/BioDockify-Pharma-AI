
"""
Research Persistence Manager
Saves and loads research state for long-running thesis projects.
Enables resuming research after days, weeks, or months.
"""
import json
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ResearchState:
    """Complete state of a research project."""
    research_id: str
    topic: str
    research_type: str
    created_at: str
    last_updated: str
    current_stage: str
    progress: float
    tasks: List[Dict[str, Any]]
    completed_tasks: List[str]
    wet_lab_experiments: List[Dict[str, Any]]
    thesis_milestones: Dict[str, Any]
    communication_history: List[Dict[str, Any]]
    knowledge_base: List[Dict[str, Any]]
    user_submissions: List[Dict[str, Any]]


class ResearchPersistenceManager:
    """
    Manages persistent storage of research state.
    Saves/loads research projects to enable long-running thesis work.
    """

    def __init__(self, storage_path: str = None):
        if storage_path is None:
            # Use BIODOCKIFY_DATA_DIR environment variable or default to /tmp
            data_dir = os.environ.get('BIODOCKIFY_DATA_DIR', '/tmp')
            storage_path = os.path.join(data_dir, 'research_state')

        self.storage_path = Path(storage_path)
        
        # Try to create directory, fallback to /tmp if failed
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Research persistence initialized at: {self.storage_path}")
        except (PermissionError, OSError) as e:
            # Fallback to /tmp if original path not writable
            fallback_path = Path('/tmp') / 'research_state'
            self.storage_path = fallback_path
            self.storage_path.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Could not create storage at original path, using fallback: {self.storage_path}")

    def save_research_state(
        self,
        research_id: str,
        topic: str,
        research_type: str,
        current_stage: str,
        progress: float,
        tasks: List[Dict[str, Any]],
        wet_lab_experiments: List[Dict[str, Any]] = None,
        thesis_milestones: Dict[str, Any] = None,
        communication_history: List[Dict[str, Any]] = None,
        knowledge_base: List[Dict[str, Any]] = None,
        user_submissions: List[Dict[str, Any]] = None
    ) -> str:
        """
        Save research state to persistent storage.
        Returns path to saved file.
        """
        state = ResearchState(
            research_id=research_id,
            topic=topic,
            research_type=research_type,
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            current_stage=current_stage,
            progress=progress,
            tasks=tasks,
            completed_tasks=[t["id"] for t in tasks if t.get("status") == "completed"],
            wet_lab_experiments=wet_lab_experiments or [],
            thesis_milestones=thesis_milestones or {},
            communication_history=communication_history or [],
            knowledge_base=knowledge_base or [],
            user_submissions=user_submissions or []
        )

        # Save to file
        filepath = self.storage_path / f"{research_id}.json"
        with open(filepath, 'w') as f:
            json.dump(asdict(state), f, indent=2)

        logger.info(f"Research state saved: {filepath}")
        return str(filepath)

    def load_research_state(self, research_id: str) -> Optional[ResearchState]:
        """
        Load research state from persistent storage.
        Returns None if research not found.
        """
        filepath = self.storage_path / f"{research_id}.json"

        if not filepath.exists():
            logger.warning(f"Research state not found: {research_id}")
            return None

        with open(filepath, 'r') as f:
            data = json.load(f)

        state = ResearchState(**data)
        logger.info(f"Research state loaded: {research_id}")
        return state

    def list_all_research(self) -> List[Dict[str, Any]]:
        """List all saved research projects."""
        research_list = []

        for filepath in self.storage_path.glob("*.json"):
            with open(filepath, 'r') as f:
                data = json.load(f)

            research_list.append({
                "research_id": data["research_id"],
                "topic": data["topic"],
                "research_type": data["research_type"],
                "created_at": data["created_at"],
                "last_updated": data["last_updated"],
                "current_stage": data["current_stage"],
                "progress": data["progress"],
                "total_tasks": len(data["tasks"]),
                "completed_tasks": len(data["completed_tasks"])
            })

        # Sort by last_updated
        research_list.sort(key=lambda r: r["last_updated"], reverse=True)
        return research_list

    def update_task_status(
        self,
        research_id: str,
        task_id: str,
        status: str,
        result: str = None
    ) -> bool:
        """Update task status in research state."""
        state = self.load_research_state(research_id)
        if not state:
            return False

        # Update task
        for task in state.tasks:
            if task["id"] == task_id:
                task["status"] = status
                if result:
                    task["result"] = result
                task["last_updated"] = datetime.now().isoformat()
                break

        # Update progress
        completed = sum(1 for t in state.tasks if t.get("status") == "completed")
        state.progress = completed / len(state.tasks) if state.tasks else 0.0
        state.last_updated = datetime.now().isoformat()

        # Save updated state
        filepath = self.storage_path / f"{research_id}.json"
        with open(filepath, 'w') as f:
            json.dump(asdict(state), f, indent=2)

        return True

    def add_wet_lab_experiment(
        self,
        research_id: str,
        experiment_type: str,
        description: str,
        protocol: str,
        required_materials: List[str],
        expected_duration: str,
        assigned_to: str
    ) -> bool:
        """Add wet lab experiment to research plan."""
        state = self.load_research_state(research_id)
        if not state:
            return False

        experiment = {
            "id": f"wetlab_{len(state.wet_lab_experiments) + 1}",
            "type": experiment_type,
            "description": description,
            "protocol": protocol,
            "required_materials": required_materials,
            "expected_duration": expected_duration,
            "assigned_to": assigned_to,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "submission": None
        }

        state.wet_lab_experiments.append(experiment)
        state.last_updated = datetime.now().isoformat()

        # Save
        filepath = self.storage_path / f"{research_id}.json"
        with open(filepath, 'w') as f:
            json.dump(asdict(state), f, indent=2)

        return True

    def submit_wet_lab_result(
        self,
        research_id: str,
        experiment_id: str,
        submission_data: Dict[str, Any]
    ) -> bool:
        """Submit wet lab experiment result."""
        state = self.load_research_state(research_id)
        if not state:
            return False

        # Find and update experiment
        for exp in state.wet_lab_experiments:
            if exp["id"] == experiment_id:
                exp["submission"] = {
                    "submitted_at": datetime.now().isoformat(),
                    "data": submission_data
                }
                exp["status"] = "completed"
                break

        state.last_updated = datetime.now().isoformat()

        # Save
        filepath = self.storage_path / f"{research_id}.json"
        with open(filepath, 'w') as f:
            json.dump(asdict(state), f, indent=2)

        return True

    def add_thesis_milestone(
        self,
        research_id: str,
        milestone_name: str,
        description: str,
        due_date: str,
        tasks: List[str]
    ) -> bool:
        """Add thesis milestone to research plan."""
        state = self.load_research_state(research_id)
        if not state:
            return False

        milestone = {
            "id": f"milestone_{len(state.thesis_milestones) + 1}",
            "name": milestone_name,
            "description": description,
            "due_date": due_date,
            "tasks": tasks,
            "status": "not_started",
            "created_at": datetime.now().isoformat()
        }

        state.thesis_milestones[milestone["id"]] = milestone
        state.last_updated = datetime.now().isoformat()

        # Save
        filepath = self.storage_path / f"{research_id}.json"
        with open(filepath, 'w') as f:
            json.dump(asdict(state), f, indent=2)

        return True

    def update_milestone_status(
        self,
        research_id: str,
        milestone_id: str,
        status: str
    ) -> bool:
        """Update thesis milestone status."""
        state = self.load_research_state(research_id)
        if not state:
            return False

        if milestone_id in state.thesis_milestones:
            state.thesis_milestones[milestone_id]["status"] = status
            state.thesis_milestones[milestone_id]["updated_at"] = datetime.now().isoformat()

        state.last_updated = datetime.now().isoformat()

        # Save
        filepath = self.storage_path / f"{research_id}.json"
        with open(filepath, 'w') as f:
            json.dump(asdict(state), f, indent=2)

        return True

    def get_resume_summary(self, research_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary for resuming research after absence.
        Shows what was done, what's needed, where to continue.
        """
        state = self.load_research_state(research_id)
        if not state:
            return None

        # Calculate time since last update
        last_update = datetime.fromisoformat(state.last_updated)
        days_away = (datetime.now() - last_update).days

        # Find pending tasks
        pending_tasks = [t for t in state.tasks if t.get("status") == "pending"]
        in_progress_tasks = [t for t in state.tasks if t.get("status") == "in_progress"]

        # Find pending wet lab experiments
        pending_wetlab = [e for e in state.wet_lab_experiments if e.get("status") == "pending"]
        completed_wetlab = [e for e in state.wet_lab_experiments if e.get("status") == "completed"]

        # Find thesis milestones in progress
        in_progress_milestones = [
            m for m in state.thesis_milestones.values()
            if m.get("status") == "in_progress"
        ]

        summary = {
            "research_id": research_id,
            "topic": state.topic,
            "research_type": state.research_type,
            "time_away_days": days_away,
            "last_update": state.last_updated,
            "current_stage": state.current_stage,
            "overall_progress": f"{state.progress * 100:.1f}%",
            "work_completed": {
                "tasks_completed": len(state.completed_tasks),
                "tasks_total": len(state.tasks),
                "wetlab_completed": len(completed_wetlab),
                "wetlab_total": len(state.wet_lab_experiments)
            },
            "what_was_done": f"Completed {len(state.completed_tasks)} tasks including {self._get_stage_summary(state)}",
            "what_needed_now": self._get_next_steps(state, pending_tasks, in_progress_tasks),
            "continue_from": self._get_resume_point(state, in_progress_tasks, pending_tasks),
            "pending_wet_lab_experiments": [
                {
                    "id": e["id"],
                    "type": e["type"],
                    "description": e["description"],
                    "assigned_to": e["assigned_to"]
                }
                for e in pending_wetlab
            ],
            "thesis_milestones_in_progress": [
                {
                    "id": m["id"],
                    "name": m["name"],
                    "description": m["description"],
                    "due_date": m["due_date"]
                }
                for m in in_progress_milestones
            ],
            "suggested_next_actions": self._get_suggested_actions(state)
        }

        return summary

    def _get_stage_summary(self, state: ResearchState) -> str:
        """Get summary of completed work by stage."""
        stage_tasks = {}
        for task in state.tasks:
            if task.get("status") == "completed":
                stage = task.get("stage", "unknown")
                stage_tasks[stage] = stage_tasks.get(stage, 0) + 1

        summary = ", ".join([f"{s}: {c} tasks" for s, c in stage_tasks.items()])
        return summary

    def _get_next_steps(
        self,
        state: ResearchState,
        pending_tasks: List[Dict],
        in_progress_tasks: List[Dict]
    ) -> str:
        """Get description of next steps."""
        if in_progress_tasks:
            return f"Continue with {len(in_progress_tasks)} in-progress tasks"
        elif pending_tasks:
            return f"Start next of {len(pending_tasks)} pending tasks"
        else:
            return "All tasks completed"

    def _get_resume_point(
        self,
        state: ResearchState,
        in_progress_tasks: List[Dict],
        pending_tasks: List[Dict]
    ) -> str:
        """Get point to resume from."""
        if in_progress_tasks:
            return f"Continue: {in_progress_tasks[0]['title']}"
        elif pending_tasks:
            return f"Start: {pending_tasks[0]['title']}"
        else:
            return "Research completed"

    def _get_suggested_actions(self, state: ResearchState) -> List[str]:
        """Get suggested next actions."""
        actions = []

        # Check for pending wet lab experiments
        pending_wetlab = [e for e in state.wet_lab_experiments if e.get("status") == "pending"]
        if pending_wetlab:
            actions.append(f"Complete {len(pending_wetlab)} pending wet lab experiments")

        # Check for upcoming thesis milestones
        today = datetime.now()
        for mid, milestone in state.thesis_milestones.items():
            if milestone.get("status") == "not_started":
                due_date = datetime.fromisoformat(milestone["due_date"])
                days_until = (due_date - today).days
                if 0 <= days_until <= 30:
                    actions.append(f"Start milestone: {milestone['name']} (due in {days_until} days)")

        # Check progress
        if state.progress < 0.25:
            actions.append("Focus on initial research planning")
        elif state.progress < 0.5:
            actions.append("Continue deep research and literature review")
        elif state.progress < 0.75:
            actions.append("Proceed with analysis and synthesis")
        else:
            actions.append("Finalize research and prepare thesis")

        return actions
