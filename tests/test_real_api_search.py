"""
Test Real API Calls - PubMed, ArXiv, Semantic Scholar

This test demonstrates the AgentPool executing actual API calls
to research databases, showcasing real-world parallel search capability.

Usage:
    python tests/test_real_api_search.py

Notes:
    - Requires internet connection
    - Uses public APIs (no authentication required for basic queries)
    - Rate limiting may apply
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestration.planner.agent_pool import AgentPool

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Real API Search Functions
# =============================================================================

async def search_pubmed_real(task: dict) -> dict:
    """
    Search PubMed using the E-utilities API (free, no auth required).
    """
    import aiohttp
    
    query = task.get("params", {}).get("query", task.get("title", ""))
    limit = task.get("params", {}).get("limit", 5)
    
    # PubMed E-utilities search endpoint
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Step 1: Search for PMIDs
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": limit,
                "retmode": "json",
                "sort": "relevance"
            }
            
            async with session.get(search_url, params=search_params) as resp:
                if resp.status != 200:
                    return {"source": "PubMed", "error": f"HTTP {resp.status}", "results": []}
                
                data = await resp.json()
                pmids = data.get("esearchresult", {}).get("idlist", [])
            
            if not pmids:
                return {"source": "PubMed", "query": query, "results": []}
            
            # Step 2: Get summaries
            summary_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "json"
            }
            
            async with session.get(summary_url, params=summary_params) as resp:
                if resp.status != 200:
                    return {"source": "PubMed", "error": f"HTTP {resp.status}", "results": []}
                
                summary_data = await resp.json()
                results_dict = summary_data.get("result", {})
            
            papers = []
            for pmid in pmids:
                paper_data = results_dict.get(pmid, {})
                if paper_data:
                    papers.append({
                        "pmid": pmid,
                        "title": paper_data.get("title", "No title"),
                        "authors": paper_data.get("authors", [])[:3],
                        "journal": paper_data.get("source", ""),
                        "year": paper_data.get("pubdate", "")[:4],
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    })
            
            return {
                "source": "PubMed",
                "query": query,
                "results": papers
            }
            
    except Exception as e:
        logger.error(f"PubMed search error: {e}")
        return {"source": "PubMed", "error": str(e), "results": []}


async def search_arxiv_real(task: dict) -> dict:
    """
    Search ArXiv using its public API (no auth required).
    """
    import aiohttp
    import xml.etree.ElementTree as ET
    
    query = task.get("params", {}).get("query", task.get("title", ""))
    limit = task.get("params", {}).get("limit", 5)
    
    # ArXiv API endpoint
    url = "http://export.arxiv.org/api/query"
    
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": limit,
                "sortBy": "relevance",
                "sortOrder": "descending"
            }
            
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return {"source": "ArXiv", "error": f"HTTP {resp.status}", "results": []}
                
                xml_text = await resp.text()
                
            # Parse XML response
            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            
            papers = []
            for entry in root.findall("atom:entry", ns):
                arxiv_id = entry.find("atom:id", ns).text.split("/abs/")[-1]
                title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                summary = entry.find("atom:summary", ns).text.strip()[:200]
                published = entry.find("atom:published", ns).text[:4]
                
                authors = []
                for author in entry.findall("atom:author", ns)[:3]:
                    name = author.find("atom:name", ns)
                    if name is not None:
                        authors.append(name.text)
                
                papers.append({
                    "arxiv_id": arxiv_id,
                    "title": title,
                    "summary": summary,
                    "authors": authors,
                    "year": published,
                    "url": f"https://arxiv.org/abs/{arxiv_id}"
                })
            
            return {
                "source": "ArXiv",
                "query": query,
                "results": papers
            }
            
    except Exception as e:
        logger.error(f"ArXiv search error: {e}")
        return {"source": "ArXiv", "error": str(e), "results": []}


async def search_semantic_scholar_real(task: dict) -> dict:
    """
    Search Semantic Scholar using its public API.
    
    For higher rate limits, set the S2_API_KEY environment variable.
    Get a key at: https://www.semanticscholar.org/product/api
    """
    import aiohttp
    import os
    
    query = task.get("params", {}).get("query", task.get("title", ""))
    limit = task.get("params", {}).get("limit", 5)
    
    # Semantic Scholar API endpoint
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    # Check for API key (provides higher rate limits)
    api_key = os.environ.get("S2_API_KEY") or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    
    try:
        headers = {}
        if api_key:
            headers["x-api-key"] = api_key
            logger.info("Using Semantic Scholar API key for higher rate limits")
        
        async with aiohttp.ClientSession() as session:
            params = {
                "query": query,
                "limit": limit,
                "fields": "paperId,title,authors,year,citationCount,venue,url"
            }
            
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 429:
                    # Rate limited - provide helpful message
                    return {
                        "source": "Semantic Scholar",
                        "error": "Rate limited. Set S2_API_KEY env var for higher limits. Get key at: https://www.semanticscholar.org/product/api",
                        "results": []
                    }
                    
                if resp.status != 200:
                    error_text = await resp.text()
                    return {"source": "Semantic Scholar", "error": f"HTTP {resp.status}: {error_text[:100]}", "results": []}
                
                data = await resp.json()
                
            papers = []
            for paper in data.get("data", []):
                authors = [a.get("name", "") for a in paper.get("authors", [])[:3]]
                papers.append({
                    "paper_id": paper.get("paperId", ""),
                    "title": paper.get("title", "No title"),
                    "authors": authors,
                    "year": paper.get("year"),
                    "citations": paper.get("citationCount", 0),
                    "venue": paper.get("venue", ""),
                    "url": paper.get("url", "")
                })
            
            return {
                "source": "Semantic Scholar",
                "query": query,
                "results": papers
            }
            
    except Exception as e:
        logger.error(f"Semantic Scholar search error: {e}")
        return {"source": "Semantic Scholar", "error": str(e), "results": []}


# =============================================================================
# Unified Executor
# =============================================================================

async def execute_real_search(task: dict) -> dict:
    """Route to the correct API based on task source."""
    source = task.get("source", "pubmed").lower()
    
    if source == "pubmed":
        return await search_pubmed_real(task)
    elif source == "arxiv":
        return await search_arxiv_real(task)
    elif source == "semantic_scholar":
        return await search_semantic_scholar_real(task)
    else:
        raise ValueError(f"Unknown source: {source}")


# =============================================================================
# Main Test
# =============================================================================

async def main():
    query = "CRISPR cancer therapy"
    
    print("=" * 70)
    print("Real API Parallel Literature Search Test")
    print("=" * 70)
    print(f"\nQuery: {query}")
    print("APIs: PubMed (NCBI), ArXiv, Semantic Scholar")
    print("\n" + "-" * 70)
    
    # Create AgentPool
    pool = AgentPool(max_concurrent=3)
    
    # Define search tasks
    tasks = [
        {"title": "PubMed Search", "source": "pubmed", "params": {"query": query, "limit": 3}},
        {"title": "ArXiv Search", "source": "arxiv", "params": {"query": query, "limit": 3}},
        {"title": "Semantic Scholar Search", "source": "semantic_scholar", "params": {"query": query, "limit": 3}},
    ]
    
    print(f"\n[*] Starting parallel search across {len(tasks)} databases...")
    
    import time
    start = time.time()
    
    # Execute in parallel
    results = await pool.execute_parallel(tasks, execute_real_search)
    
    duration = time.time() - start
    
    print(f"\n[*] Search completed in {duration:.2f}s\n")
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    total_papers = 0
    for result in results:
        print(f"\n--- {result.task_name} ---")
        if result.success:
            data = result.data
            if "error" in data:
                print(f"  [WARN] Error: {data['error']}")
            else:
                papers = data.get("results", [])
                total_papers += len(papers)
                print(f"  Found {len(papers)} papers")
                for i, paper in enumerate(papers, 1):
                    title = paper.get("title", "Unknown")[:60]
                    year = paper.get("year", "N/A")
                    print(f"    {i}. [{year}] {title}...")
        else:
            print(f"  [FAIL] {result.error}")
    
    print("\n" + "=" * 70)
    print(f"SUMMARY: Found {total_papers} papers in {duration:.2f}s")
    print("=" * 70)
    
    # Pool status
    status = pool.get_pool_status()
    print(f"\nPool Stats:")
    print(f"  - Agents spawned: {status['total_agents_spawned']}")
    print(f"  - Completed: {status['agents_by_status']['completed']}")
    print(f"  - Failed: {status['agents_by_status']['failed']}")
    
    return total_papers > 0


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        print(f"\n[{'OK' if result else 'WARN'}] Test {'passed' if result else 'completed with warnings'}")
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n[FAIL] Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
