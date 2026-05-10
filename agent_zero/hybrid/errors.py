"""
Hybrid Errors - Exception classes for control flow and self-healing.
"""
import traceback
import asyncio
import re

class RepairableException(Exception):
    """
    An exception that the agent can attempt to fix itself.
    When caught, the agent's monologue loop will prompt the LLM with the error
    to generate a fix.
    """
    pass

class InterventionException(Exception):
    """
    Triggered when the user intervenes (pauses/sends message) during execution.
    Stops the current reasoning chain to process the new input.
    """
    pass

class HandledException(Exception):
    """
    An exception that has already been logged/handled and should stop execution
    without further processing.
    """
    pass

def format_error(e: Exception) -> str:
    """Format exception trace for LLM consumption with cleaner summary."""
    tb = traceback.extract_tb(e.__traceback__)
    if not tb:
        return f"Error: {str(e)}"
    
    last_call = tb[-1]
    filename = last_call.filename
    lineno = last_call.lineno
    name = last_call.name
    
    return f"Error Type: {type(e).__name__}\nMessage: {str(e)}\nLocation: {filename}:{lineno} in {name}"
