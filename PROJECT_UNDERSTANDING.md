# BioDockify Pharma AI — Deep Project Understanding

> **Source:** Consolidated from the morning discovery session (2026-06-25, ZCode session `sess_5d45f4af`).
> This document is the single source of truth for *what this project is, how it's built,
> what's broken, and what the goal is.* It exists so the understanding is never lost to a session reset.
> Last updated: 2026-06-25.

---

## 1. The Goal (verbatim, set 12:16:57)

```
Full Agent Zero v2.0
+ Proper Addition of full working pharma modules and it dependancies
+ Agent0 must identify it as its own core file, must oschestrate it, edit it, diagnose it
= Perfect BioDockify Pharma AI — handle with care, full complex and delicate merge it is
```

**In plain terms:**
1. Bring in **upstream Agent Zero v2.0** (upgrade the core).
2. **Keep all pharma modules + their dependencies** fully working.
3. The agent must **own its own core** — be able to orchestrate, edit, and diagnose itself.
4. End state = a clean, working **BioDockify Pharma AI**.
5. Constraint: **DELICATE MERGE — do not damage Agent Zero core; do not undo the rebrand.**

---

## 2. What BioDockify Pharma AI Is

- A **pharmaceutical research AI assistant** built as a fork of Agent Zero (by Jan Tomasek).
- **v6.9.15**, ~4756 files, 16+ mature pharma modules.
- The fork keeps Agent Zero **intact** and layers pharma modules on top (the `/a0/` + `modules/` + `api/` pattern).
- Identity: "BioDockify AI" — a pharma research assistant, NOT a generic agent.
- Repo: `github.com/tajo9128/BioDockify-Pharma-AI`, cloned to `F:/Pharma-AI/BioDockify-Pharma-AI`.

---

## 3. The Two-Layer Architecture (CRITICAL INSIGHT)

The fork runs **two things in parallel**:

### Layer A — Flat Agent Zero core (the UPGRADE TARGET)
- Root: `agent.py` (39KB, 1043 lines), `models.py` (30KB), `initialize.py`, `run_ui.py`, `preload.py`
- `helpers/` (~90 files) — canonical Agent Zero helper package
- `prompts/` — stock Agent Zero prompt control-plane (modified for pharma identity)
- `webui/`, `ui/`, `public/`, `assets/` — stock Agent Zero frontend (Next.js/bun)
- Docker core: `Dockerfile.release`, `docker-compose.yml`, `Caddyfile`
- **This layer is an OLDER agent-zero than v2.0** — smaller files, missing newer helpers. This is what v2.0 will update.

### Layer B — BioDockify pharma add-on (MUST SURVIVE the merge, untouched by upstream)
- `agent_zero/` package — the rebranded "BioDockify AI" experimental layer (v19/hybrid/core). **Upstream v2.0 has NOTHING equivalent. 100% fork-owned.**
- `modules/` — 40+ pharma research module subdirs
- `api/` — ~160 endpoint files (one `ApiHandler` subclass per file)
- `orchestration/`, `services/`, `lab_interface/`, `nlp/`, `runtime/`, `skills/`, `tools/`
- `src/` — parallel BioDockify backend layer
- `.a0proj/`, `conf/`, `data/`, `knowledge/`, `library_data/`
- Identity/config docs: `identity.md`, `AGENTS.md`, `ARCHITECTURE.md`, `RESEARCH_MANAGEMENT_SYSTEM.md`, etc.

**The golden rule:** "Agent Zero is the foundation. Do not damage it. BioDockify is an *add-on* layer on top of intact Agent Zero. Files that legitimately show 'agent zero' are correct and must be left alone."

---

## 4. The Module Convention (how to add modules correctly)

Learned from `MD Lite` (the newest module) — the canonical pattern:

1. **`api/<name>.py`** — an `ApiHandler` subclass with an action-routed `process()` method (base class = `helpers/api.py`).
2. **`modules/<name>/`** — the backend engine.
3. **Frontend panel** in `webui/components/`.
4. **Work dirs** under `usr/`.
5. **Dockerfile.release + health-check updates**.

**Server entry point:** `run_ui.py` → Flask + Socket.IO + uvicorn on port 80. Each `api/<name>.py` is loaded on-demand by `helpers/ws.py`'s dynamic handler resolution.

---

## 5. The Diagnosis — Bugs Found (root-cause, evidence-based)

### Bug Class 1: The incomplete rebrand (SINGLE ROOT CAUSE — biggest issue)
A **mass find-replace turned `agent_zero` → `biodockify.ai`** everywhere — including *inside Python identifiers and import paths where dots are illegal.*

