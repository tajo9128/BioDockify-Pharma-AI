"""
Agent Zero SurfSense Executor

Fetches web pages, extracts text content, handles errors and retries.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import logging
import asyncio
import aiohttp
from datetime import datetime
from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class PageResult:
    """Result of fetching and processing a web page."""
    url: str
    title: str
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    success: bool
    error: Optional[str] = None


@dataclass
class ExecutorConfig:
    """Configuration for the Executor."""
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    user_agent: str = "Mozilla/5.0 (compatible; BioDockify-AgentZero/1.0)"
    max_concurrent: int = 5
    follow_redirects: bool = True
    max_redirects: int = 5
    max_response_size: int = 10 * 1024 * 1024  # 10MB


class Executor:
    """
    Fetches web pages and extracts text content.
    
    This component:
    - Fetches web pages
    - Extracts text content
    - Handles errors and retries
    - Returns structured results
    """
    
    def __init__(self, config: Optional[ExecutorConfig] = None):
        """
        Initialize the Executor.
        
        Args:
            config: Executor configuration (uses default if None)
        """
        self.config = config or ExecutorConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    async def start(self):
        """Start the executor and create HTTP session - Thread safe."""
        async with self._lock:
            try:
                if self.session is None or self.session.closed:
                    # Ensure session is actually None if it was closed
                    if self.session and self.session.closed:
                        self.session = None

                    timeout = aiohttp.ClientTimeout(total=self.config.timeout)
                    headers = {
                        'User-Agent': self.config.user_agent,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive'
                    }
                    self.session = aiohttp.ClientSession(
                        timeout=timeout,
                        headers=headers
                    )
                    logger.info("Executor started")
            except Exception as e:
                logger.error(f"Failed to start executor: {e}")
                raise
    
    async def stop(self):
        """Stop the executor and close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Executor stopped")
    
    async def fetch_raw(
        self,
        url: str,
        timeout: Optional[int] = None,
        _redirect_depth: int = 0
    ) -> Optional[tuple[bytes, str]]:
        """
        Fetch raw bytes and content type from a URL.
        """
        if _redirect_depth > self.config.max_redirects:
            logger.error(f"Max redirects ({self.config.max_redirects}) exceeded for {url}")
            return None

        if self.session is None:
            await self.start()
        
        timeout = timeout or self.config.timeout
        
        for attempt in range(self.config.max_retries):
            try:
                async with self.session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    allow_redirects=False 
                ) as response:
                    # 1. Check response size
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) > self.config.max_response_size:
                        logger.error(f"Response too large ({content_length} bytes) for {url}")
                        return None

                    # 2. Handle Redirects
                    if response.status in (301, 302, 303, 307, 308):
                        redirect_url = response.headers.get('Location')
                        if redirect_url:
                            return await self.fetch_raw(redirect_url, timeout, _redirect_depth + 1)
                        return None

                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', 'text/plain')
                        data = await response.read()
                        
                        if len(data) > self.config.max_response_size:
                             logger.error(f"Actual response size exceeded limit for {url}")
                             return None
                        
                        return data, content_type
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return None
                        
            except Exception as e:
                logger.warning(f"Fetch error for {url}: {e} (attempt {attempt + 1})")
            
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
        
        return None

    async def fetch_page(
        self,
        url: str,
        timeout: Optional[int] = None
    ) -> Optional[str]:
        """Fetch a page and return its text content."""
        raw = await self.fetch_raw(url, timeout)
        if raw:
            data, content_type = raw
            try:
                return data.decode('utf-8', errors='ignore')
            except:
                return None
        return None
    
    async def extract_text(
        self,
        html_or_soup: Any,
        url: str
    ) -> str:
        """
        Extract text content from HTML or existing BeautifulSoup object.
        (Fix for Performance Bottleneck #2: Double HTML Parsing)
        """
        try:
            # Re-use soup if provided
            if isinstance(html_or_soup, BeautifulSoup):
                soup = html_or_soup
            else:
                soup = BeautifulSoup(html_or_soup, 'html.parser')
            
            # Create a clone if we need to decompose elements but want to keep the original?
            # Actually, extract_text usually consumes the soup for text only.
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from {url}: {e}")
            return ""
    
    async def fetch_and_extract(
        self,
        url: str,
        timeout: Optional[int] = None
    ) -> PageResult:
        """
        Fetch a page and extract text content.
        
        Args:
            url: URL to fetch
            timeout: Request timeout
            
        Returns:
            Page result with extracted content
        """
        timestamp = datetime.now()
        
        # Fetch the page
        html = await self.fetch_page(url, timeout)
        
        if not html:
            return PageResult(
                url=url,
                title="",
                content="",
                metadata={'timestamp': timestamp.isoformat()},
                timestamp=timestamp,
                success=False,
                error="Failed to fetch page"
            )
        
        # Parse HTML ONCE (Fix for Performance Bottleneck #2)
        try:
            soup = BeautifulSoup(html, 'html.parser')
            title_tag = soup.find('title')
            title = title_tag.get_text().strip() if title_tag else ""
        except Exception as e:
            logger.error(f"Failed to parse HTML for {url}: {e}")
            # Use raw HTML for title extraction with regex as fallback
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else ""
            try:
                soup = BeautifulSoup(html, 'html.parser')  # Try again for extract_text
            except:
                soup = html # Absolute fallback
        
        # Extract text content passing the soup
        content = await self.extract_text(soup, url)
        
        # Create metadata
        metadata = {
            'url': url,
            'domain': urlparse(url).netloc,
            'content_length': len(content),
            'timestamp': timestamp.isoformat()
        }
        
        return PageResult(
            url=url,
            title=title,
            content=content,
            metadata=metadata,
            timestamp=timestamp,
            success=True
        )
    
    async def fetch_multiple(
        self,
        urls: List[str],
        max_concurrent: Optional[int] = None
    ) -> List[PageResult]:
        """
        Fetch multiple pages concurrently.
        
        Args:
            urls: List of URLs to fetch
            max_concurrent: Maximum concurrent requests (uses config default if None)
            
        Returns:
            List of page results
        """
        if self.session is None:
            await self.start()
        
        max_concurrent = max_concurrent or self.config.max_concurrent
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(url: str) -> PageResult:
            async with semaphore:
                return await self.fetch_and_extract(url)
        
        # Fetch all URLs concurrently
        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        page_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching {urls[i]}: {result}")
                page_results.append(PageResult(
                    url=urls[i],
                    title="",
                    content="",
                    metadata={'timestamp': datetime.now().isoformat()},
                    timestamp=datetime.now(),
                    success=False,
                    error=str(result)
                ))
            else:
                page_results.append(result)
        
        successful = sum(1 for r in page_results if r.success)
        logger.info(f"Fetched {successful}/{len(urls)} pages successfully")
        
        return page_results
    
    async def fetch_page_with_retry(
        self,
        url: str,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> Optional[str]:
        """
        Fetch a page with retry logic.
        
        Args:
            url: URL to fetch
            max_retries: Maximum retry attempts (uses config default if None)
            timeout: Request timeout
            
        Returns:
            HTML content or None if failed
        """
        max_retries = max_retries or self.config.max_retries
        
        for attempt in range(max_retries):
            try:
                content = await self.fetch_page(url, timeout)
                if content:
                    return content
            except Exception as e:
                logger.warning(f"Retry {attempt + 1}/{max_retries} for {url}: {e}")
            
            if attempt < max_retries - 1:
                delay = self.config.retry_delay * (2 ** attempt)
                await asyncio.sleep(delay)
        
        return None


# Convenience function for easy use
async def fetch_page_content(
    url: str,
    timeout: int = 30,
    user_agent: Optional[str] = None
) -> Optional[str]:
    """
    Convenience function to fetch a single page.
    
    Args:
        url: URL to fetch
        timeout: Request timeout
        user_agent: Custom user agent string
        
    Returns:
        HTML content or None if failed
    """
    config = ExecutorConfig(
        timeout=timeout,
        user_agent=user_agent or "Mozilla/5.0 (compatible; BioDockify-AgentZero/1.0)"
    )
    
    async with Executor(config) as executor:
        return await executor.fetch_page(url, timeout)


async def fetch_multiple_pages(
    urls: List[str],
    max_concurrent: int = 5,
    timeout: int = 30
) -> List[PageResult]:
    """
    Convenience function to fetch multiple pages.
    
    Args:
        urls: List of URLs to fetch
        max_concurrent: Maximum concurrent requests
        timeout: Request timeout
        
    Returns:
        List of page results
    """
    config = ExecutorConfig(
        timeout=timeout,
        max_concurrent=max_concurrent
    )
    
    async with Executor(config) as executor:
        return await executor.fetch_multiple(urls, max_concurrent)
