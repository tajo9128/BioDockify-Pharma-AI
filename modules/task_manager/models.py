"""
Task Manager - Models and Enums
Integration point: Agent Zero + NanoBot + ChromaDB
"""
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class TaskStatus(str, Enum):
    """Task lifecycle states"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(str, Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskType(str, Enum):
    """Task types for Agent Zero"""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    WRITING = "writing"
    CODE_EXECUTION = "code_execution"
    SYSTEM_MAINTENANCE = "system_maintenance"
    SELF_REPAIR = "self_repair"
    MEMORY_CONSOLIDATION = "memory_consolidation"
    USER_REQUEST = "user_request"
    CRON_SCHEDULED = "cron_scheduled"


class TaskDependency(BaseModel):
    """Task dependency relationship"""
    depends_on: str = Field(..., description="Task ID this depends on")
    dependency_type: str = Field(default="completion", description="completion, start, or success")


class Task(BaseModel):
    """Core Task model"""
    id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Detailed task description")

    # Task Metadata
    task_type: TaskType = Field(default=TaskType.USER_REQUEST)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    status: TaskStatus = Field(default=TaskStatus.PENDING)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = Field(None, description="When to start (if scheduled)")
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)

    # Dependencies
    dependencies: List[TaskDependency] = Field(default_factory=list)
    blocking_for: List[str] = Field(default_factory=list)  # Tasks waiting for this one

    # Execution
    assigned_agent: Optional[str] = Field(None, description="Agent ID handling this task")
    max_retries: int = Field(default=3)
    retry_count: int = Field(default=0)
    timeout_seconds: Optional[int] = Field(default=None)

    # Results
    result: Optional[Dict[str, Any]] = Field(default=None)
    error_message: Optional[str] = Field(None)

    # Memory Integration
    memory_context_ids: List[str] = Field(default_factory=list)
    requires_memory_recall: bool = Field(default=False)

    # Metrics (Prometheus)
    estimated_duration_seconds: Optional[int] = Field(None)
    actual_duration_seconds: Optional[int] = Field(None)

    # Labels for filtering
    labels: Dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)


class TaskTemplate(BaseModel):
    """Reusable task templates"""
    id: str
    name: str
    description: str
    task_type: TaskType
    default_priority: TaskPriority = TaskPriority.MEDIUM
    template_parameters: Dict[str, Any] = Field(default_factory=dict)
    required_params: List[str] = Field(default_factory=list)


class TaskBatch(BaseModel):
    """Batch of related tasks"""
    id: str
    name: str
    description: Optional[str] = None
    task_ids: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    batch_metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskExecutionEvent(BaseModel):
    """Event logged during task execution"""
    id: str
    task_id: str
    event_type: str  # created, started, progress, completed, failed, retry
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    agent_id: Optional[str] = None
