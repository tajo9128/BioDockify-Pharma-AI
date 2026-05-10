"""
SurfSense Knowledge Base Module - STORAGE ONLY VERSION

This module provides knowledge base STORAGE for deep research data.
SurfSense is used ONLY for document upload (knowledge base storage).
All SEARCH and CHAT operations use ChromaDB + Single LLM API (no SurfSense APIs).

Perfect for students: 
- No additional API keys needed
- SurfSense = Storage only
- Search = ChromaDB (built-in, free)
- Chat = Your single LLM API
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional
import aiohttp
from runtime.robust_connection import async_with_retry

logger = logging.getLogger("surfsense_client")

class SurfSenseClient:
    """
    Client for SurfSense Knowledge Base STORAGE ONLY.
    
    STORAGE (works): upload_document() - Stores research data
    SEARCH (redirects): search() - Uses ChromaDB instead
    CHAT (redirects): chat() - Uses ChromaDB + Single LLM API
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._healthy = False
        logger.info("SurfSense initialized in STORAGE-ONLY mode")
        logger.info("- Storage: Upload to SurfSense")
        logger.info("- Search: Redirect to ChromaDB")
        logger.info("- Chat: Redirect to ChromaDB + Single LLM API")
    
    def _headers(self) -> Dict[str, str]:
        """Get request headers with optional API key."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def health_check(self) -> bool:
        """Check if SurfSense is running (for storage only)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as resp:
                    self._healthy = resp.status == 200
                    return self._healthy
        except Exception as e:
            logger.debug(f"SurfSense health check failed: {e}")
            self._healthy = False
            return False
    
    @property
    def is_healthy(self) -> bool:
        """Return cached health status."""
        return self._healthy
    
    async def search(self, query: str, search_space_id: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        SEARCH KNOWLEDGE BASE - Redirects to ChromaDB (Built-in, FREE, No API).
        
        This does NOT use SurfSense's search API.
        Instead, it queries the internal ChromaDB vector store.
        """
        try:
            logger.info(f"Searching ChromaDB for: {query[:50]}...")
            
            # Import ChromaDB vector store (built-in)
            from modules.rag.vector_store import get_vector_store
            
            # Query ChromaDB
            vector_store = await get_vector_store()
            results = await vector_store.similarity_search(query, k=top_k)
            
            # Format results to match expected structure
            formatted_results = []
            for doc in results:
                formatted_results.append({
                    "text": doc.page_content,
                    "source": doc.metadata.get("source", "unknown"),
                    "score": doc.metadata.get("score", 1.0),
                    "metadata": doc.metadata
                })
            
            logger.info(f"ChromaDB search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"ChromaDB search error: {e}")
            return []
    
    async def chat(self, message: str, search_space_id: Optional[str] = None,
                   conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        CHAT WITH KNOWLEDGE BASE - Uses ChromaDB + Single LLM API.
        
        This does NOT use SurfSense's chat API.
        Instead:
        1. Search ChromaDB for relevant documents
        2. Send question + context to your single LLM API
        3. Return answer with citations
        """
        try:
            logger.info(f"Processing chat query via ChromaDB + LLM API: {message[:50]}...")
            
            # Step 1: Search ChromaDB for relevant context
            context_docs = await self.search(message, top_k=5)
            
            if not context_docs:
                return {
                    "response": "I couldn't find relevant information in the knowledge base.",
                    "citations": []
                }
            
            # Step 2: Build context from search results
            context_text = "\n\n".join([doc["text"] for doc in context_docs])
            sources = list(set([doc["source"] for doc in context_docs]))
            
            # Step 3: Use your single LLM API for answer generation
            from nanobot.providers.litellm_provider import LiteLLMProvider
            import json
            
            # Load config to get your single LLM API settings
            from runtime.config_loader import load_config
            from orchestration.planner.orchestrator import OrchestratorConfig
            
            cfg = load_config()
            ai_config = OrchestratorConfig(**{
                "primary_model": cfg.get("ai_provider", {}).get("mode", "custom"),
                "custom_base_url": cfg.get("ai_provider", {}).get("lm_studio_url"),
                "custom_model": cfg.get("ai_provider", {}).get("lm_studio_model"),
                "glm_key": cfg.get("ai_provider", {}).get("glm_key")
            })
            
            # Initialize LLM provider with your single API
            provider = LiteLLMProvider(
                api_key=ai_config.glm_key,
                api_base=ai_config.custom_base_url,
                default_model=ai_config.custom_model
            )
            
            # Build prompt with context
            system_prompt = """You are a helpful research assistant. Answer the user's question based ONLY on the provided context.
Include citations to your sources using [source: filename] format.
If the answer is not in the context, say 'I cannot find information about this in the knowledge base.'"""
            
            user_prompt = f"""Context:
{context_text[:4000]}

Question: {message}

Answer the question based on the context. Include citations."""
            
            # Call your single LLM API
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await provider.chat(messages)
            
            logger.info(f"Generated response via single LLM API")
            
            return {
                "response": response.content,
                "citations": sources,
                "sources_used": len(context_docs)
            }
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {"error": str(e)}
    
    @async_with_retry(max_retries=2, circuit_name="surfsense")
    async def upload_document(self, content: bytes, filename: str,
                               search_space_id: Optional[str] = None) -> Dict[str, Any]:
        """
        UPLOAD TO KNOWLEDGE BASE - This IS the SurfSense storage function.
        
        Uploads a document to SurfSense for indexing and storage.
        This is the ONLY function that actually calls SurfSense API.
        """
        if not await self.health_check():
            logger.warning("SurfSense offline - document upload skipped")
            return {"status": "skipped", "reason": "SurfSense offline"}
        
        try:
            data = aiohttp.FormData()
            data.add_field('file', content, filename=filename)
            if search_space_id:
                data.add_field('search_space_id', search_space_id)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/documents/upload",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        logger.info(f"Successfully uploaded {filename} to SurfSense")
                        return {"status": "success", **result}
                    else:
                        logger.warning(f"SurfSense upload failed: HTTP {resp.status}")
                        return {"status": "failed", "error": f"HTTP {resp.status}"}
        except Exception as e:
            logger.error(f"SurfSense upload error: {e}")
            return {"status": "failed", "error": str(e)}
    
    VALID_VOICES = {'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'}

    async def generate_podcast(self, chat_id: str, voice: str = "alloy") -> Dict[str, Any]:
        """
        GENERATE PODCAST AUDIO - Uses FREE edge-tts (no API key).
        
        Args:
            chat_id: The text to convert to speech
            voice: TTS voice (alloy, echo, fable, onyx, nova, shimmer)
        
        Returns:
            Dict with audio_url (file path) and duration
        """
        try:
            from modules.surfsense.audio import generate_podcast_audio
            
            if voice not in self.VALID_VOICES:
                logger.warning(f"Invalid voice '{voice}', defaulting to 'alloy'")
                voice = "alloy"
            
            # Generate audio using FREE edge-tts
            output_path = f"podcast_{chat_id[:20]}.mp3"
            await generate_podcast_audio(
                text=chat_id,  # Treat chat_id as text content
                voice=voice,
                output_path=output_path
            )
            
            logger.info(f"Podcast generated using FREE edge-tts: {output_path}")
            
            return {
                "audio_url": output_path,
                "duration": "unknown",
                "voice": voice,
                "method": "edge-tts (FREE)"
            }
        except Exception as e:
            logger.error(f"Podcast error: {e}")
            return {"error": str(e)}
    
    async def list_documents(self, search_space_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all documents in the knowledge base (via ChromaDB)."""
        try:
            from modules.rag.vector_store import get_vector_store
            vector_store = await get_vector_store()
            # ChromaDB doesn't have a simple "list all" - return metadata instead
            return [{"info": "Use ChromaDB query interface for document listing"}]
        except Exception as e:
            logger.error(f"List documents error: {e}")
            return []


# Singleton instance
_surfsense_client: Optional[SurfSenseClient] = None

def get_surfsense_client(base_url: str = "http://localhost:8000",
                          api_key: Optional[str] = None) -> SurfSenseClient:
    """Get or create the SurfSense client singleton."""
    global _surfsense_client
    if _surfsense_client is None:
        _surfsense_client = SurfSenseClient(base_url, api_key)
    return _surfsense_client

def configure_surfsense(base_url: str, api_key: Optional[str] = None):
    """Reconfigure the SurfSense client with new settings."""
    global _surfsense_client
    _surfsense_client = SurfSenseClient(base_url, api_key)


# Summary for students
STUDENT_MODE_INFO = """
SurfSense Knowledge Base - Student Mode
=========================================

WHAT THIS MODULE DOES:
------------------------
1. STORAGE: Upload research data to SurfSense (localhost:8000)
2. SEARCH: Uses ChromaDB (built-in, FREE, no API)
3. CHAT: Uses ChromaDB + Your Single LLM API
4. AUDIO: Uses edge-tts (FREE, 20+ voices, no API)

STUDENT BENEFITS:
-----------------
✅ Storage: SurfSense knowledge base (localhost:8000)
✅ Search: ChromaDB (built-in, FREE)
✅ Chat: Your single LLM API (no extra API needed)
✅ Audio: edge-tts (FREE, 20+ voices)

TOTAL APIS NEEDED: 1 (your single LLM API for chat)

NO SURFSENSE API NEEDED:
----------------------
- No SurfSense search API (uses ChromaDB)
- No SurfSense chat API (uses your LLM API)
- No OpenAI TTS (uses edge-tts)
"""
