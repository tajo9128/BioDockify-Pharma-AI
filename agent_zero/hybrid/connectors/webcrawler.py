"""
Web Crawler Connector - Based on Agent Zero SurfSense.
"""
from typing import List, Dict, Any
import logging
import asyncio
from dataclasses import asdict
from agent_zero.web_research.surfsense import SurfSense, CrawlConfig, ExtractionRules

logger = logging.getLogger(__name__)

class WebCrawlerConnector:
    """Uses SurfSense to crawl and extract web content."""
    
    def __init__(self, agent):
        self.agent = agent
        self.crawler = SurfSense()
        
    async def crawl_and_index(self, urls: List[str], depth: int = 1):
        """Crawl URLs and add to hybrid memory."""
        config = CrawlConfig(
            urls=urls,
            rules=self.crawler.create_default_rules(),
            depth=depth,
            max_pages=10  # Conservative default
        )
        
        logger.info(f"Starting crawl for {len(urls)} URLs")
        
        from agent_zero.web_research.executor import Executor
        executor = Executor()
        
        try:
            results = await self.crawler.crawl(config, executor)
            
            # Index results into memory
            for res in results:
                if res.success:
                    await self.agent.memory.add_memory(
                        f"Crawled Source: {res.url}\nTitle: {res.title}\nContent: {res.content[:1000]}",
                        area="fragments" # MemoryArea.FRAGMENTS
                    )
            
            return results
        except Exception as e:
            logger.error(f"Crawl failed: {e}")
            return []
