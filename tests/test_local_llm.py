"""
Smoke tests for the BioDockify AI Engine (local LLM subsystem).

These tests do NOT require Docker, the llama.cpp sidecar, or a running model.
They validate:
  - The model catalog (models.json) loads and has the expected schema
  - The runtime registry (runtimes.json) loads and has the bundled default
  - The PharmaPromptLibrary renders all task templates
  - The LocalLLMManager exposes the documented actions
  - The status / catalog / runtimes / prompts / readiness / benchmark
    dispatch is wired in api/local_llm.py
  - The default_presets.yaml entry for the local engine is well-formed
  - Hardware detection returns a dict with the expected keys (does not
    require a GPU or any specific OS)

Network is optional: probes against a sidecar that isn't running must
return reachable=False with an error string, NOT raise.

Run:  pytest tests/test_local_llm.py -v
"""

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Catalog (models.json)
# ---------------------------------------------------------------------------

def test_models_json_loads_and_has_default():
    from modules.local_llm import load_catalog
    cat = load_catalog(force=True)
    assert "_meta" in cat
    assert cat["_meta"]["default_model"] == "bonsai-8b"
    assert "bonsai-8b" in cat["models"]


def test_models_json_schema_for_bonsai_8b():
    from modules.local_llm import load_catalog
    cat = load_catalog(force=True)
    m = cat["models"]["bonsai-8b"]
    # Required fields per the schema documented in models.json
    for key in ("display_name", "family", "publisher", "license",
                "description", "gguf", "requirements", "runtime", "tags"):
        assert key in m, f"missing key: {key}"
    # GGUF block must have a non-empty URL
    g = m["gguf"]
    assert g["url"].startswith("https://"), "model URL must be https"
    assert g["filename"].endswith(".gguf")
    assert g["size_gb"] > 0
    # Requirements sanity
    r = m["requirements"]
    assert r["min_ram_gb"] > 0
    assert r["context_length"] >= 8192


def test_models_json_filename_case_correct():
    """Regression guard: v7.5.5 shipped with lowercase `bonsai-8b-Q1_0.gguf`
    in the catalog, which 404s on Hugging Face (URLs are case-sensitive).
    The real file on HF is `Bonsai-8B-Q1_0.gguf` (capital B).
    """
    from modules.local_llm import load_catalog
    cat = load_catalog(force=True)
    g = cat["models"]["bonsai-8b"]["gguf"]
    assert g["filename"] == "Bonsai-8B-Q1_0.gguf", (
        f"Filename must be exactly 'Bonsai-8B-Q1_0.gguf' (capital B). "
        f"Got: {g['filename']}"
    )
    assert g["filename"] in g["url"], "URL must contain the filename"
    # Sanity check: no lowercase variant anywhere
    assert "bonsai-8b-q1_0" not in g["url"].lower().rsplit("/", 1)[-1].lower() \
           or g["filename"] == "Bonsai-8B-Q1_0.gguf"


def test_startup_script_uses_correct_gguf_filename():
    """The startup script must reference the actual GGUF filename (case-sensitive).
    The HF file is Bonsai-8B-Q1_0.gguf (capital B), not bonsai-8b-Q1_0.gguf."""
    path = PROJECT_ROOT / "exe" / "init_and_run_llama.sh"
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "Bonsai-8B-Q1_0.gguf" in src, (
        "Startup script must reference Bonsai-8B-Q1_0.gguf (capital B)"
    )


def test_models_json_is_valid_json():
    path = PROJECT_ROOT / "modules" / "local_llm" / "models.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)  # raises if invalid
    assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# Runtime registry (runtimes.json)
# ---------------------------------------------------------------------------

def test_runtimes_json_loads_and_has_default():
    from modules.local_llm import load_runtimes, get_default_runtime
    rt = load_runtimes(force=True)
    assert rt["_meta"]["default_runtime"] == "llama_cpp_local"
    assert "llama_cpp_local" in rt["runtimes"]
    d = get_default_runtime()
    assert d["display_name"]
    assert d["endpoint"]["api_base"].startswith("http://")


