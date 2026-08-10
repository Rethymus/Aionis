"""Hermetic tests for the CI-refresh export guard (``_safe_export``).

The daily ``refresh-terminal-data`` workflow runs on a fresh checkout where the
gitignored ``runs/*.parquet`` / ``runs/*.json`` research artifacts are absent.
``_safe_export`` is the guard that lets the refresh skip a missing source
(preserving the tracked JSON) instead of crashing the whole export. These tests
lock its contract: pass-through on success, silent skip on FileNotFoundError,
and — critically — re-raise of any other exception so genuine bugs still surface.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# export_terminal_data.py uses a sibling import (``import export_quarto_data``),
# so it must be imported with scripts/ on sys.path — exactly how the cron runs it.
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import export_terminal_data as etd  # noqa: E402


def test_safe_export_returns_wrapped_value_on_success() -> None:
    # Arrange
    def _ok(a: int, b: int) -> int:
        return a + b

    # Act
    out = etd._safe_export("ok", _ok, 2, 3)

    # Assert
    assert out == 5


def test_safe_export_swallows_filenotfound_and_returns_none() -> None:
    # Arrange — an exporter whose source artifact is missing on a fresh checkout.
    def _missing() -> None:
        raise FileNotFoundError("runs/ic_noise_floor_survey.json")

    # Act + Assert: must not raise, must return None (tracked JSON is left alone).
    assert etd._safe_export("sigma_survey", _missing) is None


def test_safe_export_reraises_non_filenotfound_exceptions() -> None:
    # Arrange — a genuine bug (KeyError) must NOT be swallowed; only missing
    # artifacts are skipped. This is the guard against hiding real exporter bugs.
    def _buggy() -> None:
        raise KeyError("malformed payload")

    # Act + Assert
    with pytest.raises(KeyError):
        etd._safe_export("buggy", _buggy)


def test_safe_export_forwards_keyword_arguments() -> None:
    # Arrange
    def _fn(*, x: int, y: int) -> int:
        return x * y

    # Act + Assert
    assert etd._safe_export("kw", _fn, x=3, y=4) == 12
