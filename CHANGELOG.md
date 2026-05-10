# Changelog

All notable changes to **BioDockify** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v3.0.8] - 2026-02-23
### Fixed
- **Statistics API**: Fixed `CoxPHRequest` undefined error - changed to use existing `CoxRequest` model.

## [v3.0.7] - 2026-02-23
### Fixed
- **Dependencies**: Added missing `matplotlib`, `seaborn`, and `lifelines` packages required by the statistics module for survival analysis.

## [v3.0.6] - 2026-02-23
### Fixed
- **API Proxy**: Added Next.js rewrites to proxy `/api/*` requests to backend (port 8234), fixing chat connection issues in development mode.
- **Health Check**: Updated frontend health check to use proxied `/api/health` endpoint instead of direct backend URL.

## [v3.0.5] - 2026-02-23
### Fixed
- **Settings Panel**: Added close button to Settings panel that was previously unclosable due to full-screen overlay with no exit mechanism.

## [v2.6.10] - 2026-02-13
### Fixed
- **Docker Release Hardening**: Resolved environment variable mismatch (`BIODOCKIFY_DATA` vs `BIODOCKIFY_DATA_DIR`) and removed redundant layer definitions in the Dockerfile.

## [v2.6.9] - 2026-02-13
### Fixed
- **CI Hardening**: Resolved persistent `sqlite3.OperationalError` (Readonly DB) by enforcing absolute writable paths for `AdvancedMemorySystem` and `MultiTaskScheduler` via `BIODOCKIFY_DATA_DIR`.
- **Noise Reduction**: Fully suppressed ChromaDB/PostHog telemetry noise in CI logs using system environment variables.
- **Pydantic V2 Migration**: Fixed remaining `PydanticDeprecatedSince20` warnings in `BaseProvider` by adopting `ConfigDict`.
- **API Stability**: Added missing `title` field to `TaskStatus` model to resolve frontend deserialization errors.

## [v2.4.9] - 2026-02-10
### Added
- **Production Efficiency**: Final build optimizations for v2.4.9 release.
- **Version Unified**: Synchronized metadata across all systems to v2.4.9.

## [v2.4.8] - 2026-02-10
### Added
- **Production Efficiency**: Final build optimizations for stable release.
- **Version Unified**: Synchronized metadata across all systems.

## [v2.4.7] - 2026-02-10
### Fixed
- Build-blocking ESLint errors (unescaped entities, require imports)
- Version sync across all project files

## [v2.4.6] - 2026-02-10
### Added
- **Stability and Performance**: Continued optimization of the Docker build process and dependency management.

## [v2.4.5] - 2026-02-10
### Fixed
- **Docker Build Recovery**: Resolved `Unknown lockfile version` error by removing corrupt lockfiles and updating the build process.
- **Dependency Stability**: Hardened UI dependency installation by allowing fresh lockfile generation during build.

## [v2.4.4] - 2026-02-10
### Added
- **Enhanced Project System**: Implemented `ProjectPlanner`, `DeviceStateManager`, and `MultiTaskScheduler` for complex research orchestration.
- **Persistence & Progress**: Added task queue persistence and granular progress tracking for long-running research jobs.
- **Headless Resilience**: Made Playwright an optional dependency, allowing the system to run in a degraded mode when browser environments are restricted.
- **Git Maintenance**: Consolidated repository branches into `CI` and `Docker-release`.

## [v2.4.2] - 2026-02-09
### Added
- **Full Agent Zero Port**: Reached 100% parity with original Agent Zero core, including PhDPlanner (stage-aware research), PersistentMemory (long-term knowledge retention), and self-healing ReasoningEngine.
- **Security Hardening**: Implemented strict HTML escaping in Telegram to prevent XSS, added path sanitization to all file downloads, and enforced authentication for the WhatsApp bridge.
- **Reliability Improvements**: Added Discord gateway heartbeat ACK tracking to prevent zombie connections and implemented per-channel rate limiting and download timeouts.
### Removed
- Feishu/Lark channel integration (deprecated as per user request).

## [v2.4.1] - 2026-02-09
### Fixed
- **Integrity:** Resolved critical SQLite connection leaks in `task_store.py` using context managers.
- **Resource Management:** Fixed memory leaks in `ZAIProvider` and `ServiceLifecycleManager` by ensuring timeouts are cleared.
- **API Resilience:** Added 60s timeout and non-JSON error handling to the frontend API client.
- **Logic:** Fixed undefined `prompt` variable in HuggingFace provider and initialized `tmp_path` for RAG uploads.
- **WebSocket:** Fixed reconnection leaks in `AgentStatusPanel.tsx`.

## [v2.4.0] - 2026-02-08
...
