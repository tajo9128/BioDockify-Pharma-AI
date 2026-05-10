import logging
from typing import Dict, Any
from nanobot.supervisor.audit_logger import AuditLogger

class EscalationEngine:
    """
    Handles progressive escalation for supervised tasks.
    6 Levels: 0 (Healthy) to 5 (Restart Suggestion).
    """
    LEVELS = {
        0: "Healthy",
        1: "Soft Reminder",
        2: "Direct Prompt",
        3: "Diagnostic Request",
        4: "User Notification",
        5: "Restart Suggestion"
    }

    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger
        # Track current level per task: {task_id: int}
        self.task_levels: Dict[str, int] = {}

    def get_level(self, task_id: str) -> int:
        """Get current escalation level for a task."""
        return self.task_levels.get(task_id, 0)

    def escalate(self, task_id: str, detection_type: str) -> int:
        """
        Increment escalation level for a task.
        Returns the new level.
        """
        current = self.get_level(task_id)
        if current < 5:
            new_level = current + 1
            self.task_levels[task_id] = new_level
            
            action = f"Escalated to Level {new_level}: {self.LEVELS[new_level]}"
            self.audit_logger.log_action(task_id, detection_type, new_level, action)
            logging.info(f"Escalation for {task_id}: {action} (Trigger: {detection_type})")
            
            return new_level
        return 5

    def reset(self, task_id: str):
        """Reset escalation to level 0 (e.g., after activity detected)."""
        if task_id in self.task_levels and self.task_levels[task_id] > 0:
            self.audit_logger.log_action(task_id, "Activity Detected", 0, "Reset to Healthy")
            self.task_levels[task_id] = 0

    def clear_task(self, task_id: str):
        """Cleanup task tracking."""
        if task_id in self.task_levels:
            del self.task_levels[task_id]
