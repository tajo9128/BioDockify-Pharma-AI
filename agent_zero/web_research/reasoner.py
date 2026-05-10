"""
Agent Zero Reasoner

Synthesizes answers using LLM, generates citations, and provides comprehensive responses.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import logging
from datetime import datetime
from .executor import PageResult

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Citation for a source."""
    url: str
    title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    journal: Optional[str] = None
    pages: Optional[str] = None
    snippet: str = ""


@dataclass
class ResearchAnswer:
    """A research answer with citations."""
    query: str
    answer: str
    sources: List[Citation]
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasonerConfig:
    """Configuration for the Reasoner."""
    max_context_length: int = 10000
    max_sources: int = 10
    confidence_threshold: float = 0.5
    include_snippets: bool = True
    llm_model: str = "gpt-4"
    temperature: float = 0.7


class Reasoner:
    """
    Synthesizes answers using LLM and generates citations.
    
    This component:
    - Calls LLM on stored knowledge
    - Synthesizes information from multiple sources
    - Generates comprehensive answers
    - Cites sources
    """
    
    def __init__(self, config: Optional[ReasonerConfig] = None):
        """
        Initialize the Reasoner.
        
        Args:
            config: Reasoner configuration (uses default if None)
        """
        self.config = config or ReasonerConfig()
        self.llm_adapter = None  # Will be initialized with LLM provider
    
    async def _ensure_adapter(self):
        """Ensure an LLM adapter is available, attempting to load from factory if missing."""
        if self.llm_adapter is not None:
            return
            
        try:
            from modules.llm.factory import LLMFactory
            from runtime.config_loader import load_config
            cfg = load_config()
            ai_cfg = cfg.get("ai_provider", {})
            
            # Simple mock for config compatibility
            class MockConfig:
                def __init__(self, c):
                    for k, v in c.items(): setattr(self, k, v)
                    self.primary_model = c.get("primary_model", "google")

            self.llm_adapter = LLMFactory.get_adapter(ai_cfg.get("primary_model", "google"), MockConfig(ai_cfg))
            if self.llm_adapter:
                logger.info(f"LLM adapter auto-initialized: {type(self.llm_adapter).__name__}")
        except Exception as e:
            logger.error(f"Failed to auto-initialize LLM adapter: {e}")

    def set_llm_adapter(self, llm_adapter):
        """
        Set the LLM adapter for generating answers.
        
        Args:
            llm_adapter: LLM adapter instance
        """
        self.llm_adapter = llm_adapter
        logger.info(f"LLM adapter set: {type(llm_adapter).__name__}")
    
    async def reason(
        self,
        query: str,
        knowledge: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate an answer using LLM on stored knowledge.
        
        Args:
            query: Research question
            knowledge: List of knowledge snippets
            context: Additional context
            
        Returns:
            Generated answer
        """
        await self._ensure_adapter()
        if not self.llm_adapter:
            raise ValueError("LLM adapter not set and could not be auto-initialized.")
        
        # Prepare context from knowledge
        context_text = self._prepare_knowledge_context(knowledge)
        
        # Create prompt
        prompt = self._create_reasoning_prompt(query, context_text, context)
        
        # Generate answer using LLM
        try:
            answer = await self._call_llm(prompt)
            logger.info(f"Generated answer for query: {query[:50]}...")
            return answer
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return f"Unable to generate answer due to error: {str(e)}"
    
    def _prepare_knowledge_context(self, knowledge: List[str]) -> str:
        """
        Prepare context from knowledge snippets.
        
        Args:
            knowledge: List of knowledge snippets
            
        Returns:
            Formatted context string
        """
        # Limit context length
        total_length = 0
        selected_knowledge = []
        
        for snippet in knowledge:
            if total_length + len(snippet) > self.config.max_context_length:
                break
            selected_knowledge.append(snippet)
            total_length += len(snippet)
        
        # Format context
        context_parts = []
        for i, snippet in enumerate(selected_knowledge, 1):
            context_parts.append(f"[Source {i}]\n{snippet}\n")
        
        return "\n".join(context_parts)
    
    def _create_reasoning_prompt(
        self,
        query: str,
        context: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a prompt for LLM reasoning.
        
        Args:
            query: Research question
            context: Knowledge context
            additional_context: Additional context
            
        Returns:
            Formatted prompt
        """
        prompt = f"""You are a research assistant specializing in pharmaceutical and biomedical research. 

Based on the following information, provide a comprehensive answer to the user's question.

User Question:
{query}

Available Information:
{context}

Instructions:
1. Synthesize information from multiple sources
2. Provide a clear, well-structured answer
3. Include relevant details and specifics
4. Acknowledge limitations or uncertainties
5. Be objective and evidence-based
6. If information is insufficient, state this clearly

Answer:"""

        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """
        Call the LLM adapter to generate a response.
        
        Args:
            prompt: Input prompt
            
        Returns:
            LLM response
        """
        if not self.llm_adapter:
            raise ValueError("LLM adapter not set")
        
        try:
            # Call the LLM adapter
            response = await self.llm_adapter.generate(
                prompt=prompt,
                max_tokens=2000,
                temperature=self.config.temperature
            )
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    async def synthesize_answer(
        self,
        query: str,
        results: List[PageResult],
        context: Optional[Dict[str, Any]] = None
    ) -> ResearchAnswer:
        """
        Synthesize a comprehensive answer from multiple sources.
        
        Args:
            query: Research question
            results: List of page results
            context: Additional context
            
        Returns:
            Research answer with citations
        """
        if not results:
            return ResearchAnswer(
                query=query,
                answer="No relevant information found.",
                sources=[],
                confidence=0.0,
                timestamp=datetime.now(),
                metadata={'error': 'No results provided'}
            )
        
        # Filter successful results
        successful_results = [r for r in results if r.success]
        
        if not successful_results:
            return ResearchAnswer(
                query=query,
                answer="No successful results to synthesize.",
                sources=[],
                confidence=0.0,
                timestamp=datetime.now(),
                metadata={'error': 'No successful results'}
            )
        
        # Limit number of sources
        limited_results = successful_results[:self.config.max_sources]
        
        # Prepare knowledge snippets
        knowledge = []
        for result in limited_results:
            snippet = f"Source: {result.url}\nTitle: {result.title}\nContent: {result.content[:1000]}"
            knowledge.append(snippet)
        
        # Generate answer
        answer = await self.reason(query, knowledge, context)
        
        # Generate citations
        citations = await self.generate_citations(limited_results)
        
        # Calculate confidence
        confidence = self._calculate_confidence(limited_results, answer)
        
        # Create metadata
        metadata = {
            'num_sources': len(limited_results),
            'total_results': len(results),
            'successful_results': len(successful_results),
            'context': context or {}
        }
        
        return ResearchAnswer(
            query=query,
            answer=answer,
            sources=citations,
            confidence=confidence,
            timestamp=datetime.now(),
            metadata=metadata
        )
    
    async def generate_citations(
        self,
        results: List[PageResult]
    ) -> List[Citation]:
        """
        Generate citations from page results.
        
        Args:
            results: List of page results
            
        Returns:
            List of citations
        """
        citations = []
        
        for result in results:
            if not result.success:
                continue
            
            # Extract citation information
            citation = Citation(
                url=result.url,
                title=result.title,
                snippet=result.content[:200] if self.config.include_snippets else ""
            )
            
            # Try to extract additional metadata
            self._extract_citation_metadata(result, citation)
            
            citations.append(citation)
        
        logger.info(f"Generated {len(citations)} citations")
        return citations
    
    def _extract_citation_metadata(
        self,
        result: PageResult,
        citation: Citation
    ):
        """
        Extract additional citation metadata from a result.
        
        Args:
            result: Page result
            citation: Citation to update
        """
        # Try to extract year from content
        import re
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, result.content)
        if years:
            citation.year = int(years[0])
        
        # Try to extract journal name
        journal_patterns = [
            r'Journal of [A-Z][a-z]+',
            r'[A-Z][a-z]+ [A-Z][a-z]+ Journal',
            r'[A-Z][a-z]+ \& [A-Z][a-z]+'
        ]
        for pattern in journal_patterns:
            match = re.search(pattern, result.content)
            if match:
                citation.journal = match.group()
                break
    
    def _calculate_confidence(
        self,
        results: List[PageResult],
        answer: str
    ) -> float:
        """
        Calculate confidence in the answer.
        
        Args:
            results: List of page results
            answer: Generated answer
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not results:
            return 0.0
        
        # Base confidence from number of sources
        base_confidence = min(len(results) / 5.0, 1.0)
        
        # Adjust based on answer length
        answer_length_factor = min(len(answer) / 500.0, 1.0)
        
        # Adjust based on content quality
        content_quality_factor = 1.0
        for result in results:
            if len(result.content) < 100:
                content_quality_factor *= 0.9
        
        # Calculate final confidence
        confidence = base_confidence * answer_length_factor * content_quality_factor
        
        # Ensure within bounds
        confidence = max(0.0, min(confidence, 1.0))
        
        return confidence
    
    async def summarize_findings(
        self,
        results: List[PageResult],
        max_points: int = 5
    ) -> List[str]:
        """
        Summarize key findings from results.
        
        Args:
            results: List of page results
            max_points: Maximum number of key points
            
        Returns:
            List of key findings
        """
        if not self.llm_adapter:
            raise ValueError("LLM adapter not set. Call set_llm_adapter() first.")
        
        # Prepare content
        content = "\n\n".join([
            f"From {r.url}:\n{r.content[:500]}"
            for r in results[:5] if r.success
        ])
        
        # Create prompt
        prompt = f"""Summarize the key findings from the following research content. Provide at most {max_points} bullet points.

