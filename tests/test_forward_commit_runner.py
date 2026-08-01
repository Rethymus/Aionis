"""E3 Slice 3e - the standalone forward-commit runner (scripts/forward_commit.py).

TDD: these tests FAIL until ``scripts/forward_commit.py`` exists and wires the
Slice-3c freeze -> Slice-3d commit step end-to-end, mirroring
``scripts/phase_e1_run.py``. Hermetic: collectors monkeypatched (no network),
GLM provider + extra-features builder monkeypatched, panels injected via the
``_assemble_panels`` seam, all paths under tmp dirs.

Scope (plan §3 sub-slice 3e):
  * freeze -> commit ORDER in the tmp ledger (forward_iset_frozen precedes
    forward_prediction_committed);
  * PHASE_E3_NO_LEDGER=1 -> 0 forward rows but the sig is still computed;
  * predict_ts is the NYSE month-end session close;
  * refuses without an enabled GLM provider (no commit row);
  * the real runs/ledger.jsonl is untouched.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aionis.eval import forward_commit as FC
from aionis.eval import forward_commit_runner as RUN  # importable runner logic
from aionis.eval import forward_freeze as FF
from aionis.features.alignment import nyse_sessions, session_close_ts

PHASE = "E3"


# ---------------------------------------------------------------------------
# SYNTHETIC fixtures (labeled - no real data, no network)
# ---------------------------------------------------------------------------


def _synth_panel(
    n_dates: int = 30, n_tickers: int = 6, seed: int = 0, with_extra: bool = False,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = [d.normalize() for d in pd.bdate_range("2026-01-05", periods=n_dates)]
    tickers = [f"T{i}" for i in range(n_tickers)]
    rows: list[dict] = []
    for d in dates:
        for t in tickers:
            row: dict = {"date": d, "ticker": t, "y_fwd_ret": float(rng.normal(0.0, 0.01))}
            for c in FC.FEATURE_COLS:
                row[c] = float(rng.normal(0.0, 1.0))
            if with_extra:
                for c in FC.FORWARD_EXTRA_COLS:
                    row[c] = float("nan")
            rows.append(row)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df.sort_values(["date", "ticker"]).reset_index(drop=True)


def _synth_extra(panel: pd.DataFrame) -> pd.DataFrame:
    """A long extra-features frame keyed on the panel's own (date, ticker) grid."""
    cols = list(FC.FORWARD_EXTRA_COLS)
    base = panel[["date", "ticker"]].copy()
    rng = np.random.default_rng(42)
    for c in cols:
        base[c] = rng.normal(0.0, 1.0, size=len(base))
    return base


def _fund_stub() -> pd.DataFrame:
    return pd.DataFrame(columns=["ticker", "metric", "value", "filed"])


def _px_stub() -> pd.DataFrame:
    idx = pd.bdate_range("2026-01-05", periods=5)
    return pd.DataFrame({"T0": 1.0, "T1": 2.0}, index=idx)


def _mem_stub() -> pd.DataFrame:
    """Stub membership with tickers matching the test panel (T0-T5)."""
    dates = pd.bdate_range("2026-01-05", periods=10)
    tickers = [f"T{i}" for i in range(6)]  # T0-T5 to match _synth_panel
    rows = []
    for d in dates:
        for t in tickers:
            rows.append({"date": d.normalize(), "ticker": t})
    return pd.DataFrame(rows)


def _sic_stub() -> pd.DataFrame:
    return pd.DataFrame({"ticker": ["T0", "T1"], "sic": ["7370", "6021"]})


