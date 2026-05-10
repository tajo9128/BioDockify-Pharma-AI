"""
BioDockify Safety Module: Detoxify Guard
Scans generated text for safety risks, toxicity, and hyperbolic claims.
"""

import logging
from dataclasses import dataclass
from typing import List, Dict

logger = logging.getLogger(__name__)

@dataclass
class SafetyReport:
    is_safe: bool
    toxicity_score: float
    issues: List[str]

class DetoxifyGuard:
    """
    Safety guardrail for medical text generation.
    """
    
    def scan_text(self, text: str) -> SafetyReport:
        """
        Scans text for potential risks.
        For Phase 4 MVP, uses heuristic keyword scanning for 'Dangerous Hyperbole'.
        Full transformer implementation to follow in v2.2.
        """
        issues = []
        score = 0.0
        
        # 1. Hyperbole Check (Regex heuristics for MVP)
        hyperbolic_terms = [
            "cure for cancer", "100% effective", "miracle drug", 
            "guaranteed results", "secret remedy"
        ]
        
        lower_text = text.lower()
        for term in hyperbolic_terms:
            if term in lower_text:
                issues.append(f"Hyperbolic claim detected: '{term}'")
                score += 0.3
                
        # 2. Uncertainty Check
        # Pharma writing should be tentative (suggests, indicates) vs definitive (proves)
        if "proves that" in lower_text:
             issues.append("Definitive language 'proves that' detected. Consider 'suggests'.")
             score += 0.1
             
        is_safe = score < 0.5
        
        return SafetyReport(is_safe, score, issues)
