from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
import types
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plugins._office import hooks
from plugins._office.helpers import (
    artifact_editor,
    canvas_context,
    document_store,
    libreoffice,
    libreoffice_desktop,
    markdown_sessions,
)


@pytest.fixture
def office_state(tmp_path, monkeypatch):
    state = tmp_path / "state"
    backups = state / "backups"
    workdir = tmp_path / "workdir"
    documents = workdir / "documents"
    projects_parent = tmp_path / "projects"

    monkeypatch.setattr(document_store, "STATE_DIR", state)
    monkeypatch.setattr(document_store, "DB_PATH", state / "documents.sqlite3")
    monkeypatch.setattr(document_store, "BACKUP_DIR", backups)
    monkeypatch.setattr(document_store, "WORKDIR", workdir)
    monkeypatch.setattr(document_store, "DOCUMENTS_DIR", documents)
    settings_helpers = types.SimpleNamespace(get_settings=lambda: {"workdir_path": str(workdir)})
    project_helpers = types.SimpleNamespace(
        get_context_project_name=lambda context: None,
        get_project_folder=lambda name: str(projects_parent / name),
        get_projects_parent_folder=lambda: str(projects_parent),
    )
    monkeypatch.setattr(document_store, "_settings", lambda: settings_helpers)
    monkeypatch.setattr(document_store, "_projects", lambda: project_helpers)

    workdir.mkdir(parents=True, exist_ok=True)
    documents.mkdir(parents=True, exist_ok=True)
    projects_parent.mkdir(parents=True, exist_ok=True)
    document_store.ensure_dirs()
    return types.SimpleNamespace(
        state=state,
        backups=backups,
        workdir=workdir,
        documents=documents,
        projects_parent=projects_parent,
        project_helpers=project_helpers,
    )


def test_document_artifact_create_defaults_to_markdown(office_state):
    doc = document_store.create_document("document", "Research Note", content="A precise note.")

    assert doc["extension"] == "md"
    assert Path(doc["path"]).parent == office_state.workdir
    assert Path(doc["path"]).read_text(encoding="utf-8").startswith("# Research Note")


@pytest.mark.parametrize(
    ("kind", "title", "fmt", "expected_name"),
    [
        ("document", "real-chat-canvas-smoke.md", "md", "real-chat-canvas-smoke.md"),
        ("document", "Board Memo.ODT", "odt", "Board Memo.odt"),
        ("spreadsheet", "Budget.ods", "ods", "Budget.ods"),
        ("presentation", "Roadmap.odp", "odp", "Roadmap.odp"),
    ],
)
def test_create_document_does_not_duplicate_matching_extension(office_state, kind, title, fmt, expected_name):
    doc = document_store.create_document(kind, title, fmt, content="Smoke")

    assert Path(doc["path"]).name == expected_name


def test_explicit_docx_creates_valid_word_package(office_state):
    doc = document_store.create_document("document", "Board Memo", "docx", "A careful memo.")

    assert doc["extension"] == "docx"
    assert Path(doc["path"]).parent == office_state.documents
    assert libreoffice.validate_docx(doc["path"])["ok"] is True
    with zipfile.ZipFile(doc["path"]) as archive:
        assert "word/document.xml" in archive.namelist()


def test_odf_formats_create_valid_libreoffice_packages(office_state):
    writer = document_store.create_document("document", "Board Memo", "odt", "A careful memo.")
    sheet = document_store.create_document("spreadsheet", "Budget", "ods", "Name,Amount\nPlatform,1000")
    deck = document_store.create_document("presentation", "Roadmap", "odp", "Roadmap\nLaunch sequence")

    assert writer["extension"] == "odt"
    assert sheet["extension"] == "ods"
    assert deck["extension"] == "odp"
    assert Path(writer["path"]).parent == office_state.documents
    assert libreoffice.validate_odf(writer["path"])["ok"] is True
    assert libreoffice.validate_odf(sheet["path"])["ok"] is True
    assert libreoffice.validate_odf(deck["path"])["ok"] is True
    assert artifact_editor.read_artifact(writer)["text"].startswith("Board Memo")
    assert artifact_editor.read_artifact(sheet)["sheets"][0]["preview_rows"][1][1] == 1000
    assert artifact_editor.read_artifact(deck)["slides"][0]["title"] == "Roadmap"


def test_blank_docx_includes_editable_body_paragraph(office_state):
    doc = document_store.create_document("document", "Blank Memo", "docx", "")
    with zipfile.ZipFile(doc["path"]) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
        root = ET.fromstring(xml)

    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    assert len(list(root.iter(f"{{{word_ns}}}p"))) >= 2
    assert 'xml:space="preserve">&#160;</w:t>' in xml


