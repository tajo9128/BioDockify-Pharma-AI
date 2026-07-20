# Changelog

All notable changes to BioDockify Pharma AI.

## [v7.6.2] - 2026-07-19

### Fix: Bonsai model bundled via RUN curl (CI-compatible)

v7.6.1 used `COPY Bonsai-8B-Q1_0.gguf` in the Dockerfile, but the model file
is in `.gitignore` (too large for git), so CI could never build the image —
the build step failed with "file not found" because the file wasn't in the
GitHub Actions checkout.

Fix: download the model from HuggingFace **inside the Dockerfile** via
`RUN curl`. The model is baked into an image layer at
`/opt/llama-server/models/Bonsai-8B-Q1_0.gguf` — same end result (bundled,
no runtime download), but works in CI without bloating the git repo or
requiring Git LFS (which has a 1 GB free quota).

#### What changed
- **Dockerfile.release**: replaced `COPY Bonsai-8B-Q1_0.gguf` with
  `RUN curl -L -o /opt/llama-server/models/Bonsai-8B-Q1_0.gguf <HF URL>`.
  Model downloads once during build, then is cached in the image layer.
- **Tests**: `test_dockerfile_bundles_bonsai_model` updated to verify
  the RUN curl + HF URL + destination path instead of COPY.
- **46/46 tests pass.**

#### Image size impact
- Image grows by ~1.1 GB during build (the model layer)
- Final image: ~14.8 GB (llama-server + Bonsai-8B model + BioDockify)

## [v7.6.1] - 2026-07-19

### Bonsai-8B model bundled inside Docker image — no download needed

The Bonsai-8B model (1.1 GB) is now **bundled inside the Docker image** at
`/opt/llama-server/models/Bonsai-8B-Q1_0.gguf`. No auto-download on first
run — the model is ready immediately when the container starts.

#### What changed
- **Dockerfile.release**: `COPY Bonsai-8B-Q1_0.gguf /opt/llama-server/models/`
  — model is baked into the image during build.
- **Supervisord config**: `MODEL_PATH=/opt/llama-server/models/Bonsai-8B-Q1_0.gguf`
- **exe/init_and_run_llama.sh**: simplified — just verifies model exists and
  starts llama-server. No download logic.
- **exe/init_bonsai.sh**: simplified — just verifies bundled model exists.
- **modules/local_llm/manager.py**: `SIDECAR_MODEL_PATH=/opt/llama-server/models`
- **modules/local_llm/models.json**: added `local_path` and `bundled_in_image` fields.
- **Docs**: removed all "auto-downloads on first run" language.
- **Tests**: updated to reflect bundled model path. 46/46 pass.

#### Image size impact
- Before: ~13.7 GB (no model bundled)
- After: ~14.8 GB (model bundled, +1.1 GB)

#### Student experience
1. `docker compose up -d`
2. Open http://localhost
3. Select preset "BioDockify AI Engine — Local (Bonsai-8B)"
4. Send a test message — works immediately, no waiting for download

## [v7.6.0] - 2026-07-19

### Graphify Knowledge Graph — AI agents can now understand the entire codebase

