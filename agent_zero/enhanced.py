"""
Agent Zero Enhanced - NanoBot-Powered Brain

This module enhances Agent Zero's chat capabilities with NanoBot features:
- Memory context injection (daily notes + long-term)
- Skills loading for specialized tasks
- Background task spawning (subagents)
- Scheduled research jobs (cron)

Agent Zero remains the main brain - NanoBot provides the enhancements.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

from loguru import logger


class AgentZeroEnhanced:
    """
    Enhanced Agent Zero with NanoBot capabilities.
    
    This class wraps Agent Zero's chat with NanoBot's:
    - Memory system (context injection)
    - Skills loader (specialized capabilities)
    - Subagent spawning (background tasks)
    """
    
    _instance = None
    
    def __init__(self, workspace_path: str = "./workspace/agent_zero"):
        self.workspace = Path(workspace_path)
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # Lazy-load NanoBot components
        self._memory = None
        self._skills = None
        self._sessions = None
        
        logger.info(f"Agent Zero Enhanced initialized at {self.workspace}")
    
    @classmethod
    def get_instance(cls) -> "AgentZeroEnhanced":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @property
    def memory(self):
        """Get NanoBot memory store (lazy loaded)."""
        if self._memory is None:
            try:
                from nanobot.agent.memory import MemoryStore
                self._memory = MemoryStore(self.workspace)
            except ImportError:
                logger.error("NanoBot memory module not found. Please ensure NanoBot is installed.")
                raise RuntimeError("NanoBot memory system unavailable.")
        return self._memory
    
    @property
    def skills(self):
        """Get NanoBot skills loader (lazy loaded)."""
        if self._skills is None:
            try:
                from nanobot.agent.skills import SkillsLoader
                self._skills = SkillsLoader(self.workspace)
            except ImportError:
                logger.error("NanoBot skills module not found. Please ensure NanoBot is installed.")
                raise RuntimeError("NanoBot skills system unavailable.")
        return self._skills
    
    def build_enhanced_prompt(self, user_message: str) -> str:
        """
        Build an enhanced prompt with NanoBot context.
        
        Injects:
        - Memory context (what the agent remembers)
        - Skills summary (what the agent can do)
        - PhD research context
        """
        parts = []
        
        # System preamble
        # System preamble
        parts.append("""You are Agent Zero, the AI brain of BioDockify - a PhD-level pharmaceutical research assistant.

You have access to the following capabilities through your tools:
- System Administration (Read/Write Files, Execute Commands)
- Literature search (PubMed, Google Scholar)
- Paper analysis and summarization
- Knowledge graph navigation
- Statistical analysis
- Thesis generation

Respond helpfully, accurately, and concisely. Use scientific terminology when appropriate.
If asked to fix a system issue (like a config file), USE YOUR TOOLS to fix it.""")
        
        # Memory context
        if self.memory:
            memory_context = self.memory.get_memory_context()
            if memory_context:
                parts.append(f"\n<memory>\n{memory_context}\n</memory>")
        
        # Skills summary
        if self.skills:
            skills_summary = self.skills.build_skills_summary()
            if skills_summary:
                parts.append(f"\n<skills>\n{skills_summary}\n</skills>")
        
        # User message
        parts.append(f"\n<user_message>\n{user_message}\n</user_message>")
        
        return "\n".join(parts)
    
    def save_to_memory(self, content: str) -> None:
        """Save important information to memory."""
        if self.memory:
            self.memory.append_today(content)
    
    def get_memory_context(self) -> str:
        """Get current memory context."""
        if self.memory:
            return self.memory.get_memory_context()
        return ""
    
    def list_skills(self) -> list:
        """List available skills."""
        if self.skills:
            return self.skills.list_skills()
        return []
    
    async def spawn_background_task(self, task: str, label: Optional[str] = None) -> str:
        """Spawn a background research task."""
        try:
            from nanobot.agent.subagent import SubagentManager
            from nanobot.bus.queue import MessageBus
            from nanobot.providers.litellm_provider import LiteLLMProvider
            
            # Get provider from config
            from runtime.config_loader import load_config
            cfg = load_config()
            ai_config = cfg.get("ai_provider", {})
            
            provider = LiteLLMProvider(
                api_key=ai_config.get("api_key") or ai_config.get("openrouter_key"),
                default_model=ai_config.get("model", "anthropic/claude-sonnet-4-5")
            )
            
            bus = MessageBus()
            manager = SubagentManager(
                provider=provider,
                workspace=self.workspace,
                bus=bus,
            )
            
            result = await manager.spawn(task, label)
            return result
        except Exception as e:
            logger.error(f"Failed to spawn background task: {e}")
            return f"Error spawning task: {e}"


def get_agent_zero_enhanced() -> AgentZeroEnhanced:
    """Get the enhanced Agent Zero instance."""
    return AgentZeroEnhanced.get_instance()
