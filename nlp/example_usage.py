"""
Complete NLP Pipeline Integration Example

This example demonstrates the full pharma-specific NLP pipeline:
1. Parse PDFs with GROBID
2. Generate SciBERT embeddings
3. Extract themes with BERTopic
4. Detect research gaps

Make sure GROBID is running before executing:
    docker run -d --rm -p 8070:8070 lfoppiano/grobid:0.7.2
"""

import asyncio
from pathlib import Path
from typing import List
import sys


def demo_grobid_parsing():
    """Demonstrate GROBID PDF parsing"""

    from nlp.grobid_parser import GROBIDParser

    print("\n" + "="*60)
    print("1. GROBID PDF Parsing")
    print("="*60)

    # Initialize GROBID parser
    grobid = GROBIDParser(
        grobid_url="http://localhost:8070",
        timeout=120
    )

    # Example: Parse header only (faster)
    # In a real scenario, use actual PDF files
    print("\nExample: Parse PDF header")
    print("Command: paper = grobid.parse_header_only('path/to/paper.pdf')")
    print("Returns: Dictionary with title, authors, abstract, etc.")

    # Example: Batch parsing
    print("\nExample: Batch parse multiple PDFs")
    print("Command: papers = grobid.batch_parse(['paper1.pdf', 'paper2.pdf'])")
    print("Returns: List of parsed paper data")

    return grobid


def demo_scibert_embeddings():
    """Demonstrate SciBERT embedding generation"""

    from nlp.scibert_embedder import SciBERTEmbedder

    print("\n" + "="*60)
    print("2. SciBERT Embeddings")
    print("="*60)

    # Initialize embedder
    print("\nInitializing SciBERT embedder...")
    embedder = SciBERTEmbedder(
        model_name='allenai/scibert_scivocab_uncased'
    )

    # Get model info
    info = embedder.get_model_info()
    print(f"\nModel Info:")
    print(f"  Model: {info['model_name']}")
    print(f"  Device: {info['device']}")
    print(f"  Embedding Dimension: {info['embedding_dim']}")
    print(f"  Parameters: {info['num_parameters']:,}")

    # Example: Single text embedding
    print("\nExample: Single text embedding")
    sample_text = "Alzheimer's disease is a neurodegenerative disorder characterized by amyloid-beta plaques."
    print(f"Text: {sample_text[:60]}...")

    embedding = embedder.embed_text(sample_text)
    print(f"Embedding shape: {embedding.shape}")
    print(f"First 5 values: {embedding[:5]}")

    # Example: Batch embeddings
    print("\nExample: Batch embeddings")
    abstracts = [
        "Alzheimer's disease is characterized by amyloid-beta plaques.",
        "Parkinson's disease involves dopaminergic neuron loss.",
        "Diabetes mellitus is a metabolic disorder with insulin resistance.",
        "Cancer immunotherapy enhances the immune response against tumors."
    ]
    print(f"Abstracts: {len(abstracts)}")

    embeddings = embedder.embed_batch(
        abstracts,
        batch_size=32,
        show_progress=False
    )
    print(f"Embeddings shape: {embeddings.shape}")

    # Example: Similarity calculation
    print("\nExample: Cosine similarity calculation")
    query = "Neurodegenerative diseases affecting cognitive function"
    query_embedding = embedder.embed_text(query)
    similarities = embedder.compute_similarities(query_embedding, embeddings)

    print(f"Query: {query}")
    print(f"\nSimilarities:")
    for i, (abstract, sim) in enumerate(zip(abstracts, similarities)):
        print(f"  {i+1}. [{sim:.3f}] {abstract[:50]}...")

    return embedder


def demo_topic_modeling(abstracts: List[str]):
    """Demonstrate BERTopic theme extraction"""

    from nlp.bertopic_extractor import DrugDiscoveryThemeExtractor

    print("\n" + "="*60)
    print("3. BERTopic Theme Extraction")
    print("="*60)

    # Initialize theme extractor
    print("\nInitializing Drug Discovery Theme Extractor...")
    theme_extractor = DrugDiscoveryThemeExtractor(
        min_topic_size=2,  # Small for demo
        nr_topics='auto'
    )

    # Extract themes
    print(f"\nExtracting themes from {len(abstracts)} abstracts...")
    themes = theme_extractor.extract_themes(abstracts)

    print(f"\nResults:")
    print(f"  Number of topics: {themes['n_topics']}")
    print(f"  Number of documents: {themes['n_documents']}")

    # Display topics
    print(f"\nExtracted Topics:")
    for topic_id, keywords in themes['keywords'].items():
        print(f"  Topic {topic_id}: {', '.join(keywords[:5])}")

    # Example: Find similar documents
    print("\nExample: Find similar documents")
    query = "neurodegenerative disease treatment"
    similar_docs, similarities = theme_extractor.find_similar_documents(query, top_n=3)

    print(f"Query: {query}")
    print(f"\nMost similar documents:")
    for doc_idx, sim in zip(similar_docs, similarities):
        print(f"  Doc {doc_idx}: [{sim:.3f}] {abstracts[doc_idx][:60]}...")

    return theme_extractor


