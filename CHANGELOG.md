# Changelog

All notable changes to BioDockify Pharma AI.

## [v7.5.2] - 2026-07-18

### Stability Sprints (5 sprints, 30+ files changed)

#### Security (Sprint 1)
- CORS `allow_origins=["*"]` → localhost-only whitelist
- Unauthenticated backup/RFC/chat reset/terminate → all require auth
- File upload whitelist (35 safe extensions)
- Upload size limits: 50MB/file, 200MB total
- ZIP path traversal protection (rejects `..` sequences)
- CSP `unsafe-eval` removed from script-src
- `.gitignore` updated: `data/knowledge_base/` excluded

#### Backend Hardening (Sprint 2)
- Blocking `subprocess.run` wrapped in `asyncio.to_thread()` (docking_run.py, health.py)
- `time.sleep` → `await asyncio.sleep` in async handlers (mcp_servers_apply.py)
- RAG routes no longer expose raw exception details to API clients
- 10+ bare `except:` clauses fixed with proper `Exception as e` + logging
- psutil version conflict fixed (==5.9.8 → >=7.0.0)
- Duplicate pandas entry removed from requirements
- 8 unused imports removed (Response, json, pickle, threading, base64)

#### Frontend Fixes (Sprint 3)
- Broken `register-pipeline.js` path: `research-command-center` → `research-dashboard`
- Broken `register-qsar.js` path: `qsar/qsar.html` → `qsar3d/qsar3d.html`
- PPTX download: `ppt_generate` → `ppt_master` (endpoint was renamed)
- Duplicate `loadLibraryFromKB()` merged into single function
- Duplicate `selectAll()` renamed to `toggleSelectAll()` to avoid overwrite

#### Docker Hardening (Sprint 4)
- `.dockerignore`: keep `bun.lock` for reproducible Dockerfile builds
- `supervisord.conf`: socket permissions `0777` → `0770` (security)
- `health.py`: version field added from `version_info.txt`

#### Version & Documentation (Sprint 5)
- Version bumped to v7.5.2 across all files
- Frontend version display fixed (sidebar-bottom-store, welcome-screen, welcome-store)
- `ARCHITECTURE.md` rewritten to match actual codebase (was describing wrong Tauri/React/Rust stack)
- `AGENTS.md` updated with sprint history
- Backup system verified: 447KB backups with all 3 data locations captured

## [v7.5.1] - 2026-07-18
### Backup & Recovery — Bulletproof
- Fixed: every existing backup was 0.0 MB empty (3 years of PhD research not captured)
- All 3 data locations now captured: /a0/usr, /a0/.a0proj, /a0/data
- Backups visible on PC via host bind mount
- "Save to PC" button: real download flow (fetch → blob → browser download)
- "Restore from PC" button: upload .zip → auto-restore
- Daily auto-backup at 3 AM + on container start

### Research Pipeline — Complete
- 7 new tool prompts for research modules (literature, deep_research, docking, md_lite, stats, admet, drug_analysis)
- Academic Writer now loads KB sources by category with 100K char budget
- Knowledge Base: Open Notebook LM features (notebooks, notes, transformations, podcast)
- PubMed crash fixed (_batch_resolve_pmcids was never defined)
- 800-char abstract truncation removed

### Department Modules
- 7 department modules added (Pharmacology, Medicinal Chemistry, Formulation, Clinical, Pharma Analysis, Natural Products, Regulatory)
- All 8 pharmacy departments now have dedicated modules
- Each module auto-stores results to Knowledge Base

## [v7.0.6] - 2026-06-15
### Agent Zero v2.0 Core
- LiteLLM transport layer merged
- Parallel tool calling + OpenAI Responses API support
- Security-pinned dependencies

## [v6.9.5] - 2026-06-10
### Frontend Audit & Merge
- **14-module desktop**: Knowledge Base + Notebook merged into 5-tab panel
- Knowledge Base: Notebook doc cards, Chat with KB, Library, Podcast (TTS), Notes
- Removed: standalone Notebook, Patent Search, Clinical Trials, Benchmark

