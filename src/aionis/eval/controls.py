"""Control gates — what makes a real ERL lift falsifiable.

If structured events carry genuine signal, the with-ERL lift must:
  * SURVIVE on real ERL, but
  * VANISH on (a) neutral-text extraction and (b) shuffled-date pairing.

If lift survives a control, it is an artifact (the LLM echoing outcome, or a
confound), and the claim is killed. These two gates are non-optional.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.extraction.llm_client import LLMClient, MockLLMClient
from aionis.schema.erl import ERL

NEUTRAL_TEXT = (
    "A scheduled administrative release was published today. It contains routine "
    "procedural content with no specific policy action, magnitude, or market-relevant "
    "substance. No outcome is described."
)


def make_neutral_erls(events: pd.DataFrame, client: LLMClient | None = None) -> dict[str, ERL]:
    """Extract ERL from a fixed neutral passage for every event.

    Every event gets the same generic, outcome-free ERL, so its event vector
    carries no discriminating information. A real lift must disappear here.
    """
    client = client or MockLLMClient()
    out: dict[str, ERL] = {}
    for ev in events.itertuples(index=False):
        out[ev.event_id] = client.extract(
            NEUTRAL_TEXT, event_id=ev.event_id, event_type=ev.event_type
        )
    return out


def shuffled_vectors(vec: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    """Relabel each event's vector with a different event's id.

    Real ERL features are paired with the WRONG event's market state, breaking
    the event->response link. A real lift must disappear here.
    """
    rng = np.random.default_rng(seed)
    permuted = vec.index.to_numpy()[rng.permutation(len(vec))]
    return vec.set_axis(permuted, axis=0)