Content:
{content}

Key Findings:"""

        try:
            response = await self._call_llm(prompt)
            
            # Parse bullet points
            findings = []
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('*') or line.startswith('•'):
                    findings.append(line[1:].strip())
            
            return findings[:max_points]
            
        except Exception as e:
            logger.error(f"Failed to summarize findings: {e}")
            return []
    
    async def compare_sources(
        self,
        results: List[PageResult]
    ) -> Dict[str, Any]:
        """
        Compare and contrast information from multiple sources.
        
        Args:
            results: List of page results
            
        Returns:
            Comparison analysis
        """
        if not results:
            return {'error': 'No results to compare'}
        
        successful_results = [r for r in results if r.success]
        
        if len(successful_results) < 2:
            return {'error': 'Need at least 2 sources to compare'}
        
        # Prepare comparison data
        comparison = {
            'num_sources': len(successful_results),
            'domains': list(set([r.metadata.get('domain', 'unknown') for r in successful_results])),
            'total_content_length': sum(len(r.content) for r in successful_results),
            'avg_content_length': sum(len(r.content) for r in successful_results) / len(successful_results),
            'sources': [
                {
                    'url': r.url,
                    'title': r.title,
                    'domain': r.metadata.get('domain', 'unknown'),
                    'content_length': len(r.content)
                }
                for r in successful_results
            ]
        }
        
        return comparison
    
    def format_answer_with_citations(
        self,
        answer: ResearchAnswer
    ) -> str:
        """
        Format answer with inline citations.
        
        Args:
            answer: Research answer
            
        Returns:
            Formatted answer with citations
        """
        formatted = f"{answer.answer}\n\n"
        
        if answer.sources:
            formatted += "Sources:\n"
            for i, citation in enumerate(answer.sources, 1):
                formatted += f"{i}. {citation.title}\n"
                formatted += f"   URL: {citation.url}\n"
                if citation.journal:
                    formatted += f"   Journal: {citation.journal}\n"
                if citation.year:
                    formatted += f"   Year: {citation.year}\n"
                formatted += "\n"
        
        formatted += f"\nConfidence: {answer.confidence:.2f}\n"
        formatted += f"Generated: {answer.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return formatted


# Convenience function for easy use
async def synthesize_research_answer(
    query: str,
    results: List[PageResult],
    llm_adapter,
    context: Optional[Dict[str, Any]] = None,
    max_sources: int = 10
) -> ResearchAnswer:
    """
    Convenience function to synthesize a research answer.
    
    Args:
        query: Research question
        results: List of page results
        llm_adapter: LLM adapter instance
        context: Additional context
        max_sources: Maximum number of sources to use
        
    Returns:
        Research answer with citations
    """
    config = ReasonerConfig(max_sources=max_sources)
    reasoner = Reasoner(config)
    reasoner.set_llm_adapter(llm_adapter)
    
    return await reasoner.synthesize_answer(query, results, context)
