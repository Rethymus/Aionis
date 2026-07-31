"""Causal broadcast — the arm_e13 extra_features builder (E3 Slice 3b).

Assembles the long ``extra_features=[date, ticker, ...]`` frame for arm_e13 by
REUSING the verified seams, not hand-rolling:

  * :func:`aionis.features.propagation.propagate_panel` — FF-12 ex-self peer
    propagation of the 13D / 8-K self-shock indicators (``ff12_map`` is fed
    directly as the group map — it is sector-agnostic by design);
  * :func:`aionis.features.frozen_beta.broadcast_macro_beta` — the frozen
    sign-β × surprise_z macro shock (zero-LLM, PIT);
  * the idempotent sha256-keyed cache PATTERN of
    :mod:`aionis.extraction.extract` (ridden by :func:`extract_event_edges` for
    the minimal closed-enum LLM edge); and
  * the ``_long(wide, tickers, name)`` wide->long melt from
    ``scripts/phase_e1_run.py``.

Output columns: ``[date, ticker, self_13d_fwd, self_8k_fwd, peer_13d_fwd,
peer_8k_fwd, macro_causal_shock, mech_earnings_signal, mech_ownership_change,
mech_guidance, mech_other]`` — the exact shape
:func:`aionis.features.selection_panel.build_selection_panel` consumes via its
``extra_features=`` left-join (columns only, never rows).

Permissive licenses only (pandas / pydantic). No mock data in the real path:
:func:`extract_event_edges` rides a real LLM client (:class:`GLMCausalEdgeClient`
wires GLM-4-Flash); mock clients are unit-test fixtures only.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Protocol

import pandas as pd
import structlog
from pydantic import ValidationError

from aionis.extraction.llm_client import text_hash
from aionis.features.frozen_beta import broadcast_macro_beta
from aionis.features.propagation import propagate_panel
from aionis.schema.causal_edge import (
    Direction,
    ForwardCausalExtraction,
    MechanismKeyword,
    SicSector,
    assert_no_forbidden,
    direction_sign,
)

log = structlog.get_logger()

_MECH_COLUMNS: dict[MechanismKeyword, str] = {
    MechanismKeyword.EARNINGS_SIGNAL: "mech_earnings_signal",
    MechanismKeyword.OWNERSHIP_CHANGE: "mech_ownership_change",
    MechanismKeyword.GUIDANCE: "mech_guidance",
    MechanismKeyword.OTHER: "mech_other",
}


# ---------------------------------------------------------------------------
# LLM client protocol + the real GLM wire (the closed-enum event edge)
# ---------------------------------------------------------------------------


class CausalEdgeLLMClient(Protocol):
    """Minimal contract for a closed-enum causal-edge LLM client."""

    def extract_causal(self, text: str, event_id: str) -> ForwardCausalExtraction: ...


_EDGE_SYSTEM_PROMPT = """\
You extract a minimal CLOSED-ENUM causal edge for ONE forward event (a SC 13D \
filing or an 8-K Item 2.02 earnings release). Every field is a closed enum; \
return NOTHING but the JSON object below.

Hard rules:
- Pick the FF-12 sector of the event's subject company, the event's a-priori
  DIRECTION for that company's self-shock (positive / negative / neutral), the
  event MECHANISM keyword, and the a-priori horizon bucket.
- You MUST NOT infer or encode any market outcome: no price move, no expected
  return, no historical similarity/magnitude. 'neutral' direction = no view.