def test_odf_and_ooxml_creation_and_direct_edits_still_work(office_state):
    odt = document_store.create_document("document", "Writer Memo", "odt", "Old phrase")
    updated_odt, odt_payload = artifact_editor.edit_artifact(
        odt,
        operation="replace_text",
        find="Old phrase",
        replace="New phrase",
    )
    odt_read = artifact_editor.read_artifact(updated_odt)

    assert odt_payload["changed"] is True
    assert "New phrase" in odt_read["text"]

    ods = document_store.create_document(
        "spreadsheet",
        "Budget ODS",
        "ods",
        "Name,Amount\nPlatform,1000",
    )
    updated_ods, ods_payload = artifact_editor.edit_artifact(
        ods,
        operation="set_cells",
        cells={"Sheet1!B2": 12500, "Sheet1!A3": "Research", "Sheet1!B3": 4700},
    )
    ods_read = artifact_editor.read_artifact(updated_ods)
    ods_rows = ods_read["sheets"][0]["preview_rows"]

    assert ods_payload["changed"] is True
    assert ods_rows[1][1] == 12500
    assert ods_rows[2][0] == "Research"

    odp = document_store.create_document(
        "presentation",
        "Roadmap ODP",
        "odp",
        "Roadmap\nLaunch sequence\n\n---\n\nNext\nPolish rollout",
    )
    updated_odp, odp_payload = artifact_editor.edit_artifact(
        odp,
        operation="set_slides",
        slides=[
            {"title": "Now", "bullets": ["Stabilize"]},
            {"title": "Next", "bullets": ["Polish"]},
        ],
    )
    odp_read = artifact_editor.read_artifact(updated_odp)

    assert odp_payload["changed"] is True
    assert odp_read["slide_count"] == 2
    assert odp_read["slides"][1]["title"] == "Next"

    sheet = document_store.create_document(
        "spreadsheet",
        "Budget",
        "xlsx",
        "Name,Amount\nPlatform,1000",
    )
    updated_sheet, sheet_payload = artifact_editor.edit_artifact(
        sheet,
        operation="set_cells",
        cells={"Sheet1!B2": 12500, "Sheet1!A3": "Research", "Sheet1!B3": 4700},
    )
    sheet_read = artifact_editor.read_artifact(updated_sheet)
    rows = sheet_read["sheets"][0]["preview_rows"]

    assert sheet_payload["changed"] is True
    assert rows[1][1] == 12500
    assert rows[2][0] == "Research"

    deck = document_store.create_document(
        "presentation",
        "Roadmap",
        "pptx",
        "Roadmap\nLaunch sequence\n\n---\n\nNext\nPolish rollout",
    )
    created_deck_read = artifact_editor.read_artifact(deck)
    with zipfile.ZipFile(deck["path"]) as archive:
        created_slide_names = [name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")]

    assert created_deck_read["slide_count"] == 2
    assert created_deck_read["slides"][0]["title"] == "Roadmap"
    assert created_deck_read["slides"][1]["title"] == "Next"
    assert len(created_slide_names) == 2

    updated_deck, deck_payload = artifact_editor.edit_artifact(
        deck,
        operation="set_slides",
        slides=[
            {"title": "Now", "bullets": ["Stabilize"]},
            {"title": "Next", "bullets": ["Polish"]},
        ],
    )
    deck_read = artifact_editor.read_artifact(updated_deck)

    assert deck_payload["changed"] is True
    assert deck_read["slide_count"] == 2
    assert deck_read["slides"][1]["title"] == "Next"


def test_ods_direct_edit_preserves_rows_beyond_preview_window_and_blank_separators(office_state):
    rows = [["Row", "Value"], ["alpha", 1], [], ["separator-survives", 2]]
    rows.extend([[f"item-{index}", index] for index in range(4, 96)])
    doc = document_store.create_document("spreadsheet", "Long ODS", "ods", "")
    updated, payload = artifact_editor.edit_artifact(
        doc,
        operation="set_rows",
        rows=rows,
    )
    updated, payload = artifact_editor.edit_artifact(
        updated,
        operation="set_cells",
        cells={"Sheet1!B90": 9000},
    )
    parsed = artifact_editor._ods_sheets_from_bytes(Path(updated["path"]).read_bytes(), max_rows=120, max_cols=10)

    assert payload["changed"] is True
    assert parsed[0]["rows"][2] == []
    assert parsed[0]["rows"][3][0] == "separator-survives"
    assert parsed[0]["rows"][89][1] == 9000


def test_document_artifact_accepts_method_alias_for_ods_create(office_state, monkeypatch):
    tool_module = types.ModuleType("helpers.tool")

    class Response:
        def __init__(self, message, break_loop, additional=None):
            self.message = message
            self.break_loop = break_loop
            self.additional = additional

    class Tool:
        def __init__(self, agent, name, method, args, message, loop_data, **kwargs):
            self.agent = agent
            self.name = name
            self.method = method
            self.args = args
            self.message = message
            self.loop_data = loop_data

    tool_module.Response = Response
    tool_module.Tool = Tool
    monkeypatch.setitem(sys.modules, "helpers.tool", tool_module)
    spec = importlib.util.spec_from_file_location(
        "test_document_artifact_tool",
        PROJECT_ROOT / "plugins" / "_office" / "tools" / "document_artifact.py",
    )
    document_artifact_module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(document_artifact_module)
    DocumentArtifact = document_artifact_module.DocumentArtifact

    tool = DocumentArtifact(
        agent=None,
        name="document_artifact",
        method=None,
        args={},
        message="",
        loop_data=None,
    )

    response = asyncio.run(
        tool.execute(
            method="create",
            kind="document",
            title="New Calc Workbook",
            format="ods",
            content="Sheet1\n",
        )
    )
    payload = json.loads(response.message)

    assert payload["action"] == "create"
    assert payload["document"]["extension"] == "ods"
    assert Path(payload["document"]["path"]).name == "New Calc Workbook.ods"
    assert Path(document_store._path_from_a0(payload["document"]["path"])).exists()


def test_odf_is_advertised_and_docx_remains_explicit_compatibility(office_state):
    prompt = (PROJECT_ROOT / "plugins" / "_office" / "prompts" / "agent.system.tool.document_artifact.md").read_text(
        encoding="utf-8",
    )

    assert "formats: md odt ods odp docx xlsx pptx" in prompt
    assert "ODF is first-class for LibreOffice" in prompt
    assert "DOCX/XLSX/PPTX are compatibility formats" in prompt
    assert "`method` is accepted as an alias for action" in prompt
    assert "they do not open the canvas automatically" in prompt
    assert "Download and Open in canvas message actions" in prompt
    doc = document_store.create_document("document", "Use ODT", "odt", "")
    assert doc["extension"] == "odt"


def test_project_scoped_creation_uses_active_project_root(office_state, monkeypatch):
    project_root = office_state.projects_parent / "apollo"
    project_root.mkdir(parents=True, exist_ok=True)
    context = object()
    agent_module = types.SimpleNamespace(
        AgentContext=types.SimpleNamespace(get=staticmethod(lambda context_id: context))
    )

    monkeypatch.setitem(sys.modules, "agent", agent_module)
    monkeypatch.setattr(office_state.project_helpers, "get_context_project_name", lambda active_context: "apollo")
    monkeypatch.setattr(office_state.project_helpers, "get_project_folder", lambda name: str(project_root))

    markdown = document_store.create_document("document", "Project Note", "md", "Scoped.", context_id="ctx-project")
    odt = document_store.create_document("document", "Project Memo", "odt", "Scoped.", context_id="ctx-project")

    assert Path(markdown["path"]).parent == project_root
    assert Path(odt["path"]).parent == project_root / "documents"


def test_non_project_creation_uses_configured_workdir(office_state):
    markdown = document_store.create_document("document", "Workdir Note", content="Plain.")
    spreadsheet = document_store.create_document("spreadsheet", "Workdir Sheet", "ods", "Name,Value")

    assert markdown["extension"] == "md"
    assert Path(markdown["path"]).parent == office_state.workdir
    assert Path(spreadsheet["path"]).parent == office_state.documents


def test_sessions_and_canvas_context_are_neutral(office_state):
    doc = document_store.create_document("document", "Canvas Context", "md", "Private body text.")
    session = document_store.create_session(doc["file_id"], "user-a", "write", "http://localhost:32080")

    open_docs = document_store.get_open_documents()
    context = canvas_context.build_context()

    assert open_docs[0]["file_id"] == doc["file_id"]
    assert "document artifacts" in context
    assert "Private body text" not in context
    assert document_store.close_session(session_id=session["session_id"]) == 1
    assert document_store.get_open_documents() == []


def test_markdown_save_tracks_version_history(office_state):
    doc = document_store.create_document("document", "Versioned", "md", "First")
    updated = document_store.write_markdown(doc["file_id"], "# Versioned\n\nSecond\n")
    history = document_store.version_history(doc["file_id"])

    assert updated["version"] == 2
    assert history
    assert Path(updated["path"]).read_text(encoding="utf-8").endswith("Second\n")


def test_document_path_update_preserves_file_id_after_rename(office_state):
    doc = document_store.create_document("document", "Rename Me", "md", "Body")
    original = Path(doc["path"])
    renamed = original.with_name("Renamed.md")
    original.rename(renamed)

    updated = document_store.update_document_path(doc["file_id"], renamed)

    assert updated["file_id"] == doc["file_id"]
    assert updated["basename"] == "Renamed.md"
    assert updated["path"] == str(renamed)
    assert document_store.get_document(doc["file_id"])["path"] == str(renamed)


def test_document_rename_materializes_missing_markdown_with_editor_text(office_state):
    doc = document_store.create_document("document", "Unsaved Draft", "md", "Seed")
    original = Path(doc["path"])
    original.unlink()
    renamed = original.with_name("Renamed Draft.md")

    updated = document_store.rename_document(
        doc["file_id"],
        renamed,
        content="# Renamed Draft\n\nCanvas text",
    )

    assert updated["file_id"] == doc["file_id"]
    assert updated["basename"] == "Renamed Draft.md"
    assert updated["path"] == str(renamed)
    assert renamed.read_text(encoding="utf-8") == "# Renamed Draft\n\nCanvas text"


def test_document_rename_saves_dirty_markdown_and_removes_original(office_state):
    doc = document_store.create_document("document", "Dirty Rename", "md", "Old")
    original = Path(doc["path"])
    renamed = original.with_name("Clean Rename.md")

    updated = document_store.rename_document(
        doc["file_id"],
        renamed,
        content="# Clean Rename\n\nFresh text",
    )

    assert updated["version"] == 2
    assert not original.exists()
    assert renamed.read_text(encoding="utf-8") == "# Clean Rename\n\nFresh text"


def test_direct_markdown_edits_refresh_open_canvas_session(office_state, monkeypatch):
    manager = markdown_sessions.MarkdownSessionManager()
    monkeypatch.setattr(markdown_sessions, "_manager", manager, raising=False)
    doc = document_store.create_document("document", "Receiver", "md", "First")
    session = manager.open(doc)

    artifact_editor.edit_artifact(doc, operation="set_text", content="# Receiver\n\nSecond")

    assert manager._sessions[session["session_id"]].text == "# Receiver\n\nSecond"


def test_markdown_session_rejects_office_binaries(office_state):
    manager = markdown_sessions.MarkdownSessionManager()
    doc = document_store.create_document("document", "Desktop Only", "odt", "Native text")

    with pytest.raises(ValueError, match="Open .odt files in the Desktop"):
        manager.open(doc)


def test_thunar_defaults_preserve_existing_profile_settings(tmp_path):
    thunar_xml = tmp_path / "thunar.xml"
    thunar_xml.write_text(
        """<?xml version="1.1" encoding="UTF-8"?>
<channel name="thunar" version="1.0">
  <property name="last-view" type="string" value="ThunarDetailsView"/>
  <property name="last-window-width" type="int" value="900"/>
  <property name="last-show-hidden" type="bool" value="false"/>
</channel>
""",
        encoding="utf-8",
    )

    libreoffice_desktop._write_thunar_defaults(thunar_xml)

    root = ET.parse(thunar_xml).getroot()
    values = {child.get("name"): child.get("value") for child in root.findall("property")}
    assert values["last-view"] == "ThunarDetailsView"
    assert values["last-window-width"] == "900"
    assert values["last-show-hidden"] == "true"


def test_official_libreoffice_desktop_status_and_url_contract(tmp_path, monkeypatch):
    xpra_html = tmp_path / "xpra" / "www"
    xpra_html.mkdir(parents=True)
    (xpra_html / "index.html").write_text("xpra", encoding="utf-8")

    monkeypatch.setattr(libreoffice_desktop.libreoffice, "find_soffice", lambda: "/usr/bin/soffice")
    monkeypatch.setattr(
        libreoffice_desktop.shutil,
        "which",
        lambda name: f"/usr/bin/{name}"
        if name
        in {
            "xpra",
            "Xvfb",
            "xfce4-session",
            "dbus-launch",
            "xrandr",
            "xdotool",
            "thunar",
            "xfce4-terminal",
            "xfce4-settings-manager",
            "gio",
        }
        else "",
    )
    monkeypatch.setattr(libreoffice_desktop.virtual_desktop, "XPRA_HTML_ROOT_CANDIDATES", (xpra_html,))
    monkeypatch.setattr(libreoffice_desktop.virtual_desktop, "_package_installed", lambda package: True)

    status = libreoffice_desktop.collect_desktop_status()
    url = libreoffice_desktop._xpra_url("abc123")

    assert status["healthy"] is True
    assert status["xpra_html_root"] == str(xpra_html)
    assert url.startswith("/desktop/session/abc123/index.html?")
    assert "path=%2Fdesktop%2Fsession%2Fabc123%2F" in url
    assert "xpramenu=false" in url
    assert "floating_menu=false" in url
    assert "file_transfer=true" in url
    assert "sound=false" in url
    assert "encoding=jpeg" in url
    assert "quality=85" in url
    assert "speed=80" in url
    assert "printing=true" in url


def test_office_session_desktop_state_action_defaults_without_screenshot(monkeypatch):
    api_module = types.ModuleType("helpers.api")

    class ApiHandler:
        def __init__(self, app=None, thread_lock=None):
            self.app = app
            self.thread_lock = thread_lock

    api_module.ApiHandler = ApiHandler
    api_module.Request = object
    monkeypatch.setitem(sys.modules, "helpers.api", api_module)
    monkeypatch.delitem(sys.modules, "plugins._office.api.office_session", raising=False)

    from plugins._office.api import office_session

    calls = []

    class FakeManager:
        def state(self, *, include_screenshot=False):
            calls.append(include_screenshot)
            return {
                "ok": True,
                "display": ":120",
                "profile_dir": "/a0/tmp/_office/desktop/profiles/agent-zero-desktop",
                "size": {"width": 1440, "height": 900},
                "pointer": {"x": 0, "y": 0, "screen": 0, "window": 0},
                "active_window": None,
                "windows": [],
                "screenshot": {"ok": False, "path": ""},
                "capabilities": {},
                "errors": [],
            }

    monkeypatch.setattr(office_session.libreoffice_desktop, "get_manager", lambda: FakeManager())
    handler = office_session.OfficeSession(app=None, thread_lock=None)
    request = types.SimpleNamespace(headers={}, host_url="http://localhost:32080")

    default_result = asyncio.run(handler.process({"action": "desktop_state"}, request))
    screenshot_result = asyncio.run(
        handler.process({"action": "desktop_state", "include_screenshot": True}, request),
    )

    assert default_result["ok"] is True
    assert screenshot_result["ok"] is True
    assert calls == [False, True]
    monkeypatch.delitem(sys.modules, "plugins._office.api.office_session", raising=False)
    api_package = sys.modules.get("plugins._office.api")
    if api_package is not None:
        monkeypatch.delattr(api_package, "office_session", raising=False)


def test_office_session_desktop_shutdown_action_calls_manager(monkeypatch):
    api_module = types.ModuleType("helpers.api")

    class ApiHandler:
        def __init__(self, app=None, thread_lock=None):
            self.app = app
            self.thread_lock = thread_lock

    api_module.ApiHandler = ApiHandler
    api_module.Request = object
    monkeypatch.setitem(sys.modules, "helpers.api", api_module)
    monkeypatch.delitem(sys.modules, "plugins._office.api.office_session", raising=False)

    from plugins._office.api import office_session

    calls = []

    class FakeManager:
        def shutdown_system_desktop(self, *, save_first=True, source="api"):
            calls.append({"save_first": save_first, "source": source})
            return {
                "ok": True,
                "closed": 1,
                "shutdown": True,
                "intentional_shutdown": True,
                "source": source,
            }

    monkeypatch.setattr(office_session.libreoffice_desktop, "get_manager", lambda: FakeManager())
    handler = office_session.OfficeSession(app=None, thread_lock=None)
    request = types.SimpleNamespace(headers={}, host_url="http://localhost:32080")

    result = asyncio.run(
        handler.process({"action": "desktop_shutdown", "save_first": False, "source": "ui"}, request),
    )

    assert result["ok"] is True
    assert result["intentional_shutdown"] is True
    assert calls == [{"save_first": False, "source": "ui"}]
    monkeypatch.delitem(sys.modules, "plugins._office.api.office_session", raising=False)
    api_package = sys.modules.get("plugins._office.api")
    if api_package is not None:
        monkeypatch.delattr(api_package, "office_session", raising=False)


def test_official_libreoffice_desktop_manager_opens_binary_session(office_state, tmp_path, monkeypatch):
    class FakeProcess:
        pid = 4242

        def poll(self):
            return None

        def terminate(self):
            return None

        def wait(self, timeout=None):
            return 0

        def kill(self):
            return None

    monkeypatch.setattr(libreoffice_desktop, "STATE_DIR", tmp_path / "desktop")
    monkeypatch.setattr(libreoffice_desktop, "SESSION_DIR", tmp_path / "desktop" / "sessions")
    monkeypatch.setattr(libreoffice_desktop, "PROFILE_DIR", tmp_path / "desktop" / "profiles")
    monkeypatch.setattr(libreoffice_desktop, "collect_desktop_status", lambda: {"healthy": True, "message": "ok"})
    monkeypatch.setattr(libreoffice_desktop.libreoffice, "find_soffice", lambda: "/usr/bin/soffice")
    monkeypatch.setattr(libreoffice_desktop, "_port_is_free", lambda port: True)
    monkeypatch.setattr(libreoffice_desktop.virtual_desktop, "has_window", lambda **kwargs: True)
    real_get_abs_path = libreoffice_desktop.files.get_abs_path

    def fake_get_abs_path(*parts):
        if parts and parts[0] == "usr":
            return str(tmp_path.joinpath(*parts))
        return real_get_abs_path(*parts)

    monkeypatch.setattr(libreoffice_desktop.files, "get_abs_path", fake_get_abs_path)

    def fake_spawn(self, session):
        session.profile_dir.mkdir(parents=True, exist_ok=True)
        session.processes["xpra"] = FakeProcess()

    def fake_open_document(self, session, doc):
        session.processes[f"soffice-{doc['file_id']}"] = FakeProcess()

    monkeypatch.setattr(libreoffice_desktop.LibreOfficeDesktopManager, "_spawn_desktop_locked", fake_spawn)
    monkeypatch.setattr(libreoffice_desktop.LibreOfficeDesktopManager, "_open_document_locked", fake_open_document)

    doc = document_store.create_document("spreadsheet", "Official Sheet", "ods", "Name,Value\nA,1")
    manager = libreoffice_desktop.LibreOfficeDesktopManager()
    payload = manager.open(doc)

    assert payload["available"] is True
    assert payload["extension"] == "ods"
    assert payload["url"].startswith("/desktop/session/")
    registry = tmp_path / "desktop" / "profiles" / payload["session_id"] / "user" / "registrymodifications.xcu"
    registry_text = registry.read_text(encoding="utf-8")
    assert "ooSetupInstCompleted" in registry_text
    assert "FirstRun" in registry_text
    assert "Office.Paths/Variables" in registry_text
    assert "Office.Paths:NamedPath['Work']" in registry_text
    assert office_state.workdir.as_uri() in registry_text
    writer_launcher = tmp_path / "desktop" / "profiles" / payload["session_id"] / "Desktop" / "LibreOffice Writer.desktop"
    writer_text = writer_launcher.read_text(encoding="utf-8")
    assert "--writer" in writer_text
    assert f"Path={office_state.workdir}" in writer_text
    assert "X-XFCE-Trusted=true" in writer_text
    terminal_launcher = tmp_path / "desktop" / "profiles" / payload["session_id"] / "Desktop" / "Terminal.desktop"
    files_launcher = tmp_path / "desktop" / "profiles" / payload["session_id"] / "Desktop" / "Files.desktop"
    settings_launcher = tmp_path / "desktop" / "profiles" / payload["session_id"] / "Desktop" / "Settings.desktop"
    terminal_text = terminal_launcher.read_text(encoding="utf-8")
    settings_text = settings_launcher.read_text(encoding="utf-8")
    browser_launcher = tmp_path / "desktop" / "profiles" / payload["session_id"] / "Desktop" / "Browser.desktop"
    browser_text = browser_launcher.read_text(encoding="utf-8")
    assert "xfce4-terminal" in terminal_text
    assert "org.xfce.terminal" in terminal_text
    assert not files_launcher.exists()
    assert "open-url" in browser_text
    assert "firefox" not in browser_text.lower()
    assert "xfce4-settings-manager" in settings_text
    assert "org.xfce.settings.manager" in settings_text
    link_targets = {
        "Projects": "usr/projects",
        "Skills": "usr/skills",
        "Agents": "usr/agents",
        "Downloads": "usr/downloads",
    }
    workdir_link = tmp_path / "desktop" / "profiles" / payload["session_id"] / "Desktop" / "Workdir"
    assert workdir_link.is_symlink()
    assert workdir_link.resolve() == office_state.workdir
    for link_name, target in link_targets.items():
        link = tmp_path / "desktop" / "profiles" / payload["session_id"] / "Desktop" / link_name
        assert link.is_symlink()
        assert str(link.resolve()).endswith(target)
    xpra_override = (
        tmp_path
        / "desktop"
        / "profiles"
        / payload["session_id"]
        / ".local"
        / "share"
        / "applications"
        / "xpra-gui.desktop"
    )
    assert "Hidden=true" in xpra_override.read_text(encoding="utf-8")
    desktop_profile = (
        tmp_path
        / "desktop"
        / "profiles"
        / payload["session_id"]
        / ".config"
        / "xfce4"
        / "xfconf"
        / "xfce-perchannel-xml"
        / "xfce4-desktop.xml"
    )
    desktop_profile_text = desktop_profile.read_text(encoding="utf-8")
    assert "desktop-icons" in desktop_profile_text
    assert "image-path" in desktop_profile_text
    assert "usr/downloads" in desktop_profile_text
    thunar_profile = (
        tmp_path
        / "desktop"
        / "profiles"
        / payload["session_id"]
        / ".config"
        / "xfce4"
        / "xfconf"
        / "xfce-perchannel-xml"
        / "thunar.xml"
    ).read_text(encoding="utf-8")
    assert 'name="last-show-hidden" type="bool" value="true"' in thunar_profile
    user_dirs = (
        tmp_path
        / "desktop"
        / "profiles"
        / payload["session_id"]
        / ".config"
        / "user-dirs.dirs"
    ).read_text(encoding="utf-8")
    assert 'XDG_PICTURES_DIR="' in user_dirs
    assert "usr/downloads" in user_dirs
    assert f'XDG_DOCUMENTS_DIR="{office_state.workdir}"' in user_dirs
    panel_profile = (
        tmp_path
        / "desktop"
        / "profiles"
        / payload["session_id"]
        / ".config"
        / "xfce4"
        / "xfconf"
        / "xfce-perchannel-xml"
        / "xfce4-panel.xml"
    ).read_text(encoding="utf-8")
    assert "panel-1" in panel_profile
    assert "panel-2" not in panel_profile
    assert 'value="actions"' not in panel_profile
    assert 'value="launcher"' in panel_profile
    assert "agent-zero-shutdown.desktop" in panel_profile
    shutdown_app = (
        tmp_path
        / "desktop"
        / "profiles"
        / payload["session_id"]
        / ".local"
        / "share"
        / "applications"
        / "agent-zero-shutdown.desktop"
    ).read_text(encoding="utf-8")
    assert "Shutdown Desktop" in shutdown_app
    assert "shutdown-desktop" in shutdown_app
    shutdown_panel_launcher = (
        tmp_path
        / "desktop"
        / "profiles"
        / payload["session_id"]
        / ".config"
        / "xfce4"
        / "panel"
        / "launcher-9"
        / "agent-zero-shutdown.desktop"
    ).read_text(encoding="utf-8")
    assert "Shutdown Desktop" in shutdown_panel_launcher
    assert "shutdown-desktop" in shutdown_panel_launcher
    shutdown_script = (
        tmp_path
        / "desktop"
        / "profiles"
        / payload["session_id"]
        / ".agent-zero"
        / "shutdown-desktop"
    ).read_text(encoding="utf-8")
    assert "CONFIRM_SECONDS" in shutdown_script
    assert "ARM_PATH" in shutdown_script
    assert "Click Shutdown Desktop again" in shutdown_script
    assert "xmessage" in shutdown_script
    assert '"-buttons",' in shutdown_script
    desktop_helper = (
        PROJECT_ROOT / "plugins" / "_office" / "helpers" / "libreoffice_desktop.py"
    ).read_text(encoding="utf-8")
    assert "_refresh_xfce_desktop" in desktop_helper
    assert "DBUS_SESSION_BUS_ADDRESS" in desktop_helper
    autostart = (
        tmp_path
        / "desktop"
        / "profiles"
        / payload["session_id"]
        / ".config"
        / "autostart"
        / "agent-zero-office-desktop.desktop"
    )
    assert "prepare-xfce-profile.sh" in autostart.read_text(encoding="utf-8")
    profile_script = (
        tmp_path
        / "desktop"
        / "profiles"
        / payload["session_id"]
        / "prepare-xfce-profile.sh"
    ).read_text(encoding="utf-8")
    assert '"$HOME"/Desktop/*.desktop' in profile_script
    assert "agent-zero-settings.desktop" not in profile_script
    assert "metadata::xfce-exe-checksum" in profile_script
    assert "xfconf-query -c thunar -p /last-show-hidden" in profile_script
    assert "xfconf-query -c xfce4-panel" not in profile_script
    assert "launcher-*" not in profile_script
    for filename in (
        "exo-mail-reader.desktop",
        "exo-web-browser.desktop",
        "xfce4-mail-reader.desktop",
        "xfce4-web-browser.desktop",
        "xfce4-session-logout.desktop",
        "xfce4-lock-screen.desktop",
        "xflock4.desktop",
        "xfce4-switch-user.desktop",
    ):
        entry = (
            tmp_path
            / "desktop"
            / "profiles"
            / payload["session_id"]
            / ".local"
            / "share"
            / "applications"
            / filename
        ).read_text(encoding="utf-8")
        assert "NoDisplay=true" in entry
        assert "Hidden=true" in entry
    assert manager.proxy_for_token(payload["token"]) == ("127.0.0.1", libreoffice_desktop.XPRA_PORT_BASE)
    assert manager.close(payload["session_id"], save_first=False)["closed"] == 0
    assert manager.close(payload["session_id"], save_first=False)["persistent"] is True


def test_shutdown_panel_launcher_requires_second_click(tmp_path):
    profile_dir = tmp_path / "desktop" / "profiles" / libreoffice_desktop.SYSTEM_SESSION_ID
    profile_dir.mkdir(parents=True)
    desktop_path = tmp_path / "workdir"
    desktop_path.mkdir()
    session = libreoffice_desktop.DesktopSession(
        session_id=libreoffice_desktop.SYSTEM_SESSION_ID,
        file_id=libreoffice_desktop.SYSTEM_FILE_ID,
        extension="desktop",
        path=str(desktop_path),
        title=libreoffice_desktop.SYSTEM_TITLE,
        display=libreoffice_desktop.DISPLAY_BASE,
        xpra_port=libreoffice_desktop.XPRA_PORT_BASE,
        token=libreoffice_desktop.SYSTEM_SESSION_ID,
        url="/desktop/session/agent-zero-desktop/index.html",
        profile_dir=profile_dir,
    )
    script = libreoffice_desktop._write_shutdown_bridge_script(session)
    request = libreoffice_desktop._shutdown_request_path(session)
    arm = libreoffice_desktop._shutdown_arm_path(session)
    env = dict(os.environ)
    env.pop("DISPLAY", None)

    subprocess.run([sys.executable, str(script)], check=True, env=env)

    assert arm.exists()
    assert not request.exists()

    subprocess.run([sys.executable, str(script)], check=True, env=env)

    payload = json.loads(request.read_text(encoding="utf-8"))
    assert payload["source"] == "tray"
    assert payload["armed_at"] <= payload["created_at"]
    assert not arm.exists()


def test_libreoffice_desktop_sync_consumes_shutdown_marker(tmp_path, monkeypatch):
    class FakeProcess:
        pid = 5252
        terminated = False

        def poll(self):
            return None if not self.terminated else 0

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            self.terminated = True
            return 0

        def kill(self):
            self.terminated = True

    monkeypatch.setattr(libreoffice_desktop, "STATE_DIR", tmp_path / "desktop")
    monkeypatch.setattr(libreoffice_desktop, "SESSION_DIR", tmp_path / "desktop" / "sessions")
    monkeypatch.setattr(libreoffice_desktop, "PROFILE_DIR", tmp_path / "desktop" / "profiles")

    profile_dir = tmp_path / "desktop" / "profiles" / libreoffice_desktop.SYSTEM_SESSION_ID
    profile_dir.mkdir(parents=True)
    desktop_path = tmp_path / "workdir"
    desktop_path.mkdir()
    session = libreoffice_desktop.DesktopSession(
        session_id=libreoffice_desktop.SYSTEM_SESSION_ID,
        file_id=libreoffice_desktop.SYSTEM_FILE_ID,
        extension="desktop",
        path=str(desktop_path),
        title=libreoffice_desktop.SYSTEM_TITLE,
        display=libreoffice_desktop.DISPLAY_BASE,
        xpra_port=libreoffice_desktop.XPRA_PORT_BASE,
        token=libreoffice_desktop.SYSTEM_SESSION_ID,
        url="/desktop/session/agent-zero-desktop/index.html",
        profile_dir=profile_dir,
        processes={"xpra": FakeProcess()},
    )
    manager = libreoffice_desktop.LibreOfficeDesktopManager()
    manager._sessions[session.session_id] = session
    manager._write_manifest(session)
    libreoffice_desktop._write_url_bridge_script(session)
    shutdown_request = libreoffice_desktop._shutdown_request_path(session)
    shutdown_request.write_text('{"source": "tray", "created_at": 123.0}\n', encoding="utf-8")
    save_calls = []
    monkeypatch.setattr(
        manager,
        "save",
        lambda session_id, file_id="": save_calls.append((session_id, file_id)) or {"ok": True},
    )

    result = manager.sync(session_id=session.session_id)

    assert result["ok"] is True
    assert result["intentional_shutdown"] is True
    assert result["source"] == "tray"
    assert result["closed"] == 1
    assert save_calls == [(libreoffice_desktop.SYSTEM_SESSION_ID, "")]
    assert not shutdown_request.exists()
    assert not (libreoffice_desktop.SESSION_DIR / f"{session.session_id}.json").exists()
    assert manager.get(session.session_id) is None


def test_libreoffice_desktop_cleanup_preserves_live_owner_manifest(tmp_path, monkeypatch):
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    manifest = session_dir / "live.json"
    manifest.write_text(
        json.dumps({"owner_pid": os.getpid(), "pids": {"xpra": 987654}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(libreoffice_desktop, "SESSION_DIR", session_dir)
    monkeypatch.setattr(
        libreoffice_desktop,
        "_kill_pid",
        lambda _pid: pytest.fail("cleanup should not kill a desktop owned by a live UI process"),
    )

    result = libreoffice_desktop.cleanup_stale_runtime_state()

    assert result["killed"] == []
    assert manifest.exists()


def test_libreoffice_desktop_removes_stale_lock_file(tmp_path):
    doc_path = tmp_path / "Deck.pptx"
    doc_path.write_text("pptx", encoding="utf-8")
    lock_path = tmp_path / ".~lock.Deck.pptx#"
    lock_path.write_text("stale", encoding="utf-8")
    session = libreoffice_desktop.DesktopSession(
        session_id="session",
        file_id="file",
        extension="pptx",
        path=str(doc_path),
        title=doc_path.name,
        display=libreoffice_desktop.DISPLAY_BASE,
        xpra_port=libreoffice_desktop.XPRA_PORT_BASE,
        token="token",
        url="/desktop/session/token/index.html",
        profile_dir=tmp_path / "profile",
    )

    libreoffice_desktop.LibreOfficeDesktopManager()._remove_stale_lock_file(session)

    assert not lock_path.exists()


def test_cleanup_hook_removes_stale_runtime_state_idempotently(tmp_path, monkeypatch):
    source = tmp_path / "sources.list.d" / "retired.sources"
    keyring = tmp_path / "keyrings" / "retired.gpg"
    supervisor = tmp_path / "supervisor" / "retired.conf"
    runtime_dir = tmp_path / "runtime"
    marker = tmp_path / "state" / "cleanup.done"

    for path in (source, keyring, supervisor):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("old\n", encoding="utf-8")
    (runtime_dir / "nested").mkdir(parents=True, exist_ok=True)
    (runtime_dir / "nested" / "state.txt").write_text("old\n", encoding="utf-8")

    monkeypatch.setattr(hooks, "APT_SOURCE_FILE", source)
    monkeypatch.setattr(hooks, "APT_KEYRING_FILE", keyring)
    monkeypatch.setattr(hooks, "SUPERVISOR_FILE", supervisor)
    monkeypatch.setattr(hooks, "RUNTIME_DIRS", [runtime_dir])
    monkeypatch.setattr(hooks, "CLEANUP_MARKER", marker)
    monkeypatch.setattr(hooks, "_installed_packages", lambda packages: [])
    monkeypatch.setattr(hooks, "_kill_old_processes", lambda errors: None)

    def fake_ensure(installed, errors):
        assert not source.exists()
        installed.append("xpra")

    def fake_purge(removed, errors, **kwargs):
        return None

    monkeypatch.setattr(hooks, "_ensure_runtime_dependencies", fake_ensure)
    monkeypatch.setattr(hooks, "_purge_packages", fake_purge)

    first = hooks.cleanup_stale_runtime_state(force=True)
    second = hooks.cleanup_stale_runtime_state(force=True)
    skipped = hooks.cleanup_stale_runtime_state()

    assert first["ok"] is True
    assert first["installed"] == ["xpra"]
    assert second["ok"] is True
    assert skipped["skipped"] is True
    assert not source.exists()
    assert not keyring.exists()
    assert not supervisor.exists()
    assert not runtime_dir.exists()
    assert marker.exists()


def test_office_startup_defers_persistent_desktop_runtime(monkeypatch):
    calls = []
    cleanup_calls = []
    started_threads = []
    routes_module = types.ModuleType("plugins._office.helpers.libreoffice_desktop_routes")
    routes_module.install_route_hooks = lambda: calls.append("routes")
    monkeypatch.setitem(sys.modules, "plugins._office.helpers.libreoffice_desktop_routes", routes_module)
    monkeypatch.delitem(
        sys.modules,
        "plugins._office.extensions.python.startup_migration._20_office_routes",
        raising=False,
    )

    from plugins._office.extensions.python.startup_migration import _20_office_routes as office_startup

    monkeypatch.setattr(
        office_startup.hooks,
        "cleanup_stale_runtime_state",
        lambda: cleanup_calls.append("cleanup") or {"ok": True, "errors": [], "installed": [], "removed": []},
    )

    class FakeThread:
        def __init__(self, *, target, name, daemon):
            self.target = target
            self.name = name
            self.daemon = daemon

        def is_alive(self):
            return False

        def start(self):
            started_threads.append(self)

    monkeypatch.setattr(office_startup.threading, "Thread", FakeThread)

    office_startup.OfficeStartupCleanup(agent=None).execute()

    assert calls == ["routes"]
    assert cleanup_calls == []
    assert len(started_threads) == 1
    assert started_threads[0].name == "a0-office-runtime-preparation"
    assert started_threads[0].daemon is True
    assert not hasattr(office_startup, "libreoffice_desktop")

    started_threads[0].target()
    assert cleanup_calls == ["cleanup"]


def test_cleanup_hook_reruns_when_stale_packages_exist_after_old_marker(tmp_path, monkeypatch):
    marker = tmp_path / "state" / "cleanup.done"
    marker.parent.mkdir(parents=True)
    marker.write_text("old\n", encoding="utf-8")

    monkeypatch.setattr(hooks, "APT_SOURCE_FILE", tmp_path / "missing.sources")
    monkeypatch.setattr(hooks, "APT_KEYRING_FILE", tmp_path / "missing.gpg")
    monkeypatch.setattr(hooks, "SUPERVISOR_FILE", tmp_path / "missing.conf")
    monkeypatch.setattr(hooks, "RUNTIME_DIRS", [])
    monkeypatch.setattr(hooks, "CLEANUP_MARKER", marker)
    monkeypatch.setattr(hooks, "_installed_packages", lambda packages: ["coolwsd"])
    monkeypatch.setattr(hooks, "_ensure_runtime_dependencies", lambda installed, errors: None)
    monkeypatch.setattr(hooks, "_kill_old_processes", lambda errors: None)

    def fake_purge(removed, errors, **kwargs):
        removed.extend(kwargs["installed_packages"])

    monkeypatch.setattr(hooks, "_purge_packages", fake_purge)

    result = hooks.cleanup_stale_runtime_state()

    assert result["skipped"] is False
    assert result["removed"] == ["coolwsd"]


def test_cleanup_hook_removes_retired_supervisor_program_after_marker(tmp_path, monkeypatch):
    marker = tmp_path / "state" / "cleanup.done"
    marker.parent.mkdir(parents=True)
    marker.write_text("ok\n", encoding="utf-8")
    calls = []

    monkeypatch.setattr(hooks, "APT_SOURCE_FILE", tmp_path / "missing.sources")
    monkeypatch.setattr(hooks, "APT_KEYRING_FILE", tmp_path / "missing.gpg")
    monkeypatch.setattr(hooks, "SUPERVISOR_FILE", tmp_path / "missing.conf")
    monkeypatch.setattr(hooks, "RUNTIME_DIRS", [])
    monkeypatch.setattr(hooks, "CLEANUP_MARKER", marker)
    monkeypatch.setattr(hooks, "_installed_packages", lambda packages: [])
    monkeypatch.setattr(hooks, "_ensure_runtime_dependencies", lambda installed, errors: None)
    monkeypatch.setattr(hooks, "_cleanup_desktop_sessions", lambda errors: None)
    monkeypatch.setattr(hooks.shutil, "which", lambda name: "/usr/bin/supervisorctl" if name == "supervisorctl" else "")

    def fake_supervisorctl(*args):
        calls.append(args)
        if args == ("status", hooks.SUPERVISOR_PROGRAM):
            return types.SimpleNamespace(
                returncode=0,
                stdout="a0_office_collabora BACKOFF can't find command\n",
                stderr="",
            )
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hooks, "_supervisorctl", fake_supervisorctl)

    result = hooks.cleanup_stale_runtime_state()

    assert result["ok"] is True
    assert result["skipped"] is True
    assert result["errors"] == []
    assert calls == [
        ("status", hooks.SUPERVISOR_PROGRAM),
        ("stop", hooks.SUPERVISOR_PROGRAM),
        ("remove", hooks.SUPERVISOR_PROGRAM),
        ("reread",),
        ("update",),
    ]


def test_cleanup_hook_installs_missing_libreoffice_desktop_dependencies(monkeypatch):
    calls = []
    installed_state = {"xpra": False}

    monkeypatch.setattr(hooks.os, "geteuid", lambda: 0)
    monkeypatch.setattr(hooks.shutil, "which", lambda name: f"/usr/bin/{name}" if name in {"apt-get", "dpkg-query"} else "")
    monkeypatch.setattr(hooks, "RUNTIME_PACKAGES", ("xpra",))
    monkeypatch.setattr(hooks, "_package_installed", lambda package: installed_state.get(package, False))

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[:2] == ["apt-get", "install"]:
            installed_state["xpra"] = True
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hooks.subprocess, "run", fake_run)
    installed = []
    errors = []

    hooks._ensure_runtime_dependencies(installed, errors)

    assert installed == ["xpra"]
    assert errors == []
    assert calls[0] == ["apt-get", "update"]
    assert calls[1][:4] == ["apt-get", "install", "-y", "--no-install-recommends"]


def test_cleanup_hook_enables_official_xpra_repo_when_kali_lacks_candidate(tmp_path, monkeypatch):
    calls = []
    installed_state = {"xpra": False, "ca-certificates": True}
    keyring = tmp_path / "keyrings" / "xpra.asc"
    source = tmp_path / "sources.list.d" / "xpra.sources"

    monkeypatch.setattr(hooks.os, "geteuid", lambda: 0)
    monkeypatch.setattr(
        hooks.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"apt-get", "dpkg-query", "apt-cache"} else "",
    )
    monkeypatch.setattr(hooks, "RUNTIME_PACKAGES", ("xpra",))
    monkeypatch.setattr(hooks, "XPRA_KEYRING_FILE", keyring)
    monkeypatch.setattr(hooks, "XPRA_SOURCE_FILE", source)
    monkeypatch.setattr(hooks, "_download", lambda url: b"xpra-key")
    monkeypatch.setattr(hooks, "_read_os_release", lambda: {"ID": "kali", "VERSION_CODENAME": "kali-rolling"})
    monkeypatch.setattr(hooks, "_dpkg_architecture", lambda: "amd64")
    monkeypatch.setattr(hooks, "_package_installed", lambda package: installed_state.get(package, False))

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[:2] == ["apt-cache", "policy"]:
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        if command[:2] == ["apt-get", "install"]:
            installed_state["xpra"] = True
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hooks.subprocess, "run", fake_run)
    installed = []
    errors = []

    hooks._ensure_runtime_dependencies(installed, errors)

    assert errors == []
    assert installed == ["xpra"]
    assert keyring.read_bytes() == b"xpra-key"
    assert "URIs: https://xpra.org/beta" in source.read_text(encoding="utf-8")
    assert "Suites: sid" in source.read_text(encoding="utf-8")
    assert calls.count(["apt-get", "update"]) == 2
    assert calls[-1][:4] == ["apt-get", "install", "-y", "--no-install-recommends"]


