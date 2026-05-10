from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_document_canvas_uses_markdown_editor_and_official_libreoffice_desktop_frame():
    panel = (PROJECT_ROOT / "plugins" / "_office" / "webui" / "office-panel.html").read_text(
        encoding="utf-8",
    )
    store = (PROJECT_ROOT / "plugins" / "_office" / "webui" / "office-store.js").read_text(
        encoding="utf-8",
    )
    canvas_panel = (
        PROJECT_ROOT / "plugins" / "_office" / "extensions" / "webui" / "right-canvas-panels" / "office-panel.html"
    ).read_text(encoding="utf-8")

    assert "office-source-editor" in panel
    assert "data-office-source" in panel
    assert "office-rich-editor" not in panel
    assert "office-docx-pages" not in panel
    assert "office-desktop-frame" in panel
    assert "data-office-desktop-host" in panel
    assert 'x-init="$nextTick(() => $store.office.mountDesktopFrameHost($el))"' in panel
    assert 'x-effect="$store.office.attachDesktopFrame($el)"' not in panel
    assert "data-office-desktop-frame" in store
    assert 'title="LibreOffice desktop"' not in panel
    assert 'frame.setAttribute("aria-label", "Desktop")' in store
    assert "office-command-button" in panel
    assert "office-button-label" in panel
    assert "grid-template-columns: minmax(0, 1fr) auto auto auto" in panel
    assert "flex-wrap: nowrap" in panel
    assert ".modal-inner.office-modal .modal-scroll" in panel
    assert "office-modal-resizer" in panel
    assert "resize: both" not in panel
    assert 'frame.setAttribute("tabindex", "0")' in store
    assert "format_underlined" not in panel
    assert "format_align_center" not in panel
    assert "is-native-tile" not in panel
    assert "hasOfficialOffice()" in panel
    assert 'title="Rename"' in panel
    assert "@click=\"$store.office.renameActiveFile()\"" in panel
    assert "office_save" in store
    assert "desktop_save" in store
    assert "openRenameModal" in store
    assert 'callOffice("renamed"' in store
    assert "performRename" in store
    assert "payload.text" in store
    assert "handleActiveFileRenamed" in store
    assert "--office-zoom" not in panel
    assert "zoom: 1" not in store
    assert 'callOffice("desktop")' in store
    assert "ensureDesktopSession" in store
    assert 'await this.onOpen({ source: "modal" });' in store
    assert "setDesktopHostVisible" in store
    assert "isDesktopHostVisible" in store
    assert "clearDesktopViewportSyncTimers" in store
    assert "setDesktopHostVisible" in canvas_panel
    assert "queueMicrotask" in canvas_panel
    assert "isSurfaceRendered('office')" in canvas_panel
    assert "isSurfaceVisible('office')" in canvas_panel
    assert "canvas.isSurfaceMounted?.(\"office\")" in store
    assert "Starting Agent Zero Desktop environment" in store
    assert "handleOfficialOfficeClosed" in store
    assert "ResizeObserver" in store
    assert "_desktopResizeSuspended" in store
    assert "_desktopResizePending" in store
    assert "_desktopResizePendingKey" in store
    assert "_desktopViewportSyncTimers" in store
    assert "shouldDeferDesktopResize" in store
    assert "right-canvas-resize-start" in store
    assert "right-canvas-resize-end" in store
    assert "isDesktopSession" in store
    assert "desktopFrame" in store
    assert "attachDesktopFrame" in store
    assert "mountDesktopFrameHost" in store
    assert "desktopFrameSrcMatches" in store
    assert "moveDesktopFrameToKeepalive" in store
    assert "destroyDesktopFrame" in store
    assert "office-desktop-keepalive" in store
    assert "DESKTOP_SHUTDOWN_STORAGE_KEY" in store
    assert 'callOffice("desktop_shutdown"' in store
    assert "intentional_shutdown" in store
    assert "restartDesktopSession" in store
    assert "shouldShowDesktopEmptyState" in store
    assert "Restart Desktop" in panel
    assert "office-desktop-empty" in panel
    assert "unloadDesktopFrames" in store
    assert "restoreDesktopFrames" in store
    assert "officeDesktopUnloaded" not in store
    assert "primeXpraDesktopFrame" in store
    assert "normalizeXpraDesktopWindow" in store
    assert "installXpraDesktopWheelBridge" in store
    assert "installXpraDesktopAgentBridge" in store
    assert "agentZeroDesktop" in store
    assert 'callOffice("desktop_state"' in store
    assert "desktopToClient" in store
    assert "clientToDesktop" in store
    assert "requestRefresh" in store
    assert "_desktopBridgeReady" in store
    assert "_desktopKeyboardCaptureState" in store
    assert "installXpraDesktopKeyboardBridge" in store
    assert "focusDesktopFrame" in store
    assert "_desktopFocusInProgress" in store
    assert "if (this._desktopFocusInProgress) return" in store
    assert "_desktopKeyboardActive" in store
    assert "isEditableInputTarget" in store
    assert "reloadDesktopFrame" in store
    assert 'result?.reload' in store
    assert "a0_reload" in store
    assert "const DESKTOP_RESIZE_DELAY_MS = 80" in store
    assert "requestServerResize: false" in store
    assert "requestRefresh: false" in store
    assert "_desktopResizeTarget" in store
    assert "requestDesktopViewportSync" in store
    assert "syncDesktopViewport" in store
    assert "options.serverResize !== false" in store
    assert "serverResize: true" in store
    assert "server_is_desktop = true" in store
    assert "server_resize_exact = true" in store
    assert "_set_decorated?.(false)" in store
    assert "topoffset = 0" in store
    assert ".undecorated" in store
    assert "a0-xpra-desktop-frame-css" in store
    assert "installXpraDesktopFramePatches" in store
    assert "installXpraDesktopClientPatches" in store
    assert "patchedNoWindowList" in store
    assert "patchedAddWindowListItem" in store
    assert "patchedScreenResized" in store
    assert "__a0AllowScreenResize" in store
    assert "_desktopHeartbeatTimer" in store
    assert "office-modal-focus-button" in store
    assert "focusButton.title" not in store
    assert "officialOfficeUrl" in store
    assert 'parsed.searchParams.set("offscreen", secureContext ? "true" : "false")' in store
    assert 'parsed.searchParams.set("clipboard_poll", secureContext ? "true" : "false")' in store
    assert "hasOfficialOffice" in store
    assert "isOfficeSocketData" in store
    assert "office_command" not in store
    assert "office_key" not in store
    assert "office_mouse" not in store
    assert ".uno:Bold" not in store
    assert "nativeTilesToHtml" not in store
    assert "editorContainsFocus" in store
    assert "_focusAttempts" in store
    assert "_nativeEventQueue" not in store
    assert "await this.awaitNativeEvents()" not in store
    assert "<p><br></p>" not in store
    assert "setupTitle()" not in panel
    assert "Setup in progress" not in store
    assert "office-log" not in panel
    assert "New Writer document" in panel
    assert "DOCX</span>" not in panel
    assert "$store.office.create('document', 'odt')" in panel
    assert "$store.office.create('spreadsheet', 'ods')" in panel
    assert "$store.office.create('presentation', 'odp')" in panel


