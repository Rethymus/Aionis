"""P1-5 vintage discipline — drift-check classifier + provider_vintage panel.

Hermetic: the probe's _ask is monkeypatched (no network), the contracts YAML
is a tmp fixture, and the panel contract reads the COMMITTED json. The
direction-aware verdicts (unsafe/invalid/inconclusive/safe/stable) are the
CI alarm's semantics — each is pinned.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "scripts")
import probe_provider_cutoff as probe  # noqa: E402


@pytest.fixture()
def _drift_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Frozen-YAML fixture + captured _ask + tmp verdict output."""
    yaml = tmp_path / "e3_live_contracts.yaml"
    yaml.write_text(
        "provider_cutoff_policy:\n"
        "  block_on_unknown: true\n"
        '  provider_cutoff: "2023-03-10"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(probe, "_FROZEN_CONTRACTS", yaml)
    out = tmp_path / "drift.json"
    monkeypatch.setattr(probe, "DRIFT_OUT", out)
    answers: dict[str, str] = {}

    def fake_ask(api_key: str, model: str, question: str) -> str:
        # route by the date embedded in the question
        for d, ans in answers.items():
            if d in question:
                return ans
        return "UNKNOWN"

    monkeypatch.setattr(probe, "_ask", fake_ask)
    monkeypatch.setattr(probe.settings, "openai_api_key", "k")
    return answers, out


def _run(answers: dict[str, str]) -> int:
    return probe.check_drift("test-model")


def test_drift_stable(_drift_env) -> None:
    answers, out = _drift_env
    answers["2023-03-10"] = "SVB collapsed and was seized"
    answers["2024-11-06"] = "UNKNOWN"
    answers["2026-12-25"] = "UNKNOWN"
    assert _run(answers) == 0
    v = json.loads(out.read_text(encoding="utf-8"))
    assert v["status"] == "stable"
    assert v["frozen_cutoff"] == "2023-03-10"


def test_drift_unsafe_when_anchor_forgotten(_drift_env) -> None:
    answers, out = _drift_env
    answers["2023-03-10"] = "UNKNOWN"   # model forgot the anchor event
    answers["2024-11-06"] = "UNKNOWN"
    answers["2026-12-25"] = "UNKNOWN"
    assert _run(answers) == 1
    v = json.loads(out.read_text(encoding="utf-8"))
    assert v["status"] == "unsafe-drift"


def test_drift_safe_when_post_cutoff_learned(_drift_env) -> None:
    answers, out = _drift_env
    answers["2023-03-10"] = "SVB collapsed"
    answers["2024-11-06"] = "Trump was declared the winner"  # now known
    answers["2026-12-25"] = "UNKNOWN"
    assert _run(answers) == 0
    v = json.loads(out.read_text(encoding="utf-8"))
    assert v["status"] == "safe-drift"
    assert "amend" in v["note"].lower()


def test_drift_invalid_when_control_fabricated(_drift_env) -> None:
    answers, out = _drift_env
    answers["2023-03-10"] = "SVB collapsed"
    answers["2024-11-06"] = "UNKNOWN"
    answers["2026-12-25"] = "Yes, the SEC approved the global crypto exchange"
    assert _run(answers) == 1
    v = json.loads(out.read_text(encoding="utf-8"))
    assert v["status"] == "invalid"


def test_drift_inconclusive_on_probe_error(_drift_env) -> None:
    answers, out = _drift_env
    answers["2023-03-10"] = "PROBE-ERROR: HTTP Error 429"
    answers["2024-11-06"] = "UNKNOWN"
    answers["2026-12-25"] = "UNKNOWN"
    assert _run(answers) == 1
    v = json.loads(out.read_text(encoding="utf-8"))
    assert v["status"] == "inconclusive"


def test_drift_skips_green_without_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe.settings, "openai_api_key", None)
    assert probe.check_drift("m") == 0  # CI wiring: absent secret skips


# --- committed panel contract ------------------------------------------------


def test_provider_vintage_panel_contract() -> None:
    p = json.loads(
        (Path("web/src/data/aionis/provider_vintage.json")).read_text(encoding="utf-8")
    )
    assert p["panel"] == "provider_vintage" and p["provider"] == "glm"
    assert p["provider_cutoff"] == "2023-03-10"
    assert "empirical-probe-v1" in p["cutoff_provenance"]
    assert p["block_on_unknown"] is True
    b = p["probe_artifact"]["boundary"]
    assert b["latest_known"] == "2023-03-10" and b["earliest_unknown"] == "2024-11-06"
    assert b["fabrication_on_control"] is False
    assert p["latest_drift_check"]["status"] in {"stable", "safe-drift"}
    assert "never" in p["leakage_note"] or "signal" in p["leakage_note"]
