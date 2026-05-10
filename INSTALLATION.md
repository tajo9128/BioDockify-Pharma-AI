# Installation Guide (Docker Edition)

**BioDockify v2.4.9** is now a pure Docker-based application. This ensures maximum consistency across environments and simplifies the deployment of its heavy pharmaceutical research engines.

## System Requirements

*   **Operating System:** Windows 10/11, Linux (Ubuntu/Debian recommended), or macOS (Intel/M-series)
*   **Processor:** Intel Core i5 / AMD Ryzen 5 or better (AVX support required)
*   **RAM:** 16 GB minimum (32 GB recommended for large knowledge graphs)
*   **Disk Space:** 20 GB free space (for Docker images and database)
*   **Software:** Docker Desktop (Windows/Mac) or Docker Engine (Linux)

---

## Step-by-Step Installation

### 1. Prerequisites (Docker)
BioDockify relies on **Docker** to run its specialized AI models (BioBERT, GROBID, etc.) in a consistent environment.

1.  Download and install **Docker Desktop** from [docker.com](https://www.docker.com/).
2.  Ensure Docker is running and healthy.

### 2. Launch BioDockify
Since BioDockify is a pure Docker application, you can start it with a single command:

```bash
docker pull tajo9128/biodockify-ai:latest
docker run -d -p 3000:3000 --name biodockify -v biodockify-data:/app/data --restart unless-stopped tajo9128/biodockify-ai:latest
```

### 3. Access the Workstation
1.  Open your browser to: **[http://localhost:3000](http://localhost:3000)**.
2.  The application will initialize its local databases and load AI models on the first run.

---

## Troubleshooting

### "Read timed out" during Initialization
*   **Cause:** Heavy AI dependencies are loading (especially on the first run).
*   **Fix:** Wait another 60-90 seconds and refresh. The system is designed to self-heal once the backend is ready.

### CSS 404 or Style Issues
*   **Cause:** Nginx routing conflict or outdated image.
*   **Fix:** Ensure you pulled the latest version (`v2.4.0+`) which includes the Nginx static routing fixes.

### "Backend Connection Failed"
*   **Cause:** Port conflict on port 3000.
*   **Fix:** Ensure no other services are using port 3000. You can map a different host port if needed: `-p 5000:3000`.

---
**Need Help?**
Open an issue on the [GitHub repository](https://github.com/tajo9128/BioDockify-pharma-research-ai/issues).