def test_cleanup_hook_uses_trixie_xpra_components_for_kali_arm64(tmp_path, monkeypatch):
    calls = []
    installed_state = {"xpra-server": False, "xpra-x11": False, "xpra-html5": False, "ca-certificates": True}
    keyring = tmp_path / "keyrings" / "xpra.asc"
    source = tmp_path / "sources.list.d" / "xpra.sources"

    monkeypatch.setattr(hooks.os, "geteuid", lambda: 0)
    monkeypatch.setattr(
        hooks.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"apt-get", "dpkg-query", "apt-cache"} else "",
    )
    monkeypatch.setattr(hooks, "RUNTIME_PACKAGES", ("xpra-server", "xpra-x11", "xpra-html5"))
    monkeypatch.setattr(hooks, "XPRA_KEYRING_FILE", keyring)
    monkeypatch.setattr(hooks, "XPRA_SOURCE_FILE", source)
    monkeypatch.setattr(hooks, "_download", lambda url: b"xpra-key")
    monkeypatch.setattr(hooks, "_read_os_release", lambda: {"ID": "kali", "VERSION_CODENAME": "kali-rolling"})
    monkeypatch.setattr(hooks, "_dpkg_architecture", lambda: "arm64")
    monkeypatch.setattr(hooks, "_package_installed", lambda package: installed_state.get(package, False))

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[:2] == ["apt-cache", "policy"]:
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        if command[:2] == ["apt-get", "install"]:
            for package in command[4:]:
                installed_state[package] = True
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hooks.subprocess, "run", fake_run)
    installed = []
    errors = []

    hooks._ensure_runtime_dependencies(installed, errors)

    assert errors == []
    assert installed == ["xpra-server", "xpra-x11", "xpra-html5"]
    source_text = source.read_text(encoding="utf-8")
    assert "URIs: https://xpra.org\n" in source_text
    assert "Suites: trixie" in source_text
    assert "xpra" not in calls[-1]
    assert calls[-1][-3:] == ["xpra-server", "xpra-x11", "xpra-html5"]


