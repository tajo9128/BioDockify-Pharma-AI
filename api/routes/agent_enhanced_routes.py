"""
BioDockify AI Enhanced API Routes

Extends BioDockify AI with NanoBot capabilities:
- Memory management (view/save)
- Background task spawning
- Skills listing
- Scheduled research jobs
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/agent", tags=["BioDockify AI Enhanced"])


# ========== Request/Response Models ==========

class MemorySaveRequest(BaseModel):
    content: str


class SpawnTaskRequest(BaseModel):
    task: str
    label: Optional[str] = None


class ScheduleTaskRequest(BaseModel):
    name: str
    message: str
    cron_expr: Optional[str] = None
    every_seconds: Optional[int] = None


class SkillInfo(BaseModel):
    name: str
    path: str
    source: str


# ========== Helper Functions ==========

def get_enhanced():
    """Get enhanced BioDockify AI instance."""
    try:
        from agent_zero.enhanced import get_agent_zero_enhanced
        return get_agent_zero_enhanced()
    except ImportError:
        raise HTTPException(status_code=503, detail="NanoBot enhancement not available")


# ========== Memory Endpoints ==========

@router.get("/memory")
async def get_agent_memory(days: int = 7):
    """Get BioDockify AI's memory context."""
    enhanced = get_enhanced()
    return {
        "context": enhanced.get_memory_context(),
        "days": days,
        "status": "ok"
    }


@router.post("/memory")
async def save_agent_memory(request: MemorySaveRequest):
    """Save important information to BioDockify AI's memory."""
    enhanced = get_enhanced()
    enhanced.save_to_memory(request.content)
    return {"status": "ok", "message": "Saved to memory"}


# ========== Skills Endpoints ==========

@router.get("/skills")
async def list_agent_skills():
    """List BioDockify AI's available skills."""
    enhanced = get_enhanced()
    skills = enhanced.list_skills()
    return {
        "skills": skills,
        "count": len(skills),
        "status": "ok"
    }


# ========== Background Tasks ==========

@router.post("/spawn")
async def spawn_background_task(request: SpawnTaskRequest):
    """Spawn a background research task."""
    enhanced = get_enhanced()
    result = await enhanced.spawn_background_task(request.task, request.label)
    return {
        "status": "ok",
        "message": result
    }


# ========== Agent Status ==========

@router.get("/status")
async def get_agent_status():
    """Get BioDockify AI's enhanced status."""
    try:
        enhanced = get_enhanced()
        return {
            "status": "ok",
            "enhanced": True,
            "workspace": str(enhanced.workspace),
            "memory_available": enhanced.memory is not None,
            "skills_available": enhanced.skills is not None,
            "skills_count": len(enhanced.list_skills()) if enhanced.skills else 0
        }
    except Exception as e:
        return {
            "status": "ok",
            "enhanced": False,
            "error": str(e)
        }
