"""
Agent Zero SurfSense - Web Scraper

Manages URL queue, crawling strategy, extraction rules, and coordinates with Executor.
"""

from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
import logging
import asyncio
import re
from urllib.parse import urljoin, urlparse
from collections import deque
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ExtractionRules:
    """Rules for extracting content from web pages."""
    selectors: Dict[str, str] = field(default_factory=dict)
    clean_patterns: List[str] = field(default_factory=list)
    preserve_tags: List[str] = field(default_factory=lambda: ['h1', 'h2', 'h3', 'p', 'li'])
    min_content_length: int = 100
    max_content_length: int = 100000


@dataclass
class CrawlConfig:
    """Configuration for a crawl operation."""
    urls: List[str]
    rules: ExtractionRules
    depth: int = 1
    max_pages: int = 100
    respect_robots: bool = True
    delay_seconds: float = 1.0


@dataclass
class CrawlResult:
    """Result of a crawl operation."""
    url: str
    depth: int
    success: bool
    content: Optional[str] = None
    links_found: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SurfSense:
    """
    Web scraper that manages URL queue and crawling strategy.
    
    This component:
    - Manages URL queue and crawling strategy
    - Applies extraction rules
    - Enforces depth limits
    - Coordinates with Executor
    """
    
    def __init__(self):
        """Initialize SurfSense."""
        self.visited_urls: Set[str] = set()
        self.url_queue: deque = deque()
        self.domain_counts: Dict[str, int] = {}
        self.max_per_domain = 10
        self.max_queue_size = 1000  # Fix for Bug #4: Infinite URL Queue
        self.default_rules = ExtractionRules()
        
        # Default clean patterns for removing unwanted content
        self.default_rules.clean_patterns = [
            r'<script.*?</script>',
            r'<style.*?</style>',
            r'<nav.*?</nav>',
            r'<footer.*?</footer>',
            r'<header.*?</header>',
            r'<!--.*?-->',
            r'&nbsp;',
            r'\s+'
        ]
        
        # Default CSS selectors for content extraction
        self.default_rules.selectors = {
            'main': 'main, article, .content, #content',
            'title': 'h1, .title, #title',
            'abstract': '.abstract, #abstract, summary',
            'body': 'p, .text, .description'
        }
    
    async def crawl(
        self,
        config: CrawlConfig,
        executor: 'Executor'
    ) -> List[CrawlResult]:
        """
        Crawl URLs according to the configuration.
        
        Args:
            config: Crawl configuration
            executor: Executor instance for fetching pages
            
        Returns:
            List of crawl results
        """
        results = []
        self.visited_urls.clear()
        self.url_queue.clear()
        self.domain_counts.clear()
        
        # Initialize queue with seed URLs
        for url in config.urls:
            self.url_queue.append((url, 0))  # (url, depth)
        
        # Process queue
        while self.url_queue and len(results) < config.max_pages:
            url, depth = self.url_queue.popleft()
            
            # Skip if already visited
            if url in self.visited_urls:
                continue
            
            # Skip if depth exceeded
            if depth > config.depth:
                continue
            
            # Check domain limits
            domain = urlparse(url).netloc
            if self.domain_counts.get(domain, 0) >= self.max_per_domain:
                logger.debug(f"Skipping {url}: domain limit reached for {domain}")
                continue
            
            # Respect robots.txt if enabled
            if config.respect_robots and not await self._respect_robots_txt(url):
                logger.debug(f"Skipping {url}: robots.txt disallows")
                continue
            
            # Fetch and process the page
            try:
                result = await self._process_page(
                    url=url,
                    depth=depth,
                    config=config,
                    executor=executor
                )
                results.append(result)
                self.visited_urls.add(url)
                self.domain_counts[domain] = self.domain_counts.get(domain, 0) + 1
                
                # Add discovered links to queue (with size check for Bug #4)
                if depth < config.depth and len(self.url_queue) < self.max_queue_size:
                    for link in result.links_found:
                        if len(self.url_queue) < self.max_queue_size:
                            if link not in self.visited_urls:
                                self.url_queue.append((link, depth + 1))
                        else:
                            break
                
                # Respect delay between requests
                if config.delay_seconds > 0:
                    await asyncio.sleep(config.delay_seconds)
                    
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                results.append(CrawlResult(
                    url=url,
                    depth=depth,
                    success=False,
                    error=str(e)
                ))
        
        logger.info(f"Crawled {len(results)} pages")
        return results
    
    async def _process_page(
        self,
        url: str,
        depth: int,
        config: CrawlConfig,
        executor: 'Executor'
    ) -> CrawlResult:
        """
        Process a single page.
        """
        # Fetch raw content
        raw = await executor.fetch_raw(url, timeout=executor.config.timeout)
        
        if not raw:
            return CrawlResult(
                url=url,
                depth=depth,
                success=False,
                error="Failed to fetch content"
            )
        
        data, content_type = raw
        links_found = []
        
        # 1. Handle Text Content
        if "text/html" in content_type:
            html = data.decode('utf-8', errors='ignore')
            content = await executor.extract_text(html, url)
            links_found = self._extract_links(html, url)
        else:
            # For non-HTML (PDF, image, etc.), we don't extract links/text yet
            # but we preserve the raw data
            content = f"[Binary Content: {content_type}]"
            links_found = []

        # Apply extraction rules (only to text/html)
        if config.rules and "text/html" in content_type:
            content = await self.apply_extraction_rules(content, config.rules)
        
        # Check for empty/short content for HTML
        if "text/html" in content_type and (not content or len(content) < config.rules.min_content_length):
             return CrawlResult(
                url=url,
                depth=depth,
                success=False,
                error=f"Content too short or empty ({len(content) if content else 0} chars)"
            )

        # Create metadata
        metadata = {
            'depth': depth,
            'content_length': len(data),
            'links_count': len(links_found),
            'domain': urlparse(url).netloc,
            'content_type': content_type,
            'raw_data': data if "text/html" not in content_type else None
        }
        
        return CrawlResult(
            url=url,
            depth=depth,
            success=True,
            content=content,
            links_found=links_found,
            metadata=metadata
        )
    
    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """
        Extract links from HTML content.
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of absolute URLs
        """
        links = []
        
        # Extract href attributes from anchor tags
        href_pattern = r'<a[^>]+href=["\']([^"\']+)["\']'
        matches = re.findall(href_pattern, html, re.IGNORECASE)
        
        for href in matches:
            # Skip empty links and fragments
            if not href or href.startswith('#'):
                continue
            
            # Skip javascript and mailto links
            if href.startswith('javascript:') or href.startswith('mailto:'):
                continue
            
            # Convert to absolute URL
            absolute_url = urljoin(base_url, href)
            
            # Fix for Bug #13: Missing URL Validation
            if not self._is_valid_url(absolute_url):
                continue
                
            links.append(absolute_url)
        
        # Remove duplicates while preserving order (Fix for Bug #12: Inefficient List Deduplication)
        unique_links = list(dict.fromkeys(links))
        
        return unique_links

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid (Fix for Bug #13)."""
        try:
            result = urlparse(url)
            return all([result.scheme in ('http', 'https'), result.netloc])
        except:
            return False
    
    async def apply_extraction_rules(
        self,
        content: str,
        rules: ExtractionRules
    ) -> str:
        """
        Apply extraction rules to content.
        
        Args:
            content: Content to process
            rules: Extraction rules
            
        Returns:
            Processed content
        """
        if not content:
            return ""
        
        # Apply clean patterns
        for pattern in rules.clean_patterns:
            content = re.sub(pattern, ' ', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Check content length constraints
        if len(content) < rules.min_content_length:
            logger.debug(f"Content too short: {len(content)} < {rules.min_content_length}")
            return ""
        
        if len(content) > rules.max_content_length:
            logger.debug(f"Content too long: {len(content)} > {rules.max_content_length}")
            content = content[:rules.max_content_length]
        
        return content
    
    async def _respect_robots_txt(self, url: str) -> bool:
        """
        Check if URL is allowed by robots.txt (Fix for Bug #3: Missing Robots.txt Implementation).
        """
        from urllib.robotparser import RobotFileParser
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            rp = RobotFileParser()
            rp.set_url(robots_url)
            
            # Run the blocking read in a thread
            await asyncio.to_thread(rp.read)
            
            # Use a default user-agent or a custom one if available
            return rp.can_fetch("*", url)
        except Exception as e:
            logger.debug(f"Failed to check robots.txt for {url}: {e}")
            # Be conservative/permissive if check fails depending on policy; 
            # common approach is to allow if robots.txt is missing/unparseable
            return True
    
    def create_default_rules(self) -> ExtractionRules:
        """
        Create default extraction rules.
        
        Returns:
            Default extraction rules
        """
        return ExtractionRules(
            selectors=self.default_rules.selectors.copy(),
            clean_patterns=self.default_rules.clean_patterns.copy(),
            preserve_tags=self.default_rules.preserve_tags.copy(),
            min_content_length=100,
            max_content_length=100000
        )
    
    def create_medical_rules(self) -> ExtractionRules:
        """
        Create extraction rules optimized for medical/scientific content.
        
        Returns:
            Medical extraction rules
        """
        return ExtractionRules(
            selectors={
                'main': 'main, article, .content, #content, .abstract',
                'title': 'h1, .title, #title, .article-title',
                'abstract': '.abstract, #abstract, summary, .summary',
                'methods': '.methods, #methods, .methodology',
                'results': '.results, #results',
                'conclusion': '.conclusion, #conclusion, .conclusions',
                'body': 'p, .text, .description, .article-body'
            },
            clean_patterns=[
                r'<script.*?</script>',
                r'<style.*?</style>',
                r'<nav.*?</nav>',
                r'<footer.*?</footer>',
                r'<header.*?</header>',
                r'<aside.*?</aside>',
                r'<!--.*?-->',
                r'&nbsp;',
                r'\s+'
            ],
            preserve_tags=['h1', 'h2', 'h3', 'h4', 'p', 'li', 'strong', 'em'],
            min_content_length=200,
            max_content_length=150000
        )


# Convenience function for easy use
async def crawl_urls(
    urls: List[str],
    executor: 'Executor',
    depth: int = 1,
    max_pages: int = 100,
    rules: Optional[ExtractionRules] = None
) -> List[CrawlResult]:
    """
    Convenience function to crawl URLs.
    
    Args:
        urls: List of URLs to crawl
        executor: Executor instance
        depth: Maximum crawl depth
        max_pages: Maximum pages to crawl
        rules: Extraction rules (uses default if None)
        
    Returns:
        List of crawl results
    """
    surfsense = SurfSense()
    
    if rules is None:
        rules = surfsense.create_default_rules()
    
    config = CrawlConfig(
        urls=urls,
        rules=rules,
        depth=depth,
        max_pages=max_pages,
        respect_robots=True,
        delay_seconds=1.0
    )
    
    return await surfsense.crawl(config, executor)
