"""Point-in-time macro-surprise features (CPI / NFP) from ALFRED vintages.

Survey consensus (Bloomberg / Blue Chip) is proprietary, so the expectation is
*statistical*: a trailing mean of past first-print changes built ONLY from
vintages published strictly before each release. Statistical / autoregressive
expectations are the recognized fallback when survey consensus is unavailable
in the announcement-effects literature (Pearce-Roley 1985 explicitly compare
survey vs time-series expectations; Scotti 2016 builds real-time surprise
indexes from first prints), and standardizing by a trailing surprise std
follows Balduzzi-Elton-Green 2001 / Bauer-Swanson.

Timing model: the surprise for the release at time r is REVEALED AT r
(08:30 ET) — an event-time feature like the ERL text (known after t_info,
before label_start). The leakage rule here is therefore not "closes <= t_info"
but: every component of the expectation (and of the z denominator) must be
computable from vintages published STRICTLY BEFORE r; the only value dated r
is the single first print being differenced. That makes
``actual − expectation`` exactly the new information in the release.

Construction per series (CPIAUCSL → MoM %, PAYEMS → MoM diff, thousands):
the first print of reference month m is the vintage of m with minimum
``realtime_start``; the prior-month base is the LATEST vintage of m−1
published strictly before r (the value markets knew — possibly a revision);
expectation = trailing mean of the last 12 actual changes strictly before r
(min 6, else NaN); z = raw surprise / trailing std (ddof=1) of the last 24 raw
surprises strictly before r (min 12, else NaN), clipped to ±5. Strictness is
enforced structurally: ``shift(1)`` before every ``rolling`` on the
publication-ordered series, and ``merge_asof(..., allow_exact_matches=False)``
for the prior-month vintage.

Raw ALFRED JSON is cached at ``data/cache/alfred_{series_id}.json``; a cache
hit makes no HTTP call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pandas as pd
import structlog

from aionis.features.alignment import NYSE_TZ
from aionis.ingest.universe import _policy_get

log = structlog.get_logger()

_ALFRED_OBS_URL = "https://api.stlouisfed.org/fred/series/observations"
_REALTIME_START = "2000-01-01"
_REALTIME_END = "9999-12-31"
_PAGE_LIMIT = 100_000  # FRED hard cap per request; page with offset past it

# event_type -> (ALFRED series_id, month-over-month change kind)
SERIES_FOR_EVENT_TYPE: dict[str, tuple[str, Literal["pct", "diff"]]] = {
    "CPI": ("CPIAUCSL", "pct"),  # index level -> MoM % change
    "NFP": ("PAYEMS", "diff"),  # level in thousands -> MoM change in thousands
}
# Inverse lookup (series_id -> change_kind) for the date-broadcast helper.
_CHANGE_KIND_FOR_SERIES: dict[str, Literal["pct", "diff"]] = {
    sid: kind for (_et, (sid, kind)) in SERIES_FOR_EVENT_TYPE.items()
}

EXPECTATION_WINDOW = 12  # trailing actual changes forming the expectation
EXPECTATION_MIN = 6  # fewer strictly-prior changes -> NaN expectation
Z_WINDOW = 24  # trailing raw surprises in the z denominator
Z_MIN = 12  # fewer strictly-prior raw surprises -> NaN z
Z_CLIP = 5.0  # |z| cap so one fat-tailed print cannot dominate the design matrix
MATCH_TOLERANCE_DAYS = 1
MAX_UNMATCHED_SHARE = 0.20


def _download_vintages(series_id: str, fred_api_key: str) -> dict:
    """Full vintage archive for one series (paged; FRED caps rows per request)."""
    observations: list[dict] = []
    offset = 0
    while True:
        params = {
            "series_id": series_id,
            "api_key": fred_api_key,
            "file_type": "json",
            "realtime_start": _REALTIME_START,
            "realtime_end": _REALTIME_END,
            "limit": _PAGE_LIMIT,
            "offset": offset,
        }
        resp = _policy_get(_ALFRED_OBS_URL, params=params, timeout=60)
        resp.raise_for_status()
        rows = resp.json().get("observations", [])
        observations.extend(rows)
        offset += len(rows)
        if len(rows) < _PAGE_LIMIT:
            break
    log.info("alfred_downloaded", series_id=series_id, n_obs=len(observations))
    return {"observations": observations}


def fetch_alfred_vintages(series_id: str, fred_api_key: str, cache_dir: Path) -> pd.DataFrame:
    """Vintage frame [ref_date, realtime_start, value] from cache or ALFRED.

    ``ref_date`` is the reference period (month start for CPIAUCSL/PAYEMS) and
    ``realtime_start`` the publication date of that vintage. Missing values
    (FRED serializes them as ".") are dropped.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"alfred_{series_id}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
        log.info("alfred_cache_hit", series_id=series_id, path=str(cache_file))
    else:
        payload = _download_vintages(series_id, fred_api_key)
        cache_file.write_text(json.dumps(payload))
        log.info("alfred_cache_written", series_id=series_id, path=str(cache_file))

    rows = payload.get("observations", [])
    if not rows:
        raise RuntimeError(f"ALFRED returned no observations for {series_id!r}")
    df = (
        pd.DataFrame(
            {
                "ref_date": pd.to_datetime([r["date"] for r in rows]),
                "realtime_start": pd.to_datetime([r["realtime_start"] for r in rows]),
                "value": pd.to_numeric([r.get("value") for r in rows], errors="coerce"),
            }
        )
        .dropna(subset=["value"])
        .reset_index(drop=True)
    )
    if df.empty:
        raise RuntimeError(f"ALFRED observations for {series_id!r} are all missing values")
    return df


