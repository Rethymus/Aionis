"""Retail-sentiment forward-collection (Reddit mentions + FinBERT sentiment).

This is the third retail-attention series for the market-driver framework
(``docs/market-driver-framework.md`` main lines ③/⑤): retail attention is modeled
as mention volume + sentiment, following the xiaoyinsi-informed methodology.

**Forward-collection only — NO historical backfill.** There is no permissively-
licensed historical Reddit/StockTwits corpus (Pushshift died 2023; StockTwits has
no backfill; ``arctic_shift`` is unlicensed). The only PIT-honest path is to
snapshot-on-arrival from today. This module accumulates ONE snapshot per run; it
never reconstructs the past.

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
  * **G7** — PRAW only (no scrape), descriptive User-Agent, 1.5s sleep between
    subreddit pulls (PRAW honors Reddit's 100 QPM + ToS internally).

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

import pandas as pd
import structlog

from aionis.config import settings

log = structlog.get_logger()

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


def _connect_reddit(client_id: str, client_secret: str, user_agent: str):
    """Build a read-only PRAW client. Lazy-imported so the module imports without praw."""
    import praw

    # client_id+client_secret only (no username/password/refresh_token) yields a
    # read-only Application-Only OAuth client — sufficient for public submissions.
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
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

    Matches ``$TICKER`` cashtags and bare ``TICKER`` word tokens; case-insensitive
    (``aapl`` == ``AAPL`` == ``$aapl``); tokens not in the universe are ignored.
    Returns ``{TICKER: token_count}`` (uppercase keys).
    """
    counts: dict[str, int] = {}
    for m in _TOKEN_RE.finditer(text or ""):
        tok = (m.group(1) or m.group(2)).upper()
        if tok in universe:
            counts[tok] = counts.get(tok, 0) + 1
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


# --- public API ---------------------------------------------------------------


def collect_reddit_sentiment(
    tickers: list[str],
    *,
    subreddits: tuple[str, ...] = _DEFAULT_SUBREDDITS,
    lookback_hours: int = 24,
    cache_dir: Path | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    user_agent: str = "aionis/0.1 research",
) -> pd.DataFrame:
    """One forward-collection snapshot of Reddit mention volume + sentiment.

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

    Forward-only: this never reconstructs history; the series starts accumulating
    from the first run. Requires Reddit script-app credentials
    (``REDDIT_CLIENT_ID`` / ``REDDIT_CLIENT_SECRET``); raises clearly if absent.
    """
    if lookback_hours <= 0:
        raise ValueError("lookback_hours must be positive")
    if not subreddits:
        raise ValueError("subreddits must be non-empty")

    cid, csec = _resolve_creds(client_id, client_secret)
    cdir = _cache_dir(cache_dir)
    sentiment_fn = _build_sentiment_fn(cdir)
    reddit = _connect_reddit(cid, csec, user_agent)

    snapshot_ts = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    ts_compact = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    posts = _pull_posts(reddit, tuple(subreddits), lookback_hours)

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
            "source": "PRAW+FinBERT",
            "license": "PRAW BSD-2 + FinBERT Apache + Reddit ToS (display, no-resale)",
            "mode": "exploratory",
            "forward_only": True,
            "subreddits": list(subreddits),
            "lookback_hours": int(lookback_hours),
            "n_posts": len(posts),
            "n_tickers": int(len(snapshot)),
            "data_sha256": digest,
        }
    )
    return snapshot
