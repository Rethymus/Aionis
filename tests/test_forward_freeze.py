"""E3 Slice 3c - freeze the forward information set I_t (snapshot-on-arrival).

TDD: these tests FAIL until ``src/aionis/eval/forward_freeze.py`` exists and
freezes the three Slice-2 collectors under ONE shared ``(snapshot_ts,
last_poll_ts)`` clock, builds a canonical manifest of the sealed snapshot, and
appends a ``forward_iset_frozen`` ledger row whose sha256 is committed BEFORE
any fit / commit.

Scope (plan §3 sub-slice 3c; pre-reg §9):
  * shared clock - all three collectors receive the SAME (snapshot_ts, last_poll_ts);
  * canonical manifest - per-dataset ``n_rows`` + ``raw_sha256`` (re-read from the
    sealed archive) + sorted identity keys (macro: event_type/pub_date/series_id;
    13d/8k: ticker/filing_date/accession);
  * iset_sha256 - deterministic over an identical manifest; flips when a filing is
    added OR the sealed raw bytes mutate (the freeze integrity anchor);
  * ``forward_iset_frozen`` ledger row - correct event/phase, idempotent re-freeze;
  * real ledger hygiene - tests write ONLY to a tmp ``runs_dir``.

Every fixture is SYNTHETIC and labeled as such; collectors are monkeypatched (no
network). Mirrors the mocking discipline of ``tests/test_forward_ingest.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from aionis.eval import forward_freeze as FF
from aionis.ingest.forward import _common
from aionis.ingest.forward.earnings_8k_forward import DATASET as EARNINGS_DATASET
from aionis.ingest.forward.macro_forward import DATASET as MACRO_DATASET
from aionis.ingest.forward.stakes_13d_forward import DATASET as STAKES_DATASET
from aionis.reporting import forward_ledger as FL

PHASE = "E3"
SNAP = "2026-07-31T20:00:00+00:00"
LAST_POLL = "2026-06-30T20:00:00+00:00"


# ---------------------------------------------------------------------------
# SYNTHETIC collector frames (labeled - no real data, no network)
# ---------------------------------------------------------------------------


def _synth_macro() -> pd.DataFrame:
    """SYNTHETIC macro forward frame (Slice-2 collect_macro_forward shape)."""
    return pd.DataFrame([
        {"series_id": "CPIAUCSL", "event_type": "CPI", "feature": "macro_cpiaucsl_surprise",
         "ref_date": "2026-07-15", "pub_date": "2026-07-15", "surprise_z": 0.3,
         "value": 0.3, "event_ts": "2026-07-15", "snapshot_ts": SNAP},
    ])


def _synth_stakes(extra: bool = False) -> pd.DataFrame:
    """SYNTHETIC 13D forward frame (Slice-2 collect_13d_forward shape)."""
    rows = [
        {"ticker": "AAA", "cik": 1, "feature": "stake_13d_filing", "value": 1.0,
         "form": "SC 13D", "filing_date": "2026-07-10", "accession": "0001-aaa",
         "event_ts": "2026-07-10", "snapshot_ts": SNAP},
    ]
    if extra:
        rows.append(
            {"ticker": "BBB", "cik": 2, "feature": "stake_13d_filing", "value": 1.0,
             "form": "SC 13D/A", "filing_date": "2026-07-20", "accession": "0002-bbb",
             "event_ts": "2026-07-20", "snapshot_ts": SNAP}
        )
    return pd.DataFrame(rows)


def _synth_earnings() -> pd.DataFrame:
    """SYNTHETIC 8-K Item-2.02 forward frame (Slice-2 collect_8k_forward shape)."""
    return pd.DataFrame([
        {"ticker": "AAA", "cik": 1, "feature": "earnings_8k_item_2_02", "value": 1.0,
         "form": "8-K", "filing_date": "2026-07-12", "accession": "0003-aaa",
         "items": "Item 2.02", "event_ts": "2026-07-12", "snapshot_ts": SNAP},
    ])


def _patch_collectors(
    monkeypatch: pytest.MonkeyPatch,
    *,
    macro: pd.DataFrame | None = None,
    stakes: pd.DataFrame | None = None,
    earnings: pd.DataFrame | None = None,
    cache_dir: Path,
) -> list[dict]:
    """Monkeypatch the three collectors (no network). Returns the call log.

    Each mock mimics the real collector's ``archive_raw`` side effect (write the
    sealed raw archive via the real ``_common.archive_raw``) so ``freeze_forward_iset``'s
    re-read of the archive works exactly as in the real path.
    """
    calls: list[dict] = []
    macro = _synth_macro() if macro is None else macro
    stakes = _synth_stakes() if stakes is None else stakes
    earnings = _synth_earnings() if earnings is None else earnings

    def _record(dataset: str, snapshot_ts: str, last_poll_ts, cache_dir_arg: Path) -> None:
        snap = _common.canonical_snapshot_ts(snapshot_ts)
        calls.append({"dataset": dataset, "snapshot_ts": snap, "last_poll_ts": last_poll_ts})

    def _macro(*, snapshot_ts, last_poll_ts, fred_api_key, cache_dir, runs_dir):  # type: ignore[no-untyped-def]
        snap = _common.canonical_snapshot_ts(snapshot_ts)
        _record(MACRO_DATASET, snapshot_ts, last_poll_ts, cache_dir)
        _common.archive_raw(cache_dir, MACRO_DATASET, snap, macro.to_dict("records"))
        return macro.copy()

    def _stakes(ciks, *, snapshot_ts, last_poll_ts, cache_dir, runs_dir):  # type: ignore[no-untyped-def]
        snap = _common.canonical_snapshot_ts(snapshot_ts)
        _record(STAKES_DATASET, snapshot_ts, last_poll_ts, cache_dir)
        _common.archive_raw(cache_dir, STAKES_DATASET, snap, stakes.to_dict("records"))
        return stakes.copy()

    def _earnings(tickers, *, snapshot_ts, last_poll_ts, cache_dir, runs_dir):  # type: ignore[no-untyped-def]
        snap = _common.canonical_snapshot_ts(snapshot_ts)
        _record(EARNINGS_DATASET, snapshot_ts, last_poll_ts, cache_dir)
        _common.archive_raw(cache_dir, EARNINGS_DATASET, snap, earnings.to_dict("records"))
        return earnings.copy()

    monkeypatch.setattr(FF, "collect_macro_forward", _macro)
    monkeypatch.setattr(FF, "collect_13d_forward", _stakes)
    monkeypatch.setattr(FF, "collect_8k_forward", _earnings)
    return calls


def _ledger_rows(runs_dir: Path) -> list[dict]:
    ledger = runs_dir / "ledger.jsonl"
    if not ledger.exists():
        return []
    return [json.loads(ln) for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# shared clock - all three collectors receive the SAME (snapshot_ts, last_poll_ts)
# ---------------------------------------------------------------------------


def test_freeze_passes_shared_clock_to_all_three_collectors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The freeze is atomic on ONE clock: every collector sees the same snapshot_ts
    and last_poll_ts."""
    cache = tmp_path / "cache"
    cache.mkdir()
    calls = _patch_collectors(monkeypatch, cache_dir=cache)
    FF.freeze_forward_iset(
        snapshot_ts=SNAP, last_poll_ts=LAST_POLL, ciks={"AAA": 1},
        tickers=["AAA"], fred_api_key="key", cache_dir=cache, runs_dir=tmp_path,
    )
    assert len(calls) == 3
    for c in calls:
        assert c["snapshot_ts"] == _common.canonical_snapshot_ts(SNAP)
        assert c["last_poll_ts"] == LAST_POLL
    datasets = {c["dataset"] for c in calls}
    assert datasets == {MACRO_DATASET, STAKES_DATASET, EARNINGS_DATASET}


