# BioDockify AI Engine — Local LLM (Bonsai-8B)

> **Fully optional. Fully user-driven.** Bonsai-8B is one preset among
> several. You pick it for your main model, your utility model, both, or
> neither — BioDockify never forces it on you. Nothing on this page is
> required for normal use; cloud presets (Max Power / Balance / Cost
> Efficient) keep working unchanged.

> **Students: just run `docker compose up -d` and open http://localhost.**
> The model downloads automatically on first run. No scripts, no terminal
> commands, no technical knowledge needed.

> **Pharma research focus.** Run a private LLM entirely on your own machine —
> no PHI, compound structures, or case-report data ever leaves your lab. This
> matters for **air-gapped / GxP / regulatory environments**, for thesis
> work that must remain **reproducible** without depending on a cloud model's
> future availability, and for **cost-free student access**.

## What it is

The BioDockify AI Engine is a **bundled** local LLM runtime that runs
**inside the BioDockify container itself** — no separate sidecar, no extra
image pull, no profiles. It uses [llama.cpp](https://github.com/ggml-org/llama.cpp)
to serve a small but capable model ([Bonsai-8B](https://huggingface.co/prism-ml/Bonsai-8B-gguf),
~1.15 GB, 1-bit) on your own hardware.

BioDockify talks to llama-server through a standard OpenAI-compatible HTTP
endpoint (`http://localhost:8080/v1`), so the Brain layer is unchanged and
you can swap in Ollama / LM Studio / vLLM / mlx_lm.server with zero code
changes.

**Bonsai-8B is not hardcoded.** It is the *default* entry in a data-driven
catalog (`modules/local_llm/models.json`). Adding Gemma, Phi, Qwen, or a
future pharma-tuned 8B model is a one-line JSON edit — no code changes.

## Architecture

```
┌─────────────────────────────────────────────┐
│  Docker Desktop on your laptop               │
│                                              │
│  ┌─────────────────────────────────────┐    │
│  │  BioDockify container                │    │
│  │                                      │    │
│  │  ┌─────────┐  HTTP   ┌────────────┐ │    │
│  │  │  UI     │ ──────▶ │ llama-     │ │    │
│  │  │ + API   │  /v1    │ server     │ │    │
│  │  └─────────┘         └─────┬──────┘ │    │
│  │                            │ reads  │    │
│  │              ┌──────────────▼──────┐ │    │
│  │              │ /a0/usr/ai_models/  │ │    │
│  │              │ Bonsai-8B-Q1_0.gguf │ │    │
│  │              └─────────────────────┘ │    │
│  └─────────────────────────────────────┘    │
│                    │                         │
│              biodockify_usr volume           │
│              (persists across restarts)      │
└─────────────────────────────────────────────┘
                      │
                (no cloud)
```

### Key properties

- **llama-server is bundled** inside the BioDockify image (multi-stage Docker
  build). No separate image pull, no sidecar container.
- The **model auto-downloads** on first `docker compose up` (~1.1 GB,
  one-time). Subsequent starts are instant.
- The **model lives in `biodockify_usr`** volume at `/a0/usr/ai_models/`,
  not in the image. Image updates never re-download the model.
- `docker compose up -d` starts everything — **one command, one container**.
- llama-server exposes `http://localhost:8080/v1` (OpenAI-compatible).
- If download fails (no internet), BioDockify still starts — use cloud
  presets in Settings.

## Hardware requirements

| Resource        | Minimum | Recommended |
|-----------------|---------|-------------|
| System RAM      | 6 GB    | 8 GB        |
| GPU VRAM        | 0 (CPU OK) | 4 GB NVIDIA  |
| Disk            | 2 GB free | 4 GB free |
| OS              | Windows 10+, macOS 11+, Linux x86_64 | same |

**Apple Silicon (M1/M2/M3/M4):** works via the bundled llama-server. For the
fastest experience on Apple Silicon you can alternatively run `mlx_lm.server`
on the host and point BioDockify at it like any Ollama/LM Studio provider.

**CPU-only laptops:** Bonsai-8B at 1-bit is *usable* on CPU but slow
(roughly 3–8 tok/s on a modern i5/Ryzen). For routine student work on a
weak laptop, host Ollama (see existing Ollama docs) is often the better
choice; this bundled engine is intended for the **private / air-gapped**
use case.

## Install (one-time, automatic)

**There is nothing to install.** `docker compose up -d` handles everything:

1. Starts BioDockify.
2. On first run, auto-downloads Bonsai-8B (~1.1 GB) into the persistent
   volume. This happens once — subsequent starts are instant.
3. Starts llama-server inside the container automatically.

### Final step (in the UI) — pick Bonsai for either or both slots

BioDockify has two independent model slots that you control separately:

- **Main (chat) model** — does the core reasoning: literature synthesis,
  thesis drafting, MOA explanation, claim verification, etc.
- **Utility model** — does short helper tasks the agent runs in the
  background (title generation, response summarization, tool routing).

You can mix freely. There is no forced default and no routing logic that
overrides your choice:

| Setup                                  | When to use                                                    |
|----------------------------------------|----------------------------------------------------------------|
| Main = Bonsai, Utility = Bonsai        | Fully offline / air-gapped. Zero cloud spend.                  |
| Main = Bonsai, Utility = Claude/GPT    | Offline-first; cloud accelerates background helpers.           |
| Main = Claude/GPT, Utility = Bonsai    | Cloud-first; Bonsai used only when cloud is unreachable.       |
| Main = Claude/GPT, Utility = Claude    | Cloud-only (existing Max Power / Balance presets).             |
| Main = Bonsai, Utility = (cloud)       | Bonsai as the primary researcher, cloud for JSON/translation.  |

To configure:

1. Open BioDockify at `http://localhost`.
2. Go to **Settings → Models**.
3. Pick the **Main Model** (chat) — Bonsai or any cloud provider.
4. Pick the **Utility Model** — Bonsai or any cloud provider (or the same
   as Main).
5. Save. Send a test message.

If you want a ready-made starting point, the preset
**"BioDockify AI Engine — Local (Bonsai-8B)"** sets both slots to Bonsai.
You can then edit either slot independently without losing the other.

## Using the local model for pharma workflows

The AI Engine ships with a **Pharma Prompt Library**
(`modules/local_llm/pharma_prompts.py`) that wraps user prompts with domain
templates tuned for small local models. These templates enforce the
no-fabrication rule that matters most for safety/regulatory writing.

Available templates:

| Template          | Use for |
|-------------------|---------|
| `system`          | Universal pharma preamble (always on) |
| `literature`      | Synthesizing literature across KB sources |
| `moa`             | Mechanism-of-action explanation |
| `docking`         | Interpreting AutoDock Vina results |
| `admet`           | ADMET profile interpretation + Go/Optimize/Drop |
| `claims`          | 6-type pharma claim verification (JSON output) |
| `thesis`          | Methods / Results / Discussion drafting (IMRaD) |
| `ich`             | CONSORT / STROBE / PRISMA / ARRIVE / ICH compliance checks |

## Status & health

Check the engine status from the API:

```bash
curl -X POST http://localhost/api/local_llm \
  -H "Content-Type: application/json" \
  -d '{"action":"status"}'
```

Other actions:
- `{"action":"hardware"}` — detected RAM/VRAM/GPU + model recommendation
- `{"action":"catalog"}` — list of installable models from `models.json`
- `{"action":"runtimes"}` — registered backends (bundled llama.cpp, host
  Ollama, host LM Studio, future vLLM / MLX)
- `{"action":"prompts"}` — list available pharma prompt templates
- `{"action":"readiness"}` — pre-flight checks
- `{"action":"benchmark"}` — run a 50-token pharma prompt and get tok/s
  with Good (≥20) / OK (≥8) / Slow verdict

## In-app diagnostics panel

Open the right-canvas rail and click the **BioDockify AI Engine** icon
(brain). The panel has four tabs:

- **Status** — runtime reachability, latency, loaded model, hardware probe,
  install instructions when the engine isn't running.
- **Models** — full catalog with publisher, size, quantization, license, tags.
- **Runtimes** — every registered backend (bundled llama.cpp, host Ollama,
  host LM Studio, future vLLM / MLX) with endpoint URLs and install links.
- **Benchmark** — runs a fixed pharma prompt and reports tokens/sec with a
  Good / OK / Slow verdict.

All data comes from the `/api/local_llm` actions
(`status`, `hardware`, `catalog`, `runtimes`, `prompts`, `readiness`,
`benchmark`). The panel makes no external calls.

## Swapping runtimes (data-driven, no code)

The Brain talks to whichever runtime is active via a single OpenAI-compatible
endpoint. Switching from the bundled llama.cpp to host Ollama is a two-line
data change:

1. Edit `modules/local_llm/runtimes.json` → change
   `_meta.default_runtime` from `"llama_cpp_local"` to `"host_ollama"`.
2. Update the preset's `api_base` in
   `plugins/_model_config/default_presets.yaml` to match (e.g.
   `http://host.docker.internal:11434` for Ollama).

No Python changes. No Agent Zero changes.

## Adding more models (data-driven, no code)

Edit `modules/local_llm/models.json`:

```json
{
  "models": {
    "bonsai-8b": { "...": "..." },
    "my-next-model": {
      "display_name": "My Next 8B",
      "gguf": { "url": "https://...", "filename": "...gguf", "size_gb": 2.0 },
      "requirements": { "min_ram_gb": 8, "recommended_vram_gb": 6 }
    }
  }
}
```

Then update the startup script (`exe/init_bonsai.sh`) to download the new
model file, and add a preset in
`plugins/_model_config/default_presets.yaml` pointing at
`http://localhost:8080/v1`. No Python or JavaScript changes required.

## Privacy & compliance notes

- **No egress.** llama-server talks only to BioDockify via `localhost`.
  No prompts, KB content, or generated text is sent anywhere.
- **No telemetry.** The BioDockify AI Engine does not phone home.
- **HIPAA / GDPR friendly.** Because nothing leaves the host, the local engine
  is suitable for case reports containing PHI, internal assay data, and
  unpublished compound series.
- **Reproducibility.** A thesis written with a local Bonsai-8B in 2026 can be
  re-run in 2030 with the same model file. Cloud models cannot guarantee this.

## Removing the local engine

```bash
docker compose down -v   # removes ALL volumes including the downloaded model
docker compose up -d      # restarts clean — model will re-download on next start
```

To free disk space without restarting:
```bash
docker exec biodockify rm -rf /a0/usr/ai_models/
```

Then switch back to a cloud preset (Max Power / Balance / Cost Efficient) in
Settings → Models. BioDockify continues to work normally.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Model didn't download on first start | Check internet. Restart: `docker compose restart`. Download happens in background. |
| `manifest unknown` when building | You may be on an old Dockerfile. Update to v7.5.7+ which uses `ghcr.io/ggml-org/llama.cpp:server`. |
| Very slow CPU inference | Switch to host Ollama preset (see main Installation docs), or add a GPU |
| GPU not detected in WSL2 | NVIDIA GPU passthrough on Windows Docker Desktop requires `nvidia-container-toolkit`. For native GPU acceleration, use host Ollama. |
| Preset shows "missing API key" | Should not happen — `lm_studio` is in `LOCAL_PROVIDERS`. If you see it, verify `_model_config` plugin is enabled |
| `curl: (7) Connection refused` on port 8080 | llama-server starts in background via supervisord. Wait 30-60 seconds after `docker compose up` for it to load the model. |
| Want to force re-download | `docker exec biodockify rm /a0/usr/ai_models/Bonsai-8B-Q1_0.gguf && docker compose restart` |
