"""Forward ingest (E3 Slice 2) — hermetic PIT invariants (no network).

Pins the snapshot-on-arrival discipline of the three E3 forward collectors
(:mod:`aionis.ingest.forward.stakes_13d_forward`,
:mod:`aionis.ingest.forward.macro_forward`,
:mod:`aionis.ingest.forward.earnings_8k_forward`):

  * **I3** — every emitted row has ``event_ts <= snapshot_ts`` (the monotonic-
    forward clock / leakage gate), and a row that violates it raises.
  * **idempotency** — a re-freeze of the SAME ``snapshot_ts`` appends no
    duplicate parquet rows and leaves the raw archive sha256 bit-stable.
  * **cumulative preserve** — a LATER ``snapshot_ts`` appends new rows while
    preserving prior rows (no overwrite — forward-only, no backfill).
  * **ledger row** — one ``data_ingest`` row per freeze carrying
    ``forward_only: true`` + ``snapshot_ts``, written under a TEMP ``runs_dir``
    (NEVER the real ``runs/ledger.jsonl``).

No real HTTP: the EDGAR fetch boundary is monkeypatched with labeled synthetic
fixtures (clearly fixture, not real data); the ALFRED boundary is served from a
written cache file (macro_surprise's own no-network cache-hit path).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from aionis.ingest.forward import _common, earnings_8k_forward, macro_forward, stakes_13d_forward

CIK_ANSS = 1098  # synthetic fixture CIK (labels a labeled fixture, not a real pull)


# ---------------------------------------------------------------------------
# synthetic EDGAR submissions fixture builder (clearly fixture, not real data)
# ---------------------------------------------------------------------------


def _submissions(recent_rows: list[tuple], items: list[str] | None = None) -> dict:
    """Build a labeled synthetic EDGAR ``submissions_{cik}.json`` payload.

    ``recent_rows`` = list of ``(form, filingDate, accessionNumber)`` triples.
    ``items`` = optional parallel list of item-strings (one per filing); when
    omitted, an empty items list is emitted (the field EDGAR normally populates).
    """
    n = len(recent_rows)
    payload = {
        "cik": str(CIK_ANSS),
        "sic": "7372",
        "sicDescription": "FIXTURE SIC (synthetic)",
        "filings": {
            "recent": {
                "form": [r[0] for r in recent_rows],
                "filingDate": [r[1] for r in recent_rows],
                "accessionNumber": [r[2] for r in recent_rows],
                "primaryDocument": ["d.htm"] * n,
                "items": items if items is not None else [""] * n,
            },
            "files": [],
        },
    }
    return payload


def _patch_submissions_fetch(
    monkeypatch: pytest.MonkeyPatch, payload: dict
) -> list[str]:
    """Patch ``stakes_13d.fetch_submissions`` to serve ``payload`` (no network).

    Returns the call log so tests can assert the fetch boundary (not real HTTP)
    was used. Both the 13D and 8-K forward collectors reuse this fetch seam."""
    calls: list[int] = []

    def _fake_fetch(cik: int, cache_dir: Path | None = None, **kw: object) -> dict:
        calls.append(cik)
        return payload

    monkeypatch.setattr(
        "aionis.ingest.stakes_13d.fetch_submissions", _fake_fetch
    )
    monkeypatch.setattr(
        "aionis.ingest.forward.stakes_13d_forward.stakes_13d.fetch_submissions",
        _fake_fetch,
    )
    monkeypatch.setattr(
        "aionis.ingest.forward.earnings_8k_forward.stakes_13d.fetch_submissions",
        _fake_fetch,
    )
    return calls


def _patch_cik_map(monkeypatch: pytest.MonkeyPatch, tkr_to_cik: dict[str, int]) -> None:
    """Patch ``fundamentals.cik_map`` to serve a fixture map (no network)."""
    monkeypatch.setattr(
        "aionis.ingest.fundamentals.cik_map",
        lambda cache_dir=None: dict(tkr_to_cik),
    )
    monkeypatch.setattr(
        "aionis.ingest.forward.earnings_8k_forward.fundamentals.cik_map",
        lambda cache_dir=None: dict(tkr_to_cik),
    )


def _ledger_rows(runs_dir: Path) -> list[dict]:
    ledger = runs_dir / "ledger.jsonl"
    if not ledger.exists():
        return []
    return [
        json.loads(ln)
        for ln in ledger.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]


# ===========================================================================
# shared I3 gate (the leakage clock) — tested directly on the mechanism
# ===========================================================================


def test_assert_forward_clock_passes_when_all_events_le_snapshot(
    tmp_path: Path,
) -> None:
    df = pd.DataFrame({"event_ts": ["2024-03-10", "2024-03-15", "2024-03-31"]})
    # snapshot at end-of-day on the 31st -> all three filing dates are <= it.
    _common.assert_forward_clock(df, "event_ts", "2024-03-31T20:00:00+00:00")  # no raise


def test_assert_forward_clock_raises_on_future_event(tmp_path: Path) -> None:
    df = pd.DataFrame({"event_ts": ["2024-03-15", "2024-04-15"]})  # Apr 15 is future
    with pytest.raises(RuntimeError, match="I3 forward-clock violation"):
        _common.assert_forward_clock(df, "event_ts", "2024-03-31T20:00:00+00:00")


def test_assert_forward_clock_raises_on_missing_event_ts(tmp_path: Path) -> None:
    df = pd.DataFrame({"event_ts": ["2024-03-15", None]})  # NaT -> unanchorable
    with pytest.raises(RuntimeError, match="I3 forward-clock violation"):
        _common.assert_forward_clock(df, "event_ts", "2024-03-31T20:00:00+00:00")


# ===========================================================================
# collector 1 — 13D forward
# ===========================================================================


def _ciks_fixture() -> dict[str, int]:
    return {"ANSS": CIK_ANSS}


def test_13d_forward_emits_only_filings_le_snapshot_ts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """I3: every emitted 13D row has event_ts (filing_date) <= snapshot_ts."""
    # FIXTURE: one filing before snapshot, one AFTER (future — must be filtered).
    recent = [
        ("SC 13D", "2024-03-15", "0000001098-24-000001"),  # in window
        ("SC 13D", "2024-04-20", "0000001098-24-000099"),  # AFTER snapshot_ts -> drop
        ("SC 13G", "2024-03-10", "0000001098-24-000002"),  # passive -> drop (not 13D)
    ]
    _patch_submissions_fetch(monkeypatch, _submissions(recent))

    frame = stakes_13d_forward.collect_13d_forward(
        _ciks_fixture(),
        snapshot_ts="2024-03-31T20:00:00+00:00",
        last_poll_ts=None,
        cache_dir=tmp_path,
        runs_dir=tmp_path,
    )
    # only the in-window SC 13D survives.
    assert len(frame) == 1
    assert (frame["event_ts"] <= "2024-03-31T20:00:00+00:00").all()
    assert (frame["ticker"] == "ANSS").all()
    assert (frame["form"] == "SC 13D").all()
    assert (frame["feature"] == "stake_13d_filing").all()


def test_13d_forward_idempotent_rerun_no_dup_rows_stable_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Idempotency: re-freezing the SAME snapshot_ts appends no dup rows and
    leaves the raw archive sha256 bit-stable."""
    recent = [("SC 13D", "2024-03-15", "0000001098-24-000001")]
    _patch_submissions_fetch(monkeypatch, _submissions(recent))

    snap = "2024-03-31T20:00:00+00:00"
    stakes_13d_forward.collect_13d_forward(
        _ciks_fixture(), snapshot_ts=snap, cache_dir=tmp_path, runs_dir=tmp_path
    )
    raw_path = tmp_path / f"{stakes_13d_forward.DATASET}_raw_20240331T2000000000.json"
    assert raw_path.exists()
    sha1 = _common.sha256_bytes(raw_path)
    rows_after_first = len(pd.read_parquet(tmp_path / f"{stakes_13d_forward.DATASET}.parquet"))

    # re-freeze the SAME snapshot_ts
    stakes_13d_forward.collect_13d_forward(
        _ciks_fixture(), snapshot_ts=snap, cache_dir=tmp_path, runs_dir=tmp_path
    )
    sha2 = _common.sha256_bytes(raw_path)
    rows_after_second = len(pd.read_parquet(tmp_path / f"{stakes_13d_forward.DATASET}.parquet"))

    assert sha1 == sha2  # raw archive bit-stable
    assert rows_after_first == rows_after_second == 1  # no duplicate rows