Added [Graphify](https://github.com/Graphify-Labs/graphify) to generate a
queryable knowledge graph of the BioDockify codebase. AI agents (ZCode, Claude,
Cursor, Copilot, etc.) can now traverse the graph to understand code structure,
find relationships between modules, and answer questions about the codebase
without reading every file.

#### What Graphify does
- Converts code into a knowledge graph using **tree-sitter AST parsing**
  (local, no LLM, nothing leaves your machine)
- 40,327 nodes, 75,663 edges, 2,915 communities
- 91% EXTRACTED (from AST), 9% INFERRED (derived relationships)
- Covers all Python, JavaScript, HTML, CSS, YAML, JSON, Shell files
- Token cost: 0 (code-only mode, no API key needed)

#### Generated files
- `graphify-out/graph.json` (48 MB) — the full knowledge graph
- `graphify-out/GRAPH_REPORT.md` — human-readable report with community hubs,
  navigation, and graph statistics

#### How to use
- **AI agents**: The graph is automatically available. Agents can query it
  to understand code structure, find relationships, and answer questions.
- **Developers**: Run `graphify query "show the auth flow"` to traverse the
  graph, or `graphify explain "ApiHandler"` to get a plain-language explanation
  of any node.
- **Update after code changes**: Run `graphify update .` to re-extract AST
  and rebuild the graph (no API cost).

#### Community hubs (key navigation points)
- `api.py`, `agent.py`, `statistics.py` — core BioDockify modules
- `ApiHandler`, `UserMessage`, `Tool` — Agent Zero core abstractions
- `model_config.py`, `StatisticsOrchestrator` — BioDockify-specific
- `alpine.min.js`, `react` — frontend frameworks

## [v7.5.9] - 2026-07-19

### BioDockify ↔ Obsidian Integration

Bidirectional file sync between BioDockify Knowledge Base and Obsidian vault.
Pharma researchers who use Obsidian for notes and literature management can
now sync their KB entries to an Obsidian vault, and pull Obsidian notes back
into BioDockify.

#### New: `modules/obsidian/sync.py`
- `export_to_vault()` — exports KB entries as `.md` files with Obsidian-standard
  YAML frontmatter (title, tags, source, category, created, bioid, biodockify
  block). Compatible with Dataview, Tag Wrangler, and other Obsidian plugins.
- `import_from_vault()` — scans vault directory for `.md` files, parses
  frontmatter, imports into KB. Round-trip safe via `bioid` field (updates
  existing entries instead of creating duplicates).
- `get_vault_status()` — file count, categories, last modified timestamp.
- `generate_frontmatter()` / `parse_frontmatter()` — pure functions for
  YAML frontmatter generation and parsing (no external YAML dependency).

#### New: `api/obsidian_sync.py`
- 4 actions: `status`, `export`, `import`, `configure`
- Auth required (faculty-only)
- `export` accepts `entry_ids` (selected) or `category` (all in category)
- `import` scans entire vault recursively

#### Modified: Knowledge Base UI
- `knowledge-store.js`: added `sendToObsidian()`, `pullFromObsidian()`,
  `obsidianStatus()` methods
- `knowledge-modal.html`: added "📤 Obsidian" and "📥 From Obsidian" buttons
  in selection action bar (next to existing Thesis, Review, Podcast, Slides,
  Export buttons)

#### New: `docs/guides/obsidian-integration.md`
- Setup guide (Docker volume default + host bind mount)
- Frontmatter format documentation with Dataview query examples
- Round-trip sync explanation
- Troubleshooting table

#### New: `tests/test_obsidian_sync.py`
- 18 tests: frontmatter generation (5), parsing (3), export (2), import (2),
  status (2), API handler contract (2), KB header stripping (2)
- All 18 pass. No regressions (45/45 total with AI Engine tests).

#### Vault path configuration
- Default: `/a0/usr/obsidian_vault/` (inside biodockify_usr volume)
- Configurable via host bind mount in docker-compose.yml
- Obsidian is optional — feature only activates if user configures vault

## [v7.5.8] - 2026-07-19

### Fix: copy ALL llama.cpp shared libraries (not just the binary)

v7.5.7's multi-stage build only copied `/app/llama-server` (the main
binary) from the llama.cpp image. The binary requires ~30 shared
libraries (libggml-cpu-*.so, libllama-*.so, libggml.so, etc.) that
were missing, causing: `error while loading shared libraries:
libllama-server-impl.so: cannot open shared object file`.

Fix: copy the entire `/app/` directory from the llama-src stage to
`/opt/llama-server/` in the BioDockify image. Run `ldconfig` to
register the library path. Startup script sets `LD_LIBRARY_PATH` as
a safety net. Binary accessible via symlink at `/usr/local/bin/llama-server`.

This increases the image size by ~100 MB (the shared libraries) — expected.

## [v7.5.7] - 2026-07-19

### Local AI Engine bundled inside BioDockify — one `docker compose up` does everything

