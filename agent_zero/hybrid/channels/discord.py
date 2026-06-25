"""
Discord Channel - Integration with Discord Bot API.
"""
import logging
import asyncio
from agent_zero.hybrid.channels.base import BaseChannel
from agent_zero.hybrid.bus import MessageBus, OutboundMessage

logger = logging.getLogger(__name__)

class DiscordChannel(BaseChannel):
    """Discord Bot integration."""
    
    def __init__(self, bus: MessageBus, config: dict):
        super().__init__("discord", bus, config)
        self.token = config.get("token", "")
        self.client = None
        
    async def _connect(self):
        if not self.token:
            logger.error("Discord token missing!")
            self.enabled = False
            return
            
        try:
            import discord
            
            intents = discord.Intents.default()
            intents.messages = True
            intents.message_content = True
            
            self.client = discord.Client(intents=intents)
            
            @self.client.event
            async def on_ready():
                logger.info(f"Discord connected as {self.client.user}")
                
            @self.client.event
            async def on_message(message):
                if message.author == self.client.user:
                    return
                    
                await self.process_incoming(
                    content=message.content,
                    sender_id=str(message.author.id),
                    sender_name=message.author.name,
                    chat_id=str(message.channel.id),
                    raw_data={"guild_id": getattr(message.guild, "id", None)}
                )
                
            # Start client in background task
            asyncio.create_task(self.client.start(self.token))
            
        except ImportError:
            logger.error("discord.py not installed. Discord channel disabled.")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to init Discord: {e}")
            self.enabled = False
            
    async def _disconnect(self):
        if self.client:
            await self.client.close()
            
    async def send_message(self, message: OutboundMessage):
        if not self.client:
            return
            
        try:
            channel = self.client.get_channel(int(message.chat_id))
            if channel:
                await channel.send(message.content)
            else:
                logger.warning(f"Discord channel {message.chat_id} not found")
        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")
