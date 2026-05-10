import asyncio
import time
import logging
from typing import Dict, Set, Optional
from nanobot.models.heartbeat_schema import Heartbeat
from nanobot.supervisor.heartbeat_monitor import HeartbeatMonitor
from nanobot.supervisor.escalation_engine import EscalationEngine
from nanobot.supervisor.velocity_analyzer import VelocityAnalyzer
from nanobot.supervisor.task_profile_manager import TaskProfileManager
from nanobot.supervisor.audit_logger import AuditLogger

class ExecutionSupervisor:
    """
    The main orchestrator for Agent Zero supervision.
    Integrates all sub-modules into a task-adaptive active watchdog.
    """
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        
        # Components
        self.audit_logger = AuditLogger()
        self.profile_manager = TaskProfileManager()
        self.escalator = EscalationEngine(self.audit_logger)
        self.velocity_analyzer = VelocityAnalyzer()
        self.monitor = HeartbeatMonitor(self.profile_manager)
        
        # Active State
        self.active_task_ids: Set[str] = set()
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the supervision loop."""
        if self._running: return
        self._running = True
        self._loop_task = asyncio.create_task(self._supervision_loop())
        logging.info("Execution Supervisor started.")

    def stop(self):
        """Stop the supervision loop."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
        logging.info("Execution Supervisor stopped.")

    async def register_heartbeat(self, hb: Heartbeat):
        """External entry point to feed heartbeats into the supervisor."""
        task_id = hb.task_id
        if task_id not in self.active_task_ids:
            self.active_task_ids.add(task_id)
            logging.info(f"Registered new task for supervision: {task_id}")

        # Update sub-modules
        self.monitor.receive_heartbeat(hb)
        self.velocity_analyzer.update_progress(task_id, time.time(), hb.progress_percent)
        
        # If we got a heartbeat, reset escalation if it was higher than 0
        self.escalator.reset(task_id)

    async def _supervision_loop(self):
        """Continuous background loop for active task evaluation."""
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_all_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in supervision loop: {e}")

    async def _check_all_tasks(self):
        """Evaluates each active task against detection rules."""
        finished_tasks = []
        
        for task_id in list(self.active_task_ids):
            hb = self.monitor.get_last_heartbeat(task_id)
            if not hb: continue
            
            # 1. Check for Task Completion or Error (Clean exit)
            if hb.status in ["completed", "error"]:
                logging.info(f"Task {task_id} reached terminal state '{hb.status}'. Removing from supervision.")
                finished_tasks.append(task_id)
                continue
                
            # 2. Apply Detection Rules
            detected_issue = None
            
            # Rule A: Missing Heartbeat (Silence)
            if self.monitor.check_silence(task_id):
                detected_issue = "SILENCE_DETECTED"
            
            # Rule B: Stagnant Progress (Velocity)
            elif self.velocity_analyzer.is_stagnant(task_id):
                detected_issue = "PROGRESS_STALLED"
                
            # Rule C: Explicitly Blocked
            elif hb.status == "blocked":
                detected_issue = "STATUS_BLOCKED"

            # 3. Trigger Escalation if an issue was detected
            if detected_issue:
                new_level = self.escalator.escalate(task_id, detected_issue)
                await self._dispatch_escalation_action(task_id, new_level, detected_issue)
                
        # Cleanup
        for task_id in finished_tasks:
            self._cleanup_task(task_id)

    async def _dispatch_escalation_action(self, task_id: str, level: int, issue: str):
        """Dispatch actions based on escalation level."""
        # Level 0-3: Handled by NanoBot (internal logs/reminders)
        # Level 4: Notify User
        if level == 4:
            logging.warning(f"CRITICAL: Dispatching user notification for task {task_id} due to {issue}")
            # In a real integration, this would call self.receptionist.notify_user(...)
            
        # Level 5: Suggest Restart
        if level == 5:
            logging.error(f"FATAL: Suggesting task restart for {task_id}")

    def _cleanup_task(self, task_id: str):
        """Cleanup sub-modules for a specific task."""
        if task_id in self.active_task_ids:
            self.active_task_ids.remove(task_id)
        self.monitor.clear_task(task_id)
        self.velocity_analyzer.clear_task(task_id)
        self.escalator.clear_task(task_id)