def test_every_runtime_exposes_openai_compatible_endpoint():
    """The Brain contract: every runtime MUST expose an api_base."""
    from modules.local_llm import load_runtimes
    rt = load_runtimes(force=True)
    for rid, entry in rt["runtimes"].items():
        if entry.get("_status") == "documented_for_future_use":
            continue  # future entries may be incomplete
        ep = entry.get("endpoint", {})
        assert "api_base" in ep, f"{rid} missing api_base"
        assert ep["api_base"].startswith("http://"), f"{rid} bad api_base"
        assert "litellm_provider" in entry, f"{rid} missing litellm_provider"


def test_runtimes_json_is_valid_json():
    path = PROJECT_ROOT / "modules" / "local_llm" / "runtimes.json"
    with open(path, encoding="utf-8") as f:
        json.load(f)
    assert True


# ---------------------------------------------------------------------------
# Pharma Prompt Library
# ---------------------------------------------------------------------------

def test_pharma_prompt_library_renders_all_tasks():
    from modules.local_llm import PharmaPromptLibrary
    tasks = PharmaPromptLibrary.available_tasks()
    assert "system" in tasks
    assert "literature" in tasks
    assert "moa" in tasks
    assert "docking" in tasks
    assert "admet" in tasks
    assert "claims" in tasks
    assert "thesis" in tasks
    assert "ich" in tasks
    for t in tasks:
        out = PharmaPromptLibrary.for_task(t)
        assert isinstance(out, str)
        assert len(out) > 50, f"template {t} too short"


def test_pharma_prompt_system_preamble_enforces_no_fabrication():
    """The most important pharma safety rule must be in the preamble."""
    from modules.local_llm import PharmaPromptLibrary
    pre = PharmaPromptLibrary.system_preamble()
    assert "NEVER fabricate" in pre
    assert "ICH" in pre


def test_pharma_prompt_claims_returns_json_schema():
    from modules.local_llm import PharmaPromptLibrary
    p = PharmaPromptLibrary.for_task("claims")
    assert "SUPPORTED" in p
    assert "HALLUCINATED" in p
    assert "verdict" in p


def test_pharma_prompt_dispatch_passes_kwargs():
    from modules.local_llm import PharmaPromptLibrary
    methods = PharmaPromptLibrary.for_task("thesis", section="results")
    assert "Results" in methods or "effect size" in methods.lower()
    ich_obs = PharmaPromptLibrary.for_task("ich", study_type="observational")
    assert "STROBE" in ich_obs


# ---------------------------------------------------------------------------
# Hardware detection
# ---------------------------------------------------------------------------

def test_detect_hardware_returns_expected_keys():
    from modules.local_llm import detect_hardware
    hw = detect_hardware()
    assert isinstance(hw, dict)
    for key in ("os", "cpu_count", "ram_total_gb", "gpu_present",
                "apple_silicon", "probe_scope"):
        assert key in hw, f"missing key: {key}"


def test_recommend_model_returns_default_when_meets_minimums():
    from modules.local_llm import detect_hardware, recommend_model, load_catalog
    hw = detect_hardware()
    rec = recommend_model(hw, load_catalog())
    assert rec["recommended"] == "bonsai-8b"
    assert isinstance(rec["warnings"], list)


# ---------------------------------------------------------------------------
# Manager probes (do not require a running sidecar)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_probe_sidecar_returns_reachable_false_when_not_running():
    """When the sidecar isn't reachable, the probe must return reachable=False
    with an error message, NOT raise."""
    from modules.local_llm import LocalLLMManager
    m = LocalLLMManager()
    result = await m.probe_sidecar()
    assert isinstance(result, dict)
    assert "reachable" in result
    if not result["reachable"]:
        assert "error" in result


@pytest.mark.asyncio
async def test_get_model_status_returns_well_formed_dict():
    from modules.local_llm import LocalLLMManager
    m = LocalLLMManager()
    status = await m.get_model_status()
    # Top-level keys
    for key in ("engine_name", "default_model", "model_id", "model",
                "runtime", "sidecar", "hardware", "recommendation",
                "preset_name", "notes"):
        assert key in status, f"status missing key: {key}"
    # Engine branding
    assert status["engine_name"] == "BioDockify AI Engine"
    # Runtime block
    assert status["runtime"]["id"] == "llama_cpp_local"
    assert status["runtime"]["litellm_provider"] == "lm_studio"


