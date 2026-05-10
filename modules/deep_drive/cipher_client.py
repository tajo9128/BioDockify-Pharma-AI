import os
import aiohttp
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class CipherClient:
    """
    Client for interacting with the Cipher (Deep Drive) API via MCP.
    """

    def __init__(self, base_url: str = "http://cipher-api:3000"):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api"
        self._server_id: Optional[str] = None
        self._tools_map: Dict[str, str] = {} # Map 'short_name' -> 'full_tool_name'

    async def _get_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession()

    async def initialize(self):
        """
        Discover Cipher server ID and available tools.
        """
        if self._server_id:
            return

        url = f"{self.api_url}/mcp/tools"
        try:
            async with await self._get_session() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.error(f"Failed to fetch MCP tools: {response.status} - {text}")
                        return

                    data = await response.json()
                    tools = data.get("data", {}).get("tools", [])
                    
                    # Find Cipher's memory tools
                    for tool in tools:
                        name = tool.get("name", "")
                        server_id = tool.get("serverId")
                        
                        # We identify Cipher tools by their prefix or specific names
                        if "cipher_memory_search" in name:
                            self._server_id = server_id
                            self._tools_map["memory_search"] = name
                        elif "cipher_extract_and_operate_memory" in name:
                            self._server_id = server_id
                            self._tools_map["store_memory"] = name
                        elif "search_graph" in name: # Might happen if not prefixed check both
                            self._server_id = server_id # Assume same server
                            self._tools_map["graph_search"] = name

            logger.info(f"Cipher Client initialized. Server ID: {self._server_id}. Tools: {self._tools_map.keys()}")

        except Exception as e:
            logger.error(f"Error initializing Cipher Client: {e}")

    async def _execute_tool(self, tool_key: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute an MCP tool by its short key (e.g., 'memory_search').
        """
        if not self._server_id:
            await self.initialize()
            if not self._server_id:
                logger.error("Cipher Client not initialized (no server ID).")
                return None

        tool_name = self._tools_map.get(tool_key)
        if not tool_name:
            # Fallback: try to guess or use key as name if missing from map
            tool_name = f"cipher_{tool_key}" if not tool_key.startswith("cipher_") else tool_key
            logger.warning(f"Tool key '{tool_key}' not found in discovery map. Trying '{tool_name}'.")

        url = f"{self.api_url}/mcp/servers/{self._server_id}/tools/{tool_name}/execute"
        payload = {"arguments": args}

        try:
            async with await self._get_session() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.error(f"Failed to execute tool {tool_name}: {response.status} - {text}")
                        return None
                    
                    data = await response.json()
                    # Result is usually in data.data.result
                    return data.get("data", {}).get("result", {})

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return None

    async def store_memory(self, interaction: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store a new memory from an interaction.
        """
        args = {"interaction": interaction}
        if context:
            args["context"] = context
            
        result = await self._execute_tool("store_memory", args)
        if result and not result.get("isError"):
            # Check for success in tool output content?
            # Cipher usually returns text/json content.
            return True
        return False

    async def search_memory(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search knowledge memory.
        """
        args = {
            "query": query,
            "top_k": top_k
        }
        result = await self._execute_tool("memory_search", args)
        
        if not result or result.get("isError"):
            return []

        # Parse result content
        # MCP result content is a list of text/image
        # Cipher tools usually return JSON in the text content
        try:
            content = result.get("content", [])
            for item in content:
                if item.get("type") == "text":
                    import json
                    # The tool might return a stringified JSON object or just text
                    text = item.get("text", "")
                    if text.strip().startswith("{"):
                        data = json.loads(text)
                        if data.get("success") and "results" in data:
                            return data["results"]
            
            return [] 
        except Exception as e:
            logger.error(f"Error parsing memory search result: {e}")
            return []

    async def search_graph(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search the knowledge graph.
        """
        # Mapping `query` to textSearch/properties as graph search is more structured
        args = {
            "textSearch": query,
            "limit": limit
        }
        result = await self._execute_tool("graph_search", args)
        
        if not result or result.get("isError"):
            return {}

        try:
            content = result.get("content", [])
            for item in content:
                if item.get("type") == "text":
                    import json
                    text = item.get("text", "")
                    if text.strip().startswith("{"):
                        data = json.loads(text)
                        if data.get("success") and "results" in data:
                            return data["results"]
            return {}
        except Exception as e:
            logger.error(f"Error parsing graph search result: {e}")
            return {}