def demo_gap_analysis(embedder, papers_data: List[dict]):
    """Demonstrate research gap detection"""

    from nlp.gap_analyzer import PreclinicalGapAnalyzer

    print("\n" + "="*60)
    print("4. Research Gap Analysis")
    print("="*60)

    # Initialize gap analyzer
    print("\nInitializing Preclinical Gap Analyzer...")
    gap_analyzer = PreclinicalGapAnalyzer(
        embedder=embedder,
        min_entity_count=2
    )

    # Example: Assess novelty
    print("\nExample: Assess hypothesis novelty")
    hypothesis = "Investigating the role of novel amyloid-beta degradation pathways in Alzheimer's disease"
    print(f"Hypothesis: {hypothesis}")

    novelty_score = gap_analyzer.assess_novelty(
        hypothesis,
        papers_data,
        method='semantic'
    )
    print(f"Novelty Score: {novelty_score:.3f} (0-1, higher = more novel)")

    # Example: Detect research gaps
    print("\nExample: Detect research gaps")
    gaps = gap_analyzer.detect_research_gaps(
        research_area="Alzheimer's",
        papers=papers_data
    )

    print(f"\nIdentified {len(gaps)} research gaps:")
    for i, gap in enumerate(gaps[:5], 1):
        print(f"  {i}. {gap.get('description', gap.get('gap_type', 'Unknown'))}")
        print(f"     Novelty: {gap.get('novelty_score', 0):.3f}")

    # Generate report
    print("\nGenerating gap analysis report...")
    report = gap_analyzer.generate_gap_report(gaps)
    print(f"Report summary:")
    print(f"  Total gaps: {report['total_gaps']}")
    print(f"  Gap types: {report['gap_types']}")
    print(f"  Mean novelty: {report['novelty_distribution'].get('mean', 0):.3f}")

    return gap_analyzer


def demo_complete_pipeline():
    """Demonstrate the complete NLP pipeline"""

    print("\n" + "="*60)
    print("PHARMA NLP PIPELINE - COMPLETE DEMONSTRATION")
    print("="*60)

    # Sample abstracts for demo
    abstracts = [
        "Alzheimer's disease is a neurodegenerative disorder characterized by amyloid-beta plaques and tau protein tangles.",
        "Parkinson's disease involves the progressive loss of dopaminergic neurons in the substantia nigra.",
        "Diabetes mellitus is a metabolic disorder characterized by insulin resistance and hyperglycemia.",
        "Cancer immunotherapy works by enhancing the immune system's ability to recognize and destroy tumor cells.",
        "Protein kinase inhibitors are a class of targeted cancer therapeutics that block specific signaling pathways.",
        "Antibiotic resistance poses a significant threat to global health, necessitating novel drug discovery approaches.",
        "CRISPR-Cas9 gene editing technology offers new possibilities for treating genetic disorders.",
        "Monoclonal antibodies have revolutionized the treatment of autoimmune diseases and cancers.",
        "Stem cell therapy holds promise for regenerating damaged tissues and treating chronic diseases.",
        "RNA therapeutics including mRNA vaccines represent a breakthrough in drug development.",
        "Drug repurposing involves identifying new therapeutic uses for existing approved drugs.",
        "Artificial intelligence is increasingly being used to accelerate drug discovery processes.",
        "Molecular docking simulations help predict the binding affinity of small molecules to target proteins.",
        "Biomarkers play a crucial role in early disease detection and personalized medicine approaches."
    ]

    # Sample papers data
    papers_data = [
        {
            'title': 'Amyloid-beta targeting in Alzheimer\'s',
            'abstract': abstracts[0],
            'entities': [{'text': 'amyloid-beta', 'entity_type': 'protein'},
                        {'text': 'tau', 'entity_type': 'protein'}]
        },
        {
            'title': 'Parkinson\'s disease mechanisms',
            'abstract': abstracts[1],
            'entities': [{'text': 'dopaminergic', 'entity_type': 'drug'}]
        }
    ]

    try:
        # Step 1: SciBERT Embeddings
        embedder = demo_scibert_embeddings()

        # Step 2: Topic Modeling
        theme_extractor = demo_topic_modeling(abstracts)

        # Step 3: Gap Analysis
        gap_analyzer = demo_gap_analysis(embedder, papers_data)

        print("\n" + "="*60)
        print("PIPELINE DEMONSTRATION COMPLETE")
        print("="*60)
        print("\nKey Components:")
        print("  ✓ GROBIDParser - PDF structure extraction")
        print("  ✓ SciBERTEmbedder - Semantic embeddings")
        print("  ✓ DrugDiscoveryThemeExtractor - Theme extraction")
        print("  ✓ PreclinicalGapAnalyzer - Gap detection")
        print("\nPipeline Ready for Production Use!")

    except Exception as e:
        print(f"\nError during pipeline demonstration: {e}")
        import traceback
        traceback.print_exc()