def test_13d_forward_cumulative_parquet_preserves_prior_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cumulative preserve: a LATER snapshot appends new rows; priors survive."""
    # T1: one filing; T2: a DIFFERENT filing (the prior one is excluded by the
    # forward window last_poll_ts, but the cumulative parquet must still hold it).
    monkeypatch.setattr(
        "aionis.ingest.forward.stakes_13d_forward.stakes_13d.fetch_submissions",
        lambda cik, cache_dir=None, **kw: _submissions(
            [
                ("SC 13D", "2024-03-15", "0000001098-24-000001"),  # collected at T1
                ("SC 13D", "2024-04-20", "0000001098-24-000002"),  # collected at T2
            ]
        ),
    )
    t1 = "2024-03-31T20:00:00+00:00"
    t2 = "2024-04-30T20:00:00+00:00"
    stakes_13d_forward.collect_13d_forward(
        _ciks_fixture(), snapshot_ts=t1, last_poll_ts=None,
        cache_dir=tmp_path, runs_dir=tmp_path,
    )
    stakes_13d_forward.collect_13d_forward(
        _ciks_fixture(), snapshot_ts=t2, last_poll_ts=t1,
        cache_dir=tmp_path, runs_dir=tmp_path,
    )
    cum = pd.read_parquet(tmp_path / f"{stakes_13d_forward.DATASET}.parquet")
    assert len(cum) == 2  # both snapshots' rows preserved (no overwrite)
    assert set(cum["snapshot_ts"]) == {t1, t2}
    # the T1 row (filing 2024-03-15) survived the T2 freeze.
    assert (cum["filing_date"] == "2024-03-15").any()


def test_13d_forward_ledger_row_has_forward_only_and_snapshot_ts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recent = [("SC 13D", "2024-03-15", "0000001098-24-000001")]
    _patch_submissions_fetch(monkeypatch, _submissions(recent))
    stakes_13d_forward.collect_13d_forward(
        _ciks_fixture(), snapshot_ts="2024-03-31T20:00:00+00:00",
        cache_dir=tmp_path, runs_dir=tmp_path,
    )
    ingest_rows = [r for r in _ledger_rows(tmp_path) if r.get("event") == "data_ingest"]
    assert len(ingest_rows) == 1  # idempotent: one row per freeze
    row = ingest_rows[0]
    assert row["dataset"] == stakes_13d_forward.DATASET
    assert row["forward_only"] is True
    assert row["snapshot_ts"] == "2024-03-31T20:00:00+00:00"
    assert row["data_sha256"]  # non-empty
    # the real ledger is untouched — covered explicitly by test_real_ledger_jsonl_untouched.


# ===========================================================================
# collector 2 — macro forward (ALFRED cache-hit, no network)
# ===========================================================================


def _alfred_obs(ref: str, pub: str, value: float) -> dict:
    """One ALFRED observation row (FRED serializes values as strings)."""
    return {
        "date": pd.Timestamp(ref).strftime("%Y-%m-%d"),
        "realtime_start": pd.Timestamp(pub).strftime("%Y-%m-%d"),
        "value": str(value),
    }


def _write_alfred_cache(cache_dir: Path, series_id: str, rows: list[dict]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"alfred_{series_id}.json").write_text(
        json.dumps({"observations": rows})
    )


def test_macro_forward_emits_only_releases_le_snapshot_ts(
    tmp_path: Path,
) -> None:
    """I3: every emitted macro row has event_ts (pub_date) <= snapshot_ts."""
    # FIXTURE: CPI vintages — first-print per ref month, one pub AFTER snapshot.
    # Ref months are month-starts; realtime_start is the publication date.
    rows = [
        _alfred_obs("2023-10-01", "2023-11-01", 300.0),  # pub 2023-11-01 (old, pre-window base)
        _alfred_obs("2023-11-01", "2023-12-01", 301.0),  # pub 2023-12-01 (in window)
        _alfred_obs("2023-12-01", "2024-02-01", 302.0),  # pub 2024-02-01 (AFTER snapshot -> drop)
        # enough history for the trailing expectation/z windows to be non-NaN
        _alfred_obs("2023-09-01", "2023-10-01", 299.0),
        _alfred_obs("2023-08-01", "2023-09-01", 298.0),
        _alfred_obs("2023-07-01", "2023-08-01", 297.0),
        _alfred_obs("2023-06-01", "2023-07-01", 296.0),
        _alfred_obs("2023-05-01", "2023-06-01", 295.0),
        _alfred_obs("2023-04-01", "2023-05-01", 294.0),
        _alfred_obs("2023-03-01", "2023-04-01", 293.0),
        _alfred_obs("2023-02-01", "2023-03-01", 292.0),
        _alfred_obs("2023-01-01", "2023-02-01", 291.0),
        _alfred_obs("2022-12-01", "2023-01-01", 290.0),
        _alfred_obs("2022-11-01", "2022-12-01", 289.0),
        _alfred_obs("2022-10-01", "2022-11-01", 288.0),
    ]
    _write_alfred_cache(tmp_path, "CPIAUCSL", rows)
    # also need PAYEMS (NFP) cache since the collector iterates both series.
    _write_alfred_cache(tmp_path, "PAYEMS", rows)

    frame = macro_forward.collect_macro_forward(
        snapshot_ts="2024-01-15T13:30:00+00:00",  # cutoff: drops the 2024-02-01 pub
        last_poll_ts=None,
        fred_api_key="fixture-key",
        cache_dir=tmp_path,
        runs_dir=tmp_path,
    )
    assert not frame.empty
    # I3: every event_ts (pub_date) <= snapshot_ts.
    ev = pd.to_datetime(frame["event_ts"], utc=True)
    assert (ev <= pd.Timestamp("2024-01-15T13:30:00Z")).all()
    # the 2024-02-01 publication was filtered out (future).
    assert not (frame["pub_date"] == "2024-02-01").any()


def _macro_fixture_rows() -> list[dict]:
    """A reusable ~12-month labeled ALFRED fixture (one first-print vintage per month).

    ``realtime_start`` (publication) is ~1 month after the reference month-start,
    rolled correctly across the Dec->Jan year boundary via ``pd.DateOffset`` (the
    prior ``f"2023-{m + 1:02d}-01"`` form produced the invalid ``2023-13-01``).
    """
    rows: list[dict] = []
    for m in range(1, 13):
        ref = pd.Timestamp(f"2023-{m:02d}-01")
        pub = ref + pd.DateOffset(months=1)
        rows.append(_alfred_obs(ref.strftime("%Y-%m-%d"), pub.strftime("%Y-%m-%d"), 300.0 + m))
    return rows


def test_macro_forward_ledger_row_forward_only_and_snapshot_ts(
    tmp_path: Path,
) -> None:
    rows = _macro_fixture_rows()
    _write_alfred_cache(tmp_path, "CPIAUCSL", rows)
    _write_alfred_cache(tmp_path, "PAYEMS", rows)
    macro_forward.collect_macro_forward(
        snapshot_ts="2024-01-15T13:30:00+00:00", fred_api_key="fixture-key",
        cache_dir=tmp_path, runs_dir=tmp_path,
    )
    ingest_rows = [r for r in _ledger_rows(tmp_path) if r.get("event") == "data_ingest"]
    assert len(ingest_rows) == 1
    assert ingest_rows[0]["forward_only"] is True
    assert ingest_rows[0]["snapshot_ts"] == "2024-01-15T13:30:00+00:00"


def test_macro_forward_idempotent_rerun_stable_sha(
    tmp_path: Path,
) -> None:
    rows = _macro_fixture_rows()
    _write_alfred_cache(tmp_path, "CPIAUCSL", rows)
    _write_alfred_cache(tmp_path, "PAYEMS", rows)
    snap = "2024-01-15T13:30:00+00:00"
    macro_forward.collect_macro_forward(
        snapshot_ts=snap, fred_api_key="fixture-key", cache_dir=tmp_path, runs_dir=tmp_path
    )
    raw_path = tmp_path / f"{macro_forward.DATASET}_raw_20240115T1330000000.json"
    sha1 = _common.sha256_bytes(raw_path)
    n1 = len(pd.read_parquet(tmp_path / f"{macro_forward.DATASET}.parquet"))
    macro_forward.collect_macro_forward(
        snapshot_ts=snap, fred_api_key="fixture-key", cache_dir=tmp_path, runs_dir=tmp_path
    )
    sha2 = _common.sha256_bytes(raw_path)
    n2 = len(pd.read_parquet(tmp_path / f"{macro_forward.DATASET}.parquet"))
    assert sha1 == sha2
    assert n1 == n2


# ===========================================================================
# collector 3 — 8-K Item 2.02 forward (NET-NEW form-type filter)
# ===========================================================================


def test_8k_forward_keeps_only_8k_with_item_2_02_le_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Form-type filter + I3: only 8-K filings reporting Item 2.02, filed <= snapshot_ts."""
    recent = [
        ("8-K", "2024-03-10", "0000001098-24-000010"),  # 8-K w/ Item 2.02 -> KEEP
        ("8-K", "2024-03-12", "0000001098-24-000011"),  # 8-K w/o Item 2.02 -> drop
        ("8-K", "2024-04-25", "0000001098-24-000012"),  # 8-K Item 2.02 but FUTURE -> drop
        ("10-K", "2024-03-15", "0000001098-24-000013"),  # not 8-K -> drop
    ]
    items = [
        "Item 2.02 Results of Operations,Item 9.01",
        "Item 9.01",               # no 2.02
        "Item 2.02",               # future-dated -> filtered by PIT window
        "",                         # 10-K has no items
    ]
    _patch_submissions_fetch(monkeypatch, _submissions(recent, items=items))
    _patch_cik_map(monkeypatch, {"ANSS": CIK_ANSS})

    frame = earnings_8k_forward.collect_8k_forward(
        ["ANSS"], snapshot_ts="2024-03-31T20:00:00+00:00",
        cache_dir=tmp_path, runs_dir=tmp_path,
    )
    assert len(frame) == 1  # only the in-window 8-K Item 2.02
    assert (frame["form"] == "8-K").all()
    assert (frame["feature"] == "earnings_8k_item_2_02").all()
    assert (frame["event_ts"] <= "2024-03-31T20:00:00+00:00").all()
    assert (frame["accession"] == "0000001098-24-000010").all()