def test_desktop_xpra_canvas_scroll_is_forwarded_to_the_remote_session():
    store = (PROJECT_ROOT / "plugins" / "_office" / "webui" / "office-store.js").read_text(
        encoding="utf-8",
    )

    assert "canvas.addEventListener(\"wheel\"" in store
    assert "mouse_scroll_cb(normalizedEvent, xpraWindow)" in store
    assert "stopImmediatePropagation" in store
    assert "{ passive: false, capture: true }" in store
    assert "xpraDesktopWheelEvent" in store
    assert "deltaMode: { value: 0 }" in store
    assert "wheelDeltaY" in store
    assert "getModifierState: { value: getModifierState }" in store


def test_office_surface_filters_tabs_to_desktop_and_markdown_without_dashboard():
    panel = (PROJECT_ROOT / "plugins" / "_office" / "webui" / "office-panel.html").read_text(
        encoding="utf-8",
    )
    store = (PROJECT_ROOT / "plugins" / "_office" / "webui" / "office-store.js").read_text(
        encoding="utf-8",
    )

    assert "office-card-grid" not in panel
    assert "office-document-card" not in panel
    assert "visibleTabs()" in panel
    assert "openCards()" not in panel
    assert "recentCards()" not in panel
    assert "office-editor-head" not in panel
    assert "office-recent-row" not in panel
    assert "open_documents" not in store
    assert "installDesktopDocumentSession" in store
    assert "isDesktopOfficeDocument" in store
    assert "isVisibleOfficeTab" in store
    assert "return this.tabs.filter((tab) => this.isVisibleOfficeTab(tab));" in store

    file_browser_store = (
        PROJECT_ROOT / "webui" / "components" / "modals" / "file-browser" / "file-browser-store.js"
    ).read_text(encoding="utf-8")

    assert "renameAfterConfirm" in file_browser_store
    assert "renamePerformAction" in file_browser_store
    assert "renameValidateName" in file_browser_store
    assert "options.onRenamed" in file_browser_store
    assert "options.performRename" in file_browser_store
    assert "options.validateName" in file_browser_store