### New Features
- Knowledge Base: NotebookLM-style paper cards with full-paper reader on click
- Faculty CMD: Questions tab — MCQ, short, long, true/false with Bloom's taxonomy
- Statistics: auto-analyze mode (one-click descriptive + correlation + group + normality)
- Statistics: fixed file upload (DOM attachment), missing runTransform, sample rawData

### Docker
- Port mapping simplified to `80:80` → `http://localhost`
- Backup folder mount instructions added

## [v6.9.2] - 2026-06-02
### Research & Academic Management
- 5 department configs (Pharma Chemistry, Pharmacognosy, Pharmacology, Pharmaceutics, Clinical Pharmacy)
- Faculty CMD: 8 tabs (syllabus, lectures, assignments, semester, lesson, notes, slides, plagiarism)
- Knowledge Base: 18 categories, multi-format, auto-detect, document chunking, knowledge graph

## [v6.8.7] - 2026-05-31
### MM-GBSA + Fixes
- MM-GBSA free energy scoring (replaces ODDT/GNINA)
- External docking file upload
- Drug Analysis renamed, crash fixes, Docker package updates

## [v6.8.1] - 2026-05-25
### Docking & Analysis
- Meeko pure-Python PDB→PDBQT conversion (cross-platform, no obabel needed)
- Consensus Z-score scoring: Vina + MM-GBSA combined into single normalized score
- Inline 3D docking analysis: receptor+ligand viewer with H-bonds, surface, snapshot
- Best pose 2D SVG diagram + 3D PDB download

### Module Consolidation (29 → 15 toolbar icons)
- 11 modules merged into parent dashboards as tabs
- Drug Properties, Drug Analysis, Mol Optimizer → Molecule Editor (4 tabs)
- Slides, Lecture Builder → Faculty CMD
- Literature, Wet Lab → Research CMD
- Grant Writer, Regulatory, Citation Manager → Academic Writer (8 tabs)
- Docking Analysis inline in Molecular Toolkit
- Browser, Editor removed (non-functional)