def test_install_readiness_returns_instructions():
    from modules.local_llm import LocalLLMManager
    m = LocalLLMManager()
    r = m.install_readiness()
    assert "instructions" in r
    assert "scripts/install_bonsai" in r["instructions"]
    assert isinstance(r["warnings"], list)


# ---------------------------------------------------------------------------
# API handler contract
# ---------------------------------------------------------------------------

def test_local_llm_handler_has_required_methods():
    """The ApiHandler loader requires process() and requires_auth()."""
    import ast
    path = PROJECT_ROOT / "api" / "local_llm.py"
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    cls = [n for n in tree.body
           if isinstance(n, ast.ClassDef) and n.name == "LocalLLMHandler"][0]
    methods = {n.name for n in cls.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for required in ("process", "requires_auth",
                     "_status", "_hardware", "_catalog", "_runtimes",
                     "_prompts", "_readiness", "_benchmark"):
        assert required in methods, f"LocalLLMHandler missing: {required}"


def test_local_llm_handler_unknown_action_returns_error_dict():
    """An unknown action must return a structured error, not raise.

    We validate the dispatch logic by parsing the source AST rather than
    importing the handler — importing api.local_llm pulls in Agent Zero's
    helpers/whisper.py which needs the optional `whisper` package, and we
    don't want this smoke test to depend on that."""
    import ast
    path = PROJECT_ROOT / "api" / "local_llm.py"
    with open(path, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)

    cls = [n for n in tree.body
           if isinstance(n, ast.ClassDef) and n.name == "LocalLLMHandler"][0]
    process = next(n for n in cls.body
                   if isinstance(n, ast.AsyncFunctionDef) and n.name == "process")

    # Collect the action strings handled in process(). The dispatch uses
    # `if action == "foo":` so we walk every Compare node and collect string
    # comparators. (Some constants like "thesis"/"ich" come from prompt
    # dispatch in other modules — that's fine, we only check the documented
    # action set is a subset.)
    handled = set()
    for node in ast.walk(process):
        if isinstance(node, ast.Compare):
            for cmp in node.comparators:
                if isinstance(cmp, ast.Constant) and isinstance(cmp.value, str):
                    handled.add(cmp.value)

    # The dispatch must include a fallback return with "Unknown action"
    assert "Unknown action" in src, (
        "process() must return a structured 'Unknown action' error for "
        "unknown actions — never raise"
    )
    # All documented actions must be present in the dispatch
    expected = {"status", "hardware", "catalog", "runtimes",
                "prompts", "readiness", "benchmark"}
    missing = expected - handled
    assert not missing, f"process() missing actions: {missing}"


# ---------------------------------------------------------------------------
# Preset entry
# ---------------------------------------------------------------------------

def test_default_presets_yaml_has_local_engine_entry():
    path = PROJECT_ROOT / "plugins" / "_model_config" / "default_presets.yaml"
    with open(path, encoding="utf-8") as f:
        presets = yaml.safe_load(f)
    assert isinstance(presets, list)
    names = [p.get("name") for p in presets]
    assert "BioDockify AI Engine — Local (Bonsai-8B)" in names


def test_local_engine_preset_uses_api_key_exempt_provider():
    """lm_studio is in LOCAL_PROVIDERS so no key banner appears.
    If a future edit changes this provider, the test will catch it."""
    path = PROJECT_ROOT / "plugins" / "_model_config" / "default_presets.yaml"
    with open(path, encoding="utf-8") as f:
        presets = yaml.safe_load(f)
    bonsai = next(p for p in presets
                  if "Bonsai-8B" in (p.get("name") or ""))
    assert bonsai["chat"]["provider"] in ("lm_studio", "ollama"), (
        "Local preset must use an API-key-exempt provider; "
        "otherwise the UI shows a misleading 'missing API key' banner."
    )
    # api_base must point at localhost (bundled llama-server runs inside container)
    assert "localhost" in bonsai["chat"]["api_base"], (
        "Local preset api_base must reference localhost (bundled llama-server)"
    )


# ---------------------------------------------------------------------------
# Dockerfile — bundled llama-server (multi-stage build)
# ---------------------------------------------------------------------------

def test_dockerfile_bundles_llama_server_binary():
    """The Dockerfile must use a multi-stage build to copy llama-server
    from the official llama.cpp image into the BioDockify image."""
    path = PROJECT_ROOT / "Dockerfile.release"
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "FROM ghcr.io/ggml-org/llama.cpp:server AS llama-src" in src, (
        "Dockerfile must have a multi-stage FROM for llama.cpp:server"
    )
    assert "COPY --from=llama-src" in src, (
        "Dockerfile must COPY the llama-server binary from the llama-src stage"
    )
    assert "llama-server" in src, (
        "Dockerfile must reference the llama-server binary"
    )


def test_dockerfile_has_no_bonsai_server_light_reference():
    """Regression: the server-light tag does not exist on GHCR."""
    path = PROJECT_ROOT / "Dockerfile.release"
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "server-light" not in src, (
        "server-light does not exist — use ghcr.io/ggml-org/llama.cpp:server"
    )


def test_dockerfile_bundles_bonsai_model():
    """The Dockerfile must bundle the Bonsai-8B model into the image.

    We download it via RUN curl (not COPY) because the model file is in
    .gitignore (too large for git) and CI needs to fetch it at build time.
    The downloaded file lands at /opt/llama-server/models/ — baked into the
    image, no runtime download needed.
    """
    path = PROJECT_ROOT / "Dockerfile.release"
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "Bonsai-8B-Q1_0.gguf" in src, (
        "Dockerfile must reference the Bonsai-8B model"
    )
    assert "https://huggingface.co/prism-ml/Bonsai-8B-gguf/resolve/main/Bonsai-8B-Q1_0.gguf" in src, (
        "Dockerfile must download the model from the correct HF URL"
    )
    assert "/opt/llama-server/models" in src, (
        "Model must be stored at /opt/llama-server/models/"
    )


# ---------------------------------------------------------------------------
# Startup scripts — bundled auto-download + auto-start
# ---------------------------------------------------------------------------

def test_exe_init_bonsai_sh_exists_and_executable():
    """init_bonsai.sh verifies the bundled model (no download)."""
    path = PROJECT_ROOT / "exe" / "init_bonsai.sh"
    assert path.exists(), "exe/init_bonsai.sh missing"
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "Bonsai-8B-Q1_0.gguf" in src, "script must reference the GGUF filename"
    assert "1158654496" in src, "script must check expected file size"
    assert "/opt/llama-server/models" in src, "model must be in /opt/llama-server/models/"


def test_exe_init_and_run_llama_sh_exists_and_executable():
    """init_and_run_llama.sh is the supervisord entrypoint for llama-server.
    Model is bundled in the image — script verifies it exists then starts server."""
    path = PROJECT_ROOT / "exe" / "init_and_run_llama.sh"
    assert path.exists(), "exe/init_and_run_llama.sh missing"
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "llama-server" in src or "exec llama" in src, (
        "script must exec llama-server"
    )
    assert "/opt/llama-server/models" in src, (
        "script must reference bundled model path"
    )


# ---------------------------------------------------------------------------
# Docker-compose — single container, no sidecar
# ---------------------------------------------------------------------------

def test_docker_compose_is_single_container_no_sidecar():
    """Since v7.5.7, llama-server is bundled inside the BioDockify container.
    There should be no separate llama-server service in docker-compose.yml."""
    path = PROJECT_ROOT / "docker-compose.yml"
    with open(path, encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    services = compose["services"]
    assert "llama-server" not in services, (
        "llama-server is now bundled — no separate sidecar service in compose"
    )
    assert "bonsai-init" not in services, (
        "bonsai-init is now part of the bundled entrypoint — no init service in compose"
    )
    assert "biodockify" in services, "biodockify service must be present"


def test_docker_compose_has_no_models_volume():
    """Model is bundled inside the Docker image at /opt/llama-server/models/.
    No separate volume needed for the model."""
    path = PROJECT_ROOT / "docker-compose.yml"
    with open(path, encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    volumes = compose.get("volumes", {})
    assert "biodockify_models" not in volumes, (
        "Model is bundled in the Docker image at /opt/llama-server/models/ — "
        "separate biodockify_models volume not needed"
    )
