
import os
import nbformat
import pypdf
from typing import List, Dict, Any
from pathlib import Path

class DocumentIngestor:
    """
    Handles parsing of various file formats for the RAG system.
    Supports: .ipynb (Jupyter Notebooks), .pdf, .txt, .md
    """
    
    def ingest_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Ingests a file and returns a list of text chunks with metadata.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        ext = path.suffix.lower()
        
        if ext == ".ipynb":
            return self._parse_notebook(path)
        elif ext == ".pdf":
            return self._parse_pdf(path)
        elif ext == ".docx":
            return self._parse_docx(path)
        elif ext in [".md", ".txt"]:
            return self._parse_text(path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _parse_docx(self, path: Path) -> List[Dict[str, Any]]:
        """Parses DOCX files using python-docx."""
        chunks = []
        try:
            import docx
            doc = docx.Document(path)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            
            # For now, treat as one big chunk or meaningful sections?
            # Let's clean and join
            text = "\n\n".join(full_text)
            
            if text:
                chunks.append({
                    "text": text,
                    "metadata": {
                        "source": path.name,
                        "type": "docx_document"
                    }
                })
        except ImportError:
            raise ImportError("python-docx is required for .docx files. Please install it.")
        except Exception as e:
            raise ValueError(f"Failed to parse DOCX: {e}")
            
        return chunks

    def _parse_notebook(self, path: Path) -> List[Dict[str, Any]]:
        """Parses Jupyter Notebooks into cell-based chunks."""
        chunks = []
        with open(path, "r", encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)
            
        for i, cell in enumerate(nb.cells):
            content = ""
            meta_type = cell.cell_type
            
            if cell.cell_type == "markdown":
                content = f"[MARKDOWN CELL {i+1}]\n{cell.source}"
            elif cell.cell_type == "code":
                content = f"[CODE CELL {i+1}]\n{cell.source}"
                # Optional: Include output if significant?
                # For now, let's keep source code as primary.
            
            if content.strip():
                chunks.append({
                    "text": content,
                    "metadata": {
                        "source": path.name,
                        "type": "notebook_cell",
                        "cell_index": i,
                        "cell_type": meta_type
                    }
                })
        return chunks

    def _parse_pdf(self, path: Path) -> List[Dict[str, Any]]:
        """
        Parses PDFs into page-based chunks.
        Optimized for memory by processing pages sequentially.
        """
        chunks = []
        try:
            reader = pypdf.PdfReader(str(path))
            if reader.is_encrypted:
                 # TODO: Add password support if needed. For now, reject to prevent hanging/errors.
                 raise ValueError("Encrypted PDFs are not supported. Please remove password protection.")
                 
            total_pages = len(reader.pages)
            
            # Batching Logic could go here (e.g. yield generators), 
            # but since interface expects List, we strictly iterate.
            # For "Batch processing" requested by user, we'd ideally change 
            # ingestor interface to be async generator, but that's a larger refactor.
            # We ensure we just extract text cleanly here.
            
            for i in range(total_pages):
                try:
                    page = reader.pages[i]
                    text = page.extract_text()
                    if text and text.strip():
                        chunks.append({
                            "text": text,
                            "metadata": {
                                "source": path.name,
                                "type": "pdf_page",
                                "page_number": i + 1
                            }
                        })
                except Exception as page_error:
                    print(f"Warning: Failed to parse page {i+1} of {path.name}: {page_error}")
                    continue
                    
        except Exception as e:
            raise ValueError(f"Corrupt or unreadable PDF: {e}")
            
        return chunks

    def _parse_text(self, path: Path) -> List[Dict[str, Any]]:
        """Parses text/markdown files."""
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
            
        # Simple recursive splitting could go here, but for MVP keep whole or split by paragraph
        # Let's do simple naive paragraph splitting for now if it's huge
        
        return [{
            "text": text,
            "metadata": {
                "source": path.name,
                "type": "text_file"
            }
        }]

ingestor = DocumentIngestor()
