from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from helpers.extension import Extension

from plugins._a0_connector.helpers.ws_runtime import (
    computer_use_metadata_for_sid,
    remote_exec_metadata_for_sid,
    remote_file_metadata_for_sid,
    subscribed_sids_for_context,
)


@dataclass(frozen=True)
class RemoteFileCapability:
    available: bool
    write_enabled: bool = False
    access_mode: str = "Unknown"
    advertised: bool = False


class IncludeRemoteToolStubs(Extension):
    def execute(self, data: dict[str, Any] = {}, **kwargs: Any) -> None:
        if not self.agent:
            return

        result = data.get("result")
        if not isinstance(result, str):
            return

        context_id = str(getattr(self.agent.context, "id", "") or "").strip()
        if not context_id:
            return

        stubs: list[str] = []
        file_capability = _remote_file_capability(context_id)

        if file_capability.available:
            stubs.append(
                self.agent.read_prompt(
                    "agent.connector_tool.text_editor_remote.md",
                    access_mode=file_capability.access_mode,
                    write_guidance=_file_write_guidance(file_capability),
                )
            )

        if _remote_exec_available(context_id):
            stubs.append(
                self.agent.read_prompt(
                    "agent.connector_tool.code_execution_remote.md",
                    access_mode=file_capability.access_mode,
                    write_runtime_note=_exec_write_runtime_note(file_capability),
                )
            )

        computer_use = _computer_use_capability(context_id)
        if computer_use:
            stubs.append(
                self.agent.read_prompt(
                    "agent.connector_tool.computer_use_remote.md",
                    backend=computer_use["backend"],
                    trust_mode=computer_use["trust_mode"],
                    features=computer_use["features"],
                )
            )

        if not stubs:
            return

        data["result"] = (
            result.rstrip()
            + "\n\n"
            + "\n\n".join(stub.strip() for stub in stubs if stub.strip())
        )


def _subscribed_sids(context_id: str) -> list[str]:
    return sorted(subscribed_sids_for_context(context_id))


def _remote_file_capability(context_id: str) -> RemoteFileCapability:
    saw_advertised = False
    saw_enabled = False
    saw_write_enabled = False

    for sid in _subscribed_sids(context_id):
        metadata = remote_file_metadata_for_sid(sid)
        if not metadata:
            continue
        saw_advertised = True
        if not metadata.get("enabled", True):
            continue
        saw_enabled = True
        if metadata.get("write_enabled"):
            saw_write_enabled = True

    if not saw_enabled:
        return RemoteFileCapability(
            available=False,
            access_mode="Disabled" if saw_advertised else "Unknown",
            advertised=saw_advertised,
        )

    return RemoteFileCapability(
        available=True,
        write_enabled=saw_write_enabled,
        access_mode="Read&Write" if saw_write_enabled else "Read only",
        advertised=True,
    )


def _remote_exec_available(context_id: str) -> bool:
    for sid in _subscribed_sids(context_id):
        metadata = remote_exec_metadata_for_sid(sid)
        if metadata and metadata.get("enabled"):
            return True
    return False


def _computer_use_capability(context_id: str) -> dict[str, str] | None:
    for sid in _subscribed_sids(context_id):
        metadata = computer_use_metadata_for_sid(sid)
        if not metadata or not metadata.get("supported") or not metadata.get("enabled"):
            continue

        backend_id = str(metadata.get("backend_id") or "").strip() or "unknown"
        backend_family = str(metadata.get("backend_family") or "").strip()
        backend = backend_id if not backend_family else f"{backend_id}/{backend_family}"
        trust_mode = str(metadata.get("trust_mode") or "").strip() or "unknown"
        features_value = metadata.get("features")
        if isinstance(features_value, (list, tuple)):
            features = ", ".join(
                str(item).strip() for item in features_value if str(item).strip()
            )
        else:
            features = ""

        return {
            "backend": backend,
            "trust_mode": trust_mode,
            "features": features or "none advertised",
        }

    return None


def _file_write_guidance(capability: RemoteFileCapability) -> str:
    if capability.write_enabled:
        return "Writes and patches are currently available."
    return (
        "Writes and patches are disabled until the user switches the CLI to "
        "Read&Write with F3."
    )


def _exec_write_runtime_note(capability: RemoteFileCapability) -> str:
    if capability.write_enabled:
        return "Mutating runtimes are currently available because local access is Read&Write."
    if capability.available:
        return (
            "Mutating runtimes are disabled until the user switches the CLI to "
            "Read&Write with F3; use output/reset only for existing sessions."
        )
    if capability.advertised:
        return (
            "The CLI advertises remote file access as disabled; mutating runtimes "
            "are unavailable until local file access is enabled."
        )
    return (
        "The CLI did not advertise a file access mode; prefer non-mutating "
        "inspection until access is clear."
    )
