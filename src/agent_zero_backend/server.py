"""
BioDockify BioDockify AI - Core Backend
===================================
Minimal, lightweight BioDockify AI implementation with Surfsense KB.
Connects to Ollama on host machine (host.docker.internal:11434).
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("biodockify")

app = FastAPI(title="BioDockify BioDockify AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist FIRST
DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
KB_DIR = DATA_DIR / "knowledge_base"
KB_DIR.mkdir(parents=True, exist_ok=True)

# Settings file
SETTINGS_FILE = DATA_DIR / "settings.json"

# Ollama URL - try multiple options for Docker Desktop
OLLAMA_URL = os.getenv("OLLAMA_URL", "")
if not OLLAMA_URL:
    # Try host.docker.internal first for Docker Desktop
    OLLAMA_URL = "http://host.docker.internal:11434"
OLLAMA_BASE = OLLAMA_URL

class ChatRequest(BaseModel):
    message: str
    model: str = "llama3.2"
    system_prompt: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    model: str
    sources: List[str] = []

class Document(BaseModel):
    id: str
    content: str
    source: str
    title: str
    metadata: Dict[str, Any] = {}

class SearchRequest(BaseModel):
    query: str
    limit: int = 5

class SearchResult(BaseModel):
    id: str
    content: str
    source: str
    title: str
    score: float = 0.0

@app.get("/health")
async def health():
    return {"status": "ok", "ollama": OLLAMA_BASE}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with AI using Ollama or other providers"""
    try:
        import httpx
        
        ollama_url = f"{OLLAMA_BASE}/api/generate"
        
        payload = {
            "model": request.model,
            "prompt": request.message,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(ollama_url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return ChatResponse(
                    response=result.get("response", ""),
                    model=request.model,
                    sources=[]
                )
            else:
                raise HTTPException(status_code=500, detail=f"Ollama error: {response.text}")
                
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models():
    """List available Ollama models"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_BASE}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return {"models": data.get("models", [])}
            return {"models": [], "error": "Could not connect to Ollama"}
    except Exception as e:
        logger.error(f"Models error: {e}")
        return {"models": [], "error": str(e)}

@app.post("/kb/add", response_model=Document)
async def add_document(doc: Document):
    """Add document to knowledge base"""
    doc_path = KB_DIR / f"{doc.id}.json"
    
    doc_data = {
        "id": doc.id,
        "title": doc.title,
        "content": doc.content,
        "source": doc.source,
        "metadata": doc.metadata,
        "created_at": datetime.now().isoformat()
    }
    
    with open(doc_path, "w") as f:
        json.dump(doc_data, f, indent=2)
    
    logger.info(f"Added document: {doc.id}")
    return doc

@app.get("/kb/{doc_id}", response_model=Document)
async def get_document(doc_id: str):
    """Get document from knowledge base"""
    doc_path = KB_DIR / f"{doc_id}.json"
    
    if not doc_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    with open(doc_path) as f:
        doc_data = json.load(f)
    
    return Document(**doc_data)

@app.get("/kb")
async def list_documents():
    """List all documents in knowledge base"""
    docs = []
    for f in KB_DIR.glob("*.json"):
        with open(f) as fp:
            data = json.load(fp)
            docs.append({"id": data["id"], "title": data["title"], "source": data["source"]})
    return {"documents": docs}

@app.delete("/kb/{doc_id}")
async def delete_document(doc_id: str):
    """Delete document from knowledge base"""
    doc_path = KB_DIR / f"{doc_id}.json"
    
    if not doc_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_path.unlink()
    return {"status": "deleted", "id": doc_id}

@app.post("/kb/search", response_model=List[SearchResult])
async def search_kb(request: SearchRequest):
    """Search knowledge base - simple text match"""
    results = []
    query_lower = request.query.lower()
    
    for f in KB_DIR.glob("*.json"):
        with open(f) as fp:
            data = json.load(fp)
            content_lower = data.get("content", "").lower()
            
            if query_lower in content_lower or query_lower in data.get("title", "").lower():
                score = 1.0 if query_lower in data.get("title", "").lower() else 0.5
                results.append(SearchResult(
                    id=data["id"],
                    content=data.get("content", "")[:500],
                    source=data.get("source", ""),
                    title=data.get("title", ""),
                    score=score
                ))
    
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:request.limit]

@app.post("/research/search")
async def research_search(query: str, sources: List[str] = ["pubmed", "semantic_scholar"]):
    """Search academic literature"""
    results = []
    
    try:
        import httpx
        
        if "semantic_scholar" in sources:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        "https://api.semanticscholar.org/graph/v1/paper/search",
                        params={"query": query, "limit": 5, "fields": "title,abstract,authors,year,url"}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for paper in data.get("data", []):
                            results.append({
                                "source": "semantic_scholar",
                                "title": paper.get("title", ""),
                                "abstract": paper.get("abstract", ""),
                                "authors": [a.get("name", "") for a in paper.get("authors", [])[:3]],
                                "year": paper.get("year"),
                                "url": paper.get("url", "")
                            })
            except Exception as e:
                logger.warning(f"Semantic Scholar error: {e}")
        
        if "pubmed" in sources:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                        params={"db": "pubmed", "term": query, "retmax": 5, "retmode": "json"}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        id_list = data.get("esearchresult", {}).get("idlist", [])
                        if id_list:
                            fetch_resp = await client.get(
                                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                                params={"db": "pubmed", "id": ",".join(id_list), "retmode": "json"}
                            )
                            if fetch_resp.status_code == 200:
                                summary = fetch_resp.json()
                                for uid, info in summary.get("result", {}).items():
                                    if uid != "uids":
                                        results.append({
                                            "source": "pubmed",
                                            "title": info.get("title", ""),
                                            "pubdate": info.get("pubdate", ""),
                                            "authors": [a.get("name", "") for a in info.get("authors", [])[:3]],
                                            "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
                                        })
            except Exception as e:
                logger.warning(f"PubMed error: {e}")
                
    except Exception as e:
        logger.error(f"Research search error: {e}")
    
    return {"results": results[:10]}

@app.post("/pharma/search")
async def pharma_search(query: str, sources: List[str] = ["chembl", "uniprot", "pubchem"]):
    """Search pharma/biotech databases"""
    from src.pharma.clients import search_pharma_databases
    
    try:
        results = await search_pharma_databases(query, sources)
        return {"results": results}
    except Exception as e:
        logger.error(f"Pharma search error: {e}")
        return {"results": {}, "error": str(e)}

@app.get("/writing/template/{template_type}")
async def get_template(template_type: str):
    """Get writing templates"""
    from src.writing.academic import AcademicWriter
    
    writer = AcademicWriter()
    
    if template_type == "thesis":
        return {"template": writer.get_thesis_template()}
    elif template_type == "review":
        return {"template": writer.get_review_template()}
    elif template_type == "outline":
        return {"template": writer.generate_outline("")}
    
    return {"error": "Unknown template type"}

@app.get("/constitution")
async def get_constitution():
    """Get BioDockify AI constitution"""
    from pathlib import Path
    constitution_path = Path(__file__).parent / "CONSTITUTION.md"
    
    if constitution_path.exists():
        return {"constitution": constitution_path.read_text()}
    
    return {"constitution": "BioDockify BioDockify AI - Your Research Assistant"}

# ============ ESSENTIAL API ENDPOINTS FOR FRONTEND ============

def load_settings() -> Dict[str, Any]:
    """Load settings with safe defaults"""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    return data
    except Exception as e:
        logger.error(f"Settings load error: {e}")
    return {
        "persona": "phd_student",
        "default_provider": "ollama",
        "default_model": "llama3.2"
    }

def save_settings(settings: Dict[str, Any]):
    """Save settings"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Settings save error: {e}")

# Settings endpoint
@app.get("/settings")
async def get_settings():
    """Get current settings"""
    return load_settings()

@app.post("/settings")
async def update_settings(data: Dict[str, Any]):
    """Update settings"""
    current = load_settings()
    current.update(data)
    save_settings(current)
    return {"status": "updated"}

# Models endpoint
@app.get("/models")
async def get_models():
    """Get available models"""
    models = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_BASE}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name") for m in data.get("models", [])]
    except Exception as e:
        logger.error(f"Models error: {e}")
    
    return {"ollama": models}

