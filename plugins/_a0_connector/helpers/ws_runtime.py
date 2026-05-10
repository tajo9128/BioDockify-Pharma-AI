from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class PendingFileOperation:
    sid: str
    loop: asyncio.AbstractEventLoop
    future: asyncio.Future[dict[str, Any]]
    context_id: str | None = None


@dataclass
class PendingExecOperation:
    sid: str
    loop: asyncio.AbstractEventLoop
    future: asyncio.Future[dict[str, Any]]
    context_id: str | None = None


@dataclass
class PendingComputerUseOperation:
    sid: str
    loop: asyncio.AbstractEventLoop
    future: asyncio.Future[dict[str, Any]]
    context_id: str | None = None


@dataclass(frozen=True)
class RemoteTreeSnapshot:
    sid: str
    payload: dict[str, Any]
    updated_at: float


@dataclass(frozen=True)
class ComputerUseMetadata:
    supported: bool
    enabled: bool
    trust_mode: str
    artifact_root: str
    backend_id: str
    backend_family: str
    features: tuple[str, ...]
    support_reason: str
    updated_at: float


@dataclass(frozen=True)
class RemoteFileMetadata:
    enabled: bool
    write_enabled: bool
    mode: str
    updated_at: float


@dataclass(frozen=True)
class RemoteExecMetadata:
    enabled: bool
    updated_at: float


_context_subscriptions: dict[str, set[str]] = {}
_sid_contexts: dict[str, set[str]] = {}
_pending_file_ops: dict[str, PendingFileOperation] = {}
_pending_exec_ops: dict[str, PendingExecOperation] = {}
_pending_computer_use_ops: dict[str, PendingComputerUseOperation] = {}
_remote_tree_snapshots: dict[str, RemoteTreeSnapshot] = {}
_sid_computer_use_metadata: dict[str, ComputerUseMetadata] = {}
_sid_remote_file_metadata: dict[str, RemoteFileMetadata] = {}
_sid_remote_exec_metadata: dict[str, RemoteExecMetadata] = {}
_state_lock = threading.RLock()


def register_sid(sid: str) -> None:
    with _state_lock:
        _sid_contexts.setdefault(sid, set())


def unregister_sid(sid: str) -> set[str]:
    with _state_lock:
        contexts = _sid_contexts.pop(sid, set())
        _remote_tree_snapshots.pop(sid, None)
        _sid_computer_use_metadata.pop(sid, None)
        _sid_remote_file_metadata.pop(sid, None)
        _sid_remote_exec_metadata.pop(sid, None)
        for context_id in contexts:
            subscribers = _context_subscriptions.get(context_id)
            if not subscribers:
                continue
            subscribers.discard(sid)
            if not subscribers:
                _context_subscriptions.pop(context_id, None)
    return contexts


def subscribe_sid_to_context(sid: str, context_id: str) -> None:
    with _state_lock:
        _sid_contexts.setdefault(sid, set()).add(context_id)
        _context_subscriptions.setdefault(context_id, set()).add(sid)


def unsubscribe_sid_from_context(sid: str, context_id: str) -> None:
    with _state_lock:
        contexts = _sid_contexts.get(sid)
        if contexts is not None:
            contexts.discard(context_id)
            if not contexts:
                _sid_contexts.pop(sid, None)

        subscribers = _context_subscriptions.get(context_id)
        if subscribers is not None:
            subscribers.discard(sid)
            if not subscribers:
                _context_subscriptions.pop(context_id, None)


def subscribed_contexts_for_sid(sid: str) -> set[str]:
    with _state_lock:
        return set(_sid_contexts.get(sid, set()))


def subscribed_sids_for_context(context_id: str) -> set[str]:
    with _state_lock:
        return set(_context_subscriptions.get(context_id, set()))


