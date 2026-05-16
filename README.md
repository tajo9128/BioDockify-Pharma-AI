# BioDockify Pharma AI

<h1 align="center">🧬 BioDockify Pharma AI</h1>

<h3 align="center">AI Research Assistant for Pharmaceutical Sciences</h3>

<p align="center">
  <a href="https://hub.docker.com/r/tajo9128/biodockify-pharma-ai"><img src="https://img.shields.io/badge/docker-tajo9128%2Fbiodockify--pharma--ai-blue.svg" alt="Docker"/></a>
  <a href="https://github.com/tajo9128/BioDockify-Pharma-AI/releases"><img src="https://img.shields.io/badge/version-v5.9.3-green.svg" alt="Version"/></a>
  <a href="https://github.com/tajo9128/BioDockify-Pharma-AI"><img src="https://img.shields.io/badge/GitHub-BioDockify--Pharma--AI-181717?style=flat&logo=github" alt="GitHub"/></a>
</p>

---

## Fork Attribution

**BioDockify Pharma AI** is a pharmaceutical research fork of [Agent Zero](https://github.com/agent0ai/agent-zero), an open-source agentic framework created and maintained by [Jan Tomasek](https://github.com/Xrenel) and the Agent Zero team.

> **BioDockify Pharma AI is NOT standalone software.** It is built on Agent Zero, which is free and open-source. All core framework functionality, architecture, and capabilities belong to [Agent Zero](https://github.com/agent0ai/agent-zero).
>
> We thank Jan Tomasek and the Agent Zero team for their dedication to open AI software.

---

## Features

### 20 Integrated Research Modules

| # | Module | Function | Backend |
|---|--------|----------|---------|
| 1 | **Research Command Center** | Auto-research pipeline, thesis tracking, wet lab coordination | 23 REST endpoints |
| 2 | **Molecular Toolkit** | ADMET, Tanimoto similarity, chemical space PCA, AutoDock Vina docking | RDKit + Vina |
| 3 | **Statistics** | 70+ methods: descriptive, t-test, ANOVA, survival, PK/PD, power | FastAPI router |
| 4 | **Drug Properties** | MW, LogP, HBD, HBA, TPSA, Lipinski Rule-of-5 | RDKit |
| 5 | **Literature** | PubMed/Semantic Scholar/arXiv + PRISMA screening + alerts + BioNER | 3 DB + bio_ner |
| 6 | **Academic Writer** | 5-tab: Literature Review, Research Paper, Thesis, Lecture, Slides | Thesis + Lecture APIs |
| 7 | **Faculty CMD** | Syllabus parser, lecture/assignment/rubric generator, plagiarism checker | faculty_tools |
| 8 | **Grant Writer** | Full grant proposals: abstract, aims, methods, timeline, budget | Agent-driven |
| 9 | **Journal Finder** | Verify legitimacy (Scopus/WoS/SCImago/DOAJ) + suggest where to publish | 8 data sources |
| 10 | **Citation Manager** | Collect, organize, export in APA/Nature/AMA/Vancouver/BibTeX | localStorage |
| 11 | **Regulatory** | FDA/EMA guideline search + NDA/ANDA/MAA submission checklists | FDA API |
| 12 | **Slides Generator** | Academic, Clinical, Corporate, Minimal presentation styles | Slides API |
| 13 | **Lecture Builder** | Learning objectives, sections, homework, lab practical | Lecture API |
| 14 | **Wet Lab Manager** | Experiment tracking, protocols, notes, status (planned/running/completed) | localStorage + API |
| 15 | **Research Notebook** | ChromaDB vector search, SurfSense storage, tags, favorites, knowledge graph | Knowledge API |
| 16 | **System Health** | Internet, ChromaDB, RDKit, Disk, Memory monitoring | Connection Doctor |
| 17 | **Backup & Recovery** | Docker volume + GDrive cloud backup | Backup API |
| 18 | **Kali Desktop** | Full Linux desktop environment | /desktop/session |
| 19 | **Docking Studio** | AutoDock Vina: PDB + SMILES → binding energy poses | docking_prepare/run |
| 20 | **All Tools** | Quick-launch grid for all modules | N/A |

### 4 Specialized Sub-Agents

| Agent | Role | Tools |
|-------|------|-------|
| **Researcher** | Deep research, literature synthesis, drug discovery | PubMed, web scraping, patent/trial APIs |
| **Biostatistician** | Statistical analysis, clinical trials, PK/PD modeling | 70+ statistical methods |
| **Writer** | Academic writing, thesis, papers, slides, lectures | All writing APIs |
| **Hacker** | Code execution, web scraping, automation, content acquisition | Python/JS execution, browser tools |

---

## Research Workflow

```
User Request
     ↓
Agent0 (Main Orchestrator)
     ↓
├─→ Researcher ─→ Hacker (if blocked)
│         ↓
│    Biostatistician (stats)
│         ↓
└─→ Writer (output)
```

---

## Quick Start (Your Data Persists Forever)

### ⚠️ CRITICAL: Volume Persistence

All research data — memory, chats, settings, knowledge base, projects, AND backups created inside the software — is stored at `/a0/usr/` inside the container. **If you do not mount a volume at `/a0/usr/`, everything is permanently lost when the container is deleted.**

**Backups you create in the Settings panel are stored at `usr/backups/` — inside the same path. If the volume is not mounted, backups are lost too.**

### Prerequisites
- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- 8GB+ RAM recommended

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