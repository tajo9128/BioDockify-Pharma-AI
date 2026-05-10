"""
Knowledge Base Tool - Search SurfSense memory.
"""
from typing import List, Dict, Any
import logging

class KnowledgeBaseTool:
    """Tool for agents to search the knowledge base."""
    
    def __init__(self, retriever):
        self.retriever = retriever
        
    async def execute(self, query: str, filters: Dict[str, Any] = None) -> str:
        """Search and format results."""
        results = await self.retriever.search(query, top_k=5, filters=filters)
        
        if not results:
            return "No relevant information found in knowledge base."
            
        formatted = []
        for i, doc in enumerate(results, 1):
            title = doc.get('title', 'Untitled')
            content = doc.get('content', '')[:500] + "..."
            formatted.append(f"{i}. [{title}]\n{content}")
            
        return "\n\n".join(formatted)
