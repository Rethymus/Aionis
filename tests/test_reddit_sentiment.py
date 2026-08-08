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
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from xml.sax.saxutils import escape as _xml_escape

import pandas as pd
import pytest

from aionis.ingest import reddit_sentiment as rs
from aionis.ingest.http_policy import HostSpacingPolicy

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


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.headers: dict[str, str] = {}

    def request(self, method: str, url: str, **kwargs: object) -> object:
        self.calls.append((method, url, kwargs))
        return object()


class _FakeRequestor:
    def __init__(self, session: _FakeSession | None = None) -> None:
        self.session = session
        self.calls: list[tuple[str, str, dict]] = []

    def request(self, method: str, url: str, **kwargs: object) -> object:
        self.calls.append((method, url, kwargs))
        if self.session is not None:
            return self.session.request(method, url, **kwargs)
        return object()


# --- ticker extraction --------------------------------------------------------


def test_ticker_extraction_cashtag_any_case_and_uppercase_bare() -> None:
    universe = {"AAPL", "MSFT", "TSLA"}
    # $AAPL + $aapl (cashtags, any case) both count; bare "MSFT" UPPERCASE counts;
    # bare lowercase "aapl"/"msft"/"tsla" are English prose -> NOT counted.
    text = "$AAPL to the moon; aapl again; $aapl lowercase; MSFT lagging; msft?; tsla"

    counts = rs._count_ticker_mentions(text, universe)

    assert counts == {"AAPL": 2, "MSFT": 1}


def test_ticker_extraction_ignores_non_universe_tokens() -> None:
    universe = {"AAPL"}
    # GME, TSLA, and every english word are NOT in the universe -> ignored.
    text = "$GME and $TSLA are ignored; buy calls the dog"

    counts = rs._count_ticker_mentions(text, universe)

    assert counts == {}


def test_ticker_extraction_empty_text() -> None:
    assert rs._count_ticker_mentions("", {"AAPL"}) == {}
    assert rs._count_ticker_mentions(None, {"AAPL"}) == {}  # type: ignore[arg-type]


def test_ticker_extraction_short_ticker_requires_cashtag() -> None:
    # 1-3 char tickers (ARE, SO, NOW) collide with English words -> the bare word
    # is NOT counted; only the $TICKER cashtag is. Longer tickers (NVDA) bare-match.
    universe = {"ARE", "SO", "NOW", "NVDA"}
    text = "we are all so happy now; $ARE and $SO are hot; NVDA to the moon"

    counts = rs._count_ticker_mentions(text, universe)
    # bare "are"/"so"/"now" suppressed; cashtags counted; NVDA bare-word counted.
    assert counts == {"ARE": 1, "SO": 1, "NVDA": 1}


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
    # No creds in args, none in env -> the PRAW transport raises clearly, never a
    # silent fake pull. (auto/rss fall back to the zero-credential feed instead.)
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="Reddit credentials required"):
        rs.collect_reddit_sentiment(["AAPL"], cache_dir=tmp_path, transport="praw")


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


# --- shared PRAW host-spacing wrapper -----------------------------------------


def test_praw_requestor_reserves_host_slots_for_token_and_oauth_urls() -> None:
    clock = _FakeClock()
    spacing = HostSpacingPolicy(clock=clock.monotonic, sleeper=clock.sleep)
    session = _FakeSession()

    class _FakeSpacingRequestor(rs._SpacingRequestorMixin, _FakeRequestor):
        _spacing = spacing

    requestor = _FakeSpacingRequestor(session)

    requestor.request(
        "POST",
        "https://www.reddit.com/api/v1/access_token",
        data={"grant_type": "client_credentials"},
    )
    requestor.request(
        "GET",
        "https://oauth.reddit.com/r/wallstreetbets/new",
        params={"limit": 100},
    )

    assert [(method, url) for method, url, _ in session.calls] == [
        ("POST", "https://www.reddit.com/api/v1/access_token"),
        ("GET", "https://oauth.reddit.com/r/wallstreetbets/new"),
    ]
    assert clock.sleeps == []  # token and oauth hosts have independent slots


def test_praw_requestor_spaces_consecutive_pagination_requests() -> None:
    clock = _FakeClock()
    spacing = HostSpacingPolicy(clock=clock.monotonic, sleeper=clock.sleep)
    session = _FakeSession()

    class _FakeSpacingRequestor(rs._SpacingRequestorMixin, _FakeRequestor):
        _spacing = spacing

    requestor = _FakeSpacingRequestor(session)
    urls = [
        "https://oauth.reddit.com/r/wallstreetbets/new?limit=100",
        "https://oauth.reddit.com/r/wallstreetbets/new?after=t3_abc&limit=100",
        "https://oauth.reddit.com/r/wallstreetbets/new?after=t3_def&limit=100",
    ]

    for url in urls:
        requestor.request("GET", url)

    assert [url for _, url, _ in session.calls] == urls
    assert clock.sleeps == [2.0, 2.0]
    assert clock.now == 4.0


