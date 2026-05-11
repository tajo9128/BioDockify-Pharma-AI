
"""
Enhanced Research API Endpoints
Integrates auto-research with chat, bidirectional communication, and todo list management.
"""
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio

# Import research components - dynamic path resolution for cross-platform compatibility
import sys
from pathlib import Path

# Get project root dynamically
_project_root = Path(__file__).parent.parent.parent.absolute()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from modules.research_detector import ResearchTopicDetector, ResearchTopic
from modules.auto_research_orchestrator import (
    AutoResearchOrchestrator,
    TodoListManager,
    AgentCommunicationBridge,
    ResearchPlan,
    ResearchStage
)

logger = logging.getLogger(__name__)

# Global orchestrator instance (initialized at startup)
_research_orchestrator: Optional[AutoResearchOrchestrator] = None
_active_research_plans: Dict[str, ResearchPlan] = {}  # context_id -> ResearchPlan

# Request/Response models
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to process")
    context_id: str = Field(..., description="Conversation context ID")
    trigger_research: bool = Field(False, description="Manually trigger research")

class ChatResponse(BaseModel):
    response: str
    research_detected: bool
    research_plan: Optional[Dict[str, Any]] = None
    todo_list: Optional[Dict[str, Any]] = None


class AutoResearchRequest(BaseModel):
    topic: str = Field(..., description="Research topic")
    research_type: str = Field("general", description="Type: 'phd', 'grand', 'review_article', or 'general'")
    context_id: str = Field(..., description="Conversation context ID")
    auto_execute: bool = Field(True, description="Auto-execute research or just create plan")


class TodoListResponse(BaseModel):
    context_id: str
    tasks: List[Dict[str, Any]]
    summary: Dict[str, Any]
    progress: float
    current_stage: str


class CommunicationRequest(BaseModel):
    from_agent: str = Field(..., description="Sender: 'agent_zero' or 'nanobot'")
    to_agent: str = Field(..., description="Receiver: 'agent_zero' or 'nanobot'")
    message: str = Field(..., description="Message content")
    request_permission: bool = Field(False, description="Request user permission")
    data: Optional[Dict[str, Any]] = None


# Initialize orchestrator
def get_orchestrator() -> AutoResearchOrchestrator:
    """Get or create the research orchestrator."""
    global _research_orchestrator
    if _research_orchestrator is None:
        bridge = AgentCommunicationBridge(
            agent_zero_endpoint="/api/agent",
            nanobot_endpoint="/api/nanobot"
        )
        _research_orchestrator = AutoResearchOrchestrator(
            communication_bridge=bridge
        )
    return _research_orchestrator


router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("/chat", response_model=ChatResponse)
async def enhanced_chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    """
    Enhanced chat endpoint with automatic research detection.
    Detects research topics and triggers auto-research workflow.
    """
    orchestrator = get_orchestrator()
    
    # Detect if message contains research topic
    research_topic = orchestrator.detect_research_topic(request.message)
    
    research_plan = None
    todo_list = None
    
    if research_topic or request.trigger_research:
        # Research detected - create plan
        if research_topic is None:
            # Manual trigger without detection - create from message
            research_topic = ResearchTopic(
                topic=request.message,
                research_type="general",
                confidence=1.0,
                keywords=[]
            )
        
        plan = orchestrator.create_research_plan(research_topic)
        _active_research_plans[request.context_id] = plan
        
        # Execute research in background if requested
        if request.auto_execute or research_topic.confidence > 0.7:
            background_tasks.add_task(execute_research_background, request.context_id, plan)
        
        research_plan = {
            "topic": plan.topic,
            "research_type": plan.research_type,
            "stages": plan.stages,
            "created_at": plan.created_at.isoformat()
        }
        
        todo_list = get_todo_list_summary(request.context_id)
        
        # Generate response indicating research started
        response = f"🔬 Research topic detected: '{plan.topic}' ({plan.research_type})

"
        response += f"Research plan created with {len(plan.tasks)} tasks. "
        response += f"Executing research workflow automatically..."
        
    else:
        # No research detected - normal chat response
        # In production, this would route to BioDockify AI or NanoBot
        response = f"Processing your message in {request.mode} mode..."
    
    return ChatResponse(
        response=response,
        research_detected=(research_topic is not None or request.trigger_research),
        research_plan=research_plan,
        todo_list=todo_list
    )


