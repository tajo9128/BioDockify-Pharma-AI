"""
BioDockify Literature Search: Semantic Scholar Integration
Provides "Pharma-Grade" evidence ranking based on influence and citation velocity.
"""

import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SemanticScholarSearcher:
    """
    Queries Semantic Scholar Graph API for high-impact papers.
    Prioritizes 'Influential Citations' over raw volume.
    """
    
    API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    DETAILS_URL = "https://api.semanticscholar.org/graph/v1/paper/"
    
    def __init__(self, api_key: Optional[str] = None):
        self.headers = {}
        if api_key:
            self.headers["x-api-key"] = api_key
            
    def search_impact_evidence(self, query: str, limit: int = 10, min_citations: int = 5) -> List[Dict]:
        """
        Searches for papers and ranks them by scientific influence.
        
        Args:
            query: Search terms.
            limit: Max results.
            min_citations: Noise filter threshold.
            
        Returns:
            List of ranked paper dictionaries.
        """
        params = {
            "query": query,
            "limit": limit * 2, # Fetch more to filter
            "fields": "title,year,citationCount,influentialCitationCount,authors,abstract,openAccessPdf",
        }
        
        try:
            response = requests.get(self.API_URL, params=params, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                raw_papers = data.get("data", [])
                return self._rank_and_filter(raw_papers, min_citations, limit)
            else:
                logger.error(f"Semantic Scholar Error {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Semantic Scholar Search Failed: {e}")
            return []

    def _rank_and_filter(self, papers: List[Dict], min_citations: int, limit: int) -> List[Dict]:
        """
        Applies Pharma-Grade ranking logic.
        Score = (InfluentialCitations * 5) + (RawCitations * 1) + (RecencyBonus)
        """
        ranked = []
        current_year = datetime.now().year
        
        for p in papers:
            citations = p.get("citationCount", 0) or 0
            if citations < min_citations:
                continue
                
            influential = p.get("influentialCitationCount", 0) or 0
            year = p.get("year") or 2000
            
            # Recency bonus: +10 points per year for last 5 years
            age = max(0, current_year - year)
            recency_score = max(0, (5 - age) * 10)
            
            score = (influential * 5) + (citations * 1) + recency_score
            
            p["dockify_score"] = score
            ranked.append(p)
            
        # Sort descending by score
        ranked.sort(key=lambda x: x["dockify_score"], reverse=True)
        return ranked[:limit]

    def get_citation_graph(self, paper_id: str) -> Dict:
        """
        Fetches references for a paper to build the evidence graph.
        """
        url = f"{self.DETAILS_URL}{paper_id}"
        params = {"fields": "references.title,references.paperId"}
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return {}

if __name__ == "__main__":
    searcher = SemanticScholarSearcher()
    results = searcher.search_impact_evidence("Bace1 inhibitors Alzheimer")
    for r in results:
        print(f"[{r['dockify_score']:.1f}] {r['title']} ({r['year']}) - Inf: {r['influentialCitationCount']}")
