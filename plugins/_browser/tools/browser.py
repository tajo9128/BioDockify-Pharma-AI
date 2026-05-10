from __future__ import annotations

import json
from typing import Any

from helpers.tool import Response, Tool
from plugins._browser.helpers.runtime import get_runtime


class Browser(Tool):
    async def execute(
        self,
        action: str = "",
        browser_id: int | str | None = None,
        url: str = "",
        ref: int | str | None = None,
        target_ref: int | str | None = None,
        text: str = "",
        selector: str = "",
        selectors: list[str] | None = None,
        script: str = "",
        modifiers: list[str] | str | None = None,
        keys: list[str] | None = None,
        key: str = "",
        include_content: bool = False,
        focus_popup: bool | None = None,
        event_type: str = "",
        x: float = 0.0,
        y: float = 0.0,
        to_x: float = 0.0,
        to_y: float = 0.0,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        target_offset_x: float = 0.0,
        target_offset_y: float = 0.0,
        delta_x: float = 0.0,
        delta_y: float = 0.0,
        button: str = "left",
        quality: int = 80,
        full_page: bool = False,
        path: str = "",
        paths: list[str] | None = None,
        value: str = "",
        values: list[str] | None = None,
        checked: bool | None = None,
        width: int = 0,
        height: int = 0,
        calls: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Response:
        method_action = str(self.method or "").strip().lower().replace("-", "_")
        requested_action = str(action or "").strip().lower().replace("-", "_")
        clipboard_action = ""
        if method_action == "clipboard" and requested_action in {"copy", "cut", "paste"}:
            clipboard_action = requested_action
            action = "clipboard"
        else:
            action = str(action or self.method or "state").strip().lower().replace("-", "_")
        runtime = await get_runtime(self.agent.context.id)

        if isinstance(modifiers, str):
            modifiers = [modifiers] if modifiers else None
        elif isinstance(modifiers, list) and not modifiers:
            modifiers = None

        try:
            if action == "open":
                result = await runtime.call("open", url or "")
            elif action == "screenshot":
                result = await runtime.call(
                    "screenshot_file",
                    browser_id,
                    quality=quality,
                    full_page=full_page,
                    path=path,
                )
            elif action == "list":
                result = await runtime.call("list", include_content=bool(include_content))
            elif action == "state":
                result = await runtime.call("state", browser_id)
            elif action in {"set_active", "setactive", "activate", "focus"}:
                result = await runtime.call("set_active", browser_id)
            elif action == "navigate":
                result = await runtime.call("navigate", browser_id, url)
            elif action == "back":
                result = await runtime.call("back", browser_id)
            elif action == "forward":
                result = await runtime.call("forward", browser_id)
            elif action == "reload":
                result = await runtime.call("reload", browser_id)
            elif action == "content":
                payload = self._selector_payload(selector, selectors)
                result = await runtime.call("content", browser_id, payload)
            elif action == "detail":
                result = await runtime.call("detail", browser_id, self._require_ref(ref))
            elif action == "click":
                if modifiers:
                    result = await runtime.call(
                        "click", browser_id, self._require_ref(ref),
                        modifiers=modifiers, focus_popup=focus_popup,
                    )
                else:
                    result = await runtime.call("click", browser_id, self._require_ref(ref))
            elif action == "type":
                result = await runtime.call("type", browser_id, self._require_ref(ref), text)
            elif action == "submit":
                result = await runtime.call("submit", browser_id, self._require_ref(ref))
            elif action in {"type_submit", "typesubmit"}:
                result = await runtime.call(
                    "type_submit",
                    browser_id,
                    self._require_ref(ref),
                    text,
                )
            elif action == "scroll":
                result = await runtime.call("scroll", browser_id, self._require_ref(ref))
            elif action == "evaluate":
                result = await runtime.call("evaluate", browser_id, script)
            elif action in {"key_chord", "keychord"}:
                if not keys:
                    raise ValueError("key_chord requires non-empty 'keys' list")
                result = await runtime.call("key_chord", browser_id, list(keys))
            elif action == "hover":
                result = await runtime.call(
                    "hover",
                    browser_id,
                    ref=ref,
                    x=x,
                    y=y,
                    offset_x=offset_x,
                    offset_y=offset_y,
                )
            elif action == "double_click":
                result = await runtime.call(
                    "double_click",
                    browser_id,
                    ref=ref,
                    x=x,
                    y=y,
                    button=button or "left",
                    modifiers=modifiers,
                    offset_x=offset_x,
                    offset_y=offset_y,
                )
            elif action == "right_click":
                result = await runtime.call(
                    "right_click",
                    browser_id,
                    ref=ref,
                    x=x,
                    y=y,
                    modifiers=modifiers,
                    offset_x=offset_x,
                    offset_y=offset_y,
                )
            elif action == "drag":
                result = await runtime.call(
                    "drag",
                    browser_id,
                    ref=ref,
                    target_ref=target_ref,
                    x=x,
                    y=y,
                    to_x=to_x,
                    to_y=to_y,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    target_offset_x=target_offset_x,
                    target_offset_y=target_offset_y,
                )
            elif action == "wheel":
                result = await runtime.call(
                    "wheel",
                    browser_id,
                    x,
                    y,
                    delta_x,
                    delta_y,
                )
            elif action == "keyboard":
                result = await runtime.call(
                    "keyboard",
                    browser_id,
                    key=key,
                    text=text,
                )
            elif action == "clipboard":
                normalized_clipboard_action = clipboard_action or str(
                    kwargs.get("clipboard_action")
                    or kwargs.get("operation")
                    or event_type
                    or ""
                ).strip().lower()
                result = await runtime.call(
                    "clipboard",
                    browser_id,
                    action=normalized_clipboard_action,
                    text=text,
                )
            elif action in {"copy", "cut", "paste"}:
                result = await runtime.call(
                    "clipboard",
                    browser_id,
                    action=action,
                    text=text,
                )
            elif action == "set_viewport":
                result = await runtime.call("set_viewport", browser_id, width, height)
            elif action == "select_option":
                result = await runtime.call(
                    "select_option",
                    browser_id,
                    self._require_ref(ref),
                    value=value,
                    values=values,
                )
            elif action == "set_checked":
                result = await runtime.call(
                    "set_checked",
                    browser_id,
                    self._require_ref(ref),
                    checked=True if checked is None else bool(checked),
                )
            elif action == "upload_file":
                result = await runtime.call(
                    "upload_file",
                    browser_id,
                    self._require_ref(ref),
                    path=path,
                    paths=paths,
                )
            elif action == "mouse":
                result = await runtime.call(
                    "mouse", browser_id, event_type or "click", x, y,
                    button=button or "left", modifiers=modifiers,
                )
            elif action == "multi":
                if not calls:
                    raise ValueError("multi requires non-empty 'calls' list")
                result = await runtime.call("multi", list(calls))
            elif action == "close":
                result = await runtime.call("close_browser", browser_id)
            elif action == "close_all":
                result = await runtime.call("close_all_browsers")
            else:
                return Response(
                    message=f"Unknown browser action: {action}",
                    break_loop=False,
                )
        except Exception as exc:
            return Response(message=f"Browser {action} failed: {exc}", break_loop=False)

        return Response(message=self._format_result(action, result), break_loop=False)

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://captive_portal {self.agent.agent_name}: Using browser",
            content="",
            kvps=self.args,
            _tool_name=self.name,
        )

    @staticmethod
    def _require_ref(ref: int | str | None) -> int | str:
        if ref is None or str(ref).strip() == "":
            raise ValueError("ref is required for this browser action")
        return ref

    @staticmethod
    def _selector_payload(selector: str = "", selectors: list[str] | None = None) -> dict | None:
        if selectors:
            return {"selectors": selectors}
        if selector:
            return {"selector": selector}
        return None

    @staticmethod
    def _format_result(action: str, result: Any) -> str:
        if action == "content" and isinstance(result, dict):
            if set(result.keys()) == {"document"}:
                return str(result.get("document") or "")
            return json.dumps(result, indent=2, ensure_ascii=False)

        return json.dumps(result, indent=2, ensure_ascii=False, default=str)