@router.post("/trigger", response_model=Dict[str, Any])
async def trigger_research(request: AutoResearchRequest):
    """
    Manually trigger research workflow.
    Can be used to explicitly start research for a given topic.
    """
    orchestrator = get_orchestrator()
    
    # Create research topic from request
    research_topic = ResearchTopic(
        topic=request.topic,
        research_type=request.research_type,
        confidence=1.0,
        keywords=[]
    )
    
    # Create plan
    plan = orchestrator.create_research_plan(research_topic)
    _active_research_plans[request.context_id] = plan
    
    # Execute if auto_execute is True
    if request.auto_execute:
        asyncio.create_task(execute_research_background(request.context_id, plan))
    
    return {
        "status": "created",
        "context_id": request.context_id,
        "research_plan": {
            "topic": plan.topic,
            "research_type": plan.research_type,
            "stages": plan.stages,
            "task_count": len(plan.tasks)
        },
        "auto_execute": request.auto_execute
    }


@router.get("/todo/{context_id}", response_model=TodoListResponse)
async def get_todo_list(context_id: str):
    """
    Get todo list and research progress for a context.
    """
    return get_todo_list_summary(context_id)


@router.get("/progress/{context_id}", response_model=Dict[str, Any])
async def get_research_progress(context_id: str):
    """
    Get detailed research progress including stage and completion status.
    """
    if context_id not in _active_research_plans:
        raise HTTPException(status_code=404, detail="No active research for this context")
    
    plan = _active_research_plans[context_id]
    
    return {
        "context_id": context_id,
        "topic": plan.topic,
        "research_type": plan.research_type,
        "current_stage": plan.current_stage.value,
        "progress": plan.progress,
        "task_count": len(plan.tasks),
        "completed_tasks": sum(1 for t in plan.tasks if t.status == "completed"),
        "created_at": plan.created_at.isoformat()
    }


@router.post("/communicate", response_model=Dict[str, Any])
async def agent_communication(request: CommunicationRequest):
    """
    Handle bidirectional communication between BioDockify AI and NanoBot.
    Manages permissions and data exchange.
    """
    orchestrator = get_orchestrator()
    
    try:
        if request.to_agent == "nanobot":
            result = await orchestrator.bridge.send_to_nanobot(
                request.message,
                permission_required=request.request_permission
            )
        elif request.to_agent == "agent_zero":
            result = await orchestrator.bridge.send_to_agent_zero(
                request.message,
                request.data
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid target agent")
        
        return {
            "status": "success",
            "from": request.from_agent,
            "to": request.to_agent,
            "result": result
        }
    
    except Exception as e:
        logger.error(f"Communication error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communication/history")
async def get_communication_history():
    """
    Get communication history between agents.
    """
    orchestrator = get_orchestrator()
    
    return {
        "history": orchestrator.bridge.get_communication_history()
    }


# Background task helper
async def execute_research_background(context_id: str, plan: ResearchPlan):
    """Execute research in background."""
    orchestrator = get_orchestrator()
    try:
        updated_plan = await orchestrator.execute_research(plan)
        _active_research_plans[context_id] = updated_plan
        logger.info(f"Research completed for context {context_id}")
    except Exception as e:
        logger.error(f"Research execution failed for context {context_id}: {e}")
        plan.current_stage = ResearchStage.FAILED


def get_todo_list_summary(context_id: str) -> Dict[str, Any]:
    """Get todo list summary for a context."""
    if context_id not in _active_research_plans:
        return {
            "tasks": [],
            "summary": {"total_tasks": 0, "status_counts": {}, "progress": 0.0},
            "progress": 0.0,
            "current_stage": "none"
        }
    
    plan = _active_research_plans[context_id]
    
    tasks_list = [
        {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "description": task.description
        }
        for task in plan.tasks
    ]
    
    summary = {
        "total_tasks": len(plan.tasks),
        "status_counts": {},
        "progress": plan.progress,
        "pending_high_priority": 0
    }
    
    for task in plan.tasks:
        status = task.status
        summary["status_counts"][status] = summary["status_counts"].get(status, 0) + 1
        if status == "pending" and task.priority >= 4:
            summary["pending_high_priority"] += 1
    
    return {
        "context_id": context_id,
        "tasks": tasks_list,
        "summary": summary,
        "progress": plan.progress,
        "current_stage": plan.current_stage.value
    }
