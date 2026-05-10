import time
import logging
from typing import Dict, Any, Optional
from nanobot.models.heartbeat_schema import Heartbeat
from nanobot.supervisor.task_profile_manager import TaskProfileManager

class HeartbeatMonitor:
    """
    Tracks structured heartbeats per task.
    Determines if a task has gone silent or stalled based on time.
    """
    def __init__(self, profile_manager: TaskProfileManager):
        self.profile_manager = profile_manager
        # Track last heartbeat: {task_id: Heartbeat}
        self.last_heartbeats: Dict[str, Heartbeat] = {}
        # Track time of last heartbeat: {task_id: float (unix)}
        self.heartbeat_times: Dict[str, float] = {}

    def receive_heartbeat(self, hb: Heartbeat):
        """Register a new heartbeat from a task."""
        self.last_heartbeats[hb.task_id] = hb
        self.heartbeat_times[hb.task_id] = time.time()
        logging.debug(f"Received heartbeat for {hb.task_id} (Progress: {hb.progress_percent}%)")

    def check_silence(self, task_id: str) -> bool:
        """
        Check if the task has been silent longer than its profile allows.
        """
        last_time = self.heartbeat_times.get(task_id)
        if last_time is None:
            return True # Never received a heartbeat
            
        hb = self.last_heartbeats[task_id]
        profile = self.profile_manager.get_profile(hb.task_type)
        
        silence_duration = time.time() - last_time
        return silence_duration > profile.silence_threshold_seconds

    def check_progress_stall(self, task_id: str) -> bool:
        """
        Check if progress has failed to increase for too long.
        Note: This is simpler than velocity analysis and focuses on absolute time.
        """
        hb = self.last_heartbeats.get(task_id)
        if not hb: return False
        
        profile = self.profile_manager.get_profile(hb.task_type)
        
        # In a real implementation, we might track 'last_progress_increase_time'
        # For this logic, we assume the monitor loop handles the state.
        return False # Placeholder for complex stall logic handled by Supervisor

    def get_last_heartbeat(self, task_id: str) -> Optional[Heartbeat]:
        return self.last_heartbeats.get(task_id)

    def clear_task(self, task_id: str):
        if task_id in self.last_heartbeats:
            del self.last_heartbeats[task_id]
        if task_id in self.heartbeat_times:
            del self.heartbeat_times[task_id]
