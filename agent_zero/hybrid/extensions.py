"""
Hybrid Extension System - Hook points for Agent Zero style extensions.
"""
from typing import Callable, Coroutine, Any, List
import logging
import inspect
import asyncio

logger = logging.getLogger(__name__)

class Extension:
    """Base class for all hybrid extensions."""
    pass

class Extensions:
    """Manages loaded extensions and hooks."""
    
    def __init__(self, agent):
        self.agent = agent
        self.extensions: List[Extension] = []
        
    def load(self, extension: Extension):
        """Register an extension instance."""
        self.extensions.append(extension)
        logger.info(f"Loaded extension: {extension.__class__.__name__}")
        
    async def call(self, hook_name: str, *args, **kwargs) -> Any:
        """Call a hook on all loaded extensions."""
        results = []
        
        for ext in self.extensions:
            if hasattr(ext, hook_name):
                handler = getattr(ext, hook_name)
                
                try:
                    if inspect.iscoroutinefunction(handler):
                        res = await handler(*args, **kwargs)
                    else:
                        res = handler(*args, **kwargs)
                        
                    if res is not None:
                        results.append(res)
                        
                except Exception as e:
                    logger.error(f"Error in extension {ext.__class__.__name__}.{hook_name}: {e}")
                    
        return results

    # Hook Definitions (for documentation)
    # async def agent_init(self)
    # async def monologue_start(self)
    # async def message_loop_start(self)
    # async def before_llm_call(self)
    # async def after_tool_execution(self)
