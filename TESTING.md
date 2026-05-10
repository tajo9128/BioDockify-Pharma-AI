# BioDockify AI - Testing Guide
## v3.7.0

Lightweight AI Research Assistant for PhD Scholars

---

## Quick Start (Docker Desktop)

### Option 1: Docker Compose (Recommended)
```bash
# Place docker-compose.yml in your folder
# Create a data folder next to it
mkdir data

# Run
docker compose up -d

# Open browser
http://localhost:3000
```

### Option 2: Direct Run
```bash
docker run -d ^
  --name biodockify-ai ^
  -p 3000:3000 ^
  -v ./data:/app/data ^
  -e OLLAMA_URL=http://host.docker.internal:11434 ^
  -e PORT=3000 ^
  -e NODE_ENV=production ^
  --extra-hosts "host.docker.internal:host-gateway" ^
  tajo9128/biodockify-ai:latest
```

### Option 3: Use run.bat
```batch
run.bat
```

---

## Docker Desktop Settings

### ports
- `3000:3000` - Main app

### volumes  
- `./data:/app/data` - Persists all data

### environment
```
OLLAMA_URL=http://host.docker.internal:11434
PORT=3000
NODE_ENV=production
DEFAULT_PROVIDER=ollama
```

Optional API Keys:
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
MOONSHOT_API_KEY=sk-...
```

---

## First Launch

### 1. System Check (Automatic)
On first open, BioDockify AI checks:
- 🌐 Internet connectivity
- 🦙 Ollama status (if running)
- 🔑 API configurations

### 2. Setup Options

**Option A: Local Ollama (Recommended)**
```bash
# Install from https://ollama.ai
ollama serve
ollama pull llama3.2
```

**Option B: Cloud APIs**
1. Go to Settings tab
2. Enter API keys
3. Save

---

## Features

### Tabs (7)
| Tab | Purpose |
|-----|---------|
| Chat | AI conversation |
| Search | Literature search |
| Deep Research | Web + papers |
| Knowledge Base | Store & search docs |
| Writing | Thesis templates |
| PhD Journey | Project tracking |
| Settings | Configuration |

### AI Providers (11)
- Ollama (local)
- OpenAI (gpt-4o, o1)
- Anthropic (claude)
- DeepSeek
- SiliconFlow (Chinese)
- Zhipu GLM (Chinese)
- Qwen (Alibaba)
- Moonshot (Chinese)
- MiniMax (Chinese)
- Yi (01.AI)

### Skills System
| Skill | Command |
|-------|---------|
| Literature Review | /lit |
| Data Analysis | /analyze |
| Thesis Writing | /thesis |
| Research Planner | /plan |

---

## Data Persistence

All data saved in `./data` folder:
```
data/
├── settings.json
├── phd_workflow/
├── notes/
├── documents/
├── knowledge_base/
└── skills/
```

---

## Troubleshooting

### Ollama not connecting
- Install Ollama from ollama.ai
- Start: `ollama serve`
- Verify URL in Settings

### Port 3000 in use
```bash
docker stop biodockify-ai
# or
docker rm biodockify-ai
```

### View logs
```bash
docker logs biodockify-ai
```

---

## Docker Hub
- Image: `tajo9128/biodockify-ai:latest`
- Hub: https://hub.docker.com/r/tajo9128/biodockify-ai