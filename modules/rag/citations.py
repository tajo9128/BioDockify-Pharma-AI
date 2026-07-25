"""
BioDockify Knowledge Base — Citation System

Provides Perplexity-style citations for KB chat answers:
  - CitationRegistry: assigns [1], [2], ... to retrieved chunks
  - render_context(): builds <retrieved_context> block with labeled passages
  - normalize_citations(): rewrites [n] in model output → [citation:id] markers
  - citation_prompt: system prompt teaching the model the citation protocol

This module is pure-Python, no Flask, no Agent Zero deps.
Inspired by SurfSense's citation spine (github.com/MODSetter/SurfSense).

Usage:
    from modules.rag.citations import CitationRegistry, render_context, normalize_citations

    reg = CitationRegistry()
    reg.register("kb", "docking_42", "Vina Docking: aspirin vs COX-2")
    context = render_context(chunks, reg)
    # ... send to LLM ...
    final = normalize_citations(llm_reply, reg)
"""

import re
import logging
from typing import List, Dict, Any, Optional

log = logging.getLogger("rag.citations")

# Regex to find [n] citation markers in model output, EXCLUDING code spans.
# We split on code fences/inline code first, then only process non-code parts.
_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`]*`")
_ORDINAL = re.compile(r"\[(\d{1,3})\]")
_TYPE_ORDINAL = re.compile(r"\[(\w+):(\d{1,3})\]")  # [web:1], [kb:2], etc.

# Supported source types (inspired by Perplexity's citation system)
SOURCE_TYPES = {
    "kb": "Knowledge Base entry",
    "web": "Web search result",
    "page": "Full web page content",
    "conversation_history": "Previous conversation",
    "pubmed": "PubMed article",
    "semantic_scholar": "Semantic Scholar paper",
    "arxiv": "arXiv preprint",
    "europe_pmc": "Europe PMC article",
}


