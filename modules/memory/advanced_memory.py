"""
Advanced Memory System - Core Engine
Integrates with ChromaDB, Agent Zero, and Task Manager
"""

import asyncio
import logging
import uuid
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict

import chromadb
from chromadb.config import Settings
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Memory types for hierarchical organization"""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"
    LONG_TERM = "long_term"


class MemoryImportance(str, Enum):
    """Memory importance levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRIVIAL = "trivial"


@dataclass
class Memory:
    """Memory data structure"""

    id: str
    content: str
    memory_type: MemoryType
    importance: MemoryImportance
    created_at: datetime
    last_accessed: datetime
    access_count: int
    source: Optional[str] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    embedding: Optional[List[float]] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AdvancedMemorySystem:
    """
    Advanced Memory System with:
    - Vector-based semantic search (ChromaDB)
    - Hierarchical organization (episodic/semantic/procedural)
    - Memory consolidation and pruning
    - Importance-based retrieval
    - Working memory vs long-term memory
    """

    def __init__(
        self,
        persist_dir: str = "./data/chroma_memory",
        embedding_model: str = "all-MiniLM-L6-v2",
        working_memory_size: int = 50,
        long_term_limit: int = 10000,
        auto_consolidate: bool = True,
    ):
        self.persist_dir = persist_dir
        self.embedding_model_name = embedding_model
        self.working_memory_size = working_memory_size
        self.long_term_limit = long_term_limit
        self.auto_consolidate = auto_consolidate

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        self.collections = {}
        self._setup_metrics()
        self._initialize_collections()

        self.embedder = None
        self._initialize_embedder()

        self.working_memory: List[Memory] = []
        self.working_memory_index: Dict[str, int] = {}

        self.consolidation_task = None
        self.consolidation_running = False

    def _setup_metrics(self):
        """Setup Prometheus metrics"""
        try:
            self.memory_counter = Counter(
                "memory_system_memories_total",
                "Total memories stored",
                ["type", "importance"],
            )

            self.memory_query_counter = Counter(
                "memory_system_queries_total",
                "Total memory queries",
                ["type", "result"],
            )

            self.query_duration = Histogram(
                "memory_system_query_duration_seconds",
                "Memory query duration",
                ["query_type"],
            )

            self.memory_count_gauge = Gauge(
                "memory_system_memory_count",
                "Number of memories in system",
                ["collection"],
            )
        except ValueError:
            pass

    def _initialize_collections(self):
        """Initialize ChromaDB collections"""
        collection_configs = {
            "episodic_memory": "Experiences and events",
            "semantic_memory": "Facts and knowledge",
            "procedural_memory": "Methods and procedures",
            "working_memory": "Current session context",
        }

        for name, desc in collection_configs.items():
            try:
                collection = self.client.get_or_create_collection(
                    name=name, metadata={"description": desc, "hnsw:space": "cosine"}
                )
                self.collections[name] = collection
                count = collection.count()
                if hasattr(self, "memory_count_gauge"):
                    self.memory_count_gauge.labels(collection=name).set(count)
                logger.info(f"Initialized collection: {name} ({count} memories)")
            except Exception as e:
                logger.error(f"Failed to initialize collection {name}: {e}")

    def _initialize_embedder(self):
        """Initialize sentence transformer for embeddings"""
        try:
            from sentence_transformers import SentenceTransformer

            self.embedder = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Loaded embedding model: {self.embedding_model_name}")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. Using dummy embeddings."
            )
            self.embedder = None
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.embedder = None

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if self.embedder:
            embedding = self.embedder.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        return [0.0] * 384

    async def add_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.EPISODIC,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        source: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a memory to the system"""
        memory_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            created_at=now,
            last_accessed=now,
            access_count=0,
            source=source,
            tags=tags or [],
            metadata=metadata or {},
        )

        embedding = self._generate_embedding(content)
        memory.embedding = embedding

        collection_name = f"{memory_type.value}_memory"

        if collection_name in self.collections:
            collection = self.collections[collection_name]

            collection.add(
                ids=[memory_id],
                documents=[content],
                embeddings=[embedding],
                metadatas=[
                    {
                        "importance": importance.value,
                        "source": source,
                        "tags": json.dumps(tags or []),
                        "metadata": json.dumps(metadata or {}),
                        "created_at": now.isoformat(),
                        "last_accessed": now.isoformat(),
                        "access_count": 0,
                    }
                ],
            )

            if hasattr(self, "memory_counter"):
                self.memory_counter.labels(
                    type=memory_type.value, importance=importance.value
                ).inc()

            if hasattr(self, "memory_count_gauge"):
                self.memory_count_gauge.labels(collection=collection_name).set(
                    collection.count()
                )

            await self._add_to_working_memory(memory)

            logger.info(f"Added memory: {memory_id} ({memory_type.value})")

        return memory_id

    async def _add_to_working_memory(self, memory: Memory):
        """Add memory to working memory (LRU)"""
        memory_id = memory.id

        if memory_id in self.working_memory_index:
            idx = self.working_memory_index[memory_id]
            self.working_memory[idx] = memory
        else:
            self.working_memory.append(memory)
            self.working_memory_index[memory_id] = len(self.working_memory) - 1

        if len(self.working_memory) > self.working_memory_size:
            oldest = self.working_memory.pop(0)
            del self.working_memory_index[oldest.id]
            # Re-index
            self.working_memory_index = {
                m.id: i for i, m in enumerate(self.working_memory)
            }

    async def search(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10,
        min_importance: Optional[MemoryImportance] = None,
        include_working: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search memories using vector similarity"""
        import time

        start_time = time.time()

        results = []

        if include_working:
            working_results = self._search_working_memory(
                query, limit=min(limit, self.working_memory_size)
            )
            results.extend(working_results)

        collections_to_search = []
        if memory_types:
            for mem_type in memory_types:
                collection_name = f"{mem_type.value}_memory"
                if collection_name in self.collections:
                    collections_to_search.append(collection_name)
        else:
            collections_to_search = list(self.collections.keys())

        query_embedding = self._generate_embedding(query)

        for collection_name in collections_to_search:
            try:
                collection = self.collections[collection_name]
                search_results = collection.query(
                    query_embeddings=[query_embedding], n_results=limit
                )

                if search_results and search_results["ids"]:
                    for idx in range(len(search_results["ids"][0])):
                        memory_id = search_results["ids"][0][idx]
                        distance = (
                            search_results["distances"][0][idx]
                            if "distances" in search_results
                            else 0.0
                        )
                        metadata = (
                            search_results["metadatas"][0][idx]
                            if "metadatas" in search_results
                            else {}
                        )

                        if min_importance:
                            importance_order = {
                                MemoryImportance.CRITICAL: 5,
                                MemoryImportance.HIGH: 4,
                                MemoryImportance.MEDIUM: 3,
                                MemoryImportance.LOW: 2,
                                MemoryImportance.TRIVIAL: 1,
                            }
                            mem_importance = MemoryImportance(
                                metadata.get("importance", "medium")
                            )
                            if (
                                importance_order[mem_importance]
                                < importance_order[min_importance]
                            ):
                                continue

                        results.append(
                            {
                                "id": memory_id,
                                "content": search_results["documents"][0][idx]
                                if "documents" in search_results
                                else "",
                                "score": 1.0 - distance,
                                "type": collection_name.replace("_memory", ""),
                                "importance": metadata.get("importance", "medium"),
                                "source": metadata.get("source"),
                                "tags": json.loads(metadata.get("tags", "[]")),
                                "metadata": json.loads(metadata.get("metadata", "{}")),
                                "in_working_memory": False,
                            }
                        )

            except Exception as e:
                logger.error(f"Search error in {collection_name}: {e}")

        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:limit]

        query_time = time.time() - start_time
        if hasattr(self, "query_duration"):
            self.query_duration.labels(query_type="vector").observe(query_time)
        if hasattr(self, "memory_query_counter"):
            self.memory_query_counter.labels(
                type="vector", result="success" if results else "none"
            ).inc()

        for result in results:
            await self._update_access(result["id"])

        return results

    def _search_working_memory(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Simple keyword search in working memory"""
        query_words = set(query.lower().split())
        results = []

        for memory in self.working_memory:
            content_lower = memory.content.lower()

            match_score = 0
            for word in query_words:
                if word in content_lower:
                    match_score += 1

            if match_score > 0:
                results.append(
                    {
                        "id": memory.id,
                        "content": memory.content,
                        "score": match_score / len(query_words),
                        "type": "working",
                        "importance": memory.importance.value,
                        "source": memory.source,
                        "tags": memory.tags,
                        "metadata": memory.metadata,
                        "in_working_memory": True,
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def _update_access(self, memory_id: str):
        """Update access timestamp and count"""
        for collection_name, collection in self.collections.items():
            try:
                results = collection.get(ids=[memory_id])
                if results and results["ids"]:
                    old_metadata = (
                        results["metadatas"][0] if results.get("metadatas") else {}
                    )

                    new_metadata = old_metadata.copy()
                    new_metadata["last_accessed"] = datetime.now(
                        timezone.utc
                    ).isoformat()
                    new_metadata["access_count"] = (
                        old_metadata.get("access_count", 0) + 1
                    )

                    collection.update(ids=[memory_id], metadatas=[new_metadata])
                    break
            except Exception as e:
                logger.error(f"Error updating access: {e}")

    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get memory by ID"""
        for collection_name, collection in self.collections.items():
            try:
                results = collection.get(ids=[memory_id])
                if results and results["ids"]:
                    metadata = (
                        results["metadatas"][0] if results.get("metadatas") else {}
                    )

                    return {
                        "id": memory_id,
                        "content": results["documents"][0]
                        if results.get("documents")
                        else "",
                        "type": collection_name.replace("_memory", ""),
                        "importance": metadata.get("importance", "medium"),
                        "source": metadata.get("source"),
                        "tags": json.loads(metadata.get("tags", "[]")),
                        "metadata": json.loads(metadata.get("metadata", "{}")),
                        "created_at": metadata.get("created_at"),
                        "last_accessed": metadata.get("last_accessed"),
                        "access_count": metadata.get("access_count", 0),
                    }
            except Exception:
                continue

        return None

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory"""
        for collection in self.collections.values():
            try:
                collection.delete(ids=[memory_id])
                if hasattr(self, "memory_count_gauge"):
                    self.memory_count_gauge.labels(collection=collection.name).set(
                        collection.count()
                    )
                logger.info(f"Deleted memory: {memory_id}")
                return True
            except Exception:
                continue

        return False

    async def get_statistics(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        stats = {
            "total_memories": 0,
            "by_type": {},
            "by_importance": {},
            "working_memory_count": len(self.working_memory),
        }

        for collection_name, collection in self.collections.items():
            count = collection.count()
            mem_type = collection_name.replace("_memory", "")
            stats["total_memories"] += count
            stats["by_type"][mem_type] = count

        return stats

    async def clear_working_memory(self):
        """Clear working memory"""
        self.working_memory.clear()
        self.working_memory_index.clear()
        logger.info("Cleared working memory")


# Global instance
_memory_system = None


def get_memory_system(
    persist_dir: str = "./data/chroma_memory",
) -> AdvancedMemorySystem:
    """Get or create global memory system instance"""
    global _memory_system
    if _memory_system is None:
        import os

        # Respect environment variable for data directory (useful for CI/tests)
        data_dir = os.environ.get("BIODOCKIFY_DATA_DIR")
        if data_dir:
            resolved_dir = os.path.join(data_dir, "chroma_memory")
            logger.info(f"Using BIODOCKIFY_DATA_DIR for memory: {resolved_dir}")
            _memory_system = AdvancedMemorySystem(persist_dir=resolved_dir)
        else:
            _memory_system = AdvancedMemorySystem(persist_dir=persist_dir)
    return _memory_system
