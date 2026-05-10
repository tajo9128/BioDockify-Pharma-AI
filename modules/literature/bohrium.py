"""
Bohrium Database Connector
Connects to Bohrium AI Agents via MCP/HTTP to retrieve scientific literature and patents.
"""

import os
import logging
import aiohttp
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("literature.bohrium")

@dataclass
class BohriumResult:
    title: str
    url: str
    content: str
    source_type: str # 'paper' or 'patent'
    metadata: Dict[str, Any]

class BohriumConnector:
    """
    Connects to a running Bohrium Agent (MCP) to fetch scientific data.
    """
    
    def __init__(self, endpoint: Optional[str] = None):
        self.endpoint = endpoint or os.getenv("BOHRIUM_API_URL", "http://localhost:7000/mcp")
        self.timeout = 30 # seconds
        self.api_key = os.getenv("BOHRIUM_API_KEY", "")
        self.consecutive_failures = 0
        self.circuit_open = False
        self.last_failure_time = 0

    def _check_circuit(self) -> bool:
        """Check if circuit is open (broken)."""
        if self.circuit_open:
            import time
            # Reset after 5 minutes
            if time.time() - self.last_failure_time > 300:
                self.circuit_open = False
                self.consecutive_failures = 0
                return True
            return False
        return True

    async def search_literature(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for scientific literature via Bohrium.
        """
        if not self._check_circuit():
            logger.warning("Bohrium circuit is OPEN. Skipping search.")
            return []
        return await self._execute_tool("search_papers", {"query": query, "limit": limit})

    async def search_patents(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for patents via Bohrium.
        """
        return await self._execute_tool("search_patents", {"query": query, "limit": limit})

    async def _execute_tool(self, tool_name: str, arguments: Dict) -> List[Dict]:
        """
        Executes an MCP tool on the Bohrium agent.
        Standard JSON-RPC 2.0 format.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "call_tool",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 1
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.endpoint, 
                    json=payload, 
                    headers=headers, 
                    timeout=self.timeout
                ) as response:
                    
                    if response.status != 200:
                        logger.warning(f"Bohrium API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    if "error" in data:
                        logger.error(f"Bohrium MCP Error: {data['error']}")
                        return []
                        
                    # MCP 'call_tool' usually returns { content: [...] }
                    # We assume the tool returns a JSON list in the content text or directly
                    result = data.get("result", {})
                    
                    # If the result is a list of items
                    if isinstance(result, list):
                        return result

                    content = result.get("content", [])
                    import json
                    try:
                        # Try to parse the first text content as JSON if it's a string
                        text_content = content[0].get("text", "")
                        if text_content.strip().startswith("["):
                            return json.loads(text_content)
                    except:
                        pass
                            
                    return []

        except Exception as e:
            import time
            self.consecutive_failures += 1
            self.last_failure_time = time.time()
            if self.consecutive_failures >= 5:
                self.circuit_open = True
                logger.error(f"Bohrium circuit OPENed after {self.consecutive_failures} failures.")
            
            logger.debug(f"Bohrium connection failed ({self.endpoint}): {e}")
            return []