def test_cleanup_hook_skips_optional_xpra_client_codec_conflict(monkeypatch):
    calls = []
    installed_state = {
        "xpra-server": True,
        "xpra-client": False,
        "xpra-client-gtk3": False,
        "xpra-x11": True,
        "xpra-html5": True,
    }
    codec_error = (
        "E: Unable to satisfy dependencies. Reached two conflicting assignments:\n"
        "   1. xpra-codecs:arm64=6.4.3-r0-1 is selected for install\n"
        "   2. xpra-codecs:arm64 Depends libvpx9 (>= 1.12.0)\n"
        "      but none of the choices are installable: [no choices]"
    )

    monkeypatch.setattr(hooks.os, "geteuid", lambda: 0)
    monkeypatch.setattr(
        hooks.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"apt-get", "dpkg-query", "apt-cache"} else "",
    )
    monkeypatch.setattr(
        hooks,
        "RUNTIME_PACKAGES",
        ("xpra-server", "xpra-client", "xpra-client-gtk3", "xpra-x11", "xpra-html5"),
    )
    monkeypatch.setattr(hooks, "_package_installed", lambda package: installed_state.get(package, False))

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[:2] == ["apt-cache", "policy"]:
            return types.SimpleNamespace(returncode=0, stdout="Candidate: 6.4.3-r0-1\n", stderr="")
        if command[:2] == ["apt-get", "install"]:
            return types.SimpleNamespace(returncode=100, stdout="", stderr=codec_error)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hooks.subprocess, "run", fake_run)
    installed = []
    errors = []

    hooks._ensure_runtime_dependencies(installed, errors)

    assert installed == []
    assert errors == []
    assert calls[-1][-2:] == ["xpra-client", "xpra-client-gtk3"]


