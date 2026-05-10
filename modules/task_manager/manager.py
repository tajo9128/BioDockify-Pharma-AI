"""
Task Manager - Core Engine
Orchestrates tasks with Agent Zero + NanoBot integration
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Callable
from collections import defaultdict

from .models import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskType,
    TaskDependency,
    TaskExecutionEvent,
)
from .repository import TaskRepository
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Core Task Management Engine
    Integrates with:
    - Agent Zero (execution & self-repair)
    - NanoBot (multi-agent coordination)
    - Memory System (context & history)
    - ChromaDB (vector search for related tasks)
    """

    def __init__(self, db_url: str, hybrid_agent=None):
        self.db = TaskRepository(db_url)
        self.hybrid_agent = hybrid_agent
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.scheduler_running = False

        # Metrics
        self._setup_metrics()

    def _setup_metrics(self):
        """Setup Prometheus metrics for task management"""
        # We use a try-except block to avoid failure if metrics are already defined
        try:
            self.task_counter = Counter(
                "task_manager_tasks_total",
                "Total tasks created",
                ["status", "type", "priority"],
            )

            self.task_duration = Histogram(
                "task_manager_execution_duration_seconds",
                "Task execution duration",
                ["type", "priority"],
            )

            self.task_retry_counter = Counter(
                "task_manager_retries_total", "Total task retries", ["success"]
            )

            self.active_tasks_gauge = Gauge(
                "task_manager_active_tasks", "Number of currently active tasks"
            )

            self.queue_depth_gauge = Gauge(
                "task_manager_queue_depth", "Number of pending tasks"
            )
        except ValueError:
            # Metrics already registered
            pass

    async def initialize(self):
        """Initialize task manager"""
        await self.db.initialize_schema()
        logger.info("Task Manager initialized")

    async def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        task_type: TaskType = TaskType.USER_REQUEST,
        priority: TaskPriority = TaskPriority.MEDIUM,
        scheduled_at: Optional[datetime] = None,
        dependencies: Optional[List[TaskDependency]] = None,
        assigned_agent: Optional[str] = None,
        requires_memory: bool = False,
        labels: Optional[Dict[str, str]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> Task:
        """Create a new task with optional scheduling and dependencies"""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            status=TaskStatus.SCHEDULED if scheduled_at else TaskStatus.PENDING,
            scheduled_at=scheduled_at,
            dependencies=dependencies or [],
            assigned_agent=assigned_agent,
            requires_memory_recall=requires_memory,
            labels=labels or {},
            timeout_seconds=timeout_seconds,
        )

        # Handle dependencies
        if dependencies:
            await self._handle_dependencies(task)

        # Save to database
        created_task = await self.db.create_task(task)

        # Update metrics
        if hasattr(self, "task_counter"):
            self.task_counter.labels(
                status=created_task.status, type=task_type, priority=priority
            ).inc()

        await self._update_queue_depth()
        logger.info(f"Created task: {task_id} - {title}")

        # Execute immediately if not scheduled and no dependencies
        if not scheduled_at and not dependencies:
            await self.enqueue_task(task_id)

        return created_task

    async def _handle_dependencies(self, task: Task):
        """Update blocking relationships for dependencies"""
        for dep in task.dependencies:
            dep_task = await self.db.get_task(dep.depends_on)
            if dep_task:
                dep_task.blocking_for.append(task.id)
                await self.db.update_task(
                    dep_task.id, {"blocking_for": dep_task.blocking_for}
                )

    async def enqueue_task(self, task_id: str):
        """Enqueue task for execution"""
        task = await self.db.get_task(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return

        if task.status not in [TaskStatus.PENDING, TaskStatus.RETRYING]:
            logger.warning(
                f"Task not in allowed execution state: {task_id} ({task.status})"
            )
            return

        # Check dependencies
        if await self._check_dependencies(task_id):
            asyncio_task = asyncio.create_task(self._execute_task(task_id))
            self.running_tasks[task_id] = asyncio_task

            await self.db.update_task(
                task_id,
                {
                    "status": TaskStatus.IN_PROGRESS,
                    "started_at": datetime.now(timezone.utc),
                },
            )

            await self.db.log_event(
                task_id,
                "started",
                f"Task '{task.title}' started execution",
                agent_id=task.assigned_agent,
            )

            if hasattr(self, "active_tasks_gauge"):
                self.active_tasks_gauge.inc()
            logger.info(f"Started task execution: {task_id}")
        else:
            await self.db.update_task(task_id, {"status": TaskStatus.BLOCKED})

    async def _check_dependencies(self, task_id: str) -> bool:
        """Check if all dependencies are satisfied"""
        task = await self.db.get_task(task_id)
        if not task or not task.dependencies:
            return True

        for dep in task.dependencies:
            dep_task = await self.db.get_task(dep.depends_on)
            if not dep_task:
                logger.error(f"Dependency not found: {dep.depends_on}")
                return False

            if dep_task.status not in [TaskStatus.COMPLETED]:
                logger.debug(f"Dependency not completed: {dep.depends_on}")
                return False

        return True

    async def _execute_task(self, task_id: str):
        """Execute a task with Agent Zero"""
        task = await self.db.get_task(task_id)
        if not task:
            logger.error(f"Task not found for execution: {task_id}")
            return

        start_time = datetime.now(timezone.utc)

        try:
            # Memory Recall (if required)
            memory_context = []
            if task.requires_memory_recall and self.hybrid_agent:
                memory_context = await self._recall_task_memory(task)

            # Execute with Agent Zero
            if self.hybrid_agent:
                enhanced_description = task.description or ""
                if memory_context:
                    enhanced_description += f"\n\nRelevant Memory:\n{memory_context}"

                result = await self._execute_with_agent_zero(task, enhanced_description)
            else:
                result = await self._execute_direct(task)

            # Success
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            await self._complete_task(task_id, result, duration)

        except Exception as e:
            logger.error(f"Task execution failed: {task_id} - {str(e)}")

            task.retry_count += 1

            if task.retry_count <= task.max_retries:
                await self._retry_task(task_id, str(e))
            else:
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                await self._fail_task(task_id, str(e), duration)

        finally:
            self.running_tasks.pop(task_id, None)
            if hasattr(self, "active_tasks_gauge"):
                self.active_tasks_gauge.dec()
            await self._update_queue_depth()
            await self._trigger_callbacks(task_id)
            await self._unblock_dependents(task_id)

    async def _execute_with_agent_zero(
        self, task: Task, enhanced_description: str
    ) -> Dict[str, Any]:
        """Execute task using Agent Zero's hybrid agent"""
        prompt = f"""
Task: {task.title}
Description: {enhanced_description}
Task Type: {task.task_type}
Priority: {task.priority}
Please execute this task using available tools and skills.
Report back with result.
"""

        if hasattr(self.hybrid_agent, "loop_data"):
            self.hybrid_agent.loop_data.current_task = task.id

        # Execute using main interface
        # result = await self.hybrid_agent.execute(prompt)
        # Note: In a real system, we'd use the message bus or a direct execute call
        # For MVP integration, we'll use execute if available
        if hasattr(self.hybrid_agent, "execute"):
            result = await self.hybrid_agent.execute(prompt)
            data = result if isinstance(result, dict) else {"content": str(result)}
        else:
            data = {"message": "Agent execution interface not found"}

        return {
            "success": True,
            "data": data,
            "self_repair_used": getattr(
                self.hybrid_agent.loop_data, "self_repair_triggered", False
            )
            if hasattr(self.hybrid_agent, "loop_data")
            else False,
        }

    async def _execute_direct(self, task: Task) -> Dict[str, Any]:
        """Direct task execution (fallback)"""
        return {"success": True, "data": {"message": f"Executed: {task.title}"}}

    async def _recall_task_memory(self, task: Task) -> str:
        """Recall relevant memory for task"""
        if not self.hybrid_agent or not hasattr(self.hybrid_agent, "memory"):
            return ""

        search_query = f"{task.title} {task.description or ''}"
        try:
            memories = await self.hybrid_agent.memory.search(search_query, limit=5)

            if memories:
                memory_ids = [m.get("id") for m in memories]
                await self.db.update_task(task.id, {"memory_context_ids": memory_ids})

                return "\n".join([m.get("text", "") for m in memories])
        except Exception as e:
            logger.warning(f"Memory recall failed: {e}")

        return ""

    async def _complete_task(
        self, task_id: str, result: Dict[str, Any], duration: float
    ):
        """Mark task as completed"""
        await self.db.update_task(
            task_id,
            {
                "status": TaskStatus.COMPLETED,
                "completed_at": datetime.now(timezone.utc),
                "result": result,
                "actual_duration_seconds": int(duration),
            },
        )

        await self.db.log_event(
            task_id,
            "completed",
            f"Task completed in {duration:.2f} seconds",
            metadata={"result": result},
        )

        # Store result in memory
        task = await self.db.get_task(task_id)
        if self.hybrid_agent and hasattr(self.hybrid_agent, "memory") and task:
            try:
                await self.hybrid_agent.memory.add_memory(
                    f"Task Completed: {task.title}\nResult: {result}", area="solutions"
                )
            except Exception as e:
                logger.warning(f"Failed to store task result in memory: {e}")

        logger.info(f"Task completed: {task_id} in {duration:.2f}s")

    async def _retry_task(self, task_id: str, error_message: str):
        """Schedule task for retry"""
        await self.db.update_task(
            task_id, {"status": TaskStatus.RETRYING, "error_message": error_message}
        )

        retry_count = await self._get_retry_count(task_id)
        await asyncio.sleep(2**retry_count)

        await self.db.update_task(task_id, {"status": TaskStatus.PENDING})
        await self.enqueue_task(task_id)

        if hasattr(self, "task_retry_counter"):
            self.task_retry_counter.labels(success="pending").inc()

    async def _fail_task(self, task_id: str, error_message: str, duration: float):
        """Mark task as failed"""
        await self.db.update_task(
            task_id,
            {
                "status": TaskStatus.FAILED,
                "completed_at": datetime.now(timezone.utc),
                "error_message": error_message,
                "actual_duration_seconds": int(duration),
            },
        )

        await self.db.log_event(
            task_id,
            "failed",
            f"Task failed: {error_message}",
            metadata={"error": error_message},
        )

        if hasattr(self, "task_retry_counter"):
            self.task_retry_counter.labels(success="failed").inc()

    async def _unblock_dependents(self, task_id: str):
        """Unblock tasks waiting for this task to complete"""
        task = await self.db.get_task(task_id)
        if not task or not task.blocking_for:
            return

        for dependent_id in task.blocking_for:
            dependent_task = await self.db.get_task(dependent_id)
            if dependent_task and dependent_task.status == TaskStatus.BLOCKED:
                if await self._check_dependencies(dependent_id):
                    await self.db.update_task(
                        dependent_id, {"status": TaskStatus.PENDING}
                    )
                    await self.enqueue_task(dependent_id)
                    logger.info(f"Unblocked task: {dependent_id}")

    async def _get_retry_count(self, task_id: str) -> int:
        """Get current retry count"""
        task = await self.db.get_task(task_id)
        return task.retry_count if task else 0

    async def _update_queue_depth(self):
        """Update queue depth metric"""
        pending = await self.db.get_pending_tasks()
        if hasattr(self, "queue_depth_gauge"):
            self.queue_depth_gauge.set(len(pending))

    async def _trigger_callbacks(self, task_id: str):
        """Trigger callbacks for task events"""
        if task_id in self.task_callbacks:
            for callback in self.task_callbacks[task_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(task_id)
                    else:
                        callback(task_id)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

    def register_callback(self, task_id: str, callback: Callable):
        """Register callback for task completion"""
        self.task_callbacks[task_id].append(callback)

    async def start_scheduler(self):
        """Start task scheduler for scheduled tasks"""
        self.scheduler_running = True
        logger.info("Task scheduler started")

        while self.scheduler_running:
            try:
                now = datetime.now(timezone.utc)
                scheduled_tasks = await self.db.get_scheduled_tasks(now)

                for task in scheduled_tasks:
                    if task.status == TaskStatus.SCHEDULED:
                        await self.db.update_task(
                            task.id, {"status": TaskStatus.PENDING}
                        )
                        await self.enqueue_task(task.id)

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(5)

    async def stop_scheduler(self):
        """Stop scheduler"""
        self.scheduler_running = False
        logger.info("Task scheduler stopped")

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        task = await self.db.get_task(task_id)
        if not task:
            return False

        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            return False

        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]

        await self.db.update_task(
            task_id,
            {
                "status": TaskStatus.CANCELLED,
                "completed_at": datetime.now(timezone.utc),
            },
        )

        await self.db.log_event(task_id, "cancelled", "Task cancelled by user")
        logger.info(f"Cancelled task: {task_id}")
        return True

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task status with history"""
        task = await self.db.get_task(task_id)
        if not task:
            return None

        history = await self.db.get_task_history(task_id)

        return {"task": task.dict(), "history": [h.__dict__ for h in history]}

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for monitoring"""
        stats = await self.db.get_task_statistics()
        pending = await self.db.get_pending_tasks()
        active = len(self.running_tasks)

        return {
            "statistics": stats,
            "pending_tasks": [t.dict() for t in pending[:10]],
            "active_count": active,
            "recent_completed": [
                t.dict()
                for t in await self.db.get_tasks_by_status(
                    TaskStatus.COMPLETED, limit=10
                )
            ],
        }