def test_connect_reddit_passes_requestor_class_through_praw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _RecordingSpacing:
        def __init__(self) -> None:
            self.urls: list[str] = []

        def wait(self, url: str) -> None:
            self.urls.append(url)

    captured: dict[str, object] = {}

    class _FakePraw:
        class Reddit:
            def __init__(self, **kwargs: object) -> None:
                captured.update(kwargs)

    spacing = _RecordingSpacing()
    monkeypatch.setattr(rs, "_HOST_SPACING_POLICY", spacing)
    monkeypatch.setitem(sys.modules, "praw", _FakePraw)
    monkeypatch.setitem(sys.modules, "prawcore", SimpleNamespace(Requestor=_FakeRequestor))

    rs._connect_reddit("client-id", "client-secret", "aionis/0.1 research")

    assert captured["client_id"] == "client-id"
    assert captured["client_secret"] == "client-secret"
    assert captured["user_agent"] == "aionis/0.1 research"
    requestor_class = captured["requestor_class"]
    assert requestor_class is not None
    requestor = requestor_class()
    requestor.request("GET", "https://oauth.reddit.com/r/stocks/new")
    assert spacing.urls == ["https://oauth.reddit.com/r/stocks/new"]


# --- zero-credential Atom RSS transport ---------------------------------------
#
# Reddit blocked unauthenticated .json (403, 2026) + gated new OAuth tokens
# (Responsible Builder Policy). The public /new.rss Atom feed is the surviving
# keyless path. These tests pin the RSS parsing + the rss/auto transports without
# touching the network (a canned Atom feed stands in for _fetch_feed).


def _iso(hours_ago: float = 0.0) -> str:
    return (
        datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)
    ).isoformat(timespec="seconds")


def _atom(entries: list[dict]) -> bytes:
    """Build a minimal Reddit-style Atom feed; HTML content is entity-escaped
    exactly as Reddit emits it (so defusedxml -> bs4 exercises the real path)."""
    parts = []
    for e in entries:
        sub = e.get("sub", "wallstreetbets")
        parts.append(
            "<entry>"
            f"<id>tag:reddit.com,/r/{sub}/comments/{e['id']}/x</id>"
            f"<title>{e['title']}</title>"
            f'<link href="https://www.reddit.com/r/{sub}/comments/{e["id"]}/x"/>'
            f"<updated>{e.get('updated', _iso())}</updated>"
            f"<author><name>/u/{e.get('author', 'tester')}</name></author>"
            f'<content type="html">{_xml_escape(e.get("content", ""))}</content>'
            "</entry>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        + "".join(parts)
        + "</feed>"
    ).encode()


class _FakeResp:
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code
        self.headers: dict[str, str] = {}


def _fake_fetch_factory(by_sub: dict[str, bytes]):
    """A stand-in for ``rs._fetch_feed`` serving canned Atom per subreddit."""
    empty = b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'

    def _fetch(url: str, user_agent: str) -> _FakeResp:
        for name, atom in by_sub.items():
            if f"/r/{name}/" in url:
                return _FakeResp(atom)
        return _FakeResp(empty)

    return _fetch


def _wire_rss(
    monkeypatch: pytest.MonkeyPatch,
    runs_dir: Path,
    *,
    fetch=None,
) -> None:
    """Inject stub FinBERT + zero politeness sleep + hermetic ledger + (opt) RSS fetch."""
    monkeypatch.setattr(rs, "_build_sentiment_fn", lambda cache_dir: _stub_sentiment)
    monkeypatch.setattr(rs, "_SUB_SLEEP", 0.0)
    monkeypatch.setattr(rs.settings, "runs_dir", runs_dir)
    if fetch is not None:
        monkeypatch.setattr(rs, "_fetch_feed", fetch)


def test_html_to_text_strips_reddit_content_html() -> None:
    html = '<!-- SC_OFF --><div class="md"><p>NVDA to the moon</p><p>buy calls</p></div>'
    assert rs._html_to_text(html) == "NVDA to the moon buy calls"
    assert rs._html_to_text("") == ""
    assert rs._html_to_text(None) == ""  # type: ignore[arg-type]


def test_parse_atom_extracts_fields_and_scores_zero() -> None:
    atom = _atom(
        [
            {
                "id": "abc123",
                "title": "$NVDA earnings beat",
                "content": "<p>NVDA guidance raised</p>",
                "updated": _iso(1.0),
            }
        ]
    )
    entries = rs._parse_atom_entries(atom)
    assert len(entries) == 1
    post = rs._entry_to_post(entries[0], "wallstreetbets")
    assert post["id"] == "abc123"  # extracted from the /comments/<id>/ link
    assert post["subreddit"] == "wallstreetbets"
    assert "NVDA earnings beat" in post["title"]
    assert "NVDA guidance raised" in post["selftext"]
    assert post["score"] == 0  # RSS carries no upvote count
    assert post["created_utc"] > 0