### Drug Properties v2
- hERG cardiotoxicity (10 SMARTS alerts)
- AMES mutagenicity (15 alerts, Kazius-Hansen)
- pKa prediction (acidic + basic, 16 substructure patterns)
- BBB permeability score (Clark's model, 0-1 continuous)
- Melting Point (Joback group contributions)
- Drug-likeness Score (0-1 weighted composite)

### QSAR v2
- Classification models: RFC, SVC, LogisticRegression
- Batch prediction with AD status per compound
- Train/test split with external validation
- Feature selection (mutual info, ANOVA F-test)
- Read-across: ECFP4 Tanimoto analogues
- Williams Plot: SVG leverage vs residuals
- PLS VIP scores, feature importance extraction
- Full-width UI redesign

### Journal Finder Upgrade
- Deep research: 5 live source web scraping (PubMed, SCImago, DOAJ, Google Scholar, Researcher.life)
- Fake website detector: 6 checks (domain, TLD, ISSN registry, Crossref, domain age)
- Full dossier: access model, APC, license, time-to-publish, Scholar h5-index
- Research pipeline trigger via ResearchOrchestrator

### Pharmacophore Overhaul
- 13 actions; protein-based pharmacophore; PharmacoNet 10-class NCI; ZINCPharmer batch; LigandScout .ph4

### Molecule Editor 3D Viewer
- PDB protein viewer with cartoon + chain coloring
- Click-to-measure distances, residue sequence strip
- 7 rendering styles (CPK, Chain, Charge, Surface), snapshot

### Frontend Redesigns
- Journal Finder, Pharmacophore, QSAR: boxes+buttons style
- QSAR all tabs full-width
- All Tools grid: 16 live cards with subtask labels
- Welcome screen: force chat mode on first login (no empty split view)

### Bug Fixes
- 18 bugs fixed across 15 files (systematic debug)
- PDBQT sanitize-before-validate fix (Vina non-AD4 types)
- Docking analysis TypeError (sorted dicts + key mismatches)
- Molecule editor: Properties tab not loading, 3D view stuck, Alpine v3 debounce, sendTo selectors, x-create→x-init, missing catch
- Health badges: platform-aware (Docker=green, Windows=yellow)
- GNINA fallback scoring when binary missing

### Cleanup
- 9 extension registration files removed
- Redundant drug-properties JS removed
- All merged modules verified accessible from parent dashboards

## [v5.7.1] - 2026-05-15
### Added
- System Health dashboard: Internet, ChromaDB, RDKit, Disk, Memory monitoring
- Feature fallback status panel (TTS, Drug Properties, Literature)
- GDrive cloud backup UI in Backup module
- `system_health` API wiring connection_doctor + system_doctor + guardian
### Fixed
- LICENSE merge conflict markers removed

## [v5.7.0] - 2026-05-15
### Fixed
- 6 critical frontend bugs: Alpine.js `{{ }}` syntax, duplicate `clear()`, taskbar double-minimize, setInterval leak, stray `</template>`
- Null-safety guards added to 10 modules ($store?. references)
- CSS: 106-line duplicate tooltip block removed, 4 missing CSS variables defined
- Backend: logging added to drug_properties, literature_search (3 backends), kokoro_tts
- Kokoro TTS model cached as singleton (was created per-request)
- Literature arXiv fixed to HTTPS, timeouts improved
### Security
- Dockerfile: EXPOSE 50001, HEALTHCHECK every 30s

## [v5.6.4] - 2026-05-15
### Added
- Agent Zero constitution with 7 governing principles
- Proactive module monitoring (15 modules, 30-minute intervals)
- Self-healing protocol: detect → diagnose → repair → verify → log
- Aggressive research protocol with 8-item exhaustion checklist
- 15-module registry + 4 sub-agent registry in identity.md

## [v5.6.3] - 2026-05-15
### Added
- Molecular Toolkit module: ADMET prediction, Tanimoto similarity, chemical space PCA
- Wired 3 previously unwired APIs: admet_predict, molecular_similarity, chemical_space
### Audit
- Full codebase audit: 29 files changed from v4.7.7, zero Agent Zero core touched

## [v5.6.2] - 2026-05-15
### Added
- Cross-module integration: Research Dashboard → Academic Writer, Notebook → Academic Writer
- Export Research Report from Research Dashboard (pipeline + milestones + wet lab)
- Save to Notebook from Statistics results

## [v5.6.1] - 2026-05-15
### Added
- Research Notebook upgrade: tag system, favorites, knowledge graph (canvas force-directed)
- Save to Notebook button in Literature search results
- Rich entry cards with source attribution, date, entry tags

## [v5.6.0] - 2026-05-15
### Added
- Research Command Center: 4-tab dashboard (Projects, Pipeline, Milestones, Wet Lab)
- Wired to 23 existing backend API endpoints (zero new backend)
- Auto-start comprehensive research from PhD title input
- Gantt-style milestone progress tracking

## [v5.5.5] - 2026-05-15
### Added
- Session persistence (localStorage) for Statistics, Drug Properties, Literature, Academic Writer
### Fixed
- Desktop-store module ordering (duplicate order numbers resolved)

## [v5.5.4] - 2026-05-15
### Added
- 5-tab Academic Writer: Literature Review, Research Paper, Thesis, Lecture, Slides
- Kokoro TTS integration with 3-tier fallback (Kokoro → Edge-TTS → Browser)

## [v5.5.3] - 2026-05-15
### Added
- Slides Generator with style/ slide count options
- Lecture Builder with duration/level selection
- Wet Lab Manager with 3-tab interface
- Literature module with PubMed/Semantic Scholar/arXiv search

## [v5.5.2] - 2026-05-15
### Added
- Drug Properties module with SMILES input, property table, Lipinski Rule-of-5
- Literature multi-database search API (PubMed, Semantic Scholar, arXiv)

## [v5.5.1] - 2026-05-15
### Added
- Statistics module rebuild: replaced prompt() dialogs with proper dropdowns
- Download CSV/JSON buttons, data preview, agent-help buttons
- Test-type dropdown selector with parameter forms per analysis type

## [v5.5.0] - 2026-05-15
### Added
- 3-mode layout: Chat, Split-pane (chat + desktop), Full Desktop
- Resizable split divider between chat and desktop
- Right-side icon rail with 13 module launchers
- Right-canvas restored as overlay in chat panel
### Fixed
- #desktop-wrapper moved inside .container (CSS selectors now match)
- Duplicate CSS blocks removed from desktop-workspace.css
