"""Hermetic tests for the in-repo aionis-data client (clients/aionis-data).

Zero network: every fetch goes through an injected loader backed by fixture
panel samples (small synthetic mirrors of the real panel shapes, which the
root repo's panel contract tests pin separately).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CLIENT_SRC = ROOT / "clients" / "aionis-data" / "src"
sys.path.insert(0, str(CLIENT_SRC))

from aionis_data import DEFAULT_BASE_URL, AionisDataClient  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "aionis-data"


def _loader(url: str):
    """Map an API url onto the fixture tree (hermetic stand-in)."""
    tail = url.replace(DEFAULT_BASE_URL + "/", "")
    path = FIX / tail
    if not path.exists():
        raise FileNotFoundError(f"fixture for {url} missing")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture()
def client():
    return AionisDataClient(fetch_json=_loader)


def test_claims_shape_and_null_numbers(client) -> None:
    claims = client.claims()
    assert set(claims) >= {"B", "C", "D", "E1", "track_c"}
    b = claims["B"]
    assert b["ledger_row"] == 28
    assert b["prereg_doc"] == "docs/phase-b-preregistration.md"
    assert b["mean_diff"] == -0.0008
    assert b["ci_lo"] < 0 < b["ci_hi"]  # CI brackets zero -> NULL verdict


def test_ic_series_and_combined_index(client) -> None:
    rows = client.ic_series()
    assert all({"month", "us", "cn", "combined"} <= set(r) for r in rows)
    realized = client.combined_index()
    assert all(ic is not None for _, ic in realized)
    assert len(realized) == sum(1 for r in rows if r["combined"] is not None)


def test_panels_catalog_filters_available(client) -> None:
    panels = client.panels()
    keys = {p["key"] for p in panels}
    assert "evidence_matrix" in keys and "ic_monthly" in keys
    assert all(p["status"] == "available" for p in panels)
    assert all("license" in p and "as_of" in p for p in panels)


def test_panel_fetch_and_unknown_key(client) -> None:
    health = client.panel("data_health")
    assert health["status"] in {"ok", "partial"}
    with pytest.raises(FileNotFoundError):
        client.panel("does_not_exist")


def test_default_fetch_is_injectable_not_networked() -> None:
    # constructing without fetch_json must not touch the network
    c = AionisDataClient()
    assert c.base_url == DEFAULT_BASE_URL
    assert callable(c._fetch)
