"""Literature Module"""
from .discovery import discovery_engine, Paper

# Ensure backward compatibility if needed, or expose the new engine
__all__ = ['discovery_engine', 'Paper']