def test_8k_forward_item_filter_is_word_boundary_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Item 2.02 regex must NOT match 2.020 / 12.02 / 2.02-adjacent noise."""
    recent = [
        ("8-K", "2024-03-10", "a-1"),  # "Item 2.020" -> must NOT match
        ("8-K", "2024-03-11", "a-2"),  # "Item 12.02" -> must NOT match
        ("8-K", "2024-03-12", "a-3"),  # "Item 2.02"  -> matches
    ]
    items = ["Item 2.020 Financial Statements", "Item 12.02", "Item 2.02"]
    _patch_submissions_fetch(monkeypatch, _submissions(recent, items=items))
    _patch_cik_map(monkeypatch, {"ANSS": CIK_ANSS})

    frame = earnings_8k_forward.collect_8k_forward(
        ["ANSS"], snapshot_ts="2024-03-31T20:00:00+00:00",
        cache_dir=tmp_path, runs_dir=tmp_path,
    )
    assert len(frame) == 1
    assert (frame["accession"] == "a-3").all()


def test_8k_forward_idempotent_and_cumulative_preserve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Idempotency + cumulative-preserve for the net-new 8-K collector."""
    monkeypatch.setattr(
        "aionis.ingest.forward.earnings_8k_forward.stakes_13d.fetch_submissions",
        lambda cik, cache_dir=None, **kw: _submissions(
            [("8-K", "2024-03-10", "a-t1")], items=["Item 2.02"]
        ),
    )
    _patch_cik_map(monkeypatch, {"ANSS": CIK_ANSS})
    t1 = "2024-03-31T20:00:00+00:00"
    earnings_8k_forward.collect_8k_forward(
        ["ANSS"], snapshot_ts=t1, cache_dir=tmp_path, runs_dir=tmp_path
    )
    n1 = len(pd.read_parquet(tmp_path / f"{earnings_8k_forward.DATASET}.parquet"))
    # re-freeze SAME snapshot -> idempotent
    earnings_8k_forward.collect_8k_forward(
        ["ANSS"], snapshot_ts=t1, cache_dir=tmp_path, runs_dir=tmp_path
    )
    n1b = len(pd.read_parquet(tmp_path / f"{earnings_8k_forward.DATASET}.parquet"))
    assert n1 == n1b == 1

    # T2: a new 8-K Item 2.02 filing appears in the window.
    monkeypatch.setattr(
        "aionis.ingest.forward.earnings_8k_forward.stakes_13d.fetch_submissions",
        lambda cik, cache_dir=None, **kw: _submissions(
            [("8-K", "2024-03-10", "a-t1"), ("8-K", "2024-04-22", "a-t2")],
            items=["Item 2.02", "Item 2.02"],
        ),
    )
    t2 = "2024-04-30T20:00:00+00:00"
    earnings_8k_forward.collect_8k_forward(
        ["ANSS"], snapshot_ts=t2, last_poll_ts=t1, cache_dir=tmp_path, runs_dir=tmp_path
    )
    cum = pd.read_parquet(tmp_path / f"{earnings_8k_forward.DATASET}.parquet")
    assert len(cum) == 2  # T1 row preserved + T2 row appended
    assert set(cum["snapshot_ts"]) == {t1, t2}


