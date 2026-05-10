"""
Agent Zero - Autonomous Research Orchestrator for BioDockify v2.0.0

This package provides an autonomous AI system that:
- Receives high-level PhD research goals
- Decomposes goals into executable tasks
- Selects appropriate tools automatically
- Self-corrects on failures
- Maintains persistent memory across sessions

Main Components:
- AgentZero: Main orchestrator for autonomous execution
- PhDPlanner: Stage detection and tool recommendation
- PersistentMemory: Long-term memory storage and retrieval

Example Usage:
    from agent_zero import AgentZero, PhDPlanner, PersistentMemory, ToolRegistry

    # Initialize
    llm = YourLLMProvider()
    memory = PersistentMemory('./data/agent_memory')
    planner = PhDPlanner(llm)
Agent Zero Package - BioDockify AI Brain

This is the unified AI brain for BioDockify, combining:
- Agent Zero: Deep reasoning, tool execution, PhD workflows
- NanoBot: Memory, skills, scheduling, messaging channels

Usage:
    from agent_zero import get_biodockify_ai
    
    ai = get_biodockify_ai()
    await ai.initialize()
    response = await ai.chat("Research cancer treatment")
"""

__version__ = '2.0.0'
__author__ = 'BioDockify Team'

from .biodockify_ai import BioDockifyAI, get_biodockify_ai, AI

# Legacy imports for backwards compatibility
try:
    from .core.orchestrator import AgentZero
except ImportError:
    AgentZero = None

try:
    from .enhanced import AgentZeroEnhanced
except ImportError:
    AgentZeroEnhanced = None

try:
    from .channels import AgentZeroChannels, get_channels
except ImportError:
    AgentZeroChannels = None
    get_channels = None

try:
    from .skills import get_browser_scraper, get_email_messenger
except ImportError:
    get_browser_scraper = None
    get_email_messenger = None

# NanoBot Hybrid Integration (retained from original, assuming it's still relevant)
try:
    from .nanobot_bridge import HybridAgentBrain, create_hybrid_agent
except ImportError:
    HybridAgentBrain = None
    create_hybrid_agent = None

__all__ = [
    # Main interface
    "BioDockifyAI",
    "get_biodockify_ai",
    "AI",
    
    # Legacy
    "AgentZero",
    "AgentZeroEnhanced",
    "AgentZeroChannels",
    "get_channels",
    
    # Skills
    "get_browser_scraper",
    "get_email_messenger",

    # NanoBot Hybrid Integration (retained from original)
    'HybridAgentBrain',
    'create_hybrid_agent',
]
