import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class LocalEmbedder:
    """
    Local embedding using HuggingFace sentence-transformers.
    Zero-cost alternative to OpenAI/Google embeddings.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info(f"Initializing LocalEmbedder with model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        # convert_to_numpy=True returns numpy array, we need list for Chroma
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

class ChromaVectorStore:
    """
    ChromaDB integration for persistent local vector storage.
    """
    
    def __init__(self, persist_dir: str = "./data/chroma", embedding_model: str = "all-MiniLM-L6-v2"):
        self.persist_dir = persist_dir
        
        # Ensure directory exists
        os.makedirs(persist_dir, exist_ok=True)
        
        logger.info(f"Initializing ChromaDB client at {persist_dir}")
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        self.embedder = LocalEmbedder(model_name=embedding_model)
        self.collections = {}
        self._initialize_collections()
        
    def _initialize_collections(self):
        """Initialize standard collections."""
        collections_config = {
            'agent_zero_memory': 'Agent Zero long-term memory',
            'nanobot_knowledge': 'NanoBot shared knowledge',
            'research_documents': 'Research documents'
        }
        
        for name, desc in collections_config.items():
            try:
                # get_or_create_collection is the standard way
                collection = self.client.get_or_create_collection(
                    name=name,
                    metadata={
                        'description': desc,
                        'hnsw:space': 'cosine' 
                    }
                    # We utilize our own embedding function logic by passing embeddings manually to add/query
                    # OR we could wrap LocalEmbedder as a Chroma EmbeddingFunction.
                    # For clarity/control, we'll embed manually in add/search methods below.
                )
                self.collections[name] = collection
                logger.info(f"Loaded collection: {name} (Docs: {collection.count()})")
            except Exception as e:
                logger.error(f"Error creating collection {name}: {e}")

    async def add_documents(self, collection_name: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add documents to a collection.
        documents list of dicts:
        {
            "id": "optional_id",
            "text": "content",
            "metadata": {...},
            "source": "..."
        }
        """
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} does not exist.")
            
        collection = self.collections[collection_name]
        
        ids = []
        texts = []
        metadatas = []
        
        for idx, doc in enumerate(documents):
            # Generate ID if missing
            doc_id = doc.get("id", f"{collection_name}_{os.urandom(4).hex()}")
            ids.append(doc_id)
            texts.append(doc["text"])
            
            # Prepare metadata
            meta = doc.get("metadata", {}).copy()
            if "source" in doc:
                meta["source"] = doc["source"]
            metadatas.append(meta)
            
        # Generate embeddings
        try:
            embeddings = self.embedder.embed_batch(texts)
            
            # Add to Chroma
            collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            return {
                "success": True, 
                "count": len(documents),
                "collection": collection_name
            }
        except Exception as e:
            logger.error(f"Failed to add documents to {collection_name}: {e}")
            return {"success": False, "error": str(e)}

    async def search(self, collection_name: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        """
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} does not exist.")
            
        collection = self.collections[collection_name]
        
        try:
            query_embedding = self.embedder.embed(query)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            # Chroma results are lists of lists (for batch queries)
            # We only did one query, so access index 0
            
            formatted_results = []
            if results['ids']:
                num_results = len(results['ids'][0])
                for i in range(num_results):
                    formatted_results.append({
                        "id": results['ids'][0][i],
                        "score": results['distances'][0][i] if 'distances' in results and results['distances'] else 0.0,
                        "text": results['documents'][0][i] if 'documents' in results and results['documents'] else "",
                        "metadata": results['metadatas'][0][i] if 'metadatas' in results and results['metadatas'] else {}
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
