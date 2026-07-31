"""E3 Slice 3b — causal broadcast (the arm_e13 extra_features builder, hermetic).

Pins :mod:`aionis.features.causal_broadcast`: assembles the long
``extra_features=[date, ticker, ...]`` frame for arm_e13 by reusing, not
hand-rolling:

  * :func:`aionis.features.propagation.propagate_panel` — FF-12 ex-self peer
    propagation of the 13D / 8-K self-shock indicators;
  * :func:`aionis.features.frozen_beta.broadcast_macro_beta` — frozen sign-β ×
    surprise_z macro shock (zero-LLM);
  * :mod:`aionis.extraction.extract` — the idempotent sha256-keyed cache pattern,
    ridden by the thin closed-enum LLM edge extractor;
  * the ``_long(wide, tickers, name)`` wide->long melt from
    ``scripts/phase_e1_run.py``.

The LLM client is mocked (labeled fixtures); no network. Collectors' shapes are
mocked to the Slice-2 contract (``value=1.0`` indicators, ``event_ts`` PIT).
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from aionis.features.causal_broadcast import (
    build_forward_extra_features,
    extract_event_edges,
    forward_self_shocks,
)
from aionis.features.propagation import propagate_panel
from aionis.schema.causal_edge import (
    CausalEdge,
    Direction,
    ForwardCausalExtraction,
    HorizonBucket,
    MechanismKeyword,
    SicSector,
)

SESSIONS = pd.DatetimeIndex(pd.bdate_range("2024-01-02", periods=8))


# ---------------------------------------------------------------------------
# labeled fixture builders (clearly fixture, NOT real data)
# ---------------------------------------------------------------------------


def _stakes_row(ticker: str, filing: str) -> dict:
    return {
        "ticker": ticker,
        "value": 1.0,
        "event_ts": pd.Timestamp(filing),
        "filing_date": filing,
        "feature": "stake_13d_filing",
    }


def _earnings_row(ticker: str, filing: str) -> dict:
    return {
        "ticker": ticker,
        "value": 1.0,
        "event_ts": pd.Timestamp(filing),
        "filing_date": filing,
        "feature": "earnings_8k_item_2_02",
    }


def _macro_row(pub: str, event_type: str, z: float) -> dict:
    return {
        "event_type": event_type,
        "pub_date": pd.Timestamp(pub),
        "surprise_z": z,
        "value": z,
    }


class _MockCausalClient:
    """Deterministic, network-free closed-enum edge builder (test fixture only)."""

    def __init__(self, table: dict[str, ForwardCausalExtraction]) -> None:
        self.table = table
        self.calls: list[str] = []

    def extract_causal(self, text: str, event_id: str) -> ForwardCausalExtraction:
        self.calls.append(event_id)
        return self.table[event_id]


def _edge(
    direction: Direction = Direction.POSITIVE,
    mechanism: MechanismKeyword = MechanismKeyword.OWNERSHIP_CHANGE,
    sector: SicSector = SicSector.HLTH,
) -> CausalEdge:
    return CausalEdge(
        sic_sector=sector,
        direction=direction,
        mechanism_keyword=mechanism,
        horizon_bucket=HorizonBucket.SHORT,
    )


# ===========================================================================
# forward_self_shocks — wide (sessions x tickers) indicator frames
# ===========================================================================


def test_forward_self_shocks_places_indicator_at_filing_session() -> None:
    stakes = pd.DataFrame([_stakes_row("AAA", "2024-01-04")])
    earnings = pd.DataFrame([_earnings_row("BBB", "2024-01-05")])
    s13, s8 = forward_self_shocks(stakes, earnings, SESSIONS, ["AAA", "BBB"])
    d13 = pd.Timestamp("2024-01-04")
    d8 = pd.Timestamp("2024-01-05")
    assert s13.loc[d13, "AAA"] == 1.0
    assert pd.isna(s13.loc[d8, "BBB"])
    assert s8.loc[d8, "BBB"] == 1.0
    assert pd.isna(s8.loc[d13, "AAA"])
    # shape + index
    assert list(s13.index) == list(SESSIONS)
    assert list(s13.columns) == ["AAA", "BBB"]


def test_forward_self_shocks_nan_outside_filing() -> None:
    stakes = pd.DataFrame([_stakes_row("AAA", "2024-01-04")])
    earnings = pd.DataFrame([_earnings_row("AAA", "2024-01-04")])
    s13, s8 = forward_self_shocks(stakes, earnings, SESSIONS, ["AAA"])
    d = pd.Timestamp("2024-01-04")
    other = [x for x in SESSIONS if x != d]
    assert s13.loc[other, "AAA"].isna().all()
    assert s8.loc[other, "AAA"].isna().all()


def test_forward_self_shocks_off_grid_filing_forward_maps() -> None:
    """A filing on a non-session day maps to the next session (PIT)."""
    stakes = pd.DataFrame([_stakes_row("AAA", "2024-01-06")])  # Saturday
    earnings = pd.DataFrame(columns=["ticker", "value", "event_ts"])
    s13, _ = forward_self_shocks(stakes, earnings, SESSIONS, ["AAA"])
    next_session = pd.Timestamp("2024-01-08")  # Monday
    assert s13.loc[next_session, "AAA"] == 1.0
    assert s13.loc[pd.Timestamp("2024-01-05"), "AAA"] != 1.0 or pd.isna(
        s13.loc[pd.Timestamp("2024-01-05"), "AAA"]
    )


def test_forward_self_shocks_empty_inputs_yield_all_nan() -> None:
    stakes = pd.DataFrame(columns=["ticker", "value", "event_ts"])
    earnings = pd.DataFrame(columns=["ticker", "value", "event_ts"])
    s13, s8 = forward_self_shocks(stakes, earnings, SESSIONS, ["AAA", "BBB"])
    assert s13.shape == (len(SESSIONS), 2)
    assert s13.isna().all().all()
    assert s8.isna().all().all()


# ===========================================================================
# extract_event_edges — idempotent sha256-keyed cache (rides extract.py pattern)
# ===========================================================================


def test_extract_event_edges_caches_and_is_idempotent(tmp_path: Path) -> None:
    events = pd.DataFrame(
        [
            {
                "event_id": "E1",
                "ticker": "AAA",
                "event_ts": pd.Timestamp("2024-01-04"),
                "text": "ACME 13D filing text",
            }
        ]
    )
    table = {"E1": ForwardCausalExtraction(event_id="E1", causal_edges=[_edge()])}
    client = _MockCausalClient(table)

    out1 = extract_event_edges(events, client, tmp_path)
    assert out1["E1"].causal_edges[0].direction is Direction.POSITIVE
    assert client.calls == ["E1"]

    # second call: cache hit, client NOT called again, same result
    out2 = extract_event_edges(events, client, tmp_path)
    assert client.calls == ["E1"]  # no new call
    assert out2["E1"] == out1["E1"]


def test_extract_event_edges_missing_text_row_skipped(tmp_path: Path) -> None:
    events = pd.DataFrame(
        [
            {"event_id": "E1", "ticker": "AAA", "event_ts": pd.Timestamp("2024-01-04")},
            {
                "event_id": "E2",
                "ticker": "BBB",
                "event_ts": pd.Timestamp("2024-01-04"),
                "text": "BBB 8-K text",
            },
        ]
    )
    table = {"E2": ForwardCausalExtraction(event_id="E2", causal_edges=[_edge()])}
    client = _MockCausalClient(table)
    out = extract_event_edges(events, client, tmp_path)
    assert set(out.keys()) == {"E2"}  # E1 had no text -> skipped


# ===========================================================================
# build_forward_extra_features — the long [date, ticker, ...] frame
# ===========================================================================


def _base_events(ticker: str, event_ts: str, text: str) -> pd.DataFrame:
    return pd.DataFrame(
        [{"event_id": "E1", "ticker": ticker, "event_ts": pd.Timestamp(event_ts), "text": text}]
    )


def test_build_output_has_expected_long_columns() -> None:
    stakes = pd.DataFrame([_stakes_row("AAA", "2024-01-04")])
    earnings = pd.DataFrame([_earnings_row("AAA", "2024-01-05")])
    macro = pd.DataFrame([_macro_row("2024-01-04", "CPI", 2.0)])
    events = _base_events("AAA", "2024-01-04", "AAA 13D text")
    client = _MockCausalClient(
        {"E1": ForwardCausalExtraction(event_id="E1", causal_edges=[_edge()])}
    )
    ff12_map = {"AAA": SicSector.HLTH}
    ef = build_forward_extra_features(
        macro_df=macro,
        stakes_df=stakes,
        earnings_df=earnings,
        events_df=events,
        client=client,
        cache_dir=None,  # no cache (idempotent extractor still works in-memory)
        ff12_map=ff12_map,
        sessions=SESSIONS,
        tickers=["AAA"],
    )
    expected = {
        "date",
        "ticker",
        "self_13d_fwd",
        "self_8k_fwd",
        "peer_13d_fwd",
        "peer_8k_fwd",
        "macro_causal_shock",
        "mech_earnings_signal",
        "mech_ownership_change",
        "mech_guidance",
        "mech_other",
    }
    assert expected.issubset(set(ef.columns))


def test_peer_propagation_uses_propagate_panel_exself() -> None:
    """AAA & BBB both have a 13D (Hlth) -> each is the other's ex-self peer mean.

    propagate_panel's ex-self mean requires >=2 valid (non-NaN) shocks in the
    sector AND is only defined for focal tickers that themselves carry a shock
    (the ``(gmean*gn - self)/(gn-1)`` algebra). CCC (Hlth, no 13D) gets NaN.
    """
    stakes = pd.DataFrame(
        [_stakes_row("AAA", "2024-01-04"), _stakes_row("BBB", "2024-01-04")]
    )
    earnings = pd.DataFrame(columns=["ticker", "value", "event_ts"])
    macro = pd.DataFrame(columns=["event_type", "pub_date", "surprise_z"])
    events = pd.DataFrame(columns=["event_id", "ticker", "event_ts", "text"])
    client = _MockCausalClient({})
    ff12_map = {"AAA": SicSector.HLTH, "BBB": SicSector.HLTH, "CCC": SicSector.HLTH}
    ef = build_forward_extra_features(
        macro_df=macro,
        stakes_df=stakes,
        earnings_df=earnings,
        events_df=events,
        client=client,
        cache_dir=None,
        ff12_map=ff12_map,
        sessions=SESSIONS,
        tickers=["AAA", "BBB", "CCC"],
    )
    d = pd.Timestamp("2024-01-04")
    row_aaa = ef[(ef["date"] == d) & (ef["ticker"] == "AAA")]
    row_bbb = ef[(ef["date"] == d) & (ef["ticker"] == "BBB")]
    row_ccc = ef[(ef["date"] == d) & (ef["ticker"] == "CCC")]
    assert row_aaa["peer_13d_fwd"].iloc[0] == pytest.approx(1.0)  # peer = BBB
    assert row_bbb["peer_13d_fwd"].iloc[0] == pytest.approx(1.0)  # peer = AAA
    assert pd.isna(row_ccc["peer_13d_fwd"].iloc[0])  # CCC has no shock -> no propagation


def test_macro_beta_broadcast_in_build() -> None:
    """A CPI event fills macro_causal_shock for each sector member at its session."""
    stakes = pd.DataFrame(columns=["ticker", "value", "event_ts"])
    earnings = pd.DataFrame(columns=["ticker", "value", "event_ts"])
    macro = pd.DataFrame([_macro_row("2024-01-04", "CPI", 2.0)])
    events = pd.DataFrame(columns=["event_id", "ticker", "event_ts", "text"])
    client = _MockCausalClient({})
    ff12_map = {"AAA": SicSector.HLTH, "BBB": SicSector.UTILS}
    ef = build_forward_extra_features(
        macro_df=macro,
        stakes_df=stakes,
        earnings_df=earnings,
        events_df=events,
        client=client,
        cache_dir=None,
        ff12_map=ff12_map,
        sessions=SESSIONS,
        tickers=["AAA", "BBB"],
    )
    from aionis.features.frozen_beta import FROZEN_BETA

    d = pd.Timestamp("2024-01-04")
    a = ef[(ef["date"] == d) & (ef["ticker"] == "AAA")]["macro_causal_shock"].iloc[0]
    b = ef[(ef["date"] == d) & (ef["ticker"] == "BBB")]["macro_causal_shock"].iloc[0]
    assert a == pytest.approx(FROZEN_BETA[(SicSector.HLTH, "cpi")] * 2.0)
    assert b == pytest.approx(FROZEN_BETA[(SicSector.UTILS, "cpi")] * 2.0)


@pytest.mark.parametrize(
    "direction, signed",
    [
        (Direction.POSITIVE, 1.0),
        (Direction.NEGATIVE, -1.0),
    ],
)
def test_llm_edge_direction_signs_self_shock(direction: Direction, signed: float) -> None:
    """The LLM direction signs the self-shock: POSITIVE->+1, NEGATIVE->-1."""
    stakes = pd.DataFrame([_stakes_row("AAA", "2024-01-04")])
    earnings = pd.DataFrame(columns=["ticker", "value", "event_ts"])
    macro = pd.DataFrame(columns=["event_type", "pub_date", "surprise_z"])
    events = _base_events("AAA", "2024-01-04", "AAA 13D text")
    client = _MockCausalClient(
        {"E1": ForwardCausalExtraction(event_id="E1", causal_edges=[_edge(direction=direction)])}
    )
    ef = build_forward_extra_features(
        macro_df=macro,
        stakes_df=stakes,
        earnings_df=earnings,
        events_df=events,
        client=client,
        cache_dir=None,
        ff12_map={"AAA": SicSector.HLTH},
        sessions=SESSIONS,
        tickers=["AAA"],
    )
    d = pd.Timestamp("2024-01-04")
    val = ef[(ef["date"] == d) & (ef["ticker"] == "AAA")]["self_13d_fwd"].iloc[0]
    assert val == pytest.approx(signed)


def test_llm_edge_neutral_direction_signs_to_nan() -> None:
    stakes = pd.DataFrame([_stakes_row("AAA", "2024-01-04")])
    earnings = pd.DataFrame(columns=["ticker", "value", "event_ts"])
    macro = pd.DataFrame(columns=["event_type", "pub_date", "surprise_z"])
    events = _base_events("AAA", "2024-01-04", "AAA 13D text")
    client = _MockCausalClient(
        {
            "E1": ForwardCausalExtraction(
                event_id="E1", causal_edges=[_edge(direction=Direction.NEUTRAL)]
            )
        }
    )
    ef = build_forward_extra_features(
        macro_df=macro,
        stakes_df=stakes,
        earnings_df=earnings,
        events_df=events,
        client=client,
        cache_dir=None,
        ff12_map={"AAA": SicSector.HLTH},
        sessions=SESSIONS,
        tickers=["AAA"],
    )
    d = pd.Timestamp("2024-01-04")
    val = ef[(ef["date"] == d) & (ef["ticker"] == "AAA")]["self_13d_fwd"].iloc[0]
    assert math.isnan(val)  # NEUTRAL -> NaN (no directional commit)


@pytest.mark.parametrize(
    "mechanism, column",
    [
        (MechanismKeyword.OWNERSHIP_CHANGE, "mech_ownership_change"),
        (MechanismKeyword.EARNINGS_SIGNAL, "mech_earnings_signal"),
        (MechanismKeyword.GUIDANCE, "mech_guidance"),
        (MechanismKeyword.OTHER, "mech_other"),
    ],
)
def test_mechanism_keyword_one_hot(mechanism: MechanismKeyword, column: str) -> None:
    stakes = pd.DataFrame([_stakes_row("AAA", "2024-01-04")])
    earnings = pd.DataFrame(columns=["ticker", "value", "event_ts"])
    macro = pd.DataFrame(columns=["event_type", "pub_date", "surprise_z"])
    events = _base_events("AAA", "2024-01-04", "AAA 13D text")
    client = _MockCausalClient(
        {"E1": ForwardCausalExtraction(event_id="E1", causal_edges=[_edge(mechanism=mechanism)])}
    )
    ef = build_forward_extra_features(
        macro_df=macro,
        stakes_df=stakes,
        earnings_df=earnings,
        events_df=events,
        client=client,
        cache_dir=None,
        ff12_map={"AAA": SicSector.HLTH},
        sessions=SESSIONS,
        tickers=["AAA"],
    )
    d = pd.Timestamp("2024-01-04")
    val = ef[(ef["date"] == d) & (ef["ticker"] == "AAA")][column].iloc[0]
    assert val == 1.0
    # the other three mechanism columns are NaN at this event session
    others = {
        "mech_earnings_signal",
        "mech_ownership_change",
        "mech_guidance",
        "mech_other",
    } - {column}
    for c in others:
        v = ef[(ef["date"] == d) & (ef["ticker"] == "AAA")][c].iloc[0]
        assert pd.isna(v), f"{c} should be NaN at the event session"


def test_build_idempotent(tmp_path: Path) -> None:
    """Two builds over the SAME inputs produce bit-identical extra_features."""
    stakes = pd.DataFrame([_stakes_row("AAA", "2024-01-04")])
    earnings = pd.DataFrame([_earnings_row("AAA", "2024-01-05")])
    macro = pd.DataFrame([_macro_row("2024-01-04", "CPI", 2.0)])
    events = _base_events("AAA", "2024-01-04", "AAA 13D text")
    client = _MockCausalClient(
        {"E1": ForwardCausalExtraction(event_id="E1", causal_edges=[_edge()])}
    )
    common = dict(
        macro_df=macro,
        stakes_df=stakes,
        earnings_df=earnings,
        events_df=events,
        client=client,
        cache_dir=tmp_path,
        ff12_map={"AAA": SicSector.HLTH},
        sessions=SESSIONS,
        tickers=["AAA"],
    )
    a = build_forward_extra_features(**common)
    b = build_forward_extra_features(**common)
    pd.testing.assert_frame_equal(
        a.sort_values(["date", "ticker"]).reset_index(drop=True),
        b.sort_values(["date", "ticker"]).reset_index(drop=True),
    )


# ===========================================================================
# left-join compatibility with build_selection_panel(extra_features=)
# ===========================================================================


def test_extra_features_left_join_compatible_with_selection_panel() -> None:
    """The long frame merges into build_selection_panel without error/row change."""
    from aionis.features.selection_panel import build_selection_panel

    sessions3 = pd.DatetimeIndex(pd.bdate_range("2024-01-02", periods=3))
    prices = pd.DataFrame(
        {"AAA": [10.0, 10.5, 11.0]}, index=sessions3
    )
    fundamentals_long = pd.DataFrame(columns=["ticker", "filed", "metric", "value"])
    stakes = pd.DataFrame([_stakes_row("AAA", "2024-01-04")])  # off the 3-session grid
    # restrict to the 3-session grid so the event lands on it
    stakes = pd.DataFrame([_stakes_row("AAA", "2024-01-03")])
    earnings = pd.DataFrame(columns=["ticker", "value", "event_ts"])
    macro = pd.DataFrame(columns=["event_type", "pub_date", "surprise_z"])
    events = _base_events("AAA", "2024-01-03", "AAA 13D text")
    client = _MockCausalClient(
        {"E1": ForwardCausalExtraction(event_id="E1", causal_edges=[_edge()])}
    )
    ef = build_forward_extra_features(
        macro_df=macro,
        stakes_df=stakes,
        earnings_df=earnings,
        events_df=events,
        client=client,
        cache_dir=None,
        ff12_map={"AAA": SicSector.HLTH},
        sessions=sessions3,
        tickers=["AAA"],
    )
    panel = build_selection_panel(
        prices,
        fundamentals_long,
        horizon=1,
        tickers=["AAA"],
        extra_features=ef,
    )
    # the extra cols landed as columns on the panel
    assert "self_13d_fwd" in panel.columns
    assert "macro_causal_shock" in panel.columns
    assert "mech_ownership_change" in panel.columns
    # the panel row count is the (date x ticker) cartesian, unchanged by the join
    assert len(panel) == 3 * 1


# ===========================================================================
# direct propagate_panel reuse sanity (FF-12 grouping via ff12_map)
# ===========================================================================


def test_propagate_panel_accepts_ff12_map_grouping() -> None:
    """Feeding ff12_map (ticker->SicSector) to propagate_panel groups on FF-12.

    AAA & BBB both have a shock (Hlth) -> each is the other's ex-self peer. CCC
    (MONEY, singleton with a shock) -> NaN (group needs >=2 valid members).
    """
    wide = pd.DataFrame(
        {"AAA": [1.0], "BBB": [1.0], "CCC": [1.0]},
        index=pd.DatetimeIndex(["2024-01-04"]),
    )
    ff12_map = {"AAA": SicSector.HLTH, "BBB": SicSector.HLTH, "CCC": SicSector.MONEY}
    out = propagate_panel(wide, ff12_map, tickers=["AAA", "BBB", "CCC"])
    d = pd.Timestamp("2024-01-04")
    assert out.loc[d, "AAA"] == pytest.approx(1.0)  # ex-self peer = BBB
    assert out.loc[d, "BBB"] == pytest.approx(1.0)  # ex-self peer = AAA
    assert pd.isna(out.loc[d, "CCC"])  # MONEY singleton -> NaN


def test_add_usage_accumulates_tokens_none_safe() -> None:
    """FIX3: _add_usage accumulates per-call token usage; None-safe (observability)."""
    from aionis.features.causal_broadcast import _add_usage

    accum: dict[str, int] = {}
    _add_usage(accum, None)  # absent/failed usage -> no crash, no change
    assert accum == {}
    _add_usage(accum, {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
    _add_usage(accum, {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5})
    assert accum == {"prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20}
