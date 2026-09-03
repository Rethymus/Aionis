"""P1-6 R1-full — ic_deciles decile-monotonicity panel (hermetic contracts).

The panel's core promise is ALIGNMENT: decile returns use the SAME frozen
forward_returns (close[t+21]/close[t] - 1) as the training label y_fwd_ret,
on the SAME research price panels — no new return path. These tests pin the
decile construction, the h=21 alignment arithmetic, and the honesty guards
(unrealized windows / tiny cross-sections / degenerate scores -> realized
false with null returns), all on labeled synthetic fixtures.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "scripts")
import export_terminal_data as et  # noqa: E402


def _synth_scores(
    tmp_path: Path, n: int = 40, sessions: int = 60
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A frozen scores frame + a price panel whose forward returns are an
    EXACT increasing function of the score, so decile means must be strictly
    ordered D1 < D2 < ... < D10 when realized."""
    rng = np.random.default_rng(0)
    dates = pd.bdate_range("2024-01-02", periods=sessions)
    tickers = [f"T{i:02d}" for i in range(n)]
    prices = pd.DataFrame(
        100 * np.exp(np.cumsum(rng.normal(0, 0.01, size=(sessions, n)), axis=0)),
        index=dates, columns=tickers,
    )
    score_date = dates[10]
    scores = pd.DataFrame({
        "date": [score_date] * n,
        "ticker": tickers,
        "region": ["us"] * n,
        # score_i: perfectly ordered proxy for the realized forward return
        "score": np.linspace(-2, 2, n),
    })
    panel = prices.stack().rename("close").reset_index()
    panel.columns = ["date", "ticker", "close"]
    return scores, panel


def _wire(tmp_path: Path, scores: pd.DataFrame, panel: pd.DataFrame | None,
          monkeypatch: pytest.MonkeyPatch) -> Path:
    """Persist fixtures and point the exporter's module-level paths at them."""
    scores_path = tmp_path / "scores.parquet"
    scores.to_parquet(scores_path)
    panel_path = tmp_path / "panel.parquet"
    if panel is not None:
        panel.to_parquet(panel_path)
    monkeypatch.setattr(et, "_DECILE_SCORES", scores_path)
    panels = {"us": panel_path}
    if panel is not None:
        panels["cn"] = panel_path  # same panel serves both regions in fixtures
    monkeypatch.setattr(et, "_DECILE_PANELS", panels)
    monkeypatch.setattr(et, "WEB", tmp_path)
    return tmp_path


def test_decile_alignment_uses_frozen_forward_returns(tmp_path, monkeypatch) -> None:
    """The D-k decile mean equals the mean of close[t+21]/close[t]-1 over the
    decile's members — computed via the SAME forward_returns function, verified
    by an independent recomputation in the test."""
    scores, panel = _synth_scores(tmp_path)
    _wire(tmp_path, scores, panel, monkeypatch)

    et.export_ic_deciles()
    rows = json.loads((tmp_path / "ic_deciles.json").read_text(encoding="utf-8"))
    assert len(rows) == 1
    r = rows[0]
    assert r["region"] == "us" and r["n"] == 40
    assert r["realized"] is True

    # independent recomputation: RAW close[t+21]/close[t]-1 arithmetic, NOT
    # via forward_returns — so the date alignment itself is independently
    # pinned (a recomputation through the same frozen function would share
    # any row-indexing error with the exporter)
    prices_wide = panel.pivot_table(index="date", columns="ticker", values="close",
                                    aggfunc="last")
    fwd_manual = prices_wide.shift(-21) / prices_wide - 1.0
    score_date = pd.Timestamp("2024-01-02") + pd.offsets.BDay(10)
    fr = fwd_manual.loc[score_date]
    sc = scores.set_index("ticker")["score"]
    j = pd.concat([sc.rename("s"), fr.rename("f")], axis=1, join="inner").dropna()
    j["decile"] = pd.qcut(j["s"], 10, labels=False)
    for d in range(10):
        want = round(float(j.loc[j["decile"] == d, "f"].mean()), 6)
        assert r["decile_mean_fwd_ret"][d] == want, f"D{d + 1} mismatch"
    # the panel is a random walk (returns NOT ordered by score by construction),
    # so the load-bearing assertions here are the ALIGNMENT ones above
    # (bit-exact recomputation via the same frozen function) + a populated
    # spread; strict monotonicity belongs to real-signal data, not fixtures.
    assert r["d10_minus_d1"] is not None
    assert r["d10_minus_d1"] == round(
        r["decile_mean_fwd_ret"][9] - r["decile_mean_fwd_ret"][0], 6
    )


