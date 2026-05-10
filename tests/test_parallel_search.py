"""
Test Parallel Literature Search with Agent Pool

This test demonstrates the AgentPool's ability to search
multiple databases concurrently, significantly speeding up
literature discovery.

Usage:
    python tests/test_parallel_search.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestration.planner.agent_pool import AgentPool, SubAgentResult


# Mock literature search functions for each database
async def search_pubmed(task: dict) -> dict:
    """Simulate PubMed search with delay."""
    query = task.get("params", {}).get("query", task.get("title", ""))
    
    await asyncio.sleep(1.5)  # Simulate network latency
    
    return {
        "source": "PubMed",
        "query": query,
        "results": [
            {"pmid": "12345678", "title": f"PubMed result 1 for {query[:30]}", "year": 2024},
            {"pmid": "12345679", "title": f"PubMed result 2 for {query[:30]}", "year": 2023},
            {"pmid": "12345680", "title": f"PubMed result 3 for {query[:30]}", "year": 2024},
        ]
    }


async def search_arxiv(task: dict) -> dict:
    """Simulate ArXiv search with delay."""
    query = task.get("params", {}).get("query", task.get("title", ""))
    
    await asyncio.sleep(2.0)  # ArXiv is a bit slower
    
    return {
        "source": "ArXiv",
        "query": query,
        "results": [
            {"arxiv_id": "2401.12345", "title": f"ArXiv preprint 1 for {query[:30]}", "year": 2024},
            {"arxiv_id": "2401.12346", "title": f"ArXiv preprint 2 for {query[:30]}", "year": 2024},
        ]
    }


async def search_semantic_scholar(task: dict) -> dict:
    """Simulate Semantic Scholar search with delay."""
    query = task.get("params", {}).get("query", task.get("title", ""))
    
    await asyncio.sleep(1.8)  # Moderate latency
    
    return {
        "source": "Semantic Scholar",
        "query": query,
        "results": [
            {"paper_id": "abc123", "title": f"S2 paper 1 for {query[:30]}", "citations": 150, "year": 2023},
            {"paper_id": "abc124", "title": f"S2 paper 2 for {query[:30]}", "citations": 89, "year": 2024},
            {"paper_id": "abc125", "title": f"S2 paper 3 for {query[:30]}", "citations": 203, "year": 2022},
            {"paper_id": "abc126", "title": f"S2 paper 4 for {query[:30]}", "citations": 45, "year": 2024},
        ]
    }


# Unified executor that routes to the right search
async def execute_literature_search(task: dict) -> dict:
    """Execute literature search based on task source."""
    source = task.get("source", "pubmed").lower()
    
    if source == "pubmed":
        return await search_pubmed(task)
    elif source == "arxiv":
        return await search_arxiv(task)
    elif source == "semantic_scholar":
        return await search_semantic_scholar(task)
    else:
        raise ValueError(f"Unknown source: {source}")


async def run_sequential_search(query: str) -> tuple:
    """Run searches sequentially (baseline for comparison)."""
    import time
    start = time.time()
    
    tasks = [
        {"source": "pubmed", "params": {"query": query}},
        {"source": "arxiv", "params": {"query": query}},
        {"source": "semantic_scholar", "params": {"query": query}},
    ]
    
    results = []
    for task in tasks:
        result = await execute_literature_search(task)
        results.append(result)
    
    duration = time.time() - start
    return results, duration


async def run_parallel_search(query: str) -> tuple:
    """Run searches in parallel using AgentPool."""
    import time
    start = time.time()
    
    pool = AgentPool(max_concurrent=3)
    
    tasks = [
        {"title": "PubMed Search", "source": "pubmed", "params": {"query": query}},
        {"title": "ArXiv Search", "source": "arxiv", "params": {"query": query}},
        {"title": "Semantic Scholar Search", "source": "semantic_scholar", "params": {"query": query}},
    ]
    
    # Check parallelizability
    can_parallel = pool.can_parallelize(tasks)
    print(f"[*] Can parallelize: {can_parallel}")
    
    # Execute in parallel
    results = await pool.execute_parallel(tasks, execute_literature_search)
    
    duration = time.time() - start
    
    # Aggregate
    aggregated = pool.aggregate_results(results)
    
    return results, aggregated, duration, pool.get_pool_status()


async def main():
    query = "CRISPR gene therapy cancer treatment mechanisms"
    
    print("=" * 60)
    print("Parallel Literature Search Test")
    print("=" * 60)
    print(f"\nQuery: {query}\n")
    
    # Sequential baseline
    print("[1] Running SEQUENTIAL search (baseline)...")
    seq_results, seq_time = await run_sequential_search(query)
    print(f"    Sequential time: {seq_time:.2f}s")
    print(f"    Total papers: {sum(len(r['results']) for r in seq_results)}")
    
    # Parallel with AgentPool
    print("\n[2] Running PARALLEL search with AgentPool...")
    par_results, aggregated, par_time, pool_status = await run_parallel_search(query)
    print(f"    Parallel time: {par_time:.2f}s")
    print(f"    Total papers: {len(aggregated['data'])}")
    
    # Results summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    speedup = seq_time / par_time if par_time > 0 else 0
    print(f"\n  Sequential: {seq_time:.2f}s")
    print(f"  Parallel:   {par_time:.2f}s")
    print(f"  Speedup:    {speedup:.2f}x faster")
    
    print(f"\n  Papers found per source:")
    for result in par_results:
        if result.success:
            source = result.data.get("source", "Unknown")
            count = len(result.data.get("results", []))
            print(f"    - {source}: {count} papers")
        else:
            print(f"    - {result.task_name}: FAILED - {result.error}")
    
    print(f"\n  Pool Status:")
    print(f"    - Agents spawned: {pool_status['total_agents_spawned']}")
    print(f"    - Completed: {pool_status['agents_by_status']['completed']}")
    
    # Verify aggregation
    print(f"\n  Aggregation:")
    print(f"    - Success: {aggregated['success']}")
    print(f"    - Total items aggregated: {len(aggregated['data'])}")
    
    print("\n" + "=" * 60)
    print("[OK] Test completed successfully!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"[FAIL] Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