def store_remote_tree_snapshot(
    sid: str,
    payload: dict[str, Any],
) -> RemoteTreeSnapshot:
    snapshot = RemoteTreeSnapshot(
        sid=sid,
        payload=dict(payload),
        updated_at=time.time(),
    )
    with _state_lock:
        _remote_tree_snapshots[sid] = snapshot
    return snapshot


def clear_remote_tree_snapshot(sid: str) -> None:
    with _state_lock:
        _remote_tree_snapshots.pop(sid, None)


def latest_remote_tree_for_context(
    context_id: str,
    *,
    max_age_seconds: float = 90.0,
) -> dict[str, Any] | None:
    now = time.time()
    with _state_lock:
        subscribers = _context_subscriptions.get(context_id, set())
        snapshots = [
            _remote_tree_snapshots[sid]
            for sid in subscribers
            if sid in _remote_tree_snapshots
        ]

    if not snapshots:
        return None

    snapshots.sort(key=lambda item: item.updated_at, reverse=True)
    for snapshot in snapshots:
        if max_age_seconds > 0 and now - snapshot.updated_at > max_age_seconds:
            continue
        payload = dict(snapshot.payload)
        payload["sid"] = snapshot.sid
        payload["updated_at"] = snapshot.updated_at
        return payload
    return None


def select_target_sid(context_id: str) -> str | None:
    with _state_lock:
        subscribers = _context_subscriptions.get(context_id, set())
        if not subscribers:
            return None
        return sorted(subscribers)[0]


def store_sid_remote_file_metadata(sid: str, payload: dict[str, Any]) -> RemoteFileMetadata:
    write_enabled = bool(payload.get("write_enabled"))
    mode = str(payload.get("mode", "") or "").strip().lower()
    if mode not in {"read_only", "read_write"}:
        mode = "read_write" if write_enabled else "read_only"
    metadata = RemoteFileMetadata(
        enabled=bool(payload.get("enabled", True)),
        write_enabled=write_enabled,
        mode=mode,
        updated_at=time.time(),
    )
    with _state_lock:
        _sid_remote_file_metadata[sid] = metadata
    return metadata


def clear_sid_remote_file_metadata(sid: str) -> None:
    with _state_lock:
        _sid_remote_file_metadata.pop(sid, None)


def remote_file_metadata_for_sid(sid: str) -> dict[str, Any] | None:
    with _state_lock:
        metadata = _sid_remote_file_metadata.get(sid)
    if metadata is None:
        return None
    return {
        "enabled": metadata.enabled,
        "write_enabled": metadata.write_enabled,
        "mode": metadata.mode,
        "updated_at": metadata.updated_at,
    }


def select_remote_file_target_sid(context_id: str, *, require_writes: bool = False) -> str | None:
    with _state_lock:
        subscribers = sorted(_context_subscriptions.get(context_id, set()))
        fallback_sid: str | None = None
        for sid in subscribers:
            metadata = _sid_remote_file_metadata.get(sid)
            if metadata is None:
                if fallback_sid is None:
                    fallback_sid = sid
                continue
            if not metadata.enabled:
                continue
            if require_writes and not metadata.write_enabled:
                continue
            return sid
    return fallback_sid


def store_sid_remote_exec_metadata(sid: str, payload: dict[str, Any]) -> RemoteExecMetadata:
    metadata = RemoteExecMetadata(
        enabled=bool(payload.get("enabled")),
        updated_at=time.time(),
    )
    with _state_lock:
        _sid_remote_exec_metadata[sid] = metadata
    return metadata


def clear_sid_remote_exec_metadata(sid: str) -> None:
    with _state_lock:
        _sid_remote_exec_metadata.pop(sid, None)


def remote_exec_metadata_for_sid(sid: str) -> dict[str, Any] | None:
    with _state_lock:
        metadata = _sid_remote_exec_metadata.get(sid)
    if metadata is None:
        return None
    return {
        "enabled": metadata.enabled,
        "updated_at": metadata.updated_at,
    }


