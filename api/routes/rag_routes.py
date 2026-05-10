from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Dict, Any, Optional
import hashlib
import logging
from modules.rag.ingestor import ingestor
from modules.rag.vector_store import get_vector_store
from modules.library.store import library_store

router = APIRouter(prefix="/api/rag", tags=["RAG"])
logger = logging.getLogger("biodockify_rag")

@router.post("/upload")
async def upload_source(file: UploadFile = File(...)):
    """Upload file to RAG for notebook access."""
    try:
        content = await file.read()
        
        # Save to library
        record = library_store.add_file(content, file.filename)
        
        # Ingest into vector store
        file_path = library_store.get_file_path(record['id'])
        chunks = ingestor.ingest_file(str(file_path))
        if chunks:
            await get_vector_store().add_documents(chunks)
            return {"status": "success", "document_id": record['id'], "chunks": len(chunks)}
        else:
            return {"status": "warning", "message": "File indexed but no text chunks extracted", "document_id": record['id']}
            
    except Exception as e:
        logger.error(f"RAG upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def list_documents():
    """List all documents in RAG library."""
    try:
        docs = library_store.list_files()
        return {"documents": docs}
    except Exception as e:
        logger.error(f"Failed to list RAG documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete document and its vector embeddings."""
    try:
        # 1. Delete from vector store
        store = get_vector_store()
        store.delete(document_id)
        
        # 2. Delete from library
        library_store.delete_file(document_id)
        
        return {"status": "success", "message": f"Document {document_id} deleted"}
    except Exception as e:
        logger.error(f"Failed to delete RAG document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def rag_chat(request: Dict[str, Any]):
    """Chat with RAG knowledge base."""
    query = request.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
        
    try:
        store = get_vector_store()
        results = await store.search(query, k=5)
        
        context_parts = []
        sources = []
        
        for res in results:
            context_parts.append(res.get("text", ""))
            meta = res.get("metadata", {})
            sources.append(meta.get("filename") or meta.get("url") or "Unknown Source")
            
        context = "\n\n---\n\n".join(context_parts)
        
        from runtime.config_loader import load_config
        from modules.llm.factory import LLMFactory
        
        cfg = load_config()
        ai_cfg = cfg.get("ai_provider", {})
        
        # Proper config object for factory
        from orchestration.planner.orchestrator import OrchestratorConfig
        config_obj = OrchestratorConfig(**ai_cfg)

        adapter = LLMFactory.get_adapter(config_obj.primary_model, config_obj)
        
        if adapter:
            prompt = f"""You are a research assistant. Answer the user question based ONLY on the provided context.
            If context is insufficient, explain what's missing.
            
            CONTEXT:
            {context}
            
            QUESTION: {query}
            
            ANSWER:"""
            answer = await asyncio.to_thread(adapter.generate, prompt)
        else:
            answer = "AI provider not configured for RAG chat. Please check your settings."

        return {
            "answer": answer,
            "context": context,
            "sources": list(set(sources))
        }
    except Exception as e:
        logger.error(f"RAG chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/link")
async def add_link(request: Dict[str, Any]):
    """Ingest URL content into RAG."""
    url = request.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
        
    try:
        from modules.headless_research.engine import deep_research
        import tempfile
        
        result = await deep_research(url)
        if result.get("status") == "success":
            content = result["content"].encode("utf-8")
            title = result.get("title", "Web Link")
            filename = f"link_{hashlib.sha256(url.encode()).hexdigest()[:16]}.md"
            
            # Save and ingest
            record = library_store.add_file(content, filename, meta={"url": url, "title": title})
            
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.md') as tmp:
                tmp.write(content)
                tmp.close()
                chunks = ingestor.ingest_file(tmp.name)
            
            if chunks:
                await get_vector_store().add_documents(chunks)
                return {"status": "success", "document_id": record['id'], "chunks": len(chunks)}
            return {"status": "warning", "message": "Link scraped but no text extracted"}
            
        return {"status": "failed", "error": result.get("error")}
    except Exception as e:
        logger.error(f"RAG link ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def rag_health():
    """Check if RAG system is healthy."""
    try:
        vs = get_vector_store()
        return {
            "status": "healthy",
            "index_size": vs.index.ntotal if vs.index else 0,
            "dimension": vs.dimension
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
