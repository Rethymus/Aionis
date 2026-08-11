"""Hermetic tests for the CI-refresh export guard (``_safe_export``).

The daily ``refresh-terminal-data`` workflow runs on a fresh checkout where the
gitignored ``runs/*.parquet`` / ``runs/*.json`` research artifacts are absent.
``_safe_export`` is the guard that lets the refresh skip a missing source
(preserving the tracked JSON) instead of crashing the whole export. These tests
lock its contract: pass-through on success, silent skip on FileNotFoundError,
and — critically — re-raise of any other exception so genuine bugs still surface.
"""
from __future__ import annotations

import json
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


# --- _build_news_theme wiring (GDELT cache → news_sentiment panel block) -----


def _gdelt_cache(series: list[dict]) -> dict:
    return {
        "source": "GDELT Doc 2.0 timelinetone",
        "series": series,
        "n_months": len(series),
    }


def test_build_news_theme_live_when_cache_has_series(tmp_path) -> None:
    cache = tmp_path / "gdelt_news_sentiment.json"
    cache.write_text(
        json.dumps(
            _gdelt_cache(
                [
                    {"month": "2017-04", "tone": -4.0, "volume": 1000, "n": 3},
                    {"month": "2017-05", "tone": -2.0, "volume": 1100, "n": 3},
                    {"month": "2017-06", "tone": 1.5, "volume": 1200, "n": 3},
                ]
            )
        )
    )
    news = etd._build_news_theme(cache)
    assert news["status"] == "live"
    assert news["key"] == "news_sentiment"
    signals = {s["name"]: s["value"] for s in news["signals"]}
    assert signals["tone_latest"] == 1.5
    assert signals["tone_mean"] == round((-4.0 + -2.0 + 1.5) / 3, 3)
    assert signals["tone_min"] == -4.0
    assert signals["volume_latest"] == 1200
    assert signals["n_months"] == 3
    assert [p["month"] for p in news["series"]] == ["2017-04", "2017-05", "2017-06"]
    assert "2017-04" in news["headline"] and "2017-06" in news["headline"]


def test_build_news_theme_honest_when_cache_absent(tmp_path) -> None:
    # Cold CI checkout: cache missing → honest "建设中" state, NOT an exception
    # and NOT an empty live block. The tracked panel is preserved.
    news = etd._build_news_theme(tmp_path / "does_not_exist.json")
    assert news["status"] == "forward_only"
    assert news["signals"] == [] and news["series"] == []
    assert "建设中" in news["headline"]


def test_build_news_theme_honest_on_malformed_cache(tmp_path) -> None:
    cache = tmp_path / "gdelt_news_sentiment.json"
    cache.write_text("{not valid json")
    news = etd._build_news_theme(cache)
    assert news["status"] == "forward_only"
    assert news["signals"] == []


def test_build_news_theme_honest_on_empty_series(tmp_path) -> None:
    cache = tmp_path / "gdelt_news_sentiment.json"
    cache.write_text(json.dumps(_gdelt_cache([])))
    news = etd._build_news_theme(cache)
    assert news["status"] == "forward_only"
    assert news["signals"] == []


def test_build_news_theme_sparkline_caps_at_24_months(tmp_path) -> None:
    # 30 months of history → sparkline keeps only the last 24 (signals still
    # summarize the full window).
    series = [
        {"month": f"20{17 + i // 12}-{(i % 12) + 1:02d}", "tone": -1.0, "volume": 100, "n": 1}
        for i in range(30)
    ]
    cache = tmp_path / "gdelt_news_sentiment.json"
    cache.write_text(json.dumps(_gdelt_cache(series)))
    news = etd._build_news_theme(cache)
    assert len(news["series"]) == 24
    signals = {s["name"]: s["value"] for s in news["signals"]}
    assert signals["n_months"] == 30  # full history in signals


def test_refresh_news_sentiment_only_updates_news_preserves_others(tmp_path) -> None:
    # Panel-absent path: refresh ONLY news_sentiment; panel-dependent themes
    # (price/risk) keep their committed values verbatim. Locks the fix for the
    # '新闻情绪数据没有体现' root cause (the panel gate froze news_sentiment at
    # 'forward_only' even after the GDELT fetch succeeded).
    themes = tmp_path / "themes.json"
    payload = {
        "status": "ok",
        "as_of_date": "2026-07-31",
        "methodology": "frozen",
        "themes": [
            {"key": "price", "status": "live", "signals": [{"name": "momentum", "value": 0.3}]},
            {"key": "news_sentiment", "status": "forward_only", "signals": [], "series": []},
            {"key": "risk", "status": "live", "signals": [{"name": "downside_beta", "value": 1.2}]},
        ],
    }
    themes.write_text(json.dumps(payload))
    gdelt = tmp_path / "gdelt_news_sentiment.json"
    gdelt.write_text(
        json.dumps(
            _gdelt_cache(
                [
                    {"month": "2017-04", "tone": -4.0, "volume": 1000, "n": 3},
                    {"month": "2017-05", "tone": -2.0, "volume": 1100, "n": 3},
                    {"month": "2017-06", "tone": 1.5, "volume": 1200, "n": 3},
                ]
            )
        )
    )

    status = etd._refresh_news_sentiment_only(themes, gdelt)

    assert status == "live"
    result = json.loads(themes.read_text())
    news = next(t for t in result["themes"] if t["key"] == "news_sentiment")
    assert news["status"] == "live"
    assert len(news["signals"]) > 0  # tone populated from the GDELT cache
    # Panel-dependent themes UNCHANGED (verbatim):
    price = next(t for t in result["themes"] if t["key"] == "price")
    assert price["signals"] == [{"name": "momentum", "value": 0.3}]
    risk = next(t for t in result["themes"] if t["key"] == "risk")
    assert risk["signals"] == [{"name": "downside_beta", "value": 1.2}]
    # Top-level metadata preserved:
    assert result["as_of_date"] == "2026-07-31"
    assert result["methodology"] == "frozen"


def test_refresh_news_sentiment_only_returns_empty_when_no_themes_file(tmp_path) -> None:
    # No committed themes.json → nothing to partially refresh → '' (caller skips).
    status = etd._refresh_news_sentiment_only(tmp_path / "absent.json", tmp_path / "gdelt.json")
    assert status == ""
