"""
Plagiarism & Research Integrity Module
Enforces mandatory similarity checks against the internal Knowledge Base.
"""
import logging
import asyncio
from typing import Dict, List, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# We assume sentence-transformers is installed for semantics
# from sentence_transformers import SentenceTransformer, util
# For lightness/dependency management, we will use the vector_store's existing embeddings if possible,
# or a simple TF-IDF for the 'fast' check first.

from modules.rag.vector_store import get_vector_store

logger = logging.getLogger("compliance.plagiarism")

class PlagiarismChecker:
    def __init__(self):
        self.vector_store = get_vector_store()
        # Initialize a basic vectorizer for lexical checks
        self.tfidf = TfidfVectorizer(stop_words='english')

    async def check_content(self, text: str, threshold: float = 0.15) -> Dict[str, Any]:
        """
        Check the provided text against the internal corpus (Knowledge Base).
        Returns a report with similarity score and flagged status.
        
        Thresholds:
        - < 0.15: Safe (Green)
        - 0.15 - 0.25: Warning (Yellow) -> Requires Rewrite
        - > 0.25: Block (Red)
        """
        logger.info(f"Running plagiarism check on {len(text)} chars...")
        
        # 1. Semantic Check (using Vector Store)
        # We chunk the text and query the vector store to see if any chunk
        # is too close to existing documents.
        chunks = self._chunk_text(text)
        max_semantic_score = 0.0
        flagged_sections = []
        
        for chunk in chunks:
            # Search KB for this chunk
            results = await self.vector_store.search(chunk, k=1)
            if results:
                # Assuming vector store returns a score/distance
                # We need to normalize it. 
                # If using FAISS L2, lower is better. If Inner Product, higher is better.
                # Let's rely on a lexical fallback if semantic score isn't normalized.
                
                # For robustness in this v1, let's use the explicit Lexical Check against retrieved context
                # Retreive candidate source
                source_text = results[0].get('text', '')
                similarity = self._calculate_lexical_similarity(chunk, source_text)
                
                if similarity > max_semantic_score:
                    max_semantic_score = similarity
                    
                if similarity > threshold:
                    flagged_sections.append({
                        "text": chunk[:50] + "...",
                        "similarity": round(similarity * 100, 1),
                        # "source": results[0].get('metadata', {}).get('source', 'Unknown')
                        "source": "Internal KB Match" # quick fix for metadata access
                    })
        
        status = "PASSED"
        risk_level = "LOW"
        
        if max_semantic_score > 0.25:
            status = "BLOCKED"
            risk_level = "HIGH"
        elif max_semantic_score > 0.15:
            status = "FLAGGED"
            risk_level = "MEDIUM"
            
        return {
            "status": status,
            "overall_similarity": round(max_semantic_score * 100, 1),
            "risk_level": risk_level,
            "flagged_sections": flagged_sections,
            "details": f"Max similarity {round(max_semantic_score * 100, 1)}% against internal headers."
        }

    def _chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """Split text into checking chunks."""
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    def _calculate_lexical_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity of TF-IDF vectors."""
        if not text1 or not text2:
            return 0.0
        try:
            tfidf_matrix = self.tfidf.fit_transform([text1, text2])
            return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        except Exception:
            return 0.0

# Singleton
plagiarism_checker = PlagiarismChecker()
