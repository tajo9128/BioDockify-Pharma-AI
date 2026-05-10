# =============================================================================
# BioDockify v2.9.9 - Optimized Multi-Stage Docker Image
# =============================================================================

# -----------------------------------------------------------------------------
# BioDockify AI - v2.9.9 - Dockerfile
# -----------------------------------------------------------------------------
FROM oven/bun:1.1-alpine AS frontend-builder
WORKDIR /app/ui
COPY ui/package.json ui/bun.lock* ./
RUN bun install
COPY ui/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN bun run build

# -----------------------------------------------------------------------------
# Stage 2: Backend Builder (Python Environment)
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS backend-builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ cmake curl git libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY api/requirements.txt ./
COPY api/requirements_heavy.txt ./

# Install core requirements first
RUN pip install --no-cache-dir -r requirements.txt

# Install heavy requirements separately (index-url is in the file)
RUN pip install --no-cache-dir -r requirements_heavy.txt --extra-index-url https://download.pytorch.org/whl/cpu

COPY agent_zero/requirements_pharma.txt ./
# Install Pharma Intelligence Stack
RUN pip install --no-cache-dir -r requirements_pharma.txt

# ── CRITICAL: Strip the venv to reclaim ~2GB+ of space ──
# 1. Remove cache and tests (Standard cleanup only)
RUN find /opt/venv -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null; \
    find /opt/venv -type d -name 'tests' -exec rm -rf {} + 2>/dev/null; \
    find /opt/venv -type d -name 'test' -exec rm -rf {} + 2>/dev/null; \
# 2. Remove static libraries (Safe)
    find /opt/venv -type f -name '*.a' -delete 2>/dev/null; \
# 3. Remove pip, setuptools, wheel (not needed at runtime)
    pip uninstall -y pip setuptools wheel; \
    true


# -----------------------------------------------------------------------------
# Stage 3: Runtime Stage
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime
WORKDIR /app

# Ensure UTF-8 Locale
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Install runtime dependencies (OpenCV, FFmpeg, Poppler, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates libpq5 \
    libgl1 libglib2.0-0 ffmpeg poppler-utils \

    nginx supervisor chromium chromium-driver \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

# Copy virtual environment from builder
COPY --from=backend-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy Next.js standalone build
COPY --from=frontend-builder /app/ui/.next/standalone/ /app/
COPY --from=frontend-builder /app/ui/.next/static/ /app/.next/static/
COPY --from=frontend-builder /app/ui/public/ /app/public/

# Copy ALL application code (including missed directories)
COPY api/ /app/api/
COPY agent_zero/ /app/agent_zero/
COPY modules/ /app/modules/
COPY orchestration/ /app/orchestration/
COPY services/ /app/services/
COPY nlp/ /app/nlp/
COPY nanobot/ /app/nanobot/
COPY nanobot_bridge/ /app/nanobot_bridge/
COPY runtime/ /app/runtime/
COPY server.py /app/

# Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    NODE_ENV=production \
    BIODOCKIFY_DATA_DIR=/app/data \
    PORT=3000

# -----------------------------------------------------------------------------
# Inline Configurations
# -----------------------------------------------------------------------------

# Nginx Configuration
RUN rm -f /etc/nginx/sites-enabled/default && \
    echo 'server { \
    listen 3000; \
    server_name _; \
    location /_next/static/ { \
        alias /app/.next/static/; \
        expires 1y; \
        access_log off; \
        add_header Cache-Control "public, max-age=31536000, immutable"; \
    } \
    location /public/ { \
        alias /app/public/; \
    } \
    location / { \
        proxy_pass http://127.0.0.1:3001; \
        proxy_http_version 1.1; \
        proxy_set_header Upgrade $http_upgrade; \
        proxy_set_header Connection "upgrade"; \
        proxy_set_header Host $host; \
    } \
    location /api/ { \
        proxy_pass http://127.0.0.1:3000/api/; \
    } \
    location /health { \
        return 200 "OK"; \
    } \
}' > /etc/nginx/conf.d/biodockify.conf

# Supervisor Configuration
RUN echo '[supervisord] \n\
nodaemon=true \n\
\n\
[program:nginx] \n\
command=nginx -g "daemon off;" \n\
\n\
[program:backend] \n\
command=python /app/server.py \n\
environment=PYTHONPATH="/app",PYTHONUNBUFFERED="1" \n\
\n\
[program:frontend] \n\
command=/usr/bin/node /app/server.js \n\
environment=PORT="3001",HOSTNAME="0.0.0.0",NODE_ENV="production" \n\
' > /etc/supervisor/conf.d/biodockify.conf

# Startup Scripts
LABEL version="v2.9.9"
LABEL description="BioDockify - Pharma Research AI"
RUN echo '#!/bin/bash \n\
echo "BioDockify v2.9.8 - Optimized Launch" \n\
echo "Node Version: $(node -v)" \n\
echo "Node Path: $(which node)" \n\
mkdir -p /app/data \n\
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf \n\
' > /app/start.sh && chmod +x /app/start.sh

# Final Setup
EXPOSE 3000
VOLUME ["/app/data"]
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -sf http://localhost:3000/health || exit 1

CMD ["/app/start.sh"]