def test_right_canvas_surface_is_branded_as_desktop():
    surface = (
        PROJECT_ROOT
        / "plugins"
        / "_office"
        / "extensions"
        / "webui"
        / "right_canvas_register_surfaces"
        / "register-office.js"
    ).read_text(encoding="utf-8")
    handler = (
        PROJECT_ROOT
        / "plugins"
        / "_office"
        / "extensions"
        / "webui"
        / "get_tool_message_handler"
        / "document-artifact-handler.js"
    ).read_text(encoding="utf-8")
    document_actions = (
        PROJECT_ROOT
        / "plugins"
        / "_office"
        / "extensions"
        / "webui"
        / "lib"
        / "document-actions.js"
    ).read_text(encoding="utf-8")

    assert 'title: "Desktop"' in surface
    assert 'icon: "desktop_windows"' in surface
    assert "buildDocumentFileActionButtons(document)" in handler
    assert "Open in canvas" in document_actions
    assert "downloadDocument" in document_actions
    assert "/api/download_work_dir_file?path=" in document_actions
    assert "source: \"message-action\"" in document_actions


def test_official_libreoffice_desktop_route_and_packages_are_declared():
    routes = (PROJECT_ROOT / "helpers" / "virtual_desktop_routes.py").read_text(encoding="utf-8")
    primitive = (PROJECT_ROOT / "helpers" / "virtual_desktop.py").read_text(encoding="utf-8")
    desktop = (
        PROJECT_ROOT / "plugins" / "_office" / "helpers" / "libreoffice_desktop.py"
    ).read_text(encoding="utf-8")
    install = (PROJECT_ROOT / "docker" / "run" / "fs" / "ins" / "install_additional.sh").read_text(
        encoding="utf-8",
    )
    linux_desktop_skill = (
        PROJECT_ROOT / "plugins" / "_office" / "skills" / "linux-desktop" / "SKILL.md"
    ).read_text(encoding="utf-8")
    linux_desktopctl = (
        PROJECT_ROOT / "plugins" / "_office" / "skills" / "linux-desktop" / "scripts" / "desktopctl.sh"
    ).read_text(encoding="utf-8")
    desktop_state_helper = (
        PROJECT_ROOT / "plugins" / "_office" / "helpers" / "desktop_state.py"
    ).read_text(encoding="utf-8")
    hooks_py = (PROJECT_ROOT / "plugins" / "_office" / "hooks.py").read_text(encoding="utf-8")
    linux_calc_helper = (
        PROJECT_ROOT / "plugins" / "_office" / "skills" / "linux-desktop" / "scripts" / "calc_set_cell.py"
    ).read_text(encoding="utf-8")

    assert 'Mount("/desktop"' in routes
    assert 'Mount("/libreoffice"' not in routes
    assert "http.client.HTTPConnection" in routes
    assert "WSConnection" in routes
    assert "/session/" in routes
    assert "resize_session" in routes
    assert "resize_display" in primitive
    assert "DEFAULT_HEIGHT = 900" in primitive
    assert "MAX_WIDTH = 1920" in primitive
    assert "MAX_HEIGHT = 1080" in primitive
    assert "xrandr" in primitive
    assert "xpra-x11" in primitive
    assert "xpramenu" in primitive
    assert "floating_menu" in primitive
    assert '"file_transfer": "true"' in primitive
    assert '"sound": "false"' in primitive
    assert '"encoding": "jpeg"' in primitive
    assert '"quality": "85"' in primitive
    assert '"speed": "80"' in primitive
    assert '"printing": "true"' in primitive
    assert '"offscreen": "true"' in primitive
    assert "xpra" in desktop
    assert "xpra-html5" in desktop
    assert "Xvfb" in desktop
    assert "xfce4-session" in desktop
    assert "DISPLAY_START_TIMEOUT_SECONDS" in desktop
    assert '"shadow"' in desktop
    assert "--resize-display=yes" in desktop
    assert "--tray=no" in desktop
    assert "--system-tray=no" in desktop
    assert "--file-transfer=yes" in desktop
    assert "--open-files=no" in desktop
    assert "--open-url=no" in desktop
    assert "--printing=yes" in desktop
    assert "--cursors=no" not in desktop
    assert "--audio=no" in desktop
    assert "--speaker=off" in desktop
    assert "--microphone=off" in desktop
    assert "--encoding=jpeg" in desktop
    assert "--quality=85" in desktop
    assert "--speed=80" in desktop
    assert "_restart_xpra_shadow(session)" not in desktop
    assert 'result["reload"] = True' not in desktop
    assert "MAX_SCREEN_WIDTH}x{MAX_SCREEN_HEIGHT}x24" in desktop
    assert '"-ac"' in desktop
    assert "SYSTEM_TITLE = \"Desktop\"" in desktop
    assert "title=\"Desktop\"" in desktop
    assert "--log-file=xpra.log" in desktop
    assert "virtual_desktop.session_url" in desktop
    assert "xsetroot" in desktop
    assert "BLOCKING_DIALOG_TITLES" in desktop
    assert "xfce4-terminal" in desktop
    assert "thunar" in desktop
    assert "Browser.desktop" in desktop
    assert "Files.desktop" in desktop
    assert "org.xfce.terminal" in desktop
    assert "org.xfce.settings.manager" in desktop
    assert "firefox-esr" not in desktop
    assert "xfce4-settings-manager" in desktop
    assert "metadata::xfce-exe-checksum" in desktop
    assert "DESKTOP_FOLDER_LINKS" in desktop
    assert "HIDDEN_XPRA_DESKTOP_ENTRIES" in desktop
    assert "HIDDEN_XFCE_MENU_ENTRIES" in desktop
    assert "SHUTDOWN_HANDLER_DESKTOP_ID" in desktop
    assert "SHUTDOWN_PANEL_LAUNCHER_ID" in desktop
    assert "SHUTDOWN_CONFIRM_SECONDS" in desktop
    assert "Shutdown Desktop" in desktop
    assert "shutdown-request.json" in desktop
    assert "shutdown-request.arm.json" in desktop
    assert "shutdown_system_desktop" in desktop
    assert "claim_shutdown_request" in desktop
    assert "last-show-hidden" in desktop
    assert "exo-mail-reader.desktop" in desktop
    assert "exo-web-browser.desktop" in desktop
    assert "xfce4-mail-reader.desktop" in desktop
    assert "xfce4-web-browser.desktop" in desktop
    assert "xfce4-session-logout.desktop" in desktop
    assert "agent-zero-shutdown.desktop" in desktop
    assert "libreoffice-gtk3" in install
    assert "libreofficekit" not in install
    assert "gir1.2-lokdocview" not in install
    assert "python3-gi" not in install
    assert "xpra" in install
    assert "xpra-x11" in install
    assert "xpra-html5" in install
    assert "xfce4-session" in install
    assert "thunar" in install
    assert "libglib2.0-bin" in install
    assert "xfce4-terminal" in install
    assert "firefox-esr" not in install
    assert "pulseaudio" not in install
    assert "x11-xserver-utils" in install
    assert "xauth" in install
    assert "Linux Desktop Interface" in linux_desktop_skill
    assert "Use the external Agent Zero Browser" in linux_desktop_skill
    assert "/a0/usr/workdir" in linux_desktop_skill
    assert "/a0/usr/projects" in linux_desktop_skill
    assert "desktopctl.sh" in linux_desktop_skill
    assert "/a0/plugins/_office/skills/linux-desktop/scripts/desktopctl.sh" in linux_desktop_skill
    assert "calc-set-cell" in linux_desktop_skill
    assert "Clicks are explicitly last resort" in linux_desktop_skill or "clicks are explicitly last resort" in linux_desktop_skill
    assert "fresh Desktop observation" in linux_desktop_skill
    assert "observe --json --screenshot" in linux_desktop_skill
    assert "Terminal And CLI Agent Verification" in linux_desktop_skill
    assert "Do not report from an earlier screenshot path" in linux_desktop_skill
    assert "screenshot path returned by that final observation" in linux_desktop_skill
    assert "Never paste natural-language text into that shell prompt" in linux_desktop_skill
    assert "command not found" in linux_desktop_skill
    assert "TARGET_CLI=\"example-cli-agent\"" in linux_desktop_skill
    assert "FALLBACK_CMD" in linux_desktop_skill
    assert "@openai/codex" not in linux_desktop_skill
    assert "xdotool" in linux_desktopctl
    assert "agent-zero-desktop" in linux_desktopctl
    assert "launch_app" in linux_desktopctl
    assert "paste_key_for_active_window" in linux_desktopctl
    assert "active_window_is_terminal" in linux_desktopctl
    assert "WM_CLASS" in linux_desktopctl
    for command in (
        "state)",
        "observe)",
        "screenshot)",
        "active-window)",
        "geometry)",
        "wait-window)",
        "scroll)",
        "drag)",
        "right-click)",
        "paste-text)",
        "sequence)",
    ):
        assert command in linux_desktopctl
    assert "calc_set_cell.py" in linux_desktopctl
    assert "collect_state" in desktop_state_helper
    assert "compact_prompt_context" in desktop_state_helper
    assert "fresh final" in desktop_state_helper
    assert "xwd" in desktop_state_helper
    assert "PIL" in desktop_state_helper
    assert '"x11-utils"' in hooks_py
    assert '"x11-apps"' in hooks_py
    assert '"xclip"' in hooks_py
    assert '"python3-pil"' in hooks_py
    assert "wait_for_document" in linux_calc_helper
    assert "document.store()" in linux_calc_helper
    assert "read_xlsx_cell" in linux_calc_helper
    assert "DisposedException" in linux_calc_helper


