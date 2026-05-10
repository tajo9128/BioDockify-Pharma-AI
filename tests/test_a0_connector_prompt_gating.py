import importlib.util
import sys
import uuid
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _restore_real_helpers_package() -> None:
    helpers_module = sys.modules.get("helpers")
    if helpers_module is None or getattr(helpers_module, "__file__", ""):
        return

    for name in list(sys.modules):
        if name == "helpers" or name.startswith("helpers."):
            del sys.modules[name]


_restore_real_helpers_package()

from plugins._a0_connector.helpers import ws_runtime


PROMPT_ROOT = PROJECT_ROOT / "plugins" / "_a0_connector" / "prompts"
GATE_PATH = (
    PROJECT_ROOT
    / "plugins"
    / "_a0_connector"
    / "extensions"
    / "python"
    / "_functions"
    / "extensions"
    / "python"
    / "system_prompt"
    / "_11_tools_prompt"
    / "build_prompt"
    / "end"
    / "_70_include_remote_tool_stubs.py"
)


def _load_gate_class():
    spec = importlib.util.spec_from_file_location(
        "test_a0_connector_remote_tool_gate",
        GATE_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.IncludeRemoteToolStubs


IncludeRemoteToolStubs = _load_gate_class()


class FakeContext:
    def __init__(self, context_id: str):
        self.id = context_id


class FakeAgent:
    def __init__(self, context_id: str):
        self.context = FakeContext(context_id)

    def read_prompt(self, file: str, **kwargs) -> str:
        text = (PROMPT_ROOT / file).read_text(encoding="utf-8")
        for key, value in kwargs.items():
            text = text.replace("{{" + key + "}}", str(value))
        return text


def _context_id() -> str:
    return f"ctx-{uuid.uuid4()}"


def _sid() -> str:
    return f"sid-{uuid.uuid4()}"


def _parse_skill_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---")
    return yaml.safe_load(text.split("---", 2)[1]) or {}


def _apply_gate(context_id: str) -> str:
    data = {"result": "## available tools\nbase_tool"}
    IncludeRemoteToolStubs(agent=FakeAgent(context_id)).execute(data=data)
    return data["result"]


def _subscribe(
    context_id: str,
    *,
    remote_files: dict | None = None,
    remote_exec: dict | None = None,
    computer_use: dict | None = None,
) -> str:
    sid = _sid()
    ws_runtime.register_sid(sid)
    ws_runtime.subscribe_sid_to_context(sid, context_id)
    if remote_files is not None:
        ws_runtime.store_sid_remote_file_metadata(sid, remote_files)
    if remote_exec is not None:
        ws_runtime.store_sid_remote_exec_metadata(sid, remote_exec)
    if computer_use is not None:
        ws_runtime.store_sid_computer_use_metadata(sid, computer_use)
    return sid


def test_remote_tool_stubs_absent_without_subscribed_cli():
    prompt = _apply_gate(_context_id())

    assert "text_editor_remote tool" not in prompt
    assert "code_execution_remote tool" not in prompt
    assert "computer_use_remote tool" not in prompt


def test_file_only_cli_adds_text_editor_stub():
    context_id = _context_id()
    sid = _subscribe(
        context_id,
        remote_files={"enabled": True, "write_enabled": True},
    )
    try:
        prompt = _apply_gate(context_id)
    finally:
        ws_runtime.unregister_sid(sid)

    assert "text_editor_remote tool" in prompt
    assert "Current access mode: `Read&Write`" in prompt
    assert "code_execution_remote tool" not in prompt
    assert "computer_use_remote tool" not in prompt


def test_exec_enabled_cli_adds_execution_stub():
    context_id = _context_id()
    sid = _subscribe(
        context_id,
        remote_exec={"enabled": True},
    )
    try:
        prompt = _apply_gate(context_id)
    finally:
        ws_runtime.unregister_sid(sid)

    assert "code_execution_remote tool" in prompt
    assert "text_editor_remote tool" not in prompt
    assert "computer_use_remote tool" not in prompt


def test_read_only_mode_marks_mutating_operations_disabled():
    context_id = _context_id()
    sid = _subscribe(
        context_id,
        remote_files={"enabled": True, "write_enabled": False, "mode": "read_only"},
        remote_exec={"enabled": True},
    )
    try:
        prompt = _apply_gate(context_id)
    finally:
        ws_runtime.unregister_sid(sid)

    assert "text_editor_remote tool" in prompt
    assert "code_execution_remote tool" in prompt
    assert "Current access mode: `Read only`" in prompt
    assert "Writes and patches are disabled" in prompt
    assert "Mutating runtimes are disabled" in prompt


def test_computer_use_enabled_cli_adds_computer_stub():
    context_id = _context_id()
    sid = _subscribe(
        context_id,
        computer_use={
            "supported": True,
            "enabled": True,
            "trust_mode": "ask",
            "backend_id": "local",
            "backend_family": "desktop",
            "features": ["screenshots", "keyboard"],
        },
    )
    try:
        prompt = _apply_gate(context_id)
    finally:
        ws_runtime.unregister_sid(sid)

    assert "computer_use_remote tool" in prompt
    assert "Backend: `local/desktop`" in prompt
    assert "Features: `screenshots, keyboard`" in prompt
    assert "text_editor_remote tool" not in prompt
    assert "code_execution_remote tool" not in prompt


def test_remote_workflow_skills_parse():
    connector_skill = _parse_skill_frontmatter(
        PROJECT_ROOT
        / "plugins"
        / "_a0_connector"
        / "skills"
        / "a0-cli-remote-workflows"
        / "SKILL.md"
    )
    computer_skill = _parse_skill_frontmatter(
        PROJECT_ROOT / "skills" / "computer-use-remote" / "SKILL.md"
    )

    assert connector_skill["name"] == "a0-cli-remote-workflows"
    assert connector_skill["description"]
    assert computer_skill["name"] == "computer-use-remote"
    assert computer_skill["description"]
