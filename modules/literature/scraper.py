"""
PubMed Scraper Module - Zero-Cost Pharma Research AI
Handles fetching of scientific literature using Bio.Entrez (public API) with offline resilience.
"""

import re
import socket
import time
import os
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
import logging

try:
    from Bio import Entrez
except ImportError:
    Entrez = None

from modules.literature.openalex import OpenAlexScraper
from modules.literature.europe_pmc import EuropePMCScraper
from modules.literature.crossref import CrossRefScraper
from modules.literature.biorxiv import BioRxivScraper
from modules.literature.bohrium import BohriumConnector

from runtime.robust_connection import with_retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimitHandler:
    """
    Manages API rate limits and enforces sleep/resume logic.
    """
    def __init__(self, requests_per_second: int = 3):
        self.delay = 1.0 / requests_per_second
        self.last_request_time = 0
        self.consecutive_errors = 0
        
    def wait(self):
        """Passively wait to respect rate limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()

    def handle_error(self, error: Exception) -> bool:
        """
        Handle API errors. Returns True if we should retry (after sleep).
        Returns False if we should abort.
        """
        err_str = str(error).lower()
        
        # HTTP 429: Too Many Requests
        if "429" in err_str or "too many requests" in err_str:
            logger.warning("⚠ API Rate Limit Reached (HTTP 429). Entering SLEEP MODE for 60s...")
            time.sleep(60) 
            return True
            
        # HTTP 5xx: Server Errors (Retry with backoff)
        if "500" in err_str or "502" in err_str or "503" in err_str:
             sleep_time = 5 * (2 ** self.consecutive_errors)
             logger.warning(f"⚠ Server Error. Retrying in {sleep_time}s...")
             time.sleep(sleep_time)
             self.consecutive_errors += 1
             return self.consecutive_errors < 5 # Max 5 retries
             
        self.consecutive_errors = 0
        return False

# Global Rate Limiter
rate_limiter = RateLimitHandler(requests_per_second=3)

@dataclass
class PubmedScraperConfig:
    """Configuration for the PubMed Scraper."""
    email: str = os.getenv("PUBMED_EMAIL", "researcher@example.com")  # Required by NCBI
    api_key: Optional[str] = os.getenv("PUBMED_API_KEY")  # Optional: Increases rate limit
    max_results: int = 10
    tool_name: str = "BioDockify"

class PubmedScraper:
    """
    Robust PubMed scraper with offline handling and batch capabilities.
    """
    
    def __init__(self, config: Optional[PubmedScraperConfig] = None):
        """Initialize the scraper with configuration."""
        self.config = config or PubmedScraperConfig()
        
        if Entrez:
            Entrez.email = self.config.email
            Entrez.tool = self.config.tool_name
            if self.config.api_key:
                Entrez.api_key = self.config.api_key
        else:
            logger.warning("Biopython not installed. Scraper will function in OFFLINE mode only.")

    def _is_valid_pmid(self, pmid: str) -> bool:
        """Validate PMID format (Numeric, non-NaN)."""
        if not pmid or not pmid.isdigit():
            return False
        try:
            int(pmid)
            return True
        except ValueError:
            return False

    def _is_online(self, host="www.ncbi.nlm.nih.gov", port=443, timeout=3) -> bool:
        """Check for internet connectivity."""
        try:
            socket.create_connection((host, port), timeout=timeout)
            return True
        except OSError:
            return False

    @with_retry(max_retries=3, circuit_name="pubmed")
    def search_papers(self, query: str, max_results: Optional[int] = None) -> List[Dict]:
        """
        Search PubMed for papers matching the query.
        Handles Rate Limiting and Retries.
        """
        limit = max_results or self.config.max_results
        
        # 1. Check Offline Mode
        if not self._is_online():
            logger.warning("OFFLINE MODE DETECTED: Returning empty results for query: %s", query)
            return [{"title": "Network Error: Running in strict offline mode", "pmid": "000000"}]

        if not Entrez:
            logger.error("Biopython missing. Please run: pip install biopython")
            return []

        # 2. Search for IDs
        logger.info("Searching PubMed for: %s", query)
        rate_limiter.wait()
        handle = Entrez.esearch(db="pubmed", term=query, retmax=limit)
        record = Entrez.read(handle)
        handle.close()
        
        id_list = record.get("IdList", [])
        if not id_list:
            logger.info("No results found.")
            return []

        # 3. Fetch Details
        logger.info("Fetching details for %d papers...", len(id_list))
        rate_limiter.wait()
        
        handle = Entrez.efetch(db="pubmed", id=",".join(id_list), retmode="xml")
        papers = Entrez.read(handle)
        handle.close()
        
        # 4. Parse Results
        results = []
        for article in papers.get('PubmedArticle', []):
            medline = article.get('MedlineCitation', {})
            article_data = medline.get('Article', {})
            
            # Extract abstract safely
            abstract_list = article_data.get('Abstract', {}).get('AbstractText', [])
            abstract = " ".join(abstract_list) if abstract_list else "No abstract available."
            
            # Extract robust metadata
            paper = {
                "title": article_data.get('ArticleTitle', 'No title'),
                "abstract": abstract,
                "pmid": str(medline.get('PMID', '')),
                "publication_date": article_data.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {}).get('Year', 'Unknown'),
                "journal": article_data.get('Journal', {}).get('Title', 'Unknown'),
                "source": "PubMed",
                "authors": [a.get('LastName', '') + ' ' + a.get('Initials', '') 
                          for a in article_data.get('AuthorList', [])],
                "doi": next((id.title() for id in article.get('PubmedData', {}).get('ArticleIdList', []) 
                           if id.attributes.get('IdType') == 'doi'), None)
            }
            results.append(paper)
        
        return results

    def batch_search(self, queries: List[str]) -> Dict[str, List[Dict]]:
        """
        Perform searches for multiple queries with polite delays.
        """
        batch_results = {}
        for q in queries:
            batch_results[q] = self.search_papers(q)
            # Extra buffer between batches
            time.sleep(2) 
        return batch_results

@dataclass
class Paper:
    """
    Standardized Internal Data Model (PhD-Grade).
    """
    title: str
    abstract: str
    authors: List[str]
    year: str
    source: str
    doi: Optional[str] = None
    pmid: Optional[str] = None
    # OA / License Metadata
    is_open_access: bool = False
    open_access_source: Optional[str] = None # e.g. "Europe PMC", "Publisher"
    license: Optional[str] = None # e.g. "CC-BY"
    full_text_url: Optional[str] = None
    # Audit
    is_peer_reviewed: bool = True
    
    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}

@dataclass
class LiteratureConfig:
    """Configuration for the Literature Aggregator."""
    sources: List[str] = None # ["pubmed", "europe_pmc", "openalex"]
    include_preprints: bool = False
    email: str = os.getenv("PUBMED_EMAIL", "researcher@example.com")
    max_results: int = 15
    tool_name: str = "BioDockify"
    bohrium_url: Optional[str] = None

class LiteratureAggregator:
    """
    Aggregates results from multiple sources using the Three-Layer Harvesting Strategy.
    Layer 1: Discovery (Indexes)
    Layer 2: OA Detection (Filters)
    Layer 3: Retrieval (Links)
    """
    
    def __init__(self, config: Optional[LiteratureConfig] = None):
        self.config = config or LiteratureConfig()
        if self.config.sources is None:
             self.config.sources = ["pubmed", "europe_pmc", "openalex", "bohrium"]
        
        # Initialize Scrapers
        self.pubmed = PubmedScraper(PubmedScraperConfig(email=self.config.email, max_results=self.config.max_results))
        self.europe_pmc = EuropePMCScraper(email=self.config.email)
        self.openalex = OpenAlexScraper(email=self.config.email)
        self.crossref = CrossRefScraper(email=self.config.email)
        self.biorxiv = BioRxivScraper()
        self.bohrium = BohriumConnector(endpoint=self.config.bohrium_url)
        
    def search(self, query: str) -> List[Dict]:
        """
        Execute Three-Layer Strategy.
        """
        # --- LAYER 1: DISCOVERY ---
        # Find all relevant papers from authoritative indexes.
        raw_results = self._layer_1_discovery(query)
        
        # --- LAYER 2: OA DETECTION ---
        # Identify legal download paths and license status.
        processed_papers = self._layer_2_oa_detection(raw_results)
        
        # --- LAYER 3: FULL TEXT PREP ---
        # (For V1, we resolve URLs. Actual file downloading happens in Executor phase)
        # We ensure metadata is scientifically auditible.
        
        results = [p.to_dict() for p in processed_papers]
        
        # --- SURFSENSE INTEGRATION ---
        if results:
            try:
                from modules.knowledge.client import surfsense
                import asyncio
                import json
                
                # Format as structured Markdown for better RAG retrieval
                md_lines = [f"# Literature Review: {query}", f"Date: {time.strftime('%Y-%m-%d')}", ""]
                for p in results:
                    md_lines.append(f"## {p.get('title')}")
                    md_lines.append(f"**Source:** {p.get('source')} | **Year:** {p.get('year')}")
                    md_lines.append(f"**Authors:** {', '.join(p.get('authors', [])[:3])}")
                    md_lines.append(f"**Abstract:** {p.get('abstract')}")
                    md_lines.append(f"**Link:** {p.get('full_text_url') or p.get('doi')}")
                    md_lines.append(f"---")
                
                content = "\n".join(md_lines).encode('utf-8')
                filename = f"lit_review_{int(time.time())}.md"
                
                # Async Handling (similar to web_scraper)
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if loop.is_running():
                     asyncio.create_task(surfsense.upload_file(content, filename))
                else:
                     loop.run_until_complete(surfsense.upload_file(content, filename))

                logger.info(f"Uploaded literature review to SurfSense: {filename}")
            except Exception as e:
                logger.error(f"Failed to upload literature review to SurfSense: {e}")

        logger.info(f"Harvest Complete. Found {len(processed_papers)} papers ({sum(1 for p in processed_papers if p.is_open_access)} Open Access).")
        return results

    def _layer_1_discovery(self, query: str) -> List[Dict]:
        """Query indexes to find everything that exists."""
        results = []
        seen_titles = set()
        
        # Priority 1: Evidence (PubMed / Europe PMC)
        if "europe_pmc" in self.config.sources: 
             # Preference for EuroPMC because it has better OA flags built-in
             res = self.europe_pmc.search_papers(query, max_results=self.config.max_results)
             self._deduplicate_and_add(results, res, seen_titles)
             
        if "pubmed" in self.config.sources:
             res = self.pubmed.search_papers(query, max_results=self.config.max_results)
             self._deduplicate_and_add(results, res, seen_titles)

        # Priority 2: Discovery (OpenAlex / CrossRef)
        if "openalex" in self.config.sources:
            limit = 5 if len(results) > 10 else self.config.max_results
            res = self.openalex.search_papers(query, max_results=limit)
            self._deduplicate_and_add(results, res, seen_titles)
            
        if "crossref" in self.config.sources:
             res = self.crossref.search_papers(query, max_results=5)
             self._deduplicate_and_add(results, res, seen_titles)
             
        # Priority 3: Preprints
        if self.config.include_preprints:
            res = self.biorxiv.search_papers(query, max_results=5)
            self._deduplicate_and_add(results, res, seen_titles)
            
        # Priority 4: Agentic Search (Bohrium)
        if "bohrium" in self.config.sources:
             try:
                 # Bohrium returns list of dicts naturally
                 res = asyncio.run(self.bohrium.search_literature(query, limit=5))
                 # Normalize keys if needed
                 normalized_res = []
                 for item in res:
                     normalized_res.append({
                         "title": item.get('title', 'Untitled'),
                         "abstract": item.get('abstract', '') or item.get('content', '')[:500],
                         "authors": item.get('authors', []),
                         "year": item.get('year', '2024'),
                         "source": "Bohrium Agent",
                         "url": item.get('url', ''),
                         "doi": item.get('doi')
                     })
                 self._deduplicate_and_add(results, normalized_res, seen_titles)
             except Exception as e:
                 logger.warning(f"Bohrium search failed: {e}")
            
        return results

    def _layer_2_oa_detection(self, raw_items: List[Dict]) -> List[Paper]:
        """Enforce OA rules and normalize data."""
        papers = []
        for item in raw_items:
            # 1. Normalize into strict Paper model
            paper = Paper(
                title=item.get("title", "Unknown"),
                abstract=item.get("abstract", ""),
                authors=item.get("authors", []) if isinstance(item.get("authors"), list) else [],
                year=str(item.get("publication_date", "")),
                source=item.get("source", "Unknown"),
                doi=item.get("doi"),
                pmid=item.get("pmid"),
                is_peer_reviewed=item.get("is_peer_reviewed", True) # Default true unless tagged otherwise
            )
            
            # 2. Apply OA Logic
            # Rule A: Europe PMC Flag
            if item.get("is_open_access") is True:
                paper.is_open_access = True
                paper.open_access_source = "Europe PMC"
                paper.license = "OA (Unspecified)" # ideally we'd parse this deeper
                
                # Construct Full Text URL if possible (Europe PMC specific)
                if paper.pmid:
                    paper.full_text_url = f"https://www.europepmc.org/backend/ptpmcrender.fcgi?accid=PMID{paper.pmid}&blobtype=pdf"
                elif paper.doi:
                     # Fallback to DOI resolver which might paywall, so be careful. 
                     # For OA, usually EuroPMC links are safer.
                     pass
            # Rule B: Unpaywall Check - Query Unpaywall API for OA version
            if paper.doi and not paper.is_open_access:
                try:
                    unpaywall_result = self._check_unpaywall(paper.doi)
                    if unpaywall_result:
                        paper.is_open_access = True
                        paper.open_access_source = "Unpaywall"
                        paper.license = unpaywall_result.get("license", "OA")
                        paper.full_text_url = unpaywall_result.get("url")
                except Exception as e:
                    logger.debug(f"Unpaywall check failed for {paper.doi}: {e}")
            
            papers.append(paper)
        return papers
    
    def _check_unpaywall(self, doi: str) -> Optional[Dict[str, str]]:
        """
        Check Unpaywall API for open access version of a paper.
        
        Unpaywall is a free, legal API that finds open access versions of papers.
        Rate limit: Respectful use (no official limit, but be polite).
        
        Returns:
            Dict with 'url' and 'license' if OA version found, None otherwise
        """
        import requests
        
        # Use configured email for API
        email = self.config.email
        url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
        
        try:
            rate_limiter.wait()  # Be polite
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if open access
                if data.get("is_oa"):
                    best_oa = data.get("best_oa_location", {})
                    if best_oa:
                        return {
                            "url": best_oa.get("url_for_pdf") or best_oa.get("url"),
                            "license": best_oa.get("license") or "OA",
                            "source": best_oa.get("host_type", "Unknown")
                        }
            elif response.status_code == 404:
                # DOI not found in Unpaywall - this is normal
                pass
            else:
                logger.debug(f"Unpaywall returned {response.status_code} for {doi}")
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"Unpaywall request failed: {e}")
        
        return None

    def _deduplicate_and_add(self, master_list, new_items, seen_set):
        for item in new_items:
            # Normalize title for dedup
            norm_title = "".join(filter(str.isalnum, (item.get('title') or '').lower()))
            if norm_title and norm_title not in seen_set:
                seen_set.add(norm_title)
                master_list.append(item)

# Wrapper for legacy compatibility
def search_papers(query: str, max_results: int = 15, source_config: List[str] = None) -> List[Dict]:
    """Unified entry point."""
    config = LiteratureConfig(sources=source_config, max_results=max_results)
    aggregator = LiteratureAggregator(config)
    return aggregator.search(query)

if __name__ == "__main__":
    # Test block
    print("Testing Literature Aggregator...")
    papers = search_papers("Alzheimer kinase inhibitors", max_results=3, source_config=["openalex"])
    for p in papers:
        print(f"\nTitle: {p['title']}")
        print(f"Source: {p['source']}")
