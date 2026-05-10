# SurfSense Knowledge Engine

This module runs a local instance of **SurfSense**, the Unified Knowledge Engine for BioDockify. It replaces the previous Neo4j + Notebooks stack.

## Quick Start
1. Open this directory in terminal.
2. Run `docker-compose up -d`.
3. SurfSense Frontend: `http://localhost:3003` (Mapped from 3000)
4. SurfSense Backend: `http://localhost:8000`

## Integration
BioDockify connects to SurfSense backend at `http://localhost:8000` for:
- Deep Research (Search + Reasoning)
- File Management (Uploads are sent here)
- Podcast Generation

## Data
Data is persisted in the `surfsense-data` docker volume.
