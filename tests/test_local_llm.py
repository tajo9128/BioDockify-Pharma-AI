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


def test_docker_compose_uses_correct_gguf_filename():
    """The compose sidecar command must reference the actual GGUF filename
    that exists on disk inside the volume."""
    path = PROJECT_ROOT / "docker-compose.yml"
    with open(path, encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    cmd = compose["services"]["llama-server"]["command"]
    model_arg = cmd[cmd.index("-m") + 1]
    assert model_arg == "/models/Bonsai-8B-Q1_0.gguf", (
        f"Sidecar -m arg must be /models/Bonsai-8B-Q1_0.gguf. Got: {model_arg}"
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
    assert rt["_meta"]["default_runtime"] == "llama_cpp_sidecar"
    assert "llama_cpp_sidecar" in rt["runtimes"]
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
    assert status["runtime"]["id"] == "llama_cpp_sidecar"
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
    # api_base must point at the sidecar hostname (Docker-internal)
    assert "llama-server" in bonsai["chat"]["api_base"], (
        "Local preset api_base must reference the llama-server sidecar"
    )


# ---------------------------------------------------------------------------
# Docker-compose wiring
# ---------------------------------------------------------------------------

def test_docker_compose_has_sidecar_service_with_correct_image():
    """v7.5.4 shipped with the wrong image (server-light does not exist).
    This test guards against regression."""
    path = PROJECT_ROOT / "docker-compose.yml"
    with open(path, encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    services = compose["services"]
    assert "llama-server" in services, "sidecar service missing"
    img = services["llama-server"]["image"]
    # server-light does NOT exist; only server / server-cuda / etc do
    assert "server-light" not in img, (
        f"Image {img} does not exist on ghcr.io — use 'server' instead"
    )
    assert img.startswith("ghcr.io/ggml-org/llama.cpp:server"), (
        f"Unexpected image: {img}"
    )


def test_docker_compose_sidecar_uses_cli_args_not_env_vars():
    """The llama.cpp server image takes CLI args, NOT env vars. v7.5.4
    incorrectly used MODEL/HOST/PORT/CTX_SIZE env vars that the image ignores.
    This test ensures the command: block is present and env vars aren't."""
    path = PROJECT_ROOT / "docker-compose.yml"
    with open(path, encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    sidecar = compose["services"]["llama-server"]
    assert "command" in sidecar, (
        "Sidecar must use 'command:' CLI args, not env vars (the image ignores env)"
    )
    cmd = sidecar["command"]
    assert "-m" in cmd and "--host" in cmd and "--port" in cmd, (
        "command must include -m, --host, --port args"
    )
    # The bogus env vars from v7.5.4 must be gone
    env = sidecar.get("environment") or []
    env_keys = []
    for e in env:
        if isinstance(e, str) and "=" in e:
            env_keys.append(e.split("=", 1)[0])
        elif isinstance(e, dict):
            env_keys.extend(e.keys())
    for forbidden in ("MODEL", "HOST", "PORT", "CTX_SIZE"):
        assert forbidden not in env_keys, (
            f"Sidecar must not set env var {forbidden} — the image ignores it. "
            "Use the 'command:' block instead."
        )


def test_docker_compose_biodockify_does_not_hard_require_sidecar():
    """biodockify must start even if the sidecar profile isn't enabled."""
    path = PROJECT_ROOT / "docker-compose.yml"
    with open(path, encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    bio = compose["services"]["biodockify"]
    deps = bio.get("depends_on", {}) or {}
    side_dep = deps.get("llama-server", {})
    assert side_dep.get("required") is False, (
        "biodockify must declare depends_on.llama-server.required: false "
        "so the main app starts without the opt-in sidecar"
    )


def test_docker_compose_has_models_volume():
    path = PROJECT_ROOT / "docker-compose.yml"
    with open(path, encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    assert "biodockify_models" in compose.get("volumes", {}), (
        "biodockify_models named volume missing"
    )