def select_remote_exec_target_sid(context_id: str, *, require_writes: bool = False) -> str | None:
    with _state_lock:
        subscribers = sorted(_context_subscriptions.get(context_id, set()))
        fallback_sid: str | None = None
        for sid in subscribers:
            metadata = _sid_remote_exec_metadata.get(sid)
            if metadata is None:
                if fallback_sid is None:
                    fallback_sid = sid
                continue
            if metadata.enabled:
                if require_writes:
                    file_metadata = _sid_remote_file_metadata.get(sid)
                    if file_metadata is not None and (
                        not file_metadata.enabled or not file_metadata.write_enabled
                    ):
                        continue
                return sid
    return fallback_sid


def store_sid_computer_use_metadata(sid: str, payload: dict[str, Any]) -> ComputerUseMetadata:
    features_value = payload.get("features")
    if isinstance(features_value, (list, tuple)):
        features = tuple(str(item).strip() for item in features_value if str(item).strip())
    else:
        features = ()
    metadata = ComputerUseMetadata(
        supported=bool(payload.get("supported")),
        enabled=bool(payload.get("supported")) and bool(payload.get("enabled")),
        trust_mode=str(payload.get("trust_mode", "") or "").strip(),
        artifact_root=str(payload.get("artifact_root", "") or "").strip(),
        backend_id=str(payload.get("backend_id", "") or "").strip(),
        backend_family=str(payload.get("backend_family", "") or "").strip(),
        features=features,
        support_reason=str(payload.get("support_reason", "") or "").strip(),
        updated_at=time.time(),
    )
    with _state_lock:
        _sid_computer_use_metadata[sid] = metadata
    return metadata


def clear_sid_computer_use_metadata(sid: str) -> None:
    with _state_lock:
        _sid_computer_use_metadata.pop(sid, None)


def computer_use_metadata_for_sid(sid: str) -> dict[str, Any] | None:
    with _state_lock:
        metadata = _sid_computer_use_metadata.get(sid)
    if metadata is None:
        return None
    return {
        "supported": metadata.supported,
        "enabled": metadata.enabled,
        "trust_mode": metadata.trust_mode,
        "artifact_root": metadata.artifact_root,
        "backend_id": metadata.backend_id,
        "backend_family": metadata.backend_family,
        "features": list(metadata.features),
        "support_reason": metadata.support_reason,
        "updated_at": metadata.updated_at,
    }


def select_computer_use_target_sid(context_id: str) -> str | None:
    with _state_lock:
        subscribers = sorted(_context_subscriptions.get(context_id, set()))
        for sid in subscribers:
            metadata = _sid_computer_use_metadata.get(sid)
            if metadata and metadata.supported and metadata.enabled:
                return sid
    return None


def store_pending_file_op(
    op_id: str,
    *,
    sid: str,
    future: asyncio.Future[dict[str, Any]],
    loop: asyncio.AbstractEventLoop,
    context_id: str | None = None,
) -> None:
    with _state_lock:
        _pending_file_ops[op_id] = PendingFileOperation(
            sid=sid,
            loop=loop,
            future=future,
            context_id=context_id,
        )


def clear_pending_file_op(op_id: str) -> None:
    with _state_lock:
        _pending_file_ops.pop(op_id, None)


def resolve_pending_file_op(
    op_id: str,
    *,
    sid: str,
    payload: dict[str, Any],
) -> bool:
    return _resolve_pending(_pending_file_ops, op_id, sid=sid, payload=payload)


def fail_pending_file_op(
    op_id: str,
    *,
    sid: str | None = None,
    error: str,
) -> bool:
    return _fail_pending(_pending_file_ops, op_id, sid=sid, error=error)


def fail_pending_file_ops_for_sid(sid: str, *, error: str) -> None:
    _fail_pending_for_sid(_pending_file_ops, sid=sid, error=error)


