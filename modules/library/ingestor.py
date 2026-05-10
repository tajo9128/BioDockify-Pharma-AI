import os
import nbformat
import pypdf
import logging
from typing import List, Dict, Any
from pathlib import Path

from modules.rag.vector_store import get_vector_store

logger = logging.getLogger("biodockify_library")

class LibraryIngestor:
    """
    Enhanced ingestor for the Digital Library.
    Supports PDF, TXT, MD, IPYNB, and stubs for DOCX.
    Now with RAG Vector Store integration.
    """
    
    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Main entry point. Returns { text: str, meta: dict, chunks: list }.
        """
        if not file_path.exists():
             raise FileNotFoundError(f"File not found: {file_path}")
             
        ext = file_path.suffix.lower()
        content = ""
        chunks = []
        
        try:
            if ext == ".pdf":
                content, chunks = self._parse_pdf(file_path)
            elif ext == ".ipynb":
                content, chunks = self._parse_notebook(file_path)
            elif ext in [".md", ".txt"]:
                 content, chunks = self._parse_text(file_path)
            elif ext == ".docx":
                 content, chunks = self._parse_docx(file_path)
            else:
                # Fallback binary/unsupported
                return {"text": "", "meta": {"error": "Unsupported format"}, "chunks": []}
            
            # --- RAG INTEGRATION ---
            try:
                # 1. Refine chunks if mostly raw text (e.g. from txt/md)
                refined_chunks = self._refine_chunks(chunks)
                
                # 2. Extract text and metadata for VectorStore
                doc_texts = [c['text'] for c in refined_chunks if c['text'].strip()]
                doc_metas = []
                for c in refined_chunks:
                    if c['text'].strip():
                        meta = c.get('metadata', {}).copy()
                        meta['source'] = file_path.name
                        doc_metas.append(meta)

                # 3. Add to Vector Index
                if doc_texts:
                    vector_store = get_vector_store()
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(vector_store.add_documents(doc_texts, doc_metas))
                        else:
                            asyncio.run(vector_store.add_documents(doc_texts, doc_metas))
                    except Exception:
                        asyncio.run(vector_store.add_documents(doc_texts, doc_metas))
                    logger.info(f"Ingested {len(doc_texts)} chunks into VectorStore for {file_path.name}")
            except Exception as ve:
                logger.error(f"Vector Store ingestion failed for {file_path}: {ve}")
                # Don't fail the file load just because RAG failed
                
            return {
                "text": content,
                "chunks": chunks,
                "meta": {
                    "source": file_path.name,
                    "type": ext,
                    "processed": True
                }
            }
        except Exception as e:
            logger.error(f"Ingestion failed for {file_path}: {e}")
            raise e

    def _refine_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ensure chunks are of appropriate size for embedding (approx 500-1000 chars).
        Splits large chunks.
        """
        refined = []
        MAX_CHUNK_SIZE = 1000
        OVERLAP = 100
        
        for chunk in chunks:
            text = chunk.get('text', '')
            meta = chunk.get('metadata', {})
            
            if len(text) <= MAX_CHUNK_SIZE:
                refined.append(chunk)
            else:
                # Simple sliding window split
                start = 0
                while start < len(text):
                    end = start + MAX_CHUNK_SIZE
                    sub_text = text[start:end]
                    
                    sub_meta = meta.copy()
                    sub_meta['chunk_offset'] = start
                    
                    refined.append({
                        "text": sub_text,
                        "metadata": sub_meta
                    })
                    
                    start += (MAX_CHUNK_SIZE - OVERLAP)
        return refined

    def _parse_pdf(self, path: Path):
        text_content = []
        chunks = []
        reader = pypdf.PdfReader(str(path))
        
        if reader.is_encrypted:
             raise ValueError("Encrypted PDF")
             
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_content.append(page_text)
                chunks.append({
                    "text": page_text,
                    "metadata": {"page": i+1}
                })
                
        return "\n\n".join(text_content), chunks

    def _parse_notebook(self, path: Path):
        chunks = []
        full_text = []
        with open(path, "r", encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)
            
        for i, cell in enumerate(nb.cells):
            if cell.cell_type in ["markdown", "code"]:
                source = cell.source
                full_text.append(source)
                chunks.append({
                    "text": source,
                    "metadata": {"cell_type": cell.cell_type, "cell_index": i}
                })
        return "\n".join(full_text), chunks

    def _parse_text(self, path: Path):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        return text, [{"text": text, "metadata": {"type": "full_text"}}]

    def _parse_docx(self, path: Path):
        """Parses DOCX files using python-docx."""
        chunks = []
        full_text = []
        try:
            import docx
            doc = docx.Document(path)
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
                    chunks.append({
                        "text": para.text,
                        "metadata": {"type": "paragraph"}
                    })
        except ImportError:
            raise ImportError("python-docx is required. Please install it.")
            
        return "\n\n".join(full_text), chunks

library_ingestor = LibraryIngestor()
