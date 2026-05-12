"""
SciBERT Embeddings for Pharma-Semantic Understanding

This module provides SciBERT-based embeddings for pharmaceutical text analysis,
including:
- Single text embedding generation
- Batch embedding generation
- FAISS-based similarity search
- Clustering using FAISS K-means
- Semantic similarity calculations

Pipeline Flow:
Text → SciBERT Tokenizer → SciBERT Model → Embeddings → FAISS → Clusters
"""

from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
import faiss
import logging
from pathlib import Path
import pickle
from tqdm import tqdm


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SciBERTEmbedder:
    """
    SciBERT-based embedding generator for pharmaceutical text

    Features:
    - Generate embeddings for single texts
    - Batch processing with progress tracking
    - FAISS-based similarity search
    - K-means clustering
    - Cosine similarity calculations
    - Save/load FAISS indexes

    Model Options:
    - allenai/scibert_scivocab_uncased (default)
    - allenai/scibert_scivocab_cased
    - allenai/scibert_basevocab_uncased
    """

    def __init__(
        self,
        model_name: str = 'allenai/scibert_scivocab_uncased',
        device: Optional[str] = None,
        max_length: int = 512
    ):
        """
        Initialize SciBERT embedder

        Args:
            model_name: HuggingFace model name
            device: Device to run model on ('cuda', 'cpu', or None for auto)
            max_length: Maximum token length for inputs
        """
        self.model_name = model_name
        self.max_length = max_length

        # Auto-detect device
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        logger.info(f"Loading SciBERT model: {model_name}")
        logger.info(f"Using device: {self.device}")

        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()

        # Get embedding dimension
        self.embedding_dim = self.model.config.hidden_size

        logger.info(f"SciBERT loaded successfully. Embedding dimension: {self.embedding_dim}")

    def embed_text(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        Generate embedding for single text

        Args:
            text: Input text
            normalize: Whether to L2 normalize the embedding

        Returns:
            Numpy array of shape (embedding_dim,)

        Raises:
            ValueError: If text is empty
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors='pt',
            max_length=self.max_length,
            truncation=True,
            padding=True
        )

        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Generate embedding
        with torch.no_grad():
            outputs = self.model(**inputs)

        # Use [CLS] token embedding (first token)
        cls_embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()
        embedding = cls_embedding.flatten()

        # Normalize if requested
        if normalize:
            embedding = self._normalize_embedding(embedding)

        return embedding

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        normalize: bool = True,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of input texts
            batch_size: Number of texts to process at once
            normalize: Whether to L2 normalize embeddings
            show_progress: Whether to show progress bar

        Returns:
            Numpy array of shape (n_texts, embedding_dim)

        Raises:
            ValueError: If texts list is empty
        """
        if not texts:
            raise ValueError("Cannot embed empty list of texts")

        # Filter out empty texts
        valid_indices = [i for i, text in enumerate(texts) if text and text.strip()]
        valid_texts = [texts[i] for i in valid_indices]

        if not valid_texts:
            raise ValueError("No valid texts found in input")

        logger.info(f"Embedding {len(valid_texts)} texts with batch size {batch_size}")

        embeddings = []

        # Process in batches
        iterator = range(0, len(valid_texts), batch_size)
        if show_progress:
            iterator = tqdm(iterator, desc="Generating embeddings")

        for i in iterator:
            batch = valid_texts[i:i + batch_size]

            # Tokenize batch
            inputs = self.tokenizer(
                batch,
                return_tensors='pt',
                max_length=self.max_length,
                truncation=True,
                padding=True
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)

            # Extract [CLS] token embeddings
            batch_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            embeddings.append(batch_embeddings)

        # Concatenate all batches
        embeddings = np.vstack(embeddings)

        # Normalize if requested
        if normalize:
            embeddings = self._normalize_embeddings(embeddings)

        # Create full array with zeros for empty texts
        full_embeddings = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
        full_embeddings[valid_indices] = embeddings

        logger.info(f"Generated embeddings of shape: {full_embeddings.shape}")

        return full_embeddings

    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Cosine similarity score (0-1)
        """
        # Ensure embeddings are normalized
        if np.linalg.norm(embedding1) > 0:
            embedding1 = embedding1 / np.linalg.norm(embedding1)
        if np.linalg.norm(embedding2) > 0:
            embedding2 = embedding2 / np.linalg.norm(embedding2)

        # Compute cosine similarity
        similarity = np.dot(embedding1, embedding2)

        return float(similarity)

    def compute_similarities(
        self,
        query_embedding: np.ndarray,
        embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity between query and multiple embeddings

        Args:
            query_embedding: Query embedding
            embeddings: Matrix of embeddings (n, embedding_dim)

        Returns:
            Array of similarity scores (n,)
        """
        # Normalize embeddings
        if np.linalg.norm(query_embedding) > 0:
            query_embedding = query_embedding / np.linalg.norm(query_embedding)

        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        normalized_embeddings = embeddings / norms

        # Compute similarities
        similarities = np.dot(normalized_embeddings, query_embedding)

        return similarities

    def build_faiss_index(
        self,
        embeddings: np.ndarray,
        index_type: str = 'flat',
        use_gpu: bool = False
    ) -> faiss.Index:
        """
        Build FAISS index for similarity search

        Args:
            embeddings: Embeddings to index (n, embedding_dim)
            index_type: Type of index ('flat', 'ivf', 'hnsw')
            use_gpu: Whether to use GPU (if available)

        Returns:
            FAISS index object
        """
        n_vectors, dim = embeddings.shape
        logger.info(f"Building FAISS index for {n_vectors} vectors with dim={dim}")

        # Normalize embeddings for cosine similarity
        embeddings_normalized = self._normalize_embeddings(embeddings)

        if index_type == 'flat':
            # Flat index (exact search)
            index = faiss.IndexFlatIP(dim)  # Inner product = cosine similarity for normalized vectors
        elif index_type == 'ivf':
            # IVF index (approximate search)
            nlist = min(100, n_vectors // 10)  # Number of clusters
            quantizer = faiss.IndexFlatIP(dim)
            index = faiss.IndexIVFFlat(quantizer, dim, nlist)
            index.train(embeddings_normalized)
        elif index_type == 'hnsw':
            # HNSW index (hierarchical navigable small world)
            index = faiss.IndexHNSWFlat(dim, 32)
            index.hnsw.efConstruction = 200
        else:
            raise ValueError(f"Unknown index type: {index_type}")

        # Add vectors to index
        index.add(embeddings_normalized)

        # Move to GPU if requested and available
        if use_gpu and faiss.get_num_gpus() > 0:
            logger.info("Moving index to GPU")
            index = faiss.index_cpu_to_all_gpus(index)

        logger.info(f"FAISS index built successfully. Type: {index_type}")

        return index

    def search_similar(
        self,
        index: faiss.Index,
        query_text: str,
        top_k: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for similar texts using FAISS index

        Args:
            index: FAISS index
            query_text: Query text to search for
            top_k: Number of similar texts to return

        Returns:
            Tuple of (distances, indices)
        """
        # Embed query text
        query_embedding = self.embed_text(query_text, normalize=True)
        query_embedding = query_embedding.reshape(1, -1).astype('float32')

        # Search
        distances, indices = index.search(query_embedding, top_k)

        return distances[0], indices[0]

    def cluster_papers(
        self,
        abstracts: List[str],
        n_clusters: int = 10,
        niter: int = 20,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Cluster papers by semantic similarity using FAISS K-means

        Args:
            abstracts: List of paper abstracts
            n_clusters: Number of clusters to create
            niter: Number of K-means iterations
            verbose: Whether to show K-means progress

        Returns:
            Dictionary with clusters and cluster info
        """
        if len(abstracts) < n_clusters:
            logger.warning(
                f"Number of abstracts ({len(abstracts)}) is less than "
                f"n_clusters ({n_clusters}). Adjusting n_clusters."
            )
            n_clusters = min(len(abstracts), 2)

        logger.info(f"Clustering {len(abstracts)} papers into {n_clusters} clusters")

        # Generate embeddings
        embeddings = self.embed_batch(abstracts, normalize=True, show_progress=True)

        # Build K-means
        kmeans = faiss.Kmeans(
            d=embeddings.shape[1],
            k=n_clusters,
            niter=niter,
            verbose=verbose,
            gpu=torch.cuda.is_available()
        )

        # Train K-means
        logger.info("Training K-means clustering...")
        kmeans.train(embeddings)

        # Assign clusters
        _, clusters = kmeans.index.search(embeddings, 1)

        # Calculate cluster statistics
        cluster_assignments = clusters.flatten()

        # Count papers per cluster
        unique, counts = np.unique(cluster_assignments, return_counts=True)
        cluster_sizes = dict(zip(unique.tolist(), counts.tolist()))

        # Calculate cluster silhouettes (simplified)
        # Full silhouette calculation would be more expensive
        cluster_stats = {}
        for cluster_id in range(n_clusters):
            cluster_indices = np.where(cluster_assignments == cluster_id)[0]
            if len(cluster_indices) > 0:
                cluster_embeddings = embeddings[cluster_indices]
                cluster_centroid = kmeans.centroids[cluster_id]

                # Calculate average distance to centroid
                distances = np.linalg.norm(cluster_embeddings - cluster_centroid, axis=1)
                avg_distance = np.mean(distances)

                cluster_stats[cluster_id] = {
                    'n_papers': len(cluster_indices),
                    'avg_distance_to_centroid': float(avg_distance)
                }

        logger.info(f"Clustering complete. Cluster sizes: {cluster_sizes}")

        return {
            'clusters': cluster_assignments.tolist(),
            'cluster_sizes': cluster_sizes,
            'centroids': kmeans.centroids,
            'n_clusters': n_clusters,
            'cluster_stats': cluster_stats
        }

    def save_faiss_index(
        self,
        index: faiss.Index,
        file_path: str
    ):
        """
        Save FAISS index to disk

        Args:
            index: FAISS index to save
            file_path: Path to save index
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(index, str(file_path))
        logger.info(f"FAISS index saved to {file_path}")

    def load_faiss_index(self, file_path: str) -> faiss.Index:
        """
        Load FAISS index from disk

        Args:
            file_path: Path to load index from

        Returns:
            Loaded FAISS index
        """
        index = faiss.read_index(file_path)
        logger.info(f"FAISS index loaded from {file_path}")
        return index

    def save_embeddings(
        self,
        embeddings: np.ndarray,
        file_path: str
    ):
        """
        Save embeddings to disk

        Args:
            embeddings: Embeddings array to save
            file_path: Path to save embeddings
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        np.save(file_path, embeddings)
        logger.info(f"Embeddings saved to {file_path}")

    def load_embeddings(self, file_path: str) -> np.ndarray:
        """
        Load embeddings from disk

        Args:
            file_path: Path to load embeddings from

        Returns:
            Loaded embeddings array
        """
        embeddings = np.load(file_path)
        logger.info(f"Embeddings loaded from {file_path}. Shape: {embeddings.shape}")
        return embeddings

    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """L2 normalize a single embedding"""
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return embedding
        return embedding / norm

    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """L2 normalize embeddings matrix"""
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        return embeddings / norms

    def get_embedding_dim(self) -> int:
        """Get the embedding dimension"""
        return self.embedding_dim

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        return {
            'model_name': self.model_name,
            'device': self.device,
            'embedding_dim': self.embedding_dim,
            'max_length': self.max_length,
            'vocab_size': self.tokenizer.vocab_size,
            'num_parameters': sum(p.numel() for p in self.model.parameters()),
            'num_trainable_parameters': sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        }