def first_print_changes(
    vintages: pd.DataFrame, change_kind: Literal["pct", "diff"]
) -> pd.DataFrame:
    """First print per reference month and its MoM change vs the pre-release base.

    Returns one row per reference month, sorted by publication date, columns
    [ref_date, pub_date, first_print, prior_pub, prior_value, actual_change].
    The prior-month base is the latest vintage of m−1 with
    ``realtime_start`` strictly before the release (``allow_exact_matches=False``
    — a revision republished on release day itself must not be used).
    """
    fp_idx = vintages.groupby("ref_date")["realtime_start"].idxmin()
    fp = (
        vintages.loc[fp_idx]
        .rename(columns={"realtime_start": "pub_date", "value": "first_print"})
        .sort_values("pub_date")
        .reset_index(drop=True)
    )
    # Month starts by construction for CPIAUCSL/PAYEMS -> previous month start.
    fp["prior_ref"] = (fp["ref_date"].dt.to_period("M") - 1).dt.to_timestamp()

    prior_pool = (
        vintages.rename(
            columns={"ref_date": "prior_ref", "realtime_start": "prior_pub", "value": "prior_value"}
        )
        .sort_values("prior_pub")
        .reset_index(drop=True)
    )
    merged = pd.merge_asof(
        fp,
        prior_pool,
        left_on="pub_date",
        right_on="prior_pub",
        by="prior_ref",
        direction="backward",
        allow_exact_matches=False,  # strictly before r
    )
    if change_kind == "pct":
        merged["actual_change"] = (merged["first_print"] / merged["prior_value"] - 1.0) * 100.0
    elif change_kind == "diff":
        merged["actual_change"] = merged["first_print"] - merged["prior_value"]
    else:
        raise ValueError(f"unknown change_kind {change_kind!r}")
    cols = ["ref_date", "pub_date", "first_print", "prior_pub", "prior_value", "actual_change"]
    return merged[cols]


def surprise_time_series(changes: pd.DataFrame) -> pd.DataFrame:
    """Expectation, raw surprise and clipped z per release, strictly point-in-time.

    Rows are ordered by ``pub_date``; every ``shift(1)`` before a ``rolling``
    guarantees the window at release r contains only releases published
    strictly before r (this is the invariant the no-lookahead test perturbs).
    """
    ts = changes.sort_values("pub_date").reset_index(drop=True)
    prior_changes = ts["actual_change"].shift(1)
    ts["expectation"] = prior_changes.rolling(
        EXPECTATION_WINDOW, min_periods=EXPECTATION_MIN
    ).mean()
    ts["raw_surprise"] = ts["actual_change"] - ts["expectation"]
    ts["surprise_scale"] = (
        ts["raw_surprise"].shift(1).rolling(Z_WINDOW, min_periods=Z_MIN).std(ddof=1)
    )
    ts["surprise_z"] = (ts["raw_surprise"] / ts["surprise_scale"]).clip(-Z_CLIP, Z_CLIP)
    return ts


