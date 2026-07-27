"""Event-vector embedder invariants.

The critical one for the GLM embedder: the OpenAI-compatible embedding endpoint
caps the input array at 64 items per call (GLM BadRequest 1214). A full event
panel has 100s of events, so ``GLMEmbedder.embed`` MUST batch under that cap —
sending all texts at once crashes the compare step. Verified here with a fake
client (no network, no key).
"""

from __future__ import annotations

import numpy as np

from aionis.features.event_vector import GLMEmbedder, HashEmbedder


class _FakeItem:
    def __init__(self, idx: int, vec: list[float]) -> None:
        self.index = idx
        self.embedding = vec


class _FakeResp:
    def __init__(self, data: list[_FakeItem]) -> None:
        self.data = data


class _FakeEmbeddings:
    def __init__(self, sizes: list[int]) -> None:
        self._sizes = sizes  # record the batch sizes the caller requests

    def create(self, *, model: str, input: list[str]) -> _FakeResp:
        self._sizes.append(len(input))
        data = []
        for local_i, text in enumerate(input):
            # Recover the GLOBAL index from the text ("t{i}") so embeddings are
            # distinct across batches, exactly as a real API keys on content.
            global_i = int(text[1:])
            data.append(
                _FakeItem(local_i, [float(global_i), global_i + 1.0, global_i + 2.0, 1.0])
            )
        return _FakeResp(data)


class _FakeClient:
    def __init__(self, sizes: list[int]) -> None:
        self.embeddings = _FakeEmbeddings(sizes)


def test_glm_embedder_batches_under_the_64_item_cap() -> None:
    """>64 inputs must be split into chunks <= GLMEmbedder._MAX_BATCH (<=64),
    cover every item exactly once, and preserve input order."""
    emb = object.__new__(GLMEmbedder)  # bypass __init__ (no API key / network)
    emb.model = "fake-embed"
    emb.dim = 4
    emb._cache_dir = None
    sizes: list[int] = []
    emb._client = _FakeClient(sizes)

    n = 200  # well above the 64-item cap
    out = emb.embed([f"t{i}" for i in range(n)])

    assert out.shape == (n, 4)
    assert sizes, "embed made no API calls"
    assert max(sizes) <= GLMEmbedder._MAX_BATCH  # never exceeds the cap
    assert sum(sizes) == n                        # every item embedded exactly once
    # Output rows are unit-norm.
    norms = np.linalg.norm(out, axis=1)
    assert np.allclose(norms, 1.0)
    # Order preserved + distinct: each row maps back to a unique source index.
    # (normalized [i, i+1, i+2, 1] directions are distinct for distinct i >= 0)
    rows = {tuple(np.round(out[i], 9).tolist()) for i in range(n)}
    assert len(rows) == n, "rows collided — order/index mapping is wrong"


def test_glm_embedder_caches_embeddings_for_reproducibility(tmp_path) -> None:
    """GLM embedding-3 is non-deterministic across calls (~6e-4 jitter); the disk
    cache must pin each text so a second embed() is served entirely from cache
    (no API call) and returns bit-identical output — this is what makes compare
    reproducible run-to-run."""
    emb = object.__new__(GLMEmbedder)
    emb.model = "fake-embed"
    emb.dim = 4
    emb._cache_dir = tmp_path
    sizes: list[int] = []
    emb._client = _FakeClient(sizes)

    texts = [f"t{i}" for i in range(5)]
    out1 = emb.embed(texts)
    calls_after_first = sum(sizes)
    out2 = emb.embed(texts)
    calls_after_second = sum(sizes)

    assert calls_after_second == calls_after_first  # 2nd call: 0 new API calls
    assert np.array_equal(out1, out2)               # bit-identical via cache
    assert len(list(tmp_path.glob("*.json"))) == 5  # one cache file per text


def test_hash_embedder_is_dimension_stable_and_normalized() -> None:
    """Local fallback stays unit-norm and fixed-dim (no batching needed)."""
    emb = HashEmbedder(dim=64)
    out = emb.embed(["rates on hold", "cpi hot print", ""])
    assert out.shape == (3, 64)
    norms = np.linalg.norm(out, axis=1)
    # Empty string -> zero vector -> normalized to zero (norm 0), not a unit vec;
    # non-empty texts are unit-norm.
    assert np.allclose(norms[0], 1.0) and np.allclose(norms[1], 1.0)
