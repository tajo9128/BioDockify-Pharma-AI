"""Textbook Parser — multi-format document ingestion for Faculty CMD.

Extracts text and chapter structure from textbooks (PDF, EPUB, DOCX, HTML, TXT)
for use in lecture generation, slide creation, and question paper generation.

Adapted from book-to-skill (github.com/virgiliojr94/book-to-skill) parsers.
"""
import io
import os
import re
import logging
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("faculty.textbook_parser")

# ── Supported formats ────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    ".pdf", ".epub", ".docx", ".txt", ".md",
    ".html", ".htm", ".rtf",
}

# ── Chapter detection patterns (from book-to-skill/utils.py) ─────────────────
_CHAPTER_RE = re.compile(
    r"(?:^|\s)(?:chapter|ch\.?|cap[ií]tulo|cap\.?|kapitel|chapitre)\s*"
    r"(\d+|[ivxlcdm]+|[一二三四五六七八九十百千]+|[๑๒๓๔๕๖๗๘๙๐]+|[가-힣]+)",
    re.IGNORECASE,
)
_TOC_RE = re.compile(
    r"(?:table\s+of\s+contents|contents|índice|indice|目次|สารบัญ|목차)",
    re.IGNORECASE,
)


def _chapter_number(line: str) -> Optional[int]:
    """Extract chapter number from a heading line. Returns None if not a chapter heading."""
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return None
    m = _CHAPTER_RE.search(stripped)
    if not m:
        return None
    raw = m.group(1)
    # Arabic
    if raw.isdigit():
        return int(raw)
    # Roman
    roman_map = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    if all(c in roman_map for c in raw.lower()):
        total = 0
        prev = 0
        for c in reversed(raw.lower()):
            val = roman_map[c]
            total += val if val >= prev else -val
            prev = val
        return total if total > 0 else None
    return None


def detect_structure(text: str) -> Dict:
    """Detect chapter count and table of contents presence."""
    lines = text.splitlines()
    headings = []
    numbers = set()
    for line in lines:
        num = _chapter_number(line)
        if num is not None:
            numbers.add(num)
            headings.append(line.strip()[:100])

    chapters_detected = len(numbers) if numbers else 0
    has_toc = bool(_TOC_RE.search(text[:30000]))

    return {
        "chapters_detected": chapters_detected,
        "chapter_headings": headings[:20],
        "has_toc": has_toc,
    }


def split_into_chapters(text: str) -> List[Dict]:
    """Split extracted text into chapters based on detected headings.

    Returns list of dicts: {number, title, content, start_line, end_line}
    """
    lines = text.splitlines()
    chapter_starts = []

    for i, line in enumerate(lines):
        num = _chapter_number(line)
        if num is not None:
            chapter_starts.append((i, num, line.strip()[:120]))

    if not chapter_starts:
        # No chapters detected — return entire text as one chapter
        return [{
            "number": 1,
            "title": "Full Text",
            "content": text,
            "start_line": 0,
            "end_line": len(lines),
            "word_count": len(text.split()),
        }]

    chapters = []
    for idx, (start_line, num, title) in enumerate(chapter_starts):
        end_line = chapter_starts[idx + 1][0] if idx + 1 < len(chapter_starts) else len(lines)
        content = "\n".join(lines[start_line:end_line])
        chapters.append({
            "number": num,
            "title": title,
            "content": content,
            "start_line": start_line,
            "end_line": end_line,
            "word_count": len(content.split()),
        })

    return chapters


def estimate_tokens(text: str) -> int:
    """Estimate token count (approximate)."""
    words = len(text.split())
    return int(words / 0.75)


# ── Format-specific extractors ───────────────────────────────────────────────

def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes. Tries pypdf first, then raw text."""
    # Try pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages[:200]:  # limit to 200 pages
            text = page.extract_text()
            if text:
                pages.append(text)
        result = "\n\n".join(pages)
        if len(result.strip()) > 100:
            return result
    except Exception as e:
        log.warning(f"pypdf extraction failed: {e}")

    # Try pymupdf (fitz)
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = []
        for page in doc[:200]:
            pages.append(page.get_text())
        doc.close()
        result = "\n\n".join(pages)
        if len(result.strip()) > 100:
            return result
    except Exception as e:
        log.warning(f"pymupdf extraction failed: {e}")

    return ""


def _extract_epub(file_bytes: bytes) -> str:
    """Extract text from EPUB bytes."""
    # Try ebooklib
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
        book = epub.read_epub(io.BytesIO(file_bytes))
        texts = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(separator="\n")
            if text.strip():
                texts.append(text)
        result = "\n\n".join(texts)
        if len(result.strip()) > 100:
            return result
    except Exception as e:
        log.warning(f"ebooklib extraction failed: {e}")

    # Fallback: zipfile parser
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            # Find content.opf for spine order
            opf_path = None
            for name in zf.namelist():
                if name.endswith(".opf"):
                    opf_path = name
                    break
            texts = []
            for name in sorted(zf.namelist()):
                if name.endswith((".html", ".xhtml", ".htm")):
                    raw = zf.read(name).decode("utf-8", errors="replace")
                    # Strip HTML tags
                    clean = re.sub(r"<[^>]+>", " ", raw)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    if len(clean) > 50:
                        texts.append(clean)
            return "\n\n".join(texts)
    except Exception as e:
        log.warning(f"zipfile epub extraction failed: {e}")

    return ""


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes."""
    # Try python-docx
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        result = "\n\n".join(paragraphs)
        if len(result.strip()) > 100:
            return result
    except Exception as e:
        log.warning(f"python-docx extraction failed: {e}")

    # Fallback: zipfile XML parser
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            xml_bytes = zf.read("word/document.xml")
        tree = ET.fromstring(xml_bytes)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        texts = [t.text for t in tree.iter(f"{{{ns['w']}}}t") if t.text]
        return "\n".join(texts)
    except Exception as e:
        log.warning(f"zipfile docx extraction failed: {e}")

    return ""


