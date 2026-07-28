"""
Knowledge Base Auto-Store — Central capture layer for ALL module outputs.
Like Google NotebookLM: every file uploaded, every docking result, every literature
search, every research output automatically flows into the Knowledge Base with
proper categorization.

Usage (from any API/module):
    from modules.knowledge.auto_store import auto_store
    auto_store("docking", "Vina Docking: aspirin vs COX-2", result_json, source="AutoDock Vina")
"""
import os
import json
import time
import logging

log = logging.getLogger("kb.auto_store")

# Resolve KB_DIR relative to project root (same as api/knowledge.py)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
KB_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "..", "data", "knowledge_base"))
os.makedirs(KB_DIR, exist_ok=True)

INDEX_FILE = os.path.join(KB_DIR, "index.json")

# Category mapping for auto-detection
MODULE_TO_CATEGORY = {
    # Docking
    "docking": "docking",
    "docking_run": "docking",
    "docking_mmgbsa": "docking",
    "docking_analysis": "docking",
    "docking_prepare": "docking",
    "molecular_docking": "docking",
    # Literature
    "literature": "literature",
    "literature_search": "literature",
    "deep_research": "deep_research",
    "deep_review": "deep_research",
    # Drug Analysis
    "drug_analysis": "drug_analysis",
    "drug_properties": "drug_analysis",
    "admet": "drug_analysis",
    "admet_predict": "drug_analysis",
    "drug_browser": "drug_analysis",
    # QSAR
    "qsar": "qsar",
    "qsar3d": "qsar",
    # Pharmacophore
    "pharmacophore": "pharmacophore",
    # Statistics
    "statistics": "statistics",
    "statistics_analyze": "statistics",
    "statistics_auto": "statistics",
    # MD Lite — its OWN category (was wrongly dumped into docking)
    "md_lite": "md_simulation",
    # Faculty
    "faculty": "faculty",
    "faculty_tools": "faculty",
    "lecture_generate": "faculty",
    "ppt_generate": "faculty",
    "ppt_master": "faculty",
    # Writing
    "writing": "notes",
    "thesis": "notes",
    # Clinical
    "clinical": "clinical_trials",
    "clinical_trials": "clinical_trials",
    # Pharmacology & Medicinal Chemistry
    "pharmacology": "pharmacology",
    "medicinal_chemistry": "medicinal_chemistry",
    # Formulation / Pharmaceutics
    "formulation": "formulation",
    "pharma_utils": "formulation",
    # Pharma Analysis / Quality Control
    "pharma_analysis": "pharma_analysis",
    # Natural Products
    "natural_products": "natural_products",
    # Knowledge
    "knowledge": "notes",
    # Uploads
    "upload": "notes",
}


def _load_index():
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"entries": [], "categories": {}}


def _save_index(index):
    try:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Failed to save KB index: {e}")


