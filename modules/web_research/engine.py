"""
MiroThinker-Inspired Web Research Engine
Integrates Serper (Google Search) and Jina (Content Scraping) for deep internet research.
"""

import requests
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger("web_research")

class WebResearchEngine:
    """
    Engine for deep web research capabilities.
    """
    
    def __init__(self, config):
        """
        Initialize with configuration dictionary or object.
        """
        # Handle both dict and object config access
        if isinstance(config, dict):
            ai_config = config.get("ai_provider", {})
        else:
            ai_config = getattr(config, "ai_provider", {})
            if not isinstance(ai_config, dict):
                # If using Pydantic model
                try:
                    ai_config = config.ai_provider
                except:
                    ai_config = {}

        self.serper_key = ai_config.get("serper_key", "")
        self.jina_key = ai_config.get("jina_key", "")
        
        if not self.serper_key:
            logger.warning("Serper API key not found. Web search will be limited.")

    async def search_google(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search: Serper (Paid) -> DDG (Free Lite) -> Headless (Free Strong)
        """
        if self.serper_key:
            return await self._search_serper(query, limit)
        
        # Free Tier: Try DDG Lite first (Fast)
        logger.info("Free Mode: Trying DuckDuckGo Lite...")
        # Enforce "Limited API Use" for free tier to 3 unless headless takes over
        free_limit = min(limit, 3)
        results = await self._search_ddg_lite(query, free_limit)
        
        # If DDG failed or returned specific failure status
        if not results or (len(results) == 1 and results[0].get("title") == "Search Unavailable"):
            logger.info("DDG Lite failed. Engaging Strong Mode: Headless Search.")
            return await self._search_headless_strong(query, free_limit)
            
        return results

    async def _search_serper(self, query: str, limit: int) -> List[Dict]:
        """Paid API: Serper (Google Results)"""
        url = "https://google.serper.dev/search"
        payload = json.dumps({
            "q": query, 
            "num": limit,
            "autocorrect": True
        })
        headers = {
            'X-API-KEY': self.serper_key,
            'Content-Type': 'application/json'
        }

        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, headers=headers, content=payload)
                response.raise_for_status()
                data = response.json()
            
            organic = data.get("organic", [])
            results = []
            
            for res in organic:
                results.append({
                    "title": res.get("title", ""),
                    "link": res.get("link", ""),
                    "snippet": res.get("snippet", ""),
                    "source": "Google (Serper)"
                })
                
            return results
        except Exception as e:
            logger.error(f"Serper search failed: {e}")
            return []

    async def _search_ddg_lite(self, query: str, limit: int) -> List[Dict]:
        """Free Tier 1: DuckDuckGo HTML Scrape (Fast)"""
        import httpx
        try:
            url = "https://html.duckduckgo.com/html/"
            data = {'q': query}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, data=data, headers=headers)
                
                # If block detected, raise to trigger fallback
                if resp.status_code in [403, 429]:
                    raise Exception(f"DDG Blocked: {resp.status_code}")
                
                resp.raise_for_status()
                text = resp.text
            
            import re
            links = re.findall(r'<a class="result__a" href="([^"]+)">([^<]+)</a>', text)
            snippets = re.findall(r'<a class="result__snippet" href="[^"]+">([^<]+)</a>', text)
            
            results = []
            for i, (href, title) in enumerate(links):
                if i >= limit: break
                snippet = snippets[i] if i < len(snippets) else ""
                results.append({
                    "title": title,
                    "link": href,
                    "snippet": snippet,
                    "source": "DuckDuckGo (Lite)"
                })
            
            if not results: raise Exception("No results found in HTML")
            return results
            
        except Exception as e:
            logger.warning(f"DDG Lite Scrape failed: {e}")
            return [{
                "title": "Search Unavailable",
                "link": "",
                "snippet": "Fallback trigger",
                "source": "System"
            }]

    async def _search_headless_strong(self, query: str, limit: int) -> List[Dict]:
        """Free Tier 2: Headless Browser Search (Strong/Slow)"""
        try:
            logger.info(f"🚀 Launching HeadlessX Stealth Search for: {query}")
            from modules.headless_research import HeadlessResearcher
            # We use the existing researcher but direct it to Google
            
            async with HeadlessResearcher() as researcher:
                # Direct browser to Google
                google_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                
                # We need to reuse the browser session
                page = await researcher.browser.new_page()
                await researcher.stealth.apply_stealth(page)
                
                await page.goto(google_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(2000) # Wait for results
                
                # Basic extraction via Playwright evaluation
                results = await page.evaluate("""
                    () => {
                        const items = document.querySelectorAll('div.g');
                        const data = [];
                        items.forEach(item => {
                            const titleEl = item.querySelector('h3');
                            const linkEl = item.querySelector('a');
                            const snippetEl = item.querySelector('div.VwiC3b'); // This class changes often for snippets
                            
                            if (titleEl && linkEl) {
                                data.push({
                                    title: titleEl.innerText,
                                    link: linkEl.href,
                                    snippet: snippetEl ? snippetEl.innerText : ''
                                });
                            }
                        });
                        return data;
                    }
                """)
                
                # Close this page (we launched it manually)
                await page.close()
                
            formatted = []
            for res in results[:limit]:
                formatted.append({
                    "title": res['title'],
                    "link": res['link'],
                    "snippet": res['snippet'],
                    "source": "Google (HeadlessX)"
                })
                
            if not formatted:
                return [{"title": "Headless Search Empty", "link": "", "snippet": "Google returned no results."}]
                
            return formatted
            
        except ImportError:
             return [{"title": "Headless Module Missing", "link": "", "snippet": "Install playwright."}]
        except Exception as e:
            logger.error(f"Headless Search Failed: {e}")
            return [{"title": "Search Failed", "link": "", "snippet": str(e)}]

    async def deep_read(self, url: str) -> str:
        """
        Smart Deep Read:
        1. Try Fast Mode (Jina/MiroThinker)
        2. If blocked/failed -> Try Strong Mode (HeadlessX Stealth)
        """
        # 1. FAST MODE: JINA
        try:
            import httpx
            jina_url = f"https://r.jina.ai/{url}"
            headers = {'X-Return-Format': 'markdown'}
            if self.jina_key:
                headers['Authorization'] = f"Bearer {self.jina_key}"
            
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(jina_url, headers=headers)
            
            if response.status_code == 200:
                content = response.text
                if len(content) > 500: # Valid content check
                    return content
                else:
                    logger.warning(f"Jina content too short ({len(content)} chars). Trying Headless fallback.")
            else:
                logger.warning(f"Jina failed ({response.status_code}). Trying Headless fallback.")
                
        except Exception as e:
            logger.warning(f"Fast read failed: {e}. Switching to Strong Mode.")

        # 2. STRONG MODE: HEADLESSX (Stealth Browser)
        try:
            logger.info(f"🚀 Deploying HeadlessX Stealth for: {url}")
            from modules.headless_research import HeadlessResearcher
            
            async with HeadlessResearcher() as researcher:
                result = await researcher.research(url)
                
            if result.get("status") == "success":
                return f"[Source: HeadlessX Stealth]\n\n{result.get('content', '')}"
            else:
                return f"Error reading content: {result.get('error', 'Unknown error')}"
                
        except ImportError:
            return "HeadlessX module not found. Install playwright to enable Strong Mode."
        except Exception as e:
            logger.error(f"HeadlessX failed: {e}")
            return f"Failed to read content (All methods exhausted): {e}"

    async def find_pdf_strong(self, title: str) -> Optional[str]:
        """
        Stealth Hunter: Aggressively hunts for a legal PDF copy of a paper.
        Uses HeadlessX to search for "filetype:pdf" and extracts text.
        """
        try:
            # 1. Search for PDF using Headless Search
            query = f'"{title}" filetype:pdf'
            logger.info(f"🕵️ Stealth Hunting for PDF: {title}")
            
            # Use our strong search to find a PDF link
            results = await self._search_headless_strong(query, limit=1)
            
            if not results or not results[0].get('link'):
                return None
                
            pdf_url = results[0]['link']
            logger.info(f"📄 Found potential PDF: {pdf_url}")
            
            # 2. Convert PDF to Text (using Jina which handles PDFs well, or direct)
            # Jina Reader is excellent at PDF-to-Markdown
            content = await self.deep_read(pdf_url)
            
            if "Error reading content" in content or len(content) < 200:
                return None
                
            return f"[Source: Stealth PDF Hunter - {pdf_url}]\n\n{content}"
            
        except Exception as e:
            logger.warning(f"PDF Hunt failed: {e}")
            return None

    async def research_topic(self, topic: str, depth: int = 3) -> str:
        """
        Performs a deep research workflow (Async).
        Efficiency Boost: Includes PDF Hunting for paywalled/short content.
        """
        effective_depth = depth
        if not self.serper_key:
            logger.info("Free Tier: Limiting research depth to 3.")
            effective_depth = min(depth, 3)
        else:
            logger.info(f"Paid Tier: Full research depth {depth}.")
        
        results = await self.search_google(topic, limit=effective_depth)
        
        combined_report = [f"# Research Report: {topic}\n"]
        combined_report.append(f"**Mode:** {'Unlimited (Paid)' if self.serper_key else 'Limited (Free)'}")
        combined_report.append(f"**Sources Found:** {len(results)}\n")
        
        for i, res in enumerate(results):
            if not res['link']: continue
            
            print(f"[*] Reading source {i+1}: {res['title']}")
            combined_report.append(f"## Source {i+1}: {res['title']}")
            combined_report.append(f"**URL:** {res['link']}")
            combined_report.append(f"**Source:** {res.get('source', 'Web')}\n")
            
            # Attempt 1: Standard Deep Read
            content = await self.deep_read(res['link'])
            
            # Efficiency Check: If content is too short (likely paywall/abstract), Hunt for PDF
            if len(content) < 1000:
                logger.info(f"Content short ({len(content)} chars). Triggering PDF Hunt...")
                pdf_content = await self.find_pdf_strong(res['title'])
                if pdf_content:
                    content = f"{content}\n\n--- PDF VERSION FOUND ---\n{pdf_content}"
                    logger.info("PDF Hunt Successful!")
                else:
                    logger.info("PDF Hunt yielded no results.")
            
            # Truncate if too massive
            max_len = 15000 
            if len(content) > max_len:
                content = content[:max_len] + "\n...[Truncated]..."
                
            combined_report.append(content)
            combined_report.append("\n---\n")
            
        return "\n".join(combined_report)

    def _fallback_search(self, query: str) -> List[Dict]:
        """Deprecated: Logic moved to search_google"""
        return []