def test_resolve_transport_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    # explicit values pass through
    assert rs._resolve_transport("rss", None, None) == "rss"
    assert rs._resolve_transport("praw", "x", "y") == "praw"
    # auto: creds present -> praw; absent -> rss
    assert rs._resolve_transport("auto", "x", "y") == "praw"
    assert rs._resolve_transport("auto", None, None) == "rss"
    with pytest.raises(ValueError):
        rs._resolve_transport("bogus", None, None)


def test_pull_posts_rss_filters_by_lookback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rs, "_SUB_SLEEP", 0.0)
    atom = _atom(
        [
            {"id": "fresh1", "title": "$AAPL moon", "updated": _iso(1.0)},
            {"id": "oldold", "title": "$MSFT ancient", "updated": _iso(200.0)},
        ]
    )
    posts = rs._pull_posts_rss(
        ("wallstreetbets",),
        lookback_hours=24,
        user_agent="t",
        fetch=_fake_fetch_factory({"wallstreetbets": atom}),
    )
    by_id = {p["id"]: p for p in posts}
    assert set(by_id) == {"fresh1"}  # 200h-old dropped; default lookback 24h
    assert by_id["fresh1"]["score"] == 0


def test_pull_posts_rss_skips_failed_subreddit_and_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A 403/429-exhausted on one subreddit is logged + skipped; others collected.
    monkeypatch.setattr(rs, "_SUB_SLEEP", 0.0)

    def _fetch(url: str, user_agent: str) -> _FakeResp:
        if "/r/wallstreetbets/" in url:
            raise rs.HTTPStatusError(403, 1)
        return _FakeResp(_atom([{"id": "ss111", "title": "$TSLA", "updated": _iso(1.0)}]))

    posts = rs._pull_posts_rss(
        ("wallstreetbets", "stocks"),
        lookback_hours=24,
        user_agent="t",
        fetch=_fetch,
    )
    assert {p["id"] for p in posts} == {"ss111"}  # stocks still served


def test_pull_posts_rss_skips_malformed_feed_and_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A corrupt Atom payload on one subreddit is skipped; others still collected.
    monkeypatch.setattr(rs, "_SUB_SLEEP", 0.0)

    def _fetch(url: str, user_agent: str) -> _FakeResp:
        if "/r/wallstreetbets/" in url:
            return _FakeResp(b"<?xml version='1.0'?><feed><not-closed>")  # malformed
        return _FakeResp(_atom([{"id": "ok1234", "title": "$MSFT", "updated": _iso(1.0)}]))

    posts = rs._pull_posts_rss(
        ("wallstreetbets", "stocks"),
        lookback_hours=24,
        user_agent="t",
        fetch=_fetch,
    )
    assert {p["id"] for p in posts} == {"ok1234"}  # malformed WSB skipped, stocks served


def test_collect_rss_writes_snapshot_ledger_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    atom = _atom(
        [
            {
                "id": "a1",
                "title": "$AAPL to the moon",
                "content": "<p>calls</p>",
                "updated": _iso(1.0),
            },
            {"id": "m1", "title": "MSFT crashing hard", "content": "", "updated": _iso(2.0)},
        ]
    )
    _wire_rss(monkeypatch, tmp_path, fetch=_fake_fetch_factory({"wallstreetbets": atom}))
    cdir = tmp_path / "cache"

    df = rs.collect_reddit_sentiment(["AAPL", "MSFT"], transport="rss", cache_dir=cdir)

    assert set(df["ticker"]) == {"AAPL", "MSFT"}
    # score unavailable on RSS -> 0
    assert int(df.set_index("ticker").loc["AAPL", "score_sum"]) == 0

    # ledger: RSS source + transport + score_available honesty
    row = json.loads((tmp_path / "ledger.jsonl").read_text().strip())
    assert row["source"] == "RSS-atom+FinBERT (zero-credential)"
    assert row["transport"] == "rss"
    assert row["score_available"] is False
    assert row["forward_only"] is True
    assert row["n_tickers"] == 2

    # status sidecar for the terminal display
    sidecar = json.loads((cdir / "reddit_last_run.json").read_text())
    assert sidecar["transport"] == "rss"
    assert sidecar["score_available"] is False
    assert sidecar["n_tickers"] == 2


def test_collect_auto_without_creds_uses_rss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # default transport="auto" + no creds -> zero-credential RSS (not a raise).
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    atom = _atom([{"id": "a1", "title": "$AAPL to the moon", "updated": _iso(1.0)}])
    _wire_rss(monkeypatch, tmp_path, fetch=_fake_fetch_factory({"wallstreetbets": atom}))
    cdir = tmp_path / "cache"

    df = rs.collect_reddit_sentiment(["AAPL"], cache_dir=cdir)  # default auto -> rss

    assert set(df["ticker"]) == {"AAPL"}
    row = json.loads((tmp_path / "ledger.jsonl").read_text().strip())
    assert row["transport"] == "rss"  # auto fell back to the keyless feed
