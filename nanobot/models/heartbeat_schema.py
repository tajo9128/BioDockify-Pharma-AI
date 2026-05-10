from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator

class Heartbeat(BaseModel):
    """
    Structured heartbeat sent by Agent Zero to NanoBot.
    Mandatory schema for execution supervision.
    """
    task_id: str
    task_type: str
    status: Literal["running", "blocked", "waiting_input", "completed", "error"]
    progress_percent: float = Field(..., ge=0, le=100)
    activity_state: str
    timestamp: datetime
    metadata: Optional[dict] = None

    @field_validator("timestamp")
    @classmethod
    def timestamp_not_in_future(cls, v: datetime) -> datetime:
        now = datetime.now(v.tzinfo or timezone.utc) 
        if v > now:
            # Allow for slight clock skew (5 seconds)
            if (v - now).total_seconds() > 5:
                raise ValueError("timestamp cannot be in the future")
        return v