def _patch_runner(
    monkeypatch: pytest.MonkeyPatch,
    *,
    glm_enabled: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Monkeypatch the runner's external seams. Returns (panel_base, panel_e13)."""
    panel_base = _synth_panel(with_extra=False)
    panel_e13 = _synth_panel(with_extra=True)

    # I6: pinned provider resolution
    class _P:
        def __init__(self, name: str) -> None:
            self.name = name
            self.base_url = "http://x"
            self.api_key = "k"
            self.model = "glm-4-flash"

    providers = [_P("glm")] if glm_enabled else [_P("siliconflow")]
    monkeypatch.setattr(FC, "build_providers", lambda only_enabled=True: providers)

    # collectors -> tiny frames, write the sealed raw archive (so freeze's re-read works)
    from aionis.ingest.forward import _common
    from aionis.ingest.forward.earnings_8k_forward import DATASET as EARNINGS_DATASET
    from aionis.ingest.forward.macro_forward import DATASET as MACRO_DATASET
    from aionis.ingest.forward.stakes_13d_forward import DATASET as STAKES_DATASET

    def _macro(*, snapshot_ts, last_poll_ts, fred_api_key, cache_dir, runs_dir):  # type: ignore[no-untyped-def]
        snap = _common.canonical_snapshot_ts(snapshot_ts)
        cdir = _common.cache_dir(cache_dir)
        frame = pd.DataFrame([
            {"series_id": "CPIAUCSL", "event_type": "CPI", "pub_date": "2026-07-15",
             "surprise_z": 0.3, "value": 0.3, "event_ts": "2026-07-15",
             "snapshot_ts": snap, "feature": "m", "ref_date": "2026-07-15"},
        ])
        _common.archive_raw(cdir, MACRO_DATASET, snap, frame.to_dict("records"))
        return frame

    def _stakes(ciks, *, snapshot_ts, last_poll_ts, cache_dir, runs_dir):  # type: ignore[no-untyped-def]
        snap = _common.canonical_snapshot_ts(snapshot_ts)
        cdir = _common.cache_dir(cache_dir)
        frame = pd.DataFrame([
            {"ticker": "T0", "cik": 1, "feature": "stake_13d_filing", "value": 1.0,
             "form": "SC 13D", "filing_date": "2026-07-10", "accession": "0001",
             "event_ts": "2026-07-10", "snapshot_ts": snap},
        ])
        _common.archive_raw(cdir, STAKES_DATASET, snap, frame.to_dict("records"))
        return frame

    def _earnings(tickers, *, snapshot_ts, last_poll_ts, cache_dir, runs_dir):  # type: ignore[no-untyped-def]
        snap = _common.canonical_snapshot_ts(snapshot_ts)
        cdir = _common.cache_dir(cache_dir)
        frame = pd.DataFrame([
            {"ticker": "T0", "cik": 1, "feature": "earnings_8k_item_2_02", "value": 1.0,
             "form": "8-K", "filing_date": "2026-07-12", "accession": "0003",
             "items": "Item 2.02", "event_ts": "2026-07-12", "snapshot_ts": snap},
        ])
        _common.archive_raw(cdir, EARNINGS_DATASET, snap, frame.to_dict("records"))
        return frame

    monkeypatch.setattr(FF, "collect_macro_forward", _macro)
    monkeypatch.setattr(FF, "collect_13d_forward", _stakes)
    monkeypatch.setattr(FF, "collect_8k_forward", _earnings)

    # data loading + LLM client construction -> no real cache / no openai construction
    monkeypatch.setattr(
        RUN, "_load_inputs",
        lambda cache: (_fund_stub(), _px_stub(), _mem_stub(), _sic_stub(), {}),
    )
    monkeypatch.setattr(RUN, "_build_llm_client", lambda provider: None)

    # Pass-A extra-features builder -> tiny long frame (no LLM call)
    monkeypatch.setattr(RUN, "build_forward_extra_features",
                        lambda **kw: _synth_extra(panel_e13))

    # the heavy PIT panel assembly -> inject tiny prebuilt panels
    monkeypatch.setattr(RUN, "_assemble_panels",
                        lambda *a, **k: (panel_base.copy(), panel_e13.copy()))
    return panel_base, panel_e13


def _ledger_rows(runs_dir: Path) -> list[dict]:
    ledger = runs_dir / "ledger.jsonl"
    if not ledger.exists():
        return []
    return [json.loads(ln) for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _forward_rows(runs_dir: Path) -> list[dict]:
    return [r for r in _ledger_rows(runs_dir) if str(r.get("event", "")).startswith("forward_")]


# ---------------------------------------------------------------------------
# predict_ts = NYSE month-end session close
# ---------------------------------------------------------------------------


def test_predict_session_is_nyse_month_end() -> None:
    """The predict session is the LAST NYSE session of the current month."""
    sess = RUN._nyse_month_end_session(pd.Timestamp("2026-07-15"))
    assert sess == pd.Timestamp("2026-07-31")  # Friday, last NYSE session of July 2026
    # it is itself an NYSE session
    grid = nyse_sessions(pd.Timestamp("2026-07-01"), pd.Timestamp("2026-07-31"))
    assert sess in set(grid)


def test_predict_ts_is_session_close_of_month_end() -> None:
    """predict_ts is the 16:00 ET close wall-clock of the month-end session."""
    sess = RUN._nyse_month_end_session(pd.Timestamp("2026-07-15"))
    pts = RUN._predict_ts(pd.Timestamp("2026-07-15"))
    assert pts == session_close_ts(sess).isoformat()


# ---------------------------------------------------------------------------
# freeze -> commit ORDER in the tmp ledger
# ---------------------------------------------------------------------------


def test_runner_freeze_then_commit_order_in_tmp_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LIVE: forward_iset_frozen is appended BEFORE forward_prediction_committed."""
    _patch_runner(monkeypatch)
    res = RUN.main(runs_dir=tmp_path, today=pd.Timestamp("2026-07-15"))
    assert res["committed"] is True
    rows = _forward_rows(tmp_path)
    events = [r["event"] for r in rows]
    assert "forward_iset_frozen" in events
    assert "forward_prediction_committed" in events
    # iset_frozen line precedes the commit line (append order)
    assert events.index("forward_iset_frozen") < events.index("forward_prediction_committed")


# ---------------------------------------------------------------------------
# PHASE_E3_NO_LEDGER=1 -> 0 forward rows but sig computed
# ---------------------------------------------------------------------------


def test_runner_no_ledger_writes_zero_rows_but_computes_sig(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NO_LEDGER: no forward_* rows land in the ledger, but a scores sig is computed."""
    monkeypatch.setenv("PHASE_E3_NO_LEDGER", "1")
    _patch_runner(monkeypatch)
    res = RUN.main(runs_dir=tmp_path, today=pd.Timestamp("2026-07-15"))
    assert res["committed"] is False
    assert len(res["scores_sha256"]) == 64  # sig computed
    assert _forward_rows(tmp_path) == []     # zero forward rows


# ---------------------------------------------------------------------------
# refuses without GLM (no commit row)
# ---------------------------------------------------------------------------


def test_runner_refuses_without_glm_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """I6: with no enabled glm provider, main() refuses BEFORE any commit row."""
    _patch_runner(monkeypatch, glm_enabled=False)
    with pytest.raises(RuntimeError, match="glm"):
        RUN.main(runs_dir=tmp_path, cache_dir=tmp_path / "cache", today=pd.Timestamp("2026-07-15"))
    assert _forward_rows(tmp_path) == []  # no commit / iset row


# ---------------------------------------------------------------------------
# real-ledger hygiene
# ---------------------------------------------------------------------------


def test_runner_never_touches_real_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real runs/ledger.jsonl is unchanged by a live runner run."""
    real_ledger = Path(__file__).resolve().parents[1] / "runs" / "ledger.jsonl"
    before = real_ledger.read_bytes() if real_ledger.exists() else b""
    _patch_runner(monkeypatch)
    RUN.main(runs_dir=tmp_path, today=pd.Timestamp("2026-07-15"))
    after = real_ledger.read_bytes() if real_ledger.exists() else b""
    assert before == after
