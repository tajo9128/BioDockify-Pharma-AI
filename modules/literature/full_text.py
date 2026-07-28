"""Full-text retriever — 3-tier: Europe PMC XML → PDF download → Hacker Agent (6 sub-strategies)."""
import logging
import re
import time
from typing import Dict, Optional, Tuple
from io import BytesIO

import requests

logger = logging.getLogger("literature.full_text")

# ─── CORE.ac.uk base URL ───
CORE_API = "https://api.core.ac.uk/v3/search/works"


class FullTextRetriever:
    """Source-agnostic full-text retriever using article identifiers.

    Three-tier strategy (tried in order per article):
    Tier 1: Europe PMC fullTextXML (requires PMCID) — instant XML full text
    Tier 2: PDF download from OA URL + pypdf extraction — keeps PDF bytes
    Tier 3: Hacker Agent — 6 sub-strategies tried sequentially:
        3a. CORE.ac.uk API — finds OA repository copies
        3b. Semantic Scholar openAccessPdf — pre-resolved OA PDF
        3c. Jina AI reader — fast LLM-friendly HTML extraction
        3d. Playwright stealth browser — full JavaScript rendering
        3e. Google Scholar PDF hunt — finds any available PDF copy
        3f. Direct publisher HTML scrape — raw text extraction
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 "
                "BioDockifyAI/2.0 (mailto:researcher@example.com)"
            )
        })
        self._last_request_time = 0.0
        self._last_pdf_bytes: Optional[bytes] = None  # cached from Tier 2

    def _rate_limit(self, min_interval: float = 1.0):
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    # ═══════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════

    def retrieve(self, paper: Dict) -> Optional[str]:
        """Run full retrieval. Returns full text string or None.

        Side effect: sets self._last_pdf_bytes if Tier 2 succeeded.

        Strategy (5 tiers, tried in order):
          Tier 1: Europe PMC fullTextXML (requires PMCID)
          Tier 2: Unpaywall OA lookup (requires DOI + email)
          Tier 3: OpenAlex OA location (requires DOI)
          Tier 4: Direct PDF download (publisher landing page)
          Tier 5: Hacker Agent (6 sub-strategies: CORE, S2, Jina, Playwright, Scholar, scrape)
        """
        self._last_pdf_bytes = None

        # Tier 1: Europe PMC
        full_text = self._tier1_europe_pmc(paper)
        if full_text and self._is_substantial_text(full_text):
            logger.info(f"Tier 1 OK (Europe PMC): {paper.get('title', '?')[:60]}")
            return full_text

        # Tier 2: Unpaywall
        full_text, pdf_bytes = self._tier2_unpaywall(paper)
        if full_text and self._is_substantial_text(full_text):
            self._last_pdf_bytes = pdf_bytes
            logger.info(f"Tier 2 OK (Unpaywall): {paper.get('title', '?')[:60]}")
            return full_text

        # Tier 3: OpenAlex
        full_text, pdf_bytes = self._tier3_openalex(paper)
        if full_text and self._is_substantial_text(full_text):
            self._last_pdf_bytes = pdf_bytes
            logger.info(f"Tier 3 OK (OpenAlex): {paper.get('title', '?')[:60]}")
            return full_text

        # Tier 4: Direct PDF download
        full_text, pdf_bytes = self._tier4_pdf_download(paper)
        if full_text and self._is_substantial_text(full_text):
            self._last_pdf_bytes = pdf_bytes
            logger.info(f"Tier 4 OK (PDF): {paper.get('title', '?')[:60]}")
            return full_text

        # Tier 5: Hacker Agent
        full_text = self._tier5_hacker_agent(paper)
        if full_text and self._is_substantial_text(full_text):
            logger.info(f"Tier 5 OK (Hacker): {paper.get('title', '?')[:60]}")
            return full_text

        logger.warning(f"ALL TIERS FAILED: {paper.get('title', '?')[:60]}")
        return None

    async def retrieve_async(self, paper: Dict) -> Optional[str]:
        """Async wrapper for retrieve() — runs in thread pool."""
        import asyncio
        return await asyncio.to_thread(self.retrieve, paper)

    def get_last_pdf_bytes(self) -> Optional[bytes]:
        """Return raw PDF bytes from the last successful Tier 2 download."""
        return self._last_pdf_bytes

    # ═══════════════════════════════════════════════════════════════
    # Tier 1: Europe PMC full-text XML
    # ═══════════════════════════════════════════════════════════════

    def _tier1_europe_pmc(self, paper: Dict) -> Optional[str]:
        pmcid = paper.get("pmcid", "")
        if not pmcid:
            return None

        try:
            self._rate_limit(1.0)
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
            resp = self.session.get(url, timeout=30)

            if resp.status_code != 200 or len(resp.text) < 200:
                logger.debug(f"Europe PMC XML unavailable: HTTP {resp.status_code}")
                return None

            clean = re.sub(r"<[^>]+>", " ", resp.text)
            clean = re.sub(r"\s+", " ", clean).strip()
            return clean if len(clean) > 200 else None
        except Exception as e:
            logger.warning(f"Tier 1 failed: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════
    # Tier 2: Unpaywall — best OA lookup by DOI (free API, no key needed)
    # ═══════════════════════════════════════════════════════════════

    def _tier2_unpaywall(self, paper: Dict) -> Tuple[Optional[str], Optional[bytes]]:
        """Query Unpaywall for OA copy, then download + extract."""
        doi = paper.get("doi", "").strip()
        if not doi:
            return None, None

        try:
            self._rate_limit(0.5)
            # Unpaywall requires an email in the query
            url = f"https://api.unpaywall.org/v2/{doi}?email=biodockify@example.com"
            resp = self.session.get(url, timeout=15)

            if resp.status_code != 200:
                return None, None

            data = resp.json()
            best_oa = data.get("best_oa_location") or {}

            # Prefer PDF, fall back to full-text landing page
            pdf_url = best_oa.get("url_for_pdf")
            landing_url = best_oa.get("url")
            host_type = best_oa.get("host_type", "?")

            if pdf_url:
                text, pdf_bytes = self._download_and_extract_pdf(pdf_url)
                if text:
                    return text, pdf_bytes

            if landing_url:
                text = self._hack_jina(landing_url)
                if text and self._is_substantial_text(text):
                    return text, None

            return None, None
        except Exception as e:
            logger.debug(f"Tier 2 (Unpaywall) failed: {e}")
            return None, None

    # ═══════════════════════════════════════════════════════════════
    # Tier 3: OpenAlex — OA location lookup by DOI
    # ═══════════════════════════════════════════════════════════════

    def _tier3_openalex(self, paper: Dict) -> Tuple[Optional[str], Optional[bytes]]:
        """Query OpenAlex for OA locations, try each PDF."""
        doi = paper.get("doi", "").strip()
        if not doi:
            return None, None

        try:
            self._rate_limit(0.5)
            url = f"https://api.openalex.org/works/doi:{doi}"
            resp = self.session.get(url, timeout=15)

            if resp.status_code != 200:
                return None, None

            data = resp.json()
            oa_locations = data.get("open_access", {}) or {}
            locations = data.get("locations", []) or []

            # Collect candidate URLs
            candidates = []
            for loc in locations:
                pdf_url = loc.get("pdf_url")
                landing = loc.get("landing_page_url")
                if pdf_url:
                    candidates.append(pdf_url)
                if landing and landing not in candidates:
                    candidates.append(landing)

            # Also check best_oa_location
            best = oa_locations.get("oa_url") or data.get("best_oa_location", {}).get("pdf_url")
            if best and best not in candidates:
                candidates.insert(0, best)

            for url in candidates[:5]:  # try up to 5 locations
                if url.endswith(".pdf"):
                    text, pdf_bytes = self._download_and_extract_pdf(url)
                    if text:
                        return text, pdf_bytes
                else:
                    text = self._hack_jina(url)
                    if text and self._is_substantial_text(text):
                        return text, None

            return None, None
        except Exception as e:
            logger.debug(f"Tier 3 (OpenAlex) failed: {e}")
            return None, None

    # ═══════════════════════════════════════════════════════════════
    # Tier 4: Direct PDF download (from publisher or OA URL)
    # ═══════════════════════════════════════════════════════════════

    def _tier4_pdf_download(self, paper: Dict) -> Tuple[Optional[str], Optional[bytes]]:
        """Download PDF from known OA URL. Returns (text, pdf_bytes)."""
        pdf_url = paper.get("full_text_url") or paper.get("pdf_url")
        if not pdf_url:
            return None, None
        return self._download_and_extract_pdf(pdf_url)

    def _download_and_extract_pdf(self, url: str) -> Tuple[Optional[str], Optional[bytes]]:
        """Download PDF from URL and extract text. Returns (text, pdf_bytes)."""
        try:
            self._rate_limit(2.0)
            resp = self.session.get(url, timeout=45, stream=True)

            if resp.status_code != 200 or len(resp.content) < 1000:
                return None, None

            # Verify it's actually a PDF
            if not resp.content[:5].startswith(b"%PDF"):
                logger.debug(f"URL did not return PDF: {url[:60]}")
                return None, None

            pdf_bytes = resp.content
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(pdf_bytes))
            pages = []
            for page in reader.pages[:50]:  # up to 50 pages
                text = page.extract_text()
                if text and text.strip():
                    pages.append(text.strip())

            full = "\n\n".join(pages)
            if len(full) > 500:
                return full, pdf_bytes
            return None, None
        except Exception as e:
            logger.debug(f"PDF download failed: {e}")
            return None, None

    # ═══════════════════════════════════════════════════════════════
    # Tier 5: Hacker Agent — 6 sub-strategies
    # ═══════════════════════════════════════════════════════════════

    def _tier5_hacker_agent(self, paper: Dict) -> Optional[str]:
        """Try 6 sub-strategies in sequence until one returns valid text."""
        title = paper.get("title", "")
        doi = paper.get("doi", "")
        url = paper.get("url", "")

        strategies = [
            ("5a-CORE.ac.uk",    lambda: self._hack_core_ac_uk(title, doi)),
            ("5b-SemanticScholar", lambda: self._hack_semantic_scholar(paper)),
            ("5c-JinaAI",        lambda: self._hack_jina(doi or url)),
            ("5d-Playwright",    lambda: self._hack_playwright(doi or url)),
            ("5e-GoogleScholar", lambda: self._hack_google_scholar(title)),
            ("5f-RawScrape",     lambda: self._hack_raw_scrape(doi or url)),
        ]

        for label, strategy in strategies:
            try:
                logger.debug(f"Trying {label} for: {title[:60]}")
                result = strategy()
                if result and len(result) > 300:
                    if self._is_substantial_text(result):
                        logger.info(f"  {label} SUCCESS ({len(result)} chars)")
                        return f"[Source: {label}]\n\n{result}"
                    else:
                        logger.debug(f"  {label} returned only {len(result)} chars — trying next")
            except Exception as e:
                logger.debug(f"  {label} error: {e}")

        return None

    def _is_substantial_text(self, text: str) -> bool:
        """Heuristic: real article body must be substantial.

        Strict rules (aligned with auto_store stub rejection):
          - >= 3000 chars of body text (excludes abstracts)
          - Multiple paragraphs with varied content
          - Not boilerplate (high lexical diversity)
        """
        if not text or len(text) < 3000:
            return False

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.strip()) > 50]
        if len(paragraphs) < 3:
            return False

        # Lexical diversity check — real articles use varied vocabulary
        # Only reject if EXTREMELY repetitive (boilerplate/spam)
        words = text.lower().split()
        if len(words) > 100:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.10:
                return False

        return True

    # ── 3a: CORE.ac.uk API ──
    def _hack_core_ac_uk(self, title: str, doi: str) -> Optional[str]:
        """Search CORE.ac.uk for OA repository copies."""
        search_term = doi or title[:200]
        try:
            self._rate_limit(1.5)
            params = {"q": search_term, "limit": 3}
            resp = self.session.get(CORE_API, params=params, timeout=15)
            if resp.status_code != 200:
                return None

            data = resp.json()
            results = data.get("results", [])
            for item in results:
                download_url = item.get("downloadUrl") or item.get("fullText")
                if download_url:
                    try:
                        self._rate_limit(2.0)
                        dl = self.session.get(download_url, timeout=30)
                        if dl.status_code == 200 and len(dl.text) > 500:
                            return dl.text
                    except Exception:
                        continue
            return None
        except Exception as e:
            logger.debug(f"CORE.ac.uk failed: {e}")
            return None

    # ── 3b: Semantic Scholar openAccessPdf ──
    def _hack_semantic_scholar(self, paper: Dict) -> Optional[str]:
        """Use pre-fetched openAccessPdf URL from Semantic Scholar."""
        oa_pdf = paper.get("openAccessPdf")
        if isinstance(oa_pdf, dict):
            oa_url = oa_pdf.get("url")
            if oa_url:
                try:
                    self._rate_limit(2.0)
                    resp = self.session.get(oa_url, timeout=30, stream=True)
                    if resp.status_code == 200 and len(resp.content) > 1000:
                        from pypdf import PdfReader
                        reader = PdfReader(BytesIO(resp.content))
                        pages = []
                        for page in reader.pages[:50]:
                            text = page.extract_text()
                            if text and text.strip():
                                pages.append(text.strip())
                        full = "\n\n".join(pages)
                        if len(full) > 500:
                            return full
                except Exception:
                    pass
        return None

    # ── 3c: Jina AI reader ──
    def _hack_jina(self, target: str) -> Optional[str]:
        """Use Jina AI reader (free tier) to extract page content."""
        if not target:
            return None
        try:
            import httpx
        except ImportError:
            return None

        try:
            jina_url = f"https://r.jina.ai/{target}"
            headers = {"X-Return-Format": "markdown"}
            with httpx.Client(timeout=25) as client:
                resp = client.get(jina_url, headers=headers)
            if resp.status_code == 200 and len(resp.text) > 500:
                return resp.text
            return None
        except Exception as e:
            logger.debug(f"Jina failed: {e}")
            return None

    # ── 3d: Playwright stealth browser ──
    def _hack_playwright(self, target: str) -> Optional[str]:
        """Use Playwright stealth browser for JavaScript-rendered pages."""
        if not target:
            return None
        try:
            from modules.web_research.engine import WebResearchEngine
            import asyncio

            engine = WebResearchEngine()
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(engine.deep_read(target))
                finally:
                    loop.close()
                if result and "Error reading" not in result:
                    return result
                return None

            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(engine.deep_read(target), loop)
            result = future.result(timeout=60)
            if result and "Error reading" not in result:
                return result
            return None
        except Exception as e:
            logger.debug(f"Playwright failed: {e}")
            return None

    # ── 3e: Google Scholar PDF hunt ──
    def _hack_google_scholar(self, title: str) -> Optional[str]:
        """Search Google for PDF copies of the paper."""
        if not title:
            return None
        try:
            # Use DuckDuckGo lite to find PDF links (avoids Google anti-bot)
            query = f'"{title[:100]}" filetype:pdf'
            self._rate_limit(3.0)
            resp = self.session.get(
                "https://lite.duckduckgo.com/lite/",
                params={"q": query},
                timeout=15,
            )
            if resp.status_code != 200:
                return None

            # Extract PDF URLs from search results
            pdf_urls = re.findall(
                r'https?://[^\s<>"]+\.pdf[^\s<>"]*',
                resp.text,
                re.IGNORECASE,
            )
            for pdf_url in pdf_urls[:5]:
                try:
                    self._rate_limit(2.0)
                    dl = self.session.get(pdf_url, timeout=30, stream=True)
                    if dl.status_code == 200 and len(dl.content) > 1000:
                        from pypdf import PdfReader
                        reader = PdfReader(BytesIO(dl.content))
                        pages = []
                        for page in reader.pages[:50]:
                            text = page.extract_text()
                            if text and text.strip():
                                pages.append(text.strip())
                        full = "\n\n".join(pages)
                        if len(full) > 500:
                            return full
                except Exception:
                    continue
            return None
        except Exception as e:
            logger.debug(f"Google Scholar hunt failed: {e}")
            return None

    # ── 3f: Direct publisher HTML scrape ──
    def _hack_raw_scrape(self, target: str) -> Optional[str]:
        """Raw HTTP GET + BeautifulSoup text extraction — last resort."""
        if not target:
            return None
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return None

        try:
            self._rate_limit(1.0)
            resp = self.session.get(target, timeout=20, headers={
                "Accept": "text/html,application/xhtml+xml",
            })
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            # Try to find main article content
            article = (
                soup.find("article")
                or soup.find("div", class_=re.compile(r"article|content|main|body", re.I))
                or soup.find("main")
            )
            target_elem = article if article else soup

            text = target_elem.get_text(separator="\n")
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            clean = "\n\n".join(lines)

            return clean if len(clean) > 500 else None
        except Exception as e:
            logger.debug(f"Raw scrape failed: {e}")
            return None
