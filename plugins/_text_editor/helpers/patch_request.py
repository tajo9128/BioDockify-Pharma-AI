from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


PatchMode = Literal["edits", "patch_text"]


@dataclass(frozen=True)
class PatchRequest:
    mode: PatchMode
    edits: Any = None
    patch_text: str = ""


def parse_patch_request(
    edits: Any,
    patch_text: Any,
    *,
    both_error: str = "provide either edits or patch_text, not both",
    missing_error: str = "edits or patch_text is required for patch",
) -> tuple[PatchRequest | None, str]:
    """Validate the mutually-exclusive patch request shape."""
    if edits is not None and patch_text is not None:
        return None, both_error

    if patch_text is not None:
        text = str(patch_text)
        if not text.strip():
            return None, "patch_text must not be empty"
        return PatchRequest(mode="patch_text", patch_text=text), ""

    if not edits:
        return None, missing_error

    return PatchRequest(mode="edits", edits=edits), ""
