from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from plugins._office.helpers import document_store


@dataclass
class MarkdownSession:
    session_id: str
    file_id: str
    sid: str
    context_id: str
    extension: str
    path: str
    title: str
    text: str = ""
    dirty: bool = False
    active: bool = False
    opened_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)


class MarkdownSessionManager:
    """Owns native Editor sessions for Markdown documents."""

    def __init__(self) -> None:
        self._sessions: dict[str, MarkdownSession] = {}
        self._active_by_context: dict[str, str] = {}

    def open(self, doc: dict[str, Any], sid: str = "", context_id: str = "", refresh: bool = False) -> dict[str, Any]:
        ext = str(doc["extension"]).lower()
        if ext != "md":
            raise ValueError(f"Editor is only available for Markdown. Open .{ext} files in the Desktop.")

        normalized_context = str(context_id or "")
        if refresh:
            try:
                doc = document_store.register_document(doc["path"], context_id=normalized_context)
            except Exception:
                pass

        for session in self._sessions.values():
            if session.file_id != doc["file_id"] or session.context_id != normalized_context:
                continue
            if sid:
                session.sid = sid
            if refresh and not session.dirty:
                session.text = document_store.read_text_for_editor(doc)
                session.dirty = False
            session.path = doc["path"]
            session.title = doc["basename"]
            session.updated_at = time.time()
            self.activate(session.session_id)
            return self._payload(session, doc)

        session = MarkdownSession(
            session_id=uuid.uuid4().hex,
            file_id=doc["file_id"],
            sid=sid,
            context_id=normalized_context,
            extension=ext,
            path=doc["path"],
            title=doc["basename"],
            text=document_store.read_text_for_editor(doc),
        )
        self._sessions[session.session_id] = session
        self.activate(session.session_id)
        return self._payload(session, doc)

    def input(self, session_id: str, text: str | None = None, patch: dict[str, Any] | None = None) -> dict[str, Any]:
        session = self._require(session_id)
        if text is not None:
            session.text = str(text)
        elif patch:
            session.text = _apply_text_patch(session.text, patch)
        session.dirty = True
        session.updated_at = time.time()
        self.activate(session.session_id)
        return {"ok": True, "session_id": session.session_id}

    def save(self, session_id: str, text: str | None = None) -> dict[str, Any]:
        session = self._require(session_id)
        if text is not None:
            session.text = str(text)

        updated = document_store.write_markdown(session.file_id, session.text)
        session.updated_at = time.time()
        session.dirty = False
        session.path = updated["path"]
        session.title = updated["basename"]
        self._refresh_file_sessions(updated, text=session.text, dirty=False)
        return {
            "ok": True,
            "document": _public_doc(updated),
            "version": document_store.item_version(updated),
        }

    def activate(self, session_id: str) -> dict[str, Any]:
        session = self._require(session_id)
        now = time.time()
        previous_id = self._active_by_context.get(session.context_id)
        if previous_id and previous_id in self._sessions:
            self._sessions[previous_id].active = False
        session.active = True
        session.last_active_at = now
        session.updated_at = now
        self._active_by_context[session.context_id] = session.session_id
        return {"ok": True, "session_id": session.session_id}

    def renamed(self, file_id: str, doc: dict[str, Any], text: str | None = None) -> dict[str, Any]:
        updated = self._refresh_file_sessions(doc, text=text, dirty=False)
        return {"ok": True, "updated": updated, "file_id": file_id}

    def refresh_document(self, file_id: str) -> dict[str, Any]:
        normalized = str(file_id or "").strip()
        if not normalized:
            return {"ok": True, "refreshed": 0, "sessions": []}
        try:
            doc = document_store.get_document(normalized)
        except Exception:
            return {"ok": False, "refreshed": 0, "sessions": []}
        if str(doc.get("extension") or "").lower() != "md":
            return {"ok": True, "refreshed": 0, "sessions": []}

        refreshed = self._refresh_file_sessions(
            doc,
            text=document_store.read_text_for_editor(doc),
            dirty=False,
        )
        return {"ok": True, "refreshed": len(refreshed), "sessions": refreshed}

    def list_open(self, context_id: str = "", limit: int = 20) -> list[dict[str, Any]]:
        context_id = str(context_id or "")
        sessions = [session for session in self._sessions.values() if session.context_id == context_id]
        sessions.sort(key=lambda item: (not item.active, -item.last_active_at, -item.updated_at))

        grouped: dict[str, MarkdownSession] = {}
        counts: dict[str, int] = {}
        for session in sessions:
            key = session.file_id or session.path
            counts[key] = counts.get(key, 0) + 1
            current = grouped.get(key)
            if current is None or session.active or session.last_active_at > current.last_active_at:
                grouped[key] = session

        result = []
        for session in grouped.values():
            try:
                doc = document_store.get_document(session.file_id)
                version = document_store.item_version(doc)
                size = doc.get("size", 0)
                last_modified = doc.get("last_modified", "")
                path = document_store.display_path(doc.get("path", session.path))
                title = doc.get("basename") or session.title
            except Exception:
                version = ""
                size = 0
                last_modified = ""
                path = document_store.display_path(session.path)
                title = session.title
            result.append({
                "session_id": session.session_id,
                "file_id": session.file_id,
                "title": title,
                "extension": session.extension,
                "path": path,
                "version": version,
                "size": size,
                "last_modified": last_modified,
                "dirty": session.dirty,
                "active": session.active,
                "open_sessions": counts.get(session.file_id or session.path, 1),
                "last_active_at": session.last_active_at,
            })

        result.sort(key=lambda item: (not item["active"], -float(item["last_active_at"] or 0)))
        safe_limit = max(1, int(limit or 20))
        return result[:safe_limit]

    def close(self, session_id: str) -> dict[str, Any]:
        session = self._sessions.pop(str(session_id or ""), None)
        if not session:
            return {"ok": True, "closed": 0}
        if self._active_by_context.get(session.context_id) == session.session_id:
            replacement = sorted(
                [item for item in self._sessions.values() if item.context_id == session.context_id],
                key=lambda item: item.last_active_at,
                reverse=True,
            )
            if replacement:
                self.activate(replacement[0].session_id)
            else:
                self._active_by_context.pop(session.context_id, None)
        return {"ok": True, "closed": 1, "session_id": session_id}

    def close_sid(self, sid: str) -> int:
        doomed = [session_id for session_id, session in self._sessions.items() if session.sid == sid]
        for session_id in doomed:
            self.close(session_id)
        return len(doomed)

    def _refresh_file_sessions(self, doc: dict[str, Any], text: str | None = None, dirty: bool | None = None) -> list[str]:
        file_id = str(doc.get("file_id") or "").strip()
        refreshed: list[str] = []
        for session in self._sessions.values():
            if session.file_id != file_id:
                continue
            if text is not None:
                session.text = str(text)
            session.path = doc["path"]
            session.title = doc["basename"]
            if dirty is not None:
                session.dirty = dirty
            session.updated_at = time.time()
            refreshed.append(session.session_id)
        return refreshed

    def _payload(self, session: MarkdownSession, doc: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "session_id": session.session_id,
            "file_id": session.file_id,
            "title": session.title,
            "extension": session.extension,
            "path": session.path,
            "text": session.text,
            "dirty": session.dirty,
            "active": session.active,
            "context_id": session.context_id,
            "document": _public_doc(doc),
            "version": document_store.item_version(doc),
        }

    def _require(self, session_id: str) -> MarkdownSession:
        normalized = str(session_id or "").strip()
        session = self._sessions.get(normalized)
        if not session:
            raise FileNotFoundError(f"Editor session not found: {normalized}")
        return session


def get_manager() -> MarkdownSessionManager:
    global _manager
    try:
        return _manager
    except NameError:
        _manager = MarkdownSessionManager()
        return _manager


def _public_doc(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "file_id": doc["file_id"],
        "path": document_store.display_path(doc["path"]),
        "basename": doc["basename"],
        "title": doc["basename"],
        "extension": doc["extension"],
        "size": doc["size"],
        "version": document_store.item_version(doc),
        "last_modified": doc["last_modified"],
        "exists": Path(doc["path"]).exists(),
    }


def _apply_text_patch(text: str, patch: dict[str, Any]) -> str:
    if "content" in patch:
        return str(patch.get("content") or "")
    start = int(patch.get("start") or 0)
    end = int(patch.get("end") if patch.get("end") is not None else start)
    replacement = str(patch.get("text") or "")
    start = max(0, min(len(text), start))
    end = max(start, min(len(text), end))
    return text[:start] + replacement + text[end:]
