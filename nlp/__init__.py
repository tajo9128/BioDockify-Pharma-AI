"""
Pharma-Specific NLP Pipeline

This package provides a complete NLP pipeline for pharmaceutical literature analysis,
integrating GROBID, SciBERT, FAISS, and BERTopic.

Pipeline Flow:
PDF → GROBID → Structured Sections → SciBERT → Embeddings → FAISS → Clusters → BERTopic → Themes
                                                          ↓
                                                      Gap Analysis

Components:
- GROBIDParser: Parse scientific PDFs into structured TEI XML
- SciBERTEmbedder: Generate semantic embeddings using SciBERT
- DrugDiscoveryThemeExtractor: Extract themes using BERTopic
- PreclinicalGapAnalyzer: Detect research gaps and assess novelty

Example Usage:
    from nlp import GROBIDParser, SciBERTEmbedder, DrugDiscoveryThemeExtractor, PreclinicalGapAnalyzer

    # Parse PDFs
    grobid = GROBIDParser()
    papers = grobid.batch_parse(['paper1.pdf', 'paper2.pdf'])

    # Generate embeddings
    embedder = SciBERTEmbedder()
    abstracts = [p['abstract'] for p in papers]
    embeddings = embedder.embed_batch(abstracts)

    # Extract themes
    theme_extractor = DrugDiscoveryThemeExtractor()
    themes = theme_extractor.extract_themes(abstracts)

    # Find research gaps
    gap_analyzer = PreclinicalGapAnalyzer(embedder)
    gaps = gap_analyzer.detect_research_gaps("Alzheimer's", papers)
"""

from .grobid_parser import GROBIDParser, ParsedPaper
from .scibert_embedder import SciBERTEmbedder
from .bertopic_extractor import DrugDiscoveryThemeExtractor
from .gap_analyzer import PreclinicalGapAnalyzer

__version__ = '1.0.0'
__author__ = 'BioDockify Team'

__all__ = [
    'GROBIDParser',
    'ParsedPaper',
    'SciBERTEmbedder',
    'DrugDiscoveryThemeExtractor',
    'PreclinicalGapAnalyzer',
]
