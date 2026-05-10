"""
BioDockify Compliance Module: CORE Aggregator Integration
Fetches Open Access PDFs from the CORE global repository network.
"""

import requests
import logging
from typing import Optional
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class CoreAggregator:
    """
    Interface for the CORE API (core.ac.uk) to find and download OA versions of papers.
    """
    
    BASE_URL = "https://api.core.ac.uk/v3"
    
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        # Fallback public key if none provided (limited rate)
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        
    def find_oa_pdf(self, doi: str, output_dir: Path) -> Optional[Path]:
        """
        Searches CORE for a paper by DOI and attempts to download the PDF.
        
        Args:
            doi (str): Paper DOI.
            output_dir (Path): Directory to save the PDF.
            
        Returns:
            Optional[Path]: Path to downloaded file if successful, else None.
        """
        if not self.api_key:
            logger.warning("CORE API Key missing. Skipping CORE search.")
            return None
            
        clean_doi = doi.replace("doi:", "").strip()
        
        try:
            # 1. Search for Work
            search_url = f"{self.BASE_URL}/search/works"
            query = {"q": f"doi:\"{clean_doi}\"", "limit": 1}
            
            resp = requests.post(search_url, json=query, headers=self.headers, timeout=10)
            
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if not results:
                    return None
                    
                work = results[0]
                download_url = work.get("downloadUrl")
                
                if download_url:
                    # 2. Download PDF
                    pdf_path = output_dir / f"{clean_doi.replace('/', '_')}_CORE.pdf"
                    
                    # Stream download
                    with requests.get(download_url, stream=True, timeout=30) as r:
                         r.raise_for_status()
                         with open(pdf_path, 'wb') as f:
                             for chunk in r.iter_content(chunk_size=8192):
                                 f.write(chunk)
                                 
                    logger.info(f"Successfully downloaded PDF from CORE: {pdf_path}")
                    return pdf_path
            
            return None
            
        except Exception as e:
            logger.error(f"CORE aggregation failed for {doi}: {str(e)}")
            return None
