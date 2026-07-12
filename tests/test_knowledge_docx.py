import os
import json
import time
import tempfile
import shutil


# Self-contained reproduction of _store_docx_entry logic (for testing without api deps)

KB_DIR = tempfile.mkdtemp()
CATEGORIES = {"literature": "Literature"}

os.makedirs(KB_DIR, exist_ok=True)
with open(os.path.join(KB_DIR, "index.json"), "w") as f:
    json.dump({"entries": [], "categories": {}}, f)


def _load_index():
    with open(os.path.join(KB_DIR, "index.json"), "r") as f:
        return json.load(f)


def _save_index(index):
    with open(os.path.join(KB_DIR, "index.json"), "w") as f:
        json.dump(index, f, indent=2)


def _store_docx_entry(category, title, docx_bytes, tags="", source="", metadata=None):
    import time as _time

    cat_dir = os.path.join(KB_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)

    safe_title = "".join(c for c in title[:80] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    if not safe_title:
        safe_title = f"entry_{int(_time.time())}"
    filepath = os.path.join(cat_dir, f"{safe_title}.docx")

    counter = 1
    while os.path.exists(filepath):
        filepath = os.path.join(cat_dir, f"{safe_title}_{counter}.docx")
        counter += 1

    with open(filepath, "wb") as f:
        f.write(docx_bytes)

    index = _load_index()
    entry = {
        "id": f"{category}_{len(index['entries'])}",
        "title": title,
        "category": category,
        "category_label": CATEGORIES.get(category, category),
        "tags": tags.split(",") if tags else [],
        "source": source,
        "file": filepath,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "size": len(docx_bytes),
        "format": "docx",
    }
    if metadata:
        entry["metadata"] = metadata
    index["entries"].append(entry)
    index["categories"][category] = index["categories"].get(category, 0) + 1
    _save_index(index)
    return entry


# --- Tests ---

def test_store_docx_entry():
    docx_bytes = b"PK\x03\x04fake_docx_content_for_test"
    entry = _store_docx_entry(
        category="literature",
        title="Test DOCX Article",
        docx_bytes=docx_bytes,
        tags="test,demo",
        source="PubMed",
        metadata={"doi": "10.1234/test"},
    )

    assert entry["category"] == "literature"
    assert entry["title"] == "Test DOCX Article"
    assert entry["format"] == "docx"
    assert entry["size"] == len(docx_bytes)
    assert os.path.exists(entry["file"])
    assert entry["file"].endswith(".docx")

    with open(entry["file"], "rb") as f:
        assert f.read() == docx_bytes


def test_store_docx_entry_duplicate_title():
    entry1 = _store_docx_entry("literature", "Duplicate Article", b"PK_first", source="PubMed")
    entry2 = _store_docx_entry("literature", "Duplicate Article", b"PK_second", source="Semantic Scholar")

    assert entry1["file"] != entry2["file"]
    assert entry1["title"] == entry2["title"] == "Duplicate Article"


def test_store_docx_entry_no_tags():
    entry = _store_docx_entry("literature", "Simple", b"PK_simple")
    assert entry["tags"] == []
    assert entry["source"] == ""


if __name__ == "__main__":
    test_store_docx_entry()
    test_store_docx_entry_duplicate_title()
    test_store_docx_entry_no_tags()
    print("All tests PASS")

    shutil.rmtree(KB_DIR, ignore_errors=True)
