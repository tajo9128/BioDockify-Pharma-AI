"""
Notion Connector - Read pages and databases from Notion.
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class NotionConnector:
    """Connects to Notion API."""
    
    def __init__(self, token: str):
        self.token = token
        
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Search pages."""
        return []
        
    async def get_page_content(self, page_id: str) -> str:
        """Get page blocks."""
        return ""
