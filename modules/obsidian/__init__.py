"""
BioDockify ↔ Obsidian Integration

Bidirectional file sync between BioDockify Knowledge Base and Obsidian vault.
Manual sync (button click), Obsidian-standard YAML frontmatter, configurable
vault path (Docker volume default, optional host bind mount).

Public API:
    export_to_vault    — send KB entries to Obsidian vault as .md with frontmatter
    import_from_vault  — pull Obsidian .md files into BioDockify KB
    get_vault_status   — file count, last sync, conflicts
    generate_frontmatter — Obsidian-standard YAML for a KB entry
    parse_frontmatter  — extract metadata from an Obsidian .md file

Pharma relevance: Obsidian is widely used by PhD researchers for literature
notes, reading lists, and thesis drafting. This integration lets them keep
their Obsidian workflow while BioDockify handles the heavy computational
research (docking, ADMET, statistics, claim verification).
"""

from .sync import (
    export_to_vault,
    import_from_vault,
    get_vault_status,
    generate_frontmatter,
    parse_frontmatter,
)

__all__ = [
    "export_to_vault",
    "import_from_vault",
    "get_vault_status",
    "generate_frontmatter",
    "parse_frontmatter",
]
