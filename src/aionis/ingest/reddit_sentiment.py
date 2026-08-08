"""Retail-sentiment forward-collection (Reddit mentions + FinBERT sentiment).

This is the third retail-attention series for the market-driver framework
(``docs/market-driver-framework.md`` main lines ③/⑤): retail attention is modeled
as mention volume + sentiment, following the xiaoyinsi-informed methodology.

**Forward-collection only — NO historical backfill.** There is no permissively-
licensed historical Reddit/StockTwits corpus (Pushshift died 2023; StockTwits has
no backfill; ``arctic_shift`` is unlicensed). The only PIT-honest path is to
snapshot-on-arrival from today. This module accumulates ONE snapshot per run; it
never reconstructs the past.

**Dual transport** (selected by ``transport=`` on :func:`collect_reddit_sentiment`):
  * ``"praw"`` — OAuth2 script-app (``REDDIT_CLIENT_ID``/``SECRET``); carries post
    ``score``. The historical default.
  * ``"rss"`` — zero-credential public Atom feed (``/new.rss``). Reddit blocked
    unauthenticated ``.json`` (403, 2026) and gated new OAuth tokens behind the
    Responsible Builder Policy, so the Atom feed is the one surviving keyless
    path. It is Reddit's OWN published subscription format (ToS-clean for
    low-rate feed-reader use, unlike the ``.json``-without-auth hack). It carries
    the full post body (``<content type="html">``) but NOT ``score`` (recorded 0).
  * ``"auto"`` (default) — PRAW when creds resolve, else RSS; lets the collector
    run the moment OAuth is unavailable and auto-upgrade when creds appear.

Intake-rubric clearance (``docs/data-intake-rubric.md``):
  * **G1** — PRAW is BSD-2-Clause; FinBERT (ProsusAI/finbert GitHub) is Apache-2.0;
    both on the license allowlist. Reddit content is governed by Reddit ToS
    (display, no-resale) — ``mode: exploratory``.
  * **G2** — every snapshot carries a UTC ``snapshot_ts``; it is the value known
    at collection time (no future info). Forward-collected by construction.
  * **G3** — each raw pull is sha256-archived to ``data/cache/reddit_raw_<ts>.json``
    and is immutable; a later pull with different content is a NEW snapshot, never
    an overwrite. There is no provider revision because there is no historical
    series being republished.
  * **G4** — raw + snapshot are cache-pinned; ledger row records the data sha256.
  * **G5** — ``mode: exploratory``; does NOT enter confirmatory / Phase-B.
  * **G6** — retail-attention data is selection-biased (which tickers get
    discussed); declared as a scope limit, never ground truth.
  * **G7** — PRAW path: descriptive User-Agent, shared ≥2s host spacing via a
    custom requestor, 1.5s sleep between subreddit pulls (PRAW honors Reddit's
    100 QPM + ToS). RSS path: Reddit's published Atom subscription feed consumed
    at low rate through the SAME shared ≥2s host-spacing policy + bounded 429
    retry (no scrape, no key) — ToS-clean where the ``.json``-without-auth hack
    is not.

Reuses the project's existing extraction stack (``transformers``+``torch`` arrive
via the ``extraction`` extra's ``sentence-transformers``) for FinBERT — no new
heavy dependency. Weights lazy-download into ``data/cache/``.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import ParseError as _AtomParseError

import pandas as pd
import requests
import structlog

from aionis.config import settings
from aionis.ingest import universe
from aionis.ingest.http_policy import HostSpacingPolicy, HTTPStatusError

log = structlog.get_logger()

_HOST_SPACING_POLICY = universe._HTTP_POLICY.spacing

# --- tunables -----------------------------------------------------------------

_DEFAULT_SUBREDDITS = ("wallstreetbets", "stocks", "investing")
_FINBERT_MODEL = "ProsusAI/finbert"  # Apache-2.0 (producing repo)
_PULL_LIMIT = 1000  # Reddit listing hard cap; newest-first, early-stop past window
_SUB_SLEEP = 1.5  # politeness: 1-2s between subreddit pulls (G7)
_SENT_BATCH = 32
_MAX_TOKENS = 256  # FinBERT input truncation (post titles + bodies are short)
_SNAPSHOT_COLS = [
    "ticker",
    "mentions",
    "sentiment_mean",
    "bull_ratio",
    "score_sum",
    "snapshot_ts",
]

# Match a cashtag ``$TICKER`` (group 1) OR a bare alphabetic word token (group 2).
# finditer consumes the whole ``$AAPL`` via group 1, so the bare alternative never
# re-matches the symbol inside a cashtag.
_TOKEN_RE = re.compile(r"\$([A-Za-z]+)|\b([A-Za-z]+)\b")
# Bare-word matches require UPPERCASE (WSB ticker convention) AND length >= this.
# Reddit prose is lowercase, so case-insensitive bare matching counted English
# words (well/tech/cost/more) as the WELL/TECH/COST/MORE tickers. Verified on a
# real r/wallstreetbets /new pull (2026-08-08): real tickers appear UPPERCASE
# (PLTR/SMCI/TTWO), English words lowercase — case is the disambiguator. The
# length floor guards short all-caps title words (ARE/SO/AM).
_MIN_BARE_TICKER_LEN = 4


# --- shared cache / ledger helpers (mirrors ingest.vix / ingest.fundamentals) --


def _cache_dir(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ledger_path() -> Path:
    return settings.runs_dir / "ledger.jsonl"


def _append_ingest_ledger(payload: dict) -> None:
    """Append one ``data_ingest`` row to ``runs/ledger.jsonl`` (append-only).

    Matches ``reporting.run_log.log_run`` / ``ingest.vix`` discipline: one JSON
    line, UTC ``ts`` at second precision, never overwrite."""
    ledger = _ledger_path()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"), **payload}
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")
    log.info("reddit_ingest_logged", ledger=str(ledger), dataset=payload.get("dataset"))


# --- credentials --------------------------------------------------------------

_ENV_ID = "REDDIT_CLIENT_ID"
_ENV_SECRET = "REDDIT_CLIENT_SECRET"


def _resolve_creds(client_id: str | None, client_secret: str | None) -> tuple[str, str]:
    """Resolve Reddit creds from args, then env (``.env`` loaded via dotenv).

    Raises a clear error if absent — never silently fakes a pull."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:  # pragma: no cover - dotenv is a transitive dep; if missing, env-only
        pass
    cid = client_id or os.environ.get(_ENV_ID)
    csec = client_secret or os.environ.get(_ENV_SECRET)
    if not (cid and csec):
        raise RuntimeError(
            "Reddit credentials required for forward-collection: set "
            f"{_ENV_ID} / {_ENV_SECRET} in .env (or pass client_id/client_secret). "
            "Create a script-app at https://www.reddit.com/prefs/apps. This module "
            "never fakes a pull and never backfills history."
        )
    return cid, csec


