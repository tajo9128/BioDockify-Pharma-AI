"""
BioDockify Ranking Module: Semantic Scholar Integration
Ranks evidence based on scientific impact (influential citations) rather than just keyword relevance.
"""

import requests
import logging
from typing import List, Dict
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class ImpactScore:
    paper_id: str
    citation_count: int
    influential_citation_count: int
    year: int
    impact_factor_proxy: float # Derived metric

class SemanticScholarRanker:
    """
    Interfaces with Semantic Scholar Graph API to enrich and rank papers.
    Free tier allows decent throughput for real-time reranking.
    """
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper"
    
    def __init__(self, api_key: str = ""):
        self.headers = {"x-api-key": api_key} if api_key else {}
        
    def batch_rank(self, dois: List[str]) -> Dict[str, ImpactScore]:
        """
        Takes a list of DOIs and returns impact metrics for ranking.
        """
        if not dois:
            return {}
            
        # Semantic Scholar Batch API accepts IDs in the body
        url = f"{self.BASE_URL}/batch"
        payload = {"ids": [f"DOI:{doi}" for doi in dois]}
        params = {"fields": "title,year,citationCount,influentialCitationCount"}
        
        try:
            resp = requests.post(url, json=payload, params=params, headers=self.headers, timeout=15)
            
            impact_map = {}
            if resp.status_code == 200:
                results = resp.json()
                for item in results:
                    if item:
                        doi_raw = item.get("paperId", "")
                        # Note: S2 might return internal ID, we need to map back or rely on index order if stable
                        # Ideally we use the input DOI map. For MVP we trust the batch order or look for DOI field.
                        
                        score = ImpactScore(
                            paper_id=item.get("paperId"),
                            citation_count=item.get("citationCount", 0),
                            influential_citation_count=item.get("influentialCitationCount", 0),
                            year=item.get("year", 2024),
                            impact_factor_proxy=0.0
                        )
                        
                        # Calculate simple "BioDockify Impact Score"
                        # Weight influential citations heavily (x5) and recency
                        age = max(1, 2025 - (score.year or 2020))
                        score.impact_factor_proxy = (score.influential_citation_count * 5 + score.citation_count) / age
                        
                        # Start simple mapping by index if needed, but better to request externalIds to map back
                        # For this code snippet, we'll index by the S2 Paper ID, 
                        # integration logic needs to handle mapping.
                        impact_map[item.get("paperId")] = score
                        
                return impact_map
            else:
                logger.warning(f"Semantic Scholar batch failed: {resp.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Semantic Scholar ranking error: {str(e)}")
            return {}
