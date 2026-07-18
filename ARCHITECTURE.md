# BioDockify Pharma AI — System Architecture

## Overview

BioDockify Pharma AI is a pharmaceutical research platform built on the **Agent Zero v2.0** framework. It runs as a single Docker container with a Python/Flask backend, Alpine.js frontend, and supervisord process management.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                       │
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   Caddy     │  │  SearXNG    │  │    Cron     │      │
│  │ (reverse    │  │ (web search)│  │ (scheduled  │      │
│  │  proxy)     │  │             │  │  tasks)     │      │
│  └──────┬──────┘  └─────────────┘  └─────────────┘      │
│         │                                                 │
│  ┌──────▼──────┐                                         │
│  │  Flask API  │ ← 155+ API handlers (api/*.py)          │
│  │  (port 80)  │ ← Auto-discovered by filename           │
│  └──────┬──────┘                                         │
│         │                                                 │
│  ┌──────▼──────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   Agent     │  │  Knowledge  │  │  Modules    │      │
│  │   Zero      │  │    Base     │  │ (QSAR, MD,  │      │
│  │ (LLM core)  │  │ (files +    │  │  Docking,   │      │
│  │             │  │  FAISS)     │  │  Statistics) │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              Data Volumes                            │ │
│  │  /a0/usr        → workspace, chats, projects         │ │
│  │  /a0/.a0proj    → agent memory, instructions         │ │
│  │  /a0/data       → knowledge base, research sessions  │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         │
    ┌────▼────┐
    │ Browser │ ← Alpine.js + Web Components
    │ (UI)    │   22 desktop modules
    └─────────┘
```

## Components

### Frontend (Alpine.js)
- **Technology**: Alpine.js, Web Components, vanilla JS
- **State management**: Alpine.js stores (`createStore`)
- **22 desktop modules** registered in `desktop-store.js`
- **No build step** — direct HTML/JS served by Caddy

### Backend (Flask API)
- **Technology**: Python 3.12, Flask, asyncio
- **155+ API handlers** in `api/*.py`
- **Auto-discovery**: `helpers/api.py` loads handlers by filename
- **Pattern**: `class XxxHandler(ApiHandler): async def process(self, input, request)`

### Agent Zero Core
- **LLM orchestration**: Multi-provider support (OpenRouter, OpenAI, Anthropic, Ollama)
- **Tool system**: 30 tool prompts in `prompts/agent.system.tool.*.md`
- **Memory**: FAISS vector store at `/a0/.a0proj/memory/`
- **Extensions**: Plugin system in `agent_zero/extensions_v19/`

### Knowledge Base
- **Storage**: File-based (`/a0/data/knowledge_base/`) with `index.json`
- **20 categories**: literature, deep_research, docking, qsar, pharmacophore, statistics, md_simulation, drug_analysis, pharmacology, medicinal_chemistry, clinical, formulation, pharma_analysis, natural_products, regulatory, faculty, notes, misc
- **Auto-store**: `modules/knowledge/auto_store.py` — all modules auto-store results

### Modules (Pharma-Specific)
| Module | Actions | Category |
|--------|---------|----------|
| Formulation | 6 (kinetics, f2, nanoparticle, stability, excipients, DOE) | formulation |
| Clinical | 6 (DDI, TDM, renal, hepatic, naranjo, CKD-EPI) | clinical |
| Pharma Analysis | 5 (validation, f2, degradation, chromatography, LOD/LOQ) | pharma_analysis |
| Natural Products | 6 (phytochemical, extraction, IC50, plant DB, dereplication, SI) | natural_products |
| Regulatory | 5 (eCTD, ICH, stability, BE, IND/NDA) | regulatory_enhanced |
| Pharmacology | 7 (binding, dose-response, Schild, operational, selectivity, receptor DB, in-vivo) | pharmacology |
| Medicinal Chemistry | 10 (Murcko, MMPA, clustering, SMARTS, SA, retrosynthesis, named reactions, protecting groups, toxicophore, stereo) | medicinal_chemistry |

### Docker & Deployment
- **Single container** with supervisord managing 5 services
- **3 volumes**: `biodockify_usr`, `biodockify_data`, `biodockify_a0proj`
- **Health check**: `/api/health` every 30s
- **Auto-backup**: Daily at 3 AM + on startup, captures all 3 data paths

## Data Flow

```
User Request → Browser → Caddy → Flask API → Handler → Module
                                                    ↓
                                              auto_store()
                                                    ↓
                                          Knowledge Base (/a0/data/knowledge_base/)
                                                    ↓
                                          Academic Writer (loads by category)
```

## Security

- **CORS**: Localhost-only whitelist
- **CSRF**: Token-based protection on all write endpoints
- **Auth**: Session-based with `requires_auth` per handler
- **File uploads**: 35-extension whitelist, 50MB/file limit

## Version

Current: **v7.5.2** (see `version_info.txt`)
