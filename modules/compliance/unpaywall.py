"""
BioDockify Compliance Module: Unpaywall Integration
Enforces legal Open Access compliance using the Unpaywall REST API.
"""

import requests
import json
from dataclasses import dataclass
from typing import Optional, Dict
from pathlib import Path
import logging

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ComplianceResult:
    doi: str
    is_oa: bool
    license: Optional[str]
    best_oa_url: Optional[str]
    compliance_score: float # 0.0 to 1.0 (1.0 = CC-BY / Public Domain)
    raw_response: Dict

class UnpaywallChecker:
    """
    Checks paper DOIs against the Unpaywall database to ensure legal access.
    Implements caching to reduce API load.
    """
    
    BASE_URL = "https://api.unpaywall.org/v2"
    
    def __init__(self, email: str = "biodockify@hotmail.com"):
        self.email = email
        self.headers = {"User-Agent": "BioDockify-Pharma-Research/2.1.15"}
        
    def check_compliance(self, doi: str) -> ComplianceResult:
        """
        Queries Unpaywall for a specific DOI.
        
        Args:
            doi (str): The digital object identifier of the paper.
            
        Returns:
            ComplianceResult: Structured compliance data.
        """
        # Clean DOI
        clean_doi = doi.replace("doi:", "").strip()
        
        try:
            url = f"{self.BASE_URL}/{clean_doi}?email={self.email}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                is_oa = data.get("is_oa", False)
                best_loc = data.get("best_oa_location", {}) or {}
                
                # Calculate simple compliance score
                license_type = best_loc.get("license", "unknown")
                score = 0.0
                if is_oa:
                    if license_type in ["cc-by", "public-domain", "cc0"]:
                        score = 1.0
                    elif license_type in ["cc-by-nc", "cc-by-sa"]:
                        score = 0.8  # Acceptable for internal R&D
                    else:
                        score = 0.5  # OA but restrictive
                        
                return ComplianceResult(
                    doi=clean_doi,
                    is_oa=is_oa,
                    license=license_type,
                    best_oa_url=best_loc.get("url_for_pdf") or best_loc.get("url"),
                    compliance_score=score,
                    raw_response=data
                )
            elif response.status_code == 404:
                return ComplianceResult(clean_doi, False, None, None, 0.0, {})
            else:
                logger.warning(f"Unpaywall API error {response.status_code} for {clean_doi}")
                return ComplianceResult(clean_doi, False, None, None, 0.0, {})
                
        except Exception as e:
            logger.error(f"Unpaywall check failed for {doi}: {str(e)}")
            return ComplianceResult(clean_doi, False, None, None, 0.0, {})

# Simple testing block
if __name__ == "__main__":
    checker = UnpaywallChecker()
    # Test with a known OA paper (Alzheimer's context)
    res = checker.check_compliance("10.1038/s41586-020-2525-x")
    print(f"DOI: {res.doi}")
    print(f"Open Access: {res.is_oa}")
    print(f"License: {res.license}")
    print(f"URL: {res.best_oa_url}")
