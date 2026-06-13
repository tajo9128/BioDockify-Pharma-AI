# BioDockify Pharma AI

<h1 align="center">🧬 BioDockify Pharma AI</h1>

<h3 align="center">AI Research Assistant for Pharmaceutical Sciences</h3>

<p align="center">
  <a href="https://hub.docker.com/r/tajo9128/biodockify-pharma-ai"><img src="https://img.shields.io/badge/docker-tajo9128%2Fbiodockify--pharma--ai-blue.svg" alt="Docker"/></a>
  <a href="https://github.com/tajo9128/BioDockify-Pharma-AI/releases"><img src="https://img.shields.io/badge/version-v6.9.5-green.svg" alt="Version"/></a>
  <a href="https://github.com/tajo9128/BioDockify-Pharma-AI"><img src="https://img.shields.io/badge/GitHub-BioDockify--Pharma--AI-181717?style=flat&logo=github" alt="GitHub"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"/></a>
  <a href="docs/user-guide/README.md"><img src="https://img.shields.io/badge/docs-user%20guide-lightgrey.svg" alt="Documentation"/></a>
</p>

<p align="center">
  <img src="assets/screenshot.png" alt="BioDockify Pharma AI Screenshot" width="800">
</p>

**BioDockify Pharma AI** is a pharmaceutical research platform with 15 integrated modules. It features AutoDock Vina molecular docking with MM-GBSA free energy scoring, SPSS-level biostatistics (20 analysis types + auto-analyze), a 25-stage autonomous research pipeline, literature search across 10 databases, QSAR modeling, pharmacophore screening, a 36,145-journal recommender, Drug Analysis with 3Dmol.js viewer, a NotebookLM-style document reader with podcast generation, 4 AI sub-agents, faculty command center with question bank generator, and a ChromaDB knowledge base supporting PDF/DOCX/XLSX/audio/video.

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
| 2 | **Molecular Toolkit** | ADMET + Docking (Vina + MM-GBSA) + Inline 3D Analysis (interactions, clusters, residue energy) | RDKit + Vina + Meeko |
| 3 | **Statistics** | 20 analysis types + auto-analyze (descriptive/correlation/group/normality) + data transform | scipy + pandas + matplotlib |
| 4 | **Academic Writer** | 8-tab: Lit Review, Paper, Thesis, Grant, Regulatory, Citation, Lecture, Slides | Thesis + Slides + Grant APIs |
| 5 | **Faculty CMD** | 9 tabs: Syllabus, Lectures, Tasks, Semester, Lesson, Notes, Slides, Plagiarism, Questions | faculty_tools |
| 6 | **Journal Finder** | 36,145 journals + verify + deep research + fake detector + dossier | journals.db + 6 live APIs |
| 7 | **QSAR Modeler** | 6 regression + 3 classification, batch predict, read-across, feature selection | RDKit + scikit-learn |
| 8 | **Pharmacophore** | 5 tabs: Protein-based, Screen, Batch, Models, Target ID | RDKit |
| 9 | **Drug Analysis** | 3Dmol.js viewer + Properties (hERG/AMES/pKa/BBB) + Filters + Optimization + PubChem | RDKit + PubChem |
| 10 | **Docking Analysis** | 3D receptor+ligand viewer, interactions, PLIF, clusters, external file upload | 3Dmol.js + RDKit |
| 11 | **Knowledge Base** | 5 tabs: Notebook (doc cards + full reader), Chat with KB, Library, Podcast (TTS), Notes | ChromaDB + TTS |
| 12 | **MD Lite** | OpenMM molecular dynamics, GPU-accelerated (CUDA/OpenCL), 24-48hr background runs with auto-resume | OpenMM + MDTraj |
| 13 | **System Health** | Platform-aware health badges (Vina/MM-GBSA/RDKit/Meeko), Docker vs Windows | health.py |
| 14 | **Deep Research** | 5-database collection (PubMed, S2, Crossref, OpenAlex, arXiv), relevance scanning | 5 live APIs |
| 15 | **Backup & Recovery** | Full system backup/restore with preview + auto-backup | backup APIs |
| — | **All Tools** | Quick-launch grid for all 15 consolidated modules | N/A |

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

## What's New in v6.9.5

- **14-module desktop** — Knowledge Base + Notebook merged (5 tabs: Notebook, Chat, Library, Podcast, Notes)
- **Knowledge Base**: NotebookLM paper cards with full reader, podcast generation (TTS), quick notes
- **Faculty CMD**: 9 tabs including Questions generator (MCQ → True/False with Bloom's taxonomy)
- **Statistics**: auto-analyze mode (one-click descriptive, correlation, group tests, normality)
- **Docker**: simplified to `-p 80:80` open at `http://localhost`

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
# Create backup folder first
mkdir ~/biodockify-backups            # Linux / macOS
mkdir C:\biodockify-backups           # Windows

# Run container
docker run -d \
  --name biodockify-pharma \
  -p 80:80 \
  -v biodockify_pharma_usr:/a0/usr \
  -v ~/biodockify-backups:/app/data \
  tajo9128/biodockify-pharma-ai:latest

# Visit http://localhost
```

> **If container is deleted and recreated with the SAME volume name, ALL data returns.**

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
      - ./backup-data:/app/data
    restart: unless-stopped

volumes:
  biodockify_usr:
```

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