"""
Hybrid Message Bus - Asynchronous pub/sub for NanoBot/SurfSense channels.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

@dataclass
class InboundMessage:
    """Message received from a channel (e.g. Telegram)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    source: str = "unknown" # e.g. "telegram"
    sender_id: str = "unknown"
    sender_name: str = "Anonymous"
    chat_id: str = "" # Channel-specific chat ID
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class OutboundMessage:
    """Message sent back to a channel."""
    content: str
    target: str # e.g. "telegram"
    chat_id: str
    reply_to_id: Optional[str] = None
    media_url: Optional[str] = None
    
class MessageBus:
    """
    Async message bus processing inbound and outbound queues.
    """
    
    def __init__(self):
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()
        self._subscribers = []
        self._running = False
        
    async def start(self):
        self._running = True
        
    async def stop(self):
        self._running = False
        
    async def push_inbound(self, message: InboundMessage):
        await self.inbound.put(message)
        
    async def push_outbound(self, message: OutboundMessage):
        await self.outbound.put(message)
        # Notify subscribers (channels)
        for callback in self._subscribers:
            asyncio.create_task(callback(message))
            
    def subscribe(self, callback):
        """Subscribe to outbound messages."""
        self._subscribers.append(callback)
