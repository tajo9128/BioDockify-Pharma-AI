import json
import logging
from pathlib import Path
from typing import Dict, Optional
from nanobot.models.supervision_policy_schema import SupervisionPolicy, TaskProfile

class TaskProfileManager:
    """
    Manages supervision policies for different task types.
    Loads profiles dynamically from JSON.
    """
    def __init__(self, policy_path: str = "nanobot/config/supervision_policy.json"):
        self.policy_path = Path(policy_path)
        self.policy: Optional[SupervisionPolicy] = None
        self.load_policy()

    def load_policy(self):
        """Load and validate the supervision policy."""
        try:
            if not self.policy_path.exists():
                logging.warning(f"Policy file {self.policy_path} not found. Creating default policy.")
                self._create_default_policy()
            
            with open(self.policy_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Schema expects a dict of profiles
                self.policy = SupervisionPolicy(profiles=data)
                logging.info(f"Loaded {len(self.policy.profiles)} supervision profiles.")
        except Exception as e:
            logging.error(f"Failed to load supervision policy: {e}")
            # Ensure we have at least a default profile in memory
            self._create_fallback_profile()

    def get_profile(self, task_type: str) -> TaskProfile:
        """Get the specific profile for a task type, or the default."""
        if not self.policy:
            self.load_policy()
        
        return self.policy.profiles.get(task_type, self.policy.profiles.get("default"))

    def _create_fallback_profile(self):
        """In-memory default if loading fails completely."""
        default = TaskProfile(
            silence_threshold_seconds=300,
            progress_stall_seconds=600,
            escalation_steps_seconds=[300, 600, 900]
        )
        self.policy = SupervisionPolicy(profiles={"default": default})

    def _create_default_policy(self):
        """Create a default JSON file if missing."""
        default_data = {
            "default": {
                "silence_threshold_seconds": 300,
                "progress_stall_seconds": 600,
                "escalation_steps_seconds": [300, 600, 900]
            }
        }
        self.policy_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.policy_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=2)
