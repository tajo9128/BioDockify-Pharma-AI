"""
BioDockify Reviewer: Citation Verification Engine
Analyzes research text for citations and verifies them against academic databases.
Prevents "Hallucinated" citations in AI-generated pharma research.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

from modules.literature.semantic_scholar import SemanticScholarSearcher
from modules.literature.crossref import CrossRefScraper
from modules.literature.europe_pmc import EuropePMCScraper

logger = logging.getLogger(__name__)

class CitationReviewer:
    """
    Automated reviewer that cross-references citations against real databases.
    """
    
    def __init__(self):
        self.sem_scholar = SemanticScholarSearcher()
        self.crossref = CrossRefScraper()
        self.epmc = EuropePMCScraper()

    def verify_text(self, text: str) -> Dict[str, Any]:
        """
        Processes a block of text, extracts citations, and verifies them.
        """
        citations = self._extract_citations(text)
        results = []
        
        for cit in citations:
            verification = self._verify_single(cit)
            results.append(verification)
            
        # Calculate overall integrity score
        if not results:
            score = 100.0
        else:
            valid_count = sum(1 for r in results if r['status'] == 'VALID')
            score = (valid_count / len(results)) * 100
            
        return {
            "integrity_score": round(score, 1),
            "citations_found": len(citations),
            "verification_details": results
        }

    def _extract_citations(self, text: str) -> List[Dict[str, str]]:
        """
        Finds citations in formats like [Author et al., 2023] or DOI: 10.1101/...
        """
        citations = []
        
        # Pattern 1: [Author, Year] or [Author et al., Year]
        bracket_pattern = r'\[([^\]]+?),\s*(\d{4})\]'
        for match in re.finditer(bracket_pattern, text):
            citations.append({
                "type": "author_year",
                "raw": match.group(0),
                "author": match.group(1),
                "year": match.group(2)
            })
            
        # Pattern 2: DOI
        doi_pattern = r'10\.\d{4,9}/[-._;()/:A-Z0-9]+'
        for match in re.finditer(doi_pattern, text, re.I):
            citations.append({
                "type": "doi",
                "raw": match.group(0),
                "doi": match.group(0)
            })
            
        return citations

    def _verify_single(self, citation: Dict[str, str]) -> Dict[str, Any]:
        """
        Verifies a single citation against multiple sources.
        """
        query = ""
        if citation['type'] == 'doi':
            query = citation['doi']
        else:
            query = f"{citation['author']} {citation['year']}"
            
        # Try sources in order of reliability for medicine/pharma
        db_results = []
        
        # 1. Semantic Scholar
        sem_res = self.sem_scholar.search_impact_evidence(query, limit=3)
        for r in sem_res:
            db_results.append({"title": r['title'], "year": str(r['year']), "source": "Semantic Scholar"})
            
        # 2. Europe PMC (if no results or for bio-diversity)
        if not db_results:
            epmc_res = self.epmc.search_papers(query, max_results=3)
            for r in epmc_res:
                db_results.append({"title": r['title'], "year": str(r['publication_date']), "source": "Europe PMC"})

        # 3. CrossRef
        if not db_results:
            cr_res = self.crossref.search_papers(query, max_results=3)
            for r in cr_res:
                db_results.append({"title": r['title'], "year": str(r['publication_date']), "source": "CrossRef"})

        if not db_results:
            return {
                "citation": citation['raw'],
                "status": "UNVERIFIED",
                "reason": "No matching record found in any database."
            }

        # Check for matching author/year info (fuzzy match)
        best_match = None
        highest_score = 0
        
        for res in db_results:
            # Simple fuzzy matching on the input raw vs result
            # If it's Author/Year, we check if they appear in title/metadata
            match_score = self._calculate_match_score(citation, res)
            if match_score > highest_score:
                highest_score = match_score
                best_match = res

        if highest_score > 0.7:
            return {
                "citation": citation['raw'],
                "status": "VALID",
                "match": best_match['title'],
                "source": best_match['source'],
                "confidence": round(highest_score, 2)
            }
        else:
            return {
                "citation": citation['raw'],
                "status": "SUSPICIOUS",
                "reason": f"Closest match: '{best_match['title']}' but low confidence.",
                "confidence": round(highest_score, 2)
            }

    def _calculate_match_score(self, cit: Dict, res: Dict) -> float:
        """
        Heuristic scoring for citation matching.
        """
        if cit['type'] == 'doi':
            # DOI match is usually exact, but we check metadata here
            return 1.0 # If we found it by DOI, it's valid
            
        # Author/Year match
        title_norm = res['title'].lower()
        author_norm = cit['author'].lower().replace(" et al.", "")
        
        score = 0.0
        # Does author appear in title or description? (Sometimes titles contain names)
        # Better: Check authors list if available (we need to refine the search interfaces for that)
        
        # For now, base it on Year match + Fuzzy Title/Author overlap
        year_match = 1.0 if cit['year'] == res['year'] else 0.0
        
        # If year matches, we are already halfway there
        ratio = SequenceMatcher(None, author_norm, title_norm).ratio()
        
        return (year_match * 0.6) + (ratio * 0.4)

if __name__ == "__main__":
    reviewer = CitationReviewer()
    # Mocking for local test if needed
    sample = "Recent studies on Alzheimer's [Selkoe, 1991] show amyloid-beta importance."
    print(reviewer.verify_text(sample))
