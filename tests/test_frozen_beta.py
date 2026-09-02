"""E3 Slice 3a' — frozen sign-only macro β table + broadcast (hermetic).

Pins :mod:`aionis.features.frozen_beta`: the FROZEN a-priori sign-β table
(sector × shock) that drives the zero-LLM macro channel of arm_e13, and its
``broadcast_macro_beta`` — which assigns ``FROZEN_BETA[(sector, shock)] *
surprise_z`` to each sector member at the event's session. The table is a frozen
literal (no estimation DOF), so it adds no leakage and no rerun-to-significance
lever; the broadcast is PIT (events with ``pub_date`` after the freeze are
excluded) and idempotent.
"""
from __future__ import annotations

import pandas as pd
import pytest

from aionis.features.frozen_beta import (
    FROZEN_BETA,
    FROZEN_BETA_SOURCE,
    FROZEN_BETA_STATUS,
    FROZEN_BETA_VERSION,
    broadcast_macro_beta,
)
from aionis.schema.causal_edge import SicSector

SESSIONS = pd.DatetimeIndex(pd.bdate_range("2024-01-02", periods=10))


def _macro_event(pub: str, event_type: str, z: float) -> dict:
    """One Slice-2-style macro_forward row (clearly fixture, not real data)."""
    return {
        "series_id": "CPIAUCSL" if event_type == "CPI" else "PAYEMS",
        "event_type": event_type,
        "feature": f"macro_{'cpi' if event_type == 'CPI' else 'nfp'}_surprise",
        "ref_date": pd.Timestamp(pub),
        "pub_date": pd.Timestamp(pub),
        "surprise_z": z,
        "value": z,
        "event_ts": pd.Timestamp(pub),
        "snapshot_ts": "2024-01-31T00:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# the table is a FROZEN constant (24 entries, no estimation DOF)
# ---------------------------------------------------------------------------


def test_frozen_beta_covers_all_sectors_and_shocks() -> None:
    shocks = {"cpi", "nfp"}
    sectors = {s for s in SicSector}
    expected = {(s, sh) for s in sectors for sh in shocks}
    assert set(FROZEN_BETA.keys()) == expected
    assert len(FROZEN_BETA) == 24


@pytest.mark.parametrize("sector", list(SicSector))
def test_frozen_beta_values_are_signs_only(sector: SicSector) -> None:
    """Every frozen β is a pure sign (+1 or -1) — no magnitude, no estimation DOF."""
    assert FROZEN_BETA[(sector, "cpi")] in (+1, -1)
    assert FROZEN_BETA[(sector, "nfp")] in (+1, -1)


def test_frozen_beta_is_a_module_literal_constant() -> None:
    """The table is defined at import (no data touches it) — frozen for H6."""
    # Same identity across attribute access: module-level dict, never rebuilt.
    from aionis.features import frozen_beta as mod

    assert mod.FROZEN_BETA is mod.FROZEN_BETA


def test_frozen_beta_source_version_status_documented() -> None:
    # 2026-09-02 adjudication (owner-delegated, evidence-complete): the
    # originally cited paper does not exist (fabricated citation — FEDS
    # 2017-020 is Reifschneider-Tulip; three Crossref sweeps found no
    # Boudt-Neely industry paper). The sign table is OFFICIALLY frozen as a
    # project-internal qualitative prior: provenance honest, signs unchanged.
    assert "project-internal qualitative prior" in FROZEN_BETA_SOURCE
    assert "disproven" in FROZEN_BETA_SOURCE
    assert FROZEN_BETA_VERSION == "qual-prior-v2"
    assert FROZEN_BETA_STATUS == "frozen-qualitative-prior"
    # status flags the provenance state — the 2026-09-02 adjudication froze
    # the qualitative prior officially (the "sourced" state is unreachable:
    # the cited paper does not exist).
    assert FROZEN_BETA_STATUS in {
        "boudt-neely-2017-sourced",
        "exploratory-v1-qualitative",
        "frozen-qualitative-prior",
    }


# ---------------------------------------------------------------------------
# known economically-defensible signs (qualitative-v1 prior)
# ---------------------------------------------------------------------------


def test_cpi_energy_sign_positive() -> None:
    """Energy (resource pricing power) co-moves with unexpected inflation."""
    assert FROZEN_BETA[(SicSector.ENRGY, "cpi")] == 1


def test_cpi_utilities_sign_negative() -> None:
    """Utilities (bond-proxy, rate-sensitive) are hurt by inflation surprises."""
    assert FROZEN_BETA[(SicSector.UTILS, "cpi")] == -1


def test_nfp_consumer_cyclicals_positive() -> None:
    """Strong labor market lifts consumer cyclicals (Durbl / Shops)."""
    assert FROZEN_BETA[(SicSector.DURBL, "nfp")] == 1
    assert FROZEN_BETA[(SicSector.SHOPS, "nfp")] == 1


def test_nfp_defensives_negative() -> None:
    """Defensive sectors (Utils / Telcm) rotate out under strong employment."""
    assert FROZEN_BETA[(SicSector.UTILS, "nfp")] == -1
    assert FROZEN_BETA[(SicSector.TELCM, "nfp")] == -1


# ---------------------------------------------------------------------------
# broadcast_macro_beta — wide (sessions x tickers), sign*z at event session
# ---------------------------------------------------------------------------


def test_broadcast_sign_times_z_per_sector_member() -> None:
    """A CPI event assigns each sector member its OWN sector's sign * z."""
    macro = pd.DataFrame([_macro_event("2024-01-04", "CPI", 2.0)])
    ff12_map = {"AAA": SicSector.HLTH, "BBB": SicSector.MONEY, "CCC": SicSector.UTILS}
    out = broadcast_macro_beta(macro, ff12_map, SESSIONS, ["AAA", "BBB", "CCC"])
    # pub_date 2024-01-04 is a session (bdate day 3) -> lands there
    d = pd.Timestamp("2024-01-04")
    assert out.loc[d, "AAA"] == pytest.approx(
        FROZEN_BETA[(SicSector.HLTH, "cpi")] * 2.0
    )
    assert out.loc[d, "BBB"] == pytest.approx(
        FROZEN_BETA[(SicSector.MONEY, "cpi")] * 2.0
    )
    assert out.loc[d, "CCC"] == pytest.approx(
        FROZEN_BETA[(SicSector.UTILS, "cpi")] * 2.0
    )


def test_broadcast_nan_outside_event_session() -> None:
    macro = pd.DataFrame([_macro_event("2024-01-04", "CPI", 2.0)])
    ff12_map = {"AAA": SicSector.HLTH}
    out = broadcast_macro_beta(macro, ff12_map, SESSIONS, ["AAA"])
    d_event = pd.Timestamp("2024-01-04")
    other = [d for d in SESSIONS if d != d_event]
    assert out.loc[d_event, "AAA"] == pytest.approx(
        FROZEN_BETA[(SicSector.HLTH, "cpi")] * 2.0
    )
    # every other session is NaN (event-time feature, NOT carried forward)
    assert out.loc[other, "AAA"].isna().all()


def test_broadcast_nan_for_ticker_not_in_ff12_map() -> None:
    """A ticker with no ff12_map entry gets no macro shock (no sector = no sign)."""
    macro = pd.DataFrame([_macro_event("2024-01-04", "CPI", 2.0)])
    ff12_map = {"AAA": SicSector.HLTH}  # BBB absent
    out = broadcast_macro_beta(macro, ff12_map, SESSIONS, ["AAA", "BBB"])
    d = pd.Timestamp("2024-01-04")
    assert out.loc[d, "AAA"] == pytest.approx(
        FROZEN_BETA[(SicSector.HLTH, "cpi")] * 2.0
    )
    assert pd.isna(out.loc[d, "BBB"])


def test_broadcast_nfp_uses_nfp_signs() -> None:
    macro = pd.DataFrame([_macro_event("2024-01-05", "NFP", 1.5)])
    ff12_map = {"AAA": SicSector.DURBL, "BBB": SicSector.UTILS}
    out = broadcast_macro_beta(macro, ff12_map, SESSIONS, ["AAA", "BBB"])
    d = pd.Timestamp("2024-01-05")
    assert out.loc[d, "AAA"] == pytest.approx(
        FROZEN_BETA[(SicSector.DURBL, "nfp")] * 1.5
    )
    assert out.loc[d, "BBB"] == pytest.approx(
        FROZEN_BETA[(SicSector.UTILS, "nfp")] * 1.5
    )


def test_broadcast_multiple_events_same_session_sum() -> None:
    """Two events landing on the same session sum their signed shocks (union)."""
    macro = pd.DataFrame(
        [
            _macro_event("2024-01-04", "CPI", 2.0),
            _macro_event("2024-01-04", "NFP", 1.0),
        ]
    )
    ff12_map = {"AAA": SicSector.HLTH}
    out = broadcast_macro_beta(macro, ff12_map, SESSIONS, ["AAA"])
    d = pd.Timestamp("2024-01-04")
    expected = (
        FROZEN_BETA[(SicSector.HLTH, "cpi")] * 2.0
        + FROZEN_BETA[(SicSector.HLTH, "nfp")] * 1.0
    )
    assert out.loc[d, "AAA"] == pytest.approx(expected)


def test_broadcast_pub_date_off_grid_maps_forward_to_next_session() -> None:
    """A release on a non-session day maps to the next session (PIT: known then)."""
    macro = pd.DataFrame([_macro_event("2024-01-06", "CPI", 3.0)])  # Saturday
    ff12_map = {"AAA": SicSector.ENRGY}
    out = broadcast_macro_beta(macro, ff12_map, SESSIONS, ["AAA"])
    sat = pd.Timestamp("2024-01-06")
    next_session = SESSIONS[SESSIONS >= sat][0]  # Monday 2024-01-08
    assert next_session == pd.Timestamp("2024-01-08")
    assert out.loc[next_session, "AAA"] == pytest.approx(
        FROZEN_BETA[(SicSector.ENRGY, "cpi")] * 3.0
    )
    # the Saturday itself is not on the session grid
    assert sat not in out.index


# ---------------------------------------------------------------------------
# PIT — future pub_date excluded
# ---------------------------------------------------------------------------


def test_broadcast_excludes_pub_date_after_freeze() -> None:
    """An event published after the session grid's last date is NOT knowable."""
    macro = pd.DataFrame(
        [_macro_event("2024-12-31", "CPI", 2.0)]  # far after the grid
    )
    ff12_map = {"AAA": SicSector.HLTH}
    out = broadcast_macro_beta(macro, ff12_map, SESSIONS, ["AAA"])
    # the event never lands on the grid -> all NaN
    assert out["AAA"].isna().all()


def test_broadcast_nan_z_event_contributes_nan() -> None:
    """A release whose surprise_z is NaN (insufficient history) contributes NaN."""
    macro = pd.DataFrame([_macro_event("2024-01-04", "CPI", float("nan"))])
    ff12_map = {"AAA": SicSector.HLTH}
    out = broadcast_macro_beta(macro, ff12_map, SESSIONS, ["AAA"])
    assert pd.isna(out.loc[pd.Timestamp("2024-01-04"), "AAA"])


# ---------------------------------------------------------------------------
# shape + idempotent
# ---------------------------------------------------------------------------


def test_broadcast_shape_is_sessions_by_tickers() -> None:
    macro = pd.DataFrame([_macro_event("2024-01-04", "CPI", 2.0)])
    ff12_map = {"AAA": SicSector.HLTH, "BBB": SicSector.MONEY}
    out = broadcast_macro_beta(macro, ff12_map, SESSIONS, ["AAA", "BBB"])
    assert list(out.index) == list(SESSIONS)
    assert list(out.columns) == ["AAA", "BBB"]


def test_broadcast_idempotent() -> None:
    macro = pd.DataFrame([_macro_event("2024-01-04", "CPI", 2.0)])
    ff12_map = {"AAA": SicSector.HLTH}
    a = broadcast_macro_beta(macro, ff12_map, SESSIONS, ["AAA"])
    b = broadcast_macro_beta(macro, ff12_map, SESSIONS, ["AAA"])
    pd.testing.assert_frame_equal(a, b)


def test_broadcast_empty_macro_yields_all_nan_wide() -> None:
    macro = pd.DataFrame(columns=["event_type", "pub_date", "surprise_z"])
    ff12_map = {"AAA": SicSector.HLTH}
    out = broadcast_macro_beta(macro, ff12_map, SESSIONS, ["AAA"])
    assert out.shape == (len(SESSIONS), 1)
    assert out["AAA"].isna().all()
