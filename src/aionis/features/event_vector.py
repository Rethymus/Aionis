"""ERL -> event feature vector (one row per event, shared across symbols).

Combines:
  * structural one-hots/scalars from the ERL fields (action, actor type, object
    type, temporal class, uncertainty, causal depth), and
  * a text embedding of the outcome-free canonical serialization.

Embedders are swappable (Protocol) so the pipeline runs offline: HashEmbedder
needs no dependencies; BGEEmbedder uses ``BAAI/bge-small-en-v1.5`` (CPU-friendly)
when the ``extraction`` extra is installed.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd

from aionis.config import EMBEDDING_MODEL_LOCAL
from aionis.schema.erl import ERL


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray: ...


class HashEmbedder:
    """Deterministic hashing-trick embedder (no dependencies)."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=float)
        for i, t in enumerate(texts):
            for tok in re.findall(r"\w+", t.lower()):
                h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
                sign = 1.0 if (h >> 9) & 1 else -1.0
                out[i, h % self.dim] += sign
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms


class BGEEmbedder:
    """Local BGE-small embedder (sentence-transformers; needs the extraction extra)."""

    def __init__(self, model_name: str = EMBEDDING_MODEL_LOCAL) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._model.encode(texts, normalize_embeddings=True), dtype=float)


class GLMEmbedder:
    """Real semantic embeddings via an OpenAI-compatible embedding API (no torch).

    Uses the ``openai`` SDK (the wheel) so transient network errors retry, instead
    of hand-rolled ``requests``. A swappable real embedder behind the Protocol —
    GLM is a test provider here, not an architectural dependency.

    Embeddings are DISK-CACHED by text hash. GLM embedding-3 is NOT bit-identical
    across calls (GPU fp reductions jitter ~6e-4 on a unit vector), and since the
    event vectors feed PCA -> xgb that sub-1e-3 jitter moved the headline every
    run. Caching pins each text to one realization so compare results are
    reproducible. The cache key includes the model name (switching models never
    collides). Inputs >64 are batched under the per-call cap (BadRequest 1214).
    """

    _MAX_BATCH = 32  # GLM embedding-3 caps input at 64 items per call.

    def __init__(
        self, api_key: str, base_url: str, model: str = "embedding-3", timeout: int = 60,
        cache_dir: Path | str | None = None,
    ) -> None:
        from openai import OpenAI

        self._client = OpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=3
        )
        self.model = model
        self._cache_dir = Path(cache_dir) if cache_dir else None
        if self._cache_dir is not None:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        self.dim = self._probe_dim()

    def _cache_path(self, text: str) -> Path | None:
        if self._cache_dir is None:
            return None
        digest = hashlib.sha1(f"{self.model}\x00{text}".encode()).hexdigest()
        return self._cache_dir / f"{digest}.json"

    def _load_cached(self, text: str) -> list[float] | None:
        p = self._cache_path(text)
        if p is not None and p.exists():
            return json.loads(p.read_text())["vector"]
        return None

    def _store(self, text: str, vector: list[float]) -> None:
        p = self._cache_path(text)
        if p is not None:
            p.write_text(json.dumps({"model": self.model, "vector": vector}))

    def _probe_dim(self) -> int:
        return int(self.embed(["dimension probe"]).shape[1])

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=float)
        resolved: list[list[float] | None] = [None] * len(texts)
        miss_idx: list[int] = []
        for i, t in enumerate(texts):
            cached = self._load_cached(t)
            if cached is not None:
                resolved[i] = cached
            else:
                miss_idx.append(i)
        # Batch only the cache misses through the API (under the 64-item cap).
        for start in range(0, len(miss_idx), self._MAX_BATCH):
            batch = miss_idx[start : start + self._MAX_BATCH]
            chunk = [texts[i] for i in batch]
            resp = self._client.embeddings.create(model=self.model, input=chunk)
            for d in resp.data:
                gi = batch[d.index]  # resp.data is index-sorted within the request
                vec = [float(x) for x in d.embedding]
                resolved[gi] = vec
                self._store(texts[gi], vec)
        out = np.asarray(resolved, dtype=float)
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms


def make_embedder(
    provider: str | None = None,
    mock: bool = False,
    dim: int = 64,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> Embedder:
    """Choose an embedder. Real semantic options: 'glm' (API, low-mem) or 'bge' (local)."""
    if mock or (provider and provider.lower() == "hash"):
        return HashEmbedder(dim=dim)
    provider = (provider or "bge").lower()
    if provider == "glm":
        from aionis.config import settings

        return GLMEmbedder(
            api_key=api_key or settings.openai_api_key,
            base_url=base_url or settings.llm_base_url,
            model=model or "embedding-3",
            cache_dir=Path(settings.data_dir) / "embedding_cache",
        )
    return BGEEmbedder()


def build_event_vectors(
    erls: dict[str, ERL],
    embedder: Embedder,
    pca_dim: int | None = None,
) -> pd.DataFrame:
    """One feature row per event (indexed by event_id) for the design matrix.

    ``pca_dim`` (optional) PCA-reduces the embedding to that many components —
    essential when the raw embedding dim (e.g. 2048) dwarfs the sample size and
    would overfit the downstream learner. PCA is fit on this event set only.
    """
    if not erls:
        return pd.DataFrame()
    ids = list(erls)
    texts = [erls[i].canonical_text() for i in ids]
    emb = embedder.embed(texts)
    emb_dim = embedder.dim
    if pca_dim and emb.shape[1] > pca_dim:
        from sklearn.decomposition import PCA

        if emb.shape[0] <= pca_dim:
            raise ValueError(
                f"pca_dim {pca_dim} must be < number of events {emb.shape[0]}"
            )
        emb = PCA(n_components=pca_dim, svd_solver="full").fit_transform(emb)
        emb_dim = pca_dim

    rows: list[dict] = []
    for k, eid in enumerate(ids):
        erl = erls[eid]
        row: dict[str, float] = {
            "act_" + erl.action.value: 1.0,
            "actor_" + erl.actor.type.value: 1.0,
            "obj_" + erl.object.type.value: 1.0,
            "temp_" + erl.temporal.value: 1.0,
            "uncertainty": float(erl.uncertainty),
            "n_causal": float(len(erl.causal_structure)),
        }
        for j in range(emb_dim):
            row[f"emb_{j}"] = float(emb[k, j])
        rows.append(row)
    df = pd.DataFrame(rows, index=pd.Index(ids, name="event_id")).fillna(0.0)
    return df
