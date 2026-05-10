"""
Multi-Task Scheduler - Manages parallel execution of multiple tasks
Features:
- Parallel task execution
- Task queuing and prioritization
- Resource management
- Progress tracking
- Conflict detection
"""

import uuid
import asyncio
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status"""

    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutableTask:
    """Task ready for execution"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.QUEUED
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_seconds: int = 0
    progress: float = 0.0
    device_session_id: Optional[str] = None


class MultiTaskScheduler:
    """
    Multi-Task Scheduler

    Features:
    - Execute multiple tasks in parallel
    - Manage task dependencies
    - Prioritize and queue tasks
    - Track progress
    - Handle task conflicts
    - Resource allocation
    """

    def __init__(
        self,
        max_parallel_tasks=5,
        task_manager=None,
        persistence_path: str = "./data/scheduler_state.json",
    ):
        self.max_parallel_tasks = max_parallel_tasks
        self.task_manager = task_manager
        self.persistence_path = Path(persistence_path)
        self.task_queue: List[ExecutableTask] = []
        self.running_tasks: Dict[str, ExecutableTask] = {}
        self.paused_tasks: Dict[str, ExecutableTask] = {}
        self.completed_tasks: List[ExecutableTask] = []
        self.executor = ThreadPoolExecutor(max_workers=max_parallel_tasks)

        # Ensure directory exists
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)

        self._setup_logging()

    def _setup_logging(self):
        logger.info("Multi-Task Scheduler initialized")

    async def add_task(
        self,
        task_id: str,
        title: str,
        description: str,
        priority: int = 0,
        dependencies: Optional[List[str]] = None,
        estimated_seconds: int = 3600,
        device_session_id: Optional[str] = None,
    ) -> ExecutableTask:
        """Add a task to the scheduler"""
        task = ExecutableTask(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            status=TaskStatus.QUEUED,
            estimated_seconds=estimated_seconds,
            device_session_id=device_session_id,
        )

        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority)

        await self.save_state()
        logger.info(f"Added task to queue: {task_id} - {title} (priority: {priority})")
        return task

    async def update_task_progress(self, task_id: str, progress: float) -> bool:
        """Update progress for a running task"""
        if task_id in self.running_tasks:
            self.running_tasks[task_id].progress = progress
            await self.save_state()
            return True
        return False

    async def save_state(self):
        """Save current scheduler state to disk"""
        try:
            state = {
                "queued": [asdict(t) for t in self.task_queue],
                "running": [asdict(t) for t in self.running_tasks.values()],
                "paused": [asdict(t) for t in self.paused_tasks.values()],
                "completed": [asdict(t) for t in self.completed_tasks],
            }

            # Serialize datetimes
            def serializer(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj

            with open(self.persistence_path, "w") as f:
                json.dump(state, f, indent=2, default=serializer)
        except Exception as e:
            logger.error(f"Failed to save scheduler state: {e}")

    async def load_state(self):
        """Load scheduler state from disk"""
        if not self.persistence_path.exists():
            return

        try:
            with open(self.persistence_path, "r") as f:
                state = json.load(f)

            def dict_to_task(d):
                # Handle datetime parsing - ensure timezone-aware datetimes
                if d.get("started_at"):
                    dt = datetime.fromisoformat(d["started_at"])
                    # Make naive datetime timezone-aware (assume UTC)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    d["started_at"] = dt
                if d.get("completed_at"):
                    dt = datetime.fromisoformat(d["completed_at"])
                    # Make naive datetime timezone-aware (assume UTC)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    d["completed_at"] = dt
                return ExecutableTask(**d)

            self.task_queue = [dict_to_task(t) for t in state.get("queued", [])]
            self.running_tasks = {
                t["id"]: dict_to_task(t) for t in state.get("running", [])
            }
            self.paused_tasks = {
                t["id"]: dict_to_task(t) for t in state.get("paused", [])
            }
            self.completed_tasks = [dict_to_task(t) for t in state.get("completed", [])]

            # Re-queue running tasks if they weren't finished
            for tid, task in list(self.running_tasks.items()):
                task.status = TaskStatus.QUEUED
                self.task_queue.append(task)
                del self.running_tasks[tid]

            logger.info("Scheduler state loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load scheduler state: {e}")

    async def start_next_tasks(self):
        """Start next available tasks"""
        if len(self.running_tasks) >= self.max_parallel_tasks:
            logger.info(f"Maximum parallel tasks reached ({self.max_parallel_tasks})")
            return

        available_tasks = []
        for task in self.task_queue:
            if task.status == TaskStatus.QUEUED:
                deps_satisfied = await self._check_dependencies(task.dependencies)
                if deps_satisfied:
                    available_tasks.append(task)

        available_tasks.sort(key=lambda t: t.priority)

        for task in available_tasks[
            : self.max_parallel_tasks - len(self.running_tasks)
        ]:
            await self._start_task(task)

    async def _check_dependencies(self, dependencies: List[str]) -> bool:
        """Check if all dependencies are satisfied"""
        completed_ids = {t.id for t in self.completed_tasks}
        for dep_id in dependencies:
            if dep_id not in completed_ids:
                return False
        return True

    async def _start_task(self, task: ExecutableTask):
        """Start a task for execution"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        self.running_tasks[task.id] = task

        # Remove from queue
        self.task_queue = [t for t in self.task_queue if t.id != task.id]

        logger.info(f"Starting task: {task.id} - {task.title}")
        asyncio.create_task(self._execute_task(task))

    async def _execute_task(self, task: ExecutableTask):
        """Execute a task with error handling"""
        try:
            result = await self._execute_task_logic(task)
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.result = result
            task.progress = 100.0
            self.completed_tasks.append(task)
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.completed_tasks.append(task)
            logger.error(f"Task failed: {task.id} - {str(e)}")
        finally:
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]
            await self.start_next_tasks()

    async def _execute_task_logic(self, task: ExecutableTask) -> Dict[str, Any]:
        """Execute the actual task logic"""
        if self.task_manager:
            # Integration with existing TaskManager
            # Since create_task returns a Task object, we store its ID
            tm_task_id = await self.task_manager.create_task(
                title=task.title, description=task.description, priority=task.priority
            )

            # Wait for completion (poll for now as simple impl)
            while True:
                status = await self.task_manager.get_task_status(tm_task_id)
                if not status:
                    break

                tm_status = status["task"].get("status")
                if tm_status == "completed":
                    return status["task"].get("result", {})
                elif tm_status == "failed":
                    raise Exception(
                        status["task"].get("error_message", "Unknown error")
                    )

                await asyncio.sleep(5)

        # Mock successful execution if no task manager
        await asyncio.sleep(2)
        return {"success": True, "message": f"Task {task.id} executed successfully"}

    async def pause_task(self, task_id: str):
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.status = TaskStatus.PAUSED
            self.paused_tasks[task_id] = task
            del self.running_tasks[task_id]
            return True
        return False

    async def resume_task(self, task_id: str):
        if task_id in self.paused_tasks:
            task = self.paused_tasks[task_id]
            task.status = TaskStatus.QUEUED
            self.task_queue.append(task)
            del self.paused_tasks[task_id]
            await self.start_next_tasks()
            return True
        return False

    async def cancel_task(self, task_id: str):
        for i, task in enumerate(self.task_queue):
            if task.id == task_id:
                task.status = TaskStatus.CANCELLED
                self.task_queue.pop(i)
                return True
        if task_id in self.running_tasks:
            self.running_tasks[task_id].status = TaskStatus.CANCELLED
            del self.running_tasks[task_id]
            return True
        return False

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        for task in (
            self.task_queue
            + list(self.running_tasks.values())
            + list(self.paused_tasks.values())
            + self.completed_tasks
        ):
            if task.id == task_id:
                return asdict(task)
        return None

    async def get_queue_status(self) -> Dict[str, Any]:
        return {
            "queued": len(self.task_queue),
            "running": len(self.running_tasks),
            "paused": len(self.paused_tasks),
            "completed": len(self.completed_tasks),
            "max_parallel": self.max_parallel_tasks,
            "utilization": (len(self.running_tasks) / self.max_parallel_tasks * 100)
            if self.max_parallel_tasks > 0
            else 0,
        }

    async def shutdown(self):
        for task in self.running_tasks.values():
            task.status = TaskStatus.CANCELLED
        self.executor.shutdown(wait=True)
        logger.info("Multi-Task Scheduler shutdown complete")


# Global instance
_multi_task_scheduler: Optional[MultiTaskScheduler] = None


def get_multi_task_scheduler(
    max_parallel_tasks=5, task_manager=None
) -> MultiTaskScheduler:
    """Get or create global multi-task scheduler instance"""
    global _multi_task_scheduler
    if _multi_task_scheduler is None:
        import os

        # Respect environment variable for data directory (useful for CI/tests)
        data_dir = os.environ.get("BIODOCKIFY_DATA_DIR")
        if data_dir:
            persistence_path = os.path.join(data_dir, "scheduler_state.json")
            logger.info(f"Using BIODOCKIFY_DATA_DIR for scheduler: {persistence_path}")
            _multi_task_scheduler = MultiTaskScheduler(
                max_parallel_tasks=max_parallel_tasks,
                task_manager=task_manager,
                persistence_path=persistence_path,
            )
        else:
            _multi_task_scheduler = MultiTaskScheduler(
                max_parallel_tasks=max_parallel_tasks, task_manager=task_manager
            )
    return _multi_task_scheduler
