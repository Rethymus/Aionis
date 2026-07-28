"""Reddit-sentiment forward-collection invariants — hermetic (no network, no creds).

Pins the three layers of :mod:`aionis.ingest.reddit_sentiment`:
  * ticker extraction (cashtag + bare, case-insensitive, universe-filtered),
  * sentiment aggregation (bull_ratio, sentiment_mean, score_sum),
  * snapshot append (two runs -> 2x rows, never overwrite) + raw archival
    sha256 + the exploratory/forward_only ledger row.

PRAW is replaced by a fake ``praw.Reddit`` returning synthetic submissions;
FinBERT is replaced by a deterministic keyword sentiment stub. Mirrors the
offline-fixture style of ``test_vix.py`` / ``test_macro_surprise.py``.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from aionis.ingest import reddit_sentiment as rs

# --- fake PRAW (synthetic submissions, newest-first) --------------------------


class _FakeSubRef:
    """``submission.subreddit`` stand-in whose ``str()`` is the sub name."""

    def __init__(self, name: str) -> None:
        self.display_name = name

    def __str__(self) -> str:
        return self.display_name


class _FakeSubmission:
    def __init__(self, **kw: object) -> None:
        self.__dict__.update(kw)


class _FakeSubreddit:
    def __init__(self, subs: list[_FakeSubmission]) -> None:
        # caller passes them newest-first already
        self._subs = subs

    def new(self, limit: int | None = None):
        return iter(self._subs if limit is None else self._subs[:limit])


class _FakeReddit:
    def __init__(self, by_sub: dict[str, list[_FakeSubmission]]) -> None:
        self._by_sub = by_sub

    def subreddit(self, name: str) -> _FakeSubreddit:
        return _FakeSubreddit(self._by_sub.get(name, []))


def _sub(
    title: str,
    *,
    selftext: str = "",
    score: int = 0,
    age_hours: float = 1.0,
    sub: str = "wallstreetbets",
    sid: str = "x",
) -> _FakeSubmission:
    return _FakeSubmission(
        id=sid,
        title=title,
        selftext=selftext,
        score=score,
        created_utc=datetime.now(tz=timezone.utc).timestamp() - age_hours * 3600.0,
        subreddit=_FakeSubRef(sub),
    )


# --- deterministic FinBERT stub (keyword -> fixed (pos, neg, neu) triple) ------


def _stub_sentiment(texts: list[str]) -> list[tuple[float, float, float]]:
    out: list[tuple[float, float, float]] = []
    for t in texts:
        tl = t.lower()
        if any(w in tl for w in ("moon", "bull", "buy", "long", "calls")):
            out.append((0.90, 0.05, 0.05))  # positive
        elif any(w in tl for w in ("crash", "bear", "sell", "short", "puts")):
            out.append((0.05, 0.90, 0.05))  # negative
        else:
            out.append((0.10, 0.10, 0.80))  # neutral
    return out


def _wire(
    monkeypatch: pytest.MonkeyPatch,
    fake_reddit: _FakeReddit,
    *,
    runs_dir: Path,
) -> None:
    """Inject the fake PRAW + stub FinBERT + zero politeness sleep + hermetic ledger."""
    monkeypatch.setattr(rs, "_connect_reddit", lambda *a, **k: fake_reddit)
    monkeypatch.setattr(rs, "_build_sentiment_fn", lambda cache_dir: _stub_sentiment)
    monkeypatch.setattr(rs, "_SUB_SLEEP", 0.0)
    monkeypatch.setattr(rs.settings, "runs_dir", runs_dir)


# --- ticker extraction --------------------------------------------------------


def test_ticker_extraction_cashtag_and_bare_case_insensitive() -> None:
    universe = {"AAPL", "MSFT", "TSLA"}
    text = "$AAPL to the moon; aapl again; $aapl lowercase; MSFT lagging"

    counts = rs._count_ticker_mentions(text, universe)

    # $AAPL + bare "aapl" + lowercase cashtag $aapl all resolve to AAPL = 3;
    # bare "MSFT" = 1; function words ignored; no false positives.
    assert counts == {"AAPL": 3, "MSFT": 1}


def test_ticker_extraction_ignores_non_universe_tokens() -> None:
    universe = {"AAPL"}
    # GME, TSLA, and every english word are NOT in the universe -> ignored.
    text = "$GME and $TSLA are ignored; buy calls the dog"

    counts = rs._count_ticker_mentions(text, universe)

    assert counts == {}


def test_ticker_extraction_empty_text() -> None:
    assert rs._count_ticker_mentions("", {"AAPL"}) == {}
    assert rs._count_ticker_mentions(None, {"AAPL"}) == {}  # type: ignore[arg-type]


# --- sentiment aggregation (pure) ---------------------------------------------


def test_aggregate_bull_ratio_sentiment_mean_score_sum() -> None:
    posts = [
        {"title": "$AAPL to the moon", "selftext": "", "score": 10},  # positive
        {"title": "AAPL and MSFT crashing", "selftext": "", "score": 5},  # negative
        {"title": "random chatter", "selftext": "no ticker here", "score": 1},  # none
    ]

    df = rs._aggregate_snapshot(
        posts, ["AAPL", "MSFT"], _stub_sentiment, "2026-07-28T00:00:00+00:00"
    )

    # columns + order pinned
    assert list(df.columns) == [
        "ticker", "mentions", "sentiment_mean", "bull_ratio", "score_sum", "snapshot_ts"
    ]
    by = df.set_index("ticker")

    # AAPL named in 2 posts (1 positive, 1 negative)
    assert int(by.loc["AAPL", "mentions"]) == 2
    assert by.loc["AAPL", "bull_ratio"] == pytest.approx(0.5)  # 1 pos / (1 pos + 1 neg)
    assert by.loc["AAPL", "sentiment_mean"] == pytest.approx((0.85 + (-0.85)) / 2)  # 0.0
    assert int(by.loc["AAPL", "score_sum"]) == 15  # 10 + 5

    # MSFT named in 1 (negative) post
    assert int(by.loc["MSFT", "mentions"]) == 1
    assert by.loc["MSFT", "bull_ratio"] == pytest.approx(0.0)
    assert by.loc["MSFT", "sentiment_mean"] == pytest.approx(-0.85)
    assert int(by.loc["MSFT", "score_sum"]) == 5


def test_aggregate_all_neutral_bull_ratio_is_nan() -> None:
    posts = [{"title": "AAPL earnings soon", "selftext": "", "score": 2}]  # neutral (no keyword)

    df = rs._aggregate_snapshot(posts, ["AAPL"], _stub_sentiment, "t")

    row = df.iloc[0]
    assert row["ticker"] == "AAPL"
    assert int(row["mentions"]) == 1
    assert pd.isna(row["bull_ratio"])  # pos+neg == 0 -> undefined -> NaN


def test_aggregate_empty_universe_raises() -> None:
    with pytest.raises(ValueError):
        rs._aggregate_snapshot([], [""], _stub_sentiment, "t")


# --- full collect: snapshot append, raw archival, ledger ----------------------


def test_missing_creds_raises_clear_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # No creds in args, none in env -> clear RuntimeError, never a silent fake pull.
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="Reddit credentials required"):
        rs.collect_reddit_sentiment(["AAPL"], cache_dir=tmp_path)


def test_collect_writes_snapshot_and_archives_raw_and_logs_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeReddit(
        {
            "wallstreetbets": [
                _sub("$AAPL to the moon", score=10, sid="a1"),
                _sub("MSFT crashing hard", score=4, sid="m1"),
            ],
            "stocks": [],
            "investing": [],
        }
    )
    _wire(monkeypatch, fake, runs_dir=tmp_path)
    cdir = tmp_path / "cache"

    df = rs.collect_reddit_sentiment(
        ["AAPL", "MSFT"], client_id="x", client_secret="y", cache_dir=cdir
    )

    # snapshot returned
    assert set(df["ticker"]) == {"AAPL", "MSFT"}
    assert list(df.columns) == [
        "ticker", "mentions", "sentiment_mean", "bull_ratio", "score_sum", "snapshot_ts"
    ]

    # cumulative parquet written
    pq = cdir / "reddit_snapshots.parquet"
    assert pq.exists()
    disk = pd.read_parquet(pq)
    assert len(disk) == 2

    # raw archival (immutable) + sha256 pinned in the ledger
    raws = list(cdir.glob("reddit_raw_*.json"))
    assert len(raws) == 1
    raw_payload = json.loads(raws[0].read_text())
    assert len(raw_payload) == 2  # both in-window posts archived
    assert {p["id"] for p in raw_payload} == {"a1", "m1"}

    ledger = (tmp_path / "ledger.jsonl").read_text().strip().splitlines()
    assert len(ledger) == 1
    row = json.loads(ledger[0])
    assert row["event"] == "data_ingest"
    assert row["dataset"] == "reddit_sentiment"
    assert row["source"] == "PRAW+FinBERT"
    assert row["license"] == "PRAW BSD-2 + FinBERT Apache + Reddit ToS (display, no-resale)"
    assert row["mode"] == "exploratory"
    assert row["forward_only"] is True
    assert row["n_tickers"] == 2
    assert row["n_posts"] == 2
    assert row["lookback_hours"] == 24
    assert row["subreddits"] == ["wallstreetbets", "stocks", "investing"]
    assert re.fullmatch(r"[0-9a-f]{64}", row["data_sha256"])
    assert "ts" in row


def test_collect_two_runs_append_never_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # run 1 sees AAPL; run 2 sees MSFT. Overwrite would leave 1 row; append leaves 2.
    cdir = tmp_path / "cache"
    pq = cdir / "reddit_snapshots.parquet"

    _wire(
        monkeypatch,
        _FakeReddit({"wallstreetbets": [_sub("$AAPL to the moon", sid="a1")]}),
        runs_dir=tmp_path,
    )
    rs.collect_reddit_sentiment(["AAPL", "MSFT"], client_id="x", client_secret="y", cache_dir=cdir)
    assert len(pd.read_parquet(pq)) == 1

    _wire(
        monkeypatch,
        _FakeReddit({"wallstreetbets": [_sub("MSFT crashing", sid="m1")]}),
        runs_dir=tmp_path,
    )
    rs.collect_reddit_sentiment(["AAPL", "MSFT"], client_id="x", client_secret="y", cache_dir=cdir)

    disk = pd.read_parquet(pq)
    assert len(disk) == 2  # appended, NOT overwritten
    assert set(disk["ticker"]) == {"AAPL", "MSFT"}

    ledger = (tmp_path / "ledger.jsonl").read_text().strip().splitlines()
    assert len(ledger) == 2  # one ingest row per run


def test_collect_lookback_filters_old_posts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # PRAW yields newest-first: fresh (1h) before old (200h). Default lookback=24h.
    fake = _FakeReddit(
        {
            "wallstreetbets": [
                _sub("$AAPL to the moon", age_hours=1.0, sid="fresh"),
                _sub("TSLA ancient", age_hours=200.0, sid="old"),
            ]
        }
    )
    _wire(monkeypatch, fake, runs_dir=tmp_path)
    cdir = tmp_path / "cache"

    df = rs.collect_reddit_sentiment(
        ["AAPL", "TSLA"], client_id="x", client_secret="y", cache_dir=cdir, lookback_hours=24
    )

    # the 200h-old TSLA post is outside the window -> not archived, not scored.
    assert set(df["ticker"]) == {"AAPL"}
    raw = json.loads(next(cdir.glob("reddit_raw_*.json")).read_text())
    assert [p["id"] for p in raw] == ["fresh"]


def test_collect_empty_window_returns_empty_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeReddit({"wallstreetbets": [], "stocks": [], "investing": []})
    _wire(monkeypatch, fake, runs_dir=tmp_path)
    cdir = tmp_path / "cache"

    df = rs.collect_reddit_sentiment(
        ["AAPL"], client_id="x", client_secret="y", cache_dir=cdir
    )

    assert list(df.columns) == [
        "ticker", "mentions", "sentiment_mean", "bull_ratio", "score_sum", "snapshot_ts"
    ]
    assert len(df) == 0
    # no snapshot parquet created on an empty window; raw still archived; ledger n_tickers=0
    assert not (cdir / "reddit_snapshots.parquet").exists()
    assert len(list(cdir.glob("reddit_raw_*.json"))) == 1
    row = json.loads((tmp_path / "ledger.jsonl").read_text().strip())
    assert row["n_tickers"] == 0
    assert row["n_posts"] == 0
