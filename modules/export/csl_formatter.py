"""
BioDockify Export Module: CSL Formatter
Handles citation formatting using CSL (Citation Style Language) logic.
Ensures references meet target journal requirements (e.g. Nature, Cell).
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class CSLFormatter:
    """
    Simulates CSL processing for citation formatting.
    Full CSL engine requires CiteProc-JS or similar heavy deps.
    This MVP implements the core templates for top styles.
    """
    
    STYLES = {
        "nature": "{author}. {title}. {journal} {volume}, {pages} ({year}).",
        "cell": "{author} ({year}). {title}. {journal} {volume}, {pages}.",
        "ama": "{author}. {title}. {journal}. {year};{volume}:{pages}."
    }
    
    def format_citation(self, paper: Dict, style: str = "nature") -> str:
        """
        Formats a single paper dictionary into a citation string.
        """
        template = self.STYLES.get(style, self.STYLES["nature"])
        
        # Extract fields with safe defaults
        authors = paper.get("authors", [])
        author_text = self._format_authors(authors, style)
        
        return template.format(
            author=author_text,
            title=paper.get("title", "Untitled"),
            journal=paper.get("journal", "Unknown Journal"),
            volume=paper.get("volume", ""),
            pages=paper.get("pages", ""),
            year=paper.get("year", "????")
        )
        
    def _format_authors(self, authors: List[str], style: str) -> str:
        if not authors:
            return "Anonymous"
            
        if style == "nature":
            # Nature: Smith, J. et al.
            if len(authors) > 1:
                return f"{authors[0]}, et al"
            return authors[0]
        else:
            # Default: List first 3
            return ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
