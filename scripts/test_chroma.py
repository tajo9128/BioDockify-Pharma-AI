import asyncio
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.vector.chroma_integration import ChromaVectorStore

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Testing ChromaDB Local Integration...")
    
    # Initialize store (uses local path by default)
    persist_dir = "./data/test_chroma"
    store = ChromaVectorStore(persist_dir=persist_dir)
    
    # Test Data
    docs = [
        {
            "id": "doc1",
            "text": "The efficacy of EGFR inhibitors in glioblastoma remains a topic of intense clinical research.",
            "metadata": {"type": "research", "topic": "oncology"},
            "source": "Nature Medicine 2024"
        },
        {
            "id": "doc2",
            "text": "Cardiovascular side effects were noted in Phase II trials of the novel compound BK-101.",
            "metadata": {"type": "trial", "topic": "cardiology"},
            "source": "Internal Report"
        }
    ]
    
    # 1. Add Documents
    print("\n[1] Adding documents...")
    res = await store.add_documents("research_documents", docs)
    print(f"Result: {res}")
    
    # 2. Search
    print("\n[2] Testing Similarity Search (oncology query)...")
    results = await store.search("research_documents", "EGFR inhibitors glioblastoma", limit=2)
    print(f"Found {len(results)} matches:")
    for r in results:
        print(f" - [{r['score']:.4f}] {r['text'][:60]}... (Source: {r['metadata'].get('source', 'Unknown')})")

    # 3. Search (non-matching)
    print("\n[3] Testing Similarity Search (cardiology query)...")
    results = await store.search("research_documents", "heart side effects", limit=2)
    print(f"Found {len(results)} matches:")
    for r in results:
        print(f" - [{r['score']:.4f}] {r['text'][:60]}... (Source: {r['metadata'].get('source', 'Unknown')})")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
