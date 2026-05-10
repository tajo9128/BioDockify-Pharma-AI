# BioDockify AI - Lightweight Docker
# Stage 1: Build Next.js frontend (standalone)
# ======================================================
FROM oven/bun:1.1-alpine AS frontend-builder
WORKDIR /build
COPY ui/package.json ui/bun.lock* ./
RUN bun install
COPY ui/ ./
ENV NEXT_TELEMETRY_DISABLED=1
ENV BACKEND_URL=http://localhost:8000
RUN bun run build

# Stage 2: Python backend + standalone frontend
# ======================================================
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends nodejs && rm -rf /var/lib/apt/lists/*

COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/agent_zero_backend/server.py .
COPY src/agent_zero_backend/*.md ./
COPY src/writing ./writing
COPY src/pharma ./pharma

COPY --from=frontend-builder /build/.next/standalone /app/frontend
COPY --from=frontend-builder /build/.next/static /app/frontend/.next/static
COPY --from=frontend-builder /build/public /app/frontend/public

RUN mkdir -p /app/data/knowledge_base /app/data/phd_workflow /app/data/notes /app/data/documents /app/data/skills

ENV OLLAMA_URL=http://host.docker.internal:11434

EXPOSE 3000

RUN printf '#!/bin/sh\nBACKEND_PORT=8000 python /app/server.py &\ncd /app/frontend && PORT=3000 node server.js\n' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]