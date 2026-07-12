"""Full-text retriever — 3-tier: Europe PMC XML → PDF download → Hacker Agent."""
import logging
import re
import time
from typing import Dict, Optional
from io import BytesIO

import requests

logger = logging.getLogger("literature.full_text")


class FullTextRetriever:
    """Source-agnostic full-text retriever using article identifiers.

    Three-tier strategy (tried in order per article):
    Tier 1: Europe PMC fullTextXML (requires PMCID)
    Tier 2: PDF download from OA URL + pypdf extraction
    Tier 3: Hacker Agent via WebResearchEngine.deep_read()
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BioDockifyAI/1.0 (mailto:researcher@example.com)"
        })
        self._last_request_time = 0.0

    def _rate_limit(self, min_interval: float = 1.0):
        """Enforce minimum interval between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    def retrieve(self, paper: Dict) -> Optional[str]:
        """Run 3-tier retrieval. Returns full text string or None."""
        full_text = self._tier1_europe_pmc(paper)
        if full_text:
            logger.info(f"Tier 1 OK: {paper.get('title', '?')[:60]}")
            return full_text

        full_text = self._tier2_pdf_download(paper)
        if full_text:
            logger.info(f"Tier 2 OK: {paper.get('title', '?')[:60]}")
            return full_text

        full_text = self._tier3_hacker_agent(paper)
        if full_text:
            logger.info(f"Tier 3 OK: {paper.get('title', '?')[:60]}")
            return full_text

        logger.debug(f"All tiers failed: {paper.get('title', '?')[:60]}")
        return None

    def _tier1_europe_pmc(self, paper: Dict) -> Optional[str]:
        """Fetch full-text XML from Europe PMC by PMCID.

        Europe PMC fullTextXML API is free, no API key required.
        Returns clean plain text with XML tags stripped.
        """
        pmcid = paper.get("pmcid", "")
        if not pmcid:
            return None

        try:
            self._rate_limit(1.0)
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
            resp = self.session.get(url, timeout=30)

            if resp.status_code != 200 or len(resp.text) < 200:
                logger.debug(f"Europe PMC fullTextXML unavailable for {pmcid}: HTTP {resp.status_code}")
                return None

            xml_text = resp.text
            clean = re.sub(r"<[^>]+>", " ", xml_text)
            clean = re.sub(r"\s+", " ", clean).strip()

            if len(clean) > 200:
                return clean
            return None
        except Exception as e:
            logger.warning(f"Tier 1 Europe PMC failed for {pmcid}: {e}")
            return None

    def _tier2_pdf_download(self, paper: Dict) -> Optional[str]:
        """Download PDF from OA URL and extract text via pypdf.

        Uses full_text_url (from Unpaywall/Europe PMC) or pdf_url (from arXiv/Semantic Scholar).
        Limits to 30 pages to avoid memory issues.
        """
        pdf_url = paper.get("full_text_url") or paper.get("pdf_url")
        if not pdf_url:
            return None

        try:
            self._rate_limit(2.0)
            resp = self.session.get(pdf_url, timeout=30, stream=True)

            if resp.status_code != 200 or len(resp.content) < 1000:
                logger.debug(f"PDF download failed: HTTP {resp.status_code}, {len(resp.content)} bytes")
                return None

            from pypdf import PdfReader

            reader = PdfReader(BytesIO(resp.content))
            pages = []
            for i, page in enumerate(reader.pages[:30]):
                text = page.extract_text()
                if text and text.strip():
                    pages.append(text.strip())

            full = "\n\n".join(pages)
            return full if len(full) > 200 else None
        except Exception as e:
            logger.warning(f"Tier 2 PDF failed for {pdf_url}: {e}")
            return None

    def _tier3_hacker_agent(self, paper: Dict) -> Optional[str]:
        """Hacker Agent — use WebResearchEngine.deep_read() for any web-accessible content.

        Handles paywalled articles by scraping whatever HTML content is available.
        Uses Jina AI reader first (fast), falls back to Playwright stealth browser.
        """
        doi = paper.get("doi", "")
        url = paper.get("url", "")

        target_url = None
        if doi:
            target_url = f"https://doi.org/{doi}"
        elif url:
            target_url = url

        if not target_url:
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
                    result = loop.run_until_complete(engine.deep_read(target_url))
                finally:
                    loop.close()
                if result and len(result) > 200 and "Error reading" not in result:
                    return result
                return None

            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(engine.deep_read(target_url), loop)
            result = future.result(timeout=60)
            if result and len(result) > 200 and "Error reading" not in result:
                return result
            return None
        except Exception as e:
            logger.warning(f"Tier 3 Hacker Agent failed for {target_url}: {e}")
            return None
