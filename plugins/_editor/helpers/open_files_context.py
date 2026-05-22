from __future__ import annotations

from typing import Any

from plugins._editor.helpers import markdown_sessions


def build_context(context_id: str = "", max_items: int = 20) -> str:
    files = markdown_sessions.get_manager().list_open(context_id=context_id, limit=max_items)
    if not files:
        return ""

    lines = [
        "These Markdown files are open in the Editor for the active Agent Zero context. Content is omitted; use `document_artifact` with action `read` before content-sensitive edits.",
    ]
    for item in files:
        lines.append(format_open_file_line(item))
    lines.append(
        "Use `document_artifact` with action `edit` and file_id or path for saved edits; Editor sessions refresh after saved tool results."
    )
    return "\n".join(lines)


def format_open_file_line(item: dict[str, Any]) -> str:
    active = "active, " if item.get("active") else ""
    dirty = "dirty, " if item.get("dirty") else "saved, "
    return (
        f"- {item.get('title', 'Untitled')} "
        f"(.{item.get('extension', 'md')}, {active}{dirty}"
        f"file_id={item.get('file_id', '')}, path={item.get('path', '')}, "
        f"version={item.get('version', '')}, size={item.get('size', 0)} bytes, "
        f"last_modified={item.get('last_modified', '')}, open_sessions={item.get('open_sessions', 1)})"
    )