def _is_literature_stub(content: str) -> str:
    """Validate that content is a REAL full article, not a stub/abstract/metadata.

    Returns:
        None — content is valid (a real full article)
        str — reason for rejection (stub pattern detected)

    A valid full article has:
      - >= 3000 chars of body text
      - Structured sections (## Introduction, ## Methods, ## Results, ## Discussion)
        OR dense prose paragraphs
      - NOT just title + authors + abstract
    """
    if not content:
        return "empty content"
    text = content.strip()

    # --- Size gate ---
    # A real full article is at least 3000 chars (~500 words / 1.5 pages).
    # Abstracts are typically 200-300 words (~1500-2000 chars).
    if len(text) < 3000:
        return f"too short ({len(text)} chars, need >=3000 for full article)"

    # --- Stub phrase patterns ---
    stub_patterns = [
        "Full article saved as PDF",
        "Full article saved as DOCX",
        "Full article saved as",
        "Abstract not available",
        "Full text not available",
        "No full text found",
        "Full text unavailable",
        "Please download the PDF",
        "Access required",
        "Paywall — cannot access",
        "Subscription required",
        "Login required to view",
        "Sign in to view",
    ]
    for pat in stub_patterns:
        if pat.lower() in text.lower():
            return f"stub phrase: '{pat}'"

    # --- Abstract-only detection ---
    # If content is short and contains "Abstract" but no body sections, it's an abstract
    has_abstract = "abstract" in text.lower()[:1000]
    has_body_sections = any(s in text.lower() for s in [
        "## introduction", "## methods", "## methodology", "## materials and methods",
        "## results", "## discussion", "## conclusion", "## references",
        "introduction", "methods", "results", "discussion",
    ])
    if has_abstract and not has_body_sections and len(text) < 5000:
        return "abstract-only (no body sections)"

    # --- Metadata-only detection ---
    # Content that is just key-value pairs (Title: X, Authors: Y, DOI: Z)
    # without substantial prose
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        metadata_patterns = [
            l.startswith(("Title:", "Authors:", "DOI:", "PMID:", "Journal:",
                          "Published:", "Source:", "URL:", "Keywords:"))
            for l in lines
        ]
        # If >60% of non-empty lines are metadata fields, it's metadata-only
        metadata_ratio = sum(metadata_patterns) / len(lines)
        if metadata_ratio > 0.6 and len(text) < 8000:
            return "metadata-only (no article body)"

    # --- Boilerplate detection ---
    # Content that is mostly the same text repeated (low lexical diversity)
    # Real scientific articles have ~0.15-0.30 unique word ratio
    # Only reject if EXTREMELY repetitive (same words over and over)
    unique_words = len(set(text.lower().split()))
    total_words = len(text.split())
    if total_words > 100 and unique_words / total_words < 0.10:
        return "boilerplate (low lexical diversity)"

    return None  # Valid full article


def auto_store(module_name, title, content, source="", tags=None, metadata=None,
               category=None, store_as="md"):
    """Store ANY module output into the Knowledge Base automatically.

    Args:
        module_name: Name of the calling module (e.g. "docking_run", "literature_search")
        title: Human-readable title for the entry
        content: The content to store (string, dict, or list — will be formatted)
        source: Where it came from (e.g. "AutoDock Vina", "PubMed")
        tags: List of string tags
        metadata: Dict of extra metadata
        category: Override category. If None, auto-detect from module_name
        store_as: File format — "md" (markdown), "json", "txt"

    Returns:
        entry dict with id, file path, category
    """
    try:
        # Auto-detect category
        if not category:
            category = MODULE_TO_CATEGORY.get(module_name, "misc")

        # Format content
        if isinstance(content, (dict, list)):
            if store_as == "json":
                formatted_content = json.dumps(content, indent=2, ensure_ascii=False, default=str)
            else:
                # Pretty-format dict/list as markdown
                formatted_content = _format_as_markdown(content, title, source, metadata)
        elif isinstance(content, str):
            formatted_content = content
        else:
            formatted_content = str(content)

        # ── VALIDATION: Prevent storing stubs for literature entries ──
        # HARD RULE: Only full articles (with body text) are stored.
        # No abstracts, no metadata-only, no stubs. Ever.
        if category in ("literature", "deep_research"):
            is_stub = _is_literature_stub(formatted_content)
            if is_stub:
                log.warning(f"SKIP storing literature stub [{category}]: {title[:50]} "
                            f"({len(formatted_content)} chars) — {is_stub}")
                return None

        # Ensure category directory exists
        cat_dir = os.path.join(KB_DIR, category)
        os.makedirs(cat_dir, exist_ok=True)

        # Create safe filename
        safe_title = "".join(c for c in title[:50] if c.isalnum() or c in " _-").strip().replace(" ", "_")
        if not safe_title:
            safe_title = f"entry_{int(time.time())}"

        # Add timestamp to avoid collisions
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        ext = "json" if store_as == "json" else "md"
        filename = f"{safe_title}_{timestamp}.{ext}"
        filepath = os.path.join(cat_dir, filename)

        # Write content
        with open(filepath, "w", encoding="utf-8") as f:
            if store_as == "json" and isinstance(content, (dict, list)):
                json.dump(content, f, indent=2, ensure_ascii=False, default=str)
            else:
                f.write(f"# {title}\n\n")
                if tags:
                    f.write(f"**Tags:** {', '.join(tags) if isinstance(tags, list) else tags}\n\n")
                if source:
                    f.write(f"**Source:** {source}\n")
                if module_name:
                    f.write(f"**Module:** {module_name}\n")
                f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                f.write(formatted_content)

        # Update index
        index = _load_index()
        entry_id = f"{category}_{len(index['entries'])}_{timestamp}"
        entry = {
            "id": entry_id,
            "title": title,
            "category": category,
            "category_label": category.replace("_", " ").title(),
            "tags": tags or [category],
            "source": source or module_name,
            "module": module_name,
            "file": filepath,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "size": len(formatted_content),
            "metadata": metadata or {},
        }
        index["entries"].append(entry)
        index["categories"][category] = index["categories"].get(category, 0) + 1
        _save_index(index)

        log.info(f"Auto-stored [{category}]: {title[:50]} -> {filename}")
        return entry

    except Exception as e:
        log.error(f"Auto-store failed for {module_name}: {e}")
        return None


