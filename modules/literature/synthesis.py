"""
Synthesis Engine
Literature review synthesis tool for Agent Zero.
Agent Zero provides the AI content generation - this module handles structure and formatting.
"""
import logging
import threading
from typing import List, Dict, Any, Optional, Callable

from .discovery import Paper
from modules.rag.vector_store import get_vector_store

logger = logging.getLogger("literature.synthesis")


class ReviewSynthesizer:
    """
    Literature review synthesizer for Agent Zero.
    
    This module manages structure, context retrieval, and formatting.
    Agent Zero handles all content generation through callbacks.
    """
    
    # Standard review sections
    SECTIONS = [
        ("Introduction", "background context and research question"),
        ("Methodology Overview", "research methods and approaches used"),
        ("Key Findings", "main results and discoveries"),
        ("Discussion & Gaps", "implications and research gaps"),
        ("Conclusion", "summary and future directions")
    ]
    
    def __init__(self):
        self.vector_store = get_vector_store()
        self._agent_callback: Optional[Callable] = None
    
    def set_agent_callback(self, callback: Callable[[str], str]):
        """
        Set the Agent Zero callback for content generation.
        
        Args:
            callback: Function that takes a prompt and returns generated content
        """
        self._agent_callback = callback
    
    async def generate_review(
        self, 
        topic: str, 
        papers: List[Paper],
        agent_generate: Optional[Callable[[str, str, str], str]] = None
    ) -> str:
        """
        Generate a structured literature review.
        
        Args:
            topic: Research topic
            papers: List of reviewed papers
            agent_generate: Agent Zero callback for section generation
                           Signature: (topic, section_name, context) -> content
        
        Returns:
            Formatted markdown review
        """
        logger.info(f"Synthesizing review for '{topic}' from {len(papers)} papers")
        
        # Index papers for context retrieval
        await self._index_papers(papers)
        
        # Build review
        full_report = f"# Systematic Review: {topic}\n\n"
        full_report += f"*Synthesized from {len(papers)} research papers*\n\n---\n\n"
        
        for section_title, section_focus in self.SECTIONS:
            logger.info(f"Generating section: {section_title}")
            
            # Get relevant context from vector store
            context = await self._get_section_context(topic, section_title, section_focus)
            
            if agent_generate:
                # Agent Zero generates content
                content = agent_generate(topic, section_title, context)
            elif self._agent_callback:
                # Use registered callback
                prompt = self._build_section_prompt(topic, section_title, section_focus, context)
                content = self._agent_callback(prompt)
            else:
                # Fallback to structured excerpts
                content = self._fallback_section(topic, section_title, context)
            
            full_report += f"## {section_title}\n\n{content}\n\n"
        
        # Add references
        full_report += self._format_references(papers)
        
        logger.info(f"Review complete: {len(full_report)} characters")
        return full_report
    
    async def _index_papers(self, papers: List[Paper]) -> bool:
        """Index papers in vector store for RAG."""
        try:
            for paper in papers:
                if paper.abstract:
                    content = f"Title: {paper.title}\nAbstract: {paper.abstract}"
                    metadata = {
                        "title": paper.title,
                        "year": paper.year,
                        "source": paper.source,
                        "doi": paper.doi or ""
                    }
                    await self.vector_store.add_documents([content], [metadata])
            logger.debug(f"Indexed {len(papers)} papers")
            return True
        except Exception as e:
            logger.error(f"Failed to index papers: {e}")
            return False
    
    async def _get_section_context(self, topic: str, section: str, focus: str) -> str:
        """Retrieve relevant context from vector store."""
        query = f"{topic} {section} {focus}"
        try:
            results = await self.vector_store.search(query, k=5)
            
            context_parts = []
            for r in results:
                text = r.get('text', '')[:600]
                if text:
                    context_parts.append(text)
            
            return "\n".join(context_parts) if context_parts else "No specific context available."
        except Exception as e:
            logger.warning(f"Context retrieval failed: {e}")
            return "Context retrieval failed."
    
    def _build_section_prompt(self, topic: str, section: str, focus: str, context: str) -> str:
        """Build prompt for Agent Zero to generate section content."""
        return f"""Write the "{section}" section for a literature review on: {topic}

FOCUS: {focus}

RESEARCH CONTEXT:
{context if context else "No specific context available."}

INSTRUCTIONS:
- Write 200-400 words
- Use formal academic language
- Be objective and evidence-based
- Synthesize the research context provided

Write the section:"""
    
    def _fallback_section(self, topic: str, section: str, context: str) -> str:
        """Generate fallback content when no agent is available."""
        if context and context != "No specific context available.":
            excerpts = context[:800]
            return f"*Based on reviewed literature:*\n\n> {excerpts}..."
        else:
            logger.warning(f"No agent available for synthesis of section: {section}")
            return f"*This section covers {section.lower()} for {topic}. Content pending Agent Zero generation. Please ensure an AI provider is configured.*"
    
    def _format_references(self, papers: List[Paper]) -> str:
        """Format references section."""
        refs = "## References\n\n"
        for i, paper in enumerate(papers, 1):
            authors = paper.authors[0] if paper.authors else 'Unknown'
            refs += f"{i}. **{paper.title}**. {authors} et al. ({paper.year}). *{paper.source}*.\n"
            if paper.doi:
                refs += f"   DOI: [{paper.doi}](https://doi.org/{paper.doi})\n"
            refs += "\n"
        return refs
    
    async def prepare_for_agent(self, topic: str, papers: List[Paper]) -> Dict[str, Any]:
        """
        Prepare review data for Agent Zero to process.
        
        Returns structured data for Agent Zero's planning.
        """
        # Index papers first
        try:
            for paper in papers:
                if paper.abstract:
                    await self.vector_store.add_documents(
                        [f"Title: {paper.title}\nAbstract: {paper.abstract}"],
                        [{"title": paper.title}]
                    )
        except Exception as e:
            logger.warning(f"Failed to index papers for agent preparation: {e}")
        
        # Prepare section contexts
        sections_data = []
        for section_title, section_focus in self.SECTIONS:
            context = await self._get_section_context(topic, section_title, section_focus)
            sections_data.append({
                "section": section_title,
                "focus": section_focus,
                "context": context[:1500] if context else ""
            })
        
        return {
            "task": "literature_review",
            "topic": topic,
            "paper_count": len(papers),
            "sections": sections_data,
            "papers": [
                {
                    "title": p.title,
                    "year": p.year,
                    "authors": p.authors[:3] if p.authors else [],
                    "source": p.source
                }
                for p in papers[:20]  # Limit for context size
            ]
        }
    
    def assemble_review(
        self, 
        topic: str, 
        section_contents: Dict[str, str],
        papers: List[Paper]
    ) -> str:
        """
        Assemble final review from Agent Zero generated sections.
        
        Args:
            topic: Research topic
            section_contents: Dict mapping section names to content
            papers: List of reviewed papers
        
        Returns:
            Complete formatted review
        """
        full_report = f"# Systematic Review: {topic}\n\n"
        full_report += f"*Synthesized from {len(papers)} research papers*\n\n---\n\n"
        
        for section_title, _ in self.SECTIONS:
            content = section_contents.get(section_title, f"*{section_title} content pending.*")
            full_report += f"## {section_title}\n\n{content}\n\n"
        
        full_report += self._format_references(papers)
        return full_report
    
    async def generate_section(self, topic: str, section: str, papers: List[Paper]) -> Dict[str, Any]:
        """
        Prepare data for generating a single section.
        
        Returns context for Agent Zero to generate content.
        """
        focus = dict(self.SECTIONS).get(section, section)
        context = await self._get_section_context(topic, section, focus)
        
        return {
            "section": section,
            "focus": focus,
            "topic": topic,
            "context": context,
            "paper_count": len(papers)
        }


# Singleton
_synthesis_engine_instance: Optional[ReviewSynthesizer] = None
_synthesis_engine_lock = threading.Lock()


def get_synthesizer() -> ReviewSynthesizer:
    """Get or create the ReviewSynthesizer singleton."""
    global _synthesis_engine_instance
    with _synthesis_engine_lock:
        if _synthesis_engine_instance is None:
            _synthesis_engine_instance = ReviewSynthesizer()
        return _synthesis_engine_instance
