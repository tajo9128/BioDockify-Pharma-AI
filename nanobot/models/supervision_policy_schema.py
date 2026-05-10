from typing import List, Dict
from pydantic import BaseModel

class TaskProfile(BaseModel):
    """
    Sub-schema for task-specific supervision thresholds.
    """
    silence_threshold_seconds: int
    progress_stall_seconds: int
    escalation_steps_seconds: List[int]

class SupervisionPolicy(BaseModel):
    """
    Global supervision policy schema.
    Contains profiles for different task types.
    """
    profiles: Dict[str, TaskProfile]
