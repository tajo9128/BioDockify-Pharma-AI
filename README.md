# BioDockify Pharma AI

<h1 align="center">🧬 BioDockify Pharma AI</h1>

<h3 align="center">AI Research Assistant for Pharmaceutical Sciences</h3>

<p align="center">
  <a href="https://hub.docker.com/r/tajo9128/biodockify-pharma-ai"><img src="https://img.shields.io/badge/docker-tajo9128%2Fbiodockify--pharma--ai-blue.svg" alt="Docker"/></a>
  <a href="https://github.com/tajo9128/BioDockify-Pharma-AI/releases"><img src="https://img.shields.io/badge/version-4.3.5-green.svg" alt="Version"/></a>
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

### Specialized Research Agents (6 Profiles)

| Agent | Profile | Role |
|-------|---------|------|
| **Agent0** | default | Main orchestrator — coordinates sub-agents and research modules |
| **Researcher** | researcher | Deep research, literature synthesis, data analysis, web scraping |
| **Biostatistician** | biostatistician | Statistical analysis, clinical trials, hypothesis testing, PK/PD |
| **Writer** | writer | Academic writing, thesis papers, and research documentation |
| **Developer** | developer | Self-healing, debugging, code repair, system recovery |
| **Hacker** | hacker | Content acquisition when blocked, technical tasks |

### Research Backend Modules

| Module | Description |
|--------|-------------|
| **Statistics** | 70+ statistical methods — t-tests, ANOVA, regression, survival analysis, bioequivalence, PK/PD |
| **Literature** | 14+ sources — PubMed, Semantic Scholar, Europe PMC, Crossref, bioRxiv, OpenAlex |
| **WetLab** | Lab experiment tracking — PCR, ELISA, Western Blot, Cell Culture, FACS, Microscopy |
| **Thesis** | PhD thesis management with 6-chapter tracker and LaTeX export |
| **Slides** | Presentation generation with 4 themes — Default, Scientific, Corporate, Creative |
| **Auto Research Orchestrator** | Full research pipeline automation |
| **Proactive Guidance** | Research phase suggestions and workflow optimization |

### Research Database Access

| Category | Sources |
|----------|---------|
| Literature | PubMed, PubMed Central, Semantic Scholar, Europe PMC, Crossref, bioRxiv, medRxiv, OpenAlex, Scopus, Web of Science |
| Chemistry & Drugs | PubChem (NIH), ChEMBL (EBI), DrugBank |
| Clinical | ClinicalTrials.gov (US & EU) |

### BioDockify-Branded UI

- Custom sidebar with BioDockify Pharma AI branding
- Research Tools dropdown menu
- 6 dedicated research modal interfaces
- Dark/light theme with teal/cyan accent colors
- DNA double-helix favicon
- BioDockify identity logo and welcome screen

### Core Capabilities

- **Multi-Agent Cooperation** — Agents create subordinates to break down complex tasks
- **Browser Automation** — Playwright-powered web browsing with annotations
- **Code Execution** — Full Linux environment (Python, Node.js, Bash)
- **Persistent Memory** — Vector DB-powered memory and knowledge management
- **Projects** — Isolated workspaces with Git integration
- **Skills System** — Open SKILL.md standard for portable capabilities
- **MCP Client/Server** — Model Context Protocol support
- **Plugin Architecture** — Extensible with shared plugins
- **LibreOffice Integration** — Document, spreadsheet, presentation handling
- **Time Travel** — Workspace history snapshots and revert
- **WebSocket Infrastructure** — Real-time communication
- **A2A Protocol** — Agent-to-agent communication
- **Multi-Provider LLM** — OpenAI, Anthropic, DeepSeek, Ollama, and more
- **Self-Healing Developer Agent** — Automatic error diagnosis and repair
- **Speech-to-Text & Text-to-Speech** — Voice interface support

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

### Prerequisites
- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- 8GB+ RAM recommended

### 1. Run with persistence

```bash
# Pull and run — ALL data (memory, chats, knowledge, projects) stored in persistent volume
docker run -d -p 3000:3000 --name biodockify-pharma \
  -v biodockify_pharma_usr:/a0/usr \
  tajo9128/biodockify-pharma-ai:latest

# Visit http://localhost:3000
```

**If container is deleted and recreated with the same volume name, ALL data returns.**

### 2. Or use Docker Compose (recommended)

Create a folder and save this as `docker-compose.yml`:

```yaml
version: '3.8'
services:
  biodockify-pharma-ai:
    image: tajo9128/biodockify-pharma-ai:latest
    container_name: biodockify-pharma-ai
    ports:
      - "3000:3000"
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