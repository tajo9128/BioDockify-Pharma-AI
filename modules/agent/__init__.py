"""
Agent Module - Advanced Autonomous Capabilities

This module provides:
- Dependency auto-installation
- Agent spawning for parallel tasks
- Self-correction patterns
"""

from .prompts import AGENT_ZERO_SYSTEM_PROMPT
from .dependency_manager import DependencyManager, auto_install, get_manager

__all__ = [
    "AGENT_ZERO_SYSTEM_PROMPT",
    "DependencyManager",
    "auto_install", 
    "get_manager"
]
