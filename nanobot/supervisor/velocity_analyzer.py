import logging
from typing import Dict, Optional

class VelocityAnalyzer:
    """
    Computes velocity for active tasks: Δprogress / Δtime.
    Detects slowdowns based on task-specific baselines.
    """
    def __init__(self):
        # Store historical progress points per task: {task_id: [(timestamp, progress), ...]}
        self.history: Dict[str, list] = {}

    def update_progress(self, task_id: str, timestamp: float, progress: float):
        """Record a progress point."""
        if task_id not in self.history:
            self.history[task_id] = []
        
        self.history[task_id].append((timestamp, progress))
        
        # Keep only the last 10 points for a rolling window
        if len(self.history[task_id]) > 10:
            self.history[task_id].pop(0)

    def calculate_velocity(self, task_id: str) -> Optional[float]:
        """
        Calculate current velocity (progress percentage per second).
        Returns None if not enough data points.
        """
        points = self.history.get(task_id, [])
        if len(points) < 2:
            return None
        
        t1, p1 = points[0]
        tn, pn = points[-1]
        
        dt = tn - t1
        dp = pn - p1
        
        if dt <= 0:
            return 0.0
            
        return dp / dt

    def is_stagnant(self, task_id: str, baseline_velocity: float = 0.0) -> bool:
        """
        Check if the task's velocity is below the expected baseline.
        """
        v = self.calculate_velocity(task_id)
        if v is None:
            return False # Not enough data to judge yet
            
        return v <= baseline_velocity

    def clear_task(self, task_id: str):
        """Cleanup when a task is finished."""
        if task_id in self.history:
            del self.history[task_id]
