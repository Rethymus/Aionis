"""Extract ERL objects from event text, with idempotent on-disk caching.

Cache key = sha256(source_text): re-running extraction never re-spends tokens on
text already seen, and the cached object is auditable. A cache hit also makes the
no-key smoke pipeline and control-gate re-runs free.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import structlog

from aionis.extraction.llm_client import LLMClient, text_hash
from aionis.schema.erl import ERL

log = structlog.get_logger()


def extract_erls(
    events: pd.DataFrame,
    text_df: pd.DataFrame,
    client: LLMClient,
    cache_dir: Path,
) -> dict[str, ERL]:
    """Extract (or load cached) ERL for every event in ``events``.

    ``text_df`` must have columns event_id, text. Returns {event_id: ERL}.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    text_by_id = dict(zip(text_df["event_id"], text_df["text"], strict=True))

    out: dict[str, ERL] = {}
    hits = 0
    for ev in events.itertuples(index=False):
        if ev.event_id not in text_by_id:
            log.warning("no_text_for_event", event_id=ev.event_id)
            continue
        text = text_by_id[ev.event_id]
        h = text_hash(text)
        path = cache_dir / f"{h}.json"
        if path.exists():
            out[ev.event_id] = ERL.model_validate_json(path.read_text())
            hits += 1
            continue
        try:
            erl = client.extract(text, event_id=ev.event_id, event_type=ev.event_type)
        except Exception as e:  # pragma: no cover - network/model path
            log.error("extract_failed", event_id=ev.event_id, error=str(e))
            continue
        path.write_text(erl.model_dump_json(indent=2))
        out[ev.event_id] = erl
    log.info("extract_done", n=len(out), cache_hits=hits, cache_dir=str(cache_dir))
    return out


def load_erl_cache(cache_dir: Path) -> dict[str, ERL]:
    """Load all cached ERL objects (keyed by file content's event_id)."""
    cache_dir = Path(cache_dir)
    out: dict[str, ERL] = {}
    if not cache_dir.exists():
        return out
    for p in sorted(cache_dir.glob("*.json")):
        try:
            erl = ERL.model_validate_json(p.read_text())
            out[erl.event_id] = erl
        except Exception as e:  # pragma: no cover
            log.warning("bad_cache_file", path=str(p), error=str(e))
    return out


def erls_to_records(erls: dict[str, ERL]) -> pd.DataFrame:
    rows = []
    for erl in erls.values():
        rows.append(
            {
                "event_id": erl.event_id,
                "event_type": erl.event_type,
                "action": erl.action.value,
                "actor_type": erl.actor.type.value,
                "object_type": erl.object.type.value,
                "object_sector": erl.object.sector,
                "temporal": erl.temporal.value,
                "uncertainty": erl.uncertainty,
                "n_causal": len(erl.causal_structure),
                "canonical_text": erl.canonical_text(),
            }
        )
    return pd.DataFrame(rows)
