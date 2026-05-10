"""
Hybrid Agent Context - Combining Agent Zero's context management with NanoBot's simplicity.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict
import asyncio
import uuid
import random
import string
import logging

class AgentContextType(Enum):
    USER = "user"
    TASK = "task"
    BACKGROUND = "background"

@dataclass
class LoopData:
    """Data for current iteration of the agent loop."""
    iteration: int = -1
    system_prompt: list[str] = field(default_factory=list)
    user_message: Any = None
    last_response: str = ""
    current_tool: Any = None
    tools_output: str = ""
    history: list = field(default_factory=list)
    
@dataclass
class AgentConfig:
    """Configuration for the hybrid agent."""
    name: str = "Nova"
    role: str = "Research Assistant"
    workspace_path: str = "./data/workspace"
    memory_subdir: str = "default"
    ssh_enabled: bool = False
    ssh_addr: str = "localhost"
    ssh_port: int = 22
    ssh_user: str = "root"
    ssh_pass: str = ""
    performance_profile: str = "high" # "high" or "low"
    
class AgentContext:
    _contexts: dict[str, "AgentContext"] = {}
    
    def __init__(
        self,
        config: AgentConfig,
        id: str | None = None,
        name: str | None = None,
        parent: "AgentContext|None" = None
    ):
        self.id = id or self.generate_id()
        self.config = config
        self.name = name or config.name
        self.created_at = datetime.now(timezone.utc)
        self.parent = parent
        self.data: dict[str, Any] = {}
        self.paused = False
        
        # Register context
        self._contexts[self.id] = self
        
    @staticmethod
    def generate_id():
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        
    @staticmethod
    def get(id: str):
        return AgentContext._contexts.get(id)
        
    @staticmethod
    def all():
        return list(AgentContext._contexts.values())
        
    def set_data(self, key: str, value: Any):
        self.data[key] = value
        
    def get_data(self, key: str):
        return self.data.get(key)
