"""PIT S&P 500 membership universe — hermetic (no network; synthetic fixtures).

These pin the parser + PIT semantics so a regression to a today-snapshot
universe (survivorship bias / the cik_map look-ahead leak) is caught without
touching the network. Real-data ingest is exercised separately and logged.
"""
from __future__ import annotations

import pandas as pd

from aionis.ingest.universe import (
    _parse_hanshof_csv,
    _parse_pierrebrunelle_files,
    constituents_on,
    filter_reuse_mismatches,
    jaccard_monthly,
    mask_panel_to_pit,
    names_agree,
    normalize_ticker,
    universe_agreement_verdict,
)

_HANSHOF_CSV = (
    'date,tickers\n'
    '2018-01-02,"AAPL,MSFT,AMZN,BRK.B"\n'
    '2018-01-03,"AAPL,MSFT,AMZN,BRK-B"\n'
    '2018-02-01,"AAPL,MSFT,NVDA"\n'
)


def test_normalize_ticker_share_class_only() -> None:
    """All three share-class separators (``.``, ``/``) -> ``-``; upper-case;
    history suffixes kept (no ad-hoc rename mapping — that would be p-hacking)."""
    assert normalize_ticker("BRK.B") == "BRK-B"
    assert normalize_ticker("BRK/B") == "BRK-B"  # pierrebrunelle uses '/'
    assert normalize_ticker("bf-b") == "BF-B"
    assert normalize_ticker(" aapl ") == "AAPL"
    assert normalize_ticker("EKDKQ") == "EKDKQ"  # bankruptcy suffix = identity, kept
    assert normalize_ticker("FB") == "FB"  # historical ticker NOT remapped to META


def test_hanshof_parser_long_membership_and_share_class() -> None:
    mem = _parse_hanshof_csv(_HANSHOF_CSV)
    assert list(mem.columns) == ["date", "ticker"]
    d1 = set(mem.loc[mem["date"] == pd.Timestamp("2018-01-02"), "ticker"])
    assert d1 == {"AAPL", "MSFT", "AMZN", "BRK-B"}  # BRK.B -> BRK-B
    assert "BRK.B" not in mem["ticker"].to_numpy()  # no un-normalized separators remain


def test_pierrebrunelle_parser_month_start_dates() -> None:
    files = {
        "spy201801": "AAPL\tApple Inc.\t0.2\nMSFT\tMicrosoft\t0.2\n",
        "spy201802": "AAPL\tApple Inc.\t0.2\nNVDA\tNVIDIA\t0.2\n",
    }
    mem = _parse_pierrebrunelle_files(files)
    jan = set(mem.loc[mem["date"] == pd.Timestamp("2018-01-01"), "ticker"])
    feb = set(mem.loc[mem["date"] == pd.Timestamp("2018-02-01"), "ticker"])
    assert jan == {"AAPL", "MSFT"}
    assert feb == {"AAPL", "NVDA"}


def test_constituents_on_is_point_in_time() -> None:
    """A ticker added in Feb is NOT a constituent as-of a January date."""
    mem = _parse_pierrebrunelle_files({
        "spy201801": "AAPL\tA\t0.5\n",
        "spy201802": "AAPL\tA\t0.5\nNVDA\tN\t0.5\n",
    })
    assert "NVDA" not in constituents_on(mem, "2018-01-15")  # PIT: not yet added
    assert "NVDA" in constituents_on(mem, "2018-02-15")
    assert constituents_on(mem, "2017-06-01") == set()  # before any snapshot -> empty