- `def _get_biodockify.ai_version()` — **illegal** (function names can't contain a dot; parse-time syntax error).
- `from biodockify.ai.hybrid.agent import ...` — **illegal** (no `biodockify/ai/` dir exists; real dir is `agent_zero/`).
- `biodockify.ai_executions_total` — **illegal Prometheus metric name** (dots invalid; would `ValueError` at runtime, then `KeyError` in the lookup fallback).

**Scope:** 19 files, ~72 occurrences, concentrated in:
- `agent_zero/core/` (`agent_with_monitoring.py`)
- `agent_zero/hybrid/` (`agent.py`, `diagnosis.py`, `memory.py`, `prompts.py`, `channels/`, `connectors/`, `tools/`)
- `agent_zero/helpers_v19/` (`backup.py`, `git.py`, `mcp_server.py`, `self_update.py`, `update_check.py`, `fasta2a_server.py`)
- `modules/literature/discovery.py`, `tests/test_surfsense_fixes.py`

**The fix (decided with user):**
- `biodockify.ai` → **`agent_zero`** in import/module paths (matches the real dir).
- `biodockify.ai_X` → **`biodockify_ai_X`** in identifiers/code (the user's chosen underscore form).
- Display strings & docstrings keep "BioDockify AI".
- **Proof this is correct:** the working `skills/*/SKILL.md` files already use `from agent_zero.skills.X` — so `agent_zero` is the intended package path; `biodockify.ai` is purely the damage.

### Bug Class 2: `type X = Literal` (PEP 695) — Python version issue, needs 3.12+.

### Bug Class 3: Vendored third-party baselines — `skills/deep_drive/clef*` (pan12/pan13 research baselines). NOT theirs to fix; leave alone.

### KEY FINDING — live vs dead code:
- ✅ **The live BioDockify system runs fine** — all 7 entry-point files compile clean.
- The `biodockify.ai` corruption lives **entirely in experimental/v19/hybrid subsystems** that no live entry point imports.
- ⚠️ **EXCEPTION:** `agent_zero/core/agent_with_monitoring.py` is corrupted AND **imported by the test suite** (`tests/conftest.py`, `tests/benchmarks/agent_eval.py`) → `pytest` collection will **crash before any test runs.** This one is not dead code — fixing it unblocks the whole test suite.
- The `hybrid/` subsystem is the **dependency root** — fix `hybrid/agent.py` first, then the monitoring wrapper, then isolated `helpers_v19/` files.

---

## 6. The v2.0 Merge Conflict Surface (the delicate part)

### Structural fact (read first)
**Upstream v2.0 is a FLAT layout — there is NO `agent_zero/` package.** Its core lives in root `agent.py` + `models.py` + `helpers/`. So "update core to v2.0" = update the fork's **flat-layout** files, while leaving `agent_zero/`, pharma `api/` handlers, pharma `tools/`, and `Dockerfile.release` completely alone.

### Files byte-identical to v2.0 (safe, no change needed)
`initialize.py`, `jsconfig.json`, `requirements.dev.txt`, `run_tunnel.py`, `update_reqs.py`, `helpers/ws_manager.py`

### Fork's flat core is OLDER than v2.0 (upgrade targets)
| File | v2.0 | Fork | Note |
|---|---|---|---|
| `agent.py` | 60KB (1586 ln) | 39KB (1043 ln) | Fork older, NOT rebranded (0 biodockify hits) |
| `models.py` | 36KB | 30KB | Fork older |
| `helpers/skills.py` | 44KB | 33KB | Fork behind by 11KB |
| `helpers/mcp_handler.py` | 61KB | 47KB | Fork behind by 15KB |
| `helpers/settings.py` | 27KB | 25KB | -2.5KB |
| `helpers/history.py` | 25KB | 23KB | -2.5KB |
| `helpers/projects.py` | 22KB | 18KB | -3.8KB |

### Upstream-only NEW helpers (fork is missing — candidates to bring in)
`litellm_transport.py` (61KB — major), `parallel_tools.py` (23KB — major), `chat_media.py`, `ephemeral_images.py`, `llm_result.py`, `media_artifacts.py`, `responses_tools.py`, `tunnel_common.py`, `tunnel_origins.py`, + tunnel variants (`cloudflare`, `tailscale`, `microsoft`, `serveo`, `cli`).

### Fork-only helpers (must NOT be deleted)
`kokoro_tts.py`, `whisper.py`, `faiss_monkey_patch.py`, `perplexity_search.py`, `document_query.py`, `state_monitor*.py`, `tunnel_manager.py`, `virtual_desktop*.py`

### Rebrand lives here (preserve during merge)
- `run_ui.py` — fork prints `"Initializing BioDockify AI components..."`, drops csrf import
- `prompts/` — pharma identity
- `agent_zero/__init__.py` — declares `__version__='2.0.0'`, `__author__='BioDockify Team'`
- `webui/index.html`, favicon — biotech branding

---

## 7. Where Work Stopped (todo state, 2026-06-25 ~12:16)

| # | Status | Task |
|---|--------|------|
| 0 | ✅ done | Deep architecture analysis |
| 1 | ✅ done | Static analysis: compile all Python |
| 2 | ✅ done | Confirm rebrand corruption scope (root cause = dot in identifiers) |
| 3 | 🔵 **in_progress** | Lint sweep (pyflakes) for undefined names, real bugs across live code |
| 4 | ⬜ pending | Run existing test suite, capture failures (expect conftest crash from `agent_with_monitoring.py`) |
| 5 | ⬜ pending | Fix rebrand corruption (`biodockify.ai` → `agent_zero` / `biodockify_ai`) — dependency order: hybrid/ → monitoring → helpers_v19/ |
| 6 | ⬜ pending | Triage + fix remaining Critical/Important bugs |
| 7 | ⬜ pending | The delicate v2.0 merge (flat-layout files only, preserve rebrand + all pharma) |
| 8 | ⬜ pending | Assess modules vs international standards (FDA/EMA/ICH, ISO 27001/9001, GLP/GCP) |

**Upstream v2.0 clone location:** `/tmp/agent-zero-v2` (2569 files, tag v2.0, commit `855694f`) — merge source ready.

---

## 8. Operating Constraints (from user + OPERATIONAL_RULES.md)

- Never hardcode API keys/secrets.
- Never use `eval()` with user input — use `ast.literal_eval`.
- Use `defusedxml` for XML parsing.
- Add timeouts to all network requests.
- Never ship credentials in Docker images.
- Respect language/region (ISO 639-1 / 3166-1 / 8601).
- Pharmaceutical: follow FDA/EMA/ICH; cite sources; validate scientific calcs; maintain audit trail.
