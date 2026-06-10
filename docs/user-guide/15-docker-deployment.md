# Chapter 15: Docker & Deployment

## 15.1 Docker Architecture

BioDockify runs in Docker with two Python runtimes:

| Runtime | Path | Python | Purpose |
|---------|------|--------|---------|
| Framework | `/opt/venv-a0` | 3.12 | Backend, API, core logic |
| Execution | `/opt/venv` | 3.13 | Agent code execution, pip installs |

---

## 15.2 Docker Compose Configuration

```yaml
services:
  biodockify:
    image: tajo9128/biodockify-pharma-ai:v6.9.5
    ports:
      - "50001:50001"
    volumes:
      - biodockify_usr:/a0/usr
      - biodockify_data:/a0/data
      - biodockify_tmp:/a0/tmp
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
```

---

## 15.3 Volume Mounting Best Practices

| Volume | Contents | Critical? |
|--------|----------|-----------|
| `/a0/usr` | User data, plugins, uploads, settings | YES |
| `/a0/data` | Models, databases, QSAR models | YES |
| `/a0/tmp` | Docking jobs, temp files | Recommended |

---

## 15.4 Port Configuration

Default: `50001`

Change in `docker-compose.yml`:
```yaml
ports:
  - "8080:50001"  # Access via http://localhost:8080
```

---

## 15.5 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes* | LLM provider access |
| `OPENAI_API_KEY` | Alternative | OpenAI API |
| `ANTHROPIC_API_KEY` | Alternative | Anthropic API |
| `OLLAMA_HOST` | Optional | Local Ollama server |

*At least one LLM provider key required.

---

## 15.6 Resource Allocation

```yaml
deploy:
  resources:
    limits:
      memory: 8G
      cpus: '4'
```

---

## 15.7 Cloud Deployment

### AWS EC2
```bash
sudo yum install docker
git clone https://github.com/tajo9128/BioDockify-Pharma-AI.git
cd BioDockify-Pharma-AI
docker compose up -d
```

### Google Cloud Compute
```bash
sudo apt install docker.io
git clone https://github.com/tajo9128/BioDockify-Pharma-AI.git
cd BioDockify-Pharma-AI
docker compose up -d
```

---

## 15.8 Updating

```bash
docker compose pull
docker compose down
docker compose up -d
```

---

## 15.9 HEALTHCHECK

The container includes a health check:
```dockerfile
HEALTHCHECK --interval=30s --timeout=15s --retries=3 CMD \
  python3 -c "from rdkit import Chem; Chem.MolFromSmiles('CCO')" && \
  curl -sf http://localhost:50001/api/health || exit 1
```