# Frontend compatibility endpoints
@app.get("/api/settings")
async def get_api_settings():
    return load_settings()

@app.get("/api/enhanced/system/status")
async def get_system_status():
    ollama_status = {"running": False}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE}/api/tags")
            ollama_status = {"running": response.status_code == 200}
    except:
        pass
    return {
        "status": "online" if ollama_status.get("running") else "degraded",
        "ollama": ollama_status
    }

@app.get("/api/enhanced/projects")
async def get_projects():
    return {"projects": []}

@app.get("/api/health")
async def api_health():
    return {"status": "ok"}

# Ollama proxy endpoints
@app.api_route("/api/tags", methods=["GET", "POST"])
async def ollama_tags():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{OLLAMA_BASE}/api/tags", timeout=30.0)
        return resp.json()

@app.api_route("/v1/models", methods=["GET", "POST"])
async def ollama_models():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{OLLAMA_BASE}/api/tags", timeout=30.0)
        data = resp.json()
        return {
            "object": "list",
            "data": [{"id": m["name"], "object": "model"} for m in data.get("models", [])]
        }

# Main entry
if __name__ == "__main__":
    print(f"BioDockify v3.3.5_clean - Ollama: {OLLAMA_BASE}")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    uvicorn.run(app, host="0.0.0.0", port=port)