class CitationRegistry:
    """Tracks source → citation label mapping.

    Each unique source gets a monotonic label.
    Same source referenced again gets the same label.

    Supports source type prefixes (Perplexity-style):
      - [kb:1] — Knowledge Base entry
      - [web:2] — Web search result
      - [page:3] — Full web page
      - [conversation_history:4] — Previous conversation
    """

    def __init__(self):
        self._sources: Dict[str, int] = {}  # source_key → label_number
        self._labels: Dict[int, Dict[str, Any]] = {}  # label_number → metadata
        self._next: int = 1

    def register(self, source_type: str, source_id: str,
                 display: str, snippet: str = "", url: str = "") -> int:
        """Register a source and return its citation label number.

        If the source was already registered, returns its existing label.

        Args:
            source_type: One of SOURCE_TYPES keys (kb, web, page, etc.)
            source_id: Unique identifier for the source
            display: Human-readable display name
            snippet: Short text snippet from the source
            url: Optional URL for web sources
        """
        key = f"{source_type}:{source_id}"
        if key in self._sources:
            return self._sources[key]

        n = self._next
        self._next += 1
        self._sources[key] = n
        self._labels[n] = {
            "type": source_type,
            "id": source_id,
            "display": display,
            "snippet": snippet[:200] if snippet else "",
            "url": url or "",
        }
        return n

    def get_label(self, n: int) -> Optional[Dict[str, Any]]:
        """Get metadata for a citation label."""
        return self._labels.get(n)

    def get_all(self) -> Dict[int, Dict[str, Any]]:
        """Return all registered citations."""
        return dict(self._labels)

    @property
    def count(self) -> int:
        return len(self._labels)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API response (Perplexity-style structured citations)."""
        return {
            "citations": [
                {
                    "label": n,
                    "type": meta.get("type", "kb"),
                    "id": meta.get("id", ""),
                    "display": meta.get("display", ""),
                    "snippet": meta.get("snippet", ""),
                    "url": meta.get("url", ""),
                }
                for n, meta in sorted(self._labels.items())
            ]
        }


def render_context(chunks: List[Dict[str, Any]], registry: CitationRegistry,
                   max_chars: int = 12000) -> str:
    """Build a <retrieved_context> block with labeled passages.

    Each chunk gets a [type:n] label (Perplexity-style).
    The block teaches the model to cite sources.

    Args:
        chunks: List of chunk dicts with keys: content, entry_id, title, source
        registry: The CitationRegistry to register sources into
        max_chars: Maximum total character budget for the context block

    Returns:
        Formatted string ready to prepend to the LLM prompt.
    """
    if not chunks:
        return ""

    lines = [
        "<retrieved_context>",
        "Use the following passages to answer the user's question.",
        "Cite your sources using [type:n] notation (e.g. [kb:1], [web:2]).",
        "If multiple sources support a claim, stack them: [kb:1][web:2].",
        "Do NOT cite sources for general knowledge not in these passages.",
        "Do NOT invent citation numbers — only use the numbers assigned below.",
        "",
    ]

    total = 0
    for chunk in chunks:
        content = chunk.get("content", "").strip()
        if not content:
            continue

        entry_id = chunk.get("entry_id", chunk.get("id", ""))
        title = chunk.get("title", "Unknown")
        source = chunk.get("source", "")
        source_type = chunk.get("source_type", "kb")
        url = chunk.get("url", "")

        n = registry.register(source_type, str(entry_id), title, content, url)

        chunk_text = f"[{source_type}:{n}] {title}"
        if source:
            chunk_text += f" (Source: {source})"
        if url:
            chunk_text += f" ({url})"
        chunk_text += f"\n{content}\n"

        if total + len(chunk_text) > max_chars:
            # Truncate the last chunk to fit
            remaining = max_chars - total
            if remaining > 200:
                chunk_text = chunk_text[:remaining] + "...\n"
            else:
                break

        lines.append(chunk_text)
        total += len(chunk_text)

    lines.append("</retrieved_context>")

    return "\n".join(lines)


def normalize_citations(text: str, registry: CitationRegistry) -> str:
    """Rewrite [n] and [type:n] markers in model output to [citation:id] format.

    Handles both formats:
      - [1] → [citation:entry_id] (legacy)
      - [kb:1] → [citation:entry_id] (Perplexity-style)

    Carefully avoids rewriting inside code spans (```blocks``` and `inline`).

    Args:
        text: The model's reply text
        registry: The CitationRegistry with registered sources

    Returns:
        Text with [n] or [type:n] → [citation:entry_id] where applicable
    """
    if not text or registry.count == 0:
        return text

    # Split into code and non-code segments
    segments = _split_code_segments(text)

    result_parts = []
    for seg_text, is_code in segments:
        if is_code:
            result_parts.append(seg_text)
            continue

        # Replace [type:n] in non-code text (Perplexity-style)
        def _replace_typed(m):
            source_type = m.group(1)
            n = int(m.group(2))
            label = registry.get_label(n)
            if label:
                return f"[citation:{label['id']}]"
            return m.group(0)  # unknown citation — leave as-is

        seg_text = _TYPE_ORDINAL.sub(_replace_typed, seg_text)

        # Replace [n] in non-code text (legacy format)
        def _replace_legacy(m):
            n = int(m.group(1))
            label = registry.get_label(n)
            if label:
                return f"[citation:{label['id']}]"
            return m.group(0)  # unknown citation — leave as-is

        seg_text = _ORDINAL.sub(_replace_legacy, seg_text)
        result_parts.append(seg_text)

    return "".join(result_parts)


def _split_code_segments(text: str) -> List[tuple]:
    """Split text into (segment, is_code) tuples.

    Code fence blocks and inline code are marked as code=True.
    """
    segments = []
    pos = 0

    # Find all code regions (fences first, then inline)
    code_regions = []

    # Fenced code blocks
    for m in _CODE_FENCE.finditer(text):
        code_regions.append((m.start(), m.end()))

    # Inline code (not inside fences)
    for m in _INLINE_CODE.finditer(text):
        # Check not inside a fence
        inside_fence = any(s <= m.start() < e for s, e in code_regions)
        if not inside_fence:
            code_regions.append((m.start(), m.end()))

    code_regions.sort()

    for start, end in code_regions:
        if start > pos:
            segments.append((text[pos:start], False))  # non-code
        segments.append((text[start:end], True))  # code
        pos = end

    if pos < len(text):
        segments.append((text[pos:], False))

    return segments if segments else [(text, False)]


# System prompt snippet teaching the model the citation protocol
CITATION_PROMPT = """You are answering questions based on retrieved knowledge base passages.

CITATION RULES:
1. Every factual claim MUST be followed by a citation marker matching the passage number.
2. Use the [type:n] format: [kb:1] for Knowledge Base, [web:2] for web sources, etc.
3. If multiple passages support a claim, stack citations: [kb:1][web:2].
4. Copy citation numbers EXACTLY as assigned — do not invent new numbers.
5. If a claim is NOT supported by any passage, say so explicitly: "This is not covered in the available sources."
6. Prefer citing the most specific/relevant source.
7. Structure your answer clearly, grouping related information.
8. When writing for pharmaceutical research, always cite clinical trial data, ICH guidelines, and regulatory standards.
"""
