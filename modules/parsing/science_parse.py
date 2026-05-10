"""
BioDockify Parsing Module: ScienceParse Integration
Robust fallback for PDF parsing when GROBID fails, optimized for older/scanned pharma papers.
"""

import requests
import logging
from pathlib import Path
from typing import Dict, Optional, Any
import json

logger = logging.getLogger(__name__)

class ScienceParseWrapper:
    """
    Wrapper for a local ScienceParse server (default port 8080).
    ScienceParse is a Java-based PDF parser that often succeeds where GROBID fails
    on noisy or older layouts.
    """
    
    def __init__(self, endpoint: str = "http://localhost:8080/v1"):
        self.endpoint = endpoint
        
    def parse_pdf(self, pdf_path: Path) -> Optional[Dict[str, Any]]:
        """
        Sends a PDF to the local ScienceParse service.
        
        Args:
            pdf_path (Path): Path to the PDF file.
            
        Returns:
            Optional[Dict]: Structured parse result (title, sections, refs) or None.
        """
        if not pdf_path.exists():
            logger.error(f"PDF not found: {pdf_path}")
            return None
            
        try:
            with open(pdf_path, "rb") as f:
                # ScienceParse accepts the PDF as the request body
                response = requests.put(
                    self.endpoint, 
                    data=f, 
                    headers={"Content-Type": "application/pdf"},
                    timeout=60
                )
                
            if response.status_code == 200:
                data = response.json()
                return self._normalize_output(data)
            else:
                logger.warning(f"ScienceParse failed with status {response.status_code}")
                return None
                
        except requests.exceptions.ConnectionError:
            logger.warning("ScienceParse local server is not running at localhost:8080")
            return None
        except Exception as e:
            logger.error(f"ScienceParse error for {pdf_path.name}: {str(e)}")
            return None
            
    def _normalize_output(self, raw: Dict) -> Dict:
        """
        Normalizes ScienceParse JSON to align with BioDockify's 'Paper' model schema.
        """
        metadata = raw.get("metadata", {})
        
        return {
            "title": metadata.get("title"),
            "authors": metadata.get("authors", []),
            "abstract": metadata.get("abstractText"),
            "year": metadata.get("year"),
            # Sections often missing in SP, fallback to raw text if needed
            "sections": raw.get("sections", []), 
            "references": raw.get("references", [])
        }
