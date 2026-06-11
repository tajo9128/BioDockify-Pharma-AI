# Chapter 1: Installation & Quick Start Guide

## 1.1 What is BioDockify Pharma AI?

BioDockify Pharma AI is an AI-powered pharmaceutical research platform with **15 consolidated modules** covering the full drug discovery pipeline — from molecular docking and QSAR modeling to academic writing and journal selection. Built on the Agent Zero agentic framework, it combines:

- **GNINA CNN molecular docking** with AutoDock Vina
- **SwissADME-style ADMET prediction** with BOILED-Egg and Bioavailability Radar plots
- **QSAR Modeler** — 9 ML models (6 regression + 3 classification) with read-across and Williams Plot
- **Pharmacophore modeling** — 13 actions including ZINCPharmer batch screening
- **Drug Properties v2** — hERG, AMES mutagenicity, pKa, BBB permeability, melting point
- **36,145-journal Finder** with hijacked/fake journal detection
- **SPSS-level Statistics** — 20 analysis types + 8 chart types
- **4-tab Molecule Editor** — 3D viewer, drug properties, PAINS/Brenk filters, bioisostere optimization

---

## 1.2 System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|------------|
| **Operating System** | Windows 10/11 (64-bit), macOS 12+, or Ubuntu 20.04+ |
| **Docker Desktop** | v4.0+ (free for personal use) |
| **RAM** | 8 GB minimum, 16 GB recommended |
| **Disk Space** | 10 GB free (image + data + models) |
| **CPU** | 4 cores minimum, 8+ recommended for docking |
| **Internet** | Required for initial setup and API calls |

### Recommended for Full Pipeline

| Component | Recommendation |
|-----------|---------------|
| **RAM** | 32 GB for large docking campaigns |
| **GPU** | NVIDIA GPU with CUDA for GNINA CNN (optional, Vina works on CPU) |
| **Disk** | SSD with 50+ GB for model libraries and databases |

---

## 1.3 Installing Docker Desktop

### Windows

1. **Download Docker Desktop** from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
2. Run the installer (`Docker Desktop Installer.exe`)
3. During installation:
   - ✅ Enable **WSL 2 backend** (recommended)
   - ✅ Add shortcut to desktop
4. After installation, **restart your computer**
5. Launch Docker Desktop and wait for the engine to start (whale icon in system tray turns green)

### macOS

1. Download Docker Desktop for Mac (Intel or Apple Silicon)
2. Drag `Docker.app` to Applications
3. Launch Docker Desktop from Applications
4. Grant permissions when prompted

### Linux (Ubuntu/Debian)

```bash
# Install Docker Engine
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (no sudo needed)
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt-get install docker-compose-plugin
```

### Verify Docker Installation

```bash
docker --version
# Docker version 24.0.x or higher

docker compose version
# Docker Compose version v2.x.x
```

---

## 1.4 Installing BioDockify

### Step 1: Clone the Repository

```bash
git clone https://github.com/tajo9128/BioDockify-Pharma-AI.git
cd BioDockify-Pharma-AI
```

### Step 2: Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and set your API keys:

```bash
# Required: At least one LLM provider
OPENROUTER_API_KEY=your_key_here    # Recommended — access to 100+ models
# OR
OPENAI_API_KEY=your_key_here
# OR
ANTHROPIC_API_KEY=your_key_here

# Optional: Additional services
PUBMED_API_KEY=your_key_here        # For literature search rate limits
SEMANTIC_SCHOLAR_API_KEY=your_key_here
```

### Step 3: Build and Launch

```bash
# Build the Docker image (first time only — takes 5-10 minutes)
docker compose build --no-cache

# Start the platform
docker compose up -d

# Check logs
docker compose logs -f
```

### Step 4: Verify Installation

Open your browser and navigate to:

```
http://localhost
```

You should see the BioDockify chat interface. Click the **All Tools** button in the sidebar to see all 15 modules.

### Health Check

Visit `http://localhost/api/health` to verify all services:

```json
{
  "health": {
    "status": "healthy",
    "checks": [
      {"name": "Internet", "status": "ok"},
      {"name": "AutoDock Vina", "status": "ok"},
      {"name": "GNINA CNN", "status": "ok"},
      {"name": "RDKit", "status": "ok"},
      {"name": "Disk", "status": "ok", "detail": "45.2GB free"}
    ]
  }
}
```

**Expected results:**
- ✅ Internet: ok
- ✅ AutoDock Vina: ok (required for molecular docking)
- ✅ GNINA CNN: ok (deep-learning docking scoring)
- ✅ RDKit: ok (molecular descriptors and chemistry)

---

## 1.5 Data Persistence — CRITICAL

BioDockify stores all data in Docker volumes. **Without proper volume mounting, ALL data is lost when the container is removed.**

### The `/a0/usr` Volume

The most important path is `/a0/usr` — this contains:

| Path | Contents |
|------|----------|
| `/a0/usr/workdir/` | Agent workspace, uploaded files |
| `/a0/usr/plugins/` | Custom user plugins |
| `/a0/usr/uploads/` | Uploaded images and documents |
| `/a0/usr/backups/` | System backups |
| `/a0/usr/settings.json` | User configuration |

### docker-compose.yml Volume Mount

```yaml
services:
  biodockify:
    image: tajo9128/biodockify-pharma-ai:v6.9.5
    ports:
      - "80:80"
    volumes:
      - biodockify_usr:/a0/usr          # ← CRITICAL: All user data
      - biodockify_data:/a0/data        # Models, databases
      - biodockify_tmp:/a0/tmp          # Docking jobs, temp files
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
```

### What Survives Container Deletion

