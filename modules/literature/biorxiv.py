"""
bioRxiv Scraper Module
Provides access to preprint server data for biology.
"""

import requests
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class BioRxivScraper:
    """
    Scraper for bioRxiv API.
    Docs: https://api.biorxiv.org/
    """
    # Note: bioRxiv API is a bit weird, primarily designed for bulk dumping or specific DOI lookups.
    # Searching for general terms usually requires scraping their search page or using a third-party index like Europe PMC (which covers bioRxiv).
    # However, strict bioRxiv endpoint for metadata:
    
    BASE_URL = "https://api.biorxiv.org/details/biorxiv"
    
    def search_papers(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search bioRxiv. 
        CRITICAL NOTE: The official bioRxiv API does NOT support keyword search. 
        It only supports date-range interval fetching.
        
        To search bioRxiv by *keyword*, we typically rely on **Europe PMC** with the constraint `SRC:PPR` (Preprints).
        
        Therefore, this class acts as a specialized wrapper around Europe PMC for preprint-specific sourcing.
        """
        logger.info(f"Searching bioRxiv via Europe PMC proxy for: {query}")
        
        # We construct a Europe PMC query specific to bioRxiv
        proxy_query = f"{query} AND (SRC:PPR OR PUBLISHER:\"Cold Spring Harbor Laboratory\")"
        
        # Import here to avoid circular dependency at top level if not careful, though usually fine.
        from modules.literature.europe_pmc import EuropePMCScraper
        
        proxy = EuropePMCScraper()
        results = proxy.search_papers(proxy_query, max_results)
        
        # Post-process to tag as Preprint
        for p in results:
            p["source"] = "bioRxiv (Preprint)"
            p["is_peer_reviewed"] = False
            
        return results