"""

_EDGE_SCHEMA_SPEC = (
    "Return a JSON object with EXACTLY this shape:\n"
    "{\n"
    "  \"causal_edges\": [\n"
    "    {\n"
    "      \"sic_sector\": <one of: NoDur, Durbl, Manuf, Enrgy, Chems, BusEq,\n"
    "                      Telcm, Utils, Shops, Hlth, Money, Other>,\n"
    "      \"direction\": <one of: positive, negative, neutral>,\n"
    "      \"mechanism_keyword\": <one of: earnings_signal, ownership_change,\n"
    "                            guidance, other>,\n"
    "      \"horizon_bucket\": <one of: instant, short, medium, long>\n"
    "    }\n"
    "  ]\n"
    "}\n"
    "event_id is set by the caller (do NOT include it). Return exactly one edge."
)


class GLMCausalEdgeClient:
    """Real-pipeline closed-enum edge client over an OpenAI-compatible endpoint.

    Wires GLM-4-Flash (priority-1, free) via the ``openai`` SDK with JSON mode +
    pydantic validation + ONE bounded retry (mirroring
    :class:`aionis.extraction.llm_client.OpenAICompatClient`). The closed enum +
    ``extra="forbid"`` contract (:class:`ForwardCausalExtraction`) is the I5
    leakage boundary: the model literally cannot return an impact/return field.
    The ``openai`` import is lazy so unit tests never require the SDK.
    """

    def __init__(self, base_url: str, api_key: str, model: str = "glm-4-flash",
                 timeout: float = 60.0) -> None:
        from openai import OpenAI

        self.model = model
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout,
                              max_retries=0)
        # CLAUDE.md mandate: track per-call token usage (mirrors OpenAICompatClient).
        # ``None`` before the first call / when usage is missing on error.
        self.last_usage: dict | None = None

    def _chat(self, user: str) -> str:
        system = _EDGE_SYSTEM_PROMPT + "\n\nJSON schema:\n" + _EDGE_SCHEMA_SPEC
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        u = resp.usage
        if u is None:
            self.last_usage = None
        else:
            self.last_usage = {
                "prompt_tokens": getattr(u, "prompt_tokens", 0) or 0,
                "completion_tokens": getattr(u, "completion_tokens", 0) or 0,
                "total_tokens": getattr(u, "total_tokens", 0) or 0,
            }
        return resp.choices[0].message.content or ""

    def extract_causal(self, text: str, event_id: str) -> ForwardCausalExtraction:
        user = f"event_id: {event_id}\nsource text:\n{text}"
        content = self._chat(user)
        try:
            obj = {"event_id": event_id, **json.loads(content)}
            assert_no_forbidden(obj)  # FIX 7: explicit I5 pre-parse guard
            return ForwardCausalExtraction.model_validate(obj)
        except (ValidationError, json.JSONDecodeError):
            # One bounded retry feeding the failure back — no unbounded loop.
            # Other errors (e.g. an I5 ``assert_no_forbidden`` ValueError) re-raise.
            content = self._chat(
                user + "\n\nPrevious reply was invalid. Return ONLY the schema JSON."
            )
            obj = {"event_id": event_id, **json.loads(content)}
            assert_no_forbidden(obj)  # FIX 7: explicit I5 pre-parse guard
            return ForwardCausalExtraction.model_validate(obj)


# ---------------------------------------------------------------------------
# forward self-shocks — wide (sessions x tickers) indicators
# ---------------------------------------------------------------------------


def _indicator_wide(
    events: pd.DataFrame, sessions: pd.DatetimeIndex, tickers: list[str]
) -> pd.DataFrame:
    """Place a 1.0 indicator at (ticker, session) for each event's filing date.

    ``event_ts`` is forward-mapped to the first session on/after it (a weekend /
    holiday filing is knowable at the next NYSE session — PIT). Returns wide
    (sessions x tickers), NaN where no event applies.
    """
    sessions = pd.DatetimeIndex(sessions).normalize()
    wide = pd.DataFrame(float("nan"), index=sessions, columns=list(tickers))
    if events.empty or "event_ts" not in events.columns:
        return wide
    tk_set = set(tickers)
    for r in events.itertuples(index=False):
        tkr = getattr(r, "ticker", None)
        if tkr is None or tkr not in tk_set:
            continue
        ev = pd.Timestamp(getattr(r, "event_ts", None))
        if pd.isna(ev):
            continue
        ev = ev.normalize()
        if ev > sessions.max():
            continue  # PIT: filed after the freeze -> not yet knowable
        fwd = sessions[sessions >= ev]
        if len(fwd) == 0:
            continue
        wide.loc[fwd[0], tkr] = 1.0
    return wide


def forward_self_shocks(
    stakes_df: pd.DataFrame,
    earnings_df: pd.DataFrame,
    sessions: pd.DatetimeIndex,
    tickers: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Wide (sessions x tickers) 13D and 8-K Item-2.02 self-shock indicators.

    ``stakes_df`` / ``earnings_df`` follow the Slice-2 forward-collector contract
    (``[ticker, value=1.0, event_ts=filing_date, ...]``). Each filing becomes a
    ``1.0`` indicator at its (forward-mapped) session, NaN elsewhere. Returns
    ``(self_13d_wide, self_8k_wide)``.
    """
    return (
        _indicator_wide(stakes_df, sessions, tickers),
        _indicator_wide(earnings_df, sessions, tickers),
    )


