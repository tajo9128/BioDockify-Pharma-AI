# BioDockify Pharma AI

<h1 align="center">🧬 BioDockify Pharma AI</h1>

<h3 align="center">AI Research Assistant for Pharmaceutical Sciences</h3>

<p align="center">
  <a href="https://hub.docker.com/r/tajo9128/biodockify-pharma-ai"><img src="https://img.shields.io/badge/docker-tajo9128%2Fbiodockify--pharma--ai-blue.svg" alt="Docker"/></a>
  <a href="https://github.com/tajo9128/BioDockify-Pharma-AI/releases"><img src="https://img.shields.io/badge/version-v6.8.1-green.svg" alt="Version"/></a>
  <a href="https://github.com/tajo9128/BioDockify-Pharma-AI"><img src="https://img.shields.io/badge/GitHub-BioDockify--Pharma--AI-181717?style=flat&logo=github" alt="GitHub"/></a>
</p>

<p align="center">
  <img src="assets/screenshot.png" alt="BioDockify Pharma AI Screenshot" width="800">
</p>

**BioDockify Pharma AI** is a comprehensive pharmaceutical research platform with 15 consolidated modules. It combines GNINA CNN molecular docking (conda-forge), Vina docking, Meeko PDB→PDBQT, ProLIF interaction fingerprints, consensus Z-score scoring, SPSS-level biostatistics (20 analysis types + 8 charts), a 25-stage autonomous research pipeline, 10 literature databases, 6-model QSAR (regression + classification), pharmacophore screening (PharmacoNet NCI + ZINCPharmer batch), a 36,145-journal recommender with hijacked journal + fake website detection, an avant-garde JSME molecule editor with 3Dmol.js viewer (4-tab: 3D, Properties, Filters, Optimize), drug properties v2 (hERG/AMES/pKa/BBB/melting point/druglikeness score), and 4 specialized AI sub-agents for deep research, statistics, writing, and execution.

---

## Fork Attribution

