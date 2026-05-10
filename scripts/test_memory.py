import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.deep_drive.memory_engine import MemoryEngine

async def main():
    # Configure logging to see internal engine messages
    import logging
    logging.basicConfig(level=logging.INFO)

    print("Testing Native Memory Engine (Deep Drive) - Local Graph Mode...")
    
    # Initialize Engine
    # Ensure Memgraph is running on localhost:7687 OR fallback to local graph
    engine = MemoryEngine()
    
    # Clean up previous local graph for fresh test
    if engine.local_graph_path and os.path.exists(engine.local_graph_path):
        try:
             # Reset internal graph
             import networkx as nx
             engine.local_graph = nx.DiGraph() 
             print("[*] cleared previous local graph state.")
        except: pass

    print("[1] Initialized Memory Engine.")
    
    # Test Store Memory
    print("\n[2] Testing Store Memory...")
    inter = "The user is researching Glioblastoma treatments using inhibitord of EGFR."
    success = await engine.store_memory(inter, context={"source": "test_script", "entities": {"drugs": ["EGFR inhibitors"], "diseases": ["Glioblastoma"]}})
    
    if success:
        print("[+] Memory stored successfully.")
    else:
        print("[-] Failed to store memory (might be insignificant or error).")
        
    # Test Search Memory (Vector)
    print("\n[3] Testing Vector Search...")
    # Give it a moment? In-memory/local vector store should be instant usually.
    results = await engine.search_memory("EGFR inhibitors glioblastoma", top_k=2)
    print(f"[+] Found {len(results)} vector matches.")
    for r in results:
        print(f"    - {r.get('text', '')[:50]}... (Score: {r.get('score', 0):.2f})")
        
    # Test Graph Search
    print("\n[4] Testing Graph Search...")
    # Matches 'Glioblastoma' entity stored above
    graph_results = await engine.search_graph("Glioblastoma", limit=5)
    nodes = graph_results.get("nodes", [])
    print(f"[+] Found {len(nodes)} nodes in graph.")
    for n in nodes:
        labels = n.get('labels', ['Node'])
        label = labels[0] if labels else 'Node'
        name = n.get('properties', {}).get('name', 'Unknown')
        print(f"    - {label}: {name}")

    engine.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
