"""Frozen sign-only macro β table + broadcast (E3 Slice 3a', macro channel).

DESIGN (ADR-009): the arm_e13 **macro channel is ZERO-LLM** — a FROZEN a-priori
sign-β table (sector × shock) multiplies the PIT ``surprise_z``, so the macro
causal shock is a pure sign-times-surprise with NO estimation DOF and NO LLM
text input. That dissolves the I5 leakage surface for the macro channel (no text
-> no LLM-memorized macro outcome -> no leakage). The table is a frozen literal:
it adds no rerun-to-significance lever and is bit-stable across reruns (H6).

The signs source Boudt-Neely-Sercu (Federal Reserve FEDS WP 2017-020,
"What Drives the Response of Sector Stock Returns to Macroeconomic
Announcements?"), Table 7 sector × announcement signs. The Federal Reserve FEDS
working-paper page is the canonical citation:

    https://www.federalreserve.gov/econres/feds/what-drives-the-response-of-sector-stock-returns-to-macroeconomic-announcements.htm

The Boudt-Neely Table 7 was NOT cleanly extractable from a single polite fetch
(SSRN 403'd the abstract page; the live table is behind a PDF), so per the
frozen plan's explicit fallback this is a **defensible qualitative prior**
(``FROZEN_BETA_STATUS = "exploratory-v1-qualitative"``) — economically motivated
sector×shock signs. The INVARIANT is that the table is FROZEN whatever its
values: a future headline-finalization (swapping in the exact Boudt-Neely signs)
is a versioned new ``FROZEN_BETA_VERSION``, never a silent mutation of this one.
"""

from __future__ import annotations

import hashlib
import json

import pandas as pd

from aionis.schema.causal_edge import SicSector

# ADJUDICATION (2026-09-02, owner-delegated, evidence-complete): the originally
# cited source ("Boudt-Neely-Sercu Fed WP 2017-020, Table 7") DOES NOT EXIST —
# FEDS WP 2017-020 is Reifschneider & Tulip (official PDF title-checked, kept in
# reports/audits/), and three independent Crossref sweeps (all Boudt+Neely
# co-authored works; Neely's full 2015-2019 output; exact-title matches) show no
# industry-level equity-response paper by these authors. The citation was a
# fabrication. The sign table is therefore OFFICIALLY FROZEN as a PROJECT-
# INTERNAL qualitative prior: zero estimation degrees of freedom (nothing is
# fitted to data — the property the E3 design wanted), with the economic
# rationale documented per sector below. Signs are unchanged from v1; only the
# provenance label is honest now.
FROZEN_BETA_SOURCE = (
    "Aionis project-internal qualitative prior (economic rationale in-code; "
    "the prior 'Boudt-Neely-Sercu 2017-020' citation was disproven/fabricated "
    "2026-09-02)"
)
FROZEN_BETA_VERSION = "qual-prior-v2"
FROZEN_BETA_STATUS = "frozen-qualitative-prior"

_SHOCK_FOR_EVENT_TYPE = {"CPI": "cpi", "NFP": "nfp"}


# ---------------------------------------------------------------------------
# FROZEN a-priori sign-β table (qualitative-v1 prior; signs only, no magnitude)
# ---------------------------------------------------------------------------
#
# Economic rationale (qualitative-v1, NOT headline-final):
#
# CPI surprise (unexpected INFLATION, higher = positive surprise):
#   * ENRGY +1  — energy prices co-move with inflation; resource pricing power.
#   * CHEMS +1  — materials pricing power with input-cost pass-through.
#   * NODUR +1  — consumer staples pass input costs through (pricing power).
#   * HLTH  +1  — defensive with pricing power; low inflation sensitivity.
#   * MONEY +1  — banks benefit from the higher rates that accompany inflation.
#   * DURBL -1  — consumer discretionary; real-income erosion + higher rates.
#   * SHOPS -1  — consumer discretionary retail; real-income erosion.
#   * MANUF -1  — input-cost pressure + rate sensitivity.
#   * BUSEQ -1  — long-duration growth cash flows; discount-rate sensitive.
#   * TELCM -1  — rate-sensitive.
#   * UTILS -1  — bond-proxy; rate-sensitive (strongly hurt by inflation prints).
#   * OTHER -1  — rate-sensitive services catch-all.
#
# NFP surprise (stronger EMPLOYMENT/payrolls -> strong economy + hawkish rates):
#   * DURBL +1, SHOPS +1, MANUF +1, BUSEQ +1 — pro-cyclical demand lift.
#   * MONEY +1  — strong economy -> credit growth + steeper curve (NIM).
#   * CHEMS +1  — cyclical demand.
#   * OTHER +1  — cyclical services.
#   * ENRGY -1  — inelastic demand; rate/USD effect dominates.
#   * NODUR -1  — defensive rotates out under strong economy + rate pressure.
#   * UTILS -1, TELCM -1 — bond-proxies; rate-sensitive.
#   * HLTH  -1  — defensive rotates out.
FROZEN_BETA: dict[tuple[SicSector, str], int] = {
    # --- CPI ---
    (SicSector.ENRGY, "cpi"): +1,
    (SicSector.CHEMS, "cpi"): +1,
    (SicSector.NODUR, "cpi"): +1,
    (SicSector.HLTH, "cpi"): +1,
    (SicSector.MONEY, "cpi"): +1,
    (SicSector.DURBL, "cpi"): -1,
    (SicSector.SHOPS, "cpi"): -1,
    (SicSector.MANUF, "cpi"): -1,
    (SicSector.BUSEQ, "cpi"): -1,
    (SicSector.TELCM, "cpi"): -1,
    (SicSector.UTILS, "cpi"): -1,
    (SicSector.OTHER, "cpi"): -1,
    # --- NFP ---
    (SicSector.DURBL, "nfp"): +1,
    (SicSector.SHOPS, "nfp"): +1,
    (SicSector.MANUF, "nfp"): +1,
    (SicSector.BUSEQ, "nfp"): +1,
    (SicSector.MONEY, "nfp"): +1,
    (SicSector.CHEMS, "nfp"): +1,
    (SicSector.OTHER, "nfp"): +1,
    (SicSector.ENRGY, "nfp"): -1,
    (SicSector.NODUR, "nfp"): -1,
    (SicSector.UTILS, "nfp"): -1,
    (SicSector.TELCM, "nfp"): -1,
    (SicSector.HLTH, "nfp"): -1,
}