def test_right_canvas_requires_explicit_open_and_is_absent_on_mobile():
    canvas_store = (
        PROJECT_ROOT / "webui" / "components" / "canvas" / "right-canvas-store.js"
    ).read_text(encoding="utf-8")
    canvas_html = (
        PROJECT_ROOT / "webui" / "components" / "canvas" / "right-canvas.html"
    ).read_text(encoding="utf-8")
    canvas_css = (
        PROJECT_ROOT / "webui" / "components" / "canvas" / "right-canvas.css"
    ).read_text(encoding="utf-8")
    handler = (
        PROJECT_ROOT
        / "plugins"
        / "_office"
        / "extensions"
        / "webui"
        / "get_tool_message_handler"
        / "document-artifact-handler.js"
    ).read_text(encoding="utf-8")
    after_loop = (
        PROJECT_ROOT
        / "plugins"
        / "_office"
        / "extensions"
        / "webui"
        / "set_messages_after_loop"
        / "auto-open-document-results.js"
    ).read_text(encoding="utf-8")

    init_registration = canvas_store.index('await callJsExtensions("right_canvas_register_surfaces", this);')
    init_ensure = canvas_store.index("this.ensureActiveSurface();", init_registration)
    register_surface = canvas_store.index("registerSurface(surface)")
    register_guard = canvas_store.index("if (!this._registering)", register_surface)
    guarded_ensure = canvas_store.index("this.ensureActiveSurface();", register_guard)
    open_surface = canvas_store.index("async open", register_surface)

    assert init_registration < init_ensure
    assert register_surface < register_guard < guarded_ensure < open_surface
    assert "right-canvas-resize-start" in canvas_store
    assert "right-canvas-resize-end" in canvas_store
    assert "dispatchResizeEvent" in canvas_store
    assert "this.isOpen = false;" in canvas_store
    assert "wasMobileMode && this.width < MIN_WIDTH" in canvas_store
    assert "const MIN_WIDTH = 0" in canvas_store
    assert "const MAX_WIDTH" not in canvas_store
    assert "0.58" not in canvas_store
    assert "min(900px, 58vw)" not in canvas_css
    assert "max-width: none" in canvas_css
    assert "if (this.isMobileMode && !surface.actionOnly)" in canvas_store
    assert "if (this.isMobileMode)" in canvas_store
    assert "shouldRender()" in canvas_store
    assert "$store.rightCanvas.shouldRender()" in canvas_html
    assert 'title="Open as window"' in canvas_html
    assert 'title="Close canvas"' in canvas_html
    assert 'aria-label="Close canvas"' in canvas_html
    assert "@click=\"$store.rightCanvas.close()\"" in canvas_html
    assert canvas_html.index('title="Open as window"') < canvas_html.index('title="Close canvas"')
    assert "body.right-canvas-mobile-mode .right-canvas" in canvas_css
    assert "display: none !important" in canvas_css
    assert "autoOpenOfficeCanvas" not in handler
    assert "isOfficeCanvasAlreadyOpen" in after_loop
    assert 'canvas?.isOpen && canvas?.activeSurfaceId === "office"' in after_loop
    assert "office.openSession?.(" in after_loop
    assert 'source: "tool-result-sync"' in after_loop
    assert 'rightCanvas.open' not in after_loop