# ---------------------------------------------------------------------------
# manifest canonical / sorted
# ---------------------------------------------------------------------------


def test_manifest_is_canonical_and_sorted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Manifest: per-dataset n_rows + raw_sha256 (re-read) + sorted identity keys."""
    cache = tmp_path / "cache"
    cache.mkdir()
    _patch_collectors(monkeypatch, cache_dir=cache)
    out = FF.freeze_forward_iset(
        snapshot_ts=SNAP, last_poll_ts=LAST_POLL, ciks={"AAA": 1},
        tickers=["AAA"], fred_api_key="key", cache_dir=cache, runs_dir=tmp_path,
    )
    manifest = FF.iset_manifest(out, uv_lock_sha256="uv" * 32)
    # macro keys = (event_type, pub_date_iso, series_id), sorted
    macro_keys = manifest[MACRO_DATASET]["keys"]
    assert macro_keys == [["CPI", "2026-07-15", "CPIAUCSL"]]
    assert macro_keys == sorted(macro_keys)
    # 13d/8k keys = (ticker, filing_date_iso, accession), sorted
    assert manifest[STAKES_DATASET]["keys"] == [["AAA", "2026-07-10", "0001-aaa"]]
    assert manifest[EARNINGS_DATASET]["keys"] == [["AAA", "2026-07-12", "0003-aaa"]]
    # per-dataset n_rows + raw_sha256 (re-read from the sealed archive)
    assert manifest[MACRO_DATASET]["n_rows"] == 1
    assert manifest[STAKES_DATASET]["n_rows"] == 1
    assert manifest[EARNINGS_DATASET]["n_rows"] == 1
    for ds in (MACRO_DATASET, STAKES_DATASET, EARNINGS_DATASET):
        assert len(manifest[ds]["raw_sha256"]) == 64
    assert manifest["uv_lock_sha256"] == "uv" * 32
    # manifest is JSON-serializable (the sha256 input must be stable)
    json.dumps(manifest, default=str, sort_keys=True)


# ---------------------------------------------------------------------------
# iset_sha256 determinism + integrity flips
# ---------------------------------------------------------------------------


def test_iset_sha256_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Identical freeze -> identical iset_sha256 (H6 determinism, freeze portion)."""
    cache = tmp_path / "cache"
    cache.mkdir()
    _patch_collectors(monkeypatch, cache_dir=cache)
    out = FF.freeze_forward_iset(
        snapshot_ts=SNAP, last_poll_ts=LAST_POLL, ciks={"AAA": 1},
        tickers=["AAA"], fred_api_key="key", cache_dir=cache, runs_dir=tmp_path,
    )
    m1 = FF.iset_manifest(out, uv_lock_sha256="uv" * 32)
    m2 = FF.iset_manifest(
        {**out, "macro_df": out["macro_df"].copy(), "stakes_df": out["stakes_df"].copy(),
         "earnings_df": out["earnings_df"].copy()},
        uv_lock_sha256="uv" * 32,
    )
    assert FF.iset_sha256_from_manifest(m1) == FF.iset_sha256_from_manifest(m2)


