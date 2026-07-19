# BioDockify Pharma AI

<h1 align="center">🧬 BioDockify Pharma AI</h1>

<h3 align="center">AI Research Assistant for Pharmaceutical Sciences</h3>

<p align="center">
  <a href="https://hub.docker.com/r/tajo9128/biodockify-pharma-ai"><img src="https://img.shields.io/badge/docker-tajo9128%2Fbiodockify--pharma--ai-blue.svg" alt="Docker"/></a>
  <a href="https://github.com/tajo9128/BioDockify-Pharma-AI/releases"><img src="https://img.shields.io/badge/version-v7.5.2-green.svg" alt="Version"/></a>
  <a href="https://github.com/tajo9128/BioDockify-Pharma-AI"><img src="https://img.shields.io/badge/GitHub-BioDockify--Pharma--AI-181717?style=flat&logo=github" alt="GitHub"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"/></a>
  <a href="docs/user-guide/README.md"><img src="https://img.shields.io/badge/docs-user%20guide-lightgrey.svg" alt="Documentation"/></a>
</p>

<p align="center">
  <img src="assets/screenshot.png" alt="BioDockify Pharma AI Screenshot" width="800">
</p>

**BioDockify Pharma AI** is a pharmaceutical research platform built on the **Agent Zero v2.0** core, with **25+ integrated modules** covering all 8 pharmacy departments. It features AutoDock Vina molecular docking with MM-GBSA free energy scoring, OpenMM molecular dynamics (MD Lite), SPSS/jamovi-level biostatistics (20+ analysis types), a 25-stage autonomous research pipeline, literature search across 10 databases with automatic full-text retrieval, QSAR modeling, pharmacophore screening, 7 department modules (Pharmaceutics, Clinical Pharmacy, Pharma Analysis, Natural Products, Regulatory Affairs, **Pharmacology**, **Medicinal Chemistry**), a Knowledge Base redesigned as Open Notebook LM (notebooks, 3-column layout, AI transformations, podcast), an Academic Writer that pulls real sources from the KB to write theses/reviews, a 36,145-journal recommender, 4 AI sub-agents, and bulletproof backup to PC.

---

## Fork Attribution

