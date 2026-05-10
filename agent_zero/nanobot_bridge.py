"""
NanoBot Bridge - Hybrid Integration Layer for Agent Zero + NanoBot

This module connects NanoBot's ultra-lightweight agent capabilities with
BioDockify's PhD-focused Agent Zero orchestrator, creating a powerful hybrid.

Features Integrated from NanoBot:
- Memory System (daily notes + long-term MEMORY.md)
- Skills Loader (SKILL.md with frontmatter)
- Subagent Spawning (background task execution)
- Cron Service (scheduled research tasks)
- Multi-Channel Messaging (Telegram, Discord, WhatsApp)
- LiteLLM Multi-Provider (10+ LLM backends)

Author: BioDockify Team
"""

import asyncio
from pathlib import Path
from typing import Any, Optional

from loguru import logger

# NanoBot imports
from nanobot.agent.loop import AgentLoop
from nanobot.agent.memory import PersistentMemory
from nanobot.agent.skills import SkillsLoader
from nanobot.agent.subagent import SubagentManager
from nanobot.bus.queue import MessageBus
from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule
from nanobot.session.manager import SessionManager

# Agent Zero imports
from agent_zero.core.orchestrator import AgentZero, ToolRegistry, Tool


class HybridAgentBrain:
    """
    Hybrid Agent Zero + NanoBot Brain.
    
    Combines:
    - Agent Zero: PhD research orchestration, tool registry, persistent memory
    - NanoBot: Lightweight agent loop, skills, cron, multi-channel messaging
    """
    
    def __init__(
        self,
        workspace: Path,
        llm_provider: Optional[LiteLLMProvider] = None,
        api_key: Optional[str] = None,
        model: str = "anthropic/claude-sonnet-4-5",
        brave_api_key: Optional[str] = None,
    ):
        self.workspace = workspace
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # Initialize LiteLLM Provider (unified multi-provider)
        self.provider = llm_provider or LiteLLMProvider(
            api_key=api_key,
            default_model=model,
        )
        
        # Initialize Message Bus (for async communication)
        self.bus = MessageBus()
        
        # Initialize NanoBot Memory (daily notes + long-term)
        self.memory = PersistentMemory(workspace)
        
        # Initialize Skills Loader
        self.skills = SkillsLoader(workspace)
        
        # Initialize Session Manager
        self.sessions = SessionManager(workspace)
        
        # Initialize Cron Service
        self.cron = CronService(
            store_path=workspace / "cron_jobs.json",
            on_job=self._execute_cron_job,
        )
        
        # Initialize Agent Loop
        self.agent_loop = AgentLoop(
            bus=self.bus,
            provider=self.provider,
            workspace=workspace,
            model=model,
            brave_api_key=brave_api_key,
            cron_service=self.cron,
        )
        
        # Track running state
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        
        logger.info(f"Hybrid Agent Brain initialized at {workspace}")
    
    async def start(self) -> None:
        """Start the hybrid agent (agent loop + cron service)."""
        if self._running:
            return
        
        self._running = True
        
        # Start cron service
        await self.cron.start()
        
        # Start agent loop in background
        self._loop_task = asyncio.create_task(self.agent_loop.run())
        
        logger.info("Hybrid Agent Brain started")
    
    async def stop(self) -> None:
        """Stop the hybrid agent."""
        self._running = False
        
        # Stop agent loop
        self.agent_loop.stop()
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        
        # Stop cron service
        self.cron.stop()
        
        logger.info("Hybrid Agent Brain stopped")
    
    async def chat(
        self,
        message: str,
        session_key: str = "default",
        channel: str = "api",
    ) -> str:
        """
        Send a message to the agent and get a response.
        
        This uses NanoBot's efficient agent loop for processing.
        """
        response = await self.agent_loop.process_direct(
            content=message,
            session_key=f"{channel}:{session_key}",
            channel=channel,
            chat_id=session_key,
        )
        return response
    
    async def spawn_background_task(
        self,
        task: str,
        label: Optional[str] = None,
    ) -> str:
        """Spawn a background subagent to handle a task."""
        return await self.agent_loop.subagents.spawn(
            task=task,
            label=label,
            origin_channel="api",
            origin_chat_id="background",
        )
    
    def schedule_task(
        self,
        name: str,
        message: str,
        cron_expr: Optional[str] = None,
        every_seconds: Optional[int] = None,
    ) -> dict:
        """
        Schedule a recurring task.
        
        Args:
            name: Human-readable name for the job.
            message: The message/task to execute when triggered.
            cron_expr: Cron expression (e.g., "0 9 * * *" for 9am daily).
            every_seconds: Run every N seconds (alternative to cron_expr).
        """
        if cron_expr:
            schedule = CronSchedule(kind="cron", expr=cron_expr)
        elif every_seconds:
            schedule = CronSchedule(kind="every", every_ms=every_seconds * 1000)
        else:
            raise ValueError("Must provide cron_expr or every_seconds")
        
        job = self.cron.add_job(
            name=name,
            schedule=schedule,
            message=message,
        )
        
        return {
            "id": job.id,
            "name": job.name,
            "next_run": job.state.next_run_at_ms,
        }
    
    async def _execute_cron_job(self, job) -> Optional[str]:
        """Execute a cron job by sending its message to the agent."""
        logger.info(f"Executing cron job: {job.name}")
        return await self.chat(
            message=job.payload.message,
            session_key=f"cron:{job.id}",
            channel="cron",
        )
    
    # ========== Memory Methods ==========
    
    def save_memory(self, content: str) -> None:
        """Save content to today's memory notes."""
        self.memory.append_today(content)
    
    def get_memory_context(self) -> str:
        """Get formatted memory context for prompts."""
        return self.memory.get_memory_context()
    
    def get_recent_memories(self, days: int = 7) -> str:
        """Get memories from the last N days."""
        return self.memory.get_recent_memories(days)
    
    # ========== Skills Methods ==========
    
    def list_skills(self) -> list[dict]:
        """List all available skills."""
        return self.skills.list_skills()
    
    def load_skill(self, name: str) -> Optional[str]:
        """Load a specific skill's content."""
        return self.skills.load_skill(name)
    
    def get_skills_summary(self) -> str:
        """Get XML summary of all skills for agent context."""
        return self.skills.build_skills_summary()


# ========== Factory Function ==========

def create_hybrid_agent(
    workspace_path: str = "./workspace",
    api_key: Optional[str] = None,
    model: str = "anthropic/claude-sonnet-4-5",
    brave_api_key: Optional[str] = None,
) -> HybridAgentBrain:
    """
    Factory function to create a Hybrid Agent Brain.
    
    Args:
        workspace_path: Path to the agent's workspace directory.
        api_key: LLM API key (OpenRouter, Anthropic, etc.).
        model: Model identifier (e.g., "anthropic/claude-sonnet-4-5").
        brave_api_key: Optional Brave Search API key for web search.
    
    Returns:
        A configured HybridAgentBrain instance.
    """
    return HybridAgentBrain(
        workspace=Path(workspace_path),
        api_key=api_key,
        model=model,
        brave_api_key=brave_api_key,
    )
