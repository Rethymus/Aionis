"""Synthetic data generators for tests and the no-key smoke pipeline.

These let the entire experiment machinery (alignment, design matrix, CV,
metrics, models, controls) be exercised and verified without network access or
API keys. Realistic-enough structure (random-walk prices, dated events at
plausible intraday times) — not realistic returns.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.features.alignment import NYSE_TZ, session_close_ts

_INTRADAY_TIMES = ("08:30", "14:00")  # CPI/NFP pre-open, FOMC intraday


def make_synthetic_prices(
    sessions: pd.DatetimeIndex,
    symbols: list[str],
    seed: int = 0,
    drift: float = 0.0003,
    vol: float = 0.012,
) -> pd.DataFrame:
    """Wide adjusted-close DataFrame: index = session date, columns = symbols."""
    rng = np.random.default_rng(seed)
    n = len(sessions)
    data: dict[str, np.ndarray] = {}
    for i, sym in enumerate(symbols):
        shocks = rng.normal(drift, vol, size=n)
        # Stagger starting prices so symbols are distinguishable.
        path = 100.0 * (1.0 + 0.01 * i) * np.cumprod(1.0 + shocks)
        data[sym] = path
    return pd.DataFrame(data, index=pd.DatetimeIndex(sessions))


def make_synthetic_events(
    sessions: pd.DatetimeIndex,
    n: int,
    event_types: tuple[str, ...] = ("FOMC", "CPI", "NFP"),
    seed: int = 1,
) -> pd.DataFrame:
    """Dated events at plausible release times, on/within the session grid."""
    rng = np.random.default_rng(seed)
    # Drop the first/last few sessions so t_info and label_end always exist.
    pool = sessions[5 : len(sessions) - 5]
    chosen = rng.choice(pool, size=min(n, len(pool)), replace=False)
    rows: list[dict] = []
    for d in np.sort(chosen):
        etype = rng.choice(event_types)
        d = pd.Timestamp(d).tz_localize(None).normalize()
        time = rng.choice(_INTRADAY_TIMES)
        hour, minute = (int(x) for x in time.split(":"))
        event_ts = (d + pd.Timedelta(hours=hour, minutes=minute)).tz_localize(NYSE_TZ)
        rows.append(
            {
                "event_id": f"{etype}_{d:%Y%m%d}",
                "event_type": str(etype),
                "event_ts": event_ts,
            }
        )
    return pd.DataFrame(rows).drop_duplicates("event_id").reset_index(drop=True)


def make_synthetic_event_text(events: pd.DataFrame, seed: int = 2) -> pd.DataFrame:
    """Plausible structural text per event for testing extraction without a key.

    The text is deliberately outcome-free (no price moves), mirroring the
    as-released primary-document contract.
    """
    rng = np.random.default_rng(seed)
    verbs = {
        "FOMC": ["hold", "raise", "cut"],
        "CPI": ["report", "release"],
        "NFP": ["report", "release"],
    }
    rows = []
    for ev in events.itertuples(index=False):
        verb = rng.choice(verbs.get(ev.event_type, ["announce"]))
        rows.append(
            {
                "event_id": ev.event_id,
                "text": (
                    f"The {ev.event_type} release on {ev.event_ts:%Y-%m-%d}: "
                    f"the committee voted to {verb} its policy stance. "
                    f"This is a structural description with no market outcome."
                ),
            }
        )
    return pd.DataFrame(rows)


__all__ = [
    "make_synthetic_prices",
    "make_synthetic_events",
    "make_synthetic_event_text",
    "session_close_ts",
]
