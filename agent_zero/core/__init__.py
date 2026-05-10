"""
Agent Zero - Autonomous Research Orchestrator Core Module

This package contains the core components of the autonomous agent system:
- Orchestrator: Main autonomous execution loop
- Planner: Multi-step reasoning and PhD stage detection
- Memory: Persistent storage and retrieval system
"""

from .orchestrator import AgentZero
from .planner import PhDPlanner
from .memory import PersistentMemory

__all__ = ['AgentZero', 'PhDPlanner', 'PersistentMemory']
__version__ = '2.0.0'
