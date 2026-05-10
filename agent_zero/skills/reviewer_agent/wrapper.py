"""
ReviewerAgent Skill Wrapper
Integrates the citation verification engine into Agent Zero skills.
"""

from typing import Dict, Any, Optional
import threading
try:
    from modules.literature.reviewer import CitationReviewer
except ImportError:
    try:
        from agent_zero.literature.reviewer import CitationReviewer
    except ImportError:
        logger.error("CitationReviewer not found in modules or agent_zero.")
        raise
from loguru import logger

class ReviewerAgentSkill:
    """
    Skill for verifying academic citations and preventing hallucinations.
    """
    
    def __init__(self):
        self.reviewer = CitationReviewer()
        logger.info("Reviewer Agent Skill Initialized")

    def verify_citations(self, text: str) -> Dict[str, Any]:
        """
        Extract and verify citations from a block of text.
        
        Args:
            text: The research text containing citations (e.g., [Author, Year])
            
        Returns:
            Dictionary with integrity score and verification details.
        """
        logger.info(f"Reviewing text for citations (Length: {len(text)})")
        return self.reviewer.verify_text(text)

# Singleton
_reviewer_instance: Optional[ReviewerAgentSkill] = None
_reviewer_lock = threading.Lock()

def get_reviewer_agent() -> ReviewerAgentSkill:
    """Get singleton instance of ReviewerAgentSkill."""
    global _reviewer_instance
    with _reviewer_lock:
        if _reviewer_instance is None:
            _reviewer_instance = ReviewerAgentSkill()
    return _reviewer_instance