# ---------------------------------------------------------------------------
# extract_event_edges — idempotent sha256-keyed cache (rides extract.py pattern)
# ---------------------------------------------------------------------------


def _has_text(v: object) -> bool:
    if v is None:
        return False
    if isinstance(v, float) and math.isnan(v):
        return False
    return str(v).strip() != ""


def _add_usage(accum: dict[str, int], usage: dict | None) -> None:
    """Accumulate a per-call ``last_usage`` dict into running token totals.

    ``None``-safe (a failed/absent usage leaves the totals unchanged). Mirrors the
    CLAUDE.md "log per-call token usage" discipline by letting ``extract_event_edges``
    sum prompt/completion/total tokens across the (cache-missing) calls and emit the
    cumulative totals in its ``extract_edges_done`` log line.
    """
    if not isinstance(usage, dict):
        return
    for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
        accum[k] = accum.get(k, 0) + int(usage.get(k, 0) or 0)


def extract_event_edges(
    events_df: pd.DataFrame,
    client: CausalEdgeLLMClient,
    cache_dir: Path | None,
) -> dict[str, ForwardCausalExtraction]:
    """Extract (or load cached) closed-enum edges for every event with text.

    Mirrors :func:`aionis.extraction.extract.extract_erls`: cache key =
    ``sha256(source_text)`` (16-char, same as ERL); a cache hit spends no tokens.
    ``cache_dir=None`` disables disk caching (in-memory only) — for tests / a
    fresh run that does not want persistence. Events with no ``text`` are skipped
    (a warning, matching ``extract_erls``). Returns ``{event_id: extraction}``.
    """
    use_cache = cache_dir is not None
    if use_cache:
        cache_dir = Path(cache_dir)  # type: ignore[assignment]
        cache_dir.mkdir(parents=True, exist_ok=True)  # type: ignore[union-attr]
    out: dict[str, ForwardCausalExtraction] = {}
    hits = 0
    usage_totals: dict[str, int] = {}
    text_by_id: dict[str, object] = {}
    if "text" in events_df.columns:
        text_by_id = dict(zip(events_df["event_id"], events_df["text"], strict=True))

    for ev in events_df.itertuples(index=False):
        text = text_by_id.get(ev.event_id)
        if not _has_text(text):
            log.warning("no_text_for_event", event_id=ev.event_id)
            continue
        h = text_hash(str(text))
        if use_cache:
            path = cache_dir / f"causal_edge_{h}.json"  # type: ignore[union-attr]
            if path.exists():
                out[ev.event_id] = ForwardCausalExtraction.model_validate_json(
                    path.read_text()
                )
                hits += 1
                continue
        try:
            ext = client.extract_causal(str(text), ev.event_id)
        except Exception as e:  # pragma: no cover - network/model path
            log.error("extract_edge_failed", event_id=ev.event_id, error=str(e))
            continue
        if use_cache:
            path.write_text(ext.model_dump_json(indent=2))  # type: ignore[used-before-assignment]
        _add_usage(usage_totals, getattr(client, "last_usage", None))
        out[ev.event_id] = ext
    log.info(
        "extract_edges_done",
        n=len(out), cache_hits=hits, cached=use_cache, **usage_totals,
    )
    return out


