"""
OpenAlex Scraper Module
Provides access to scientific literature via the OpenAlex API (Free, No Auth Required).
"""

import requests
import logging
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)

class OpenAlexScraper:
    """
    Scraper for OpenAlex API.
    Docs: https://docs.openalex.org/
    """
    
    BASE_URL = "https://api.openalex.org/works"
    
    def __init__(self, email: Optional[str] = None):
        """
        Initialize OpenAlex scraper.
        email: Optional, puts you in the 'polite pool' for faster/better access.
        """
        self.email = email

    def search_papers(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search OpenAlex for works matching the query.
        """
        params = {
            "search": query,
            "per-page": max_results,
            "filter": "type:article" # Focus on articles
        }
        
        if self.email:
            params["mailto"] = self.email
            
        headers = {
            "User-Agent": f"BioDockify/1.0 ({self.email or 'anon'})"
        }
            
        try:
            logger.info(f"Searching OpenAlex for: {query}")
            resp = requests.get(self.BASE_URL, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            results = []
            
            for item in data.get("results", []):
                # Safely extract abstract (OpenAlex uses an inverted index, so we need to reconstruct perfectly or use snippet)
                # Actually OpenAlex recently added 'abstract' mostly or we use the inverted index.
                # For simplicity in this v1, we used the 'display_name' as title and construct a basic record.
                # Reconstructing abstract from inverted index is complex; we'll check if 'abstract_inverted_index' exists.
                
                abstract = self._reconstruct_abstract(item.get("abstract_inverted_index"))
                if not abstract:
                    abstract = "Abstract not available directly from OpenAlex metadata."
                
                paper = {
                    "title": item.get("display_name", "No Title"),
                    "abstract": abstract,
                    "pmid": item.get("ids", {}).get("pmid", "").replace("https://pubmed.ncbi.nlm.nih.gov/", ""),
                    "doi": item.get("doi", "").replace("https://doi.org/", ""),
                    "publication_date": str(item.get("publication_year", "Unknown")),
                    "journal": item.get("primary_location", {}).get("source", {}).get("display_name", "Unknown"),
                    "source": "OpenAlex",
                    "authors": [a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])],
                    "url": item.get("doi") or item.get("id")
                }
                results.append(paper)
                
            return results
            
        except Exception as e:
            logger.error(f"OpenAlex Search Failed: {e}")
            return []

    def _reconstruct_abstract(self, inverted_index: Optional[Dict]) -> str:
        """Reconstruct abstract from OpenAlex inverted index."""
        if not inverted_index:
            return ""
            
        try:
            # Create a list of (index, word) tuples
            word_index = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_index.append((pos, word))
            
            # Sort by index
            word_index.sort()
            
            # Join words
            return " ".join([w[1] for w in word_index])
        except:
            return ""

# Helper
def search_openalex(query: str, max_results: int = 10) -> List[Dict]:
    scraper = OpenAlexScraper()
    return scraper.search_papers(query, max_results)
