"""
BioDockify AI - Single AI Engine using Agent Zero v1.9
Replaces Lite/Hybrid modes with single unified Agent Zero v1.9
"""

import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


class BioDockifyAI:
    """
    Single unified AI Controller for BioDockify.
    Uses Agent Zero v1.9 as the sole AI engine for all operations.
    """

    _instance = None
    _agent = None

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = BioDockifyAI()
        return cls._instance

    def __init__(self):
        self._agent = None
        self._init_done = False

    async def initialize(self, workspace_path: str = "./data/workspace"):
        """Initialize Agent Zero v1.9."""
        if self._init_done:
            return

        logger.info("Initializing BioDockify AI (Agent Zero v1.9)...")

        try:
            from agent_zero.agent_zero_v19 import Agent, AgentContext
            from agent_zero.helpers import dotenv

            self._agent = Agent(0)
            self._init_done = True
            logger.info("BioDockify AI (Agent Zero v1.9) Initialized Successfully.")
            return

        except Exception as e:
            logger.error(f"Failed to initialize Agent Zero v1.9: {e}")
            raise e

    async def process_chat(self, user_message: str, mode: str = "agent0") -> str:
        """
        Process user chat message using Agent Zero v1.9.
        Single mode - no Lite/Hybrid distinction.
        """
        if not self._agent:
            await self.initialize()

        logger.info(f"Agent Zero v1.9 processing: {user_message[:50]}...")

        try:
            from agent_zero.agent_zero_v19 import AgentContext

            context = AgentContext(config=self._agent.config)
            response = await self._agent.chat(user_message, context)
            return response

        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            return f"I encountered an error processing your request: {str(e)}"

    async def run_task(self, task: str):
        """Run an autonomous task."""
        if not self._agent:
            await self.initialize()

        response = await self.process_chat(task)
        return response


def get_biodockify_ai():
    return BioDockifyAI.get_instance()


AI = BioDockifyAI
