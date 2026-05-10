# HeadlessX for BioDockify

This folder contains the setup for **HeadlessX**, a self-hosted headless browser service used by BioDockify to scrape complex websites (Scientific journals, Single Page Apps, heavily protected sites).

## Why use this?
BioDockify's default "Internet Search" uses a standard HTTP fetch, which is fast but fails on:
- Sites using Cloudflare/Akamai protection.
- Sites that load content via JavaScript (React, Vue, etc.).
- Scientific publishers that block simple bots.

**HeadlessX** solves this by running a real browser in a container, simulating human behavior.

## Quick Start

### Prerequisites
- Docker Desktop installed and running.

### 1. Start the Service
Open a terminal in this directory (`modules/headlessx`) and run:
```powershell
docker-compose up -d
```

That's it! HeadlessX will start on `http://localhost:3000`.

### 2. Verify
Visit `http://localhost:3000/api/health` in your browser. You should see `{"status":"ok"}`.

### 3. Usage in BioDockify
BioDockify (v2.13.53+) automatically detects if HeadlessX is running at `http://localhost:3000` and uses it for web scraping.

## Configuration
Edit `docker-compose.yml` to change:
- `MAX_CONCURRENT_SESSIONS`: Number of parallel tabs (Default: 5).
- `AUTH_TOKEN`: If you add this, update `ui/src/lib/web_fetcher.ts` with the token.
