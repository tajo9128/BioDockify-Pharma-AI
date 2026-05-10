"""
Screening Engine
Paper screening tool for Agent Zero.
Agent Zero provides the AI reasoning - this module handles data processing.
"""
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import asdict

from .discovery import Paper

logger = logging.getLogger("literature.screening")


class ContentScreener:
    """
    Paper screening processor for Agent Zero.
    
    This module prepares data for Agent Zero to evaluate.
    Agent Zero handles all LLM operations and decision-making.
    """
    
    def __init__(self):
        self._agent_callback: Optional[Callable] = None
    
    def set_agent_callback(self, callback: Callable[[str], str]):
        """
        Set the Agent Zero callback for AI operations.
        
        Args:
            callback: Function that takes a prompt and returns AI response
        """
        self._agent_callback = callback
    
    async def screen_papers(
        self, 
        papers: List[Paper], 
        criteria: str,
        agent_evaluate: Optional[Callable[[Paper, str], bool]] = None
    ) -> List[Paper]:
        """
        Screen papers against inclusion criteria.
        
        Args:
            papers: List of papers to screen
            criteria: Inclusion/exclusion criteria text
            agent_evaluate: Optional callback from Agent Zero for per-paper evaluation
                           Signature: (paper: Paper, criteria: str) -> bool
        
        Returns:
            Filtered list of included papers
        """
        logger.info(f"Screening {len(papers)} papers against criteria: {criteria}")
        
        if not papers:
            return []
        
        # If Agent Zero provides an evaluation callback, use it
        if agent_evaluate:
            return await self._agent_screen(papers, criteria, agent_evaluate)
        
        # If we have a registered agent callback, prepare data for batch evaluation
        if self._agent_callback:
            return await self._batch_screen_with_agent(papers, criteria)
        
        # Fallback to heuristic screening
        logger.info("No agent callback - using heuristic screening")
        return self._heuristic_screen(papers, criteria)
    
    async def _agent_screen(
        self, 
        papers: List[Paper], 
        criteria: str,
        evaluate_fn: Callable[[Paper, str], bool]
    ) -> List[Paper]:
        """Screen using Agent Zero's evaluation function."""
        selected = []
        
        for paper in papers:
            try:
                is_relevant = evaluate_fn(paper, criteria)
                if is_relevant:
                    selected.append(paper)
                    logger.debug(f"INCLUDED: {paper.title[:50]}...")
                else:
                    logger.debug(f"EXCLUDED: {paper.title[:50]}...")
            except Exception as e:
                logger.warning(f"Error evaluating paper: {e}, including by default")
                selected.append(paper)
        
        logger.info(f"Agent screening: {len(selected)}/{len(papers)} papers included")
        return selected
    
    async def _batch_screen_with_agent(
        self, 
        papers: List[Paper], 
        criteria: str
    ) -> List[Paper]:
        """Prepare batch data for Agent Zero to process."""
        # Prepare paper summaries for Agent Zero
        paper_summaries = []
        for i, paper in enumerate(papers):
            summary = {
                "index": i,
                "title": paper.title,
                "year": paper.year,
                "abstract_preview": (paper.abstract or "")[:500],
                "source": paper.source
            }
            paper_summaries.append(summary)
        
        # Format for Agent Zero
        prompt = f"""Evaluate these papers against the criteria and return indices to INCLUDE.

CRITERIA: {criteria}

PAPERS:
{self._format_papers_for_agent(paper_summaries)}

Return a JSON array of indices to include, e.g. [0, 2, 5]"""

        try:
            response = self._agent_callback(prompt)
            included_indices = self._parse_indices(response)
            selected = [papers[i] for i in included_indices if i < len(papers)]
            logger.info(f"Agent batch screening: {len(selected)}/{len(papers)} papers included")
            return selected
        except Exception as e:
            logger.error(f"Agent batch screening failed: {e}")
            return self._heuristic_screen(papers, criteria)
    
    def _format_papers_for_agent(self, summaries: List[Dict]) -> str:
        """Format paper summaries for Agent Zero prompt."""
        lines = []
        for s in summaries:
            lines.append(f"[{s['index']}] {s['title']} ({s['year']}) - {s['abstract_preview'][:200]}...")
        return "\n".join(lines)
    
    def _parse_indices(self, response: str) -> List[int]:
        """Parse Agent Zero's response to extract paper indices."""
        import json
        import re
        
        # Try to extract JSON array
        match = re.search(r'\[[\d,\s]+\]', response)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        
        # Fallback: extract all numbers
        numbers = re.findall(r'\d+', response)
        return [int(n) for n in numbers]
    
    def _heuristic_screen(self, papers: List[Paper], criteria: str) -> List[Paper]:
        """Fallback heuristic screening without AI."""
        criteria_lower = criteria.lower()
        keywords = [w.strip() for w in criteria_lower.split() if len(w) > 3]
        
        scored_papers = []
        for paper in papers:
            score = 0
            text = f"{paper.title} {paper.abstract or ''}".lower()
            
            for kw in keywords:
                if kw in text:
                    score += 1
            
            if paper.year and paper.year >= 2021:
                score += 2
            
            scored_papers.append((paper, score))
        
        scored_papers.sort(key=lambda x: x[1], reverse=True)
        cutoff = max(10, len(scored_papers) // 2)
        selected = [p for p, s in scored_papers[:cutoff] if s > 0]
        
        if not selected:
            selected = [p for p, s in scored_papers[:10]]
        
        logger.info(f"Heuristic screening: {len(selected)}/{len(papers)} papers")
        return selected
    
    def prepare_for_agent(self, papers: List[Paper], criteria: str) -> Dict[str, Any]:
        """
        Prepare screening data for Agent Zero to process.
        
        Returns a structured dict that Agent Zero can use.
        """
        return {
            "task": "paper_screening",
            "criteria": criteria,
            "paper_count": len(papers),
            "papers": [
                {
                    "index": i,
                    "title": p.title,
                    "year": p.year,
                    "authors": p.authors[:3] if p.authors else [],
                    "abstract": p.abstract or "",
                    "source": p.source,
                    "doi": p.doi
                }
                for i, p in enumerate(papers)
            ]
        }
    
    def apply_agent_decision(self, papers: List[Paper], included_indices: List[int]) -> List[Paper]:
        """
        Apply Agent Zero's screening decision.
        
        Args:
            papers: Original paper list
            included_indices: Indices that Agent Zero marked as included
        
        Returns:
            Filtered paper list
        """
        return [papers[i] for i in included_indices if 0 <= i < len(papers)]


# Factory function
def get_screener() -> ContentScreener:
    """Get a ContentScreener instance."""
    return ContentScreener()
