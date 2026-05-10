
"""
Research Topic Detector
Detects research topics in user messages and triggers auto-research workflow.
"""
import re
import logging
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ResearchTopic:
    """Detected research topic with metadata."""
    topic: str
    research_type: str  # "phd", "grand", "review_article", "general"
    confidence: float
    keywords: List[str]

class ResearchTopicDetector:
    """
    Detects research topics in user messages.
    Triggers auto-research workflow when detected.
    """
    
    RESEARCH_INDICATORS = [
        r"\b(research|study|investigate|explore|analyze|review)\b",
        r"\b(PhD|thesis|dissertation|doctoral)\b",
        r"\b(literature|systematic|meta-analysis)\s+(review|study)\b",
        r"\b(grant|proposal|funding)\b",
        r"\b(impact|effect|relationship|correlation)\s+(of|between|on)\b",
    ]
    
    PHARMA_INDICATORS = [
        r"\b(drug|medication|therapy|treatment)\b",
        r"\b(disease|disorder|syndrome|condition)\b",
        r"\b(clinical trial|phase\s+[IiV]+|randomized)\b",
        r"\b(biomarker|mechanism|pathway)\b",
        r"\b(precursor|synthesis|formulation)\b",
    ]
    
    RESEARCH_TYPES = {
        "phd": [
            r"\b(PhD|doctoral|dissertation|thesis)\s+(research|study|project)\b",
            r"\b(complete|full|comprehensive)\s+(research|study)\b"
        ],
        "grand": [
            r"\b(grand|major|large-scale)\s+(research|project|study)\b",
            r"\b(multi-center|international|collaborative)\s+(research|study)\b"
        ],
        "review_article": [
            r"\b(systematic|literature|meta-analysis)\s+(review|article)\b",
            r"\b(write|create|draft)\s+(review|article|paper)\b"
        ]
    }
    
    def detect(self, message: str) -> Optional[ResearchTopic]:
        """Detect if message contains a research topic."""
        message_lower = message.lower()
        
        has_research_indicator = any(
            re.search(pattern, message_lower, re.IGNORECASE)
            for pattern in self.RESEARCH_INDICATORS
        )
        
        if not has_research_indicator:
            return None
        
        research_type = "general"
        confidence = 0.5
        
        for rtype, patterns in self.RESEARCH_TYPES.items():
            if any(re.search(pattern, message_lower, re.IGNORECASE) for pattern in patterns):
                research_type = rtype
                confidence = 0.8
                break
        
        topic = self._extract_topic(message)
        keywords = self._extract_keywords(message)
        
        has_pharma = any(
            re.search(pattern, message_lower, re.IGNORECASE)
            for pattern in self.PHARMA_INDICATORS
        )
        if has_pharma:
            confidence = min(confidence + 0.15, 1.0)
        
        return ResearchTopic(
            topic=topic,
            research_type=research_type,
            confidence=confidence,
            keywords=keywords
        )
    
    def _extract_topic(self, message: str) -> str:
        """Extract main research topic from message."""
        topic = message
        prefixes_to_remove = [
            r"^(I want to|I need to|Please|Can you|Could you)\s+",
            r"^(research|study|investigate|explore|analyze|review)\s+",
            r"^(a|an|the)\s+"
        ]
        
        for prefix in prefixes_to_remove:
            topic = re.sub(prefix, "", topic, flags=re.IGNORECASE)
        
        return topic.strip()
    
    def _extract_keywords(self, message: str) -> List[str]:
        """Extract research keywords from message."""
        keywords = []
        
        for pattern in self.PHARMA_INDICATORS:
            matches = re.findall(pattern, message, re.IGNORECASE)
            keywords.extend(matches)
        
        capitalized = re.findall(r"\b[A-Z][a-z]+\b", message)
        keywords.extend(capitalized)
        
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)
        
        return unique_keywords[:10]