def test_jaccard_identical_disjoint_partial() -> None:
    daily = pd.DataFrame({
        "date": pd.to_datetime(["2018-01-31"] * 3 + ["2018-02-28"] * 3),
        "ticker": ["A", "B", "C", "A", "B", "D"],
    })
    identical = pd.DataFrame({
        "date": pd.to_datetime(["2018-01-01"] * 3 + ["2018-02-01"] * 3),
        "ticker": ["A", "B", "C", "A", "B", "D"],
    })
    assert jaccard_monthly(daily, identical).min() == 1.0

    disjoint = pd.DataFrame({
        "date": pd.to_datetime(["2018-01-01"] * 2 + ["2018-02-01"] * 2),
        "ticker": ["X", "Y", "X", "Y"],
    })
    jd = jaccard_monthly(daily, disjoint)
    assert (jd.to_numpy() == 0.0).all()

    # Daily {A,B,C} vs monthly {A,B}: intersection 2 / union 3 = 2/3.
    partial = pd.DataFrame({
        "date": pd.to_datetime(["2018-01-01"] * 2 + ["2018-02-01"] * 2),
        "ticker": ["A", "B", "A", "B"],
    })
    jp = jaccard_monthly(daily, partial)
    assert abs(jp.loc[pd.Timestamp("2018-01-01")] - 2 / 3) < 1e-9


def test_verdict_threshold_fires_correctly() -> None:
    agree = universe_agreement_verdict(pd.Series([0.97, 0.98, 0.96]))
    assert agree["agreement"] is True
    assert agree["min_jaccard"] == 0.96

    disagree = universe_agreement_verdict(pd.Series([0.97, 0.90, 0.98]))
    assert disagree["agreement"] is False
    assert disagree["min_jaccard"] == 0.90
    assert str(disagree["min_jaccard_month"]).startswith("1970") is False  # a real month


def test_mask_panel_to_pit_drops_non_constituents_and_pre_snapshot() -> None:
    """A panel row is kept iff its ticker was a PIT constituent on that date; rows
    before the first snapshot are dropped (no universe forward-fill)."""
    mem = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-02-01", "2024-02-01"]),
        "ticker": ["A", "B", "A", "C"],  # Jan={A,B}; Feb={A,C} (B dropped, C added)
    })
    panel = pd.DataFrame({
        "date": pd.to_datetime(["2023-12-15", "2024-01-15", "2024-01-15",
                                "2024-02-15", "2024-02-15", "2024-01-15"]),
        "ticker": ["A", "A", "B", "A", "C", "X"],  # X never in index
        "v": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
    })
    out = mask_panel_to_pit(panel, mem)
    kept = {(d.strftime("%Y-%m"), t)
            for d, t in zip(out["date"], out["ticker"], strict=True)}
    assert ("2023-12", "A") not in kept     # before first snapshot -> dropped
    assert ("2024-01", "X") not in kept     # never a constituent -> dropped
    assert ("2024-01", "A") in kept and ("2024-01", "B") in kept
    assert ("2024-02", "A") in kept and ("2024-02", "C") in kept  # C added; PIT


def test_names_agree_catches_reuse_keeps_rename() -> None:
    # same company -> agree (even across suffix / punctuation variants)
    assert names_agree("Apple Inc.", "Apple Inc.")
    assert names_agree("Meta Platforms, Inc.", "Meta Platforms")
    # reused ticker, different company -> disagree (the BBT case)
    assert not names_agree("Beacon Financial Corp", "BB&T Corporation")
    # ambiguous name (only short / suffix tokens) -> keep (don't over-drop)
    assert names_agree("Co Ltd", "BB&T")


def test_filter_reuse_mismatches_flags_wrong_entity_keeps_rest() -> None:
    """Stage-1 (pure): a token-mismatched ticker is FLAGGED (candidate), not dropped;
    confirmation is stage-2 (SEC name history)."""
    resolved = {"AAPL": 320193, "BBT": 1108134, "MSFT": 789019}
    pb_names = {"AAPL": "Apple Inc.", "BBT": "BB&T Corporation", "MSFT": "Microsoft"}
    sec_titles = {
        320193: "Apple Inc.",
        1108134: "Beacon Financial Corp",   # reused ticker -> flagged candidate
        789019: "Microsoft Corp",
    }
    clean, flagged = filter_reuse_mismatches(resolved, pb_names, sec_titles)
    assert set(clean) == {"AAPL", "MSFT"}
    assert set(flagged) == {"BBT"}
    assert flagged["BBT"]["sec"] == "Beacon Financial Corp"
    # a ticker missing from pb_names is kept (PB membership already vouches for it)
    clean2, flagged2 = filter_reuse_mismatches({"NEW": 1}, {}, {1: "Anything"})
    assert "NEW" in clean2 and not flagged2