**BioDockify Pharma AI** is a pharmaceutical research fork of [Agent Zero](https://github.com/agent0ai/agent-zero), an open-source agentic framework created and maintained by [Jan Tomasek](https://github.com/Xrenel) and the Agent Zero team.

> **BioDockify Pharma AI is NOT standalone software.** It is built on Agent Zero, which is free and open-source. All core framework functionality, architecture, and capabilities belong to [Agent Zero](https://github.com/agent0ai/agent-zero).
>
> We thank Jan Tomasek and the Agent Zero team for their dedication to open AI software.

---

## Features

### 22 Consolidated Research Modules

| # | Module | Function | Backend |
|---|--------|----------|---------|
| 1 | **Research Command Center** | Auto-research pipeline + Literature Search + Wet Lab tracking | 23 REST endpoints |
| 2 | **Molecular Toolkit** | ADMET + Docking (Vina + MM-GBSA) + Inline 3D Analysis (interactions, clusters, residue energy) | RDKit + Vina + Meeko |
| 3 | **Statistics** | 20 analysis types + auto-analyze (descriptive/correlation/group/normality) + data transform | scipy + pandas + matplotlib |
| 4 | **Academic Writer** | 8-tab: Lit Review, Paper, Thesis (PhD/M.Pharm/B.Pharm/Pharm.D), Grant, Regulatory, Citation, Lecture, Slides + **"Use KB Sources"** button (loads by category, 100K char budget, real citations from KB) | Thesis + Slides + Grant APIs + KB integration |
| 5 | **Faculty CMD** | 9 tabs: Syllabus, Lectures, Tasks, Semester, Lesson, Notes, Slides, Plagiarism, Questions | faculty_tools |
| 6 | **Journal Finder** | 36,145 journals + verify + deep research + fake detector + dossier | journals.db + 6 live APIs |
| 7 | **QSAR Modeler** | 6 regression + 3 classification, batch predict, read-across, feature selection | RDKit + scikit-learn |
| 8 | **Pharmacophore** | 5 tabs: Protein-based, Screen, Batch, Models, Target ID | RDKit |
| 9 | **Drug Analysis** | 3Dmol.js viewer + Properties (hERG/AMES/pKa/BBB) + Filters + Optimization + PubChem | RDKit + PubChem |
| 10 | **Docking Analysis** | 3D receptor+ligand viewer, interactions, PLIF, clusters, external file upload | 3Dmol.js + RDKit |
| 11 | **Knowledge Base** | Open Notebook LM-style: Notebooks, Sources | Notes | Chat, AI transformations, podcast, source filters (by module + time), category sidebar, DOCX export, full text extraction (PDF/DOCX/XLSX) | auto_store |
| 12 | **MD Lite** | OpenMM molecular dynamics, GPU-accelerated (CUDA/OpenCL), 24-48hr background runs with auto-resume | OpenMM + MDTraj |
| 13 | **System Health** | Platform-aware health badges (Vina/MM-GBSA/RDKit/Meeko), Docker vs Windows | health.py |
| 14 | **Deep Research** | 5-database collection (PubMed, S2, Crossref, OpenAlex, arXiv), relevance scanning | 5 live APIs |
| 15 | **Backup & Recovery** | Full system backup/restore + Save to PC + Restore from PC + daily auto-backup | backup APIs |
| 16 | **Formulation Lab** | Release kinetics (5 models), dissolution f2, nanoparticle, ICH stability, excipients, DOE/RSM | scipy + numpy |
| 17 | **Clinical Pharmacy** | DDI (15 pairs), TDM, renal dose (CKD-EPI), hepatic (Child-Pugh), Naranjo ADR | drug DB |
| 18 | **Pharma Analysis** | ICH Q2(R2) validation, f2, forced degradation, chromatography, LOD/LOQ | ICH methods |
| 19 | **Natural Products** | Phytochemical screening (7 classes), extraction yield, IC50 4PL, plant DB, dereplication | RDKit |
| 20 | **Regulatory Affairs** | eCTD/CTD structure, 40+ ICH guidelines, stability planner, BE report, IND/NDA checklists | ICH database |
| 21 | **Pharmacology** | Receptor binding (Kd/Bmax), dose-response 4PL (EC50/IC50), Schild pA2, operational model (τ/KA), selectivity, receptor DB, in-vivo design | scipy + RDKit |
| 22 | **Medicinal Chemistry** | Murcko scaffolds, MMPA, Butina clustering, SMARTS search, SA score, retrosynthesis, named reactions, protecting groups, toxicophore scan, stereo analysis | RDKit |
| — | **All Tools** | Quick-launch grid for all modules | N/A |

### Merged Modules (Accessible via Parent Dashboards)

| Original Module | Now Accessible Via |
|----------------|-------------------|
| Drug Properties | Drug Analysis → Properties tab |
| Drug Analysis (PAINS/Brenk/NIH) | Drug Analysis → Filters tab |
| Molecular Optimizer | Drug Analysis → Optimize tab |
| Literature Search (10 DB) | Research CMD → Literature tab |
| Wet Lab Manager | Research CMD → Wet Lab tab |
| Grant Writer | Academic Writer → Grant tab |
| Regulatory (FDA/EMA) | Academic Writer → Regulatory tab |
| Citation Manager | Academic Writer → Citations tab |
| Slides Generator | Faculty CMD → Slides tab |
| Lecture Builder | Faculty CMD → Lectures tab |
| Docking Deep Analysis | Molecular Toolkit → Analysis tab |

### MM-GBSA Free Energy Scoring

After AutoDock Vina completes, MM-GBSA free energy scoring runs automatically (CPU-only, no GPU required):

| Term | Description |
|------|-------------|
| **MM** | Molecular mechanics energy from Vina (VdW + electrostatics) |
| **GB** | Generalized Born desolvation penalty |
| **SA** | Solvent-accessible surface area hydrophobic penalty |
| **Interaction** | Protein-ligand close contact bonus |

Output: Per-pose MM-GBSA energies, Z-scores, and consensus with Vina (`0.4*Vina_Z + 0.6*MMGBSA_Z`). Displayed as a table in the Docking results.

### Docking Input Formats

Molecular Toolkit docking accepts multiple formats via RDKit + OpenBabel conversion:

| File | Accepted Formats |
|------|-----------------|
| Protein | `.pdb`, `.pdbqt`, `.ent`, `.mol2`, `.cif` |
| Ligand | `.smi` (SMILES), `.sdf`, `.mol`, `.pdb`, `.mol2` |

Both protein and ligand are auto-converted to PDBQT for Vina docking.

### 4 Specialized Sub-Agents

| Agent | Role | Tools |
|-------|------|-------|
| **Researcher** | Deep research, literature synthesis, drug discovery | 10 literature APIs, PRISMA screening, BioNER, web scraping, patent/trial APIs |
| **Biostatistician** | SPSS-level analysis, clinical trials, PK/PD modeling | 20 analysis types, 8 chart types, data transform/reduction, PCA, survival, meta-analysis |
| **Writer** | Academic writing, thesis, papers, slides, lectures, journal selection | All writing APIs, 36,145-journal database |
| **Hacker** | Code execution, web scraping, automation, debugging | Python/JS execution, browser tools, system repair |

---

## Research Workflow

```
User Request
     ↓
Agent0 (Main Orchestrator)
     ↓
├─→ Researcher ─→ Hacker (if blocked)
│         ↓
│    Biostatistician (SPSS-level stats) + QSAR (predictions)
│         ↓
│    Pharmacophore (feature detection)
│         ↓
├─→ Molecular Toolkit (Docking: Vina → MM-GBSA)
│         ↓
│    Deep Analysis (3D View, Interactions, Clusters)
│         ↓
├─→ Pipeline Engine (25-stage autonomous workflow)
│    Debate → Experiment → Self-Heal → Verify → Quality Gate → HITL
│         ↓
└─→ Writer (output) + Journal Recommender (36,145 journals) + Mol Optimizer
```

---

## What's New in v7.5.1

### Complete Research Pipeline: Literature → Knowledge Base → Academic Writer
The full pipeline now works end-to-end — every research output flows into the Knowledge Base by category, and the Academic Writer pulls real sources to write theses/reviews:
- **Literature Search**: 10 databases (PubMed, Semantic Scholar, Europe PMC, arXiv, bioRxiv, etc.) with automatic full-text retrieval via 3-tier fetch (Europe PMC → PDF → Hacker Agent)
- **Deep Research**: Multi-database comprehensive gathering (50-300 papers) with deduplication and relevance scoring
- **Agent Tool Prompts**: 7 new tool prompts teach the agent how to call research modules (literature_search, deep_research, docking_run, md_lite, statistics_analyze, admet_predict, drug_analysis) — agent no longer fabricates data
- **Academic Writer KB Integration**: New "Use KB Sources" UI with category dropdown (literature, deep_research, docking, etc. kept SEPARATE), 100K char budget (full text → abstracts → titles priority), writer prompt includes "Cite ONLY from KB sources — do not fabricate"
- **800-char abstract truncation removed**: Full abstracts now stored (was silently truncating all PubMed results)
- **PubMed crash fixed**: `_batch_resolve_pmcids` was referenced but never defined — literature_search silently returned 0 papers on every search
- **KB Storage fix**: 3 modules (literature_search, deep_research, faculty_tools) used a Flask-bound import that fails in the agent environment — replaced with stdlib-only `auto_store`

### 7 New Department Modules (v7.5.0)
All 8 departments from the thesis structure enum now have dedicated modules:

| Department | Module | Key Actions |
|-----------|--------|-------------|
| **Pharmaceutics** | `formulation.py` | Release kinetics (5 models), dissolution f2, nanoparticle characterization, ICH stability prediction, excipient database, DOE/RSM optimization |
| **Clinical Pharmacy** | `clinical.py` | Drug-drug interactions (15 pairs), therapeutic drug monitoring (TDM), renal dose adjustment (CKD-EPI 2021), hepatic (Child-Pugh), Naranjo ADR causality |
| **Pharma Analysis** | `pharma_analysis.py` | ICH Q2(R2) method validation, dissolution f2, forced degradation, chromatography resolution/tailing/capacity, LOD/LOQ (S/N + std deviation) |
| **Natural Products** | `natural_products.py` | Phytochemical screening (7 classes), extraction yield (4 methods), IC50 4PL fitting, plant database (6 medicinal plants), dereplication, selectivity index |
| **Regulatory Affairs** | `regulatory_enhanced.py` | ICH M4 eCTD structure, 40+ ICH guidelines database, ICH stability planner, bioequivalence report (90% CI), IND/NDA/ANDA checklists |
| **Pharmacology** (NEW) | `pharmacology.py` | Receptor binding (Kd/Bmax/Scatchard/Hill), dose-response 4PL (EC50/IC50), Schild pA2/KB, Black-Leff operational model (τ/KA), selectivity ratios, 25+ receptor database, in-vivo study design (5 endpoints + power analysis) |
| **Medicinal Chemistry** (NEW) | `medicinal_chemistry.py` | Murcko scaffold extraction, Matched Molecular Pair Analysis (MMPA), Butina clustering + diversity picking, SMARTS substructure search, synthetic accessibility score, retrosynthesis (10 disconnection motifs), 30+ named reactions database, 20+ protecting groups database, toxicophore scan (15 alerts), stereochemistry analysis (R/S, E/Z) |

### Knowledge Base — Open Notebook LM Features
- **Notebooks**: Create notebooks, add KB sources with context levels (full/summary/off), write notes (manual + AI-authored)
- **3-Column Layout**: Sources | Notes | Chat — identical to Open Notebook LM
- **AI Transformations**: Summarize, Key Findings, Critical Analysis, Timeline
- **Podcast Generation**: From notebook sources with configurable speakers, format (interview/discussion/lecture), tone, length
- **Per-Notebook Chat**: Full notebook context sent to Agent Zero
- **DOCX export**: Every KB entry generates both .md (fast read) and .docx (downloadable)
- **Source filters**: All/7d/30d time filter + source module dropdown (Literature, Docking, QSAR, etc.)
- **File upload with text extraction**: PDF (PyMuPDF), DOCX (python-docx), XLSX (openpyxl) — every uploaded file is readable

### Backup & Recovery — Bulletproof (v7.5.1)
**CRITICAL FIX**: Every existing backup was 0.0 MB empty. 3 years of PhD research was not captured. All fixed:
- **All 3 data locations captured**: `/a0/usr` (workspace), `/a0/.a0proj` (agent memory), `/a0/data` (knowledge base)
- **Backups visible on PC**: Container created with `-v C:/Users/biodo/biodockify-backups:/a0/usr/backups` — backups appear directly in Windows Explorer
- **Save to PC button**: Real download flow (fetch → blob → browser download) — no longer just a tooltip
- **Restore from PC button**: Upload .zip → auto-restore with correct path extraction
- **Restore buttons work**: Fixed `has_archive` → `has_zip` field name mismatch
- **Daily auto-backup**: Cron job at 3 AM + on-startup backup after 60s delay
- **Keeps last 7 auto-backups**, prunes older ones
- **`backup-data.bat`**: Fixed wrong volume name + now captures all 3 locations
- **`restore-data.bat`**: New companion script for PC-side restore
- **Dockerfile VOLUME**: Now declares `/a0/.a0proj` and `/a0/data` alongside `/a0/usr`

### PAINS FilterCatalog Upgrade
- Replaced 8 hardcoded SMARTS patterns with RDKit FilterCatalog full set (~480 patterns: PAINS_A + PAINS_B + PAINS_C)
- Fallback to basic patterns if FilterCatalog unavailable

### ADMET Science-Based Models
- BBB: BOILED-Egg model (Wager 2010) — TPSA + LogP threshold
- hERG: pkCSM-inspired weighted score (MW + LogP + HBD + TPSA + aromatic rings)
- Bioavailability: SwissADME-style composite (was hard-coded "0.55")
- CYP450: SMARTS-based metabolic soft spot detection (1A2, 2C9, 2C19, 2D6, 3A4)
- Plasma Protein Binding: Valko 2001 LogP correlation

### MM-GBSA Approximation Disclaimer
- Renamed to "Approximate Binding Score" with clear documentation that it's NOT proper MM-GBSA
- Scientific disclaimer added — honest about limitations

### Full Article Retrieval
- `FullTextRetriever` wired into literature_search and deep_research after every search
- 3-tier retrieval: Europe PMC (open access) → PDF extraction → Hacker Agent (paywall bypass)
- PMCID extraction added to PubMed search for Tier 1 Europe PMC full text

## What's New in v7.0.6

A major release: **Agent Zero v2.0 core** merged into BioDockify Pharma AI, plus jamovi-parity statistics and hardening across the pharma modules.

### Agent Zero v2.0 Core
- **LiteLLM transport layer** — broader provider compatibility, global config (`configure_litellm`, `set_litellm_params`, kwargs normalization/merge)
- **Parallel tool calling** + **OpenAI Responses API** support in `agent.py`
- **49 helpers updated** to v2.0 + **14 new helpers** (litellm_transport, parallel_tools, responses_tools, chat_media, ephemeral_images, media_artifacts, llm_result, tunnel helpers)
- **Security-pinned dependencies**: `litellm==1.88.1` (CVE-2026-42271 fix), `starlette==1.0.1` (Host header validation fix)
- Chat/storage layer version-matched (history metadata support)

### Statistics — jamovi-parity (new)
- **Bayesian suite** (`modules/statistics/bayesian.py`): Bayes factors (BF₁₀/BF₀₁) for t-test, ANOVA, correlation, regression; Bayesian binomial test (response rates, Phase II); posterior summaries with HDI; Lee & Wagenmakers evidence categories — the same engine jamovi uses (pingouin)
- **PDF report export** (`modules/statistics/pdf_report.py`): BioDockify-letterhead PDFs with DNA-helix motif, formatted result tables, methodology + interpretation sections, GLP/GCP/FDA/EMA compliance footer. `POST /api/statistics/report/pdf`

### Pharma Module Fixes
- **MD Lite**: 4-bug fix — hydrogens added before solvent, protein-only NoCutoff validation, consistent topology/system atom counts, `neutralize=False` (resolves CL ion template errors), robust PDB sanitizer (CRYST1 synthesis, non-protein HETATM stripping)
- **Pharmacophore**: all 16 actions verified passing; coordinate-format robustness (accepts both `[x,y,z]` list and `{x,y,z}` dict)

### Rebrand & Hardening
- **Rebrand corruption fixed** — zero `biodockify.ai` in any Python file (illegal dots in identifiers/imports/metric names repaired across 19 files)
- **Update checker** points to BioDockify GitHub releases (not agent-zero server)
- **Dockerfile.release**: copies v2.0 core files, extends rebrand sed to Python core, adds all pharma deps (biopython, lifelines, semanticscholar, pingouin, arviz, reportlab) to both venvs

## What's New in v6.9.15

- **7 bug fixes**: PK/PD API rewrite (correct PKPDAnalysis constructor), MD Lite forcefield fallback chain (5 combos), PRO/NPRO template mismatch (pH-aware hydrogens), PDB sanitization (malformed ATOM/HETATM), double solvation removed, Protein Prep download fix, Dockerfile statsmodels + sentence-transformers pre-cache
- **Module removed**: Standalone Protein Prep — redundant with docking's built-in protein preparation (PDBFixer removed from Dockerfile)
- **16 desktop modules**: PK/PD Dashboard added, Protein Prep removed

## What's New in v6.9.12

- **MD Lite module (#15)** — OpenMM molecular dynamics, GPU-accelerated (CUDA/OpenCL), 24-48hr background runs with auto-resume from checkpoint
- **Statistics**: jamovi-level UX — editable table (50 rows), chip assignment, live update, APA tables, inline plots, Python syntax output
- **15-module desktop** — MD Lite slotted below Molecular Toolkit
- **Knowledge Base**: Recent documents tab showing 50 newest entries
- **32+ bug fixes**: pagination index, Cohen's d, numpy serialization, slot conflicts, bare except, chart data flow

## What's New in v6.9.5

- **14-module desktop** — Knowledge Base + Notebook merged (5 tabs: Notebook, Chat, Library, Podcast, Notes)
- **Knowledge Base**: NotebookLM paper cards with full reader, podcast generation (TTS), quick notes
- **Faculty CMD**: 9 tabs including Questions generator (MCQ → True/False with Bloom's taxonomy)
- **Statistics**: auto-analyze mode (one-click descriptive, correlation, group tests, normality)
- **Docker**: simplified to `-p 80:80` open at `http://localhost`

---

## Quick Start (Your Data Persists Forever)

### ⚠️ CRITICAL: Volume Persistence — 3 Locations

Your research data lives in 3 places inside the container. **All 3 must be mounted as volumes** to survive container deletion:

| Volume | Container Path | What's Inside |
|--------|---------------|---------------|
| `biodockify_usr` | `/a0/usr` | Workspace, chats, projects, plugins, backups |
| `biodockify_data` | `/a0/data` | Knowledge base, deep research sessions |
| `biodockify_a0proj` | `/a0/.a0proj` | Agent memory (FAISS), instructions, project config |

**Backups are stored at `/a0/usr/backups/`** — mount a host folder there to see them directly in Windows Explorer.

### Prerequisites
- **Docker Desktop** (Windows/macOS) or Docker Engine (Linux) — required
- **An AI model** — pick one of:
  - **Cloud** (default): any provider API key (OpenRouter, OpenAI, Anthropic, etc.), **or**
  - **Local & private** (optional): the bundled **BioDockify AI Engine** runs Bonsai-8B on your own machine with **no cloud, no egress, no API spend**. Ideal for air-gapped labs, PHI case reports, and unpublished compound data. **Just run `docker compose up -d` — the model downloads automatically on first run.** See [docs/guides/bonsai-local-llm.md](docs/guides/bonsai-local-llm.md) or use host **Ollama** (see Installation guide).
- 8GB+ RAM recommended (12GB+ for large docking jobs)

### 1. Run with persistence (REQUIRED)

```bash
# Create backup folder first
mkdir ~/biodockify-backups            # Linux / macOS
mkdir C:\Users\biodo\biodockify-backups   # Windows (adjust username)

# Run container with ALL 3 volumes + host backup mount
docker run -d \
  --name biodockify \
  -p 80:80 \
  -v biodockify_usr:/a0/usr \
  -v biodockify_data:/a0/data \
  -v biodockify_a0proj:/a0/.a0proj \
  -v ~/biodockify-backups:/a0/usr/backups \
  tajo9128/biodockify-pharma-ai:latest

# Visit http://localhost
```

> **If container is deleted and recreated with the SAME volume names, ALL data returns automatically.** Backups appear at `~/biodockify-backups` on your PC — visible in your file manager, survives even `docker volume rm`.

---

### 2. Or use Docker Compose

Save as `docker-compose.yml`:

```yaml
services:
  biodockify:
    image: tajo9128/biodockify-pharma-ai:latest
    container_name: biodockify
    ports:
      - "80:80"
    volumes:
      - biodockify_usr:/a0/usr
      - biodockify_data:/a0/data
      - biodockify_a0proj:/a0/.a0proj
      - ~/biodockify-backups:/a0/usr/backups
    restart: unless-stopped

volumes:
  biodockify_usr:
  biodockify_data:
  biodockify_a0proj:
```

```bash
docker compose up -d
```

### 3. Backup to PC

**Option A — In-app** (recommended): Open **Backup & Recovery** panel → click **"Save to PC"** → .zip downloads to your Downloads folder.

**Option B — Script** (Windows): Double-click `backup-data.bat` to save all research data (workspace + agent memory + knowledge base) to your Desktop.

**Option C — Automatic**: Backups run daily at 3 AM + on every container restart. They appear in `~/biodockify-backups/` on your PC.

---

## Data Persistence — What Survives Container Deletion

All user data is stored across 3 Docker volumes:

### Volume 1: `/a0/usr` (biodockify_usr)

| Data | Path | Survives? |
|---|---|---|
| **💬 Chat history** | `/a0/usr/chats/` | ✅ Yes |
| **⚙️ Settings** | `/a0/usr/settings.json` | ✅ Yes |
| **🔑 API keys & secrets** | `/a0/usr/secrets.env` | ✅ Yes |
| **📂 Projects** | `/a0/usr/projects/` | ✅ Yes |
| **📄 Workdir files** | `/a0/usr/workdir/` | ✅ Yes |
| **🧩 User plugins** | `/a0/usr/plugins/` | ✅ Yes |
| **🛠️ User skills** | `/a0/usr/skills/` | ✅ Yes |
| **💾 Backups** | `/a0/usr/backups/` | ✅ Yes + on PC if host-mounted |

### Volume 2: `/a0/data` (biodockify_data)

| Data | Path | Survives? |
|---|---|---|
| **📚 Knowledge base** | `/a0/data/knowledge_base/` | ✅ Yes |
| **📚 Literature (papers)** | `/a0/data/knowledge_base/literature/` | ✅ Yes |
| **🔬 Deep research sessions** | `/a0/data/knowledge_base/deep_research/` | ✅ Yes |
| **🧬 Docking results** | `/a0/data/knowledge_base/docking/` | ✅ Yes |
| **⚗️ MD simulations** | `/a0/data/knowledge_base/md_simulation/` | ✅ Yes |
| **📊 QSAR models** | `/a0/data/knowledge_base/qsar/` | ✅ Yes |
| **💊 Pharmacophore** | `/a0/data/knowledge_base/pharmacophore/` | ✅ Yes |
| **📈 Statistics** | `/a0/data/knowledge_base/statistics/` | ✅ Yes |
| **💊 Drug analysis** | `/a0/data/knowledge_base/drug_analysis/` | ✅ Yes |
| **🫀 Pharmacology** | `/a0/data/knowledge_base/pharmacology/` | ✅ Yes |
| **🧪 Medicinal Chemistry** | `/a0/data/knowledge_base/medicinal_chemistry/` | ✅ Yes |

### Volume 3: `/a0/.a0proj` (biodockify_a0proj)

| Data | Path | Survives? |
|---|---|---|
| **🧠 Agent memory (FAISS)** | `/a0/.a0proj/memory/` | ✅ Yes |
| **📋 Instructions** | `/a0/.a0proj/instructions/` | ✅ Yes |
| **⚙️ Project config** | `/a0/.a0proj/project.json` | ✅ Yes |

### 3-Year PhD — Long-Term Memory Strategy

1. **Automatic memory**: The FAISS vector DB stores conversations, solutions, and facts automatically. It persists in the `biodockify_a0proj` Docker volume.
2. **Regular backups**: Open **Backup & Recovery** panel → **"Save to PC"** to download a .zip to your Downloads folder. Or double-click `backup-data.bat` on Windows. Backups also run automatically at 3 AM daily.
3. **Host backup folder**: Mount `~/biodockify-backups:/a0/usr/backups` — backups appear directly in your file manager at `~/biodockify-backups/`. Survives container deletion AND `docker volume rm`.
4. **Migration**: When upgrading to a new version:
   ```bash
   docker compose down          # stop old container
   docker compose pull          # pull new image
   docker compose up -d         # start with new image + existing volumes
   ```
   All data returns automatically — no migration needed.

---

## Docker Hub

**Image**: `tajo9128/biodockify-pharma-ai:latest`

https://hub.docker.com/r/tajo9128/biodockify-pharma-ai

---

## License

BioDockify Pharma AI is open-source under the [MIT License](LICENSE), inherited from the [Agent Zero](https://github.com/agent0ai/agent-zero) framework by Jan Tomasek. See the original repository for framework license details.

## Documentation

- [User Guide](docs/user-guide/README.md) — 28 chapters covering installation, modules, research workflows
- [Architecture](ARCHITECTURE.md) — system design and component overview
- [AGENTS.md](AGENTS.md) — developer reference and conventions
- [CHANGELOG](CHANGELOG.md) — release history

## Support

- [GitHub Issues](https://github.com/tajo9128/BioDockify-Pharma-AI/issues)
- [Docker Hub](https://hub.docker.com/r/tajo9128/biodockify-pharma-ai)
- [Agent Zero](https://github.com/agent0ai/agent-zero) (original framework)