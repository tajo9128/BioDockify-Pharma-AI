"""
Scraper Module for Headless Browser
Extracts clean content from web pages using Markdownify and BeautifulSoup.
"""
import logging
from bs4 import BeautifulSoup
from markdownify import markdownify as md

logger = logging.getLogger("headless_research.scraper")

class Scraper:
    def __init__(self):
        pass

    async def clean_html(self, html: str) -> str:
        """Parse HTML, remove clutter, and return cleaned soup."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove intrusive elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'iframe', 'noscript', 'svg']):
                tag.decompose()
            
            # Remove ads and popups by common class names (heuristic)
            ad_keywords = ['ad', 'popup', 'newsletter', 'cookie', 'banner', 'sidebar']
            for tag in soup.find_all(class_=True):
                if any(k in str(tag.get('class')).lower() for k in ad_keywords):
                    tag.decompose()
            
            return str(soup)
        except Exception as e:
            logger.error(f"HTML cleaning failed: {e}")
            return html

    async def extract_markdown(self, html: str) -> str:
        """Convert HTML to clean Markdown."""
        try:
            cleaned_html = await self.clean_html(html)
            markdown = md(cleaned_html, heading_style="ATX", strip=['a', 'img']) # Strip links/images for clean text
            
            # Post-processing to remove excessive newlines
            import re
            markdown = re.sub(r'\n{3,}', '\n\n', markdown)
            return markdown.strip()
        except Exception as e:
            logger.error(f"Markdown extraction failed: {e}")
            return ""

    async def get_metadata(self, page) -> dict:
        """Extract page metadata (title, description)."""
        try:
            return {
                "title": await page.title(),
                "url": page.url,
            }
        except Exception:
            return {}
