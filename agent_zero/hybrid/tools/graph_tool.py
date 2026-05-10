"""
Knowledge Graph Tool for Agent Zero.
Enables interaction with SurfSense Knowledge Engine for graph-based research data.
"""
import logging
from typing import Dict, Any, List, Optional
from modules.graph_builder.loader import get_loader

logger = logging.getLogger(__name__)

class KnowledgeGraphTool:
    """
    Allows the agent to query and manipulate the Knowledge Graph.
    Supports SurfSense Knowledge Engine (replaces Neo4j).
    """
    
    def __init__(self):
        self.loader = get_loader()

    def query_graph(self, params: Dict[str, Any]) -> str:
        """
        Execute a Cypher query against the Knowledge Graph.
        params:
            query (str): The Cypher query to execute.
            parameters (dict): Optional parameters for the query.
        """
        query = params.get("query")
        if not query:
            return "Error: 'query' parameter is required."
        
        parameters = params.get("parameters", {})
        
        try:
            results = self.loader.execute_query(query, parameters)
            if results is None:
                return "Graph database is not connected or offline."
            
            if not results:
                return "Query executed successfully. No results returned."
                
            # Limit results to avoid overwhelming context
            if len(results) > 20:
                return f"Returned {len(results)} records. First 20: {results[:20]}"
            
            return str(results)
        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            return f"Error executing query: {str(e)}"

    def get_schema(self, params: Dict[str, Any] = None) -> str:
        """
        Get the current graph schema (Node labels and Relationship types).
        """
        try:
            # SurfSense Knowledge Engine schema query
            labels_query = "CALL db.labels()"
            types_query = "CALL db.relationshipTypes()"
            
            labels = self.loader.execute_query(labels_query)
            types = self.loader.execute_query(types_query)
            
            if labels is None or types is None:
                 return "Graph database is not connected or offline."
                 
            # Format output
            flat_labels = [list(r.values())[0] for r in labels]
            flat_types = [list(r.values())[0] for r in types]
            
            return f"Node Labels: {flat_labels}\nRelationship Types: {flat_types}"
            
        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            return f"Error retrieval schema: {str(e)}"

    def add_node(self, params: Dict[str, Any]) -> str:
        """
        Add a node to the graph.
        params:
            label (str): Node label (e.g., 'Protein', 'Drug')
            properties (dict): Node properties.
        """
        label = params.get("label")
        props = params.get("properties", {})
        
        if not label:
            return "Error: 'label' is required."
            
        # Sanitize label (Cypher doesn't allow parameters for labels)
        if not label.isalnum():
             return "Error: Label must be alphanumeric."
             
        query = f"MERGE (n:{label} {{id: $id}}) SET n += $props RETURN n"
        
        # Ensure there's a unique ID if possible, otherwise just create
        if "id" not in props:
             # If no ID, use name or fallback to creating without merge on ID (duplicate risk)
             query = f"CREATE (n:{label}) SET n = $props RETURN n"
        
        try:
            self.loader.execute_query(query, {"props": props, "id": props.get("id")})
            return f"Added/Updated node :{label} with properties {props}"
        except Exception as e:
            return f"Error adding node: {e}"
