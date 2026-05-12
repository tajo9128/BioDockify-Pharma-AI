"""
Simple TTL Caching Module
Provides in-memory caching for LLM and vector search results.
"""

import time
import logging
import functools
import json
import hashlib
from typing import Any, Dict, Optional, Callable

logger = logging.getLogger("simple_cache")

class TTLDict(dict):
    """Dictionary with Time-To-Live for entries."""
    def __init__(self, default_ttl: int = 3600):
        super().__init__()
        self.default_ttl = default_ttl
        self._expiries = {}

    def __setitem__(self, key, value):
        self.set(key, value)

    def set(self, key, value, ttl: Optional[int] = None):
        expiry = time.time() + (ttl if ttl is not None else self.default_ttl)
        super().__setitem__(key, value)
        self._expiries[key] = expiry

    def __getitem__(self, key):
        if key not in self:
            raise KeyError(key)
        if time.time() > self._expiries[key]:
            self.__delitem__(key)
            raise KeyError(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def __delitem__(self, key):
        super().__delitem__(key)
        if key in self._expiries:
            del self._expiries[key]

    def cleanup(self):
        """Remove expired entries."""
        now = time.time()
        expired = [k for k, v in self._expiries.items() if now > v]
        for k in expired:
            self.__delitem__(k)

# Global caches
_llm_cache = TTLDict(default_ttl=7200)  # 2 hours for LLM calls
_vector_cache = TTLDict(default_ttl=3600)  # 1 hour for vector search

def cache_llm_call(func: Callable):
    """Decorator to cache LLM calls based on prompt and parameters."""
    @functools.wraps(func)
    def wrapper(self, prompt: str, **kwargs):
        # Create a stable key
        key_data = {
            "prompt": prompt,
            "model": getattr(self, "model", "default"),
            "params": {k: v for k, v in kwargs.items() if k != "timeout"}
        }
        key = hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
        
        if key in _llm_cache:
            logger.debug(f"LLM Cache Hit for {key}")
            return _llm_cache[key]
        
        result = func(self, prompt, **kwargs)
        if result and not str(result).startswith("[AI Unavailable]"):
            _llm_cache[key] = result
        return result
    return wrapper

def async_cache_llm_call(func: Callable):
    """Async version of LLM cache decorator."""
    @functools.wraps(func)
    async def wrapper(self, prompt: str, **kwargs):
        key_data = {
            "prompt": prompt,
            "model": getattr(self, "model", "default"),
            "params": {k: v for k, v in kwargs.items() if k != "timeout"}
        }
        key = hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
        
        if key in _llm_cache:
            logger.debug(f"LLM Cache Hit for {key}")
            return _llm_cache[key]
        
        result = await func(self, prompt, **kwargs)
        if result and not str(result).startswith("[AI Unavailable]"):
            _llm_cache[key] = result
        return result
    return wrapper
