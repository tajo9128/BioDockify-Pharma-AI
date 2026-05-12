"""
BERTopic for Drug Discovery Theme Extraction

This module provides BERTopic-based theme extraction for pharmaceutical literature,
including:
- Automatic topic modeling
- Hierarchical topic discovery
- Topic visualization
- Document-topic similarity search
- Dynamic topic analysis

Pipeline Flow:
Texts → SciBERT Embeddings → UMAP → HDBSCAN → BERTopic → Topics → Themes
"""

from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
from typing import List, Dict, Optional, Any, Tuple
import numpy as np
import logging
from pathlib import Path
import plotly.graph_objects as go
from collections import Counter


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DrugDiscoveryThemeExtractor:
    """
    BERTopic-based theme extractor for drug discovery literature

    Features:
    - Automatic topic extraction from abstracts
    - Hierarchical topic modeling
    - Interactive topic visualization
    - Document-topic similarity search
    - Topic evolution analysis
    - Custom pharmaceutical stopwords

    Models:
    - Embedding: SciBERT (allenai/scibert_scivocab_uncased)
    - Dimensionality Reduction: UMAP
    - Clustering: HDBSCAN
    - Topic Representation: c-TF-IDF
    """

    # Pharmaceutical-specific stopwords
    PHARMA_STOPWORDS = {
        'study', 'paper', 'article', 'result', 'method', 'analysis',
        'show', 'demonstrate', 'suggest', 'indicate', 'conclusion',
        'purpose', 'background', 'objective', 'material', 'design',
        'significantly', 'important', 'considerable', 'substantial',
        'however', 'therefore', 'thus', 'consequently', 'furthermore',
        'also', 'additionally', 'moreover', 'previously', 'previously',
        'compared', 'comparison', 'versus', 'relative', 'regarding',
        'using', 'used', 'according', 'based', 'including', 'among',
        'within', 'throughout', 'through', 'during', 'following',
        'abstract', 'introduction', 'conclusion', 'discussion', 'method'
    }

    def __init__(
        self,
        embedding_model: str = 'allenai/scibert_scivocab_uncased',
        min_topic_size: int = 10,
        nr_topics: str = 'auto',
        calculate_probabilities: bool = False,
        verbose: bool = True,
        umap_n_components: int = 5,
        umap_n_neighbors: int = 15,
        hdbscan_min_cluster_size: int = 10,
        hdbscan_min_samples: Optional[int] = None
    ):
        """
        Initialize Drug Discovery Theme Extractor

        Args:
            embedding_model: Sentence transformer model for embeddings
            min_topic_size: Minimum topic size
            nr_topics: Number of topics ('auto' or integer)
            calculate_probabilities: Whether to calculate topic probabilities
            verbose: Whether to show verbose output
            umap_n_components: UMAP n_components parameter
            umap_n_neighbors: UMAP n_neighbors parameter
            hdbscan_min_cluster_size: HDBSCAN min_cluster_size
            hdbscan_min_samples: HDBSCAN min_samples (None = auto)
        """
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)

        # Initialize UMAP for dimensionality reduction
        self.umap_model = UMAP(
            n_components=umap_n_components,
            n_neighbors=umap_n_neighbors,
            min_dist=0.0,
            metric='cosine',
            random_state=42
        )

        # Initialize HDBSCAN for clustering
        hdbscan_params = {
            'min_cluster_size': hdbscan_min_cluster_size,
            'metric': 'euclidean',
            'prediction_data': True
        }
        if hdbscan_min_samples is not None:
            hdbscan_params['min_samples'] = hdbscan_min_samples

        self.hdbscan_model = HDBSCAN(**hdbscan_params)

        # Initialize BERTopic
        self.model = BERTopic(
            embedding_model=self.embedding_model,
            umap_model=self.umap_model,
            hdbscan_model=self.hdbscan_model,
            min_topic_size=min_topic_size,
            nr_topics=nr_topics,
            calculate_probabilities=calculate_probabilities,
            verbose=verbose
        )

        self.fitted = False
        logger.info("Drug Discovery Theme Extractor initialized")

    def extract_themes(
        self,
        abstracts: List[str],
        topics_to_remove: Optional[List[int]] = None,
        n_words: int = 10
    ) -> Dict[str, Any]:
        """
        Extract drug discovery themes from abstracts

        Args:
            abstracts: List of paper abstracts
            topics_to_remove: List of topic IDs to remove (e.g., outliers)
            n_words: Number of words per topic

        Returns:
            Dictionary with topics, keywords, and document assignments

        Raises:
            ValueError: If abstracts list is empty
        """
        if not abstracts:
            raise ValueError("Cannot extract themes from empty abstracts list")

        # Filter out empty abstracts
        valid_abstracts = [a for a in abstracts if a and a.strip()]
        if not valid_abstracts:
            raise ValueError("No valid abstracts found")

        logger.info(f"Extracting themes from {len(valid_abstracts)} abstracts")

        # Fit model
        topics, probs = self.model.fit_transform(valid_abstracts)

        # Get topic information
        topic_info = self.model.get_topic_info()

        # Remove pharmaceutical stopwords from topic words
        self._clean_topic_words(self.model, self.PHARMA_STOPWORDS)

        # Get topic information again after cleaning
        topic_info = self.model.get_topic_info()

        # Get top keywords per topic
        topics_keywords = {}
        for topic_id in topic_info['Topic']:
            if topic_id != -1:  # Exclude outliers
                words = self.model.get_topic(topic_id)
                topics_keywords[topic_id] = [word for word, _ in words[:n_words]]

        # Filter out specific topics if requested
        if topics_to_remove:
            filtered_topics = []
            filtered_probs = []
            for t, p in zip(topics, probs):
                if t not in topics_to_remove:
                    filtered_topics.append(t)
                    filtered_probs.append(p)
            topics = filtered_topics
            probs = np.array(filtered_probs)

        # Calculate topic distributions
        unique_topics, counts = np.unique(topics, return_counts=True)
        topic_distributions = dict(zip(unique_topics.tolist(), counts.tolist()))

        self.fitted = True

        logger.info(f"Extracted {len(topics_keywords)} themes")

        return {
            'topics': topics,
            'probabilities': probs.tolist() if probs is not None else [],
            'topic_info': topic_info.to_dict('records'),
            'keywords': topics_keywords,
            'topic_distributions': topic_distributions,
            'n_topics': len(topics_keywords),
            'n_documents': len(topics)
        }

    def _clean_topic_words(self, model: BERTopic, stopwords: set):
        """Clean topic words by removing pharmaceutical stopwords"""
        # Get current topics
        topic_words = model.get_topics()

        # Clean each topic's words
        cleaned_topics = {}
        for topic_id, words in topic_words.items():
            if topic_id != -1:  # Don't clean outliers
                cleaned_words = [
                    (word, weight) for word, weight in words
                    if word.lower() not in stopwords
                ]
                cleaned_topics[topic_id] = cleaned_words

        # Update model's topic representations
        model.topic_representations_ = cleaned_topics

    def get_topic_keywords(
        self,
        topic_id: int,
        n_words: int = 10
    ) -> List[str]:
        """
        Get top keywords for a specific topic

        Args:
            topic_id: Topic ID
            n_words: Number of keywords to return

        Returns:
            List of keyword strings
        """
        if not self.fitted:
            raise RuntimeError("Model must be fitted before getting topic keywords")

        keywords = self.model.get_topic(topic_id)
        return [word for word, _ in keywords[:n_words]] if keywords else []

    def get_topic_documents(
        self,
        topic_id: int,
        documents: List[str],
        n_docs: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get most relevant documents for a topic

        Args:
            topic_id: Topic ID
            documents: Original documents
            n_docs: Number of documents to return

        Returns:
            List of dictionaries with document info
        """
        if not self.fitted:
            raise RuntimeError("Model must be fitted before getting topic documents")

        # Get documents for this topic
        docs = self.model.get_representative_docs(topic_id)

        if docs is None:
            return []

        # Get topic info
        topic_info = self.model.get_topic_info()
        topic_row = topic_info[topic_info['Topic'] == topic_id]

        results = []
        for i, doc in enumerate(docs[:n_docs]):
            results.append({
                'document': doc,
                'topic_id': topic_id,
                'topic_size': int(topic_row['Count'].values[0]) if len(topic_row) > 0 else 0,
                'rank': i + 1
            })

        return results

    def find_similar_documents(
        self,
        query: str,
        top_n: int = 10
    ) -> Tuple[List[int], List[float]]:
        """
        Find documents similar to query

        Args:
            query: Query text
            top_n: Number of similar documents to return

        Returns:
            Tuple of (document_indices, similarities)
        """
        if not self.fitted:
            raise RuntimeError("Model must be fitted before finding similar documents")

        similar_docs, similarities = self.model.find_topics(query, top_n=top_n)

        return similar_docs, similarities

    def visualize_topics(
        self,
        output_path: str = './topics_viz.html',
        width: int = 1000,
        height: int = 700
    ) -> str:
        """
        Generate interactive topic visualization

        Args:
            output_path: Path to save HTML file
            width: Plot width in pixels
            height: Plot height in pixels

        Returns:
            Path to saved visualization file
        """
        if not self.fitted:
            raise RuntimeError("Model must be fitted before visualizing topics")

        logger.info(f"Generating topic visualization: {output_path}")

        # Get topic visualization from BERTopic
        fig = self.model.visualize_topics(width=width, height=height)

        # Save to HTML
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_file))

        logger.info(f"Topic visualization saved to {output_file}")

        return str(output_path)

    def visualize_topic_hierarchy(
        self,
        output_path: str = './topics_hierarchy.html',
        width: int = 1000,
        height: int = 700
    ) -> str:
        """
        Generate hierarchical topic visualization

        Args:
            output_path: Path to save HTML file
            width: Plot width in pixels
            height: Plot height in pixels

        Returns:
            Path to saved visualization file
        """
        if not self.fitted:
            raise RuntimeError("Model must be fitted before visualizing hierarchy")

        logger.info(f"Generating topic hierarchy visualization: {output_path}")

        fig = self.model.visualize_hierarchy(width=width, height=height)

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_file))

        logger.info(f"Topic hierarchy saved to {output_path}")

        return str(output_path)

    def visualize_topic_distribution(
        self,
        output_path: str = './topics_distribution.html',
        top_n_topics: int = 10,
        width: int = 1000,
        height: int = 700
    ) -> str:
        """
        Generate topic distribution visualization (barchart)

        Args:
            output_path: Path to save HTML file
            top_n_topics: Number of topics to display
            width: Plot width in pixels
            height: Plot height in pixels

        Returns:
            Path to saved visualization file
        """
        if not self.fitted:
            raise RuntimeError("Model must be fitted before visualizing distribution")

        logger.info(f"Generating topic distribution visualization: {output_path}")

        # Get topic info
        topic_info = self.model.get_topic_info()

        # Sort by frequency and get top N
        topic_info = topic_info.sort_values('Count', ascending=False)
        top_topics = topic_info.head(top_n_topics + 1)  # +1 to exclude outlier if present

        # Exclude outlier topic (-1)
        top_topics = top_topics[top_topics['Topic'] != -1]

        # Create bar chart
        fig = go.Figure(data=[
            go.Bar(
                x=[f"Topic {tid}" for tid in top_topics['Topic']],
                y=top_topics['Count'],
                marker_color='steelblue'
            )
        ])

        fig.update_layout(
            title='Topic Distribution',
            xaxis_title='Topic',
            yaxis_title='Document Count',
            width=width,
            height=height
        )

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_file))

        logger.info(f"Topic distribution saved to {output_file}")

        return str(output_path)

    def get_topic_summary(self, topic_id: int, documents: List[str]) -> Dict[str, Any]:
        """
        Get a comprehensive summary of a topic

        Args:
            topic_id: Topic ID
            documents: All documents

        Returns:
            Dictionary with topic summary
        """
        if not self.fitted:
            raise RuntimeError("Model must be fitted before getting topic summary")

        # Get keywords
        keywords = self.get_topic_keywords(topic_id, n_words=20)

        # Get representative documents
        topic_docs = self.get_topic_documents(topic_id, documents, n_docs=3)

        # Get topic size
        topic_info = self.model.get_topic_info()
        topic_row = topic_info[topic_info['Topic'] == topic_id]
        topic_size = int(topic_row['Count'].values[0]) if len(topic_row) > 0 else 0

        return {
            'topic_id': topic_id,
            'size': topic_size,
            'keywords': keywords,
            'representative_documents': topic_docs
        }

    def save_model(self, output_path: str):
        """
        Save the fitted BERTopic model

        Args:
            output_path: Path to save model
        """
        if not self.fitted:
            raise RuntimeError("Model must be fitted before saving")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        self.model.save(str(output_path))
        logger.info(f"BERTopic model saved to {output_path}")

    def load_model(self, model_path: str):
        """
        Load a fitted BERTopic model

        Args:
            model_path: Path to saved model
        """
        self.model = BERTopic.load(model_path)
        self.fitted = True
        logger.info(f"BERTopic model loaded from {model_path}")

    def merge_topics(self, topics_to_merge: List[int]) -> int:
        """
        Merge multiple topics into one

        Args:
            topics_to_merge: List of topic IDs to merge

        Returns:
            ID of merged topic
        """
        if not self.fitted:
            raise RuntimeError("Model must be fitted before merging topics")

        self.model.merge_topics(topics_to_merge)
        logger.info(f"Merged topics: {topics_to_merge}")

        # Return the first topic ID (target of merge)
        return topics_to_merge[0]

    def reduce_topics(self, nr_topics: int):
        """
        Reduce the number of topics

        Args:
            nr_topics: Target number of topics
        """
        if not self.fitted:
            raise RuntimeError("Model must be fitted before reducing topics")

        self.model.reduce_topics(nr_topics)
        logger.info(f"Reduced topics to {nr_topics}")

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        info = {
            'fitted': self.fitted,
            'embedding_model': str(type(self.embedding_model)),
            'umap_model': str(type(self.umap_model)),
            'hdbscan_model': str(type(self.hdbscan_model))
        }

        if self.fitted:
            topic_info = self.model.get_topic_info()
            info['n_topics'] = len(topic_info[topic_info['Topic'] != -1])
            info['n_outliers'] = int(topic_info[topic_info['Topic'] == -1]['Count'].values[0])

        return info
