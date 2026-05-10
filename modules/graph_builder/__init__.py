"""
Graph Builder Module
--------------------
Provides functionality to load data into the Neo4j Knowledge Graph.

NOTE: This module is deprecated. SurfSense Knowledge Engine is the primary
knowledge management system. Neo4j support is kept for backward compatibility
but the neo4j package is no longer required.
"""

try:
    from .loader import (
        Neo4jLoader, 
        get_loader, 
        create_constraints, 
        add_paper, 
        connect_compound,
        NEO4J_AVAILABLE
    )
except ImportError:
    # Fallback if loader has issues
    NEO4J_AVAILABLE = False
    Neo4jLoader = None
    get_loader = lambda: None
    create_constraints = lambda: None
    add_paper = lambda *args, **kwargs: None
    connect_compound = lambda *args, **kwargs: None

__all__ = [
    'Neo4jLoader', 
    'get_loader', 
    'create_constraints', 
    'add_paper', 
    'connect_compound',
    'NEO4J_AVAILABLE'
]
