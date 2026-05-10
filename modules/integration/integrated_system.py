"""
Integration Module - Agent Zero + NanoBot + Task Manager + Memory
Unifies all systems into a cohesive production-ready platform
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from agent_zero.hybrid.agent import HybridAgent

from modules.task_manager.manager import TaskManager
from modules.task_manager.models import Task, TaskType, TaskPriority, TaskStatus
from modules.memory.advanced_memory import (
    AdvancedMemorySystem, MemoryType, MemoryImportance, get_memory_system
)

from prometheus_client import Counter, Gauge, start_http_server

logger = logging.getLogger(__name__)


class IntegratedSystem:
    """
    Unified System - Integrates Agent Zero, NanoBot, Task Manager, and Memory
    """

    def __init__(
        self,
        db_url: str,
        hybrid_agent: HybridAgent,
        memory_persist_dir: str = "./data/chroma_memory"
    ):
        self.task_manager = TaskManager(db_url, hybrid_agent=hybrid_agent)
        self.memory_system = get_memory_system(persist_dir=memory_persist_dir)

        self.hybrid_agent = hybrid_agent
        self.is_initialized = False
        self.is_running = False

        self._setup_metrics()

    def _setup_metrics(self):
        """Setup integrated system metrics"""
        try:
            # We use a standard port 8000 for metrics if not already started
            # start_http_server(8000)
            
            self.integrated_requests_counter = Counter(
                'integrated_system_requests_total',
                'Total integrated system requests',
                ['subsystem', 'action', 'status']
            )

            self.active_agents_gauge = Gauge(
                'integrated_system_active_agents',
                'Number of active agents'
            )

            self.system_health_gauge = Gauge(
                'integrated_system_health',
                'System health score (0-100)'
            )
        except ValueError:
            pass

        logger.info("Integrated metrics initialized")

    async def initialize(self):
        """Initialize all subsystems"""
        logger.info("Initializing Integrated System...")

        await self.task_manager.initialize()
        logger.info("✅ Task Manager initialized")

        logger.info("✅ Memory System initialized")

        if hasattr(self.hybrid_agent, 'start_services'):
            await self.hybrid_agent.start_services()
            logger.info("✅ Agent Zero services started")

        await self._setup_integrations()

        self.is_initialized = True
        logger.info("Integrated System initialized successfully")

    async def _setup_integrations(self):
        """Set up cross-system integrations"""
        # Register task manager callbacks
        # We need a way to hook into completion
        self.task_manager.register_callback(None, self._on_task_event)
        logger.info("✅ Cross-system integrations set up")

    async def _on_task_event(self, task_id: str):
        """Handle task events - proxy to specialized handlers"""
        if not task_id:
            return
        await self._on_task_completion(task_id)

    async def _on_task_completion(self, task_id: str):
        """Handle task completion - store in memory"""
        status_data = await self.task_manager.get_task_status(task_id)
        if not status_data:
            return

        task_dict = status_data['task']
        status = task_dict.get('status')

        if status == TaskStatus.COMPLETED:
            memory_content = f"""
Task: {task_dict.get('title')}
Description: {task_dict.get('description', '')}
Result: {task_dict.get('result', {})}
Type: {task_dict.get('task_type')}
Completed: {task_dict.get('completed_at')}
            """.strip()

            await self.memory_system.add_memory(
                content=memory_content,
                memory_type=MemoryType.PROCEDURAL,
                importance=MemoryImportance.HIGH,
                source=f"task:{task_id}",
                tags=['task', str(task_dict.get('task_type')), 'completed'],
                metadata={
                    'task_id': task_id,
                    'task_type': str(task_dict.get('task_type')),
                    'completed_at': str(task_dict.get('completed_at'))
                }
            )

            logger.info(f"Stored task result in memory: {task_id}")

        elif status == TaskStatus.FAILED:
            memory_content = f"""