# ---------------------------------------------------------------------------
# edges -> direction sign wide + mechanism one-hot wide
# ---------------------------------------------------------------------------


def _first_edge(ext: ForwardCausalExtraction) -> tuple[Direction, MechanismKeyword] | None:
    """The event's (direction, mechanism) from its first edge; None if no edges.

    Realistic case is ONE edge per event (a 13D filing = ownership_change). When
    the LLM returns several, the FIRST edge governs the sign + mechanism tag
    (deterministic given the ordered list).
    """
    if not ext.causal_edges:
        return None
    e = ext.causal_edges[0]
    return (e.direction, e.mechanism_keyword)


def _edges_to_wide(
    edges: dict[str, ForwardCausalExtraction],
    events_df: pd.DataFrame,
    sessions: pd.DatetimeIndex,
    tickers: list[str],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Direction-sign wide + mechanism one-hot wide frames (sessions x tickers).

    * ``direction_wide[ticker, session]`` = :func:`direction_sign` of the event's
      first edge (first-wins per (ticker, session)); NaN where no event / NEUTRAL.
    * ``mech_<keyword>[ticker, session]`` = 1.0 where that event's mechanism
      matches the keyword (indicator; non-matching columns stay NaN everywhere).

    The event's session is the forward-map of its ``event_ts`` (PIT). A ticker
    with no event at a session stays NaN in every column.
    """
    sessions = pd.DatetimeIndex(sessions).normalize()
    direction_wide = pd.DataFrame(float("nan"), index=sessions, columns=list(tickers))
    mech_wide = {
        col: pd.DataFrame(float("nan"), index=sessions, columns=list(tickers))
        for col in _MECH_COLUMNS.values()
    }
    if events_df.empty or not edges:
        return direction_wide, mech_wide
    tk_set = set(tickers)
    ev_lookup = {
        r.event_id: (getattr(r, "ticker", None), pd.Timestamp(getattr(r, "event_ts", None)))
        for r in events_df.itertuples(index=False)
    }
    for event_id, ext in edges.items():
        tkr, ev_ts = ev_lookup.get(event_id, (None, pd.NaT))
        if tkr is None or tkr not in tk_set or pd.isna(ev_ts):
            continue
        ev_ts = ev_ts.normalize()
        if ev_ts > sessions.max():
            continue  # PIT
        fwd = sessions[sessions >= ev_ts]
        if len(fwd) == 0:
            continue
        d = fwd[0]
        dm = _first_edge(ext)
        if dm is None:
            continue
        direction, mechanism = dm
        # direction: first-wins per (ticker, session)
        if pd.isna(direction_wide.loc[d, tkr]):
            direction_wide.loc[d, tkr] = direction_sign(direction)
        # mechanism: one-hot indicator (set 1.0; idempotent under repeats)
        mech_wide[_MECH_COLUMNS[mechanism]].loc[d, tkr] = 1.0
    return direction_wide, mech_wide


# ---------------------------------------------------------------------------
# wide -> long melt (mirrors scripts/phase_e1_run.py::_long)
# ---------------------------------------------------------------------------


def _long(wide: pd.DataFrame, tickers: list[str], name: str) -> pd.DataFrame:
    """Wide (date x ticker) -> long [date, ticker, <name>] (retains NaN rows).

    ``.stack()`` on pandas >=3.0 retains NaN rows, so the (sessions x tickers)
    cartesian is preserved — every ``_long`` of a common-grid frame has identical
    ``[date, ticker]`` keys, making outer merges row-stable (no row explosion).
    """
    return (
        wide[list(tickers)].stack().rename(name).reset_index()
        .rename(columns={"level_0": "date", "level_1": "ticker"})
    )


# ---------------------------------------------------------------------------
# the orchestrator — build the long extra_features frame for arm_e13
# ---------------------------------------------------------------------------


def build_forward_extra_features(
    *,
    macro_df: pd.DataFrame,
    stakes_df: pd.DataFrame,
    earnings_df: pd.DataFrame,
    events_df: pd.DataFrame,
    client: CausalEdgeLLMClient,
    cache_dir: Path | None,
    ff12_map: dict[str, SicSector],
    sessions: pd.DatetimeIndex,
    tickers: list[str],
) -> pd.DataFrame:
    """Assemble the long ``[date, ticker, ...]`` extra_features frame for arm_e13.

    Combines the four causal channels:

    * **self shocks** (13D / 8-K Item-2.02 indicators), signed by the LLM edge
      ``direction`` (POSITIVE->+1, NEGATIVE->-1, NEUTRAL->NaN);
    * **peer propagation** — ex-self FF-12 peer mean of the UNSIGNED self-shock
      indicators (the E1 propagation claim, zero-LLM);
    * **macro causal shock** — frozen sign-β × surprise_z broadcast (zero-LLM);
    * **mechanism one-hot** — ``mech_<keyword>`` indicators from the LLM edge.

    Returns a long frame ready for
    :func:`aionis.features.selection_panel.build_selection_panel`'s
    ``extra_features=`` left-join (columns only, never rows).
    """
    sessions = pd.DatetimeIndex(sessions).normalize()
    tickers = list(tickers)

    # 1. self-shock indicators (wide)
    self_13d, self_8k = forward_self_shocks(stakes_df, earnings_df, sessions, tickers)

    # 2. FF-12 ex-self peer propagation of the UNSIGNED self-shock indicators.
    #    ff12_map (ticker->SicSector) is fed directly: propagate_panel groups on
    #    the map values (SicSector is a str subclass), so FF-12 grouping is a
    #    zero-code-change swap (plan §1: "feed ff12_map, NOT sic_map").
    peer_13d = propagate_panel(self_13d, ff12_map, tickers=tickers)
    peer_8k = propagate_panel(self_8k, ff12_map, tickers=tickers)

    # 3. macro causal shock (frozen sign-β × surprise_z, zero-LLM, PIT)
    macro_causal = broadcast_macro_beta(macro_df, ff12_map, sessions, tickers)

    # 4. LLM event edge -> direction signs the self-shock + mechanism one-hot
    edges: dict[str, ForwardCausalExtraction] = {}
    if not events_df.empty:
        edges = extract_event_edges(events_df, client, cache_dir)
    direction_wide, mech_wide = _edges_to_wide(edges, events_df, sessions, tickers)

    # direction signs the self-shock (NEUTRAL / no-edge -> NaN, carries no signal)
    self_13d_fwd = self_13d * direction_wide
    self_8k_fwd = self_8k * direction_wide

    # 5. melt each to long and merge on [date, ticker] (outer; common grid ->
    #    identical keys -> no row explosion)
    longs = [
        _long(self_13d_fwd, tickers, "self_13d_fwd"),
        _long(self_8k_fwd, tickers, "self_8k_fwd"),
        _long(peer_13d, tickers, "peer_13d_fwd"),
        _long(peer_8k, tickers, "peer_8k_fwd"),
        _long(macro_causal, tickers, "macro_causal_shock"),
    ]
    for col in _MECH_COLUMNS.values():
        longs.append(_long(mech_wide[col], tickers, col))

    merged = longs[0]
    for frame in longs[1:]:
        merged = merged.merge(frame, on=["date", "ticker"], how="outer")

    merged["date"] = pd.to_datetime(merged["date"]).dt.normalize()
    col_order = [
        "date",
        "ticker",
        "self_13d_fwd",
        "self_8k_fwd",
        "peer_13d_fwd",
        "peer_8k_fwd",
        "macro_causal_shock",
        *_MECH_COLUMNS.values(),
    ]
    return merged[col_order]


__all__ = [
    "CausalEdgeLLMClient",
    "GLMCausalEdgeClient",
    "forward_self_shocks",
    "extract_event_edges",
    "build_forward_extra_features",
]
