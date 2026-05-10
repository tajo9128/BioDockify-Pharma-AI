from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from helpers.extract_tools import normalize_tool_request


def test_normalize_tool_request_accepts_fallback_keys() -> None:
    assert normalize_tool_request({"tool": "response", "args": {"text": "ok"}}) == (
        "response",
        {"text": "ok"},
    )


def test_normalize_tool_request_uses_fallback_when_canonical_name_is_empty() -> None:
    assert normalize_tool_request(
        {"tool_name": "", "tool": "response", "args": {"text": "ok"}}
    ) == ("response", {"text": "ok"})


def test_normalize_tool_request_uses_fallback_when_canonical_args_are_invalid() -> None:
    assert normalize_tool_request(
        {"tool_name": "response", "tool_args": None, "args": {"text": "ok"}}
    ) == ("response", {"text": "ok"})


def test_normalize_tool_request_rejects_missing_args() -> None:
    with pytest.raises(ValueError, match="tool_args"):
        normalize_tool_request({"tool_name": "response"})
