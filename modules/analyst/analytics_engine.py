"""
Research Analyst Module - BioDockify Pharma Research AI
Handles graph algorithms and data analytics on the Neo4j Knowledge Graph.
"""

import logging
from typing import Dict, List, Any, Optional
from modules.graph_builder.loader import get_loader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BioDockify.Analyst")

class ResearchAnalyst:
    """
    Performs analysis on the Knowledge Graph to extract insights.
    """
    
    def __init__(self):
        """Initialize connection to the Knowledge Graph."""
        self.loader = get_loader()
        # Lazy connection - do not connect in __init__ to prevent startup hangs
        # self.loader.connect() 
        logger.info("Research Analyst initialized (Graph connection is lazy).")

    def get_graph_statistics(self) -> Dict[str, int]:
        """
        Get summary statistics of the Knowledge Graph.
        
        Returns:
            Dict with counts of various node types.
        """
        stats = {
            "Papers": 0,
            "Drugs": 0,
            "Diseases": 0,
            "Genes": 0,
            "Relationships": 0
        }
        
        if not self.loader._connected:
            return stats

        queries = {
            "Papers": "MATCH (n:Paper) RETURN count(n) as count",
            "Drugs": "MATCH (n:Compound) RETURN count(n) as count", # Assuming 'Compound' maps to drugs
            "Diseases": "MATCH (n:Disease) RETURN count(n) as count",
            "Genes": "MATCH (n:Gene) RETURN count(n) as count",
            "Relationships": "MATCH ()-[r]->() RETURN count(r) as count"
        }

        for key, query in queries.items():
            try:
                result = self.loader.execute_query(query)
                if result and len(result) > 0:
                    stats[key] = result[0]['count']
            except Exception as e:
                logger.warning(f"Failed to get stats for {key}: {e}")
        
        return stats

    def find_potential_repurposing(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Identify potential drug repurposing candidates.
        Pattern: Drug -> Targets -> Gene -> Associated with -> Disease
        (Simplified A-B-C logic for MVP)
        """
        if not self.loader._connected:
            return []

        query = """
        MATCH (d:Compound)-[:TARGETS]->(g:Gene)-[:ASSOCIATED_WITH]->(dis:Disease)
        RETURN d.name as Drug, g.name as Target, dis.name as Disease
        LIMIT $limit
        """
        
        try:
            return self.loader.execute_query(query, {"limit": limit}) or []
        except Exception as e:
            logger.error(f"Repurposing query failed: {e}")
            return []

    def find_shortest_path(self, start_name: str, end_name: str) -> List[Dict[str, Any]]:
        """
        Find the shortest path between two entities in the graph.
        """
        if not self.loader._connected:
            return []

        query = """
        MATCH (start {name: $start}), (end {name: $end})
        MATCH p = shortestPath((start)-[*]-(end))
        RETURN p
        """
        
        try:
            # Note: Returning raw path objects might need serialization adjustment
            # For MVP, we'll return a simplified list of nodes
            # real implementation would parse the path structure
            result = self.loader.execute_query(query, {"start": start_name, "end": end_name})
            return result or []
        except Exception as e:
            logger.error(f"Shortest path query failed: {e}")
            return []
