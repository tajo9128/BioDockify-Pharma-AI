"""
Headless Research Engine
Main orchestrator for stealth browsing, content extraction, and SurfSense sync.
Constraints: No Docker, strictly Playwright Python.
"""
import os
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    # Define stubs for type hinting
    class Page: pass
    class Browser: pass
    class BrowserContext: pass

from .stealth import StealthContext
from .behavior import HumanBehavior
from .scraper import Scraper
from modules.surfsense import get_surfsense_client

logger = logging.getLogger("headless_research.engine")

class HeadlessResearcher:
    """
    Main class for autonomous deep research.
    Manages browser lifecycle, applies stealth, handles extraction, and syncs to SurfSense.
    """
    
    def __init__(self, headless: bool = True, profile_path: str = "./data/browser_profile"):
        self.headless = headless
        self.profile_path = Path(profile_path)
        self.profile_path.mkdir(parents=True, exist_ok=True)
        
        self.stealth = StealthContext()
        self.behavior = HumanBehavior()
        self.scraper = Scraper()
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
        self.timeout = int(os.getenv("BROWSER_TIMEOUT", "60000"))

    async def __aenter__(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is not installed. Deep research capabilities are disabled. "
                "Install with 'pip install playwright' and 'playwright install'."
            )
            
        self.playwright = await async_playwright().start()
        
        # Launch options for stability and stealth
        args = self.stealth.get_stealth_args()
        
        # Use persistent context to consolidate feature from agent_zero skill
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_path),
            headless=self.headless,
            args=args,
            viewport={'width': 1280, 'height': 800}
        )
        self.browser = self.context.browser # For abstraction compatibility
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()

    async def research(self, url: str) -> Dict[str, Any]:
        """
        Deep research a URL:
        1. Navigate stealthily
        2. Simulate human reading
        3. Extract content
        4. Sync to Knowledge Base / SurfSense
        """
        if not self.context:
            raise RuntimeError("Browser not started. Use 'async with' context manager.")
        
        logger.info(f"Starting deep research on: {url}")
        
        # Reuse or create page
        page = await self.context.new_page()
        self.page = page
        
        # Inject Stealth Scripts
        await self.stealth.apply_stealth(page)
        
        try:
            # 1. Navigate with robust timeout
            response = await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            if not response or response.status >= 400:
                logger.warning(f"Navigation failed with status {response.status if response else 'Unknown'}")
                return {"status": "failed", "error": f"Navigation failed: {response.status if response else 'Unknown'}"}
            
            # 2. Simulate Human Behavior
            await self.behavior.simulate_reading(page)
            
            # 3. Extract Content
            html = await page.content()
            markdown_content = await self.scraper.extract_markdown(html)
            metadata = await self.scraper.get_metadata(page)
            
            # Check for excessive size or empty content
            if not markdown_content or len(markdown_content) < 50:
                logger.warning(f"Scrape produced very low content for {url}")
            
            result = {
                "status": "success",
                "url": url,
                "title": metadata.get("title", "Untitled"),
                "content": markdown_content,
                "length": len(markdown_content)
            }
            
            # 4. Sync to SurfSense
            await self._sync_to_surfsense(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Research failed for {url}: {e}")
            screenshot_path = f"error_{url.replace('://', '_').replace('/', '_')[:100]}.png"
            try:
                await page.screenshot(path=screenshot_path)
            except:
                pass
            return {"status": "error", "error": str(e)}
        finally:
            await page.close() # Close page but keep context

    async def _sync_to_surfsense(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Upload research result to SurfSense as a document."""
        sync_status = {"surfsense": "unknown", "internal": "pending"}
        if result.get("status") != "success":
            return sync_status
            
        try:
            content = result.get("content", "").encode("utf-8")
            filename = f"research_{result['title'][:50].strip().replace(' ', '_')}.md"
            
            # Use the SurfSense client we built earlier
            client = get_surfsense_client()
            upload_result = await client.upload_document(content, filename)
            sync_status["surfsense"] = upload_result.get("status", "success")
            
            logger.info(f" synced to SurfSense: {upload_result}")
            
            # Also sync to internal vector store (fallback/dual-write)
            from modules.library.store import library_store
            from modules.rag.ingestor import ingestor
            from modules.rag.vector_store import get_vector_store
            
            # internal store
            file_record = library_store.add_file(content, filename)
            
            # internal ingest
            # We treat it as a temporary file for ingestion
            temp_path = library_store.get_file_path(file_record['id'])
            chunks = ingestor.ingest_file(str(temp_path))
            if chunks:
                await get_vector_store().add_documents(chunks)
                logger.info(f"Synced to internal KB: {len(chunks)} chunks")
                sync_status["internal"] = "success"
                
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            sync_status["error"] = str(e)
            
        return sync_status

# Convenience function for simple usage
async def deep_research(url: str) -> Dict[str, Any]:
    if not PLAYWRIGHT_AVAILABLE:
        return {
            "status": "error", 
            "error": "Playwright not installed. Deep research unavailable."
        }
        
    async with HeadlessResearcher() as researcher:
        return await researcher.research(url)
