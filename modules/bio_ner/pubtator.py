"""
BioDockify NER Module: PubTator Integration
Pharma-grade entity normalization to reduce false positives (e.g., CAT gene vs cat animal).
"""

import requests
import logging
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)

class PubTatorValidator:
    """
    Validates and normalizes biomedical entities using the NIH PubTator API.
    """
    
    API_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator-api/publications/export/biocjson"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BioDockify-Research-Agent/2.4.0 (biodockify@hotmail.com)"
        })

    def normalize_entities(self, pmids: List[str]) -> Dict[str, List[Dict]]:
        """
        Fetches curated entity annotations for a list of PMIDs.
        
        Args:
            pmids: List of PubMed IDs.
            
        Returns:
            Dict mapping PMID to list of normalized entities (Gene, Chemical, Disease).
        """
        if not pmids:
            return {}

        # PubTator accepts batch requests (limit ~100 usually, playing safe with 50)
        chunk_size = 50
        results = {}
        
        for i in range(0, len(pmids), chunk_size):
            chunk = pmids[i:i + chunk_size]
            pmid_str = ",".join(chunk)
            
            try:
                # Using the bioconcepts export
                params = {"pmids": pmid_str}
                response = self.session.get(self.API_URL, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    self._parse_bioc_json(data, results)
                else:
                    logger.warning(f"PubTator API error {response.status_code}: {response.text}")
                    
                time.sleep(1) # Respect rate limits (3 requests/sec usually)
                
            except Exception as e:
                logger.error(f"PubTator fetch failed: {e}")
                
        return results

    def _parse_bioc_json(self, data: Dict, results: Dict):
        """Parses the BioC JSON format from PubTator."""
        for document in data.get("documents", []):
            pmid = document.get("id")
            entities = []
            
            # Extract annotations
            for passage in document.get("passages", []):
                for annotation in passage.get("annotations", []):
                    # We utilize the infons for type and identifier
                    infons = annotation.get("infons", {})
                    entity_type = infons.get("type")
                    identifier = infons.get("identifier") # Mesh ID or NCBI Gene ID
                    text = annotation.get("text")
                    
                    if entity_type in ["Gene", "Chemical", "Disease", "Mutation"]:
                        entities.append({
                            "text": text,
                            "type": entity_type,
                            "id": identifier,
                            "normalized": True
                        })
            
            results[pmid] = entities

    def validate_term(self, term: str, expected_type: str) -> bool:
        """
        Quick check if a term is a known valid entity of expected type.
        (Note: PubTator is document-centric, so this is a heuristic scan 
         or requires a semantic lookup which PubTator doesn't directly offer cleanly 
         without a PMID. We returns True for now to avoid blocking, 
         or could implement a dictionary check if needed.)
        """
        # Placeholder for strict term validation if needed.
        return True

if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    validator = PubTatorValidator()
    # Test with a known paper (COVID-19 related)
    res = validator.normalize_entities(["32511993"])
    print(res)
