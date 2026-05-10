import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.deep_drive.cipher_client import CipherClient

async def main():
    print("Testing Cipher Integration...")
    
    # Use localhost:3002 for host-side testing
    client = CipherClient(base_url="http://localhost:3002")
    
    print("[1] Initializing Client...")
    await client.initialize()
    
    if not client._server_id:
        print("[-] Failed to initialize client. Is Cipher API running on port 3002?")
        return

    print(f"[+] Client Initialized. Server ID: {client._server_id}")
    
    # Test Store Memory
    print("\n[2] Testing Store Memory...")
    inter = "The user is researching Glioblastoma treatments using inhibitord of EGFR."
    success = await client.store_memory(inter, context={"source": "test_script"})
    
    if success:
        print("[+] Memory stored successfully.")
    else:
        print("[-] Failed to store memory.")
        
    # Test Search Memory
    print("\n[3] Testing Search Memory...")
    # Give it a moment for indexing (though in-memory might be instant)
    await asyncio.sleep(1)
    
    results = await client.search_memory("EGFR inhibitors glioblastoma", top_k=2)
    print(f"[+] Found {len(results)} memories.")
    for r in results:
        print(f"    - {r.get('text', '')[:50]}... (Score: {r.get('similarity', 0):.2f})")
        
    # Test Graph Search
    print("\n[4] Testing Graph Search...")
    graph_results = await client.search_graph("Glioblastoma", limit=5)
    nodes = graph_results.get("nodes", [])
    print(f"[+] Found {len(nodes)} nodes in graph.")
    for n in nodes:
        print(f"    - {n.get('labels', ['Node'])[0]}: {n.get('properties', {}).get('name', 'Unknown')}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