def test_office_skills_preserve_markdown_first_and_opt_in_desktop_policy():
    office_skill = (
        PROJECT_ROOT / "plugins" / "_office" / "skills" / "office-artifacts" / "SKILL.md"
    ).read_text(encoding="utf-8")
    desktop_skill = (
        PROJECT_ROOT / "plugins" / "_office" / "skills" / "linux-desktop" / "SKILL.md"
    ).read_text(encoding="utf-8")
    markdown_skill = (
        PROJECT_ROOT / "plugins" / "_office" / "skills" / "markdown-documents" / "SKILL.md"
    ).read_text(encoding="utf-8")
    word_skill = (
        PROJECT_ROOT / "plugins" / "_office" / "skills" / "word-documents" / "SKILL.md"
    ).read_text(encoding="utf-8")
    excel_skill = (
        PROJECT_ROOT / "plugins" / "_office" / "skills" / "excel-workbooks" / "SKILL.md"
    ).read_text(encoding="utf-8")
    presentation_skill = (
        PROJECT_ROOT / "plugins" / "_office" / "skills" / "presentation-decks" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "ODF is first-class" in office_skill
    assert "DOCX, XLSX, or PPTX only" in office_skill
    assert "custom document canvas" in office_skill
    assert "must not open the canvas automatically" in office_skill
    assert "Download and Open in canvas actions" in office_skill
    assert "method: \"create\"" in office_skill
    assert "The Desktop is opt-in" in desktop_skill
    assert "coordinate clicks only as a last resort" in desktop_skill
    assert "After any GUI action, verify" in desktop_skill
    assert "custom Markdown editor" in desktop_skill
    assert "Never open the Desktop/canvas automatically" in desktop_skill
    assert "persistent Desktop runtime during initial startup" in desktop_skill
    assert '"format": "md"' in markdown_skill
    assert "never open the canvas automatically" in markdown_skill
    assert '"format": "odt"' in word_skill
    assert "DOCX only" in word_skill
    assert "must not open the canvas automatically" in word_skill
    assert '"format": "ods"' in excel_skill
    assert "For a blank workbook request" in excel_skill
    assert "must not open the canvas automatically" in excel_skill
    assert '"format": "odp"' in presentation_skill
    assert "must not open the canvas automatically" in presentation_skill


def test_office_extra_prompt_includes_existing_desktop_state_without_opening_canvas():
    canvas_context = (
        PROJECT_ROOT / "plugins" / "_office" / "helpers" / "canvas_context.py"
    ).read_text(encoding="utf-8")
    prompt = (
        PROJECT_ROOT / "plugins" / "_office" / "prompts" / "agent.extras.office_canvas.md"
    ).read_text(encoding="utf-8")

    assert "build_desktop_context" in canvas_context
    assert "session_manifest_exists" in canvas_context
    assert "collect_state(include_screenshot=False)" in canvas_context
    assert "compact_prompt_context" in canvas_context
    assert "ensure_system_desktop" not in canvas_context
    assert "[DOCUMENT CANVAS]" in prompt
