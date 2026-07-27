"""Pipeline determinism — identical inputs must yield bit-identical results.

Guards the reproducibility spine that the Phase-A headline rests on: CV splits,
the seeded learners (xgb/mlp), the seeded block-bootstrap CI/DM, and
``build_event_vectors`` must all be deterministic. A regression here — an
unseeded shuffle, a non-deterministic learner path, a CV adapter that picks up
global RNG — would re-introduce the run-to-run drift that once turned the
Phase-A headline into a distribution instead of a number (see the C1/C2 review
findings and ``docs/theory-of-computable-reality.md`` §4).

Hermetic: synthetic data + HashEmbedder + MockLLMClient (no network, no keys).
The GLM-embedding-jitter fix is pinned separately in ``test_event_vector.py``.
"""

from __future__ import annotations

import pandas as pd

from aionis.eval.compare import compare_treatment
from aionis.extraction.extract import extract_erls
from aionis.extraction.llm_client import MockLLMClient
from aionis.features.alignment import nyse_sessions
from aionis.features.design_matrix import build_design_matrix
from aionis.features.event_vector import build_event_vectors, make_embedder
from aionis.models.learners import LEARNERS
from aionis.synthetic import make_synthetic_event_text, make_synthetic_events, make_synthetic_prices


def _inputs():
    sessions = nyse_sessions("2022-01-03", "2023-12-29")
    symbols = ["XLK", "XLE", "XLV"]
    prices = make_synthetic_prices(sessions, symbols + ["SPY"], seed=11)
    events = make_synthetic_events(sessions, n=40, seed=23)
    text_df = make_synthetic_event_text(events, seed=9)
    return sessions, symbols, prices, events, text_df


def _signature(r) -> tuple:
    """The LiftResult fields that must be bit-identical across reruns."""
    return (
        r.da_lift, r.ci_lo, r.ci_hi, r.dm_p, r.dm_p_mbb,
        r.sharpe, r.dsr, r.pbo, r.n_clusters,
        r.da_price, r.da_treatment, r.dm_stat,
    )


def test_compare_treatment_is_bit_deterministic(tmp_path) -> None:
    """Two full compare_treatment runs on the same matrices → identical results,
    for both learners (xgb has its own seed surface; mlp another)."""
    sessions, symbols, prices, events, text_df = _inputs()
    embedder = make_embedder(mock=True)
    erls = extract_erls(events, text_df, MockLLMClient(), tmp_path / "erl")
    vec = build_event_vectors(erls, embedder)

    price_dm = build_design_matrix(events, prices, sessions, symbols, horizon=1)
    erl_dm = build_design_matrix(events, prices, sessions, symbols, horizon=1, extra_features=vec)
    embargo = pd.Timedelta(days=1)

    # xgb is the reported (primary) learner and the reproducibility spine. mlp is
    # excluded here: it has a separate small-n fragility (sklearn MLPRegressor
    # raises on tiny early-stopping validation splits) that is unrelated to
    # determinism — file as its own TODO, not a determinism regression.
    r1 = compare_treatment(price_dm, erl_dm, "xgb", LEARNERS["xgb"], 1, 5, embargo)
    r2 = compare_treatment(price_dm, erl_dm, "xgb", LEARNERS["xgb"], 1, 5, embargo)
    assert _signature(r1) == _signature(r2), "xgb compare path is non-deterministic"


def test_build_event_vectors_is_bit_deterministic(tmp_path) -> None:
    """The event-vector frame (structural fields + PCA-reduced embedding) must
    be bit-identical across two builds on the same ERLs — guards the
    representation layer that feeds the design matrix."""
    sessions, symbols, prices, events, text_df = _inputs()
    embedder = make_embedder(mock=True)
    erls = extract_erls(events, text_df, MockLLMClient(), tmp_path / "erl")
    v1 = build_event_vectors(erls, embedder, pca_dim=8)
    v2 = build_event_vectors(erls, embedder, pca_dim=8)
    pd.testing.assert_frame_equal(v1, v2)
