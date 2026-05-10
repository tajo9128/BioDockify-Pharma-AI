import asyncio
import json
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from api.routes.rag_routes import list_documents, delete_document
from modules.library.store import library_store

async def verify_rag():
    print("--- Verifying RAG Hardening ---")
    
    # 1. Test List Documents
    print("Testing List Documents...")
    try:
        res = await list_documents()
        print(f"Docs found: {len(res.get('documents', []))}")
        print("PASS: List documents endpoint functional.")
    except Exception as e:
        print(f"FAIL: List documents failed: {e}")

    # 2. Test Deletion (Mock or Non-existent)
    print("Testing Delete Document (Non-existent)...")
    try:
        # This will test the logic flow even if it fails to find the doc
        res = await delete_document("test-non-existent")
        print(f"Delete result: {res}")
    except Exception as e:
        print(f"Expected failure or Handled error: {e}")

    print("\nRAG MANUAL VERIFICATION COMPLETE")

if __name__ == "__main__":
    asyncio.run(verify_rag())