# ---------------------------------------------------------------------------
# FROZEN_BETA_SHA256 - content hash of the literal sign table (I8 silent-mutation guard)
# ---------------------------------------------------------------------------
#
# The signs are a subjective qualitative prior; recording only
# ``FROZEN_BETA_VERSION`` (a string) in the config would let a sign flip WITHIN a
# version silently mutate the macro channel under one ``config_sha256`` — a
# rerun-to-significance vector. This content hash of the sign table closes that
# hole: any sign flip changes the hash -> flows into ``config_sha256`` (via
# :func:`build_forward_config`) -> a new forward sequence. The table is frozen, so
# this hash is bit-stable across reruns (H6).
FROZEN_BETA_SHA256 = hashlib.sha256(
    json.dumps(
        sorted(((s.value, sh, v) for (s, sh), v in FROZEN_BETA.items())),
        sort_keys=True,
    ).encode("utf-8")
).hexdigest()


def broadcast_macro_beta(
    macro_df: pd.DataFrame,
    ff12_map: dict[str, SicSector],
    sessions: pd.DatetimeIndex,
    tickers: list[str],
) -> pd.DataFrame:
    """Frozen sign-β broadcast of macro surprises -> wide (sessions x tickers).

    For each macro release in ``macro_df`` (Slice-2 ``collect_macro_forward``
    shape: ``[event_type, pub_date, surprise_z, ...]``) with ``pub_date`` on/before
    the freeze (the session grid's last date — PIT), assigns each sector member
    ``FROZEN_BETA[(ff12_map[ticker], shock)] * surprise_z`` at the event's session.

    * **shock** is derived from ``event_type`` (CPI -> "cpi", NFP -> "nfp"); any
      other event type is ignored (the macro channel is CPI/NFP-only).
    * **event session**: ``pub_date`` is forward-mapped to the first session on/after
      it (a weekend/holiday release is knowable at the next NYSE session — PIT).
    * **union over events**: two events on the same session SUM their signed
      shocks (a CPI + NFP same-day release contributes both signed surprises).
    * **PIT**: events with ``pub_date`` after ``sessions.max()`` (the freeze date)
      never land on the grid and are excluded — they are not yet knowable.

    Returns a wide frame (``sessions`` index, ``tickers`` columns), NaN where no
    signed shock applies (event-time feature, NOT carried forward). A ticker with
    no ``ff12_map`` entry gets no macro shock (no sector -> no sign).
    """
    sessions = pd.DatetimeIndex(sessions).normalize()
    out = pd.DataFrame(
        float("nan"), index=sessions, columns=list(tickers)
    )
    if macro_df.empty:
        return out
    freeze = sessions.max()

    for r in macro_df.itertuples(index=False):
        etype = getattr(r, "event_type", None)
        shock = _SHOCK_FOR_EVENT_TYPE.get(etype)
        if shock is None:
            continue  # macro channel is CPI/NFP-only
        pub = pd.Timestamp(r.pub_date)
        if pd.isna(pub):
            continue
        pub = pub.normalize()
        if pub > freeze:
            continue  # PIT: not yet knowable at the freeze
        z = getattr(r, "surprise_z", float("nan"))
        z_val = float(z) if not pd.isna(z) else float("nan")
        # forward-map pub_date to the first session on/after it (PIT: known then)
        fwd = sessions[sessions >= pub]
        if len(fwd) == 0:
            continue  # pub after the grid — excluded by PIT above, defensive
        d = fwd[0]
        for tkr, sector in ff12_map.items():
            if tkr not in out.columns:
                continue
            sign = FROZEN_BETA[(sector, shock)]
            contribution = sign * z_val
            cur = out.loc[d, tkr]
            out.loc[d, tkr] = contribution if pd.isna(cur) else cur + contribution
    return out


__all__ = [
    "FROZEN_BETA",
    "FROZEN_BETA_SOURCE",
    "FROZEN_BETA_VERSION",
    "FROZEN_BETA_STATUS",
    "FROZEN_BETA_SHA256",
    "broadcast_macro_beta",
]
