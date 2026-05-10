"""
Agent Zero Search Planner

Generates search queries and chooses appropriate sources for web research.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    """Configuration for a research source."""
    name: str
    base_url: str
    priority: int
    depth_limit: int
    search_params: dict = field(default_factory=dict)
    extraction_rules: dict = field(default_factory=dict)
    score: int = 0  # Add score field for Bug #14


@dataclass
class SearchQuery:
    """A search query with context."""
    question: str
    context: Optional[Dict[str, Any]] = None
    knowledge_available: bool = True


@dataclass
class SearchPlan:
    """A plan for executing web research."""
    query: str
    sources: List[SourceConfig]
    estimated_time_minutes: int
    steps: List[str]


class SearchPlanner:
    """
    Generates search queries and selects appropriate sources for web research.
    
    This component:
    - Generates search queries from user questions
    - Chooses sources (PubMed, WHO, Google Scholar, etc.)
    - Determines search depth and scope
    - Creates execution plans
    """
    
    def __init__(self):
        """Initialize the Search Planner."""
        self.sources = {
            'pubmed': SourceConfig(
                name='PubMed',
                base_url='https://pubmed.ncbi.nlm.nih.gov',
                priority=1,
                depth_limit=2
            ),
            'who': SourceConfig(
                name='WHO',
                base_url='https://www.who.int',
                priority=2,
                depth_limit=1
            ),
            'google_scholar': SourceConfig(
                name='Google Scholar',
                base_url='https://scholar.google.com',
                priority=3,
                depth_limit=1
            ),
            'crossref': SourceConfig(
                name='CrossRef',
                base_url='https://api.crossref.org',
                priority=4,
                depth_limit=1
            )
        }
    
    def analyze_question(self, query: SearchQuery) -> List[str]:
        """
        Analyze a user question and extract key terms for searching.
        
        Args:
            query: The user's research question
            
        Returns:
            List of search terms
        """
        # Extract key terms from the question
        question_lower = query.question.lower()
        
        # Define domain-specific term extractors
        medical_terms = [
            r'\b(drug|medicine|pharmaceutical|treatment|therapy)\b',
            r'\b(disease|disorder|condition|syndrome|symptom)\b',
            r'\b(protein|enzyme|receptor|ligand|binding)\b',
            r'\b(molecular|structure|compound|docking|simulation)\b'
        ]
        
        # Extract terms using regex
        terms = []
        for pattern in medical_terms:
            matches = re.findall(pattern, question_lower)
            terms.extend(matches)
        
        # Also extract individual words (3+ characters)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', question_lower)
        terms.extend(words)
        
        # Remove duplicates and limit to top 10 terms
        unique_terms = list(set(terms))[:10]
        
        logger.info(f"Extracted {len(unique_terms)} search terms from question")
        return unique_terms
    
    def recommend_sources(
        self,
        query: SearchQuery,
        max_sources: int = 3
    ) -> List[SourceConfig]:
        """
        Recommend appropriate sources based on the query and available knowledge.
        
        Args:
            query: The search query
            max_sources: Maximum number of sources to recommend
            
        Returns:
            List of recommended source configurations
        """
        # Analyze query to determine source priorities
        question_lower = query.question.lower()
        
        # Priority scoring for sources
        source_scores = []
        
        for source_name, config in self.sources.items():
            score = 0
            
            # Check for domain-specific terms
            if 'drug' in question_lower or 'medicine' in question_lower:
                if source_name in ['pubmed', 'who']:
                    score += 3  # High priority for medical queries
            
            # Check for academic terms
            if 'research' in question_lower or 'study' in question_lower:
                if source_name in ['pubmed', 'google_scholar', 'crossref']:
                    score += 2
            
            # Check for molecular terms
            if 'protein' in question_lower or 'molecule' in question_lower:
                if source_name in ['pubmed', 'crossref']:
                    score += 2
            
            # Base priority based on source type
            if source_name == 'pubmed':
                score += 2
            elif source_name == 'who':
                score += 1
            elif source_name == 'google_scholar':
                score += 1
            elif source_name == 'crossref':
                score += 1
            
            source_scores.append((source_name, score, config))
        
        # Sort by score and take top N sources
        source_scores.sort(key=lambda x: x[1], reverse=True)
        selected_sources = source_scores[:max_sources]
        
        # Attach scores to config objects before returning
        result_configs = []
        for name, score, config in selected_sources:
            config.score = score
            result_configs.append(config)
            
        logger.info(f"Recommended {len(selected_sources)} sources: {[s[0] for s in selected_sources]} with scores")
        return result_configs
    
    def generate_search_queries(
        self,
        query: SearchQuery,
        sources: List[SourceConfig]
    ) -> List[str]:
        """
        Generate search queries for each selected source.
        
        Args:
            query: The search query
            sources: List of source configurations
            
        Returns:
            List of search queries
        """
        queries = []
        
        for source in sources:
            # Generate source-specific query
            source_query = self._generate_source_query(query, source)
            queries.append(source_query)
        
        logger.info(f"Generated {len(queries)} search queries")
        return queries
    
    def _generate_source_query(
        self,
        query: SearchQuery,
        source: SourceConfig
    ) -> str:
        """
        Generate a search query for a specific source.
        """
        # Extract search terms from the question
        terms = self.analyze_question(query)
        
        # Format terms for the specific source
        if not terms:
            return f"Search {source.name} for relevant information"
        
        # Join terms with OR for search
        terms_str = ' OR '.join(terms)
        
        # Add source-specific modifiers
        query_str = f"{terms_str}"
        
        # Add depth limit if specified
        if source.depth_limit > 0:
            query_str += f" (limit to {source.depth_limit} levels deep)"
        
        return query_str
    
    def create_search_plan(
        self,
        query: SearchQuery,
        context: Optional[Dict[str, Any]] = None
    ) -> SearchPlan:
        """
        Create a detailed execution plan for web research.
        
        Args:
            query: The search query
            context: Additional context for planning
            
        Returns:
            A search plan with steps and time estimates
        """
        # Recommend sources based on query
        recommended_sources = self.recommend_sources(query)
        
        # Calculate estimated time (5 minutes per source)
        estimated_time = len(recommended_sources) * 5
        
        # Create execution steps
        steps = []
        for i, source in enumerate(recommended_sources, 1):
            steps.append(f"{i}. Search {source.name}")
            steps.append(f"{i}. Extract relevant information")
        
        # Add synthesis step
        steps.append(f"{len(recommended_sources) + 1}. Synthesize results")
        
        plan = SearchPlan(
            query=query.question,
            sources=recommended_sources,
            estimated_time_minutes=estimated_time,
            steps=steps
        )
        
        logger.info(f"Created search plan with {len(steps)} steps")
        return plan


# Convenience function for easy use
async def plan_web_research(
    question: str,
    context: Optional[Dict[str, Any]] = None,
    max_sources: int = 3
) -> SearchPlan:
    """
    Convenience function to plan web research.
    
    Args:
        question: Research question
        context: Additional context
        max_sources: Maximum number of sources to use
        
    Returns:
        A search plan for web research
    """
    planner = SearchPlanner()
    query = SearchQuery(question=question, context=context)
    
    return planner.create_search_plan(query, max_sources=max_sources)
