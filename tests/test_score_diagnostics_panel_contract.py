"""Contract tests for the score-diagnostics panel (web/src/data/aionis/).

TASK-DISP-R1A: the /atlas diagnostics section renders this panel — a pure
descriptive-statistics derivation over the FROZEN confirmatory OOS score
cross-section (no returns join, no config, no ledger, no new research claim).

Hermetic checks: the synthetic parquet fixtures are built INSIDE these tests
and used only as test fixtures (the one mock-like data the repo rules allow);
exact-value pins on n / mean / std / IQR cross-validated against numpy, and an
exact rank-autocorrelation value cross-validated against a scipy-free
rank+Pearson implementation. The committed panel is reconciled against
ic_monthly.json — both derive from the same frozen score parquet, but the IC
series covers only months with a valid OOS return window, so the measured
relation (score-month coverage ⊇ IC-month coverage per region) is asserted as
measured on 2026-08-28, with the exact surplus months pinned.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

DATA = Path("web/src/data/aionis")
PANEL = DATA / "score_diagnostics.json"
sys.path.insert(0, str(Path("scripts").resolve()))
import export_quarto_data as eq  # noqa: E402
import export_terminal_data as et  # noqa: E402

# --- fixture machinery (labeled synthetic test fixtures) ----------------------


def _fx_df(rows: list[tuple[str, str, str, float]]) -> pd.DataFrame:
    """(month-end-ish date, ticker, region, score) rows -> parquet-shaped df."""
    return pd.DataFrame(
        [
            {"date": pd.Timestamp(d), "ticker": t, "region": r, "score": float(s)}
            for d, t, r, s in rows
        ]
    )


def _run_export(
    tmp_path, monkeypatch, df: pd.DataFrame
) -> list[dict]:
    runs = tmp_path / "runs"
    runs.mkdir()
    df.to_parquet(runs / "track_c_confirmatory_oos_scores.parquet", index=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(eq, "OUT", tmp_path)
    eq.export_score_diagnostics()
    return json.loads((tmp_path / "score_diagnostics.json").read_text())


def _rank(v) -> np.ndarray:
    """Average ranks (1-based), ties averaged — scipy-free, pandas-independent."""
    v = np.asarray(v, dtype=float)
    order = np.argsort(v, kind="mergesort")
    ranks = np.empty(len(v), dtype=float)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
            j += 1
        ranks[order[i : j + 1]] = (i + j + 2) / 2  # mean of 1-based ranks i+1..j+1
        i = j + 1
    return ranks


def _spearman(a, b) -> float:
    """Pearson on ranks — an independent second algorithm for cross-checks."""
    ra, rb = _rank(a), _rank(b)
    return float(np.corrcoef(ra, rb)[0, 1])


# --- exporter exact-value locks (synthetic fixtures) --------------------------


def test_export_exact_moments_and_iqr(tmp_path, monkeypatch) -> None:
    """n / mean / std(ddof=1) / IQR(linear) are exact; first month is null."""
    df = _fx_df(
        [
            ("2021-01-29", "a", "us", 1.0),
            ("2021-01-29", "b", "us", 2.0),
            ("2021-01-29", "c", "us", 3.0),
            ("2021-01-29", "d", "us", 4.0),
            ("2021-01-29", "x", "cn", 10.0),
            ("2021-01-29", "y", "cn", 20.0),
        ]
    )
    rows = _run_export(tmp_path, monkeypatch, df)
    assert len(rows) == 2
    # Sort contract: month asc, then region lexicographic ("cn" < "us").
    assert [(r["month"], r["region"]) for r in rows] == [
        ("2021-01", "cn"),
        ("2021-01", "us"),
    ]
    us = rows[1]
    vals = np.array([1.0, 2.0, 3.0, 4.0])
    assert us["n"] == 4
    assert us["score_mean"] == 2.5 == round(float(np.mean(vals)), 6)
    assert us["score_std"] == round(float(np.std(vals, ddof=1)), 6)
    assert us["score_std"] == pytest.approx(1.290994, abs=1e-6)
    assert us["score_iqr"] == 1.5 == round(
        float(np.percentile(vals, 75) - np.percentile(vals, 25)), 6
    )
    assert us["rank_autocorr"] is None, "first month of a region chain is null"


def test_export_rank_autocorr_exact_and_null_chain_breaks(
    tmp_path, monkeypatch
) -> None:
    """A known rank permutation gives the exact Spearman; degenerate -> null.

    Month 2 is month 1's ranking with one adjacent swap: for n=30 untied ranks
    Spearman = 1 - 6*sum(d^2)/(n^3-n) = 1 - 12/26970. Month 3 is perfectly
    reversed (-1). Month 4 is constant (zero variance -> undefined -> null).
    """
    tickers = [f"t{i:02d}" for i in range(30)]
    m1 = {t: float(i) for i, t in enumerate(tickers)}
    m2 = dict(m1)
    m2["t00"], m2["t01"] = m1["t01"], m1["t00"]  # one adjacent swap
    m3 = {t: -m2[t] for t in tickers}  # perfect reversal OF MONTH 2 -> -1.0
    m4 = {t: 5.0 for t in tickers}  # constant cross-section

    def month_rows(scores: dict[str, float], day: str) -> list[tuple]:
        return [("2021-0" + day, t, "us", s) for t, s in scores.items()]

    rows = _run_export(
        tmp_path,
        monkeypatch,
        _fx_df(
            month_rows(m1, "1")
            + month_rows(m2, "2")
            + month_rows(m3, "3")
            + month_rows(m4, "4")
        ),
    )
    assert [r["month"] for r in rows] == ["2021-01", "2021-02", "2021-03", "2021-04"]
    expected = round(1 - 6 * 2 / (30**3 - 30), 6)
    assert rows[0]["rank_autocorr"] is None
    assert rows[1]["rank_autocorr"] == expected == 0.999555
    # Independent scipy-free algorithm must agree on the same 6-rounded value.
    assert round(_spearman(list(m1.values()), list(m2.values())), 6) == expected
    assert rows[2]["rank_autocorr"] == -1.0
    assert rows[3]["rank_autocorr"] is None, "constant scores are honestly null"


def test_export_overlap_under_30_is_honest_null(tmp_path, monkeypatch) -> None:
    """Overlap < 30 names -> null; exactly 30 -> a real value."""
    m1 = {f"t{i:02d}": float(i) for i in range(50)}
    # Month 2 keeps only 29 of month 1's names (adds 21 new ones).
    m2 = {**{t: float(i) for i, t in enumerate(sorted(m1)[:29])},
          **{f"u{i:02d}": 100.0 + i for i in range(21)}}
    # Month 3 overlaps month 2 by exactly 30 names (adds 20 new ones).
    m3_old = {t: float(i) for i, t in enumerate(list(m2)[:30])}
    m3 = {**m3_old, **{f"v{i:02d}": 200.0 + i for i in range(20)}}

    def mk(scores: dict[str, float], month: str) -> list[tuple]:
        return [(month, t, "us", s) for t, s in scores.items()]

    rows = _run_export(
        tmp_path, monkeypatch, _fx_df(mk(m1, "2021-01") + mk(m2, "2021-02") + mk(m3, "2021-03"))
    )
    assert [r["month"] for r in rows] == ["2021-01", "2021-02", "2021-03"]
    assert rows[0]["rank_autocorr"] is None
    assert rows[1]["rank_autocorr"] is None, "29 overlapping names < 30 -> null"
    v = rows[2]["rank_autocorr"]
    assert isinstance(v, float), "30 overlapping names is enough to report"
    assert -1.0 <= v <= 1.0


def test_export_region_chains_independent_across_gap_months(
    tmp_path, monkeypatch
) -> None:
    """Each region chains against ITS OWN previous with-data month.

    CN skips 2021-02, so CN's 2021-03 autocorrelation must be computed against
    CN's 2021-01 (perfect rank preservation here -> exactly 1.0), never against
    another region's cross-section (no shared tickers -> would be null).
    """
    us_t = [f"u{i:02d}" for i in range(30)]
    cn_t = [f"c{i:02d}" for i in range(30)]
    rows_in = (
        [("2021-01-29", t, "us", float(i)) for i, t in enumerate(us_t)]
        + [("2021-01-29", t, "cn", float(i)) for i, t in enumerate(cn_t)]
        + [("2021-02-26", t, "us", float(29 - i)) for i, t in enumerate(us_t)]
        + [("2021-03-31", t, "us", float(i)) for i, t in enumerate(us_t)]
        + [("2021-03-31", t, "cn", 2.0 * float(i)) for i, t in enumerate(cn_t)]
    )
    rows = _run_export(tmp_path, monkeypatch, _fx_df(rows_in))
    keys = [(r["month"], r["region"]) for r in rows]
    assert keys == sorted(keys)
    assert ("2021-02", "cn") not in keys, "months without data are not fabricated"
    by = {(r["month"], r["region"]): r for r in rows}
    assert by[("2021-01", "cn")]["rank_autocorr"] is None
    assert by[("2021-03", "cn")]["rank_autocorr"] == 1.0, (
        "CN 2021-03 chains against CN 2021-01 (previous CN with-data month)"
    )
    assert by[("2021-02", "us")]["rank_autocorr"] == -1.0
    assert by[("2021-03", "us")]["rank_autocorr"] == -1.0, (
        "US 2021-03 (identity) vs US 2021-02 (reversed) — chained, not reset"
    )


def test_export_rounds_to_six_decimals(tmp_path, monkeypatch) -> None:
    """All reported floats carry the byte-stability rounding (6 dp)."""
    scores = [0.1, 0.1, 0.2]
    df = _fx_df([("2021-01-29", t, "us", s) for t, s in zip("abc", scores, strict=True)])
    rows = _run_export(tmp_path, monkeypatch, df)
    r = rows[0]
    assert r["score_mean"] == round(float(np.mean(scores)), 6) == 0.133333
    assert r["score_std"] == round(float(np.std(scores, ddof=1)), 6)
    assert r["score_iqr"] == round(
        float(np.percentile(scores, 75) - np.percentile(scores, 25)), 6
    )
    for row in rows:
        for k in ("score_mean", "score_std", "score_iqr"):
            assert row[k] == round(float(row[k]), 6)


# --- committed panel (tracked JSON, generated from the REAL frozen parquet) ---


def _load() -> list[dict]:
    return json.loads(PANEL.read_text(encoding="utf-8"))


FIELDS = {"month", "region", "n", "score_mean", "score_std", "score_iqr",
          "rank_autocorr"}


def test_score_diagnostics_panel_shape() -> None:
    """Field contract, region whitelist, sort contract, honest null policy."""
    rows = _load()
    assert len(rows) == 134, "measured 2026-08-28: 134 (month, region) groups"
    months = []
    for r in rows:
        assert set(r) == FIELDS, r
        assert r["region"] in {"us", "cn"}, r["region"]
        assert re.fullmatch(r"\d{4}-\d{2}", r["month"]), r["month"]
        assert isinstance(r["n"], int) and r["n"] >= 1, r
        for k in ("score_mean", "score_std", "score_iqr"):
            assert isinstance(r[k], (int, float)) and np.isfinite(r[k]), (k, r)
        ac = r["rank_autocorr"]
        assert ac is None or (isinstance(ac, (int, float)) and -1.0 <= ac <= 1.0), r
        months.append(r["month"])
    keys = [(r["month"], r["region"]) for r in rows]
    assert keys == sorted(keys), "rows must be month-asc, region-lexicographic"
    assert len(set(keys)) == len(keys), "no duplicate (month, region)"
    assert months[0] == "2021-01" and months[-1] == "2026-08"
    # Honest nulls: ONLY each region chain's first month (measured).
    nulls = {(r["month"], r["region"]) for r in rows if r["rank_autocorr"] is None}
    assert nulls == {("2021-01", "cn"), ("2021-01", "us")}


def test_score_diagnostics_panel_measured_pins() -> None:
    """Values pinned as measured on 2026-08-28 from the frozen parquet.

    These are descriptive statistics of the frozen score surface — they pin the
    committed panel against silent drift, they do not assert any research claim.
    """
    rows = _load()
    us = [r for r in rows if r["region"] == "us"]
    cn = [r for r in rows if r["region"] == "cn"]
    assert (len(us), len(cn)) == (66, 68)
    assert us[0]["month"] == "2021-01" and us[-1]["month"] == "2026-06"
    assert cn[0]["month"] == "2021-01" and cn[-1]["month"] == "2026-08"
    acs = [r["rank_autocorr"] for r in rows if r["rank_autocorr"] is not None]
    assert len(acs) == 132
    assert min(acs) == 0.194064
    assert max(acs) == 0.938698
    ns = [r["n"] for r in rows]
    assert min(ns) == 446 and max(ns) == 929
    widest_std = max(rows, key=lambda r: r["score_std"])
    assert (widest_std["month"], widest_std["region"], widest_std["score_std"]) == (
        "2021-11",
        "us",
        1.001488,
    )
    widest_iqr = max(rows, key=lambda r: r["score_iqr"])
    assert (widest_iqr["month"], widest_iqr["region"], widest_iqr["score_iqr"]) == (
        "2025-02",
        "us",
        1.211827,
    )
    by = {(r["month"], r["region"]): r for r in rows}
    assert by[("2021-01", "cn")] == {
        "month": "2021-01", "region": "cn", "n": 929, "score_mean": -0.96863,
        "score_std": 0.607444, "score_iqr": 0.695692, "rank_autocorr": None,
    }
    assert by[("2021-01", "us")] == {
        "month": "2021-01", "region": "us", "n": 446, "score_mean": -1.803919,
        "score_std": 0.970988, "score_iqr": 0.994268, "rank_autocorr": None,
    }
    assert by[("2026-08", "cn")]["rank_autocorr"] == 0.938698
    assert by[("2026-08", "cn")]["n"] == 929


def test_score_diagnostics_reconciles_with_ic_monthly() -> None:
    """Both panels derive from the same frozen score parquet; coverage ⊇.

    Measured relation (2026-08-28): every (region, month) the IC series reports
    is also present in the score diagnostics, but not vice versa — the IC
    series stops at 2026-06 (its forward-return window) and has a null US cell
    in 2026-06, while the score surface reaches 2026-08. Asserted exactly as
    measured; a future re-export that changes the surplus must be a conscious
    re-pin, not silent drift.
    """
    sd = _load()
    ic = json.loads((DATA / "ic_monthly.json").read_text(encoding="utf-8"))
    sd_us = {r["month"] for r in sd if r["region"] == "us"}
    sd_cn = {r["month"] for r in sd if r["region"] == "cn"}
    ic_us = {r["month"] for r in ic if r["us"] is not None}
    ic_cn = {r["month"] for r in ic if r["cn"] is not None}
    assert len(ic) == 66 and ic[0]["month"] == "2021-01" and ic[-1]["month"] == "2026-06"
    assert ic_us <= sd_us, "US IC months must be a subset of US score months"
    assert ic_cn <= sd_cn, "CN IC months must be a subset of CN score months"
    assert sd_us - ic_us == {"2026-06"}, "US: score surface has the IC-null month"
    assert sd_cn - ic_cn == {"2026-07", "2026-08"}, "CN: two months past IC window"


# --- export-lane registration (manifests + as_of extraction) -------------------


def test_score_diagnostics_registered_in_manifests() -> None:
    """The panel is a first-class citizen of the freshness map and the catalog."""
    entry = next(
        (e for e in et._DATA_HEALTH_MANIFEST if e[0] == "score_diagnostics"), None
    )
    assert entry == ("score_diagnostics", "score_diagnostics.json", et._DH_FROZEN), (
        "score diagnostics derive from frozen OOS artifacts (ledger lineage)"
    )
    ic_idx = next(i for i, e in enumerate(et._DATA_HEALTH_MANIFEST) if e[0] == "ic_monthly")
    sd_idx = et._DATA_HEALTH_MANIFEST.index(entry)
    assert sd_idx == ic_idx + 1, "registered directly after ic_monthly"
    license_, source = et._API_LICENSE["score_diagnostics"]
    assert license_ == "Aionis research artifacts (repo MIT)"
    assert "unverified" not in license_
    assert "display-only" in source


def test_score_diagnostics_as_of_from_last_month() -> None:
    """as_of is the panel's own last observed month (2026-08), never fabricated."""
    assert et._dh_as_of("score_diagnostics", "score_diagnostics.json") == "2026-08"
    dh = json.loads((DATA / "data_health.json").read_text(encoding="utf-8"))
    panel = next((p for p in dh["panels"] if p["key"] == "score_diagnostics"), None)
    assert panel is not None, "must appear in the committed freshness map"
    assert panel["category"] == "frozen"
    assert panel["as_of"] == "2026-08"
    assert panel["rows"] == 134
    cat = json.loads((DATA / "api_catalog.json").read_text(encoding="utf-8"))
    ep = next((e for e in cat["endpoints"] if e["key"] == "score_diagnostics"), None)
    assert ep is not None and ep["status"] == "available"
    assert ep["freshness"] == "frozen"
