# BioDockify Pharma AI

<h1 align="center">🧬 BioDockify Pharma AI</h1>

<h3 align="center">AI Research Assistant for Pharmaceutical Sciences</h3>

<p align="center">
  <a href="https://hub.docker.com/r/tajo9128/biodockify-pharma-ai"><img src="https://img.shields.io/badge/docker-tajo9128%2Fbiodockify--pharma--ai-blue.svg" alt="Docker"/></a>
  <a href="https://github.com/tajo9128/BioDockify-Pharma-AI/releases"><img src="https://img.shields.io/badge/version-v6.8.7-green.svg" alt="Version"/></a>
  <a href="https://github.com/tajo9128/BioDockify-Pharma-AI"><img src="https://img.shields.io/badge/GitHub-BioDockify--Pharma--AI-181717?style=flat&logo=github" alt="GitHub"/></a>
</p>

<p align="center">
  <img src="assets/screenshot.png" alt="BioDockify Pharma AI Screenshot" width="800">
</p>

**BioDockify Pharma AI** is a comprehensive pharmaceutical research platform with 15 consolidated modules. It combines MM-GBSA free energy scoring (CPU-only), AutoDock Vina molecular docking, Meeko PDB→PDBQT conversion, external docking file upload (Vina/Glide/GOLD/AutoDock-GPU/rDock/PLANTS), SPSS-level biostatistics (20 analysis types + 8 charts), a 25-stage autonomous research pipeline, 10 literature databases, 6-model QSAR (regression + classification), pharmacophore screening (PharmacoNet NCI + ZINCPharmer batch), a 36,145-journal recommender with hijacked journal + fake website detection, a Drug Analysis module with 3Dmol.js viewer (3D, Properties, Filters, Optimize), drug properties v2 (hERG/AMES/pKa/BBB/melting point/druglikeness score), and 4 specialized AI sub-agents for deep research, statistics, writing, and execution.

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
| 2 | **Molecular Toolkit** | ADMET + SwissADME + BOILED-Egg plot + Bioavailability Radar + Docking (Vina + MM-GBSA) + Inline 3D Docking Analysis (interactions, clusters, residue energy, PLIF) | RDKit + Vina + Meeko |
| 3 | **Statistics** | 20 analysis types + 8 chart types + data transform | scipy + scikit-learn + pandas + matplotlib |
| 4 | **Academic Writer** | 8-tab: Lit Review, Paper, Thesis, Grant Writer, Regulatory, Citation Manager, Lecture, Slides | Thesis + Slides + Grant APIs |
| 5 | **Faculty CMD** | Syllabus, Lectures, Assignments, Plagiarism, Slides generation | faculty_tools |
| 6 | **Journal Finder** | 36,145 Scopus/WoS journals + verify + deep research (5 live sources) + fake website detector + full dossier + suggest | journals.db + 6 live APIs |
| 7 | **QSAR Modeler** | 6 regression + 3 classification models, batch predict, read-across, feature selection, Williams Plot, PLS VIP | RDKit + scikit-learn |
| 8 | **Pharmacophore** | 5 tabs: Protein-based, Screen, Batch, Models, Target ID | RDKit |
| 9 | **Drug Analysis** | 3Dmol.js viewer (7 styles) + Properties (hERG/AMES/pKa/BBB/MP/druglikeness) + PAINS/Brenk/NIH Filters + Bioisostere Mutagenesis + PubChem search | RDKit + PubChem |
| 10 | **Docking Analysis** | 3D receptor+ligand viewer with H-bonds, surface, snapshot. Interaction SVG + PLIF + RMSD clusters + residue energy. **External file upload** from any platform | 3Dmol.js + RDKit |
| 11 | **Knowledge Base** | ChromaDB vector store, semantic search, persistent research memory | ChromaDB |
| 12 | **System Health** | Platform-aware health badges (Vina + MM-GBSA + RDKit + Meeko), Docker vs Windows detection | health.py |
| 13 | **Deep Research** | 5-database collection (PubMed, Semantic Scholar, Crossref, OpenAlex, arXiv), relevance scanning, store to KB | 5 live APIs |
| 14 | **Backup & Recovery** | Full system backup/restore with preview + auto-backup on first health check | backup APIs |
| 15 | **All Tools** | Quick-launch grid for all 15 consolidated modules | N/A |

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

### MM-GBSA Free Energy Scoring (v6.8.7)

After AutoDock Vina completes, MM-GBSA free energy scoring runs automatically (CPU-only, no GPU required):

| Term | Description |
|------|-------------|
| **MM** | Molecular mechanics energy from Vina (VdW + electrostatics) |
| **GB** | Generalized Born desolvation penalty |
| **SA** | Solvent-accessible surface area hydrophobic penalty |
| **Interaction** | Protein-ligand close contact bonus |

Output: Per-pose MM-GBSA energies, Z-scores, and consensus with Vina (`0.4*Vina_Z + 0.6*MMGBSA_Z`). Displayed as a table in the Docking results.

### External Docking File Upload (v6.8.7)

Upload receptor + docked ligand files from **any docking platform** for deep analysis:

| Platform | Receptor Format | Ligand Format |
|----------|----------------|---------------|
| AutoDock Vina | PDB/PDBQT | PDBQT (multi-model) |
| Glide (Schrödinger) | PDB | SDF |
| GOLD | PDB/MOL2 | SDF |
| AutoDock-GPU | PDBQT | PDBQT |
| rDock | PDB/MOL2 | SDF |
| PLANTS | PDB/MOL2 | SDF |

Upload panel in Deep Analysis → toggle "Upload Files" → choose receptor + ligand → auto-runs full analysis (3D view, interactions, clusters, residue energy, torsion).

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

## What's New in v6.8.7

### External Docking File Upload
Upload receptor + docked ligand files from any platform (AutoDock Vina, Glide, GOLD, AutoDock-GPU, rDock, PLANTS) for deep analysis. Supports PDB, PDBQT, CIF, MOL2 for receptor and PDBQT, SDF for ligand poses. Auto-creates job and runs full analysis (3D view, interactions, clusters, residue energy, torsion).

### MM-GBSA Free Energy Scoring (replaces ODDT/GNINA)
CPU-only, no GPU required. Combines Vina MM term + GB desolvation + SA surface area + protein interaction bonus. Spatial grid optimization for large proteins. Per-pose MM-GBSA energies, Z-scores, and consensus with Vina.

### Drug Analysis (renamed from Molecule Editor)
Removed JSME Java applet drawing. Simplified to SMILES input + analysis (3D view, Properties, Filters, Optimize, PubChem search).

### Security & Stability
- **file_info.py sandboxed** — blocks access to /etc/shadow, /root, /proc, /sys
- **restart.py auth** — requires authentication + CSRF
- **5 crash fixes** — chat_export, chat_files_path_get, nudge, chat_load, upload_work_dir_files
- **8 bug fixes** — literature search, knowledge base, clinical trials, self_heal, lecture generator, upload, chat errors, JS exceptions

### Dockerfile
- Added scipy, scikit-learn, pandas, matplotlib for Statistics module
- Fixed pip install path (full /opt/venv-a0/bin/python)
- Healthcheck on port 80

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