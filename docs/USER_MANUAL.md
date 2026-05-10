# BioDockify AI Desktop Edition - User Manual

## Table of Contents
1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [Initial Setup](#initial-setup)
5. [Features Guide](#features-guide)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)

---

## Introduction

**BioDockify AI** is a zero-cost pharmaceutical research platform that enables literature analysis, entity extraction, knowledge graph building, and lab protocol generation.

### Key Features
- 📚 **Literature Analysis** - Parse PDFs and extract biomedical entities
- 🧬 **Entity Extraction** - Identify drugs, diseases, proteins, and genes
- 🔗 **Knowledge Graph** - Build connections between entities using Neo4j
- 📋 **Lab Protocols** - Generate SiLA 2 XML protocols and DOCX reports
- 🌐 **Zero-Cost AI** - Runs locally with Ollama or use your own API keys

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 | Windows 11 |
| RAM | 8 GB | 16 GB |
| Storage | 5 GB | 20 GB |
| Python | 3.10+ | 3.11 |
| Node.js | 18+ | 20 LTS |

### Required Software
- **Python 3.10+** - For the FastAPI backend
- **Neo4j** - For knowledge graph storage
- **Ollama** (optional) - For local LLM inference

---

## Installation

### Step 1: Download the Installer
1. Go to [BioDockify Releases](https://github.com/tajo9128/BioDockify-pharma-research-ai/releases)
2. Download the latest `.exe` installer
3. Run the installer and follow the prompts

### Step 2: Install Backend Dependencies
Open a terminal in the install directory and run:
```bash
pip install -r requirements.txt
```

### Step 3: Start the Backend
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```
Or use the provided batch file:
```bash
start_backend.bat
```

### Step 4: Launch BioDockify
Double-click the **BioDockify AI** shortcut on your desktop.

---

## Initial Setup

### 1. Neo4j Configuration (Knowledge Graphs)

#### Option A: Docker (Recommended)
```bash
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

#### Option B: Manual Installation
1. Download from [neo4j.com/download](https://neo4j.com/download/)
2. Install and start Neo4j Desktop
3. Create a new database with password `password`

### 2. Ollama Setup (Local LLM)

#### Install Ollama
```bash
# Windows: Download from https://ollama.ai/download
# Then pull a model:
ollama pull llama3.2
```

#### Verify Ollama is Running
```bash
curl http://localhost:11434/api/tags
```

### 3. Configure BioDockify
Create `runtime/config.yaml`:
```yaml
# LLM Configuration
ollama_url: "http://localhost:11434"
model_name: "llama3.2"

# Neo4j Configuration
neo4j_host: "bolt://localhost:7687"
neo4j_user: "neo4j"
neo4j_password: "password"

# Optional: Cloud API Keys
openai_key: ""  # Leave empty for local mode
elsevier_key: ""  # For literature search
```

---

## Features Guide

### 1. Starting a Research Task

1. **Enter Research Topic**
   - Type your research topic (e.g., "Alzheimer's Drug Repurposing")
   - Click **Start Research**

2. **Monitor Progress**
   - Watch the 4-step pipeline:
     - 📖 Literature Search
     - 🔍 Entity Extraction
     - 🔗 Graph Building
     - 📊 Synthesis

3. **View Results**
   - Extracted entities (drugs, diseases, proteins)
   - Knowledge graph connections
   - Research summary

### 2. Entity Types Detected

| Entity Type | Color | Example |
|-------------|-------|---------|
| Drug | 🔵 Blue | Donepezil, Memantine |
| Disease | 🔴 Red | Alzheimer's, Parkinson's |
| Protein | 🟢 Green | BACE1, APP, Tau |
| Gene | 🟣 Purple | APOE, PSEN1 |

### 3. Knowledge Graph

The knowledge graph shows relationships:
- Drug → TREATS → Disease
- Drug → BINDS → Protein
- Gene → CAUSES → Disease

**Viewing the Graph:**
1. Complete a research task
2. Click "View Knowledge Graph"
3. Use mouse to pan/zoom
4. Click nodes for details

### 4. Lab Protocol Generation

Generate protocols for lab automation:

1. **Select Research Session**
2. Click **Generate Protocol**
3. Choose format:
   - **SiLA 2 XML** - For liquid handlers
   - **DOCX Report** - For documentation

### 5. Settings

Access via the ⚙️ icon:

#### LLM Mode
- **Local (Ollama)** - Free, runs on your machine
- **Cloud (OpenAI)** - Requires API key, faster

#### Database
- Configure Neo4j connection
- Test connection status

---

## Configuration

### config.yaml Options

```yaml
# ===== LLM Settings =====
ollama_url: "http://localhost:11434"
model_name: "llama3.2"  # or llama3, mistral, etc.

# Cloud Mode (optional)
openai_key: "sk-..."
openai_model: "gpt-4o-mini"

# ===== Database Settings =====
neo4j_host: "bolt://localhost:7687"
neo4j_user: "neo4j"
neo4j_password: "your-password"

# ===== API Settings =====
backend_port: 8000
cors_origins: ["http://localhost:3000"]

# ===== Literature Search =====
elsevier_key: ""  # Scopus API key
pubmed_email: ""  # For PubMed API
```

### Environment Variables

Alternative to config.yaml:
```bash
set OPENAI_API_KEY=sk-...
set NEO4J_PASSWORD=password
set OLLAMA_HOST=http://localhost:11434
```

---

## Troubleshooting

### Backend Won't Start

**Error:** `ModuleNotFoundError: No module named 'xxx'`
```bash
pip install -r requirements.txt
```

**Error:** Port 8000 already in use
```bash
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Neo4j Connection Failed

1. Verify Neo4j is running:
   ```bash
   curl http://localhost:7474
   ```
2. Check credentials in config.yaml
3. Ensure firewall allows port 7687

### Ollama Not Responding

1. Check if Ollama is running:
   ```bash
   ollama list
   ```
2. Restart Ollama:
   ```bash
   ollama serve
   ```
3. Verify model is downloaded:
   ```bash
   ollama pull llama3.2
   ```

### App Shows Blank Screen

1. Check if backend is running at http://localhost:8000
2. Open DevTools (F12) → Console for errors
3. Clear cache: `Ctrl+Shift+R`

### Build/Release Issues

For CI/CD issues, check:
- [GitHub Actions](https://github.com/tajo9128/BioDockify-pharma-research-ai/actions)
- Ensure all secrets are configured

---

## Support

- **GitHub Issues:** [Report bugs](https://github.com/tajo9128/BioDockify-pharma-research-ai/issues)
- **Documentation:** Check `docs/` folder in the repository

---

## Quick Start Checklist

- [ ] Download and install BioDockify
- [ ] Install Python dependencies (`pip install -r requirements.txt`)
- [ ] Start Neo4j (Docker or manual)
- [ ] Install Ollama and pull a model
- [ ] Create `runtime/config.yaml`
- [ ] Start backend (`python -m uvicorn api.main:app`)
- [ ] Launch BioDockify AI desktop app
- [ ] Enter a research topic and start!

---

**Version:** 1.0.29  
**Last Updated:** January 2026
