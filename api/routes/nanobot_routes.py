"""
NanoBot API Routes - Exposes hybrid agent features via REST API.

Endpoints:
- POST /api/nanobot/chat - Chat with the hybrid agent
- POST /api/nanobot/spawn - Spawn a background task
- POST /api/nanobot/schedule - Schedule a recurring task
- GET /api/nanobot/memory - Get memory context
- GET /api/nanobot/skills - List available skills
- GET /api/nanobot/cron - List scheduled jobs
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import asyncio

from agent_zero.nanobot_bridge import HybridAgentBrain, create_hybrid_agent


# Initialize the hybrid agent
_agent: Optional[HybridAgentBrain] = None


def get_agent() -> HybridAgentBrain:
    """Get or create the singleton hybrid agent instance."""
    global _agent
    if _agent is None:
        _agent = create_hybrid_agent(
            workspace_path="./workspace/nanobot",
            model="anthropic/claude-sonnet-4-5",
        )
    return _agent


router = APIRouter(prefix="/api/nanobot", tags=["NanoBot Hybrid Agent"])


# ========== Request/Response Models ==========

class ChatRequest(BaseModel):
    message: str
    session_key: str = "default"


class ChatResponse(BaseModel):
    response: str
    session_key: str


class SpawnRequest(BaseModel):
    task: str
    label: Optional[str] = None


class SpawnResponse(BaseModel):
    status: str
    message: str


class ScheduleRequest(BaseModel):
    name: str
    message: str
    cron_expr: Optional[str] = None
    every_seconds: Optional[int] = None


class ScheduleResponse(BaseModel):
    id: str
    name: str
    next_run: Optional[int]


class MemoryResponse(BaseModel):
    context: str
    recent_days: int


class SkillInfo(BaseModel):
    name: str
    path: str
    source: str


class SkillsResponse(BaseModel):
    skills: list[SkillInfo]
    count: int


class CronJobInfo(BaseModel):
    id: str
    name: str
    enabled: bool
    next_run_at_ms: Optional[int]
    last_status: Optional[str]


class CronListResponse(BaseModel):
    jobs: list[CronJobInfo]
    count: int


# ========== API Endpoints ==========

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the hybrid agent."""
    agent = get_agent()
    
    try:
        response = await agent.chat(
            message=request.message,
            session_key=request.session_key,
        )
        return ChatResponse(
            response=response,
            session_key=request.session_key,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spawn", response_model=SpawnResponse)
async def spawn_task(request: SpawnRequest):
    """Spawn a background task."""
    agent = get_agent()
    
    try:
        result = await agent.spawn_background_task(
            task=request.task,
            label=request.label,
        )
        return SpawnResponse(status="ok", message=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule", response_model=ScheduleResponse)
async def schedule_task(request: ScheduleRequest):
    """Schedule a recurring task."""
    agent = get_agent()
    
    try:
        job = agent.schedule_task(
            name=request.name,
            message=request.message,
            cron_expr=request.cron_expr,
            every_seconds=request.every_seconds,
        )
        return ScheduleResponse(
            id=job["id"],
            name=job["name"],
            next_run=job["next_run"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory", response_model=MemoryResponse)
async def get_memory(days: int = 7):
    """Get the agent's memory context."""
    agent = get_agent()
    
    return MemoryResponse(
        context=agent.get_memory_context(),
        recent_days=days,
    )


@router.post("/memory")
async def save_memory(content: str):
    """Save content to today's memory."""
    agent = get_agent()
    agent.save_memory(content)
    return {"status": "ok", "message": "Memory saved"}


@router.get("/skills", response_model=SkillsResponse)
async def list_skills():
    """List all available skills."""
    agent = get_agent()
    skills = agent.list_skills()
    
    return SkillsResponse(
        skills=[SkillInfo(**s) for s in skills],
        count=len(skills),
    )


@router.get("/skills/{name}")
async def get_skill(name: str):
    """Get a specific skill's content."""
    agent = get_agent()
    content = agent.load_skill(name)
    
    if content is None:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    
    return {"name": name, "content": content}


@router.get("/cron", response_model=CronListResponse)
async def list_cron_jobs():
    """List all scheduled jobs."""
    agent = get_agent()
    jobs = agent.cron.list_jobs(include_disabled=True)
    
    return CronListResponse(
        jobs=[
            CronJobInfo(
                id=j.id,
                name=j.name,
                enabled=j.enabled,
                next_run_at_ms=j.state.next_run_at_ms,
                last_status=j.state.last_status,
            )
            for j in jobs
        ],
        count=len(jobs),
    )


@router.delete("/cron/{job_id}")
async def remove_cron_job(job_id: str):
    """Remove a scheduled job."""
    agent = get_agent()
    removed = agent.cron.remove_job(job_id)
    
    if not removed:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    return {"status": "ok", "message": f"Job {job_id} removed"}


@router.get("/status")
async def get_status():
    """Get the hybrid agent's status."""
    agent = get_agent()
    
    return {
        "agent": "HybridAgentBrain",
        "version": "1.0.0",
        "workspace": str(agent.workspace),
        "skills_count": len(agent.list_skills()),
        "cron_status": agent.cron.status(),
        "running_subagents": agent.agent_loop.subagents.get_running_count(),
    }
