"""
Smoke tests for the BioDockify ↔ Obsidian integration.

Tests the core sync logic (frontmatter generation, parsing, export/import)
without requiring Docker, a running container, or an actual Obsidian vault.

Run:  pytest tests/test_obsidian_sync.py -v
"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Frontmatter generation
# ---------------------------------------------------------------------------

def test_generate_frontmatter_basic():
    from modules.obsidian.sync import generate_frontmatter
    entry = {
        "id": "docking_0",
        "title": "Vina Docking: aspirin vs COX-2",
        "tags": ["docking", "molecular-docking"],
        "source": "AutoDock Vina",
        "category": "docking",
        "created_at": "2026-07-19 14:30:00",
    }
    fm = generate_frontmatter(entry)
    assert fm.startswith("---\n")
    assert fm.rstrip().endswith("---")
    assert 'title: "Vina Docking: aspirin vs COX-2"' in fm
    assert "tags:" in fm
    assert "  - docking" in fm
    assert "  - molecular-docking" in fm
    assert 'source: "AutoDock Vina"' in fm
    assert 'category: "docking"' in fm
    assert "created: 2026-07-19T14:30:00" in fm
    assert 'bioid: "docking_0"' in fm


def test_generate_frontmatter_with_biodockify_block():
    from modules.obsidian.sync import generate_frontmatter
    entry = {
        "id": "literature_5",
        "title": "Cancer therapy review",
        "tags": ["review", "oncology"],
        "source": "PubMed",
        "category": "literature",
        "created_at": "2026-07-19T10:00:00",
        "module": "literature_search",
        "category_label": "Literature & Papers",
        "file": "/a0/data/knowledge_base/literature/cancer_therapy_review.md",
    }
    fm = generate_frontmatter(entry)
    assert "biodockify:" in fm
    assert '  module: "literature_search"' in fm
    assert '  category_label: "Literature & Papers"' in fm
    assert '  original_file: "/a0/data/knowledge_base/literature/cancer_therapy_review.md"' in fm


def test_generate_frontmatter_empty_tags():
    from modules.obsidian.sync import generate_frontmatter
    entry = {"id": "notes_1", "title": "Quick note", "tags": [], "category": "notes"}
    fm = generate_frontmatter(entry)
    assert "tags: []" in fm


def test_generate_frontmatter_string_tags():
    """Tags stored as comma-separated string should be split into a list."""
    from modules.obsidian.sync import generate_frontmatter
    entry = {"id": "test_1", "title": "Test", "tags": "docking, cox-2, aspirin", "category": "docking"}
    fm = generate_frontmatter(entry)
    assert "  - docking" in fm
    assert "  - cox-2" in fm
    assert "  - aspirin" in fm


def test_generate_frontmatter_escapes_quotes():
    from modules.obsidian.sync import generate_frontmatter
    entry = {"id": "test_1", "title": 'He said "hello"', "source": "Test", "category": "misc"}
    fm = generate_frontmatter(entry)
    assert 'He said \\"hello\\"' in fm


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def test_parse_frontmatter_roundtrip():
    """Generate frontmatter, write to file, parse back — all fields preserved."""
    from modules.obsidian.sync import generate_frontmatter, parse_frontmatter
    entry = {
        "id": "docking_42",
        "title": "Vina Docking: aspirin vs COX-2",
        "tags": ["docking", "molecular-docking", "cox-2"],
        "source": "AutoDock Vina",
        "category": "docking",
        "created_at": "2026-07-19 14:30:00",
        "module": "docking_run",
        "category_label": "Docking Results",
        "file": "/a0/data/knowledge_base/docking/vina_docking_aspirin_cox2.md",
    }
    fm = generate_frontmatter(entry)
    body = "## Results\n\nBinding energy: -8.5 kcal/mol\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(fm)
        f.write("\n")
        f.write(body)
        tmppath = f.name

    try:
        parsed = parse_frontmatter(tmppath)
        assert parsed["title"] == "Vina Docking: aspirin vs COX-2"
        assert "docking" in parsed["tags"]
        assert "molecular-docking" in parsed["tags"]
        assert parsed["source"] == "AutoDock Vina"
        assert parsed["category"] == "docking"
        assert parsed["bioid"] == "docking_42"
        assert parsed["module"] == "docking_run"
        assert "Binding energy" in parsed["content"]
    finally:
        os.unlink(tmppath)


def test_parse_frontmatter_no_frontmatter():
    """Files without frontmatter should return content as-is with filename-derived title."""
    from modules.obsidian.sync import parse_frontmatter
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# My Research Notes\n\nSome content here.\n")
        tmppath = f.name

    try:
        parsed = parse_frontmatter(tmppath)
        assert parsed["title"]  # derived from filename
        assert "Some content here" in parsed["content"]
        assert parsed["bioid"] == ""  # no frontmatter
    finally:
        os.unlink(tmppath)


def test_parse_frontmatter_inline_tags():
    """Tags as inline list: tags: [docking, cox-2]"""
    from modules.obsidian.sync import parse_frontmatter
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write('---\ntitle: "Test"\ntags: [docking, cox-2]\ncategory: "docking"\n---\n\nBody.\n')
        tmppath = f.name

    try:
        parsed = parse_frontmatter(tmppath)
        assert "docking" in parsed["tags"]
        assert "cox-2" in parsed["tags"]
    finally:
        os.unlink(tmppath)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def test_export_to_vault_creates_files():
    from modules.obsidian.sync import export_to_vault, _sanitize_filename

    with tempfile.TemporaryDirectory() as kb_dir, tempfile.TemporaryDirectory() as vault_dir:
        # Create a fake KB .md file
        cat_dir = os.path.join(kb_dir, "docking")
        os.makedirs(cat_dir)
        md_file = os.path.join(cat_dir, "aspirin_cox2.md")
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("# Vina Docking: aspirin vs COX-2\n\n**Tags:** docking\n\n**Source:** AutoDock Vina\n\nResults here.\n")

        entries = [{
            "id": "docking_0",
            "title": "Vina Docking: aspirin vs COX-2",
            "tags": ["docking"],
            "source": "AutoDock Vina",
            "category": "docking",
            "created_at": "2026-07-19 14:30:00",
            "file": md_file,
        }]

        result = export_to_vault(entries, vault_dir)
        assert result["exported"] == 1
        assert result["skipped"] == 0
        assert len(result["errors"]) == 0

        # Verify vault file exists
        vault_file = os.path.join(vault_dir, "docking", _sanitize_filename("Vina Docking: aspirin vs COX-2") + ".md")
        assert os.path.isfile(vault_file)

        # Verify content has frontmatter
        with open(vault_file, encoding="utf-8") as f:
            content = f.read()
        assert content.startswith("---\n")
        assert "Results here" in content


def test_export_to_vault_skips_missing_files():
    from modules.obsidian.sync import export_to_vault

    with tempfile.TemporaryDirectory() as vault_dir:
        entries = [{"id": "x_0", "title": "Missing", "file": "/nonexistent/file.md", "category": "misc"}]
        result = export_to_vault(entries, vault_dir)
        assert result["exported"] == 0
        assert result["skipped"] == 1
        assert len(result["errors"]) == 1


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def test_import_from_vault_creates_kb_entries():
    from modules.obsidian.sync import import_from_vault

    with tempfile.TemporaryDirectory() as vault_dir, \
         tempfile.TemporaryDirectory() as kb_dir:

        # Create a fake Obsidian .md file with frontmatter
        cat_dir = os.path.join(vault_dir, "literature")
        os.makedirs(cat_dir)
        obs_file = os.path.join(cat_dir, "my_paper.md")
        with open(obs_file, "w", encoding="utf-8") as f:
            f.write('---\ntitle: "My Paper"\ntags:\n  - pharmacology\n  - review\nsource: "Obsidian"\ncategory: "literature"\ncreated: 2026-07-19T10:00:00\n---\n\n# My Paper\n\nContent from Obsidian.\n')

        index_path = os.path.join(kb_dir, "index.json")
        result = import_from_vault(vault_dir, kb_dir, index_path)
        assert result["imported"] == 1
        assert result["skipped"] == 0

        # Verify KB file was created
        kb_file = os.path.join(kb_dir, "literature", "My_Paper.md")
        assert os.path.isfile(kb_file)

        # Verify index was updated
        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)
        assert len(index["entries"]) == 1
        assert index["entries"][0]["title"] == "My Paper"


def test_import_from_vault_nonexistent_dir():
    from modules.obsidian.sync import import_from_vault

    with tempfile.TemporaryDirectory() as kb_dir:
        index_path = os.path.join(kb_dir, "index.json")
        result = import_from_vault("/nonexistent/vault", kb_dir, index_path)
        assert result["imported"] == 0
        assert len(result["errors"]) == 1
        assert "not found" in result["errors"][0]["error"]


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def test_get_vault_status_nonexistent():
    from modules.obsidian.sync import get_vault_status
    status = get_vault_status("/nonexistent/vault")
    assert status["exists"] is False
    assert status["file_count"] == 0


def test_get_vault_status_populated():
    from modules.obsidian.sync import get_vault_status

    with tempfile.TemporaryDirectory() as vault_dir:
        # Create some .md files in category subdirs
        for cat in ["docking", "literature", "pharmacology"]:
            d = os.path.join(vault_dir, cat)
            os.makedirs(d)
            with open(os.path.join(d, f"test_{cat}.md"), "w") as f:
                f.write(f"# Test {cat}\n")

        status = get_vault_status(vault_dir)
        assert status["exists"] is True
        assert status["file_count"] == 3
        assert set(status["categories"]) == {"docking", "literature", "pharmacology"}
        assert status["last_modified"] is not None


# ---------------------------------------------------------------------------
# API handler contract
# ---------------------------------------------------------------------------

def test_obsidian_sync_handler_has_required_methods():
    """The ApiHandler loader requires process() and requires_auth()."""
    import ast
    path = PROJECT_ROOT / "api" / "obsidian_sync.py"
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    cls = [n for n in tree.body
           if isinstance(n, ast.ClassDef) and n.name == "ObsidianSyncHandler"][0]
    methods = {n.name for n in cls.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for required in ("process", "requires_auth", "_status", "_export", "_import", "_configure"):
        assert required in methods, f"ObsidianSyncHandler missing: {required}"


def test_obsidian_sync_handler_unknown_action_returns_error():
    """Unknown actions must return a structured error."""
    import ast
    path = PROJECT_ROOT / "api" / "obsidian_sync.py"
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "Unknown action" in src, "Must return structured error for unknown actions"


# ---------------------------------------------------------------------------
# KB header stripping
# ---------------------------------------------------------------------------

def test_strip_kb_header():
    from modules.obsidian.sync import _strip_kb_header
    content = "# My Title\n\n**Tags:** docking, cox-2\n\n**Source:** AutoDock Vina\n\nActual content here.\n"
    stripped = _strip_kb_header(content)
    assert "Actual content here" in stripped
    assert "# My Title" not in stripped
    assert "**Tags:**" not in stripped
    assert "**Source:**" not in stripped


def test_strip_kb_header_no_header():
    from modules.obsidian.sync import _strip_kb_header
    content = "Just plain content.\n"
    stripped = _strip_kb_header(content)
    assert "Just plain content" in stripped
