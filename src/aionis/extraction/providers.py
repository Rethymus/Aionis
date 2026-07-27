"""Provider definitions for the multi-key policy router.

Each provider is an OpenAI-compatible endpoint (GLM, SiliconFlow, ModelScope, …)
with its policy terms (RPM / TPM / daily quota). The router uses these terms to
auto-switch keys when one is rate-limited or out of quota. Adding a provider is
one entry here + its key in ``.env``.
"""
from __future__ import annotations

from dataclasses import dataclass

import structlog

from aionis.config import settings

log = structlog.get_logger()


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    api_key: str
    model: str
    priority: int            # lower = preferred
    rpm: int | None = None
    tpm: int | None = None
    daily_quota: int | None = None   # calls/day
    note: str = ""


# Static catalog. Policy terms from each platform's free-tier docs (2026-07).
_CATALOG: list[dict] = [
    {
        "name": "glm", "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": settings.openai_api_key, "model": settings.llm_model or "glm-4-flash",
        "priority": 1, "rpm": 30, "note": "GLM-4-Flash, free, concurrency-limited",
    },
    {
        "name": "siliconflow", "base_url": "https://api.siliconflow.cn/v1",
        "api_key": settings.siliconflow_api_key, "model": "Qwen/Qwen2.5-7B-Instruct",
        "priority": 2, "rpm": 1000, "tpm": 80000, "note": "9B-tier free",
    },
    {
        "name": "modelscope", "base_url": "https://api-inference.modelscope.cn/v1",
        "api_key": settings.modelscope_api_key, "model": "Qwen/Qwen3-Next-80B-A3B-Instruct",
        "priority": 3, "daily_quota": 2000, "note": "2000 calls/day (dynamic per-model)",
    },
]


def build_providers(only_enabled: bool = True) -> list[Provider]:
    """Materialize providers that have a key present; optionally skip disabled ones."""
    out: list[Provider] = []
    for d in _CATALOG:
        key = d.get("api_key")
        enabled = "DISABLED" not in d.get("note", "") and bool(key)
        if only_enabled and not enabled:
            continue
        if not key:
            continue
        out.append(
            Provider(
                name=d["name"], base_url=d["base_url"], api_key=key, model=d["model"],
                priority=d["priority"], rpm=d.get("rpm"), tpm=d.get("tpm"),
                daily_quota=d.get("daily_quota"), note=d.get("note", ""),
            )
        )
    log.info("providers_loaded", n=len(out), names=[p.name for p in out])
    return out
