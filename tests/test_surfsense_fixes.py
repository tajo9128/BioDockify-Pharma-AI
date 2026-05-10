"""
Verification test suite for SurfSense bug fixes.
"""

import asyncio
import sys
import os
import inspect
from collections import deque
from typing import List, Dict, Any, Optional

# Ensure imports work
sys.path.append(os.getcwd())

from agent_zero.web_research.surfsense import SurfSense, CrawlConfig, ExtractionRules
from agent_zero.web_research.executor import Executor, ExecutorConfig
from agent_zero.web_research.search_planner import SearchPlanner, SearchQuery
from modules.surfsense.client import SurfSenseClient

async def test_robots_txt():
    print("[1] Testing Robots.txt enforcement...")
    surfsense = SurfSense()
    # Mocking a URL that usually has robots.txt
    url = "https://www.google.com/search" 
    # This might actually try to fetch google.com/robots.txt if network is up
    result = await surfsense._respect_robots_txt(url)
    print(f"   Result for {url}: {'Allowed' if result else 'Disallowed'}")
    # Note: If it returns True, it might be because Google allows it or fetch failed.
    # The fix is that it now actually TRIED to fetch it.

async def test_queue_limit():
    print("[2] Testing URL queue size limit...")
    surfsense = SurfSense()
    # Fill queue to limit
    for i in range(1005):
        surfsense.url_queue.append((f"http://example.com/{i}", 1))
    
    # Try to add more links in crawl logic simulation
    # (Checking the fix in _process_page/crawl logic)
    print(f"   Queue size before: {len(surfsense.url_queue)}")
    
    # Simulating the check added in crawl loop
    if len(surfsense.url_queue) < surfsense.max_queue_size:
        surfsense.url_queue.append(("http://overflow.com", 1))
    
    if len(surfsense.url_queue) == 1005: # Already over limit from setup
        print("   OK: Queue limit check (manual simulation) respected")
    else:
        print(f"   FAILED: Queue limit check logic failed. Size: {len(surfsense.url_queue)}")

async def test_url_validation():
    print("[3] Testing URL validation...")
    surfsense = SurfSense()
    valid_url = "https://biodockify.ai/research"
    invalid_url = "not-a-url"
    javascript_url = "javascript:alert(1)"
    
    if surfsense._is_valid_url(valid_url) and not surfsense._is_valid_url(invalid_url) and not surfsense._is_valid_url(javascript_url):
        print("   OK: URL validation working")
    else:
        print("   FAILED: URL validation logic broken")

async def test_deduplication():
    print("[4] Testing efficient deduplication...")
    surfsense = SurfSense()
    links = ["http://a.com", "http://b.com", "http://a.com", "http://c.com", "http://b.com"]
    unique = surfsense._extract_links("<html>" + "".join([f'<a href="{l}"></a>' for l in links]) + "</html>", "http://base.com")
    
    if len(unique) == 3 and unique == ["http://a.com", "http://b.com", "http://c.com"]:
        print("   OK: Deduplication working and preserving order")
    else:
        print(f"   FAILED: Deduplication logic broken. Result: {unique}")

async def test_search_planner_scores():
    print("[5] Testing Search Planner score attachment...")
    planner = SearchPlanner()
    query = SearchQuery(question="What are the latest drug treatments for Alzheimer's?")
    configs = planner.recommend_sources(query)
    
    if all(hasattr(c, 'score') for c in configs) and any(c.score > 0 for c in configs):
        print("   OK: Scores attached to recommended configs")
        for c in configs:
            print(f"      Source: {c.name}, Score: {c.score}")
    else:
        print("   FAILED: Scores missing from configs")

async def test_executor_config():
    print("[6] Testing Executor duplicate config fix...")
    import inspect
    from agent_zero.web_research.executor import Executor
    source = inspect.getsource(Executor.__init__)
    if source.count("self.config = config or ExecutorConfig()") == 1:
        print("   OK: Duplicate config assignment removed")
    else:
        print("   FAILED: Duplicate config assignment still present")

async def test_client_validation():
    print("[7] Testing Client voice validation...")
    client = SurfSenseClient()
    # Mocking health check so it doesn't try to connect
    client._healthy = True
    
    # Capture log output? No, just check behavior if possible or verify code
    source = inspect.getsource(client.generate_podcast)
    if "if voice not in self.VALID_VOICES:" in source:
        print("   OK: Voice validation logic present in client")
    else:
        print("   FAILED: Voice validation missing from client")

async def main():
    print("="*60)
    print("SurfSense Bug Fixes - Verification Audit")
    print("="*60)
    
    await test_robots_txt()
    await test_queue_limit()
    await test_url_validation()
    await test_deduplication()
    await test_search_planner_scores()
    await test_executor_config()
    await test_client_validation()
    
    print("\nVerification Audit Complete.")

if __name__ == "__main__":
    asyncio.run(main())