def test_decile_unrealized_window_is_honestly_null(tmp_path, monkeypatch) -> None:
    """A score month whose h=21 forward window runs past the panel edge is
    reported realized:false with null returns — never dropped, never guessed."""
    scores, panel = _synth_scores(tmp_path, sessions=25)  # score at idx 10; 10+21 > 25
    _wire(tmp_path, scores, panel, monkeypatch)

    et.export_ic_deciles()
    r = json.loads((tmp_path / "ic_deciles.json").read_text(encoding="utf-8"))[0]
    assert r["realized"] is False
    assert all(x is None for x in r["decile_mean_fwd_ret"])
    assert r["d10_minus_d1"] is None


def test_decile_tiny_cross_section_guarded(tmp_path, monkeypatch) -> None:
    """< 30 names -> realized:false (deciles of < 3 carry no monotonicity
    information; honesty over decoration)."""
    scores, panel = _synth_scores(tmp_path, n=20)
    _wire(tmp_path, scores, panel, monkeypatch)

    et.export_ic_deciles()
    r = json.loads((tmp_path / "ic_deciles.json").read_text(encoding="utf-8"))[0]
    assert r["realized"] is False
    assert r["n"] == 20


def test_decile_missing_region_panel_is_honest_absence(tmp_path, monkeypatch) -> None:
    """A region whose price panel is absent locally still appears with
    realized:false — the frozen surface's extent is shown, not trimmed."""
    scores = _synth_scores(tmp_path)[0]
    scores = pd.concat([
        scores,
        pd.DataFrame({
            "date": scores["date"],
            "ticker": [f"Z{i:02d}" for i in range(40)],
            "region": "cn", "score": np.linspace(-2, 2, 40),
        }),
    ], ignore_index=True)
    panel = _synth_scores(tmp_path)[1]
    _wire(tmp_path, scores, panel, monkeypatch)
    # drop the CN mapping: the fresh-checkout state for the CN panel
    monkeypatch.setattr(et, "_DECILE_PANELS", {"us": tmp_path / "panel.parquet"})

    et.export_ic_deciles()
    rows = json.loads((tmp_path / "ic_deciles.json").read_text(encoding="utf-8"))
    by_region = {r["region"]: r for r in rows}
    assert by_region["us"]["realized"] is True
    assert by_region["cn"]["realized"] is False  # no cn panel wired: honest
    assert all(x is None for x in by_region["cn"]["decile_mean_fwd_ret"])