def test_cleanup_hook_reports_required_xpra_codec_conflict(monkeypatch):
    codec_error = (
        "E: Unable to satisfy dependencies. Reached two conflicting assignments:\n"
        "   1. xpra-codecs:arm64=6.4.3-r0-1 is selected for install\n"
        "   2. xpra-codecs:arm64 Depends libvpx9 (>= 1.12.0)\n"
        "      but none of the choices are installable: [no choices]"
    )

    monkeypatch.setattr(hooks.os, "geteuid", lambda: 0)
    monkeypatch.setattr(
        hooks.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"apt-get", "dpkg-query", "apt-cache"} else "",
    )
    monkeypatch.setattr(hooks, "RUNTIME_PACKAGES", ("xpra-server",))
    monkeypatch.setattr(hooks, "_package_installed", lambda package: False)

    def fake_run(command, **kwargs):
        if command[:2] == ["apt-cache", "policy"]:
            return types.SimpleNamespace(returncode=0, stdout="Candidate: 6.4.3-r0-1\n", stderr="")
        if command[:2] == ["apt-get", "install"]:
            return types.SimpleNamespace(returncode=100, stdout="", stderr=codec_error)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hooks.subprocess, "run", fake_run)
    installed = []
    errors = []

    hooks._ensure_runtime_dependencies(installed, errors)

    assert installed == []
    assert errors == [codec_error]


def test_self_update_launch_invokes_office_cleanup(monkeypatch, tmp_path):
    manager = load_self_update_manager()
    calls = []

    class Logger:
        def log(self, message=""):
            return None

    class Process:
        pass

    monkeypatch.setattr(manager, "run_office_cleanup_hook", lambda repo_dir, logger: calls.append(repo_dir))
    monkeypatch.setattr(manager, "run_command", lambda *args, **kwargs: None)
    monkeypatch.setattr(manager.subprocess, "Popen", lambda *args, **kwargs: Process())

    repo = tmp_path / "repo"
    repo.mkdir()
    process = manager.launch_ui_process(repo, Logger())

    assert isinstance(process, Process)
    assert calls == [repo]


def load_self_update_manager():
    manager_path = PROJECT_ROOT / "docker" / "run" / "fs" / "exe" / "self_update_manager.py"
    spec = importlib.util.spec_from_file_location("test_self_update_manager_office", manager_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