# --- I/O seams (monkeypatch targets for hermetic tests) -----------------------


class _SpacingRequestorMixin:
    """Reserve a shared host slot before delegating each request URL."""

    _spacing: HostSpacingPolicy

    def request(self, *args, **kwargs):
        url = kwargs.get("url")
        if url is None and len(args) >= 2:
            url = args[1]
        if not isinstance(url, str):
            raise TypeError("PRAW request must include a URL")
        self._spacing.wait(url)
        return super().request(*args, **kwargs)


def _spacing_requestor_class(spacing: HostSpacingPolicy | None = None):
    """Build a ``prawcore.Requestor`` subclass bound to ``spacing``."""
    if spacing is None:
        spacing = _HOST_SPACING_POLICY
    from prawcore import Requestor

    class _PrawSpacingRequestor(_SpacingRequestorMixin, Requestor):
        _spacing = spacing

    return _PrawSpacingRequestor


def _connect_reddit(client_id: str, client_secret: str, user_agent: str):
    """Build a read-only PRAW client. Lazy-imported so the module imports without praw."""
    import praw

    # client_id+client_secret only (no username/password/refresh_token) yields a
    # read-only Application-Only OAuth client — sufficient for public submissions.
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        requestor_class=_spacing_requestor_class(_HOST_SPACING_POLICY),
    )


