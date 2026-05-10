"""
BioDockify Normalization Module: PubTator Central Integration
Standardizes biomedical entities using NCBI's state-of-the-art PubTator 3 API.
Maps raw text to MeSH, NCBI Gene, and chemical IDs.
"""

import requests
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class NormalizedEntity:
    text: str
    type: str # Gene, Disease, Chemical, Species, Mutation, CellLine
    id: str
    offset: int

class PubTatorNormalizer:
    """
    Interface for PubTator Central API.
    Used to validate and normalize entities extracted by local models (scispaCy/Gliner).
    """
    
    API_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/annotations/annotate/submit"
    RETRIEVE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/annotations/annotate/retrieve"
    
    def normalize_text(self, text: str) -> List[NormalizedEntity]:
        """
        Submits text to PubTator for entity tagging.
        Note: Use judiciously as this is an external API call.
        Prefer normalizing abstracts over full text.
        """
        try:
            # Submit Request
            payload = {"text": text}
            response = requests.post(self.API_URL, json=payload, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"PubTator submit failed: {response.text}")
                return []
                
            session_id = response.json().get("SessionID")
            
            # In a real sync implementaiton, we'd poll. 
            # For this MVP, we assume fast response or implement a short wait.
            # PubTator 3 can be async.
            
            # Simulating synchronous return for short texts (often cached)
            # If complex polling is needed, this would be expanded.
            
            return [] # Placeholder for async logic implementation in v2.2
            
        except Exception as e:
            logger.error(f"PubTator normalization failed: {str(e)}")
            return []

    def get_pmid_annotations(self, pmid: str) -> List[NormalizedEntity]:
        """
        Retrieves pre-computed annotations for a PubMed ID.
        This is the preferred, fast method for existing papers.
        """
        url = f"https://www.ncbi.nlm.nih.gov/research/pubtator-api/publications/export/biocjson?pmids={pmid}"
        
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                entities = []
                
                # BiocJSON parsing logic
                for doc in data.get("passages", []):
                    for ann in doc.get("annotations", []):
                        entities.append(NormalizedEntity(
                            text=ann.get("text"),
                            type=ann["infons"].get("type"),
                            id=ann["infons"].get("identifier"),
                            offset=ann["locations"][0]["offset"]
                        ))
                return entities
                
            return []
        except Exception as e:
            logger.error(f"PubTator PMID fetch failed: {str(e)}")
            return []
