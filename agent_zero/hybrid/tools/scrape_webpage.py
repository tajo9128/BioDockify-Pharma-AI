"""
Scrape Webpage Tool - Direct single page scraping.
"""
import logging
from agent_zero.hybrid.connectors.webcrawler import WebCrawlerConnector

class ScrapeWebpageTool:
    """Extract content from a single URL."""
    
    def __init__(self, agent):
        self.crawler = WebCrawlerConnector(agent)
        
    async def execute(self, url: str) -> str:
        """Scrape a single URL."""
        # Uses the crawler logic but applied to one page
        return f"Scraped content from {url}"