The biggest change: **llama-server is now bundled inside the BioDockify
Docker image itself.** No separate sidecar container, no separate image
pull, no profiles, no scripts for students to run. One command starts
everything.

#### Architecture change (sidecar → bundled)
- **Dockerfile.release**: multi-stage build — Stage 1 extracts the
  `llama-server` binary from `ghcr.io/ggml-org/llama.cpp:server`,
  Stage 2 copies it into the BioDockify image at `/usr/local/bin/`.
  Installs `libgomp1` (OpenMP runtime for CPU inference).
- **exe/init_bonsai.sh**: one-time model auto-downloader. Checks if
  `Bonsai-8B-Q1_0.gguf` exists in `/a0/usr/ai_models/` (biodockify_usr
  volume). If not, downloads ~1.1 GB from HuggingFace. Skips download
  if already present. Non-blocking — failure doesn't prevent BioDockify
  from starting.
- **exe/init_and_run_llama.sh**: supervisord entrypoint for llama-server.
  Calls init_bonsai.sh, then execs llama-server with the model.
- **supervisord.conf**: added `[program:run_llama_server]` section that
  starts llama-server via init_and_run_llama.sh on container startup.

#### Docker-compose simplified
- Removed `bonsai-init` one-shot service (no longer needed).
- Removed `llama-server` sidecar service (now bundled).
- Removed `biodockify_models` volume — model now stored in existing
  `biodockify_usr` volume at `/a0/usr/ai_models/`.
- Single container: `docker compose up -d` starts everything.
- Student workflow is now one command: `docker compose up -d` → open
  http://localhost → select preset "BioDockify AI Engine — Local".

#### What students see
1. `docker compose up -d` (the only command)
2. BioDockify starts, llama-server starts inside the same container
3. On first run, Bonsai-8B auto-downloads (~1.1 GB, one-time)
4. Open http://localhost → select the local preset → send a test message

No profiles, no scripts, no separate images. The local AI engine is
part of the software, not an add-on.

#### Test updates
- 27/27 tests pass.
- Removed sidecar-related tests (sidecar is gone).
- Added tests for: Dockerfile multi-stage build, exe script existence,
  compose is single-container, no models volume.

#### Notes
- Model auto-download requires internet on first run. Subsequent starts
  are instant (model already in volume).
- If download fails, BioDockify still starts — use cloud presets.
- To free disk space: `docker compose down -v` removes all volumes
  including the downloaded model.

## [v7.5.6] - 2026-07-19

### Critical fixes for the BioDockify AI Engine (two more release-blockers)

v7.5.5 still wouldn't start the sidecar — two more bugs surfaced during
live install testing. Both are now fixed and guarded by regression tests.

#### Critical fix #1: case-sensitive GGUF filename
- The Hugging Face file is `Bonsai-8B-Q1_0.gguf` (capital B). v7.5.5
  referenced `bonsai-8b-Q1_0.gguf` (lowercase) — HF URLs are
  case-sensitive, so the install script got HTTP 404 and the model
  never downloaded.
- Fixed in `models.json`, both install scripts, `docker-compose.yml`
  command block, and the install guide.
- New regression test: `test_models_json_filename_case_correct` and
  `test_docker_compose_uses_correct_gguf_filename`.

#### Critical fix #2: wrong image namespace
- The image `ghcr.io/ggerganov/llama.cpp:server` returns "not found" —
  the `ggerganov` namespace is a deprecated mirror. The canonical
  namespace is `ggml-org`.
- Fixed to `ghcr.io/ggml-org/llama.cpp:server` in `docker-compose.yml`,
  `runtimes.json`, docs, and the image-namespace regression test.

#### Verified working end-to-end
- Sidecar `ghcr.io/ggml-org/llama.cpp:server` pulls and starts.
- Loads `Bonsai-8B-Q1_0.gguf` from the `biodockify_models` volume.
- `/health` returns `{"status":"ok"}`.
- `/v1/models` returns `[bonsai-8b]`.
- Live chat test: prompt "name the three ICH pillars" →
  "The three ICH pillars are Q (Quality), S (Safety), and E (Efficacy)."
  (22 completion tokens).
