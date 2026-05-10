"""
Research Router
Handles research task management and real-time updates.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from pydantic import BaseModel
import json

import logging
logger = logging.getLogger(__name__)

# Import Orchestrator
try:
    from orchestration.planner.orchestrator import ResearchOrchestrator, OrchestratorConfig
    HAS_ORCHESTRATOR = True
except ImportError as e:
    logger.warning(f"Research orchestrator not available: {e}")
    ResearchOrchestrator = None
    HAS_ORCHESTRATOR = False

router = APIRouter()

# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    title: str
    mode: str = "local"  # "local" or "cloud"

class TaskResponse(BaseModel):
    success: bool
    message: str
    task_id: str

class TaskStatus(BaseModel):
    task_id: str
    title: Optional[str] = None
    status: str  # pending, running, completed, failed
    progress: int
    logs: List[str]
    result: Optional[dict] = None
    created_at: str

# -----------------------------------------------------------------------------
# State & WebSocket Manager
# -----------------------------------------------------------------------------

class ConnectionManager:
    """Thread-safe WebSocket connection manager."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        async with self._lock:
            connections = self.active_connections.copy()
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Connection may have closed, remove it
                await self.disconnect(connection)

manager = ConnectionManager()

# Agent Thinking State (for real-time status UI)
class AgentThinkingState:
    """Tracks agent reasoning and execution state for UI display."""
    
    def __init__(self):
        self.current_task: Optional[str] = None
        self.current_step: int = 0
        self.total_steps: int = 0
        self.thinking_traces: List[Dict] = []
        self.execution_log: List[Dict] = []
        self.is_running: bool = False
        self.progress_percent: int = 0
        
    def start_task(self, task_name: str, total_steps: int = 1):
        self.current_task = task_name
        self.total_steps = total_steps
        self.current_step = 0
        self.is_running = True
        self.thinking_traces = []
        self.execution_log = []
        self.progress_percent = 0
        
    def add_thinking(self, step: str, reasoning: str):
        self.thinking_traces.append({
            "step": step,
            "reasoning": reasoning,
            "timestamp": datetime.now().isoformat()
        })
        
    def log_execution(self, action: str, status: str, details: Optional[dict] = None):
        self.execution_log.append({
            "action": action,
            "status": status,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
        
    def advance_step(self):
        self.current_step += 1
        if self.total_steps > 0:
            self.progress_percent = min(100, int(self.current_step / self.total_steps * 100))
            
    def complete(self):
        self.is_running = False
        self.progress_percent = 100
        
    def get_status(self) -> dict:
        return {
            "current_task": self.current_task,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress_percent": self.progress_percent,
            "is_running": self.is_running,
            "latest_thinking": self.thinking_traces[-1] if self.thinking_traces else None,
            "recent_log": self.execution_log[-5:] if self.execution_log else []
        }

agent_state = AgentThinkingState()

# Persistent task store (SQLite-backed for production reliability)
from runtime.task_store import get_task_store, TaskStore

async def get_task_dict(task_id: str) -> dict:
    """Helper to get task dict ensuring it exists."""
    store = get_task_store()
    task = await store.get_task(task_id)
    if not task:
         # Fallback empty if deleted during run
         return {"task_id": task_id, "status": "unknown", "logs": []}
    return task

# -----------------------------------------------------------------------------
# Background Task Logic
# -----------------------------------------------------------------------------

async def run_research_task(task_id: str, title: str, mode: str):
    """
    Executes the research orchestration in the background and streams updates.
    """
    store = get_task_store()
    
    # 1. Init
    await store.update_task(task_id, status="running")
    await store.append_log(task_id, f"Starting research on: {title} (Mode: {mode})")
    
    # Initialize agent thinking state for real-time UI updates
    agent_state.start_task(f"Research: {title}", total_steps=5)
    agent_state.add_thinking("Initialization", f"Starting {mode} research on topic: {title}")
    agent_state.log_execution("task_init", "success", {"task_id": task_id, "mode": mode})
    
    await manager.broadcast({
        "type": "task_update",
        "data": await get_task_dict(task_id)
    })

    try:
        from runtime.config_loader import load_config
        config = load_config()
        
        if mode == "local":
            try:
                await store.append_log(task_id, "Initializing MiroThinker Web Engine...")
                try:
                    from modules.web_research.engine import WebResearchEngine
                    engine = WebResearchEngine(config)
                    HAS_WEB_ENGINE = True
                except ImportError:
                    logger.error("WebResearchEngine not found in modules.web_research.engine")
                    HAS_WEB_ENGINE = False
                    
                if not HAS_WEB_ENGINE:
                    await store.update_task(task_id, status="failed")
                    await store.append_log(task_id, "CRITICAL: Web research engine module missing. Deep search unavailable.")
                    await manager.broadcast({"type": "task_update", "data": await get_task_dict(task_id)})
                    return

                # Step 1: Search
                await store.update_task(task_id, progress=10)
                await store.append_log(task_id, f"Searching web for: {title}...")
                await manager.broadcast({"type": "task_update", "data": await get_task_dict(task_id)})
                
                # Run async search directly
                results = await engine.search_google(title, 5)
                await store.append_log(task_id, f"Found {len(results)} relevant sources.")
                
                # Step 2: Deep Read
                await store.update_task(task_id, progress=30)
                await store.append_log(task_id, "Deep reading and scraping content...")
                await manager.broadcast({"type": "task_update", "data": await get_task_dict(task_id)})
                
                full_context = ""
                for i, res in enumerate(results):
                    msg = f"Reading: {res.get('title', 'Unknown')}"
                    await store.append_log(task_id, msg)
                    
                    # Update agent thinking state
                    agent_state.add_thinking("Deep Reading", f"Extracting content from: {res.get('title', 'Unknown')[:50]}...")
                    agent_state.advance_step()
                    
                    content = await engine.deep_read(res['link'])
                    full_context += f"# Source: {res['title']}\nURL: {res['link']}\n\n{content}\n\n"
                    
                    # Update progress
                    current_prog = 30 + int((i+1)/len(results) * 40) # 30 to 70
                    await store.update_task(task_id, progress=current_prog)
                    agent_state.log_execution("deep_read", "success", {"source": res.get('title', '')[:30]})
                    await manager.broadcast({"type": "task_update", "data": await get_task_dict(task_id)})
                
                # Step 3: Synthesis with LLM
                await store.update_task(task_id, progress=80)
                await store.append_log(task_id, "Synthesizing research report with AI...")
                agent_state.add_thinking("Synthesis", "Generating comprehensive research report using AI analysis...")
                agent_state.advance_step()
                await manager.broadcast({"type": "task_update", "data": await get_task_dict(task_id)})
                
                try:
                    # Get Primary LLM
                    from modules.llm.factory import LLMFactory
                    
                    ai_cfg = config.get("ai_provider", {})
                    
                    # Simple object mock for factory
                    class MockConfig:
                        def __init__(self, cfg):
                            self.google_key = cfg.get("google_key")
                            self.openrouter_key = cfg.get("openrouter_key")
                            self.huggingface_key = cfg.get("huggingface_key")
                            self.glm_key = cfg.get("glm_key")
                            self.custom_key = cfg.get("custom_key")
                            self.custom_base_url = cfg.get("custom_base_url")
                            self.custom_model = cfg.get("custom_model")
                            self.ollama_url = cfg.get("ollama_url")
                            self.ollama_model = cfg.get("ollama_model")
                            self.primary_model = cfg.get("primary_model", "google")

                    adapter = LLMFactory.get_adapter(ai_cfg.get("primary_model", "google"), MockConfig(ai_cfg))
                    
                    if adapter:
                        prompt = f"""
                        You are an expert research analyst. Synthesize the following raw web search data into a comprehensive research report about "{title}".
                        
                        Structure:
                        1. Executive Summary
                        2. Key Findings
                        3. Detailed Analysis
                        4. Sources Analysis
                        
                        RAW DATA:
                        {full_context[:50000]}
                        """
                        
                        # Use async_generate if available, else run in thread
                        if hasattr(adapter, 'async_generate'):
                            report = await adapter.async_generate(prompt)
                        else:
                            report = await asyncio.to_thread(adapter.generate, prompt)
                        await store.append_log(task_id, "Report generation complete.")
                    else:
                        report = f"## Research Analysis\n\nAI Synthesis Failed: No valid AI provider configured.\n\n### Raw Data\n{full_context}"
                        await store.append_log(task_id, "AI generation skipped (no provider).")

                except Exception as e:
                    await store.append_log(task_id, f"AI Synthesis Error: {e}")
                    report = f"## Research Analysis\n\nError during synthesis: {e}\n\n### Raw Data\n{full_context}"

                # For now, we save raw context + report
                results_data = {
                    "summary": "Deep Web Research Complete",
                    "sources": results,
                    "full_report": report,
                    "raw_context": full_context
                }
                await store.update_task(task_id, result=results_data)
                
                # --- Bridge to RAG / Notebook (Bug #2) ---
                try:
                    from modules.rag.ingestor import ingestor
                    from modules.rag.vector_store import get_vector_store
                    from modules.library.store import library_store
                    import tempfile
                    
                    await store.append_log(task_id, "Ingesting report into knowledge base for Notebook access...")
                    
                    # Save report as file in library
                    report_filename = f"research_{task_id}.md"
                    report_text = f"# Research: {title}\n\n{report}\n\n## Raw Context Source\n{full_context[:10000]}"
                    record = library_store.add_file(report_text.encode("utf-8"), report_filename, meta={"task_id": task_id, "topic": title, "type": "research_report"})
                    
                    # Ingest into vector store
                    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.md') as tmp:
                        tmp.write(report_text.encode("utf-8"))
                        tmp.close()
                        chunks = ingestor.ingest_file(tmp.name)
                        
                    if chunks:
                        await get_vector_store().add_documents(chunks)
                        await store.append_log(task_id, f"Ingested {len(chunks)} chunks into knowledge base.")
                    else:
                        await store.append_log(task_id, "Warning: Could not extract chunks from report for indexing.")
                except Exception as e:
                    logger.error(f"Failed to bridge research to RAG: {e}")
                    await store.append_log(task_id, f"Warning: RAG indexing failed: {e}")

            except Exception as e:
                logger.error(f"Web research task failed: {e}")
                await store.update_task(task_id, status="failed")
                await store.append_log(task_id, f"Deep Research Error: {str(e)}")
                await manager.broadcast({"type": "task_update", "data": await get_task_dict(task_id)})
                return
            
        else:
            # 2. Standard Research (Real Orchestrator)
            if ResearchOrchestrator and HAS_ORCHESTRATOR:
                await store.append_log(task_id, "Executing Research Orchestrator...")
                try:
                    orch = ResearchOrchestrator()
                    # Generate Plan
                    plan = await orch.plan_research(title, mode, task_id=task_id)
                    
                    if not plan or not plan.steps:
                        raise ValueError("Failed to generate research plan.")
                        
                    await store.append_log(task_id, f"Plan generated with {len(plan.steps)} steps.")
                    
                    # Real Execution via Executor
                    from orchestration.executor import ResearchExecutor
                    executor = ResearchExecutor(task_id=task_id)
                    
                    # Execute Plan (Handles logging and progress internally)
                    context = await executor.execute_plan(plan)
                    
                    # Update Result
                    result_payload = {
                        "summary": f"Research on {title} complete.",
                        "entities": context.entities,
                        "stats": context.analyst_stats,
                        "papers_found": len(context.known_papers)
                    }
                    await store.update_task(task_id, result=result_payload)
                    
                    # Bridge to RAG
                    try:
                        from modules.rag.ingestor import ingestor
                        from modules.rag.vector_store import get_vector_store
                        from modules.library.store import library_store
                        
                        await store.append_log(task_id, "Persisting findings to Knowledge Base...")
                        findings_text = f"# Research: {title}\n\n## Abstract Context\n{context.extracted_text[:10000]}\n\n## Analytics\n{json.dumps(context.analyst_stats, indent=2)}"
                        
                        report_filename = f"research_results_{task_id}.md"
                        record = library_store.add_file(findings_text.encode("utf-8"), report_filename, meta={"task_id": task_id, "topic": title})
                        
                        file_path = library_store.get_file_path(record['id'])
                        chunks = ingestor.ingest_file(str(file_path))
                        if chunks:
                            get_vector_store().add_documents(chunks)
                    except Exception as bridge_err:
                        logger.warning(f"RAG bridge failed: {bridge_err}")
                        await store.append_log(task_id, f"RAG bridge failed: {bridge_err}")

                except Exception as e:
                    logger.error(f"Orchestration failed: {e}")
                    await store.append_log(task_id, f"Execution Error: {e}")
                    await store.update_task(task_id, status="failed")
                    return
            else:
                # Fallback to simulation if no orchestrator
                await store.append_log(task_id, "Using standard simulation (Orchestrator unavailable).")
        
        # 3. Complete
        await store.update_task(task_id, status="completed", progress=100)
        await store.append_log(task_id, "Research completed successfully.")
        
        # Ensure result exists if not set
        task_curr = await get_task_dict(task_id)
        if not task_curr.get("result"):
             await store.update_task(task_id, result={"summary": f"Research on {title} complete.", "plan_id": "plan_123"})
        
        await manager.broadcast({
            "type": "task_update",
            "data": await get_task_dict(task_id)
        })

    except Exception as e:
        await store.update_task(task_id, status="failed")
        await store.append_log(task_id, f"Error: {str(e)}")
        await manager.broadcast({
            "type": "task_update",
            "data": await get_task_dict(task_id)
        })

# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.post("/start", response_model=TaskResponse)
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Start a new research task."""
    # Try Phase 10 Integrated System first (Agent Zero)
    try:
        from modules.integration.integrated_system import get_integrated_system
        integrated = get_integrated_system()
        
        if integrated:
            logger.info(f"Routing research request '{request.title}' through Agent Zero (Integrated System)")
            task_id = await integrated.create_research_task(
                query=request.title,
                use_deep_research=True # Default to deep research for Agent Zero
            )
            
            return TaskResponse(
                success=True,
                message="Research task orchestrated by Agent Zero started successfully",
                task_id=task_id
            )
    except Exception as e:
        logger.warning(f"Fallback to legacy research: Integrated System error: {e}")

    # Legacy / Fallback Research Path
    task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    # Create task record in async store
    try:
        await get_task_store().create_task(task_id, request.title, request.mode)
        
        # Start background execution
        background_tasks.add_task(run_research_task, task_id, request.title, request.mode)
        
        return TaskResponse(
            success=True,
            message="Research task started successfully (Legacy Mode)",
            task_id=task_id
        )
    except Exception as e:
        logger.error(f"Failed to start research task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start task: {e}")

@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get status of a specific task."""
    task = await get_task_store().get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/tasks", response_model=List[TaskStatus])
async def list_tasks():
    """List all tasks."""
    return await get_task_store().list_tasks()

@router.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time task updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for client messages if any (ping/pong)
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@router.websocket("/ws/agent-thinking")
async def agent_thinking_stream(websocket: WebSocket):
    """
    WebSocket for real-time agent thinking traces.
    Clients receive status updates every second while the agent is running.
    """
    await websocket.accept()
    try:
        while True:
            status = agent_state.get_status()
            await websocket.send_json({
                "type": "agent_status",
                "data": status
            })
            await asyncio.sleep(1)  # Send updates every second
    except WebSocketDisconnect:
        pass  # Client disconnected


@router.get("/agent-status")
async def get_agent_status():
    """Get current agent execution status (polling alternative to WebSocket)."""
    return agent_state.get_status()
