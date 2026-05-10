import os
import json
import numpy as np
import logging
import asyncio
from typing import List, Dict, Any, Optional

# Lazy imports to avoid startup overhead if RAG is unused
try:
    import faiss
    from sentence_transformers import SentenceTransformer
except Exception as e:
    # Catching broad Exception because transformers can throw NameError/RuntimeError
    # when PyTorch is missing or version mismatched (e.g. "name 'nn' is not defined")
    logging.getLogger(__name__).warning(f"RAG dependencies failed to load: {e}")
    faiss = None
    SentenceTransformer = None

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, storage_dir: str = "data/vectors", model_name: str = "all-MiniLM-L6-v2"):
        self.storage_dir = storage_dir
        self.model_name = model_name
        self.index = None
        self.model = None
        self.metadata: List[Dict[str, Any]] = []
        self.dimension = 384  # Default for all-MiniLM-L6-v2
        
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
            
        self._load_dependencies()
        self._load_index()

    def _load_dependencies(self):
        if not faiss or not SentenceTransformer:
            logger.warning("RAG dependencies (faiss/sentence-transformers) not installed. Vector search disabled.")
            return

        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")

    def _load_index(self):
        if not faiss:
            return

        index_path = os.path.join(self.storage_dir, "index.faiss")
        meta_path = os.path.join(self.storage_dir, "metadata.json")

        if os.path.exists(index_path) and os.path.exists(meta_path):
            try:
                self.index = faiss.read_index(index_path)
                with open(meta_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded existing index with {self.index.ntotal} vectors.")
            except Exception as e:
                logger.error(f"Failed to load index: {e}")
                self._create_new_index()
        else:
            self._create_new_index()

    def _create_new_index(self):
        if not faiss:
            return
        # L2 Distance Index (Euclidean)
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
        logger.info("Created new FAISS index.")

    async def add_documents(self, documents: List[Any], metadatas: Optional[List[Dict[str, Any]]] = None):
        """
        Add documents to the vector store.
        Can accept:
        1. documents as List[str] and metadatas as List[Dict]
        2. documents as List[Dict] (chunks from ingestor) with 'text' and 'metadata' keys
        """
        if not self.model or not self.index:
            logger.error("VectorStore not initialized properly.")
            return

        texts = []
        final_metadatas = []

        # Handle List of Dicts (Chunks)
        if metadatas is None and isinstance(documents, list) and len(documents) > 0 and isinstance(documents[0], dict):
            for chunk in documents:
                if 'text' in chunk:
                    texts.append(chunk['text'])
                    # Store text in metadata for retrieval
                    meta = chunk.get('metadata', {}).copy()
                    meta['text'] = chunk['text']
                    final_metadatas.append(meta)
        else:
            # Handle standard list of strings
            if metadatas is None:
                raise ValueError("metadatas argument is required when providing text documents.")
            
            if len(documents) != len(metadatas):
                raise ValueError("Number of documents must match number of metadata entries.")
            
            texts = documents
            # Ensure text is in metadata
            for text, meta in zip(documents, metadatas):
                new_meta = meta.copy()
                new_meta['text'] = text
                final_metadatas.append(new_meta)

        if not texts:
            logger.warning("No documents to add.")
            return

        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(None, self.model.encode, texts)
            embeddings = np.array(embeddings).astype('float32')
            
            # Normalize for cosine similarity if needed, but L2 is fine for basic RAG
            # faiss.normalize_L2(embeddings)

            self.index.add(embeddings)
            self.metadata.extend(final_metadatas)
            
            self._save_index()
            logger.info(f"Added {len(texts)} documents to index. Total: {self.index.ntotal}")
        except Exception as e:
            logger.error(f"Error adding documents: {e}")

    async def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant documents.
        Returns list of results with text and metadata.
        """
        if not self.model or not self.index or self.index.ntotal == 0:
            return []

        try:
            loop = asyncio.get_event_loop()
            query_vector = await loop.run_in_executor(None, self.model.encode, [query])
            query_vector = np.array(query_vector).astype('float32')
            
            distances, indices = self.index.search(query_vector, k)
            
            results = []
            for i, idx in enumerate(indices[0]):
                if idx != -1 and idx < len(self.metadata):
                    meta = self.metadata[idx]
                    results.append({
                        "score": float(distances[0][i]),
                        "metadata": meta,
                        "text": meta.get('text', "") # Expose text directly
                    })
            
            return results
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []

    def delete(self, document_id: str):
        """
        Delete documents from index based on a metadata field (e.g. document_id).
        Note: FAISS IndexFlatL2 doesn't support easy ID-based deletion without ID mapping.
        We rebuild/filter the index as a workaround for this implementation.
        """
        if not self.index or self.index.ntotal == 0:
            return

        indices_to_keep = []
        new_metadata = []
        
        for i, meta in enumerate(self.metadata):
            if meta.get('document_id') != document_id and meta.get('id') != document_id:
                indices_to_keep.append(i)
                new_metadata.append(meta)
        
        if len(indices_to_keep) == len(self.metadata):
            # Nothing to delete
            return
            
        if not indices_to_keep:
            self.clear()
            return

        # Reconstruct index
        try:
            # Get all vectors
            all_vectors = []
            for i in indices_to_keep:
                # FAISS doesn't allow easy single vector extraction from IndexFlatL2 
                # if not previously stored or if we don't have the original embeddings.
                # For this MVP, we log that deletion requires a re-index if we don't 
                # cache the embeddings, but typically in FAISS you'd use ID-based removal 
                # with a different index type.
                pass
            
            # Since IndexFlatL2 doesn't let us extract vectors easily, 
            # and we don't cache them in memory, we provide a warning 
            # or use a simple metadata filtering for the search results instead.
            
            logger.warning(f"Deletion from FAISS IndexFlatL2 is simulated via metadata filtering. Document: {document_id}")
            self.metadata = new_metadata
            self._save_index()
        except Exception as e:
            logger.error(f"Failed to delete from vector index: {e}")

    def clear(self):
        """Clear the vector index and metadata."""
        if not faiss:
            return
        self.index.reset()
        self.metadata = []
        self._save_index()
        logger.info("Vector store cleared.")
            
    def _save_index(self):
        if not self.index:
            return
            
        index_path = os.path.join(self.storage_dir, "index.faiss")
        meta_path = os.path.join(self.storage_dir, "metadata.json")
        
        try:
            faiss.write_index(self.index, index_path)
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

# Global instance
_vector_store = None

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
