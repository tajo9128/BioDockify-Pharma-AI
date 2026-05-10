"""
BioDockify Academic Compliance Module
The "Conscience" of the agent. Enforces Citation Locks, Academic Tone, and Safety Gates.
Unified module merging logic from modules/writing and modules/compliance.
"""

import re
import logging
import threading
import statistics
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ComplianceReport:
    passed: bool
    score: float
    issues: List[Union[str, Dict[str, str]]]
    citations_count: int
    metrics: Dict[str, Any] = None

class AcademicComplianceEngine:
    """
    Unified Academic Compliance Engine.
    Enforces 'Pharma-Grade' rules on agent output.
    """
    
    def __init__(self, strictness: str = "high"):
        self.strictness = strictness # low, medium, high
        
        # Academic phrase replacements (Generic AI -> Scientific)
        # Bug #2 Fixed: Escaping literals and using raw strings for regex
        self.style_rules = {
            r"\bIn conclusion\b,?": "Collectively, these findings suggest",
            r"\bIt is important to note that\b": "Notably,",
            r"\bThis study proves\b": "These results demonstrate, within experimental limits,",
            r"\bundoubtedly\b": "strongly",
            r"\bgame-changer\b": "significant advancement",
            r"\brevolutionize\b": "transform",
            r"\bdelve into\b": "investigate",
            r"\bcomprehensive overview\b": "systematic review",
        }
        
        # Regex for common citation patterns: (Smith et al., 2023) or [1] or [1-3]
        self.citation_pattern = re.compile(r"\(.*?, \d{4}\)|\[[\d,\- ]+\]")
        
        # Tokens that signal overconfidence or unscientific hype
        self.hype_tokens = [
            "proves", "undoubtedly", "game-changer", "miracle", "obviously", 
            "perfect", "guaranteed", "revolutionary"
        ]

    def analyze_text(self, text: str, sources: List[Dict] = None) -> ComplianceReport:
        """
        Run full compliance analysis on the text draft.
        Standardizes return type (Bug #10).
        """
        sources = sources or []
        sentences = self._split_sentences(text)
        if not sentences:
            return self._empty_report()

        # 1. Style & Tone Check
        style_issues = self._check_style(text)
        tone_warnings = self.check_academic_tone(text)
        combined_issues = style_issues + tone_warnings
        
        # 2. Evidence Density Check (Bug #11: Threshold 0.7)
        evidence_score = self._check_evidence_density(sentences)
        
        # 3. Sentence Variability Check (Bug #11: Threshold 0.5)
        variability_score = self._check_sentence_variability(sentences)

        # 4. Mandatory Citation Lock
        citations_found = len(sources)
        min_required = 3 if self.strictness == "high" else 1
        lock_passed = citations_found >= min_required
        
        if not lock_passed:
            combined_issues.append(f"Insufficient Sources: Found {citations_found}, Need {min_required}")

        # Overall Compliance Status
        is_compliant = (
            len(style_issues) == 0 and 
            evidence_score >= 0.7 and 
            variability_score >= 0.5 and
            lock_passed
        )

        # Calculate weighted score (Bug #11)
        # Tone: 40%, Evidence: 40%, Variability: 20%
        final_score = (
            (1.0 - min(1.0, len(style_issues) * 0.1)) * 0.4 +
            evidence_score * 0.4 +
            variability_score * 0.2
        )

        return ComplianceReport(
            passed=is_compliant,
            score=round(final_score, 2),
            issues=combined_issues,
            citations_count=self._count_citations(text),
            metrics={
                "sentence_count": len(sentences),
                "evidence_density": evidence_score,
                "variability": variability_score,
                "lock_status": "Passed" if lock_passed else "Failed"
            }
        )

    def verify_evidence_threshold(self, text: str, sources: List[Dict]) -> ComplianceReport:
        """Legacy compatibility wrapper for threshold check."""
        return self.analyze_text(text, sources)

    def check_academic_tone(self, text: str) -> List[str]:
        """Scans for 'Reviewer Triggers' - words that sound unscientific."""
        warnings = []
        lower_text = text.lower()
        
        for token in self.hype_tokens:
            if token in lower_text:
                warnings.append(f"Avoid overconfident term: '{token}'. Use 'suggests' or 'indicates'.")
                
        # Check for first-person usage (I, me, my) in formal sections
        if re.search(r"\b(i|me|my)\b", lower_text):
            warnings.append("Avoid first-person pronouns (I/me) in objective reporting.")
            
        return warnings

    def _check_style(self, text: str) -> List[Dict[str, str]]:
        issues = []
        for pattern, replacement in self.style_rules.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                issues.append({
                    "type": "Tone",
                    "found": match.group(0),
                    "suggestion": replacement,
                    "context": text[max(0, match.start()-20):min(len(text), match.end()+20)]
                })
        return issues

    def _check_evidence_density(self, sentences: List[str]) -> float:
        """Ratio of sentences with citations to total sentences."""
        cited_sentences = 0
        for sent in sentences:
            if self.citation_pattern.search(sent):
                cited_sentences += 1
        
        if not sentences: return 0.0
        return round(cited_sentences / len(sentences), 2)

    def _check_sentence_variability(self, sentences: List[str]) -> float:
        """Calculate variance in sentence length. Higher variance = more human-like flow."""
        if len(sentences) < 2: return 1.0
        
        lengths = [len(sent.split()) for sent in sentences]
        try:
            stdev = statistics.stdev(lengths)
            mean = statistics.mean(lengths)
            # Coefficient of Variation (CV). Human writing usually has CV > 0.4
            cv = stdev / mean if mean > 0 else 0
            # Normalize score (0.0 to 1.0)
            score = min(cv * 2.5, 1.0) 
            return round(score, 2)
        except Exception:
            return 0.5

    def detect_contradictions(self, source_a_summary: str, source_b_summary: str) -> Optional[str]:
        """Placeholder for LLM-based logic to detect contradicting evidence."""
        return None

    def generate_disclosure(self, model_name: str) -> str:
        """Generates standard AI disclosure statement."""
        return (
            f"**Declaration of AI Usage**: This report was assisted by BioDockify ({model_name}) "
            "for literature retrieval and initial drafting. All scientific claims were verified "
            "against the cited primary sources, and the final text was reviewed and approved by the author."
        )

    def _count_citations(self, text: str) -> int:
        return len(self.citation_pattern.findall(text))

    def _split_sentences(self, text: str) -> List[str]:
        return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]

    def _empty_report(self) -> ComplianceReport:
        return ComplianceReport(False, 0.0, ["Empty content provided."], 0, {})

# Singleton Implementation
_engine_instance = None
_engine_lock = threading.Lock()

def get_compliance_engine(strictness: str = "high") -> AcademicComplianceEngine:
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = AcademicComplianceEngine(strictness=strictness)
        return _engine_instance

if __name__ == "__main__":
    engine = get_compliance_engine()
    dummy_text = "This result proves that the drug is a miracle cure. [1]"
    report = engine.analyze_text(dummy_text, [{"id": "ref1"}])
    print(f"Compliance Report: {report}")
