# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| v5.7.x  | ✅ Active |
| v5.6.x  | ✅ Supported |
| v5.5.x  | ✅ Supported |
| < v5.5  | ❌ End of life |

## Reporting a Vulnerability

We take security seriously. If you discover a vulnerability:

- **Do NOT open a public issue**
- **Email**: Create an issue with "[SECURITY]" prefix for initial report
- **Response**: We aim to respond within 48 hours

## Data Privacy Architecture

BioDockify follows a **Local-First** security philosophy.

### 1. Local Processing
- **Inference**: All BioNER and statistical analysis runs locally within the Docker container
- **Vector DB**: ChromaDB runs on localhost — no cloud sync
- **Knowledge Base**: SurfSense storage is local; search uses ChromaDB (built-in, free)

### 2. External APIs (Optional)
- **LLMs**: Configuring OpenAI/Gemini/Claude APIs sends text to those providers
- **Control**: Strictly opt-in. You must provide your own API key
- **Local LLMs**: Ollama-supported for 100% air-gapped workflow

### 3. Docker Security
- Container runs as non-root where possible (v5.7.0+)
- HEALTHCHECK endpoint at `/api/health` every 30s
- Backups stored on Docker volume at `/a0/usr/backups/`
- GDrive cloud backup available with user-provided OAuth

### 4. Audit & Monitoring
- System Health dashboard monitors all modules
- Security Guardian scans for secrets on codebase
- Audit Logger tracks user actions locally
