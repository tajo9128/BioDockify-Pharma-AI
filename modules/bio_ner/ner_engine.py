"""
Bio-NER Engine - BioDockify Pharma Research AI
Biomedical Named Entity Recognition with Hybrid Transformers/Regex Logic.
"""

import os
import re
import logging
from typing import Dict, List, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BioDockify.NER")

class RegexMatcher:
    """
    Lightweight fallback matcher for offline/zero-cost mode.
    Identifies entities based on common linguistic patterns.
    """
    
    PATTERNS = {
        "drugs": [
            r"\b\w+vir\b",       # Antivirals (e.g., acyclovir)
            r"\b\w+mab\b",       # Monoclonal antibodies (e.g., rituximab)
            r"\b\w+ib\b",        # Tyrosine kinase inhibitors (e.g., imatinib)
            r"\b\w+stat\b",      # Enzyme inhibitors
        ],
        "diseases": [
            r"\b\w+ syndrome\b",
            r"\b\w+ disease\b",
            r"\bcancer\b",
            r"\btumor\b",
            r"\b\w+itis\b",      # Inflammation
            r"\b\w+osis\b",      # Condition
            r"\b\w+emia\b",      # Blood condition
            r"\b\w+pathy\b"      # Disorder
        ],
        "genes": [
            r"\b[A-Z]{2,}[0-9]+\b",  # Gene symbols like BRCA1, TP53, EGFR
            r"\b[A-Z]{3,}\b"         # Capitalized acronyms (heuristic)
        ]
    }

    def extract(self, text: str) -> Dict[str, List[str]]:
        results = {
            "drugs": [],
            "diseases": [],
            "genes": []
        }
        
        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE if category == "diseases" else 0)
                for match in matches:
                    word = match.group(0)
                    # Simple filter to avoid common stop words if needed
                    if len(word) > 3 and word not in results[category]:
                        results[category].append(word)
                        
        return results

class BioNER:
    """
    Main Bio-NER Engine.
    Attempts to load local Transformer models; falls back to RegexMatcher.
    """
    
    def __init__(self, model_path: str = None):
        self.use_transformers = False
        self.model = None
        self.tokenizer = None
        self.fallback_matcher = RegexMatcher()
        
        # Check for models in brain/models
        # For MVP/Zero-cost, we default to Regex unless user downloaded a model
        # Logic to load huggingface model would go here
        
        if model_path and os.path.exists(model_path):
             self._load_transformers(model_path)
        else:
            logger.info("No local NER model found. Using Regex Fallback mode.")

    def _load_transformers(self, path: str):
        try:
            from transformers import AutoTokenizer, AutoModelForTokenClassification
            from transformers import pipeline
            
            logger.info(f"Loading NER model from {path}...")
            self.tokenizer = AutoTokenizer.from_pretrained(path)
            self.model = AutoModelForTokenClassification.from_pretrained(path)
            self.nlp = pipeline("ner", model=self.model, tokenizer=self.tokenizer, aggregation_strategy="simple")
            self.use_transformers = True
            logger.info("Transformer model loaded successfully.")
        except ImportError:
            logger.warning("Transformers library missing. Using Regex fallback.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities from text.
        """
        if self.use_transformers:
            return self._extract_with_transformers(text)
        else:
            return self.fallback_matcher.extract(text)

    def _extract_with_transformers(self, text: str) -> Dict[str, List[str]]:
        # Placeholder for transformer logic mapping pipeline output to dict
        results = {"drugs": [], "diseases": [], "genes": []}
        predictions = self.nlp(text)
        # Map based on model labels (e.g. B-DISEASE -> diseases)
        # This implementation depends on specific model schema
        return results

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "type": "Transformer" if self.use_transformers else "RegexMatcher",
            "active": True
        }

if __name__ == "__main__":
    ner = BioNER()
    sample = "The patient was treated with rituximab for arthritis. BRCA1 mutation detected."
    print(f"Input: {sample}")
    print(f"Output: {ner.extract_entities(sample)}")
