# BioDockify ↔ Obsidian Integration

> **Optional feature.** Obsidian is not required for BioDockify to work. This
> integration lets researchers who use Obsidian for notes and literature
> management sync their Knowledge Base entries to an Obsidian vault, and pull
> Obsidian notes back into BioDockify.

## What it does

| Direction | What happens |
|-----------|-------------|
| **BioDockify → Obsidian** | Selected KB entries are exported as `.md` files with Obsidian-standard YAML frontmatter, organized into category folders |
| **Obsidian → BioDockidian** | `.md` files from the vault are imported into the BioDockify KB with metadata preserved |

## Setup

### Option 1: Default Docker volume (simplest)

The vault lives at `/a0/usr/obsidian_vault/` inside the `biodockify_usr` Docker volume. No configuration needed — just click the buttons.

To access the vault from your host PC, add a bind mount in `docker-compose.yml`:

```yaml
volumes:
  - biodockify_usr:/a0/usr
  - C:/Users/biodo/MyObsidianVault:/a0/usr/obsidian_vault  # ← add this
  - biodockify_data:/a0/data
  - biodockify_a0proj:/a0/.a0proj
```

Then point Obsidian to `C:/Users/biodo/MyObsidianVault`.

### Option 2: Existing Obsidian vault (host bind mount)

If you already have an Obsidian vault on your PC, mount it directly:

```yaml
volumes:
  - biodockify_usr:/a0/usr
  - D:/MyResearchVault:/a0/usr/obsidian_vault
  - biodockify_data:/a0/data
  - biodockify_a0proj:/a0/.a0proj
```

Restart BioDockify: `docker compose down && docker compose up -d`

## Usage

### Send to Obsidian

1. Open **Knowledge Base** in BioDockify
2. Select one or more entries (checkbox on each card)
3. Click **📤 Obsidian** in the action bar
4. Files appear in your vault under category subfolders

### Pull from Obsidian

1. Open **Knowledge Base** in BioDockify
2. Click **📥 From Obsidian** in the action bar (no selection needed — imports all)
3. Files from the vault are imported into the KB with their metadata preserved

## Frontmatter Format

Exported files use Obsidian-standard YAML frontmatter:

```yaml
---
title: "Vina Docking: aspirin vs COX-2"
tags:
  - docking
  - molecular-docking
  - cox-2
source: "AutoDock Vina"
category: "docking"
created: 2026-07-19T14:30:00
bioid: "docking_42_20260719_143000"
biodockify:
  module: "docking_run"
  category_label: "Docking Results"
  original_file: "/a0/data/knowledge_base/docking/vina_docking_aspirin_cox2.md"
---

# Vina Docking: aspirin vs COX-2

(docking results content...)
```

### Frontmatter fields

| Field | Description | Obsidian compatible? |
|-------|-------------|---------------------|
| `title` | Entry title | ✅ Used by Dataview |
| `tags` | Category + custom tags | ✅ Tag Wrangler, Dataview |
| `source` | Source module/API | ✅ Dataview |
| `category` | KB category | ✅ Dataview |
| `created` | ISO timestamp | ✅ Dataview date queries |
| `bioid` | BioDockify entry ID | For round-trip sync |
| `biodockify` | Full KB metadata | Preserved for re-import |

### Dataview queries

Once your KB entries are in Obsidian, you can use the
[Dataview](https://blacksmithgu.github.io/obsidian-dataview/) plugin:

```dataview
TABLE source, category, created
FROM "docking"
SORT created DESC
```

```dataview
LIST
FROM #pharmacology
WHERE source = "BioDockify"
```

```dataview
TABLE title, source
WHERE bioid != null
SORT created DESC
LIMIT 20
```

## Vault directory structure

```
obsidian_vault/
  literature/
    paper-title-1.md
    paper-title-2.md
  docking/
    vina-docking-aspirin-cox2.md
  pharmacology/
    receptor-binding-study.md
  medicinal_chemistry/
    scaffold-analysis.md
  deep_research/
    cancer-therapy-review.md
  notes/
    research-ideas.md
```

Each KB category maps to an Obsidian folder.

## Round-trip sync

The `bioid` field enables round-trip sync:

1. **Export** KB entry → vault file gets `bioid: "docking_42_20260719_143000"`
2. You **edit** the file in Obsidian (add notes, fix formatting)
3. **Pull from Obsidian** → BioDockify finds the matching `bioid` and updates the KB entry

New files (no `bioid`) are imported as new KB entries.

## API reference

All endpoints require authentication.

### `POST /api/obsidian_sync` — Status

```json
{"action": "status"}
```

Returns:
```json
{
  "status": "ok",
  "exists": true,
  "file_count": 42,
  "categories": ["docking", "literature", "pharmacology"],
  "last_modified": "2026-07-19T14:30:00",
  "path": "/a0/usr/obsidian_vault"
}
```

### `POST /api/obsidian_sync` — Export

```json
{
  "action": "export",
  "entry_ids": ["docking_0", "literature_1"],
  "category": null
}
```

Or export all entries in a category:
```json
{"action": "export", "category": "docking"}
```

### `POST /api/obsidian_sync` — Import

```json
{"action": "import"}
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "vault directory not found" | Add a bind mount in docker-compose.yml (see Setup above) |
| Duplicate entries on import | Check if `bioid` is present in the frontmatter — it prevents duplicates |
| Tags not appearing in Obsidian | Ensure tags use lowercase with hyphens (auto-formatted on export) |
| Obsidian doesn't see new files | Click the vault refresh button in Obsidian, or restart Obsidian |
| Import skips files | Files without content (empty body after frontmatter) are skipped |
