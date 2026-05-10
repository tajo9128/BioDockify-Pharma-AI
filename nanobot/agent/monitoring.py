"""
Progress Monitoring Service - BioDockify NanoBot
Background task to track Agent Zero's progress and broadcast updates.
"""
import asyncio
import logging
from typing import Dict, Any, Set
from runtime.task_store import get_task_store
from nanobot.utils.broadcaster import StatusBroadcaster
from nanobot.utils.reproducibility import ReproducibilityEngine
from pathlib import Path

logger = logging.getLogger("nanobot.monitoring")

class ProgressMonitor:
    """
    Background service that monitors TaskStore.
    Calculates progress and triggers broadcasts for significant events.
    """
    
    def __init__(self, broadcaster: StatusBroadcaster, project_root: str = "./data/workspace", interval: int = 10):
        self.broadcaster = broadcaster
        self.interval = interval
        self.repro_engine = ReproducibilityEngine(Path(project_root))
        self.known_tasks: Set[str] = set()
        self.task_states: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        """Start the background monitoring task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Progress Monitor started.")

    def stop(self):
        """Stop the background monitoring task."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Progress Monitor stopped.")

    async def _monitor_loop(self):
        """Periodically check TaskStore for updates."""
        store = get_task_store()
        while self._running:
            try:
                tasks = await store.list_tasks(limit=10)
                for task in tasks:
                    task_id = task["task_id"]
                    
                    # 1. Detect New Tasks
                    if task_id not in self.known_tasks:
                        self.known_tasks.add(task_id)
                        self.task_states[task_id] = task
                        await self.broadcaster.broadcast_status(
                            f"New research task started: {task.get('title', 'Untitled')}",
                            title="🚀 Task Initiated"
                        )
                        # Automatic SRSE Snapshot on Task Start
                        await self.repro_engine.create_snapshot(
                            label=f"Pre-Execution: {task.get('title')}",
                            workflow_state={"task_id": task_id, "phase": "initialization", "progress": 0}
                        )
                    
                    # 2. Detect Stage/Progress Changes
                    old_state = self.task_states.get(task_id, {})
                    old_progress = old_state.get("progress", 0)
                    new_progress = task.get("progress", 0)
                    
                    if new_progress > old_progress:
                        logger.info(f"Task {task_id} progress update: {new_progress}%")
                        # Only broadcast significant milestones (e.g., every 25% or completion)
                        if new_progress == 100:
                            await self.broadcaster.notify_completion(
                                task_id, 
                                task.get("title", ""), 
                                "Research pipeline executed all steps."
                            )
                            # Automatic SRSE Snapshot on Completion
                            await self.repro_engine.create_snapshot(
                                label=f"Post-Execution: {task.get('title')}",
                                workflow_state={"task_id": task_id, "phase": "completion", "progress": 100},
                                outputs=task.get("result", {})
                            )
                        elif (new_progress // 25) > (old_progress // 25):
                            await self.broadcaster.broadcast_status(
                                f"Task '{task.get('title')}' is {new_progress}% complete.",
                                title="🕒 Progress Update"
                            )
                            # Automatic SRSE Milestone Snapshot
                            await self.repro_engine.create_snapshot(
                                label=f"Milestone ({new_progress}%): {task.get('title')}",
                                workflow_state={"task_id": task_id, "phase": "execution", "progress": new_progress}
                            )

                    # 3. Detect Status Transitions (e.g., failed)
                    old_status = old_state.get("status")
                    new_status = task.get("status")
                    if new_status != old_status and new_status == "failed":
                         await self.broadcaster.broadcast_status(
                             f"Task '{task.get('title')}' encountered an error and failed.",
                             title="❌ Task Failed"
                         )

                    # Update local state
                    self.task_states[task_id] = task

            except Exception as e:
                logger.error(f"Error in Progress Monitor loop: {e}")
            
            await asyncio.sleep(self.interval)
