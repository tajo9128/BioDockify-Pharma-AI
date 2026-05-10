"""
Broadcaster Utility - BioDockify NanoBot
Handles cross-platform status updates and notifications.
"""
import logging
import asyncio
from typing import Optional, Dict, Any
from nanobot.agent.tools.communication import EmailTool
from nanobot.agent.tools.discord import DiscordTool

logger = logging.getLogger("nanobot.broadcaster")

class StatusBroadcaster:
    """
    Dispatches notifications across various channels:
    - In-app (WebSocket)
    - Telegram
    - Discord
    - Email
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.email_tool = EmailTool()
        self.discord_tool = DiscordTool()
        # Telegram will be handled via python-telegram-bot or direct webhook
        
    async def broadcast_status(self, message: str, title: str = "Research Update"):
        """Send a message to all configured channels."""
        logger.info(f"Broadcasting: {message}")
        
        # 1. Internal Log
        logger.info(f"[BROADCAST] {title}: {message}")
        
        # 2. Discord (If configured)
        try:
            # Assuming channel_id is in config or environment
            discord_channel = self.config.get("discord_channel_id")
            if discord_channel:
                 await self.discord_tool.execute(channel_id=discord_channel, message=f"**{title}**\n{message}")
        except Exception as e:
            logger.warning(f"Discord broadcast failed: {e}")

        # 3. Email (If high importance)
        if "Critical" in title or "Failed" in title:
            try:
                recipient = self.config.get("admin_email")
                if recipient:
                    await self.email_tool.execute(to=recipient, subject=title, body=message)
            except Exception as e:
                logger.warning(f"Email broadcast failed: {e}")

        # 4. Telegram (Placeholder for now)
        # TODO: Implement telegram bot sender
        
    async def notify_stage_transition(self, task_id: str, old_stage: str, new_stage: str):
        """Specifically notify about research stage transitions."""
        msg = f"Task {task_id} transitioned from {old_stage} to {new_stage}."
        await self.broadcast_status(msg, title="🔬 Stage Transition")

    async def notify_completion(self, task_id: str, title: str, result_summary: str):
        """Notify user of task completion."""
        msg = f"Task '{title}' (ID: {task_id}) is complete.\n\nSummary:\n{result_summary}"
        await self.broadcast_status(msg, title="✅ Research Complete")
