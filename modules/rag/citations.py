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


class CitationRegistry:
    """Tracks source → citation label mapping.

    Each unique source gets a monotonic [n] label.
    Same source referenced again gets the same label.
    """

    def __init__(self):
        self._sources: Dict[str, int] = {}  # source_key → label_number
        self._labels: Dict[int, Dict[str, Any]] = {}  # label_number → metadata
        self._next: int = 1

    def register(self, source_type: str, source_id: str,
                 display: str, snippet: str = "") -> int:
        """Register a source and return its citation label number.

        If the source was already registered, returns its existing label.
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
        """Serialize for API response."""
        return {
            "citations": [
                {"label": n, **meta}
                for n, meta in sorted(self._labels.items())
            ]
        }


def render_context(chunks: List[Dict[str, Any]], registry: CitationRegistry,
                   max_chars: int = 12000) -> str:
    """Build a <retrieved_context> block with labeled passages.

    Each chunk gets a [n] label. The block teaches the model to cite sources.

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
        "Cite your sources using [n] notation (e.g. [1], [2]).",
        "If multiple sources support a claim, stack them: [1][2].",
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

        n = registry.register("kb", str(entry_id), title, content)

        chunk_text = f"[{n}] {title}"
        if source:
            chunk_text += f" (Source: {source})"
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
    """Rewrite [n] markers in model output to [citation:id] format.

    Carefully avoids rewriting inside code spans (```blocks``` and `inline`).

    Args:
        text: The model's reply text
        registry: The CitationRegistry with registered sources

    Returns:
        Text with [n] → [citation:entry_id] where applicable
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

        # Replace [n] in non-code text
        def _replace(m):
            n = int(m.group(1))
            label = registry.get_label(n)
            if label:
                return f"[citation:{label['id']}]"
            return m.group(0)  # unknown citation — leave as-is

        seg_text = _ORDINAL.sub(_replace, seg_text)
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
1. Every factual claim MUST be followed by a citation marker [n] matching the passage number.
2. If multiple passages support a claim, stack citations: [1][2].
3. Copy citation numbers EXACTLY as assigned — do not invent new numbers.
4. If a claim is NOT supported by any passage, say so explicitly: "This is not covered in the available sources."
5. Prefer citing the most specific/relevant source.
6. Structure your answer clearly, grouping related information.
"""