def _event_dates(event_ts: pd.Series) -> pd.Series:
    """Calendar date (naive, normalized) of each event in ET."""
    if event_ts.dt.tz is not None:
        event_ts = event_ts.dt.tz_convert(NYSE_TZ).dt.tz_localize(None)
    return event_ts.dt.normalize()


def build_surprise_features(
    events: pd.DataFrame,
    fred_api_key: str,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """One row per event_id: [surprise_z, has_surprise] (floats, zero-filled).

    CPI/NFP events are matched to a first-print publication on the same
    calendar date, or up to one day PRIOR (backward-only: a release dated after
    the event is future information). Each tolerant match is logged. FOMC events
    carry no data-release surprise -> 0.0/0.0. Unmatched CPI/NFP events or
    NaN z (insufficient strictly-prior history) -> 0.0/0.0 with a warning; if
    more than 20% of CPI+NFP events fail *date matching*, the matching logic
    is broken and this raises rather than silently degrading the experiment.
    """
    required = {"event_id", "event_type", "event_ts"}
    if missing := required - set(events.columns):
        raise ValueError(f"events frame missing columns: {sorted(missing)}")
    if events["event_id"].duplicated().any():
        raise ValueError("events frame has duplicate event_ids")
    if cache_dir is None:
        from aionis.config import settings

        cache_dir = settings.data_dir / "cache"

    out = pd.DataFrame(
        {"surprise_z": 0.0, "has_surprise": 0.0},
        index=pd.Index(events["event_id"].to_numpy(), name="event_id"),
    )
    # BACKWARD-ONLY: offset 0 is the event's own release (the surprise is
    # revealed AT event_ts, before label_start — PIT-valid per the design); -1d
    # tolerates a schedule mismatch where the event frame predates the print. A
    # forward (+1d) offset would attach a not-yet-published surprise -> lookahead.
    offsets = [pd.Timedelta(days=-d) for d in range(MATCH_TOLERANCE_DAYS + 1)]
    unmatched: list[str] = []
    nan_z: list[str] = []
    n_macro = 0

    for event_type, (series_id, change_kind) in SERIES_FOR_EVENT_TYPE.items():
        subset = events.loc[events["event_type"] == event_type]
        if subset.empty:
            continue
        n_macro += len(subset)
        vintages = fetch_alfred_vintages(series_id, fred_api_key, cache_dir)
        ts = surprise_time_series(first_print_changes(vintages, change_kind))
        # Government-shutdown catch-up releases first-print two ref months on one
        # pub_date; keep the most recent ref month (the headline) and log it, so
        # the silent dict-collapse cannot attach the wrong ref month's surprise.
        dup = ts.loc[ts["pub_date"].duplicated(keep=False), "pub_date"]
        if not dup.empty:
            log.warning(
                "surprise_duplicate_pub_date",
                series_id=series_id,
                pub_dates=sorted(dup.dt.strftime("%Y-%m-%d").unique().tolist()),
            )
        ts_headline = ts.sort_values(["pub_date", "ref_date"]).drop_duplicates(
            "pub_date", keep="last"
        )
        z_by_pub = dict(zip(ts_headline["pub_date"], ts_headline["surprise_z"], strict=True))

        dates = _event_dates(subset["event_ts"])
        for event_id, event_date in zip(subset["event_id"], dates, strict=True):
            pub = next((event_date + o for o in offsets if event_date + o in z_by_pub), None)
            if pub is None:
                unmatched.append(event_id)
                continue
            if pub != event_date:
                log.info(
                    "surprise_tolerant_match",
                    event_id=event_id,
                    pub_date=str(pub.date()),
                    event_date=str(event_date.date()),
                )
            z = z_by_pub[pub]
            if pd.isna(z):
                nan_z.append(event_id)
                continue
            out.loc[event_id] = [float(z), 1.0]

    if unmatched or nan_z:
        log.warning(
            "surprise_zero_filled",
            n_unmatched=len(unmatched),
            unmatched=unmatched,
            n_nan_z=len(nan_z),
            nan_z=nan_z,
        )
    if n_macro and len(unmatched) / n_macro > MAX_UNMATCHED_SHARE:
        raise RuntimeError(
            f"macro-surprise matching failed: {len(unmatched)}/{n_macro} CPI+NFP events "
            f"({len(unmatched) / n_macro:.0%}) have no first print within "
            f"±{MATCH_TOLERANCE_DAYS} day — the date matching is broken: {unmatched}"
        )
    log.info(
        "surprise_features_built",
        n_events=len(out),
        n_macro=n_macro,
        n_with_surprise=int(out["has_surprise"].sum()),
    )
    return out


def macro_surprise_date_broadcast(
    series_id: str,
    as_of_dates: pd.DatetimeIndex,
    fred_api_key: str,
    cache_dir: Path | None = None,
    *,
    name: str | None = None,
) -> pd.Series:
    """Date-broadcast macro surprise for the Phase C selection panel.

    Phase C consumes the macro surprise as a *cross-section-broadcast* feature
    (one value per session, identical across tickers) — not event-keyed. This
    builds the per-release ``surprise_z`` with the *same* construction as
    :func:`build_surprise_features`, then carries it forward to each as-of date
    with a backward ``merge_asof``: the value at ``d`` is the surprise of the
    most recent release published on or before ``d``; NaN before the first
    release with a computable ``surprise_z``.

    This is the PIT broadcast rule of ``docs/phase-c-preregistration.md`` §8 — a
    release published at ``r`` is knowable at every ``d >= r`` and NEVER at
    ``d < r`` (this is *not* price forward-fill; it is the legitimate "last known
    macro surprise", PIT-correct because the surprise revealed at ``r`` remains
    the latest knowable value until the next release). ``as_of_dates`` MUST be
    sorted ascending (the session grid is).

    Returns a date-indexed :class:`~pandas.Series` ready to hand to
    :func:`aionis.features.selection_panel.build_selection_panel` via the
    ``macro=`` argument (assemble multiple into one date-indexed frame).
    """
    if cache_dir is None:
        from aionis.config import settings

        cache_dir = settings.data_dir / "cache"
    change_kind = _CHANGE_KIND_FOR_SERIES.get(series_id)
    if change_kind is None:
        raise ValueError(
            f"no change_kind registered for series_id {series_id!r} "
            f"(known: {sorted(_CHANGE_KIND_FOR_SERIES)})"
        )
    vintages = fetch_alfred_vintages(series_id, fred_api_key, cache_dir)
    ts = surprise_time_series(first_print_changes(vintages, change_kind))
    # One surprise_z per pub_date: a catch-up release first-prints two ref months
    # on one pub_date; keep the headline (most recent ref month), same discipline
    # as build_surprise_features. Drop NaN-z releases (insufficient strictly-prior
    # history) so the broadcast is NaN until a real surprise exists.
    head = (
        ts.dropna(subset=["surprise_z"])
        .sort_values(["pub_date", "ref_date"])
        .drop_duplicates("pub_date", keep="last")[["pub_date", "surprise_z"]]
        .sort_values("pub_date")
    )
    dates = pd.DatetimeIndex(as_of_dates).normalize()
    head["pub_date"] = head["pub_date"].dt.normalize()
    left = pd.DataFrame({"date": dates})
    right = head.rename(columns={"pub_date": "date"})
    m = pd.merge_asof(left, right, on="date", direction="backward")
    out = pd.Series(
        m["surprise_z"].to_numpy(), index=dates,
        name=name or f"macro_{series_id.lower()}_surprise",
    )
    log.info(
        "macro_surprise_broadcast_built",
        series_id=series_id, n=len(out), n_valid=int(out.notna().sum()),
    )
    return out
