# Pharma-Specific NLP Pipeline

A comprehensive NLP pipeline for pharmaceutical literature analysis, integrating GROBID, SciBERT, FAISS, and BERTopic for automated research gap detection and theme extraction.

## Pipeline Architecture

```
PDF → GROBID → Structured Sections → SciBERT → Embeddings → FAISS → Clusters → BERTopic → Themes
                                                          ↓
                                                      Gap Analysis
```

## Features

- **PDF Parsing**: Extract structured content from scientific PDFs using GROBID
- **Semantic Embeddings**: Generate domain-aware embeddings using SciBERT
- **Similarity Search**: Fast vector similarity search with FAISS
- **Clustering**: Automatic document clustering based on semantic similarity
- **Topic Modeling**: Extract research themes using BERTopic
- **Gap Detection**: Identify under-explored research areas
- **Novelty Scoring**: Assess research hypothesis novelty

## Installation

### Prerequisites

1. Python 3.8 or higher
2. Docker (for GROBID)

### Install Dependencies

```bash
cd nlp
pip install -r requirements.txt
```

### Start GROBID

GROBID is required for PDF parsing. Run it using Docker:

```bash
docker run -d --rm -p 8070:8070 lfoppiano/grobid:0.7.2
```

Verify GROBID is running:

```bash
curl http://localhost:8070/api/isalive
```

## Quick Start

```python
from nlp import (
    GROBIDParser,
    SciBERTEmbedder,
    DrugDiscoveryThemeExtractor,
    PreclinicalGapAnalyzer
)

# 1. Parse PDFs
grobid = GROBIDParser()
papers = grobid.batch_parse(['paper1.pdf', 'paper2.pdf'])

# 2. Generate embeddings
embedder = SciBERTEmbedder()
abstracts = [p['abstract'] for p in papers]
embeddings = embedder.embed_batch(abstracts)

# 3. Extract themes
theme_extractor = DrugDiscoveryThemeExtractor()
themes = theme_extractor.extract_themes(abstracts)
print(f"Found {themes['n_topics']} themes")

# 4. Find research gaps
gap_analyzer = PreclinicalGapAnalyzer(embedder)
gaps = gap_analyzer.detect_research_gaps("Alzheimer's", papers)
print(f"Identified {len(gaps)} research gaps")
```

## Components

### 1. GROBID Parser

Parse scientific PDFs into structured TEI XML format.

#### Usage

```python
from nlp import GROBIDParser

# Initialize
grobid = GROBIDParser(grobid_url="http://localhost:8070")

# Parse single PDF
paper = grobid.parse_pdf('paper.pdf')
print(f"Title: {paper.title}")
print(f"Abstract: {paper.abstract}")
print(f"Sections: {len(paper.sections)}")
print(f"References: {len(paper.references)}")

# Parse header only (faster)
metadata = grobid.parse_header_only('paper.pdf')

# Batch parse multiple PDFs
results = grobid.batch_parse(['paper1.pdf', 'paper2.pdf'], max_workers=4)

# Get statistics
stats = grobid.get_statistics(parsed_papers)
```

#### Features

- Full text parsing with sections
- Metadata extraction (title, authors, keywords)
- Reference extraction
- Figure and table detection
- Batch processing with parallel execution
- Error handling and retry logic

### 2. SciBERT Embedder

Generate semantic embeddings using the SciBERT model.

#### Usage

```python
from nlp import SciBERTEmbedder

# Initialize
embedder = SciBERTEmbedder(
    model_name='allenai/scibert_scivocab_uncased',
    device='cuda'  # or 'cpu'
)

# Single text embedding
embedding = embedder.embed_text("Drug discovery methods")
print(f"Shape: {embedding.shape}")  # (768,)

# Batch embeddings
embeddings = embedder.embed_batch(texts, batch_size=32)

# Compute similarity
similarity = embedder.compute_similarity(emb1, emb2)

# Build FAISS index
index = embedder.build_faiss_index(embeddings, index_type='flat')

# Search similar documents
distances, indices = embedder.search_similar(index, query_text, top_k=10)

# Cluster papers
clusters = embedder.cluster_papers(abstracts, n_clusters=10)

# Save/load
embedder.save_embeddings(embeddings, 'embeddings.npy')
embedder.save_faiss_index(index, 'index.faiss')
```

#### Features

- Single and batch embedding generation
- Cosine similarity computation
- FAISS index building (Flat, IVF, HNSW)
- K-means clustering
- Save/load embeddings and indexes
- GPU support

### 3. Drug Discovery Theme Extractor

Extract research themes using BERTopic.

#### Usage

```python
from nlp import DrugDiscoveryThemeExtractor

# Initialize
extractor = DrugDiscoveryThemeExtractor(
    min_topic_size=10,
    nr_topics='auto'
)

# Extract themes
themes = extractor.extract_themes(abstracts)

# Get topic keywords
keywords = extractor.get_topic_keywords(topic_id=0, n_words=10)

# Get representative documents
docs = extractor.get_topic_documents(topic_id=0, documents=abstracts)

# Find similar documents
similar_docs, similarities = extractor.find_similar_documents("query", top_n=10)

# Visualize topics
extractor.visualize_topics('topics.html')
extractor.visualize_topic_hierarchy('hierarchy.html')
extractor.visualize_topic_distribution('distribution.html')

# Save model
extractor.save_model('bertopic_model')
```

#### Features

- Automatic topic extraction
- Hierarchical topic modeling
- Pharmaceutical stopwords filtering
- Interactive visualizations
- Document similarity search
- Save/load models
- Topic merging and reduction

