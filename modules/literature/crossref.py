"""
CrossRef Scraper Module
Provides metadata and DOI resolution for general academic verification.
"""

import requests
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class CrossRefScraper:
    """
    Scraper for CrossRef API.
    Docs: https://api.crossref.org/
    """
    
    BASE_URL = "https://api.crossref.org/works"
    
    def __init__(self, email: Optional[str] = None):
        self.email = email

    def search_papers(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search CrossRef.
        """
        params = {
            "query": query,
            "rows": max_results,
            "select": "DOI,title,abstract,author,published-print,container-title,is-referenced-by-count"
        }
        
        headers = {}
        if self.email:
            headers["User-Agent"] = f"BioDockify/1.0 (mailto:{self.email})"
            
        try:
            logger.info(f"Searching CrossRef for: {query}")
            resp = requests.get(self.BASE_URL, params=params, headers=headers, timeout=12)
            resp.raise_for_status()
            
            data = resp.json()
            items = data.get("message", {}).get("items", [])
            results = []
            
            for item in items:
                # Titles in CrossRef are lists
                title_list = item.get("title", [])
                title = title_list[0] if title_list else "No Title"
                
                # Dates are nested structures
                date_parts = item.get("published-print", {}).get("date-parts", [[None]])
                year = str(date_parts[0][0]) if date_parts[0][0] else "Unknown"
                
                # Authors
                authors = [f"{a.get('given','')} {a.get('family','')}".strip() for a in item.get("author", [])]
                
                paper = {
                    "title": title,
                    "abstract": item.get("abstract", "Abstract not available (CrossRef)."), # Often missing in CrossRef
                    "doi": item.get("DOI", ""),
                    "publication_date": year,
                    "journal": item.get("container-title", ["Unknown"])[0],
                    "source": "CrossRef",
                    "authors": authors,
                    "citation_count": item.get("is-referenced-by-count", 0)
                }
                results.append(paper)
                
            return results
            
        except Exception as e:
            logger.error(f"CrossRef Search Failed: {e}")
            return []
