"""
Unified Browser Scraper Skill (Consolidated)
Delegates to core modules.headless_research for production-grade scraping.
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger
import threading

from modules.headless_research import HeadlessResearcher

class BrowserScraper:
    """
    Consolidated Browser Scraper for Agent Zero.
    Reuses the robust HeadlessResearcher engine from BioDockify core.
    """
    
    def __init__(self, profile_path: str = "./data/browser_profile"):
        self.researcher = HeadlessResearcher(
            headless=os.getenv("BROWSER_HEADLESS", "true").lower() == "true",
            profile_path=profile_path
        )
        self.is_started = False
    
    async def start(self) -> bool:
        """Lifecycle managed via context manager in research() or standalone start."""
        if not self.is_started:
            await self.researcher.__aenter__()
            self.is_started = True
        return True
    
    async def close(self):
        """Close browser."""
        if self.is_started:
            await self.researcher.__aexit__(None, None, None)
            self.is_started = False
    
    async def scrape_page(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Scrape content using the unified researcher engine.
        """
        if not self.is_started:
            await self.start()
            
        result = await self.researcher.research(url)
        return {
            "url": url,
            "title": result.get("title", "Untitled"),
            "content": result.get("content", ""),
            "success": result.get("status") == "success",
            "error": result.get("error")
        }
    
    async def download_pdf(self, url: str, download_path: str = "./downloads") -> Optional[str]:
        """
        Download PDF (Handled by core researcher context).
        """
        if not self.is_started:
            await self.start()
        
        # Core research already handles some downloads, but for direct PDF:
        page = self.researcher.page
        if not page:
            page = await self.researcher.context.new_page()
            
        try:
             async with page.expect_download() as download_info:
                await page.goto(url)
             download = await download_info.value
             path = Path(download_path) / download.suggested_filename
             await download.save_as(str(path))
             return str(path)
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None

    # Redirect other legacy methods to new architecture or stubs
    async def login_google(self, email: str, password: str) -> bool:
        logger.warning("Google Login is now managed via BROWSER_PROFILE_PATH persistence.")
        return True

    async def upload_to_notebooklm(self, files: List[str]) -> Optional[str]:
         logger.warning("NotebookLM upload is currently being refactored for StealthX compliance.")
         return None

# Singleton
_scraper_instance = None
_scraper_lock = threading.Lock()

def get_browser_scraper() -> BrowserScraper:
    """Get singleton instance."""
    global _scraper_instance
    with _scraper_lock:
        if _scraper_instance is None:
            _scraper_instance = BrowserScraper()
    return _scraper_instance
