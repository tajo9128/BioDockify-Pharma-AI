"""Literature Module"""
try:
    from .discovery import discovery_engine, Paper
except ImportError:
    discovery_engine = None
    Paper = None

__all__ = ['discovery_engine', 'Paper']