def test_iset_sha256_flips_when_a_filing_is_added(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adding a 13D filing grows the manifest keys -> flips iset_sha256."""
    cache = tmp_path / "cache"
    cache.mkdir()
    _patch_collectors(monkeypatch, cache_dir=cache, stakes=_synth_stakes(extra=False))
    out_a = FF.freeze_forward_iset(
        snapshot_ts=SNAP, last_poll_ts=LAST_POLL, ciks={"AAA": 1},
        tickers=["AAA"], fred_api_key="key", cache_dir=cache, runs_dir=tmp_path,
    )
    sha_a = FF.iset_sha256_from_manifest(FF.iset_manifest(out_a, uv_lock_sha256="uv" * 32))

    # re-freeze with an extra filing (new cache so archive re-seals)
    cache2 = tmp_path / "cache2"
    cache2.mkdir()
    _patch_collectors(monkeypatch, cache_dir=cache2, stakes=_synth_stakes(extra=True))
    out_b = FF.freeze_forward_iset(
        snapshot_ts=SNAP, last_poll_ts=LAST_POLL, ciks={"AAA": 1, "BBB": 2},
        tickers=["AAA", "BBB"], fred_api_key="key", cache_dir=cache2, runs_dir=tmp_path,
    )
    sha_b = FF.iset_sha256_from_manifest(FF.iset_manifest(out_b, uv_lock_sha256="uv" * 32))
    assert sha_a != sha_b


def test_iset_sha256_flips_when_sealed_raw_bytes_mutate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutating sealed raw archive bytes (rows unchanged) flips raw_sha256 and the iset_sha256."""
    cache = tmp_path / "cache"
    cache.mkdir()
    _patch_collectors(monkeypatch, cache_dir=cache)
    out = FF.freeze_forward_iset(
        snapshot_ts=SNAP, last_poll_ts=LAST_POLL, ciks={"AAA": 1},
        tickers=["AAA"], fred_api_key="key", cache_dir=cache, runs_dir=tmp_path,
    )
    sha_before = FF.iset_sha256_from_manifest(FF.iset_manifest(out, uv_lock_sha256="uv" * 32))

    # mutate the sealed stakes archive bytes on disk, then re-freeze (mock skips
    # re-write because archive_raw is sealed -> the re-read picks up the mutation)
    raw_path = cache / f"{STAKES_DATASET}_raw_{_common.compact_snapshot_ts(SNAP)}.json"
    raw_path.write_text(raw_path.read_text() + " TAMPERED")
    out2 = FF.freeze_forward_iset(
        snapshot_ts=SNAP, last_poll_ts=LAST_POLL, ciks={"AAA": 1},
        tickers=["AAA"], fred_api_key="key", cache_dir=cache, runs_dir=tmp_path,
    )
    sha_after = FF.iset_sha256_from_manifest(FF.iset_manifest(out2, uv_lock_sha256="uv" * 32))
    assert sha_before != sha_after


# ---------------------------------------------------------------------------
# forward_iset_frozen ledger row + idempotency
# ---------------------------------------------------------------------------


def test_commit_forward_iset_frozen_appends_correct_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """commit_forward_iset_frozen appends ONE forward_iset_frozen row (event/phase/schema)."""
    cache = tmp_path / "cache"
    cache.mkdir()
    _patch_collectors(monkeypatch, cache_dir=cache)
    out = FF.freeze_forward_iset(
        snapshot_ts=SNAP, last_poll_ts=LAST_POLL, ciks={"AAA": 1},
        tickers=["AAA"], fred_api_key="key", cache_dir=cache, runs_dir=tmp_path,
    )
    iset_sha = FF.iset_sha256_from_manifest(FF.iset_manifest(out, uv_lock_sha256="uv" * 32))
    row = FF.commit_forward_iset_frozen(
        snapshot_ts=SNAP, iset_sha256=iset_sha, runs_dir=tmp_path,
        manifest_summary={"n_rows_total": 3},
    )
    assert row["event"] == "forward_iset_frozen"
    assert row["phase"] == PHASE
    assert row["snapshot_ts"] == _common.canonical_snapshot_ts(SNAP)
    assert row["iset_sha256"] == iset_sha
    assert row["manifest_summary"] == {"n_rows_total": 3}
    assert row.get("_appended") is True
    frozen = [r for r in _ledger_rows(tmp_path) if r.get("event") == "forward_iset_frozen"]
    assert len(frozen) == 1


def test_commit_forward_iset_frozen_is_idempotent_on_refreeze(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Re-freeze of identical (snapshot_ts, iset_sha256) appends NO duplicate row."""
    cache = tmp_path / "cache"
    cache.mkdir()
    _patch_collectors(monkeypatch, cache_dir=cache)
    out = FF.freeze_forward_iset(
        snapshot_ts=SNAP, last_poll_ts=LAST_POLL, ciks={"AAA": 1},
        tickers=["AAA"], fred_api_key="key", cache_dir=cache, runs_dir=tmp_path,
    )
    iset_sha = FF.iset_sha256_from_manifest(FF.iset_manifest(out, uv_lock_sha256="uv" * 32))
    r1 = FF.commit_forward_iset_frozen(snapshot_ts=SNAP, iset_sha256=iset_sha, runs_dir=tmp_path)
    r2 = FF.commit_forward_iset_frozen(snapshot_ts=SNAP, iset_sha256=iset_sha, runs_dir=tmp_path)
    assert r1.get("_appended") is True
    assert r2.get("_appended") is False
    frozen = [r for r in _ledger_rows(tmp_path) if r.get("event") == "forward_iset_frozen"]
    assert len(frozen) == 1  # no duplicate


# ---------------------------------------------------------------------------
# real-ledger hygiene - never touches runs/ledger.jsonl
# ---------------------------------------------------------------------------


def test_freeze_never_touches_real_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Anti-leakage hygiene: the real runs/ledger.jsonl is unchanged by these ops."""
    real_ledger = Path(__file__).resolve().parents[1] / "runs" / "ledger.jsonl"
    before = real_ledger.read_bytes() if real_ledger.exists() else b""
    cache = tmp_path / "cache"
    cache.mkdir()
    _patch_collectors(monkeypatch, cache_dir=cache)
    out = FF.freeze_forward_iset(
        snapshot_ts=SNAP, last_poll_ts=LAST_POLL, ciks={"AAA": 1},
        tickers=["AAA"], fred_api_key="key", cache_dir=cache, runs_dir=tmp_path,
    )
    iset_sha = FF.iset_sha256_from_manifest(FF.iset_manifest(out, uv_lock_sha256="uv" * 32))
    FF.commit_forward_iset_frozen(snapshot_ts=SNAP, iset_sha256=iset_sha, runs_dir=tmp_path)
    after = real_ledger.read_bytes() if real_ledger.exists() else b""
    assert before == after


def test_read_forward_rows_returns_iset_frozen(tmp_path: Path) -> None:
    """Cross-check: forward_iset_frozen rows are readable via read_forward_rows (I1 family)."""
    FL._append_ledger_row(tmp_path, {
        "event": "forward_iset_frozen", "phase": PHASE, "mode": "exploratory",
        "snapshot_ts": SNAP, "iset_sha256": "a" * 64,
    })
    rows = FL.read_forward_rows(runs_dir=tmp_path, event="forward_iset_frozen")
    assert len(rows) == 1
    assert rows[0]["iset_sha256"] == "a" * 64
