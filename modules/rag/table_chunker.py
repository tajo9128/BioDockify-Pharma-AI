"""
BioDockify Knowledge Base — Table-Aware Chunker

Prevents markdown tables from being split mid-row during chunking.
Tables (header + separator + all rows) are kept as single indivisible chunks.
Prose between tables is chunked normally.

This is critical for pharma research: docking score tables, ADMET property
tables, SAR activity tables, and clinical trial endpoint tables are the
densest factual content. Splitting them destroys the data.

Pure Python, no external deps. Drop-in replacement for the fixed-size
window approach in modules/rag/chunker.py.

Usage:
    from modules.rag.table_chunker import chunk_text_table_aware
    chunks = chunk_text_table_aware(markdown_text, max_chars=1500)
"""

import re
import logging
from typing import List

log = logging.getLogger("rag.table_chunker")

# Matches a markdown table block: header row, separator row, and body rows
# A table starts with a line containing | and the next line is |---|---|
_TABLE_RE = re.compile(
    r"(?:^[ \t]*\|.*\|[ \t]*\n"  # header row
    r"^[ \t]*\|[\s\-:|]+\|[ \t]*\n"  # separator row
    r"(?:^[ \t]*\|.*\|[ \t]*\n)*)"  # body rows (zero or more)
    , re.MULTILINE
)


def chunk_text_table_aware(text: str, max_chars: int = 1500,
                           overlap: int = 100) -> List[str]:
    """Chunk text while keeping markdown tables intact.

    Strategy:
      1. Find all table blocks in the text
      2. For prose between tables, use sliding-window chunking
      3. Each table block becomes a single chunk (if it fits in max_chars)
      4. Tables larger than max_chars are split at row boundaries

    Args:
        text: The markdown text to chunk
        max_chars: Maximum characters per chunk
        overlap: Character overlap between prose chunks

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    # Find all table regions
    table_matches = list(_TABLE_RE.finditer(text))

    if not table_matches:
        # No tables — use simple sliding window
        return _sliding_window(text, max_chars, overlap)

    chunks = []
    last_end = 0

    for tm in table_matches:
        # Chunk the prose BEFORE this table
        prose = text[last_end:tm.start()]
        if prose.strip():
            chunks.extend(_sliding_window(prose, max_chars, overlap))

        # Extract the table
        table_text = tm.group(0)

        if len(table_text) <= max_chars:
            # Table fits in one chunk
            chunks.append(table_text.rstrip())
        else:
            # Table too large — split at row boundaries
            chunks.extend(_split_table_by_rows(table_text, max_chars))

        last_end = tm.end()

    # Chunk any remaining prose after the last table
    remaining = text[last_end:]
    if remaining.strip():
        chunks.extend(_sliding_window(remaining, max_chars, overlap))

    return [c for c in chunks if c.strip()]


def _sliding_window(text: str, max_chars: int, overlap: int) -> List[str]:
    """Simple sliding-window chunker for prose text.

    Tries to break at paragraph or sentence boundaries.
    """
    if not text.strip():
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + max_chars, text_len)

        # Try to break at a paragraph boundary
        if end < text_len:
            para_break = text.rfind("\n\n", start, end)
            if para_break > start + max_chars // 2:
                end = para_break + 2
            else:
                # Try sentence boundary
                sent_break = text.rfind(". ", start, end)
                if sent_break > start + max_chars // 2:
                    end = sent_break + 2
                else:
                    # Try word boundary
                    word_break = text.rfind(" ", start, end)
                    if word_break > start + max_chars // 2:
                        end = word_break + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break
        start = end - overlap

    return chunks


def _split_table_by_rows(table_text: str, max_chars: int) -> List[str]:
    """Split a large markdown table at row boundaries.

    Keeps header + separator in each chunk so each is a valid standalone table.
    """
    lines = table_text.strip().split("\n")
    if len(lines) < 3:
        return [table_text.strip()]

    # First two lines are header + separator
    header = lines[0]
    separator = lines[1]
    body_lines = lines[2:]

    header_block = f"{header}\n{separator}\n"
    header_len = len(header_block)

    chunks = []
    current_rows = []
    current_len = header_len

    for row in body_lines:
        row_len = len(row) + 1  # +1 for newline
        if current_len + row_len > max_chars and current_rows:
            # Flush current chunk
            chunk = header_block + "\n".join(current_rows) + "\n"
            chunks.append(chunk.rstrip())
            current_rows = []
            current_len = header_len

        current_rows.append(row)
        current_len += row_len

    # Don't forget the last chunk
    if current_rows:
        chunk = header_block + "\n".join(current_rows) + "\n"
        chunks.append(chunk.rstrip())

    return chunks