def _format_as_markdown(data, title, source, metadata):
    """Format a dict/list as readable markdown."""
    lines = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"## {key.replace('_', ' ').title()}\n")
                lines.append(_format_nested(value, indent=1))
                lines.append("")
            elif isinstance(value, str) and len(value) > 200:
                lines.append(f"**{key.replace('_', ' ').title()}:**\n\n{value}\n")
            else:
                lines.append(f"**{key.replace('_', ' ').title()}:** {value}")
        return "\n".join(lines)
    elif isinstance(data, list):
        for i, item in enumerate(data, 1):
            lines.append(f"### Entry {i}\n")
            lines.append(_format_as_markdown(item, "", "", None))
            lines.append("---\n")
        return "\n".join(lines)
    return str(data)


def _format_nested(data, indent=1):
    """Format nested dict/list for markdown."""
    prefix = "  " * indent
    lines = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}- **{key}:**")
                lines.append(_format_nested(value, indent + 1))
            else:
                val_str = str(value)
                if len(val_str) > 150:
                    val_str = val_str[:150] + "..."
                lines.append(f"{prefix}- {key}: {val_str}")
    elif isinstance(data, list):
        for i, item in enumerate(data[:20]):  # Limit to 20 items
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}- [{i+1}]")
                lines.append(_format_nested(item, indent + 1))
            else:
                val_str = str(item)
                if len(val_str) > 100:
                    val_str = val_str[:100] + "..."
                lines.append(f"{prefix}- {val_str}")
    return "\n".join(lines)


def auto_store_file(module_name, title, filepath, source="", category=None, tags=None):
    """Store an existing file (e.g. a downloaded PDF, generated PDBQT, etc.) into KB index.

    Args:
        module_name: Calling module name
        title: Title for the entry
        filepath: Path to the file (will be copied or indexed)
        source: Source label
        category: Override category
        tags: Tags list
    """
    try:
        if not os.path.exists(filepath):
            log.warning(f"auto_store_file: file not found: {filepath}")
            return None

        if not category:
            category = MODULE_TO_CATEGORY.get(module_name, "misc")

        # Get file size
        file_size = os.path.getsize(filepath)

        # Update index (reference the file, don't copy it)
        index = _load_index()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        entry_id = f"{category}_{len(index['entries'])}_{timestamp}"
        entry = {
            "id": entry_id,
            "title": title,
            "category": category,
            "category_label": category.replace("_", " ").title(),
            "tags": tags or [category],
            "source": source or module_name,
            "module": module_name,
            "file": filepath,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "size": file_size,
            "metadata": {"original_file": filepath},
        }
        index["entries"].append(entry)
        index["categories"][category] = index["categories"].get(category, 0) + 1
        _save_index(index)

        log.info(f"Auto-stored file [{category}]: {title[:50]} -> {filepath}")
        return entry

    except Exception as e:
        log.error(f"auto_store_file failed: {e}")
        return None