def demo_clustering_with_faiss():
    """Demonstrate FAISS clustering"""

    from nlp.scibert_embedder import SciBERTEmbedder

    print("\n" + "="*60)
    print("5. FAISS Clustering")
    print("="*60)

    # Initialize embedder
    embedder = SciBERTEmbedder()

    # Sample abstracts
    abstracts = [
        "Alzheimer's disease is a neurodegenerative disorder.",
        "Parkinson's disease involves dopaminergic neuron loss.",
        "Amyloid-beta plaques characterize Alzheimer's pathology.",
        "Dopamine deficiency causes Parkinson's symptoms.",
        "Diabetes is a metabolic disorder.",
        "Insulin resistance underlies type 2 diabetes.",
        "Cancer involves uncontrolled cell growth.",
        "Tumors result from genetic mutations.",
        "Immunotherapy treats cancer effectively.",
        "Chemotherapy targets rapidly dividing cells."
    ]

    print(f"\nClustering {len(abstracts)} abstracts...")

    # Cluster papers
    cluster_results = embedder.cluster_papers(
        abstracts=abstracts,
        n_clusters=3,
        niter=20
    )

    print(f"\nClustering Results:")
    print(f"  Number of clusters: {cluster_results['n_clusters']}")
    print(f"  Cluster sizes: {cluster_results['cluster_sizes']}")

    # Display assignments
    print(f"\nCluster Assignments:")
    for i, cluster_id in enumerate(cluster_results['clusters']):
        print(f"  Paper {i+1}: Cluster {cluster_id} - {abstracts[i][:50]}...")


def main():
    """Main function to run demonstrations"""

    print("\n" + "="*60)
    print("PHARMA-SPECIFIC NLP PIPELINE - INTEGRATION EXAMPLE")
    print("="*60)
    print("\nThis example demonstrates the complete NLP pipeline:")
    print("  1. GROBID - PDF parsing")
    print("  2. SciBERT - Semantic embeddings")
    print("  3. BERTopic - Theme extraction")
    print("  4. Gap Analysis - Research gap detection")
    print("  5. FAISS - Clustering")

    # Run complete pipeline demo
    demo_complete_pipeline()

    # Run clustering demo
    demo_clustering_with_faiss()

    print("\n" + "="*60)
    print("ADDITIONAL EXAMPLES")
    print("="*60)
    print("\nFor GROBID parsing with real PDFs:")
    print("  1. Start GROBID: docker run -d -p 8070:8070 lfoppiano/grobid:0.7.2")
    print("  2. Initialize parser: grobid = GROBIDParser()")
    print("  3. Parse PDF: paper = grobid.parse_pdf('paper.pdf')")
    print("  4. Batch parse: papers = grobid.batch_parse(pdf_list)")

    print("\nFor saving/loading results:")
    print("  # Save embeddings")
    print("  embedder.save_embeddings(embeddings, 'embeddings.npy')")
    print("  # Save FAISS index")
    print("  embedder.save_faiss_index(index, 'index.faiss')")
    print("  # Save BERTopic model")
    print("  theme_extractor.save_model('bertopic_model')")
    print("  # Save gaps")
    print("  gap_analyzer.save_gaps(gaps, 'gaps.json')")

    print("\nFor visualization:")
    print("  # Topic visualization")
    print("  theme_extractor.visualize_topics('topics.html')")
    print("  # Topic hierarchy")
    print("  theme_extractor.visualize_topic_hierarchy('hierarchy.html')")

    print("\n" + "="*60)


if __name__ == '__main__':
    main()
