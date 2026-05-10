import json
import logging
from datetime import datetime, timezone
from pathlib import Path

class AuditLogger:
    """
    Provides immutable, append-only JSONL logging for supervisor actions.
    """
    def __init__(self, log_path: str = "audit_log.jsonl"):
        self.log_path = Path(log_path)
        # Ensure directory exists but file is append-only
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_action(self, task_id: str, detection_type: str, escalation_level: int, action_taken: str):
        """Append a structured entry to the audit log."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "detection_type": detection_type,
            "escalation_level": escalation_level,
            "action_taken": action_taken
        }
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            # Fallback to system logging if file write fails
            logging.error(f"Failed to write to audit log: {e}")
            logging.info(f"AUDIT_FALLBACK: {entry}")
