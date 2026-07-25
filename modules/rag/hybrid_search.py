"""
BioDockify Knowledge Base — Hybrid Search Engine

Combines semantic (vector) search with keyword (BM25) search using
Reciprocal Rank Fusion (RRF). This dramatically improves retrieval for
pharma-specific queries where exact terms matter:

  - Drug names: "aspirin", "imatinib", "ASPP 8273"
  - Gene mutations: "BRAF V600E", "EGFR L858R"
  - SMILES strings: "CC(=O)OC1=CC=CC=C1C(=O)O"
  - Assay IDs: "NCT01234567", "CHEMBL1234"

Pure semantic search misses these because they don't cluster in embedding
space. BM25 catches exact matches; RRF merges both ranked lists.

Uses only stdlib + rank_bm25 (tiny pure-Python package). Falls back to
vector-only search if rank_bm25 is not installed.

Usage:
    from modules.rag.hybrid_search import HybridSearcher
    searcher = HybridSearcher()
    searcher.index(chunks)  # list of {id, content, ...}
    results = searcher.search("aspirin COX-2 inhibition", top_k=10)
"""

import re
import math
import logging
from typing import List, Dict, Any, Optional, Tuple

log = logging.getLogger("rag.hybrid_search")

# RRF constant (standard value from the original paper)
RRF_K = 60


class HybridSearcher:
    """Hybrid search combining BM25 keyword matching with vector similarity.

    Falls back gracefully:
      - If rank_bm25 is not installed → vector-only
      - If no vector index → BM25-only
      - If neither → simple substring search
    """

    def __init__(self):
        self._bm25 = None
        self._chunks: List[Dict[str, Any]] = []
        self._texts: List[str] = []
        self._tokenized: List[List[str]] = []
        self._has_bm25 = False

        try:
            from rank_bm25 import BM25Okapi
            self._bm25_cls = BM25Okapi
            self._has_bm25 = True
        except ImportError:
            log.info("rank_bm25 not installed — hybrid search falls back to vector-only")
            self._has_bm25 = False

    def index(self, chunks: List[Dict[str, Any]]):
        """Index chunks for BM25 search.

        Args:
            chunks: List of chunk dicts with a 'content' key
        """
        self._chunks = chunks
        self._texts = [c.get("content", "") for c in chunks]
        self._tokenized = [_tokenize(t) for t in self._texts]

        if self._has_bm25 and self._tokenized:
            self._bm25 = self._bm25_cls(self._tokenized)
            log.info(f"BM25 index built: {len(self._tokenized)} chunks")

    def search(self, query: str, top_k: int = 10,
               vector_scores: Optional[List[Tuple[int, float]]] = None) -> List[Dict[str, Any]]:
        """Run hybrid search.

        Args:
            query: Search query
            top_k: Number of results to return
            vector_scores: Optional pre-computed vector search results as
                           [(chunk_index, score), ...]. If None, only BM25 is used.

        Returns:
            List of chunk dicts with added 'score' and 'rank' fields
        """
        if not self._chunks:
            return []

        # Get BM25 rankings (or keyword fallback if rank_bm25 not installed)
        if self._has_bm25:
            bm25_rankings = self._bm25_search(query, top_k * 3)
        else:
            bm25_rankings = self._keyword_search(query, top_k * 3)

        # Get vector rankings (if provided)
        vector_rankings = []
        if vector_scores:
            # Sort by score descending (lower distance = better for L2)
            sorted_vec = sorted(vector_scores, key=lambda x: x[1])
            vector_rankings = [(idx, rank) for rank, (idx, _) in enumerate(sorted_vec)]

        # If we have neither BM25 nor vector, try keyword fallback
        if not bm25_rankings and not vector_rankings:
            bm25_rankings = self._keyword_search(query, top_k * 3)

        # Fuse with RRF
        fused = self._fuse_rrf(bm25_rankings, vector_rankings, top_k)

        # Build results
        results = []
        for chunk_idx, score in fused:
            chunk = dict(self._chunks[chunk_idx])
            chunk["hybrid_score"] = round(score, 4)
            results.append(chunk)

        return results

    def _bm25_search(self, query: str, top_k: int) -> List[Tuple[int, int]]:
        """Run BM25 search and return [(chunk_index, rank), ...]."""
        if not self._has_bm25 or not self._bm25:
            return []

        tokens = _tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        return [(idx, rank) for rank, idx in enumerate(ranked[:top_k])]

    def _keyword_search(self, query: str, top_k: int) -> List[Tuple[int, int]]:
        """Simple keyword-based search fallback when rank_bm25 is not installed.

        Scores each chunk by counting query term matches (case-insensitive).
        Uses the same pharma-aware tokenizer.
        """
        query_tokens = set(_tokenize(query))
        if not query_tokens:
            return []

        scored = []
        for idx, tokens in enumerate(self._tokenized):
            chunk_token_set = set(tokens)
            overlap = len(query_tokens & chunk_token_set)
            if overlap > 0:
                scored.append((idx, overlap))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [(idx, rank) for rank, (idx, _) in enumerate(scored[:top_k])]

    def _fuse_rrf(self, bm25_results: List[Tuple[int, int]],
                  vector_results: List[Tuple[int, int]],
                  top_k: int) -> List[Tuple[int, float]]:
        """Fuse two ranked lists using Reciprocal Rank Fusion.

        RRF score = sum of 1/(k + rank) for each list where the doc appears.
        """
        scores: Dict[int, float] = {}

        for chunk_idx, rank in bm25_results:
            scores[chunk_idx] = scores.get(chunk_idx, 0) + 1.0 / (RRF_K + rank + 1)

        for chunk_idx, rank in vector_results:
            scores[chunk_idx] = scores.get(chunk_idx, 0) + 1.0 / (RRF_K + rank + 1)

        # Sort by fused score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        return ranked[:top_k]


def _tokenize(text: str) -> List[str]:
    """Simple tokenizer for BM25.

    Handles pharma-specific terms:
    - Splits on whitespace and punctuation
    - Preserves alphanumeric tokens (catches NCT01234567, CHEMBL1234)
    - Lowercases for case-insensitive matching
    - Splits camelCase (BRAFv600E → braf, v600e)
    """
    # Lowercase
    text = text.lower()

    # Replace common pharma separators with spaces
    text = re.sub(r"[_\-/\\]", " ", text)

    # Split camelCase: V600E → v 600 e, BRAFV600E → braf v 600 e
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = text.lower()

    # Extract alphanumeric tokens (catches NCT01234567, CHEMBL1234)
    tokens = re.findall(r"[a-z0-9]+", text)

    # Also split long alphanumeric into parts (NCT01234567 → nct, 01234567)
    expanded = []
    for tok in tokens:
        expanded.append(tok)
        # Split letter/number boundaries
        parts = re.findall(r"[a-z]+|[0-9]+", tok)
        if len(parts) > 1:
            expanded.extend(parts)

    return expanded