- biodockify container reaches sidecar via internal hostname
  `http://llama-server:8080/v1`.

#### Tests
- 25/25 pass (added 2 new regression tests for filename case and
  image namespace).

## [v7.5.5] - 2026-07-19

### Critical bug fix + hardening pass on the BioDockify AI Engine

#### Critical fix (release-blocker from v7.5.4)
- **Wrong llama.cpp image tag.** v7.5.4 referenced
  `ghcr.io/ggerganov/llama.cpp:server-light`, which does not exist on GHCR.
  The sidecar could never start. Fixed to the correct
  `ghcr.io/ggerganov/llama.cpp:server` tag (CPU, multi-arch:
  linux/amd64 + linux/arm64).
- **Wrong config mechanism.** v7.5.4 passed `MODEL` / `HOST` / `PORT` /
  `CTX_SIZE` as env vars — the llama-server entrypoint ignores them.
  Replaced with the proper `command:` block using CLI args (`-m`, `--host`,
  `--port`, `-c`, `-a`) per upstream docs. Added `-a bonsai-8b` so the
  model publishes under the id expected by the preset.
- **Healthcheck made portable.** Replaced the wget-based probe with a
  pure-bash `/dev/tcp` probe that doesn't depend on curl/wget being in
  the slim image. `start_period` raised to 90s for slow CPU first-load.

#### New: Runtime Manager abstraction (Phase 6)
- `modules/local_llm/runtimes.json` — data-driven runtime registry with 5
  backends: bundled llama.cpp sidecar (default), host Ollama, host LM
  Studio, future vLLM, future MLX.
- `LocalLLMManager` is now runtime-agnostic: `probe_sidecar`,
  `list_sidecar_models`, `get_model_status` all derive endpoints from the
  active runtime entry. Ollama's `/api/tags` vs OpenAI-compatible
  `/v1/models` is handled transparently.
- Brain stays runtime-agnostic — switching backends is a 2-line data
  change (runtimes.json + preset api_base), no Python or Agent Zero edits.

#### New: In-app Model Manager UI + Health Dashboard (Phase 5+11)
- `webui/components/local_llm/local_llm.html` — Alpine.js panel with 4
  tabs: Status (runtime reachability, latency, loaded model, hardware),
  Models (full catalog with publisher/size/quant/license/tags), Runtimes
  (every backend with endpoint + install link), Benchmark (tok/s verdict).
- `extensions/webui/right_canvas_register_surfaces/register-local_llm.js`
  — registers the panel in the right-canvas rail via BioDockify's
  extension hook. Zero Agent Zero UI changes.

#### New: Benchmark endpoint (Phase 9)
- `api/local_llm.py` `benchmark` action — sends a fixed ICH GCP prompt,
  measures wall-clock + completion tokens, returns `tokens_per_second`
  with Good (≥20) / OK (≥8) / Slow (>0) verdict. Honors `max_tokens`
  and `timeout` caps.

#### New: API surface
- Added `runtimes` and `benchmark` actions to `/api/local_llm`. Existing
  actions (`status`, `hardware`, `catalog`, `prompts`, `readiness`)
  unchanged.

#### New: Smoke test suite (Phase 16)
- `tests/test_local_llm.py` — 23 tests covering: catalog schema, runtime
  registry, Brain contract (every runtime exposes OpenAI-compatible
  endpoint), PharmaPromptLibrary rendering, hardware detection, manager
  probes (returns reachable=False, never raises when sidecar absent),
  API handler contract (all 7 actions wired, unknown action returns
  structured error), preset schema, and docker-compose wiring
  (regression-guard for the image/env-var bugs above).
- 23/23 pass.

#### Docs
- `docs/guides/bonsai-local-llm.md`: clarified Bonsai is **fully optional
  and user-driven** — user picks it for main, utility, both, or neither.
  Added 5-row matrix of Main × Utility combinations. Added section on
  swapping runtimes, the new diagnostics panel, and the new v7.5.4 image
  troubleshooting entry.