def _extract_html(file_bytes: bytes) -> str:
    """Extract text from HTML bytes."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(file_bytes, "html.parser")
        return soup.get_text(separator="\n")
    except Exception:
        # Fallback: strip tags with regex
        text = file_bytes.decode("utf-8", errors="replace")
        clean = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", clean).strip()


def _extract_rtf(file_bytes: bytes) -> str:
    """Extract text from RTF bytes."""
    try:
        from striprtf.striprtf import rtf_to_text
        return rtf_to_text(file_bytes.decode("utf-8", errors="replace"))
    except Exception:
        # Fallback: strip RTF control words
        text = file_bytes.decode("utf-8", errors="replace")
        text = re.sub(r"\\[a-z]+\d*\s?", "", text)
        text = re.sub(r"[{}]", "", text)
        return text.strip()


def _extract_text(file_bytes: bytes) -> str:
    """Extract text from plain text bytes."""
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
        try:
            return file_bytes.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return file_bytes.decode("utf-8", errors="replace")


# ── Main extraction API ──────────────────────────────────────────────────────

_EXTRACTORS = {
    ".pdf": _extract_pdf,
    ".epub": _extract_epub,
    ".docx": _extract_docx,
    ".html": _extract_html,
    ".htm": _extract_html,
    ".rtf": _extract_rtf,
    ".txt": _extract_text,
    ".md": _extract_text,
}


def extract_textbook(file_bytes: bytes, filename: str) -> Dict:
    """Extract text and chapter structure from a textbook file.

    Args:
        file_bytes: Raw file bytes (decoded from base64 by the caller)
        filename: Original filename (used for format detection)

    Returns:
        Dict with keys:
            - success: bool
            - text: str (full extracted text)
            - chapters: list of chapter dicts
            - structure: dict with chapters_detected, chapter_headings, has_toc
            - metadata: dict with filename, format, char_count, word_count, est_tokens
            - error: str (if success is False)
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        # Try magic byte sniffing
        if file_bytes[:4] == b"%PDF":
            ext = ".pdf"
        elif file_bytes[:2] == b"PK":
            if b"word/document.xml" in file_bytes[:5000]:
                ext = ".docx"
            elif b"application/epub" in file_bytes[:5000]:
                ext = ".epub"
            else:
                return {"success": False, "error": f"Unsupported format: {filename}"}
        else:
            # Assume plain text
            ext = ".txt"

    extractor = _EXTRACTORS.get(ext)
    if not extractor:
        return {"success": False, "error": f"No extractor for {ext}"}

    try:
        text = extractor(file_bytes)
    except Exception as e:
        log.error(f"Extraction failed for {filename}: {e}")
        return {"success": False, "error": f"Extraction failed: {e}"}

    if not text or len(text.strip()) < 100:
        return {"success": False, "error": f"Could not extract meaningful text from {filename}"}

    # Detect structure
    structure = detect_structure(text)

    # Split into chapters
    chapters = split_into_chapters(text)

    # Metadata
    word_count = len(text.split())
    est_tokens = estimate_tokens(text)

    return {
        "success": True,
        "text": text,
        "chapters": chapters,
        "structure": structure,
        "metadata": {
            "filename": filename,
            "format": ext.lstrip("."),
            "char_count": len(text),
            "word_count": word_count,
            "est_tokens": est_tokens,
            "chapters_found": len(chapters),
        },
    }


def extract_chapter_content(text: str, chapter_number: int) -> Optional[str]:
    """Extract content for a specific chapter number from full text."""
    chapters = split_into_chapters(text)
    for ch in chapters:
        if ch["number"] == chapter_number:
            return ch["content"]
    return None


def extract_topics_from_chapters(chapters: List[Dict]) -> List[str]:
    """Extract topic titles from chapter list for syllabus mapping."""
    topics = []
    for ch in chapters:
        title = ch.get("title", "")
        # Clean up "Chapter N: Title" format
        cleaned = re.sub(r"^(?:chapter|ch\.?)\s*\d+\s*[:.\-—]?\s*", "", title, flags=re.IGNORECASE).strip()
        if cleaned and cleaned != "Full Text":
            topics.append(cleaned)
    return topics
