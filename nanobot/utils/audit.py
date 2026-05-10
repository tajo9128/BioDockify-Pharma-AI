"""Audit Logging for NanoBot Receptionist."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

class AuditLogger:
    """
    Handles logging of administrative actions, tool usage, and system changes.
    Ensures transparency and reproducibility.
    """
    
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
    def log_action(self, action: str, details: Dict[str, Any], status: str = "success") -> None:
        """Log an action to the audit file."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details,
            "status": status
        }
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to audit log: {e}")

    def log_tool_usage(self, tool_name: str, arguments: Dict[str, Any], result_summary: str) -> None:
        """Log tool usage for transparency."""
        self.log_action("tool_usage", {
            "tool": tool_name,
            "arguments": arguments,
            "result_summary": result_summary
        })