def store_pending_exec_op(
    op_id: str,
    *,
    sid: str,
    future: asyncio.Future[dict[str, Any]],
    loop: asyncio.AbstractEventLoop,
    context_id: str | None = None,
) -> None:
    with _state_lock:
        _pending_exec_ops[op_id] = PendingExecOperation(
            sid=sid,
            loop=loop,
            future=future,
            context_id=context_id,
        )


def clear_pending_exec_op(op_id: str) -> None:
    with _state_lock:
        _pending_exec_ops.pop(op_id, None)


def resolve_pending_exec_op(
    op_id: str,
    *,
    sid: str,
    payload: dict[str, Any],
) -> bool:
    return _resolve_pending(_pending_exec_ops, op_id, sid=sid, payload=payload)


def fail_pending_exec_op(
    op_id: str,
    *,
    sid: str | None = None,
    error: str,
) -> bool:
    return _fail_pending(_pending_exec_ops, op_id, sid=sid, error=error)


def fail_pending_exec_ops_for_sid(sid: str, *, error: str) -> None:
    _fail_pending_for_sid(_pending_exec_ops, sid=sid, error=error)


def store_pending_computer_use_op(
    op_id: str,
    *,
    sid: str,
    future: asyncio.Future[dict[str, Any]],
    loop: asyncio.AbstractEventLoop,
    context_id: str | None = None,
) -> None:
    with _state_lock:
        _pending_computer_use_ops[op_id] = PendingComputerUseOperation(
            sid=sid,
            loop=loop,
            future=future,
            context_id=context_id,
        )


def clear_pending_computer_use_op(op_id: str) -> None:
    with _state_lock:
        _pending_computer_use_ops.pop(op_id, None)


def resolve_pending_computer_use_op(
    op_id: str,
    *,
    sid: str,
    payload: dict[str, Any],
) -> bool:
    return _resolve_pending(_pending_computer_use_ops, op_id, sid=sid, payload=payload)


def fail_pending_computer_use_op(
    op_id: str,
    *,
    sid: str | None = None,
    error: str,
) -> bool:
    return _fail_pending(_pending_computer_use_ops, op_id, sid=sid, error=error)


def fail_pending_computer_use_ops_for_sid(sid: str, *, error: str) -> None:
    _fail_pending_for_sid(_pending_computer_use_ops, sid=sid, error=error)


def _resolve_pending(
    registry: dict[str, PendingFileOperation | PendingExecOperation | PendingComputerUseOperation],
    op_id: str,
    *,
    sid: str,
    payload: dict[str, Any],
) -> bool:
    with _state_lock:
        pending = registry.get(op_id)
        if pending is None or pending.sid != sid:
            return False
        registry.pop(op_id, None)

    pending.loop.call_soon_threadsafe(_set_future_result, pending.future, dict(payload))
    return True


def _fail_pending(
    registry: dict[str, PendingFileOperation | PendingExecOperation | PendingComputerUseOperation],
    op_id: str,
    *,
    sid: str | None,
    error: str,
) -> bool:
    with _state_lock:
        pending = registry.get(op_id)
        if pending is None:
            return False
        if sid is not None and pending.sid != sid:
            return False
        registry.pop(op_id, None)

    pending.loop.call_soon_threadsafe(
        _set_future_result,
        pending.future,
        {"op_id": op_id, "ok": False, "error": error},
    )
    return True


def _fail_pending_for_sid(
    registry: dict[str, PendingFileOperation | PendingExecOperation | PendingComputerUseOperation],
    *,
    sid: str,
    error: str,
) -> None:
    with _state_lock:
        matches = [
            (op_id, pending)
            for op_id, pending in registry.items()
            if pending.sid == sid
        ]
        for op_id, _pending in matches:
            registry.pop(op_id, None)

    for op_id, pending in matches:
        pending.loop.call_soon_threadsafe(
            _set_future_result,
            pending.future,
            {"op_id": op_id, "ok": False, "error": error},
        )


def _set_future_result(
    future: asyncio.Future[dict[str, Any]],
    payload: dict[str, Any],
) -> None:
    if not future.done():
        future.set_result(payload)