def test_8k_forward_ledger_row_forward_only_and_snapshot_ts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_submissions_fetch(
        monkeypatch,
        _submissions([("8-K", "2024-03-10", "a-1")], items=["Item 2.02"]),
    )
    _patch_cik_map(monkeypatch, {"ANSS": CIK_ANSS})
    earnings_8k_forward.collect_8k_forward(
        ["ANSS"], snapshot_ts="2024-03-31T20:00:00+00:00",
        cache_dir=tmp_path, runs_dir=tmp_path,
    )
    ingest_rows = [r for r in _ledger_rows(tmp_path) if r.get("event") == "data_ingest"]
    assert len(ingest_rows) == 1
    row = ingest_rows[0]
    assert row["dataset"] == earnings_8k_forward.DATASET
    assert row["forward_only"] is True
    assert row["snapshot_ts"] == "2024-03-31T20:00:00+00:00"
    assert row["data_sha256"]


def test_real_ledger_jsonl_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sanity: a forward freeze writes ONLY to the temp runs_dir, never the real
    ``runs/ledger.jsonl`` (which stays at its baseline 39 lines)."""
    real_ledger = Path("runs/ledger.jsonl")
    before = (
        len(real_ledger.read_text(encoding="utf-8").splitlines()) if real_ledger.exists() else 0
    )
    _patch_submissions_fetch(
        monkeypatch,
        _submissions([("SC 13D", "2024-03-15", "a-1")]),
    )
    stakes_13d_forward.collect_13d_forward(
        _ciks_fixture(), snapshot_ts="2024-03-31T20:00:00+00:00",
        cache_dir=tmp_path, runs_dir=tmp_path,
    )
    after = (
        len(real_ledger.read_text(encoding="utf-8").splitlines()) if real_ledger.exists() else 0
    )
    assert before == after == 39