Failed Task: {task_dict.get('title')}
Description: {task_dict.get('description', '')}
Error: {task_dict.get('error_message')}
Type: {task_dict.get('task_type')}
Retries: {task_dict.get('retry_count')}
            """.strip()

            await self.memory_system.add_memory(
                content=memory_content,
                memory_type=MemoryType.PROCEDURAL,
                importance=MemoryImportance.HIGH,
                source=f"task:{task_id}",
                tags=['task', 'failed', 'self_repair'],
                metadata={
                    'task_id': task_id,
                    'task_type': str(task_dict.get('task_type')),
                    'error': task_dict.get('error_message')
                }
            )

            logger.info(f"Stored failed task for self-repair: {task_id}")

    async def execute_task_with_memory(
        self,
        title: str,
        description: str,
        task_type: TaskType = TaskType.USER_REQUEST,
        priority: TaskPriority = TaskPriority.MEDIUM,
        recall_memory: bool = True
    ) -> str:
        """Execute a task with automatic memory recall"""
        memory_context = []
        if recall_memory:
            search_query = f"{title} {description or ''}"
            memories = await self.memory_system.search(
                search_query,
                limit=5,
                memory_types=[MemoryType.PROCEDURAL, MemoryType.SEMANTIC]
            )

            if memories:
                memory_context = [f"- {m['content']}" for m in memories]
                logger.info(f"Recalled {len(memories)} relevant memories")

        enhanced_description = description or ""
        if memory_context:
            enhanced_description += f"\n\nRelevant Context from Memory:\n" + "\n".join(memory_context)

        task = await self.task_manager.create_task(
            title=title,
            description=enhanced_description,
            task_type=task_type,
            priority=priority,
            requires_memory=recall_memory
        )

        if hasattr(self, 'integrated_requests_counter'):
            self.integrated_requests_counter.labels(
                subsystem='task_manager',
                action='create',
                status='success'
            ).inc()

        return task.id

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status with memory context"""
        status = await self.task_manager.get_task_status(task_id)

        if status:
            task_dict = status['task']
            related_memories = await self.memory_system.search(
                f"task:{task_id} {task_dict.get('title')}",
                limit=3
            )

            status['related_memories'] = related_memories

        return status

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        task_dashboard = await self.task_manager.get_dashboard_data()
        memory_stats = await self.memory_system.get_statistics()

        agent_state = {
            "is_running": getattr(self.hybrid_agent, 'is_running', False),
            "loop_iterations": getattr(self.hybrid_agent.loop_data, 'iterations', 0) if hasattr(self.hybrid_agent, 'loop_data') else 0
        }

        return {
            "tasks": task_dashboard,
            "memory": memory_stats,
            "agent_zero": agent_state,
            "system": {
                "initialized": self.is_initialized,
                "running": self.is_running,
                "health": await self._calculate_health()
            }
        }

    async def _calculate_health(self) -> float:
        """Calculate overall system health score (0-100)"""
        score = 100.0

        try:
            task_stats = await self.task_manager.db.get_task_statistics()
            total_tasks = task_stats.get('total_tasks', 0)
            if total_tasks > 0:
                failed_ratio = task_stats['status_counts'].get('failed', 0) / total_tasks
                score -= failed_ratio * 20

            memory_stats = await self.memory_system.get_statistics()
            if memory_stats['working_memory_count'] > 45:
                score -= 10

            if not getattr(self.hybrid_agent, 'is_running', True):
                score -= 30
        except Exception as e:
            logger.warning(f"Health calculation degraded: {e}")
            score -= 10

        return max(0.0, min(100.0, score))

    async def start(self):
        """Start all systems"""
        if not self.is_initialized:
            await self.initialize()

        logger.info("Starting Integrated System...")

        asyncio.create_task(self.task_manager.start_scheduler())
        asyncio.create_task(self._health_monitor_loop())

        self.is_running = True
        if hasattr(self, 'active_agents_gauge'):
            self.active_agents_gauge.set(1)
        logger.info("Integrated System started successfully")

    async def stop(self):
        """Stop all systems"""
        logger.info("Stopping Integrated System...")

        self.is_running = False

        await self.task_manager.stop_scheduler()

        if hasattr(self.hybrid_agent, 'stop_services'):
            await self.hybrid_agent.stop_services()

        if hasattr(self, 'active_agents_gauge'):
            self.active_agents_gauge.set(0)
        logger.info("Integrated System stopped")

    async def _health_monitor_loop(self):
        """Background health monitoring loop"""
        while self.is_running:
            try:
                health = await self._calculate_health()
                if hasattr(self, 'system_health_gauge'):
                    self.system_health_gauge.set(health)
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(60)

    async def create_research_task(
        self,
        query: str,
        priority: TaskPriority = TaskPriority.HIGH,
        use_deep_research: bool = True
    ) -> str:
        """Create a research task with SurfSense integration"""
        description = f"Research query: {query}"

        if use_deep_research:
            description += "\n\nUse SurfSense deep research pipeline for comprehensive results."

        return await self.execute_task_with_memory(
            title=f"Research: {query[:50]}",
            description=description,
            task_type=TaskType.RESEARCH,
            priority=priority,
            recall_memory=True
        )

    async def create_self_repair_task(
        self,
        error_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a self-repair task"""
        description = f"""
Error: {error_description}
Context: {context or ''}
Use Agent Zero's self-repair capabilities to diagnose and fix this issue.
        """.strip()

        return await self.task_manager.create_task(
            title="Self-Repair Task",
            description=description,
            task_type=TaskType.SELF_REPAIR,
            priority=TaskPriority.CRITICAL,
            requires_memory=True
        )


# Global instance
_integrated_system: Optional[IntegratedSystem] = None


def get_integrated_system() -> Optional[IntegratedSystem]:
    """Get global integrated system instance"""
    return _integrated_system


async def initialize_integrated_system(
    db_url: str,
    hybrid_agent: HybridAgent,
    memory_persist_dir: str = "./data/chroma_memory"
) -> IntegratedSystem:
    """Initialize integrated system"""
    global _integrated_system

    if _integrated_system is None:
        _integrated_system = IntegratedSystem(
            db_url=db_url,
            hybrid_agent=hybrid_agent,
            memory_persist_dir=memory_persist_dir
        )

        await _integrated_system.initialize()

    return _integrated_system
