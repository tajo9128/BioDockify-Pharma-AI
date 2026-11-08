"""Multi-section long-form writing pipeline + citation style switching.

Additive module — handles 50+ page reviews via outline→per-section→merge.
Citation styles: numbered (default), Vancouver, APA, AMA.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

SECTION_TEMPLATES = {
    "introduction": "Provide background, rationale, and objectives. Cite foundational work.",
    "methods": "Describe study design, participants, interventions, outcomes, and analysis. Cite methodological references.",
    "results": "Present findings objectively with data. Cite supporting tables/figures.",
    "discussion": "Interpret findings, compare with literature, discuss limitations. Cite comparisons.",
    "conclusion": "Summarize key findings and implications. Keep concise.",
    "literature_review": "Synthesize the current state of knowledge. Organize by theme, not paper-by-paper. Cite all claims.",
    "mechanism_of_action": "Describe molecular/cellular mechanisms with pathway detail. Cite primary research.",
    "clinical_evidence": "Review trial evidence including study design, population, outcomes, and quality assessment.",
    "safety_and_adverse_effects": "Cover known ADRs, contraindications, warnings. Cite safety data.",
    "regulatory_landscape": "Discuss approval status, guidelines, and compliance requirements.",
}


def build_outline(topic: str, doc_type: str = "review", num_sections: int = 8) -> List[Dict[str, str]]:
    """Generate a document outline with section prompts."""
    if doc_type == "review":
        default = [
            ("introduction", "Background and scope"),
            ("literature_review", "Current state of knowledge"),
            ("methods", "Literature search methodology"),
            ("mechanism_of_action", "Mechanistic insights"),
            ("clinical_evidence", "Clinical trial evidence"),
            ("safety_and_adverse_effects", "Safety profile"),
            ("regulatory_landscape", "Regulatory and guideline context"),
            ("discussion", "Synthesis and future directions"),
            ("conclusion", "Summary"),
        ]
    elif doc_type == "thesis":
        default = [
            ("introduction", "Introduction and background"),
            ("literature_review", "Literature review"),
            ("methods", "Materials and methods"),
            ("results", "Results"),
            ("discussion", "Discussion"),
            ("conclusion", "Conclusions and future work"),
        ]
    else:  # research paper
        default = [
            ("introduction", "Introduction"),
            ("methods", "Methods"),
            ("results", "Results"),
            ("discussion", "Discussion"),
        ]

    sections = default[:max(4, min(num_sections, len(default)))]
    return [{"id": s[0], "title": s[1],
             "prompt_hint": SECTION_TEMPLATES.get(s[0], "Write this section."),
             "word_target": 500 if s[0] == "conclusion" else 1500}
            for s in sections]


# ── Citation style switching ───────────────────────────────────────────────────

_CITATION_FORMATS = {
    "numbered": "[{n}] {author}. {title}. {journal}. {year};{volume}:{pages}.",
    "vancouver": "{author}. {title}. {journal}. {year};{volume}({issue}):{pages}.",
    "apa": "{author} ({year}). {title}. {journal}, {volume}({issue}), {pages}.",
    "ama": "{author}. {title}. {journal}. {year};{volume}({issue}):{pages}.",
}


def format_citation(ref: Dict[str, str], style: str = "numbered", n: int = 1) -> str:
    """Format a single citation reference in the specified style."""
    template = _CITATION_FORMATS.get(style, _CITATION_FORMATS["numbered"])
    # normalize author list
    authors = ref.get("author", ref.get("authors", ""))
    if isinstance(authors, list):
        if len(authors) > 6:
            authors = ", ".join(authors[:6]) + " et al."
        elif len(authors) > 1:
            authors = ", ".join(authors[:-1]) + " & " + authors[-1]
        else:
            authors = authors[0] if authors else "Unknown"

    fields = {
        "n": n,
        "author": authors,
        "title": ref.get("title", ref.get("citation_title", "Untitled")),
        "journal": ref.get("journal", ref.get("container_title", "")),
        "year": ref.get("year", ref.get("publication_year", "")),
        "volume": ref.get("volume", ""),
        "issue": ref.get("issue", ""),
        "pages": ref.get("pages", ref.get("page_range", "")),
    }
    try:
        return template.format(**fields)
    except (KeyError, IndexError):
        return f"[{n}] {fields['author']}. {fields['title']}. {fields['journal']}. {fields['year']}."


def reformat_bibliography(references: List[Dict], style: str = "vancouver") -> List[str]:
    """Reformat an entire reference list in the chosen citation style."""
    return [format_citation(ref, style, i + 1) for i, ref in enumerate(references)]


def inline_citations_to_style(text: str, style: str = "vancouver") -> str:
    """Convert inline [1], [2] citations to the target style marker.
    Vancouver/numbered/AMA keep [n]; APA converts to (Author, year) if resolvable."""
    if style == "apa":
        # Pattern: [n] or [n,m] — can't resolve without ref map, keep as placeholder
        # In practice, the caller pre-processes with the ref map
        return text
    return text  # numbered/vancouver/ama all use [n] format
