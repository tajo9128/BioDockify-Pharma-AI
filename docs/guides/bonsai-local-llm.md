# BioDockify AI Engine — Local LLM (Bonsai-8B)

> **Pharma research focus.** Run a private LLM entirely on your own machine —
> no PHI, compound structures, or case-report data ever leaves your lab. This
> matters for **air-gapped / GxP / regulatory environments**, for thesis
> work that must remain **reproducible** without depending on a cloud model's
> future availability, and for **cost-free student access**.

## What it is

The BioDockify AI Engine is an **optional** local LLM runtime that runs as a
Docker sidecar alongside BioDockify. It uses [llama.cpp](https://github.com/ggerganov/llama.cpp)
to serve a small but capable model ([Bonsai-8B](https://huggingface.co/prism-ml/Bonsai-8B-gguf),
~1.15 GB, 1-bit) on your own hardware. BioDockify talks to it through a
standard OpenAI-compatible HTTP endpoint, so the Brain layer is unchanged and
tomorrow you can swap in Ollama / LM Studio / vLLM / mlx_lm.server with zero
code changes.

**Bonsai-8B is not hardcoded.** It is the *default* entry in a data-driven
catalog (`modules/local_llm/models.json`). Adding Gemma, Phi, Qwen, or a future
pharma-tuned 8B model is a one-line JSON edit — no code changes.

## Architecture

```
            ┌──────────────────────────────────────────────────┐
            │  Docker Desktop on your laptop / lab workstation │
            │                                                  │
            │   ┌───────────────┐    ┌──────────────────────┐  │
            │   │  biodockify   │───▶│   llama-server        │  │
            │   │  (UI + API)   │ HTTP│   (sidecar, opt-in)  │  │
            │   └───────────────┘ /v1│  ghcr.io/ggerganov/  │  │
            │                         │  llama.cpp:server-   │  │
            │                         │  light               │  │
            │                         └──────────┬───────────┘  │
            │                                    │ mounts       │
            │                         ┌──────────▼───────────┐  │
            │                         │ biodockify_models    │  │
            │                         │ (named volume)       │  │
            │                         │ /models/bonsai-8b-…  │  │
            │                         └──────────────────────┘  │
            └──────────────────────────────────────────────────┘
                                  │
                            (no cloud)
```

Key properties:

- The **model lives in a Docker volume**, not in the image. Image updates never
  re-download the ~1.15 GB GGUF.
- The sidecar is **opt-in** via `docker compose --profile local-llm up`. A
  plain `docker compose up` is unchanged.
- BioDockify declares `depends_on: llama-server (required: false)` so it
  starts fine even when the sidecar is absent.
- The sidecar exposes an **OpenAI-compatible `/v1`** endpoint. The Brain uses
  LiteLLM as usual; no provider code changes.

## Hardware requirements

| Resource        | Minimum | Recommended |
|-----------------|---------|-------------|
| System RAM      | 6 GB    | 8 GB        |
| GPU VRAM        | 0 (CPU OK) | 4 GB NVIDIA  |
| Disk            | 2 GB free | 4 GB free |
| OS              | Windows 10+, macOS 11+, Linux x86_64 | same |

**Apple Silicon (M1/M2/M3/M4):** works via the llama.cpp sidecar. For the
fastest experience on Apple Silicon you can alternatively run `mlx_lm.server`
on the host and point BioDockify at it like any Ollama/LM Studio provider.

**CPU-only laptops:** Bonsai-8B at 1-bit is *usable* on CPU but slow
(roughly 3–8 tok/s on a modern i5/Ryzen). For routine student work on a
weak laptop, host Ollama (see existing Ollama docs) is often the better
choice; this bundled sidecar is intended for the **private / air-gapped**
use case.

## Install (one-time)

### Windows

```bat
scripts\install_bonsai.bat
```

### Linux / macOS

```bash
bash scripts/install_bonsai.sh
```

### What the installer does

1. Verifies Docker is running.
2. Probes host RAM and GPU. Warns (does not block) if below minimum.
3. Creates the `biodockify_models` named volume if missing.
4. Downloads `bonsai-8b-Q1_0.gguf` (~1.15 GB) from Hugging Face into the
   volume via a one-shot alpine container. (Nothing is installed on your host
   filesystem outside Docker.)
5. Starts the `llama-server` sidecar via `docker compose --profile local-llm up -d`.
6. Polls `http://localhost:8081/health` until the sidecar is ready (≤90 s).

### Final step (in the UI)

1. Open BioDockify at `http://localhost`.
2. Go to **Settings → Models**.
3. In the preset switcher (chat bar or settings panel), select
   **"BioDockify AI Engine — Local (Bonsai-8B)"**.
4. Send a test message.

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

To preview a rendered template (no LLM call):

```bash
curl -X POST http://localhost/api/local_llm \
  -H "Content-Type: application/json" \
  -d '{"action":"prompts","task":"admet"}'
```

## Status & health

Check the engine status from the API:

```bash
curl -X POST http://localhost/api/local_llm \
  -H "Content-Type: application/json" \
  -d '{"action":"status"}'
```

Example response:

```json
{
  "status": "ok",
  "engine_name": "BioDockify AI Engine",
  "default_model": "bonsai-8b",
  "model": { "display_name": "Bonsai-8B (1-bit)", "size_gb": 1.15, "context_length": 32768 },
  "sidecar": {
    "running": true,
    "latency_ms": 12,
    "loaded_models": ["bonsai-8b"],
    "endpoint": "http://llama-server:8080/v1"
  },
  "hardware": { "ram_total_gb": 16.0, "vram_total_gb": 4.0, "gpu_present": true, "gpu_name": "NVIDIA ...", "apple_silicon": false },
  "preset_name": "BioDockify AI Engine — Local (Bonsai-8B)",
  "notes": ["Sidecar is healthy."]
}
```

Other actions:
- `{"action":"hardware"}` — detected RAM/VRAM/GPU + model recommendation
- `{"action":"catalog"}` — list of installable models from `models.json`
- `{"action":"prompts"}` — list available pharma prompt templates
- `{"action":"readiness"}` — pre-flight checks for the install script

## Privacy & compliance notes

- **No egress.** The sidecar talks only to BioDockify over the internal Docker
  network. No prompts, KB content, or generated text is sent anywhere.
- **No telemetry.** The BioDockify AI Engine does not phone home.
- **HIPAA / GDPR friendly.** Because nothing leaves the host, the local engine
  is suitable for case reports containing PHI, internal assay data, and
  unpublished compound series.
- **Reproducibility.** A thesis written with a local Bonsai-8B in 2026 can be
  re-run in 2030 with the same model file. Cloud models cannot guarantee this.

## Removing the local engine

```bash
docker compose --profile local-llm stop llama-server
docker compose --profile local-llm rm -f llama-server
docker volume rm biodockify_models   # frees the ~1.15 GB
```

Then switch back to a cloud preset (Max Power / Balance / Cost Efficient) in
Settings → Models. BioDockify continues to work normally.

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

Then add a preset in `plugins/_model_config/default_presets.yaml` pointing at
`http://llama-server:8080/v1` and update the installer's `MODEL_FILE` /
`MODEL_URL`. No Python or JavaScript changes required.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Sidecar `unhealthy` after 90 s | `docker compose --profile local-llm logs llama-server` |
| `model file not found` in sidecar logs | Re-run the install script; verify `docker run --rm -v biodockify_models:/models alpine ls -la /models` |
| Very slow CPU inference | Switch to host Ollama preset (see main Installation docs), or add a GPU |
| Port 8081 already in use | Edit `docker-compose.yml` and change `8081:8080` to a free host port; also update `HEALTH_URL` in the install scripts |
| GPU not detected in WSL2 | NVIDIA GPU passthrough on Windows Docker Desktop requires `nvidia-container-toolkit`; the bundled sidecar image falls back to CPU |
| Preset shows "missing API key" | Should not happen — `lm_studio` is in `LOCAL_PROVIDERS`. If you see it, verify `_model_config` plugin is enabled |
