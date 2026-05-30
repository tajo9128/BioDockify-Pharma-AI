# Chapter 12: System Administration

## 12.1 System Health
Real-time monitoring of all dependencies.

### Access Path
**All Tools → System Health** (or click ❤️ icon)

### Health Badges (Header)
| Badge | Status | Meaning |
|-------|--------|---------|
| Vina | 🟢/🔴 | AutoDock Vina installed |
| CNN | 🟢/🟡/🔴 | GNINA: ok / Docker required / missing |
| RDKit | 🟢/🔴 | RDKit chemistry library |

### Full Health Check
Visit `http://localhost:50001/api/health` for JSON:
```json
{
  "health": {
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

---

## 12.2 Backup & Recovery

### What Survives Container Deletion

| Action | Data Safe? |
|--------|-----------|
| `docker compose restart` | ✅ Yes |
| `docker compose down` | ✅ Yes |
| `docker compose down -v` | ❌ NO — volumes deleted |
| `docker compose build --no-cache` | ✅ Yes |
| Uninstall Docker Desktop | ❌ NO — export first |

### Desktop Backup (Windows)
```cmd
backup-data.bat
```
Creates timestamped backup in project directory.

### Docker Backup
```bash
docker compose exec biodockify tar czf /tmp/backup.tar.gz /a0/usr
docker compose cp biodockify:/tmp/backup.tar.gz ./backup.tar.gz
```

### Restore
```bash
docker compose cp ./backup.tar.gz biodockify:/tmp/backup.tar.gz
docker compose exec biodockify tar xzf /tmp/backup.tar.gz -C /
```

---

## 12.3 Benchmark Suite
Run before large campaigns:
- API health checks
- Storage validation
- Memory utilization
- Dependency version matrix
- Pass/fail per check

---

## 12.4 Docker Commands Reference

| Command | Purpose |
|---------|---------|
| `docker compose up -d` | Start platform |
| `docker compose down` | Stop platform |
| `docker compose logs -f` | View logs |
| `docker compose build --no-cache` | Rebuild image |
| `docker compose pull` | Pull latest image |
| `docker compose restart` | Restart services |
| `docker exec -it biodockify bash` | Enter container shell |

---

## 12.5 Updating to New Versions
```bash
# 1. Backup
backup-data.bat

# 2. Pull & restart
docker compose pull
docker compose down
docker compose up -d

# 3. Verify
curl http://localhost:50001/api/health
```

---

## 12.6 Resource Allocation
Edit `docker-compose.yml`:
```yaml
services:
  biodockify:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
```

---

## 12.7 Cloud Deployment

### AWS
```bash
# EC2 instance with Docker
sudo yum install docker
git clone https://github.com/tajo9128/BioDockify-Pharma-AI.git
cd BioDockify-Pharma-AI
docker compose up -d
```

### Google Cloud
```bash
# Compute Engine with Docker
sudo apt install docker.io
git clone https://github.com/tajo9128/BioDockify-Pharma-AI.git
cd BioDockify-Pharma-AI
docker compose up -d
```
