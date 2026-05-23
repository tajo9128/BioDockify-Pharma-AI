# Avant-Garde Molecule Editor — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace basic SMILES text input with a full-featured molecular editor: JSME drawing canvas, 3Dmol.js viewer, real-time property panel, PubChem search, multi-format export, recent history.

**Architecture:** JSME self-hosted in `webui/vendor/jsme/`. SMILES syncs bidirectionally between JSME canvas and text input. Backend RDKit APIs handle 3D conformer, export, PubChem. 3Dmol.js CDN on-demand. All nb-panel design system + ApiHandler pattern.

**Constraint:** ZERO changes to agent.py, helpers/, plugins/, prompts/, index.html.

---

## File Manifest

| Action | File | Lines |
|--------|------|-------|
| New | `api/structure_3d.py` | ~50 |
| New | `api/structure_export.py` | ~70 |
| New | `api/pubchem_lookup.py` | ~60 |
| New | `webui/vendor/jsme/jsme.nocache.js` | binary |
| Rewrite | `webui/components/molecule-editor/molecule-editor.html` | ~280 |

---

### Task 1: `api/structure_3d.py` — 3D Conformer Generator

`POST /api/structure_3d` — RDKit ETKDG+MMFF → SDF for 3Dmol.js.
Input: `{smiles: "..."}` → Output: `{success: true, sdf: "...", num_atoms: N}`

### Task 2: `api/structure_export.py` — Multi-Format Export

`POST /api/structure_export` — Export PNG/SVG/MOL/SDF.
Input: `{smiles: "...", format: "png"}` → binary download with correct mimetype.

### Task 3: `api/pubchem_lookup.py` — PubChem Name→SMILES

`POST /api/pubchem_lookup` — PubChem PUG REST API.
Input: `{query: "aspirin"}` → `{success: true, smiles: "...", cid: 2244}`

### Task 4: Download JSME library

`webui/vendor/jsme/jsme.nocache.js` — self-hosted JS editor. Starlette serves webui/ as static root.

### Task 5: Rewrite molecule-editor.html

2-column layout. Left: JSME canvas + SMILES + PubChem + Quick Load + Recent + File upload.
Right: Tabbed (3D View/Properties) + Export buttons + Send To buttons.
Store: `createStore("moleculeEditor", {...})` with JSME callbacks, 3Dmol init, property load, PubChem search, export triggers, recent history in localStorage.

### Task 6: Integration Verification

- Compile all Python files
- Verify no existing files changed
- Verify each new API file has exactly one ApiHandler
- Smoke test: load example, 3D view, properties, PubChem search, export, send to docking

### Task 7: Commit with descriptive message

---

## Non-Goals
No changes to agent.py, helpers/, plugins/, prompts/, index.html
No new Python deps (RDKit already required)
No changes to desktop-store.js or research-tools.html
