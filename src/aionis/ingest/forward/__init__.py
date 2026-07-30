"""E3 forward-live ingest — snapshot-on-arrival collectors (Slice 2).

Three PIT-as-of-t event-source collectors, each following the snapshot-on-arrival
discipline of :mod:`aionis.ingest.reddit_sentiment` (the project's forward-
collection exemplar). Together they let a month-end E3 commit FREEZE an ``I_t``
snapshot containing ONLY data with ``filed/released <= snapshot_ts`` — the data
spine for E3's "zero lookahead" guarantee (plan §1.1 piece 4, invariant I3).

  * :mod:`.stakes_13d_forward` — poll EDGAR ``submissions_{cik}.json`` for SC 13D /
    13D-A filings FILED in ``(last_poll_ts, snapshot_ts]`` (reuses
    :mod:`aionis.ingest.stakes_13d`).
  * :mod:`.macro_forward` — ALFRED scheduled-release (CPI/NFP) surprise as-of
    ``snapshot_ts`` (reuses :mod:`aionis.features.macro_surprise`).
  * :mod:`.earnings_8k_forward` — EDGAR 8-K Item 2.02 earnings releases, NET-NEW
    form-type filter (reuses :mod:`aionis.ingest.fundamentals` cik_map +
    :mod:`aionis.ingest.stakes_13d` submissions stack).

Forward differs from existing PIT ingest in ONE way (plan §1.1 piece 4): forward
= "as-of now, never revised, never backfilled." The first run starts the series
at its own ``snapshot_ts``; there is no historical reconstruction. Each collector
emits a ``(ticker/date, feature)`` long frame, writes an immutable raw archive
(sha256-pinned), appends to a cumulative parquet (concat — never overwrite), and
appends one ``data_ingest`` ledger row carrying ``forward_only: true`` +
``snapshot_ts``. The I3 monotonic-forward clock (``event_ts <= snapshot_ts``) is
asserted on every emitted row — the leakage gate for this slice.
"""
from __future__ import annotations

from aionis.ingest.forward import _common

__all__ = ["_common"]
