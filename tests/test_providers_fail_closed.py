"""Provider catalog model pin is fail-closed (I8 silent-mutation guard).

2026-11-06: the glm entry used to fall back to the stale hardcoded id
'glm-4-flash' whenever LLM_MODEL was unset — the same wiring defect that
made three monthly CI vintage probes (2026-09/10/11) interrogate a model
the frozen contract never described. A present API key without a pinned
model id must now raise instead of routing extraction through a guessed
model; an absent key still skips green (CI semantics preserved).

Hermetic: no network — the catalog entries are patched in-place and only
the router's gating logic is exercised.
"""
from __future__ import annotations

import pytest

from aionis.extraction import providers

_GLM = providers._CATALOG[0]  # noqa: SLF001 — fixture: patch the glm entry


def test_glm_key_without_pinned_model_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(_GLM, "api_key", "k")
    monkeypatch.setitem(_GLM, "model", None)
    with pytest.raises(ValueError, match="refusing to route"):
        providers.build_providers(only_enabled=True)


def test_glm_materializes_pinned_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(_GLM, "api_key", "k")
    monkeypatch.setitem(_GLM, "model", "glm-4.7-flash")
    out = providers.build_providers(only_enabled=True)
    glm = [p for p in out if p.name == "glm"]
    assert glm and glm[0].model == "glm-4.7-flash"


def test_glm_absent_key_still_skips_green(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(_GLM, "api_key", None)
    monkeypatch.setitem(_GLM, "model", None)  # even misconfigured: no key, no raise
    out = providers.build_providers(only_enabled=True)
    assert all(p.name != "glm" for p in out)
