"""
Agent Zero Web Research Module

Provides web research capabilities for Agent Zero.
Includes:
- Search Planner: Generates search queries and selects sources
- SurfSense: Web scraping with extraction rules
- Executor: Fetches pages and extracts text
- Curator: Saves results and manages metadata
- Reasoner: Synthesizes answers using LLM
"""

from .search_planner import SearchPlanner, SearchQuery, SearchPlan, SourceConfig
from .surfsense import SurfSense, ExtractionRules, CrawlConfig, CrawlResult
from .executor import Executor, PageResult, ExecutorConfig
from .curator import Curator, CuratorConfig, QueryMetadata, ResultMetadata, SearchIndex
from .reasoner import Reasoner, ReasonerConfig, Citation, ResearchAnswer

__all__ = [
    # Search Planner
    'SearchPlanner',
    'SearchQuery',
    'SearchPlan',
    'SourceConfig',
    # SurfSense
    'SurfSense',
    'ExtractionRules',
    'CrawlConfig',
    'CrawlResult',
    # Executor
    'Executor',
    'PageResult',
    'ExecutorConfig',
    # Curator
    'Curator',
    'CuratorConfig',
    'QueryMetadata',
    'ResultMetadata',
    'SearchIndex',
    # Reasoner
    'Reasoner',
    'ReasonerConfig',
    'Citation',
    'ResearchAnswer',
]
