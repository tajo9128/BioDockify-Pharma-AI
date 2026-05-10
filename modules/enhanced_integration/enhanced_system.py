"""
Enhanced Integration System - Unifies all modules
Features:
- Project-based task management
- Device awareness
- Multi-task execution
- Persistent memory
- Agent Zero planning
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import asdict

from modules.project_planner.project_planner import (
    ProjectPlanner,
    get_project_planner,
    ProjectType,
)
from modules.device_manager.device_state_manager import (
    DeviceStateManager,
    get_device_state_manager,
    DeviceState,
)
from modules.multi_task.multi_task_scheduler import (
    MultiTaskScheduler,
    get_multi_task_scheduler,
)
from modules.memory.advanced_memory import get_memory_system

logger = logging.getLogger(__name__)


class EnhancedSystem:
    """
    Enhanced Integration System

    Unifies:
    - Project Planner (Agent Zero planning)
    - Device State Manager (device awareness)
    - Multi-Task Scheduler (parallel execution)
    - Memory System (persistent storage)
    - Agent Zero (execution)
    """

    def __init__(self, hybrid_agent=None, max_parallel_tasks=5):
        self.hybrid_agent = hybrid_agent

        # Initialize subsystems
        self.memory_system = get_memory_system()
        self.project_planner = get_project_planner(
            hybrid_agent=hybrid_agent, memory_system=self.memory_system
        )
        self.device_manager = get_device_state_manager(memory_system=self.memory_system)

        # For multi-task scheduler, we might need a reference to the existing task manager
        # If we can't find one, it will use its internal mock execution
        task_manager = None
        try:
            from modules.integration.integrated_system import get_integrated_system

            integrated = get_integrated_system()
            task_manager = integrated.task_manager if integrated else None
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning(
                f"Optional integrated system not available: {e}. Using standalone scheduler."
            )

        self.multi_task_scheduler = get_multi_task_scheduler(
            max_parallel_tasks=max_parallel_tasks, task_manager=task_manager
        )

        self.is_initialized = False
        self.is_running = False
        self._setup_logging()

    def _setup_logging(self):
        logger.info("Enhanced System initializing")

    async def initialize(self, device_id: str = "default_device"):
        """Initialize all subsystems"""
        logger.info("Initializing Enhanced System...")

        # Initialize device manager
        await self.device_manager.initialize(device_id)

        self.is_initialized = True
        logger.info("Enhanced System initialized successfully")

    async def create_project(
        self,
        project_title: str,
        project_type: ProjectType = ProjectType.RESEARCH,
        additional_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new project with comprehensive task list
        """
        # Use Project Planner to create project
        project = await self.project_planner.create_project_from_title(
            project_title=project_title,
            project_type=project_type,
            additional_context=additional_context,
        )

        # Create device session for project
        session = await self.device_manager.create_session(project.id)

        # Add project tasks to multi-task scheduler
        # We need a mapping from task title/name to task ID for dependencies
        title_to_id = {task.title: task.id for task in project.tasks}

        for task in project.tasks:
            # Map dependency titles to IDs if they aren't already IDs
            mapped_deps = []
            for dep in task.depends_on:
                if dep in title_to_id:
                    mapped_deps.append(title_to_id[dep])
                else:
                    mapped_deps.append(dep)

            await self.multi_task_scheduler.add_task(
                task_id=task.id,
                title=task.title,
                description=task.description,
                priority=task.priority,
                dependencies=mapped_deps,
                estimated_seconds=int(task.estimated_hours * 3600),
                device_session_id=session.session_id,
            )

        # Start executing tasks
        await self.multi_task_scheduler.start_next_tasks()

        return {
            "success": True,
            "project_id": project.id,
            "project": {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "project_type": project.project_type.value,
                "estimated_completion": project.estimated_completion.isoformat()
                if project.estimated_completion
                else None,
                "total_tasks": len(project.tasks),
                "total_hours": sum(task.estimated_hours for task in project.tasks),
                "session_id": session.session_id,
            },
        }

    async def suspend_and_save(self):
        """
        Suspend all work and save state
        Called when device goes offline
        """
        logger.info("Suspending and saving state...")

        # Suspend device
        await self.device_manager.suspend()

        # Save all project contexts
        for project_id in self.device_manager.active_projects:
            # For each active project, we save its current state
            # This is a stub for potential richer UI context saving
            await self.device_manager.save_project_context(
                project_id,
                {"suspended_at": datetime.now(timezone.utc).isoformat()},
            )

        logger.info("State saved successfully")

    async def resume_and_restore(self):
        """
        Resume work and restore state
        Called when device comes online
        """
        logger.info("Resuming and restoring state...")

        # Resume device
        await self.device_manager.resume()

        # Restore project contexts
        for project_id in self.device_manager.active_projects:
            await self.device_manager.restore_project_context(project_id)

        # Resume task execution
        await self.multi_task_scheduler.start_next_tasks()

        logger.info("State restored successfully")

    async def update_task_progress(
        self, project_id: str, task_id: str, progress: float
    ) -> Dict[str, Any]:
        """Update progress for a task"""
        # Update progress in scheduler
        success = await self.multi_task_scheduler.update_task_progress(
            task_id, progress
        )

        if success:
            # Also update in project planner if it's 100%
            if progress >= 100.0:
                await self.complete_task(
                    project_id, task_id, {"status": "completed via progress update"}
                )
            else:
                # Save project context for intermediate progress
                await self.device_manager.save_project_context(
                    project_id,
                    {
                        "last_task_update": task_id,
                        "last_progress": progress,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

        return {"success": success, "task_id": task_id, "progress": progress}

    async def complete_task(
        self, project_id: str, task_id: str, result_data: Dict[str, Any]
    ):
        """Mark a task as completed with results"""
        # Update task in project planner
        await self.project_planner.update_task_status(
            project_id=project_id,
            task_id=task_id,
            status="completed",
            progress_data=result_data,
        )

        # Update project context
        await self.device_manager.save_project_context(
            project_id, {"task_completed": task_id, "result": result_data}
        )

        logger.info(f"Task completed: {task_id} in project: {project_id}")

    async def get_project_status(self, project_id: str) -> Dict[str, Any]:
        """Get comprehensive project status"""
        # Get project from planner
        project = await self.project_planner.get_project(project_id)
        if not project:
            return {"error": "Project not found"}

        # Get progress
        progress = await self.project_planner.calculate_project_progress(project_id)

        # Get task statuses
        tasks = await self.project_planner.get_project_tasks(project_id)

        # Get device status
        device_status = await self.device_manager.get_device_status()

        # Get queue status
        queue_status = await self.multi_task_scheduler.get_queue_status()

        return {
            "project": {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "project_type": project.project_type.value,
                "estimated_completion": project.estimated_completion.isoformat()
                if project.estimated_completion
                else None,
                "status": project.status,
            },
            "progress": progress,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "phase": t.phase.value,
                    "priority": t.priority,
                    "status": t.status,
                    "estimated_hours": t.estimated_hours,
                }
                for t in tasks
            ],
            "device_status": device_status,
            "task_queue": queue_status,
        }

    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        # Get projects
        projects = await self.project_planner.list_projects()

        # Get device status
        device_status = await self.device_manager.get_device_status()

        # Get task queue status
        queue_status = await self.multi_task_scheduler.get_queue_status()

        # Get memory statistics
        memory_stats = (
            await self.memory_system.get_statistics() if self.memory_system else {}
        )

        return {
            "projects": [
                {
                    "id": p.id,
                    "title": p.title,
                    "project_type": p.project_type.value,
                    "status": p.status,
                    "total_tasks": len(p.tasks),
                }
                for p in projects
            ],
            "active_projects": self.device_manager.active_projects,
            "device_status": device_status,
            "task_queue": queue_status,
            "memory_stats": memory_stats,
            "system_initialized": self.is_initialized,
            "system_running": self.is_running,
        }

    async def start(self):
        """Start the enhanced system"""
        if not self.is_initialized:
            await self.initialize()

        self.is_running = True
        logger.info("Enhanced System started")

        # Start multi-task scheduler
        await self.multi_task_scheduler.start_next_tasks()

    async def stop(self):
        """Stop the enhanced system"""
        logger.info("Stopping Enhanced System...")

        # Shutdown multi-task scheduler
        await self.multi_task_scheduler.shutdown()

        self.is_running = False
        logger.info("Enhanced System stopped")


# Global instance
_enhanced_system: Optional[EnhancedSystem] = None


def get_enhanced_system(hybrid_agent=None, max_parallel_tasks=5) -> EnhancedSystem:
    """Get or create global enhanced system instance"""
    global _enhanced_system
    if _enhanced_system is None:
        _enhanced_system = EnhancedSystem(
            hybrid_agent=hybrid_agent, max_parallel_tasks=max_parallel_tasks
        )
    return _enhanced_system