def _build_sentiment_fn(cache_dir: Path):
    """Lazy-load ProsusAI/finbert; return ``texts -> list[(pos, neg, neu)]``.

    Reuses ``transformers``+``torch`` already in the env via the ``extraction``
    extra's ``sentence-transformers`` — no new heavy dep. Weights cache under
    ``cache_dir`` so reruns make no download."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    cache = str(cache_dir)
    tokenizer = AutoTokenizer.from_pretrained(_FINBERT_MODEL, cache_dir=cache)
    model = AutoModelForSequenceClassification.from_pretrained(_FINBERT_MODEL, cache_dir=cache)
    model.eval()
    # FinBERT id2label is {0:'positive',1:'negative',2:'neutral'}; read it from the
    # config so per-text probs are always returned in canonical (pos, neg, neu) order
    # regardless of the model's internal index permutation.
    id2label = {int(k): v.lower() for k, v in model.config.id2label.items()}
    idx_pos = next(i for i, v in id2label.items() if "pos" in v)
    idx_neg = next(i for i, v in id2label.items() if "neg" in v)
    idx_neu = next(i for i, v in id2label.items() if "neu" in v)

    def sentiment_fn(texts: list[str]) -> list[tuple[float, float, float]]:
        out: list[tuple[float, float, float]] = []
        with torch.no_grad():
            for start in range(0, len(texts), _SENT_BATCH):
                batch = texts[start : start + _SENT_BATCH]
                enc = tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=_MAX_TOKENS,
                    return_tensors="pt",
                )
                probs = torch.softmax(model(**enc).logits, dim=-1).tolist()
                for row in probs:
                    out.append((row[idx_pos], row[idx_neg], row[idx_neu]))
        return out

    return sentiment_fn


# --- pure extraction + aggregation (unit-testable, no I/O) --------------------


def _count_ticker_mentions(text: str, universe: set[str]) -> dict[str, int]:
    """Token mention counts for tickers in ``universe``.

    ``$TICKER`` cashtags count in any case (the ``$`` is the unambiguous ticker
    signal). Bare words count only when UPPERCASE (the WSB ticker convention) and
    length >= :data:`_MIN_BARE_TICKER_LEN` — Reddit prose is lowercase, so
    case-insensitive bare matching would count ``well``/``tech``/``more`` as the
    WELL/TECH/MORE tickers (verified on a real pull, 2026-08-08). Tokens not in
    the universe are ignored. Returns ``{TICKER: count}`` (uppercase keys).
    """
    counts: dict[str, int] = {}
    for m in _TOKEN_RE.finditer(text or ""):
        cashtag = m.group(1)
        if cashtag is not None:
            tok = cashtag.upper()
            if tok in universe:
                counts[tok] = counts.get(tok, 0) + 1
            continue
        bare = m.group(2)
        if (
            bare is not None
            and bare.isupper()
            and len(bare) >= _MIN_BARE_TICKER_LEN
            and bare in universe
        ):
            counts[bare] = counts.get(bare, 0) + 1
    return counts


def _classify(p: float, n: float, u: float) -> str:
    """3-class argmax of a (positive, negative, neutral) triple; ties -> neutral."""
    if p > n and p > u:
        return "pos"
    if n > p and n > u:
        return "neg"
    return "neu"


def _aggregate_snapshot(
    posts: list[dict],
    tickers: list[str],
    sentiment_fn,
    snapshot_ts: str,
) -> pd.DataFrame:
    """One snapshot row per ticker that received >=1 post mention.

    Each post is scored ONCE (FinBERT on ``title + selftext``); a post that names
    several universe tickers donates the same sentiment vote to each. ``mentions``
    is the count of distinct posts naming the ticker (attention), so ``mentions``,
    ``sentiment_mean``, ``bull_ratio`` and ``score_sum`` share one denominator.

      * ``sentiment_mean`` = mean of ``(positive - negative)`` over those posts.
      * ``bull_ratio`` = positive / (positive + negative); NaN when all neutral.
      * ``score_sum`` = sum of Reddit post scores over those posts.
    """
    universe = {t.strip().upper() for t in tickers if t and t.strip()}
    if not universe:
        raise ValueError("tickers universe must be non-empty")

    texts = [f"{p.get('title', '')} {p.get('selftext', '')}".strip() for p in posts]
    probs = sentiment_fn(texts) if texts else []

    acc: dict[str, dict] = {}
    for post, (p_pos, p_neg, _p_neu) in zip(posts, probs, strict=True):
        body = f"{post.get('title', '')} {post.get('selftext', '')}"
        for tkr in _count_ticker_mentions(body, universe):  # keys -> once per ticker
            a = acc.setdefault(
                tkr, {"mentions": 0, "sent_sum": 0.0, "pos": 0, "neg": 0, "score_sum": 0}
            )
            a["mentions"] += 1
            a["sent_sum"] += p_pos - p_neg
            # bull_ratio needs only pos / neg counts; neutral votes are not stored.
            cls = _classify(p_pos, p_neg, _p_neu)
            if cls in ("pos", "neg"):
                a[cls] += 1
            a["score_sum"] += int(post.get("score", 0) or 0)

    rows = []
    for tkr, a in acc.items():
        m = a["mentions"]
        pos, neg = a["pos"], a["neg"]
        bull = pos / (pos + neg) if (pos + neg) > 0 else float("nan")
        rows.append(
            {
                "ticker": tkr,
                "mentions": m,
                "sentiment_mean": a["sent_sum"] / m,
                "bull_ratio": bull,
                "score_sum": a["score_sum"],
                "snapshot_ts": snapshot_ts,
            }
        )
    return pd.DataFrame(rows, columns=_SNAPSHOT_COLS)


# --- raw pull (PRAW -> list[dict]) --------------------------------------------


def _pull_posts(reddit, subreddits: tuple[str, ...], lookback_hours: int) -> list[dict]:
    """Collect public submissions within the lookback window across subreddits.

    PRAW ``subreddit.new(limit=...)`` yields newest-first, so iteration early-stops
    once a submission predates the cutoff. A ``_SUB_SLEEP`` pause between subreddits
    keeps us polite (G7)."""
    cutoff = datetime.now(tz=timezone.utc).timestamp() - lookback_hours * 3600.0
    posts: list[dict] = []
    for i, name in enumerate(subreddits):
        if i > 0:
            time.sleep(_SUB_SLEEP)  # politeness between subreddit pulls
        n_seen = 0
        for submission in reddit.subreddit(name).new(limit=_PULL_LIMIT):
            n_seen += 1
            if submission.created_utc < cutoff:
                break  # newest-first: nothing older will re-enter the window
            posts.append(
                {
                    "id": submission.id,
                    "subreddit": str(submission.subreddit),
                    "created_utc": float(submission.created_utc),
                    "title": submission.title or "",
                    "selftext": getattr(submission, "selftext", "") or "",
                    "score": int(getattr(submission, "score", 0) or 0),
                }
            )
        log.info(
            "reddit_subreddit_pulled",
            subreddit=name, n_in_window=len(posts), n_scanned=n_seen,
        )
    return posts


# --- zero-credential Atom RSS transport (OAuth blocked) -----------------------
#
# Reddit's unauthenticated ``.json`` endpoints return 403 as of 2026 (Responsible
# Builder Policy + patched rate-limit tracking). The public ``.rss`` (Atom) feed
# is the one surviving zero-credential path: it is Reddit's OWN published
# subscription format, intended for feed-reader consumption at low rates —
# ToS-clean (G7) where the ``.json``-without-auth hack is not. Verified
# 2026-08-08: subreddit ``/new.rss`` returns HTTP 200 with full post bodies in
# ``<content type="html">``; only ``score`` (upvotes) is unavailable vs PRAW.
# Used when PRAW creds are absent (transport "rss", or "auto" fallback).

_ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}
_RSS_LIMIT = 100  # Reddit RSS returns <=~25-50 entries; the cap is defensive.
_POST_ID_RE = re.compile(r"/comments/([a-z0-9]{4,})", re.IGNORECASE)


def _html_to_text(html: str) -> str:
    """Strip Reddit Atom ``<content type="html">`` to plain text.

    ``bs4`` (already a dep via the extraction stack) collapses nested HTML; block
    elements join with a space so ticker tokens never merge across tags."""
    from bs4 import BeautifulSoup

    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def _atom_child_text(entry, tag: str) -> str:
    node = entry.find(f"a:{tag}", _ATOM_NS)
    return (node.text or "") if node is not None else ""


def _entry_created_utc(entry) -> float | None:
    """Epoch seconds from ``<published>`` (creation), else ``<updated>``."""
    for tag in ("published", "updated"):
        node = entry.find(f"a:{tag}", _ATOM_NS)
        if node is not None and node.text:
            try:
                return datetime.fromisoformat(node.text).timestamp()
            except ValueError:
                continue
    return None


def _entry_to_post(entry, subreddit: str) -> dict:
    """One Atom ``<entry>`` -> the same post dict shape PRAW's ``_pull_posts`` emits.

    ``score`` is 0 (the Atom feed carries no upvote count); everything else the
    aggregator needs — ``title``, ``selftext`` (HTML-stripped), ``created_utc``,
    ``id``, ``subreddit`` — is present, so :func:`_aggregate_snapshot` is reused
    unchanged."""
    link_node = entry.find("a:link", _ATOM_NS)
    link_href = link_node.get("href", "") if link_node is not None else ""
    id_text = _atom_child_text(entry, "id")
    match = _POST_ID_RE.search(link_href) or _POST_ID_RE.search(id_text)
    created = _entry_created_utc(entry)
    return {
        "id": match.group(1) if match else "",
        "subreddit": subreddit,
        "created_utc": float(created) if created is not None else 0.0,
        "title": _atom_child_text(entry, "title"),
        "selftext": _html_to_text(_atom_child_text(entry, "content")),
        "score": 0,
    }


def _parse_atom_entries(xml_bytes: bytes) -> list:
    """Parse Reddit Atom feed bytes -> entry Elements (XXE-safe via defusedxml)."""
    from defusedxml import ElementTree as DET

    return DET.fromstring(xml_bytes).findall("a:entry", _ATOM_NS)


def _fetch_feed(url: str, user_agent: str):
    """Fetch one Reddit Atom feed with project host-spacing + bounded 429 retry.

    Monkeypatch seam for hermetic tests. Reuses the shared
    :class:`~aionis.ingest.http_policy.HostSpacingPolicy` (>=2s/host) and a bounded
    :class:`~aionis.ingest.http_policy.RetryPolicy` that honors ``Retry-After`` on
    429/5xx plus transient connection errors."""
    from aionis.ingest.http_policy import HttpRequestPolicy, RetryPolicy

    policy = HttpRequestPolicy(
        spacing=_HOST_SPACING_POLICY,
        retry=RetryPolicy(max_retries=2),
        retry_exceptions=(requests.exceptions.RequestException,),
    )
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/atom+xml,application/xml,text/xml",
    }
    return policy.request(url, lambda: requests.get(url, headers=headers, timeout=30))


def _pull_posts_rss(
    subreddits: tuple[str, ...],
    lookback_hours: int,
    user_agent: str,
    *,
    fetch=None,
) -> list[dict]:
    """Collect public submissions via the zero-credential Atom RSS feed.

    Mirrors :func:`_pull_posts` (PRAW): one pass per subreddit, newest-first feed,
    entries older than ``lookback_hours`` dropped. A per-subreddit fetch failure
    (403 / 429-exhausted / network) is logged and SKIPPED — a display feed collects
    what it can rather than aborting the whole snapshot. Same ``_SUB_SLEEP``
    politeness between subreddits as the PRAW path."""
    fetch = fetch or _fetch_feed
    cutoff = datetime.now(tz=timezone.utc).timestamp() - lookback_hours * 3600.0
    posts: list[dict] = []
    for i, name in enumerate(subreddits):
        if i > 0:
            time.sleep(_SUB_SLEEP)  # politeness between subreddit feeds
        url = f"https://www.reddit.com/r/{name}/new.rss?limit={_RSS_LIMIT}"
        try:
            resp = fetch(url, user_agent)
            entries = _parse_atom_entries(resp.content)
        except (
            HTTPStatusError,
            requests.exceptions.RequestException,
            _AtomParseError,
        ) as exc:
            log.warning("reddit_rss_subreddit_failed", subreddit=name, error=str(exc))
            continue
        kept = 0
        for entry in entries:
            created = _entry_created_utc(entry)
            if created is None or created < cutoff:
                continue
            posts.append(_entry_to_post(entry, name))
            kept += 1
        log.info(
            "reddit_rss_subreddit_pulled",
            subreddit=name, n_in_window=kept, n_scanned=len(entries),
        )
    return posts


# --- public API ---------------------------------------------------------------


def _resolve_transport(
    transport: str, client_id: str | None, client_secret: str | None
) -> str:
    """Resolve ``transport`` to a concrete ``"praw"`` | ``"rss"``.

    ``"auto"`` prefers PRAW (carries ``score``) when creds resolve; otherwise
    falls back to the zero-credential RSS path with a clear log, so the collector
    works the moment OAuth is unavailable (2026 Responsible Builder block)."""
    if transport not in ("auto", "praw", "rss"):
        raise ValueError(f"transport must be 'auto' | 'praw' | 'rss', got {transport!r}")
    if transport != "auto":
        return transport
    try:
        _resolve_creds(client_id, client_secret)
        return "praw"
    except RuntimeError:
        log.info(
            "reddit_transport_auto_fallback",
            reason="no PRAW credentials -> zero-credential RSS",
        )
        return "rss"


def collect_reddit_sentiment(
    tickers: list[str],
    *,
    subreddits: tuple[str, ...] = _DEFAULT_SUBREDDITS,
    lookback_hours: int = 24,
    cache_dir: Path | None = None,
    transport: str = "auto",
    client_id: str | None = None,
    client_secret: str | None = None,
    user_agent: str = "aionis/0.1 research",
) -> pd.DataFrame:
    """One forward-collection snapshot of Reddit mention volume + sentiment.

    ``transport`` selects the pull mechanism (see module docstring): ``"praw"``
    (OAuth2, carries ``score``; raises if creds absent), ``"rss"`` (zero-credential
    public Atom feed; ``score`` recorded 0), or ``"auto"`` (default — PRAW when
    creds resolve, else RSS).

    For each subreddit, pulls recent public submissions whose ``created_utc`` falls
    within ``lookback_hours`` of now, matches ``$TICKER`` / bare ``TICKER`` tokens
    in title+body against ``tickers``, scores each post with FinBERT, and aggregates
    per mentioned ticker into ``[ticker, mentions, sentiment_mean, bull_ratio,
    score_sum, snapshot_ts]``.

    Side effects (append-only, never overwrite):
      * Appends the snapshot rows to ``data/cache/reddit_snapshots.parquet``
        (parquet concat with any existing snapshot — prior rows preserved).
      * Archives the raw pull to ``data/cache/reddit_raw_<ts>.json`` (immutable,
        G3/G10) and sha256-pins it.
      * Appends one ``data_ingest`` ledger row
        (``mode: exploratory``, ``forward_only: true``).
      * Writes ``data/cache/reddit_last_run.json`` (status sidecar for the display).

    Forward-only: this never reconstructs history; the series starts accumulating
    from the first run.
    """
    if lookback_hours <= 0:
        raise ValueError("lookback_hours must be positive")
    if not subreddits:
        raise ValueError("subreddits must be non-empty")

    transport = _resolve_transport(transport, client_id, client_secret)
    cdir = _cache_dir(cache_dir)

    # Pull FIRST: the praw branch resolves creds (and raises clearly if absent)
    # BEFORE the heavy FinBERT download — a missing-creds call must never pay the
    # ~438MB weight cost just to fail. The rss branch needs no creds.
    if transport == "praw":
        cid, csec = _resolve_creds(client_id, client_secret)
        reddit = _connect_reddit(cid, csec, user_agent)
        posts = _pull_posts(reddit, tuple(subreddits), lookback_hours)
        source = "PRAW+FinBERT"
        license_str = "PRAW BSD-2 + FinBERT Apache + Reddit ToS (display, no-resale)"
        score_available = True
    else:
        posts = _pull_posts_rss(tuple(subreddits), lookback_hours, user_agent)
        source = "RSS-atom+FinBERT (zero-credential)"
        license_str = (
            "Reddit Atom RSS (public feed) + FinBERT Apache + "
            "Reddit ToS (display, no-resale)"
        )
        score_available = False

    # Score posts with FinBERT — only AFTER a successful pull (heavy lazy load).
    sentiment_fn = _build_sentiment_fn(cdir)

    snapshot_ts = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    ts_compact = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Raw archival (immutable) + sha256 — G3/G4/G10.
    raw_path = cdir / f"reddit_raw_{ts_compact}.json"
    raw_path.write_text(json.dumps(posts, ensure_ascii=False))
    digest = _sha256(raw_path)
    log.info("reddit_raw_archived", path=str(raw_path), n_posts=len(posts), sha256=digest)

    snapshot = _aggregate_snapshot(posts, tickers, sentiment_fn, snapshot_ts)

    # Append to the cumulative parquet (concat preserves all prior snapshots).
    # An empty window creates no file and never disturbs an existing one.
    snapshot_path = cdir / "reddit_snapshots.parquet"
    if not snapshot.empty:
        if snapshot_path.exists():
            prior = pd.read_parquet(snapshot_path)
            pd.concat([prior, snapshot], ignore_index=True).to_parquet(snapshot_path)
        else:
            snapshot.to_parquet(snapshot_path)
    log.info(
        "reddit_snapshot_written",
        path=str(snapshot_path),
        n_rows=len(snapshot),
        n_tickers=int(snapshot["ticker"].nunique()) if not snapshot.empty else 0,
    )

    _append_ingest_ledger(
        {
            "event": "data_ingest",
            "dataset": "reddit_sentiment",
            "source": source,
            "license": license_str,
            "mode": "exploratory",
            "forward_only": True,
            "transport": transport,
            "score_available": score_available,
            "subreddits": list(subreddits),
            "lookback_hours": int(lookback_hours),
            "n_posts": len(posts),
            "n_tickers": int(len(snapshot)),
            "data_sha256": digest,
        }
    )

    # Status sidecar for the terminal display layer (transport + score honesty).
    (cdir / "reddit_last_run.json").write_text(
        json.dumps(
            {
                "snapshot_ts": snapshot_ts,
                "transport": transport,
                "score_available": score_available,
                "n_posts": len(posts),
                "n_tickers": int(len(snapshot)),
                "subreddits": list(subreddits),
                "lookback_hours": int(lookback_hours),
            },
            ensure_ascii=False,
        )
    )
    return snapshot