**BioDockify Pharma AI** is a pharmaceutical research fork of [Agent Zero](https://github.com/agent0ai/agent-zero), an open-source agentic framework created and maintained by [Jan Tomasek](https://github.com/Xrenel) and the Agent Zero team.

> **BioDockify Pharma AI is NOT standalone software.** It is built on Agent Zero, which is free and open-source. All core framework functionality, architecture, and capabilities belong to [Agent Zero](https://github.com/agent0ai/agent-zero).
>
> We thank Jan Tomasek and the Agent Zero team for their dedication to open AI software.

---

## Features

### 15 Consolidated Research Modules

| # | Module | Function | Backend |
|---|--------|----------|---------|
| 1 | **Research Command Center** | Auto-research pipeline + Literature Search + Wet Lab tracking | 23 REST endpoints |
| 2 | **Molecular Toolkit** | ADMET + SwissADME + BOILED-Egg plot + Bioavailability Radar + Docking (Vina+GNINA) + Inline 3D Docking Analysis (interactions, clusters, residue energy, PLIF, consensus Z-score) | RDKit + Vina + GNINA + Meeko |
| 3 | **Statistics** | 20 analysis types + 8 chart types + data transform | FastAPI router |
| 4 | **Academic Writer** | 8-tab: Lit Review, Paper, Thesis, Grant Writer, Regulatory, Citation Manager, Lecture, Slides | Thesis + Slides + Grant APIs |
| 5 | **Faculty CMD** | Syllabus, Lectures, Assignments, Plagiarism, Slides generation | faculty_tools |
| 6 | **Journal Finder** | 36,145 Scopus/WoS journals + verify + deep research (5 live sources) + fake website detector + full dossier + suggest | journals.db + 6 live APIs |
| 7 | **QSAR Modeler** | 6 regression + 3 classification models, batch predict, read-across, feature selection, Williams Plot, PLS VIP | RDKit + scikit-learn |
| 8 | **Pharmacophore** | 13 actions: ligand, protein-based, ZINCPharmer batch screen, PharmacoNet NCI, LigandScout .ph4, weighted screening | RDKit |
| 9 | **Molecule Editor** | JSME drawing + 3Dmol.js viewer (7 styles) + Properties (hERG/AMES/pKa/BBB/MP/druglikeness) + PAINS/Brenk/NIH Filters + Bioisostere Mutagenesis | RDKit + PubChem |
| 10 | **Docking Analysis** | 3D receptor+ligand viewer with H-bonds, surface, snapshot, zoom. Interaction SVG + PLIF + RMSD clusters + residue energy | 3Dmol.js + RDKit |
| 11 | **Knowledge Base** | ChromaDB vector store, semantic search, persistent research memory | ChromaDB |
| 12 | **System Health** | Platform-aware health badges (Vina + GNINA + RDKit), Docker vs Windows detection | health.py |
| 13 | **Benchmark** | API health, storage, memory, dependency validation | benchmark.py |
| 14 | **Backup & Recovery** | Full system backup/restore with preview | backup APIs |
| 14 | **Backup & Recovery** | Full system backup/restore with preview | backup APIs |
| 15 | **All Tools** | Quick-launch grid for all 15 consolidated modules | N/A |

### Merged Modules (Accessible via Parent Dashboards)

| Original Module | Now Accessible Via |
|----------------|-------------------|
| Drug Properties | Molecule Editor → Properties tab |
| Drug Analysis (PAINS/Brenk/NIH) | Molecule Editor → Filters tab |
| Molecular Optimizer | Molecule Editor → Optimize tab |
| Literature Search (10 DB) | Research CMD → Literature tab |
| Wet Lab Manager | Research CMD → Wet Lab tab |
| Grant Writer | Academic Writer → Grant tab |
| Regulatory (FDA/EMA) | Academic Writer → Regulatory tab |
| Citation Manager | Academic Writer → Citations tab |
| Slides Generator | Faculty CMD → Slides tab |
| Lecture Builder | Faculty CMD → Lectures tab |
| Docking Deep Analysis | Molecular Toolkit → Analysis tab |

### GNINA CNN Docking (v6.8.1)

GNINA deep-learning docking auto-chains after AutoDock Vina with the same prepared PDBQT files:

| Mode | Description |
|------|-------------|
| `rescore` (default) | CNN rescoring of Vina poses |
| `all` | CNN scoring on all generated poses |
| `refinement` | CNN-guided ligand pose refinement |
| `none` | Traditional Vina scoring only |

Outputs: `gnina_docked.pdbqt`, `gnina_docked.sdf`, `gnina_log.txt` alongside Vina results. Downloadable from the Docking tab.

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
├─→ Molecular Toolkit (Docking: Vina → GNINA CNN)
│         ↓
│    Deep Analysis (3D View, Interactions, Clusters)
│         ↓
├─→ Pipeline Engine (25-stage autonomous workflow)
│    Debate → Experiment → Self-Heal → Verify → Quality Gate → HITL
│         ↓
└─→ Writer (output) + Journal Recommender (36,145 journals) + Mol Optimizer
```

---

## What's New in v6.6.0

### Avant-Garde Molecule Editor
Full-featured molecular editor replacing basic SMILES input:
- **JSME Drawing Canvas**: Self-hosted in-browser molecular drawing (atoms, bonds, rings). Bidirectional sync with SMILES text input.
- **3Dmol.js Viewer**: 3D structure in 5 styles (Stick, Ball+Stick, Sphere, Cartoon, Surface). Conformer from RDKit ETKDG+MMFF.
- **Property Panel**: Real-time MW, LogP, TPSA, HBD, HBA, Rotatable Bonds, Lipinski pass/fail.
- **PubChem Search**: Type compound name → auto-load SMILES + CID + formula.
- **Export**: PNG, SVG, MOL, SDF 3D — all generated by RDKit backend.
- **History**: Last 10 molecules saved in localStorage.
- **Quick Load**: 6 drug examples (Aspirin, Caffeine, Ibuprofen, Glucose, Sildenafil, Paracetamol).
- 3 new backend APIs: `structure_3d`, `structure_export`, `pubchem_lookup`.

### Journal Finder Agentic Research Engine
Journal module rebuilt from fragmented state into a unified research engine:
- **DB-Powered**: DecisionEngine now queries the 36,145-journal SQLite database FIRST before live API calls.
- **Unified API**: Replaced two siloed APIs with a single handler supporting 6 actions: search, verify, profile, suggest, stats, history.
- **Hijacked Journal Detection**: Cross-references against `data/integrity/hijacked_journals.json` on every verification.
- **Agent Tool Rewrite**: Was a ghost tool (returned instructions). Now actually executes DB queries and live API calls with 7 actions.
- **Frontend**: 4 tabs — Verify, Search DB (36K journals), Suggest, Dossier (full journal profile with hijacked alerts).
- **Bug Fix**: Fixed broken `verify_journal` pipeline action in `api/main.py` (TypeError on url param + dict attribute access).

### Vina PDBQT Crash Prevention + GNINA Docker Install
- **PDBQT Sanitizer**: 3-layer defense against `parse_pdbqt.cpp(69)` Vina crashes. Deep validation checks charge (col 71-76) and atom type (col 78-79) on every record. Auto-fixes blank charges → 0.00, infers atom types from elements.
- **GNINA**: Added to `Dockerfile.release` (wget from GitHub releases v1.3). Added to Docker HEALTHCHECK.

### What's New in v6.4.0

### AutoResearchClaw Pipeline (10 Dimensions)
A fully autonomous 25-stage research pipeline comparable to the paid AutoResearchClaw product:
- **9 Phases**: Scoping → Literature → Molecular → QSAR → Docking → Statistics → Decision → Writing → Publication
- **Triple Debate System**: Hypothesis (Pharmacologist/Biostatistician/Chemist), Method (Docking/QSAR/Pharmacophore/Literature), Results (Writer/Biostatistician)
- **Self-Healing**: PIVOT to alternative methods, REFINE parameters on failure — max 3 retries per domain
- **5-Layer Verification**: PubMed ID, CrossRef DOI, ClinicalTrials NCT, PubChem CID, LLM relevance
- **5 Quality Gates**: Literature (≥5 papers), Molecular (Lipinski/MW), Docking (≥3 poses), Statistical (significance/effect size), Publication (IMRaD/citation integrity)
- **8 HITL Modes**: Full Auto, Gate Only, Checkpoint, Co-Pilot, Step-by-Step, Express, Regulatory (ICH E9), Custom
- **Cross-Run Evolution**: Ebbinghaus 30-day time-decay knowledge retention across research sessions

### SPSS-Pro Biostatistics
Complete SPSS-level statistical suite beyond basic analysis:
- **20 Analysis Types**: Descriptive, Correlation, T-Test, ANOVA (4 post-hoc), Linear/Multiple/Logistic/Poisson/Negative Binomial/Stepwise Regression, 7 Non-Parametric tests, Survival (Kaplan-Meier + Cox), Normality (3 tests), Homogeneity (2 tests), ROC, Meta-Analysis, PK/PD, Bioequivalence (TOST), Power Analysis, Curve Estimation (11 models)
- **8 Chart Types**: Histogram, Boxplot, Scatter, Q-Q, Bar, ROC Curve, Survival Curve, Correlation Heatmap — auto-generated base64 PNG
- **Data Transformation**: Compute variable (formula), Recode, Rank, Fill Missing (mean/median/interpolate), Standardize (z-score/minmax/robust)
- **Data Reduction**: PCA/Factor Analysis (eigenvalues, loadings, scree plot), Cronbach's Alpha Reliability, K-Means + Hierarchical Clustering with dendrogram
- **Advanced Deep**: Missing Value Analysis, Curve Estimation, ROC with DeLong comparison, Stepwise Regression (AIC/BIC forward/backward)

### Literature Search (10 Databases)
Expanded from 3 to 10 academic databases — all free, no paid API keys:
- PubMed, Semantic Scholar, Google Scholar (citation-ranked), Scopus, Web of Science, arXiv, Elsevier (ScienceDirect), Springer Nature, Europe PMC, bioRxiv/medRxiv
- Scopus, WoS, Elsevier, and Springer use CrossRef proxy + 36,145-journal ISSN index for filtering

### Journal Recommender
- 36,145 Scopus + WoS journals in a SQLite database
- Filter by indexing (Scopus/WoS/dual), open access, and subject category
- Quality scoring: novelty, rigor, breadth, evidence, clarity → tier assignment (Tier 1-4)
- Agent tool: "Recommend a journal for my paper"

### GNINA CNN Docking

AutoDock Vina is now paired with **GNINA CNN deep-learning scoring**. After Vina completes, GNINA automatically runs with the same prepared PDBQT files. Download GNINA PDBQT, SDF, and log alongside Vina outputs. CNN scoring modes: `none`, `all`, `rescore`, `refinement`.

### 7 Computational Chemistry Modules
QSAR modeling (6 ML algorithms), Pharmacophore detection and library screening, Deep Docking Analysis (3D molecular viewer + 6 analysis tabs), Molecular Optimization, Advanced Drug-Likeness Filters (PAINS/Brenk/NIH), 2D Molecule Editor, and System Benchmarking Suite.

### Deep Docking Analysis
Six-tab analysis panel with **3Dmol.js molecular viewer** (all 16 MoleculeViewer features: cartoon/stick/ball+stick/sphere, chain coloring, surface, H-bond cylinders, snapshot PNG, 4 quick presets), 2D interaction diagram (RDKit SVG), per-residue energy decomposition bar chart, RMSD pose clustering, and ligand torsion analysis.

### Bug Fixes (v6.4.0)
- Python 3.11 `type` syntax: replaced `type[X | Y]` with `type[X, Y]` for Docker compatibility
- FastAPI `startup_event()` undefined → caused NameError on startup
- Ketcher CDN down (`lifescience.opensource.epam.com`) → replaced with RDKit 2D preview + external link
- Duplicate crontab in requirements.txt → removed
- 22 garbage/broken files deleted from root

### Bug Fixes (v6.3.0)
- Docking download links fixed (path segments → query params)
- Pose ranking corrected (explicit energy sort, most-negative = 1st)
- Grid box auto-detection from protein atom coordinates
- Structured Vina log with detailed energy table
- SurfSense KB search fixed (await/sync method name mismatch)
- Knowledge Base file upload handler fixed
- Podcast generation wired to edge-tts (was hardcoded stub)
- Docking prepare format detection cleaned up

---

## Quick Start (Your Data Persists Forever)

### ⚠️ CRITICAL: Volume Persistence

All research data — memory, chats, settings, knowledge base, projects, AND backups created inside the software — is stored at `/a0/usr/` inside the container. **If you do not mount a volume at `/a0/usr/`, everything is permanently lost when the container is deleted.**

**Backups you create in the Settings panel are stored at `usr/backups/` — inside the same path. If the volume is not mounted, backups are lost too.**

### Prerequisites
- **Docker Desktop** (Windows/macOS) or Docker Engine (Linux) — required
- **Paid API Keys**: An AI model provider API key is required (OpenRouter, OpenAI, Anthropic, etc.)
- 8GB+ RAM recommended (12GB+ for large docking jobs)

### 1. Run with persistence (REQUIRED)

```bash
# ⚠️  The -v flag is REQUIRED. Without it, ALL data is lost on container delete.
docker run -d -p 50001:50001 --name biodockify-pharma \
  -v biodockify_pharma_usr:/a0/usr \
  tajo9128/biodockify-pharma-ai:latest

# Visit http://localhost:3000
```

**If container is deleted and recreated with the SAME volume name (`biodockify_pharma_usr`), ALL data returns.**

### 2. Or use Docker Compose (recommended)

Create a folder and save this as `docker-compose.yml`:

```yaml
version: '3.8'
services:
  biodockify-pharma-ai:
    image: tajo9128/biodockify-pharma-ai:latest
    container_name: biodockify-pharma-ai
    ports:
      - "50001:50001"
    volumes:
      - biodockify_pharma_usr:/a0/usr
    restart: unless-stopped

volumes:
  biodockify_pharma_usr:
```

Then run:
```bash
docker compose up -d
```

### 3. Desktop backup (Windows)

Double-click `backup-data.bat` to save all research data to your Desktop.

---

## Data Persistence — What Survives Container Deletion

All user data is stored in the Docker volume mounted at `/a0/usr`:

| Data | Path in container | Survives container delete? |
|---|---|---|
| **🧠 Memory (FAISS vector DB)** | `/a0/usr/memory/` | ✅ Yes (with volume mount) |
| **💬 Chat history** | `/a0/usr/chats/` | ✅ Yes |
| **⚙️ Settings** | `/a0/usr/settings.json` | ✅ Yes |
| **🔑 API keys & secrets** | `/a0/usr/secrets.env` | ✅ Yes |
| **📚 Knowledge base** | `/a0/usr/knowledge/` | ✅ Yes |
| **📂 Projects** | `/a0/usr/projects/` | ✅ Yes |
| **📄 Workdir files** | `/a0/usr/workdir/` | ✅ Yes |
| **🧩 User plugins** | `/a0/usr/plugins/` | ✅ Yes |
| **🛠️ User skills** | `/a0/usr/skills/` | ✅ Yes |

### 3-Year PhD — Long-Term Memory Strategy

1. **Automatic memory**: The FAISS vector DB stores conversations, solutions, and facts automatically. It persists in the Docker volume.
2. **Regular backups**: Run `backup-data.bat` (Windows) or the built-in backup (Settings → Backup & Restore) to save snapshots to your desktop.
3. **Migration**: When upgrading to a new version:
   ```bash
   docker compose down          # stop old container
   docker compose pull          # pull new image
   docker compose up -d         # start with new image + existing volume
   ```
   All data returns automatically — no migration needed.

---

## Docker Hub

**Image**: `tajo9128/biodockify-pharma-ai:latest`

https://hub.docker.com/r/tajo9128/biodockify-pharma-ai

---

## License

BioDockify Pharma AI is a pharmaceutical research fork of Agent Zero. See [Agent Zero repository](https://github.com/agent0ai/agent-zero) for original license and documentation.

---

## Support & Links

- BioDockify Issues: https://github.com/tajo9128/BioDockify-Pharma-AI/issues
- Docker Hub: https://hub.docker.com/r/tajo9128/biodockify-pharma-ai
- Agent Zero (original): https://github.com/agent0ai/agent-zero