| Scenario | Data Survives? |
|----------|---------------|
| `docker compose restart` | ✅ Yes — volumes persist |
| `docker compose down` | ✅ Yes — volumes persist |
| `docker compose down -v` | ❌ NO — volumes deleted! |
| `docker compose build --no-cache` | ✅ Yes — volumes persist |
| Uninstall Docker Desktop | ❌ NO — unless you export volumes first |

### Desktop Backup (Windows)

Run `backup-data.bat` from the project root to create a timestamped backup:

```cmd
backup-data.bat
```

This creates a backup in the project directory that can be restored later.

---

## 1.6 Choosing the Right File Paths

### For Research Data

| File Type | Recommended Location | Why |
|-----------|---------------------|-----|
| PDB protein files | Upload via Molecule Editor or paste directly | Stored in `/a0/usr/uploads/` |
| SMILES libraries | Paste in QSAR/Pharmacophore tabs | Temporary — save to CSV first |
| CSV datasets | Upload via QSAR Modeler | Stored in container |
| Docking results | Auto-saved in `/a0/tmp/docking_jobs/` | Download via PDBQT/SDF buttons |
| QSAR models | Auto-saved in `data/qsar_models/` | Persists in volume |

### Best Practices

1. **Always download important results** — Use the download buttons in each module
2. **Name your models** — When training QSAR, give descriptive model names
3. **Use CSV format** — For QSAR datasets, use CSV with clear column headers
4. **Keep SMILES canonical** — Use RDKit-canonical SMILES for consistency
5. **Backup before upgrades** — Run `backup-data.bat` before updating Docker image

---

## 1.7 Optional Settings

### LLM Provider Configuration

Navigate to **Settings → LLM** to configure:

| Provider | Best For | Setup |
|----------|----------|-------|
| **OpenRouter** | Access to 100+ models, single API key | Set `OPENROUTER_API_KEY` in `.env` |
| **OpenAI** | GPT-4, fast responses | Set `OPENAI_API_KEY` |
| **Anthropic** | Claude, research tasks | Set `ANTHROPIC_API_KEY` |
| **Ollama** | Local models, no API costs | Run Ollama locally, set `OLLAMA_HOST` |

### Speech Settings

BioDockify supports text-to-speech with 3-tier fallback:

1. **Kokoro TTS** (best quality, requires GPU)
2. **Edge-TTS** (good quality, free)
3. **Browser TTS** (basic, always available)

Configure in **Settings → Speech**.

### Theme & Display

- **Dark mode**: Default, toggle in Settings
- **Layout modes**: Chat (default), Split-Pane (side-by-side), Full Desktop
- **Font size**: Adjustable in Settings

---

## 1.8 First Launch Walkthrough

### Step 1: Open the Interface

Navigate to `http://localhost`. You'll see the welcome screen with a chat input.

### Step 2: Explore the Modules

Click **All Tools** in the sidebar to see the module grid:

| Module | What It Does |
|--------|-------------|
| **Research CMD** | Start a research pipeline |
| **Molecular Toolkit** | ADMET + Docking |
| **Molecule Editor** | Draw molecules + 3D view |
| **QSAR** | Train ML models |
| **Pharmacophore** | Virtual screening |
| **Journal Finder** | Find journals for your paper |
| **Academic Writer** | Write papers/theses/grants |
| **Faculty CMD** | Teaching tools |
| **Statistics** | Statistical analysis |

### Step 3: Try the Molecule Editor

1. Click **Molecule Editor** in the module grid
2. Type `CC(=O)Oc1ccccc1C(=O)O` (aspirin) in the SMILES field
3. Press Enter — watch the 3D structure render
4. Click **Properties** tab — see MW, LogP, hERG, AMES predictions
5. Click **Filters** tab — see PAINS/Brenk/NIH alerts
6. Click **Optimize** tab — generate bioisosteric replacements

### Step 4: Try Docking

1. Open **Molecular Toolkit**
2. Paste a protein PDB in the Protein card
3. Paste a ligand SMILES in the Ligand card
4. Click **Run Docking**
5. View results in the **Analysis** tab with 3D viewer

### Step 5: Try QSAR

1. Open **QSAR Modeler**
2. Upload a CSV with SMILES + activity columns
3. Select Regression or Classification
4. Click **Process Dataset** → **Start Training**
5. View metrics, feature importance, and Williams Plot

---

## 1.9 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|---------|
| Port 80 already in use | Change port in `docker-compose.yml`: `"8080:80"` |
| GNINA shows yellow/warn | Normal on Windows — GNINA requires Docker (Linux). Use Docker for full docking pipeline |
| RDKit import error | Rebuild: `docker compose build --no-cache` |
| WebSocket connection failed | Check X-CSRF-Token header, clear browser cache |
| 3D viewer not loading | Check internet connection (3Dmol.js loads from CDN) |
| Model not found after training | Check volume mount — models saved in `data/qsar_models/` |
| Welcome screen empty | Fixed in v6.9.5 — forces chat mode on first login |

### Getting Help

- **GitHub Issues**: [github.com/tajo9128/BioDockify-Pharma-AI/issues](https://github.com/tajo9128/BioDockify-Pharma-AI/issues)
- **Health Check**: Visit `http://localhost/api/health`
- **Logs**: `docker compose logs -f --tail=100`

---

## 1.10 Updating to New Versions

```bash
# 1. Backup your data
backup-data.bat        # Windows
# OR
docker compose exec biodockify tar czf /tmp/backup.tar.gz /a0/usr

# 2. Pull latest image
docker compose pull

# 3. Restart with new image
docker compose down
docker compose up -d

# 4. Verify health
curl http://localhost/api/health
```

**Your data is safe** — volumes persist across container updates.