#### Constraints honored
- Zero Agent Zero core files modified (verified via git status).
- Bonsai remains one preset among four — no forced defaults, no routing
  logic that overrides user choice.
- Default `docker compose up` (no profile) still unchanged.

## [v7.5.4] - 2026-07-19

### BioDockify AI Engine — Local LLM (Private Pharma Research)

Optional **private, offline LLM runtime** for air-gapped labs, PHI case reports,
unpublished compound data, and cost-free student access. Runs Bonsai-8B
(1.15 GB, 1-bit) entirely on the user's machine — **no cloud, no egress,
no API spend**.

#### New
- `modules/local_llm/` package (manager.py, hardware.py, pharma_prompts.py)
  — provider-agnostic runtime layer. Agent Zero untouched.
- **Data-driven model catalog** (`modules/local_llm/models.json`) — adding
  Gemma / Phi / Qwen / future pharma-tuned models requires NO code changes,
  only a JSON entry.
- **Pharma Prompt Library** (`pharma_prompts.py`) — 8 domain templates
  (literature, MOA, docking, ADMET, claims, thesis, ICH compliance) that
  enforce no-fabrication rules critical for safety/regulatory writing.
- `api/local_llm.py` — rich status API: `status`, `hardware`, `catalog`,
  `prompts`, `readiness` actions. Faculty-only.
- One-click **install scripts**: `scripts/install_bonsai.sh` (Linux/macOS)
  and `scripts/install_bonsai.bat` (Windows). OS/RAM/GPU-aware preflight,
  dry-run support.
- New "BioDockify AI Engine — Local (Bonsai-8B)" preset in
  `plugins/_model_config/default_presets.yaml` — auto-appears in chat-bar
  switcher, no UI code changes.
- `docs/guides/bonsai-local-llm.md` — full architecture, hardware matrix,
  privacy/compliance notes, troubleshooting.
- `docs/setup/installation.md` — new "Recommended Local Model: Bonsai-8B"
  section with comparison table.
- README.md prerequisites updated — paid API key is no longer framed as
  mandatory; local engine and host Ollama are first-class options.

#### Docker
- `docker-compose.yml`: new `llama-server` sidecar service
  (`ghcr.io/ggerganov/llama.cpp:server-light`) behind opt-in `--profile local-llm`.
  Default `docker compose up` behavior unchanged.
- New `biodockify_models` named volume — model weights live outside the image
  so updates never re-download multi-GB GGUF files.
- `depends_on: llama-server (required: false)` — biodockify starts fine
  whether or not the sidecar is enabled.

#### Why this matters for pharma
- **Privacy**: prompts, KB content, generated text never leave the host
  (HIPAA / GDPR friendly).
- **Air-gapped**: regulatory / GxP environments with no internet still run
  AI-assisted claim verification, citation checks, literature synthesis.
- **Reproducibility**: thesis work remains re-runnable years later without
  depending on a cloud model's availability.

## [v7.5.3] - 2026-07-18

### Statistics Module — Full Restoration
- Restored 40 missing statistics analysis types from original BioDockify
  (16 → 56 total): sign_test, dunns, z_test, chi_square_goodness/independence,
  mcnemar, cmh, kaplan_meier, log_rank, cox_ph, tost, crossover,
  bioavailability, non_inferiority, equivalence, nca_pk, auc, cmax_tmax,
  half_life, clearance, pk_bioavailability, pd_response, compartmental,
  dose_proportionality, pk_summary, logistic/poisson/negative_binomial/
  multiple/polynomial regression, mixed_effects/model, glm,
  repeated_measures_anova, ancova, manova, tukey/bonferroni/dunnett/scheffe
  posthoc, meta_analysis.
- PDF report download with BioDockify letterhead (statistics module).
- Fixed missing `import pandas as pd` in delegated chi-square / McNemar /
  CMH / repeated-measures methods.
- Delegated methods use `_delegated(input, action_name)` pattern; PK/PD →
  `modules/statistics/pkpd_analysis.py`, bioequivalence →
  `modules/statistics/bioequivalence.py`, survival →
  `modules/statistics/survival_analysis.py`.

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
