"""
BioDockify Writing Module: LanguageTool Integration
Enforces academic tone, grammar correctness, and avoiding passive voice.
Requires a local LanguageTool server (or use public API for low volume).
"""

import requests
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class GrammarIssue:
    message: str
    context: str
    offset: int
    length: int
    rule_id: str
    category: str

class LanguageToolChecker:
    """
    Wrapper for LanguageTool API.
    Can point to local server (http://localhost:8010/v2) or public API.
    """
    
    def __init__(self, endpoint: str = "http://localhost:8010/v2"):
        self.endpoint = endpoint
        self.public_api = "https://api.languagetool.org/v2" 
        # Fallback to public for demo if local not found, BUT warn user
        self.use_public = False 
        
    def check_text(self, text: str) -> List[GrammarIssue]:
        """
        Scans text for grammar and style issues.
        """
        url = f"{self.endpoint}/check"
        params = {
            "text": text,
            "language": "en-US",
            "enabledCategories": "STYLE,CASING,GRAMMAR,TYPOGRAPHY"
        }
        
        try:
            resp = requests.post(url, data=params, timeout=5)
            
            # Fallback logic if local server missing
            if resp.status_code != 200 and not self.use_public:
                logger.warning("Local LanguageTool not found. Switching to Public API (Limited).")
                url = f"{self.public_api}/check"
                resp = requests.post(url, data=params, timeout=10)

            if resp.status_code == 200:
                matches = resp.json().get("matches", [])
                issues = []
                for m in matches:
                    issues.append(GrammarIssue(
                        message=m["message"],
                        context=m["context"]["text"],
                        offset=m["offset"],
                        length=m["length"],
                        rule_id=m["rule"]["id"],
                        category=m["rule"]["category"]["id"]
                    ))
                return issues
            else:
                logger.error(f"LanguageTool API failed: {resp.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"LanguageTool check failed: {e}")
            return []
            
    def get_tone_score(self, issues: List[GrammarIssue]) -> float:
        """
        Calculates a simple 'Academic Tone Score' (1.0 - 0.0) based on style issues.
        """
        if not issues:
            return 1.0
            
        style_errors = sum(1 for i in issues if i.category == 'STYLE')
        # Penalty model: -0.05 per style error
        score = max(0.0, 1.0 - (style_errors * 0.05))
        return score
