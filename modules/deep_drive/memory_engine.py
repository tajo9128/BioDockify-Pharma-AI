import logging
import asyncio
import json
import re
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import networkx as nx
from networkx.readwrite import json_graph

# Import Vector Store
from modules.rag.vector_store import get_vector_store

# Import Graph Driver
try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False

logger = logging.getLogger(__name__)

class MemoryEngine:
    """
    Native implementation of Deep Drive Memory Engine.
    Combines Vector Search (RAG) and Knowledge Graph (Memgraph) 
    to provide advanced context and reasoning capabilities.
    """

    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", neo4j_auth: tuple = ("", "")):
        self.vector_store = get_vector_store()
        self.driver = None
        self.local_graph = None
        self.local_graph_path = os.path.join("data", "knowledge_graph.json")

        if HAS_NEO4J:
            try:
                self.driver = GraphDatabase.driver(neo4j_uri, auth=neo4j_auth)
                # Verify connectivity
                self.driver.verify_connectivity()
                logger.info("Connected to Knowledge Graph (Memgraph/Neo4j).")
            except Exception as e:
                logger.warning(f"Failed to connect to Knowledge Graph: {e}. Falling back to Local NetworkX Graph.")
                self.driver = None
                self._load_local_graph()
        else:
            logger.info("Neo4j driver not found. Using Local NetworkX Graph.")
            self._load_local_graph()

    def _load_local_graph(self):
        if os.path.exists(self.local_graph_path):
            try:
                with open(self.local_graph_path, 'r') as f:
                    data = json.load(f)
                self.local_graph = json_graph.node_link_graph(data)
                logger.info(f"Loaded local graph with {self.local_graph.number_of_nodes()} nodes.")
            except Exception as e:
                logger.error(f"Failed to load local graph: {e}")
                self.local_graph = nx.DiGraph()
        else:
            self.local_graph = nx.DiGraph()

    def _save_local_graph(self):
        if self.local_graph:
            try:
                data = json_graph.node_link_data(self.local_graph)
                with open(self.local_graph_path, 'w') as f:
                    json.dump(data, f)
            except Exception as e:
                logger.error(f"Failed to save local graph: {e}")

    def close(self):
        if self.driver:
            self.driver.close()
        self._save_local_graph()

    async def store_memory(self, interaction: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store a new memory.
        1. Analyzes interaction for significance.
        2. extracts facts.
        3. Vectorizes and stores in VectorDB.
        4. Extracts entities and stores in GraphDB.
        """
        if not interaction:
            return False

        # 1. Significance Check (Ported from Cipher)
        if not self._is_significant(interaction):
            logger.info("Interaction deemed insignificant. Skipping memory storage.")
            return False

        # 2. Vector Storage
        try:
            metadata = context or {}
            metadata["timestamp"] = datetime.now().isoformat()
            metadata["type"] = "memory"
            
            await self.vector_store.add_documents([interaction], [metadata])
            logger.info("Stored memory in Vector Store.")
        except Exception as e:
            logger.error(f"Vector storage failed: {e}")
            return False

        # 3. Graph Storage (Simple Entity Extraction for MVP)
        # In a full implementation, we'd use an LLM or NER model here to extract structured triplets.
        # For now, we perform basic keyword extraction or use provided entities if available in context.
        # 3. Graph Storage
        # In a full implementation, we'd use an LLM or NER model here to extract structured triplets.
        # For now, we use provided entities if available in context.
        try:
            # If context provides entities, use them
            if context and context.get("entities"):
               await self._store_graph_entities(context["entities"], interaction)
        except Exception as e:
            logger.error(f"Graph storage failed: {e}")

        return True

    async def search_memory(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search vector memory.
        """
        return await self.vector_store.search(query, k=top_k)

    async def search_graph(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search knowledge graph for nodes matching the query.
        """
        results = {"nodes": [], "edges": []}

        # 1. Neo4j Search
        if self.driver:
            # Simple fuzzy search on 'name' property of nodes
            cypher = """
            MATCH (n)
            WHERE toLower(n.name) CONTAINS toLower($query)
            RETURN n, labels(n) as labels
            LIMIT $limit
            """
            
            try:
                def match_tx(tx, q, l):
                    return list(tx.run(cypher, query=q, limit=l))

                # run blocking driver in executor
                records = await asyncio.to_thread(
                    lambda: self.driver.session().execute_read(match_tx, query, limit)
                )

                for record in records:
                    node = record["n"]
                    labels = record["labels"]
                    # Convert Node object to dict
                    node_props = dict(node)
                    results["nodes"].append({
                        "id": node.element_id if hasattr(node, 'element_id') else node.id,
                        "labels": labels,
                        "properties": node_props
                    })
                
                return results

            except Exception as e:
                logger.error(f"Graph search failed: {e}")
                return {}
        
        # 2. Local NetworkX Search
        elif self.local_graph is not None:
            logger.info(f"Searching Local Graph (Nodes: {self.local_graph.number_of_nodes()}). Query: {query}")
            query_lower = query.lower()
            count = 0
            for node, attrs in self.local_graph.nodes(data=True):
                name = attrs.get("name", "").lower()
                # logger.info(f"Checking node: {node}, name: {name}")
                if query_lower in name:
                    results["nodes"].append({
                        "id": node,
                        "labels": [attrs.get("label", "Entity")],
                        "properties": attrs
                    })
                    count += 1
                    if count >= limit:
                        break
            return results
        
        return {}

    async def _store_graph_entities(self, entities: Dict[str, List[str]], source_text: str):
        """
        Store extracted entities in the graph.
        """
        if not entities:
            return

        # 1. Neo4j Storage
        if self.driver:
            def write_tx(tx, ents):
                for label, names in ents.items():
                    if isinstance(names, list):
                        for name in names:
                            # Merge node to avoid duplicates
                            # Clean label to be safe (alphanumeric)
                            safe_label = "".join(filter(str.isalnum, label.capitalize()))
                            if not safe_label: safe_label = "Entity"
                            
                            query = f"MERGE (n:{safe_label} {{name: $name}}) RETURN n"
                            tx.run(query, name=name)

            await asyncio.to_thread(
                lambda: self.driver.session().execute_write(write_tx, entities)
            )
        
        # 2. Local NetworkX Storage
        elif self.local_graph is not None:
            for label, names in entities.items():
                if isinstance(names, list):
                    for name in names:
                        safe_label = "".join(filter(str.isalnum, label.capitalize()))
                        if not safe_label: safe_label = "Entity"
                        
                        # Use name as ID for simplicity in local graph
                        if not self.local_graph.has_node(name):
                            self.local_graph.add_node(name, label=safe_label, name=name, source="memory_engine")
            
            self._save_local_graph()
            
        logger.info(f"Stored {sum(len(v) for v in entities.values())} entities in Knowledge Graph.")

    def _is_significant(self, content: str) -> bool:
        """
        Filter trivial interactions. Ported logic from Cipher.
        """
        if not content or len(content.strip()) < 10:
            return False
            
        text = content.lower().strip()
        
        # Skip patterns
        skip_patterns = [
            r"^(hello|hi|hey|thanks|thank you|ok|okay|yes|no|goodbye)$",
            r"^search(ing)? for",
            r"^task (started|completed)"
        ]
        
        for p in skip_patterns:
            if re.search(p, text):
                return False
                
        # Technical indicators (Simplified)
        tech_words = ["algorithm", "code", "function", "error", "api", "database", "graph", "protein", "gene", "drug", "molecular"]
        if any(w in text for w in tech_words):
            return True
            
        # Default: if length is substantial, keep it
        return len(text) > 50
