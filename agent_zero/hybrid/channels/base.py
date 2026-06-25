"""
Base Channel - Abstract base class for all communication channels.
"""
from abc import ABC, abstractmethod
import logging
from typing import Optional, List
from agent_zero.hybrid.bus import MessageBus, InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)

class BaseChannel(ABC):
    """
    Abstract interface for channels (Telegram, Discord, etc).
    """
    
    def __init__(self, name: str, bus: MessageBus, config: dict):
        self.name = name
        self.bus = bus
        self.config = config
        self.enabled = config.get("enabled", False)
        
    async def start(self):
        """Start the channel listener."""
        if not self.enabled:
            logger.info(f"Channel {self.name} is disabled.")
            return
            
        logger.info(f"Starting channel: {self.name}")
        # Subscribe to bus to receive outbound messages targeting this channel
        self.bus.subscribe(self._handle_outbound)
        await self._connect()
        
    async def stop(self):
        """Stop the channel."""
        if not self.enabled:
            return
        await self._disconnect()
        logger.info(f"Stopped channel: {self.name}")
        
    async def _handle_outbound(self, message: OutboundMessage):
        """Handle message from agent to user."""
        if message.target != self.name:
            return
            
        try:
            await self.send_message(message)
        except Exception as e:
            logger.error(f"Error sending to {self.name}: {e}")
            
    async def process_incoming(self, content: str, sender_id: str, sender_name: str, chat_id: str, raw_data: dict = None):
        """Push incoming message to bus."""
        msg = InboundMessage(
            content=content,
            source=self.name,
            sender_id=sender_id,
            sender_name=sender_name,
            chat_id=chat_id,
            raw_data=raw_data or {}
        )
        await self.bus.push_inbound(msg)
        
    @abstractmethod
    async def _connect(self):
        """Connect to the external service."""
        pass
        
    @abstractmethod
    async def _disconnect(self):
        """Disconnect from external service."""
        pass
        
    @abstractmethod
    async def send_message(self, message: OutboundMessage):
        """Send message to external service."""
        pass