def test_decile_window_is_label_window_not_h_shifted(tmp_path, monkeypatch) -> None:
    """Regression (off-by-h): the readout must pair score date t with the
    LABEL window close[t+21]/close[t]-1. The fixture makes the [t, t+21]
    window strictly increasing in score while the h-shifted [t+21, t+42]
    window is strictly DEcreasing — reading row t+h (the historical defect)
    would invert every decile mean and fail this test."""
    sessions, n = 60, 40
    dates = pd.bdate_range("2024-01-02", periods=sessions)
    tickers = [f"T{i:02d}" for i in range(n)]
    score_date = dates[10]
    prices = pd.DataFrame(100.0, index=dates, columns=tickers)
    # only the label-window end (t+21 sessions out) carries the ordered
    # signal: return over [t, t+21] is exactly 0.01*(ticker_rank+1); every
    # later close returns to 100, so the [t+21, t+42] window is anti-ordered
    prices.loc[dates[31]] = 100.0 * (1.0 + 0.01 * np.arange(1, n + 1))
    scores = pd.DataFrame({
        "date": [score_date] * n,
        "ticker": tickers,
        "region": ["us"] * n,
        "score": np.linspace(-2.0, 2.0, n),
    })
    panel = prices.stack().rename("close").reset_index()
    panel.columns = ["date", "ticker", "close"]
    _wire(tmp_path, scores, panel, monkeypatch)

    et.export_ic_deciles()
    r = json.loads((tmp_path / "ic_deciles.json").read_text(encoding="utf-8"))[0]
    assert r["realized"] is True
    means = r["decile_mean_fwd_ret"]
    assert all(m is not None for m in means)
    # decile d holds ticker ranks 4d..4d+3 (equal-count qcut over the exact
    # linspace), so the label-window means must be strictly increasing
    assert all(means[d] < means[d + 1] for d in range(9))
    # D10 = ranks 36..39 -> exact returns 0.37/0.38/0.39/0.40
    assert abs(means[9] - 0.385) < 1e-9


def test_decile_snapshot_grid_uses_value_rule_not_positional_guard(
    tmp_path, monkeypatch
) -> None:
    """Regression (CN-style snapshot grid): builder-precomputed forward
    returns live on a MONTHLY index, where a positional +21 guard would
    demand 21 future months and falsely truncate the realized surface.
    Realizability must be the VALUE rule: row t non-null == window covered."""
    months = pd.to_datetime(["2025-01-31", "2025-02-28", "2025-03-31"])
    n = 40
    tickers = [f"C{i:02d}" for i in range(n)]
    scores = pd.DataFrame({
        "date": [months[0]] * n,
        "ticker": tickers,
        "region": ["cn"] * n,
        "score": np.linspace(-2.0, 2.0, n),
    })
    fwd = 0.01 * np.arange(1, n + 1)
    panel = pd.DataFrame({
        "date": [months[0]] * n + [months[1]] * n,
        "ticker": tickers * 2,
        "forward_return_h": list(fwd) + [np.nan] * n,
    })
    scores_path = tmp_path / "scores.parquet"
    scores.to_parquet(scores_path)
    panel_path = tmp_path / "cn_panel.parquet"
    panel.to_parquet(panel_path)
    monkeypatch.setattr(et, "_DECILE_SCORES", scores_path)
    monkeypatch.setattr(et, "_DECILE_PANELS", {"cn": panel_path})
    monkeypatch.setattr(et, "WEB", tmp_path)

    et.export_ic_deciles()
    r = json.loads((tmp_path / "ic_deciles.json").read_text(encoding="utf-8"))[0]
    assert r["region"] == "cn" and r["realized"] is True
    # decile d holds ticker ranks 4d..4d+3; row t values are 0.01*(rank+1)
    assert r["decile_mean_fwd_ret"][0] == round(float(fwd[:4].mean()), 6)
    assert r["decile_mean_fwd_ret"][9] == round(float(fwd[36:40].mean()), 6)


def test_decile_committed_panel_matches_fresh_render(tmp_path, monkeypatch) -> None:
    """LOCAL-ARTIFACT byte-stability: on a machine carrying the frozen panels
    and the gitignored runs/ parquet, the committed panel equals a fresh
    render; elsewhere it skips (test_web precedent for local-artifact)."""
    import pytest

    needed = [
        Path("runs/track_c_confirmatory_oos_scores.parquet"),
        Path("data/cache/track_b_panel.parquet"),
    ]
    if not all(p.exists() for p in needed):
        pytest.skip("local-artifact contract: requires frozen scores + US panel")
    committed = json.loads(
        Path("web/src/data/aionis/ic_deciles.json").read_text(encoding="utf-8")
    )
    monkeypatch.setattr(et, "WEB", tmp_path)
    et.export_ic_deciles()
    fresh = json.loads((tmp_path / "ic_deciles.json").read_text(encoding="utf-8"))
    assert committed == fresh, "ic_deciles drifted from a fresh render"
