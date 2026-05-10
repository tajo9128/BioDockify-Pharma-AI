"""
MonitoredNanoBotCoordinator - Prometheus-instrumented wrapper for NanoBot Hybrid Brain.
Tracks active subagents and skill usage metrics.
"""

import logging
from typing import Dict, Any, Optional
from prometheus_client import Counter, Gauge
from pathlib import Path

from agent_zero.nanobot_bridge import HybridAgentBrain

logger = logging.getLogger("BioDockify.MonitoredNanoBot")

class MonitoredNanoBotCoordinator:
    """
    NanoBot with monitoring while keeping all features.
    """
    
    def __init__(self, workspace_path: str, config: Dict[str, Any]):
        # Initialize original NanoBot Hybrid Brain
        self.brain = HybridAgentBrain(
            workspace=Path(workspace_path),
            api_key=config.get("api_key"),
            model=config.get("model", "anthropic/claude-sonnet-4-5"),
            brave_api_key=config.get("brave_api_key")
        )
        
        # Setup metrics
        self._setup_metrics()
    
    def _setup_metrics(self):
        """Setup NanoBot metrics."""
        try:
            # Current active subagent count
            self.bot_count = Gauge(
                'nanobot_active_count',
                'Number of active NanoBots'
            )
            
            # Total coordinations (chat requests)
            self.coordination_counter = Counter(
                'nanobot_coordinations_total',
                'Total NanoBot coordinations',
                ['result']
            )
            
            # Skill usage tracking
            self.skill_usage = Counter(
                'nanobot_skill_usage_total',
                'Skill usage by NanoBots',
                ['skill', 'status']
            )
        except ValueError:
            # Metrics already registered (e.g. during tests or hot reload)
            from prometheus_client import REGISTRY
            self.bot_count = REGISTRY._names_to_collectors['nanobot_active_count']
            self.coordination_counter = REGISTRY._names_to_collectors['nanobot_coordinations_total']
            self.skill_usage = REGISTRY._names_to_collectors['nanobot_skill_usage_total']
    
    async def chat(self, message: str, session_key: str = "default", channel: str = "api") -> str:
        """
        Coordinate NanoBot chat with monitoring.
        """
        # Update active bot count before processing
        if self.brain.agent_loop and self.brain.agent_loop.subagents:
            self.bot_count.set(self.brain.agent_loop.subagents.get_running_count())
            
        try:
            response = await self.brain.chat(
                message=message,
                session_key=session_key,
                channel=channel
            )
            self.coordination_counter.labels(result='success').inc()
            return response
            
        except Exception as e:
            self.coordination_counter.labels(result='failed').inc()
            logger.error(f"NanoBot chat failed: {e}")
            raise

    async def spawn_background_task(self, task: str, label: Optional[str] = None) -> str:
        """Spawn subagent with monitoring."""
        try:
            res = await self.brain.spawn_background_task(task, label)
            # Update gauge immediately
            if self.brain.agent_loop and self.brain.agent_loop.subagents:
                self.bot_count.set(self.brain.agent_loop.subagents.get_running_count())
            return res
        except Exception as e:
            logger.error(f"Failed to spawn NanoBot task: {e}")
            raise

    async def start(self):
        """Start underlying services."""
        await self.brain.start()
        
    async def stop(self):
        """Stop underlying services."""
        await self.brain.stop()

    def update_metrics(self):
        """Manually trigger metrics update (e.g. for background count)."""
        if self.brain.agent_loop and self.brain.agent_loop.subagents:
            self.bot_count.set(self.brain.agent_loop.subagents.get_running_count())
