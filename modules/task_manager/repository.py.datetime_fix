"""
Task Manager - Database Layer
PostgreSQL integration with async support
"""
import asyncio
import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    create_engine, Column, String, DateTime, Integer, Text, 
    Float, JSON, Boolean, ForeignKey, Index, select, and_, or_
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from .models import Task, TaskStatus, TaskPriority, TaskType

logger = logging.getLogger(__name__)

Base = declarative_base()


class TaskORM(Base):
    """SQLAlchemy ORM for Task"""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    task_type = Column(String, nullable=False, index=True)
    priority = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    scheduled_at = Column(DateTime, nullable=True, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    dependencies = Column(JSON, nullable=True, default=list)
    blocking_for = Column(JSON, nullable=True, default=list)

    assigned_agent = Column(String, nullable=True, index=True)
    max_retries = Column(Integer, default=3)
    retry_count = Column(Integer, default=0)
    timeout_seconds = Column(Integer, nullable=True)

    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    memory_context_ids = Column(JSON, nullable=True, default=list)
    requires_memory_recall = Column(Boolean, default=False, index=True)

    estimated_duration_seconds = Column(Integer, nullable=True)
    actual_duration_seconds = Column(Integer, nullable=True)

    labels = Column(JSON, nullable=True, default=dict)

    # Indexes for common queries
    __table_args__ = (
        Index('ix_tasks_status_priority', 'status', 'priority'),
        Index('ix_tasks_scheduled_status', 'scheduled_at', 'status'),
        Index('ix_tasks_agent_status', 'assigned_agent', 'status'),
    )


class TaskExecutionEventORM(Base):
    """SQLAlchemy ORM for TaskExecutionEvent"""
    __tablename__ = "task_events"

    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey('tasks.id'), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    message = Column(Text, nullable=True)
    event_metadata = Column(JSON, nullable=True, default=dict)
    agent_id = Column(String, nullable=True)

    # Index for querying task history
    __table_args__ = (
        Index('ix_task_events_task_id_timestamp', 'task_id', 'timestamp'),
    )


class TaskRepository:
    """
    Repository for Task CRUD operations
    Integrates with PostgreSQL for persistence
    """

    def __init__(self, db_url: str):
        """Initialize repository with async database connection"""
        self.db_url = db_url
        self.engine = create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def initialize_schema(self):
        """Create tables if they don't exist"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Task database schema initialized")

    async def create_task(self, task: Task) -> Task:
        """Create a new task"""
        async with self.async_session() as session:
            async with session.begin():
                task_orm = TaskORM(**task.dict())
                session.add(task_orm)
                await session.flush()

                # Create initial event
                event_orm = TaskExecutionEventORM(
                    id=f"event_{task.id}_{datetime.utcnow().timestamp()}",
                    task_id=task.id,
                    event_type="created",
                    message=f"Task '{task.title}' created"
                )
                session.add(event_orm)

            await session.commit()
            logger.info(f"Created task: {task.id}")
            return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(TaskORM).where(TaskORM.id == task_id)
            )
            task_orm = result.scalar_one_or_none()
            if task_orm:
                # Filter out SQLAlchemy internal state
                data = {k: v for k, v in task_orm.__dict__.items() if not k.startswith('_')}
                return Task(**data)
            return None

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Task]:
        """Update task fields"""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(TaskORM).where(TaskORM.id == task_id)
                )
                task_orm = result.scalar_one_or_none()

                if not task_orm:
                    return None

                for key, value in updates.items():
                    if hasattr(task_orm, key):
                        setattr(task_orm, key, value)

                await session.commit()
                await session.refresh(task_orm)
                logger.info(f"Updated task: {task_id}")
                data = {k: v for k, v in task_orm.__dict__.items() if not k.startswith('_')}
                return Task(**data)

    async def get_pending_tasks(
        self,
        limit: int = 50,
        agent_id: Optional[str] = None
    ) -> List[Task]:
        """Get pending tasks ordered by priority"""
        async with self.async_session() as session:
            query = select(TaskORM).where(
                TaskORM.status == TaskStatus.PENDING
            )

            if agent_id:
                query = query.where(
                    or_(
                        TaskORM.assigned_agent == agent_id,
                        TaskORM.assigned_agent.is_(None)
                    )
                )

            query = query.order_by(
                TaskORM.priority.desc(),
                TaskORM.created_at.asc()
            ).limit(limit)

            result = await session.execute(query)
            return [Task(**{k: v for k, v in row.__dict__.items() if not k.startswith('_')}) for row in result.scalars()]

    async def get_scheduled_tasks(self, before: datetime) -> List[Task]:
        """Get tasks scheduled to run before given time"""
        async with self.async_session() as session:
            query = select(TaskORM).where(
                and_(
                    TaskORM.status == TaskStatus.SCHEDULED,
                    TaskORM.scheduled_at <= before
                )
            ).order_by(TaskORM.scheduled_at.asc())

            result = await session.execute(query)
            return [Task(**{k: v for k, v in row.__dict__.items() if not k.startswith('_')}) for row in result.scalars()]

    async def get_tasks_by_status(
        self,
        status: TaskStatus,
        limit: int = 100
    ) -> List[Task]:
        """Get tasks by status"""
        async with self.async_session() as session:
            query = select(TaskORM).where(
                TaskORM.status == status
            ).order_by(TaskORM.created_at.desc()).limit(limit)

            result = await session.execute(query)
            return [Task(**{k: v for k, v in row.__dict__.items() if not k.startswith('_')}) for row in result.scalars()]

    async def get_task_history(self, task_id: str) -> List[TaskExecutionEventORM]:
        """Get execution events for a task"""
        async with self.async_session() as session:
            query = select(TaskExecutionEventORM).where(
                TaskExecutionEventORM.task_id == task_id
            ).order_by(TaskExecutionEventORM.timestamp.desc())

            result = await session.execute(query)
            return list(result.scalars())

    async def log_event(
        self,
        task_id: str,
        event_type: str,
        message: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None
    ):
        """Log a task execution event"""
        async with self.async_session() as session:
            async with session.begin():
                event = TaskExecutionEventORM(
                    id=f"event_{task_id}_{datetime.utcnow().timestamp()}_{event_type}",
                    task_id=task_id,
                    event_type=event_type,
                    message=message,
                    event_metadata=event_metadata or {},
                    agent_id=agent_id
                )
                session.add(event)
                await session.commit()

    async def get_task_statistics(self) -> Dict[str, Any]:
        """Get task statistics for monitoring"""
        async with self.async_session() as session:
            # Count by status
            result = await session.execute(
                select(TaskORM.status)
            )
            status_counts = {}
            for row in result:
                status_counts[row[0]] = status_counts.get(row[0], 0) + 1

            # Count by type
            result = await session.execute(
                select(TaskORM.task_type)
            )
            type_counts = {}
            for row in result:
                type_counts[row[0]] = type_counts.get(row[0], 0) + 1

            # Average duration for completed tasks
            result = await session.execute(
                select(TaskORM.actual_duration_seconds).where(
                    TaskORM.status == TaskStatus.COMPLETED
                )
            )
            durations = [row[0] for row in result if row[0] is not None]
            avg_duration = sum(durations) / len(durations) if durations else 0

            return {
                "status_counts": status_counts,
                "type_counts": type_counts,
                "average_duration_seconds": avg_duration,
                "total_tasks": sum(status_counts.values())
            }
