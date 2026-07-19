"""
BioDockify ↔ Obsidian sync engine.

All functions are pure-data transforms + filesystem operations.
No Flask, no Agent Zero, no database — just .md files and YAML frontmatter.

Vault path defaults to /a0/usr/obsidian_vault/ (inside biodockify_usr volume).
Users can override via settings or host bind mount.
"""

import os
import re
import time
import json
import logging
from typing import Dict, List, Any, Optional

log = logging.getLogger("obsidian.sync")

# Default vault path — inside biodockify_usr volume
DEFAULT_VAULT_PATH = "/a0/usr/obsidian_vault"

# BioDockify KB root
KB_ROOT = "/a0/data/knowledge_base"

# KB index file
KB_INDEX = os.path.join(KB_ROOT, "index.json")

# YAML frontmatter delimiters
FRONTMATTER_DELIM = "---"


# ---------------------------------------------------------------------------
# Frontmatter generation (BioDockify → Obsidian)
# ---------------------------------------------------------------------------

def generate_frontmatter(entry: Dict[str, Any], content: str = "") -> str:
    """Generate Obsidian-standard YAML frontmatter for a KB entry.

    Compatible with Dataview, Tag Wrangler, and other Obsidian plugins.
    Includes a `bioid` field for round-trip sync (re-import without duplicates).
    """
    title = entry.get("title", "Untitled")
    tags = entry.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    source = entry.get("source", "")
    category = entry.get("category", "misc")
    created = entry.get("created_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
    bioid = entry.get("id", "")
    module = entry.get("module", "")
    category_label = entry.get("category_label", category)
    original_file = entry.get("file", "")

    # Build YAML lines
    lines = [FRONTMATTER_DELIM]
    lines.append(f'title: "{_escape_yaml(title)}"')

    # Tags as YAML list
    if tags:
        lines.append("tags:")
        for tag in tags:
            tag_clean = tag.strip().lower().replace(" ", "-")
            if tag_clean:
                lines.append(f"  - {tag_clean}")
    else:
        lines.append("tags: []")

    if source:
        lines.append(f'source: "{_escape_yaml(source)}"')
    lines.append(f'category: "{category}"')

    # Format created date as ISO
    if "T" not in created and len(created) == 19:
        # Convert "2026-07-19 14:30:00" to "2026-07-19T14:30:00"
        created = created.replace(" ", "T", 1)
    lines.append(f"created: {created}")

    if bioid:
        lines.append(f'bioid: "{bioid}"')

    # BioDockify-specific metadata block (preserves full KB metadata for re-import)
    if module or category_label or original_file:
        lines.append("biodockify:")
        if module:
            lines.append(f'  module: "{_escape_yaml(module)}"')
        if category_label:
            lines.append(f'  category_label: "{_escape_yaml(category_label)}"')
        if original_file:
            lines.append(f'  original_file: "{_escape_yaml(original_file)}"')

    lines.append(FRONTMATTER_DELIM)
    return "\n".join(lines) + "\n"


def _escape_yaml(s: str) -> str:
    """Escape special characters for YAML string values."""
    return s.replace('"', '\\"').replace("\n", " ").replace("\r", "")


# ---------------------------------------------------------------------------
# Frontmatter parsing (Obsidian → BioDockify)
# ---------------------------------------------------------------------------

def parse_frontmatter(filepath: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from an Obsidian .md file.

    Returns a dict with: title, tags, source, category, created, bioid,
    module, category_label, original_file, content (body after frontmatter).
    Falls back gracefully if no frontmatter is present.
    """
    result = {
        "title": "",
        "tags": [],
        "source": "",
        "category": "misc",
        "created": "",
        "bioid": "",
        "module": "",
        "category_label": "",
        "original_file": "",
        "content": "",
    }

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        log.warning(f"Failed to read {filepath}: {e}")
        return result

    # Check for frontmatter
    if not text.startswith(FRONTMATTER_DELIM + "\n"):
        # No frontmatter — entire file is content
        result["content"] = text
        result["title"] = _title_from_filename(filepath)
        return result

    # Split frontmatter from body
    second_delim = text.find("\n" + FRONTMATTER_DELIM + "\n", len(FRONTMATTER_DELIM) + 1)
    if second_delim == -1:
        result["content"] = text
        result["title"] = _title_from_filename(filepath)
        return result

    fm_text = text[len(FRONTMATTER_DELIM) + 1 : second_delim]
    body = text[second_delim + len(FRONTMATTER_DELIM) + 2 :]

    result["content"] = body.strip()

    # Parse simple YAML (no external dependency)
    in_biodockify = False
    for line in fm_text.split("\n"):
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue

        if line == "biodockify:":
            in_biodockify = True
            continue

        # Indented lines under biodockify:
        if in_biodockify and line.startswith("  "):
            key, val = _parse_yaml_line(line.strip())
            if key == "module":
                result["module"] = val
            elif key == "category_label":
                result["category_label"] = val
            elif key == "original_file":
                result["original_file"] = val
            continue
        else:
            in_biodockify = False

        # Top-level keys
        if line.startswith("tags:") and "[" in line:
            # Inline list: tags: [docking, molecular-docking]
            val = line.split(":", 1)[1].strip()
            result["tags"] = [t.strip().strip('"').strip("'")
                              for t in val.strip("[]").split(",") if t.strip()]
        elif line.startswith("  - ") and not in_biodockify:
            # List item under tags:
            tag = line.strip().lstrip("- ").strip()
            if tag:
                result["tags"].append(tag)
        else:
            key, val = _parse_yaml_line(line)
            if key == "title":
                result["title"] = val
            elif key == "source":
                result["source"] = val
            elif key == "category":
                result["category"] = val
            elif key == "created":
                result["created"] = val
            elif key == "bioid":
                result["bioid"] = val

    # Fallback title
    if not result["title"]:
        result["title"] = _title_from_filename(filepath)

    return result


def _parse_yaml_line(line: str) -> tuple:
    """Parse a simple YAML key: value line. Returns (key, value_str)."""
    if ":" not in line:
        return ("", line)
    key, val = line.split(":", 1)
    val = val.strip().strip('"').strip("'")
    return (key.strip(), val)


def _title_from_filename(filepath: str) -> str:
    """Derive a title from a filename."""
    name = os.path.splitext(os.path.basename(filepath))[0]
    # Convert underscores/hyphens to spaces
    return name.replace("_", " ").replace("-", " ").title()


# ---------------------------------------------------------------------------
# Export: BioDockify → Obsidian
# ---------------------------------------------------------------------------

def export_to_vault(
    entries: List[Dict[str, Any]],
    vault_path: str = DEFAULT_VAULT_PATH,
) -> Dict[str, Any]:
    """Export KB entries to an Obsidian vault directory.

    Each entry is written as a .md file with Obsidian-standard YAML frontmatter,
    organized into category subdirectories.

    Args:
        entries: List of KB entry dicts (from index.json).
        vault_path: Path to the Obsidian vault directory.

    Returns:
        {exported: int, skipped: int, errors: [{file, error}]}
    """
    exported = 0
    skipped = 0
    errors = []

    for entry in entries:
        try:
            category = entry.get("category", "misc")
            title = entry.get("title", "Untitled")
            source_file = entry.get("file", "")

            if not source_file or not os.path.isfile(source_file):
                errors.append({"file": source_file, "error": "source file not found"})
                skipped += 1
                continue

            # Read the KB .md file content
            with open(source_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Strip the existing BioDockify header (# Title, **Tags:**, **Source:**)
            content = _strip_kb_header(content)

            # Generate frontmatter
            fm = generate_frontmatter(entry, content)

            # Build vault path
            cat_dir = os.path.join(vault_path, category)
            os.makedirs(cat_dir, exist_ok=True)

            safe_title = _sanitize_filename(title)
            vault_file = os.path.join(cat_dir, f"{safe_title}.md")

            # Write to vault
            with open(vault_file, "w", encoding="utf-8") as f:
                f.write(fm)
                f.write("\n")
                f.write(content)

            exported += 1

        except Exception as e:
            errors.append({"file": entry.get("file", "?"), "error": str(e)})
            skipped += 1

    log.info(f"Obsidian export: {exported} exported, {skipped} skipped, {len(errors)} errors")
    return {"exported": exported, "skipped": skipped, "errors": errors}


def _strip_kb_header(content: str) -> str:
    """Strip the BioDockify KB header from a .md file.

    KB .md files start with: # Title, **Tags:** ..., **Source:** ..., then content.
    We strip this because the frontmatter replaces it.
    """
    lines = content.split("\n")
    i = 0
    # Skip # Title line
    if lines and lines[0].startswith("# "):
        i = 1
    # Skip blank lines and **Tags:**/**Source:** lines
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("**Tags:**") or line.startswith("**Source:**"):
            i += 1
            continue
        break
    return "\n".join(lines[i:]).strip()


def _sanitize_filename(title: str) -> str:
    """Sanitize a title for use as a filename."""
    safe = "".join(c for c in title if c.isalnum() or c in " _-").strip()
    safe = safe.replace(" ", "_")[:80]
    return safe if safe else f"entry_{int(time.time())}"


# ---------------------------------------------------------------------------
# Import: Obsidian → BioDockify
# ---------------------------------------------------------------------------

def import_from_vault(
    vault_path: str = DEFAULT_VAULT_PATH,
    kb_root: str = KB_ROOT,
    kb_index_path: str = KB_INDEX,
) -> Dict[str, Any]:
    """Import .md files from an Obsidian vault into the BioDockify KB.

    Scans the vault directory recursively for .md files. For each file:
    - Parses YAML frontmatter to extract metadata
    - If `bioid` matches an existing KB entry, updates it
    - Otherwise, creates a new KB entry

    Args:
        vault_path: Path to the Obsidian vault directory.
        kb_root: BioDockify KB root directory.
        kb_index_path: Path to index.json.

    Returns:
        {imported: int, updated: int, skipped: int, errors: [{file, error}]}
    """
    if not os.path.isdir(vault_path):
        return {"imported": 0, "updated": 0, "skipped": 0,
                "errors": [{"file": vault_path, "error": "vault directory not found"}]}

    imported = 0
    updated = 0
    skipped = 0
    errors = []

    # Load existing index for bioid lookup
    index = _load_index(kb_index_path)
    bioid_map = {e.get("id"): e for e in index.get("entries", []) if e.get("id")}

    # Scan vault for .md files
    for root, dirs, files in os.walk(vault_path):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            filepath = os.path.join(root, fname)

            try:
                parsed = parse_frontmatter(filepath)
                content = parsed.get("content", "")
                if not content.strip():
                    skipped += 1
                    continue

                bioid = parsed.get("bioid", "")
                category = parsed.get("category", "misc")
                title = parsed.get("title", _title_from_filename(filepath))
                source = parsed.get("source", "Obsidian")
                tags = parsed.get("tags", [])
                tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)

                if bioid and bioid in bioid_map:
                    # Update existing entry
                    _update_entry(bioid, content, kb_root, kb_index_path)
                    updated += 1
                else:
                    # Create new entry — use auto_store pattern
                    cat_dir = os.path.join(kb_root, category)
                    os.makedirs(cat_dir, exist_ok=True)

                    safe_title = _sanitize_filename(title)
                    new_file = os.path.join(cat_dir, f"{safe_title}.md")

                    # Write .md with BioDockify header
                    with open(new_file, "w", encoding="utf-8") as f:
                        f.write(f"# {title}\n\n")
                        if tags_str:
                            f.write(f"**Tags:** {tags_str}\n\n")
                        f.write(f"**Source:** {source}\n\n")
                        f.write(content)

                    # Add to index
                    entry = {
                        "id": f"{category}_{len(index.get('entries', []))}",
                        "title": title,
                        "category": category,
                        "category_label": category.replace("_", " ").title(),
                        "tags": tags if isinstance(tags, list) else [],
                        "source": source,
                        "file": new_file,
                        "docx_file": None,
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "size": len(content),
                    }
                    index.setdefault("entries", []).append(entry)
                    imported += 1

            except Exception as e:
                errors.append({"file": filepath, "error": str(e)})
                skipped += 1

    # Save updated index
    _save_index(index, kb_index_path)

    log.info(f"Obsidian import: {imported} new, {updated} updated, {skipped} skipped")
    return {"imported": imported, "updated": updated, "skipped": skipped, "errors": errors}


def _update_entry(bioid: str, content: str, kb_root: str, kb_index_path: str):
    """Update an existing KB entry's content by bioid."""
    index = _load_index(kb_index_path)
    for entry in index.get("entries", []):
        if entry.get("id") == bioid:
            filepath = entry.get("file", "")
            if filepath and os.path.isfile(filepath):
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f'# {entry.get("title", "Untitled")}\n\n')
                    tags = entry.get("tags", [])
                    if tags:
                        f.write(f'**Tags:** {", ".join(tags)}\n\n')
                    f.write(f'**Source:** {entry.get("source", "")}\n\n')
                    f.write(content)
                entry["size"] = len(content)
                _save_index(index, kb_index_path)
            break


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def get_vault_status(vault_path: str = DEFAULT_VAULT_PATH) -> Dict[str, Any]:
    """Get the status of the Obsidian vault directory.

    Returns: {exists, file_count, categories, last_modified, path}
    """
    if not os.path.isdir(vault_path):
        return {
            "exists": False,
            "file_count": 0,
            "categories": [],
            "last_modified": None,
            "path": vault_path,
        }

    file_count = 0
    categories = set()
    last_modified = 0

    for root, dirs, files in os.walk(vault_path):
        for fname in files:
            if fname.endswith(".md"):
                file_count += 1
                fpath = os.path.join(root, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                    if mtime > last_modified:
                        last_modified = mtime
                except Exception:
                    pass

        # Category = immediate subdirectory of vault root
        rel = os.path.relpath(root, vault_path)
        if rel != "." and os.sep not in rel:
            categories.add(rel)

    return {
        "exists": True,
        "file_count": file_count,
        "categories": sorted(categories),
        "last_modified": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(last_modified))
        if last_modified else None,
        "path": vault_path,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_index(path: str = KB_INDEX) -> Dict[str, Any]:
    """Load the KB index.json."""
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"entries": [], "categories": {}}


def _save_index(index: Dict[str, Any], path: str = KB_INDEX):
    """Save the KB index.json."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