### 4. Preclinical Gap Analyzer

Detect research gaps and assess novelty.

#### Usage

```python
from nlp import PreclinicalGapAnalyzer

# Initialize
analyzer = PreclinicalGapAnalyzer(
    embedder=embedder,
    faiss_index=index,
    neo4j_client=None  # Optional Neo4j client
)

# Assess hypothesis novelty
score = analyzer.assess_novelty(
    hypothesis="Investigating novel amyloid-beta pathways",
    papers=papers,
    method='semantic'  # or 'entity', 'combined'
)
print(f"Novelty Score: {score:.3f}")

# Detect research gaps
gaps = analyzer.detect_research_gaps(
    research_area="Alzheimer's",
    papers=papers
)

# Rank gaps by potential
gaps = analyzer.rank_gaps_by_potential(gaps)

# Generate report
report = analyzer.generate_gap_report(gaps, 'report.json')

# Save/load gaps
analyzer.save_gaps(gaps, 'gaps.json')
loaded = analyzer.load_gaps('gaps.json')
```

#### Features

- Entity frequency analysis
- Under-explored combination detection
- Semantic gap detection
- Graph-based gap detection (with Neo4j)
- Novelty scoring (semantic, entity, combined)
- Gap ranking and prioritization
- Comprehensive gap reports

## Advanced Usage

### Custom Configuration

```python
# SciBERT with custom settings
embedder = SciBERTEmbedder(
    model_name='allenai/scibert_basevocab_uncased',
    device='cuda',
    max_length=512
)

# BERTopic with custom settings
extractor = DrugDiscoveryThemeExtractor(
    embedding_model='allenai/scibert_scivocab_uncased',
    min_topic_size=5,
    nr_topics=20,
    umap_n_components=10,
    umap_n_neighbors=15,
    hdbscan_min_cluster_size=10
)

# Gap analyzer with custom thresholds
analyzer = PreclinicalGapAnalyzer(
    embedder=embedder,
    min_entity_count=3,
    density_threshold=0.1
)
```

### GPU Acceleration

```python
# SciBERT on GPU
embedder = SciBERTEmbedder(device='cuda')

# FAISS on GPU
index = embedder.build_faiss_index(embeddings, use_gpu=True)

# Clustering on GPU
clusters = embedder.cluster_papers(
    abstracts,
    n_clusters=10,
    niter=20
)
```

### Integration with Neo4j

For graph-based gap detection:

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

analyzer = PreclinicalGapAnalyzer(
    embedder=embedder,
    faiss_index=index,
    neo4j_client=driver
)

gaps = analyzer.detect_research_gaps("Alzheimer's", papers)
```

## Examples

Run the complete integration example:

```bash
cd nlp
python example_usage.py
```

## Output

### Parsed Paper Structure

```python
{
    'title': 'Paper Title',
    'abstract': 'Abstract text...',
    'sections': [
        {'heading': 'Introduction', 'text': '...'},
        {'heading': 'Methods', 'text': '...'}
    ],
    'references': [
        {'title': 'Reference title', 'authors': [...], 'year': 2023}
    ],
    'authors': ['Author 1', 'Author 2'],
    'keywords': ['keyword1', 'keyword2'],
    'metadata': {'journal': 'Journal Name', 'doi': '...'}
}
```

### Theme Extraction Results

```python
{
    'topics': [0, 1, 2, ...],
    'probabilities': [[0.9, 0.1, 0.0], ...],
    'keywords': {
        0: ['amyloid', 'beta', 'plaque', 'alzheimer', ...],
        1: ['dopamine', 'parkinson', 'neuron', ...]
    },
    'n_topics': 5
}
```

### Gap Analysis Results

```python
{
    'entity': 'protein_X',
    'gap_type': 'under_explored',
    'novelty_score': 0.9,
    'description': 'Entity mentioned in only 1 paper',
    'rank': 1
}
```

## Performance Tips

1. **Batch Processing**: Always use batch processing for large datasets
2. **GPU Usage**: Use GPU for faster embedding generation and clustering
3. **FAISS Index Types**:
   - `flat`: Exact search, slower
   - `ivf`: Faster, slight accuracy loss
   - `hnsw`: Fastest, requires tuning
4. **Topic Size**: Adjust `min_topic_size` based on dataset size
5. **Caching**: Save and reload embeddings/models to avoid recomputation

## Troubleshooting

### GROBID Connection Issues

```bash
# Check if GROBID is running
curl http://localhost:8070/api/isalive

# Restart GROBID if needed
docker restart <container_id>
```

### Out of Memory Errors

```python
# Reduce batch size
embeddings = embedder.embed_batch(texts, batch_size=16)

# Use smaller model
embedder = SciBERTEmbedder(model_name='allenai/scibert_basevocab_uncased')
```

### Slow Processing

```python
# Use GPU
embedder = SciBERTEmbedder(device='cuda')

# Use IVF index instead of flat
index = embedder.build_faiss_index(embeddings, index_type='ivf')

# Reduce topic modeling complexity
extractor = DrugDiscoveryThemeExtractor(
    umap_n_components=5,  # Reduce from default
    hdbscan_min_cluster_size=10  # Increase from default
)
```

## API Reference

See inline docstrings in each module for complete API documentation.

```bash
# Show help
python -c "from nlp import GROBIDParser; help(GROBIDParser)"
```

## Contributing

This pipeline is part of the BioDockify project. Contributions welcome!

## License

BioDockify - Pharma NLP Pipeline

## Version

Current Version: 1.0.0
