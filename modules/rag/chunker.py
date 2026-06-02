"""Document Chunker — split documents into hierarchical chunks for indexing.

Splits documents into:
- Sections (by heading markers ##, ###, etc.)
- Paragraphs (by blank lines)
- Sentences (by punctuation)

Returns structured chunks with metadata for vector indexing.
"""
import re
from typing import List, Dict, Any


def chunk_document(text: str, doc_id: str = "", max_chunk_chars: int = 500, overlap_chars: int = 50) -> List[Dict[str, Any]]:
    """Split document text into hierarchical chunks.
    
    Args:
        text: Document text content
        doc_id: Document identifier
        max_chunk_chars: Maximum characters per chunk
        overlap_chars: Overlap between consecutive chunks
    
    Returns:
        List of chunk dicts with metadata
    """
    if not text or not text.strip():
        return []

    chunks = []
    sections = _split_sections(text)

    for sec_idx, (section_title, section_text) in enumerate(sections):
        paragraphs = _split_paragraphs(section_text)

        for para_idx, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue

            # If paragraph fits in one chunk, keep it whole
            if len(paragraph) <= max_chunk_chars:
                chunks.append({
                    "doc_id": doc_id,
                    "section_idx": sec_idx,
                    "section_title": section_title,
                    "paragraph_idx": para_idx,
                    "text": paragraph.strip(),
                    "word_count": len(paragraph.split()),
                    "char_count": len(paragraph),
                })
            else:
                # Split long paragraphs into overlapping windows
                sub_chunks = _sliding_window(paragraph, max_chunk_chars, overlap_chars)
                for sub_idx, sub_text in enumerate(sub_chunks):
                    chunks.append({
                        "doc_id": doc_id,
                        "section_idx": sec_idx,
                        "section_title": section_title,
                        "paragraph_idx": para_idx,
                        "sub_idx": sub_idx,
                        "text": sub_text.strip(),
                        "word_count": len(sub_text.split()),
                        "char_count": len(sub_text),
                    })

    return chunks


def _split_sections(text: str) -> List[tuple]:
    """Split text into sections by markdown headings."""
    lines = text.split("\n")
    sections = []
    current_title = "Introduction"
    current_lines = []

    for line in lines:
        if re.match(r'^#{1,4}\s+', line):
            # Save previous section
            if current_lines:
                sections.append((current_title, "\n".join(current_lines)))
            current_title = line.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_lines:
        sections.append((current_title, "\n".join(current_lines)))

    # If no headings found, treat entire text as one section
    if not sections:
        sections.append(("Document", text))

    return sections


def _split_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs by blank lines."""
    paragraphs = re.split(r'\n\s*\n', text)
    return [p.strip() for p in paragraphs if p.strip()]


def _sliding_window(text: str, window_size: int, overlap: int) -> List[str]:
    """Split text into overlapping windows."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + window_size, len(text))
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
        if start >= len(text):
            break
    return chunks


def chunk_papers(papers: List[Dict], max_chunk_chars: int = 500) -> List[Dict[str, Any]]:
    """Chunk a list of paper dicts (from literature search).
    
    Each paper gets chunked into:
    - Title chunk
    - Abstract chunk (if long enough)
    - Full text chunks (if available)
    """
    all_chunks = []

    for paper in papers:
        doc_id = paper.get("doi") or paper.get("pmid") or paper.get("title", "")[:50]
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        full_text = paper.get("full_text", "")

        # Title chunk
        if title:
            all_chunks.append({
                "doc_id": doc_id,
                "section_idx": 0,
                "section_title": "Title",
                "paragraph_idx": 0,
                "text": title,
                "word_count": len(title.split()),
                "char_count": len(title),
                "metadata": {
                    "doi": paper.get("doi"),
                    "pmid": paper.get("pmid"),
                    "journal": paper.get("journal"),
                    "year": paper.get("year"),
                    "authors": paper.get("authors", [])[:3],
                },
            })

        # Abstract chunk(s)
        if abstract:
            if len(abstract) <= max_chunk_chars:
                all_chunks.append({
                    "doc_id": doc_id,
                    "section_idx": 1,
                    "section_title": "Abstract",
                    "paragraph_idx": 0,
                    "text": abstract,
                    "word_count": len(abstract.split()),
                    "char_count": len(abstract),
                    "metadata": {
                        "doi": paper.get("doi"),
                        "pmid": paper.get("pmid"),
                    },
                })
            else:
                sub_chunks = _sliding_window(abstract, max_chunk_chars, 50)
                for idx, sub in enumerate(sub_chunks):
                    all_chunks.append({
                        "doc_id": doc_id,
                        "section_idx": 1,
                        "section_title": "Abstract",
                        "paragraph_idx": idx,
                        "text": sub.strip(),
                        "word_count": len(sub.split()),
                        "char_count": len(sub),
                        "metadata": {
                            "doi": paper.get("doi"),
                            "pmid": paper.get("pmid"),
                        },
                    })

        # Full text chunks (if available)
        if full_text:
            text_chunks = chunk_document(full_text, doc_id, max_chunk_chars)
            for chunk in text_chunks:
                chunk["metadata"] = {
                    "doi": paper.get("doi"),
                    "pmid": paper.get("pmid"),
                }
            all_chunks.extend(text_chunks)

    return all_chunks
