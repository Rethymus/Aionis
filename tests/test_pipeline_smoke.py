"""End-to-end smoke test: the full pipeline runs without any API keys or network.

Exercises ingestion(synthetic) -> design matrix -> purged CV -> metrics, and the
Phase 3 comparison with the offline MockLLMClient + HashEmbedder. This is the
no-key regression gate for the whole MVP machinery.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.eval.compare import compare_treatment
from aionis.eval.controls import make_neutral_erls, shuffled_vectors
from aionis.eval.evaluate import cross_validate
from aionis.extraction.extract import extract_erls
from aionis.extraction.llm_client import MockLLMClient
from aionis.features.alignment import nyse_sessions
from aionis.features.design_matrix import build_design_matrix
from aionis.features.event_vector import build_event_vectors, make_embedder
from aionis.models.learners import LEARNERS
from aionis.synthetic import make_synthetic_event_text, make_synthetic_events, make_synthetic_prices


def _build_inputs(horizon: int = 1, n_events: int = 40):
    sessions = nyse_sessions("2022-01-03", "2023-12-29")
    symbols = ["XLK", "XLE", "XLV"]
    prices = make_synthetic_prices(sessions, symbols + ["SPY"], seed=11)
    events = make_synthetic_events(sessions, n=n_events, seed=23)
    text_df = make_synthetic_event_text(events, seed=9)
    return sessions, symbols, prices, events, text_df


def test_full_pipeline_smoke(tmp_path) -> None:
    sessions, symbols, prices, events, text_df = _build_inputs()
    embedder = make_embedder(mock=True)

    # Phase 0/1: design matrix + price-only CV.
    price_dm = build_design_matrix(events, prices, sessions, symbols, horizon=1)
    assert len(price_dm) > 0
    result = cross_validate(price_dm, {"xgb": LEARNERS["xgb"]}, n_splits=4)
    assert {"DA", "MAE", "MSE", "up_baseline"} <= set(result.metrics.columns)
    assert 0.0 <= result.metrics.loc["xgb", "DA"] <= 1.0

    # Phase 2: extract ERLs offline, build event vectors.
    erls = extract_erls(events, text_df, MockLLMClient(), tmp_path / "erl")
    assert len(erls) == len(events)
    vec = build_event_vectors(erls, embedder)
    assert vec.shape[0] == len(erls) and vec.shape[1] > 1

    # Phase 3: with-ERL vs price-only.
    erl_dm = build_design_matrix(events, prices, sessions, symbols, horizon=1, extra_features=vec)
    lift = compare_treatment(
        price_dm,
        erl_dm,
        "xgb",
        LEARNERS["xgb"],
        horizon=1,
        n_splits=4,
        embargo=pd.Timedelta(days=1),
    )
    assert isinstance(lift.da_lift, float)
    assert np.isfinite(lift.da_lift)
    # da_lift and the CI share the same clustered estimand (mean of per-event-date
    # lifts), so the point estimate must sit inside the bootstrap interval.
    assert lift.ci_lo <= lift.da_lift <= lift.ci_hi


def test_control_gates_run(tmp_path) -> None:
    """Neutral-text and shuffled-date gates execute and return finite lifts."""
    sessions, symbols, prices, events, text_df = _build_inputs()
    embedder = make_embedder(mock=True)
    erls = extract_erls(events, text_df, MockLLMClient(), tmp_path / "erl")
    real_vec = build_event_vectors(erls, embedder)
    neutral_vec = build_event_vectors(make_neutral_erls(events), embedder)
    shuffled_vec = shuffled_vectors(real_vec)

    price_dm = build_design_matrix(events, prices, sessions, symbols, horizon=1)
    emb = pd.Timedelta(days=1)
    for vec in (real_vec, neutral_vec, shuffled_vec):
        dm = build_design_matrix(events, prices, sessions, symbols, horizon=1, extra_features=vec)
        lift = compare_treatment(
            price_dm, dm, "xgb", LEARNERS["xgb"], horizon=1, n_splits=4, embargo=emb
        )
        assert np.isfinite(lift.da_lift)
        assert np.isfinite(lift.dm_p)
        assert np.isfinite(lift.dm_p_mbb)
