# Installation Guide — BioDockify Pharma AI v7.5.2

BioDockify runs as a single Docker container. One command to install, one command to start.

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **OS** | Windows 10+, Linux, macOS | Any with Docker Desktop |
| **RAM** | 8 GB | 16 GB+ |
| **Disk** | 10 GB free | 20 GB+ |
| **Docker** | Docker Desktop 4.x | Latest stable |
| **CPU** | 4 cores | 8+ cores |

## Quick Start

### Windows / macOS

```bash
# 1. Install Docker Desktop from https://www.docker.com/
# 2. Create backup folder
mkdir C:\Users\%USERNAME%\biodockify-backups

# 3. Run BioDockify
docker run -d ^
  --name biodockify ^
  -p 80:80 ^
  -v biodockify_usr:/a0/usr ^
  -v biodockify_data:/a0/data ^
  -v biodockify_a0proj:/a0/.a0proj ^
  -v C:\Users\%USERNAME%\biodockify-backups:/a0/usr/backups ^
  --restart unless-stopped ^
  tajo9128/biodockify-pharma-ai:latest

# 4. Open http://localhost in your browser
```

### Linux

```bash
# 1. Install Docker Engine
curl -fsSL https://get.docker.com | sh

# 2. Create backup folder
mkdir -p ~/biodockify-backups

# 3. Run BioDockify
docker run -d \
  --name biodockify \
  -p 80:80 \
  -v biodockify_usr:/a0/usr \
  -v biodockify_data:/a0/data \
  -v biodockify_a0proj:/a0/.a0proj \
  -v ~/biodockify-backups:/a0/usr/backups \
  --restart unless-stopped \
  tajo9128/biodockify-pharma-ai:latest

# 4. Open http://localhost in your browser
```

### Docker Compose

Save as `docker-compose.yml` and run `docker compose up -d`:

```yaml
services:
  biodockify:
    image: tajo9128/biodockify-pharma-ai:latest
    container_name: biodockify
    ports:
      - "80:80"
    volumes:
      - biodockify_usr:/a0/usr
      - biodockify_data:/a0/data
      - biodockify_a0proj:/a0/.a0proj
      - ~/biodockify-backups:/a0/usr/backups
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped

volumes:
  biodockify_usr:
  biodockify_data:
  biodockify_a0proj:
```

## Data Persistence

All research data lives in **3 Docker volumes**:

| Volume | Path | Contents |
|--------|------|----------|
| `biodockify_usr` | `/a0/usr` | Workspace, chats, projects, plugins |
| `biodockify_data` | `/a0/data` | Knowledge base, research sessions |
| `biodockify_a0proj` | `/a0/.a0proj` | Agent memory, instructions, config |

**Your data survives container deletion** as long as you use named volumes.

## Backup

Backups are stored at `/a0/usr/backups/` (mapped to your PC via the host mount).

**Three ways to backup:**
1. **In-app**: Open Backup & Recovery panel → "Save to PC" (downloads .zip to your Downloads folder)
2. **Script**: Double-click `backup-data.bat` (Windows) to save all 3 data locations to Desktop
3. **Automatic**: Backups run daily at 3 AM and on every container startup

## Updating

```bash
# Stop and remove old container (data is safe in volumes)
docker stop biodockify && docker rm biodockify

# Pull latest image
docker pull tajo9128/biodockify-pharma-ai:latest

# Run with same volume names — all data returns automatically
docker run -d \
  --name biodockify \
  -p 80:80 \
  -v biodockify_usr:/a0/usr \
  -v biodockify_data:/a0/data \
  -v biodockify_a0proj:/a0/.a0proj \
  -v ~/biodockify-backups:/a0/usr/backups \
  --restart unless-stopped \
  tajo9128/biodockify-pharma-ai:latest
```

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Container won't start | Port 80 in use | Use `-p 8080:80` and visit `http://localhost:8080` |
| "Unhealthy" status | Still initializing | Wait 60 seconds, then refresh |
| Data missing | Wrong volume names | Ensure all 3 volumes use correct names |
| Slow first response | Model warmup | Normal on first request after restart |
| No AI responses | No API key configured | Open Settings → add your API key |

## Support

- [GitHub Issues](https://github.com/tajo9128/BioDockify-Pharma-AI/issues)
- [Docker Hub](https://hub.docker.com/r/tajo9128/biodockify-pharma-ai)
