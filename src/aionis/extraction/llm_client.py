"""Swappable LLM client for ERL extraction + a multi-key policy router.

OpenAICompatClient uses the ``openai`` SDK (the universal wheel for any
OpenAI-compatible endpoint: GLM, SiliconFlow, ModelScope, …) with JSON mode +
pydantic validation + ONE bounded retry. ProviderRouter selects among providers
by policy terms (RPM / TPM / daily quota) and auto-switches keys on rate-limit or
quota exhaustion. MockLLMClient stays for unit-test fixtures. GLM is one provider
in the pool, not an architectural center.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Protocol

import structlog
from pydantic import ValidationError

from aionis.extraction.providers import Provider, build_providers
from aionis.schema.erl import (
    ERL,
    ActionType,
    Actor,
    ActorType,
    CausalLink,
    ERLObject,
    ObjectType,
    TemporalClass,
)

log = structlog.get_logger()

SYSTEM_PROMPT = """\
You extract a STRUCTURAL event representation (ERL) from an as-released
primary document.

Hard rules:
- Describe ONLY what happened structurally: who acted, what action, on what object,
  the a-priori expected temporal class, and a hypothesized causal mechanism.
- You MUST NOT mention, infer, or encode any market outcome: no price move, no
  'markets rose/fell', no magnitude of market response, no historical analogy's
  result. The summary and causal links must be outcome-free.
- Fill every field. Use the provided event_id and event_type. Pick closest enums.
- `uncertainty` is your a-priori confidence in the extraction (0..1), NOT anything
  about market impact."""

_ERL_SCHEMA_SPEC = """\
Return a JSON object with EXACTLY these top-level keys:
{
  "event_type": <string>,
  "actor": {
    "name": <string>,
    "type": <one of: government, central_bank, company, organization, individual, collective>,
    "influence_scope": <string>
  },
  "action": <one of: increase, decrease, restrict, encourage, delay, remove,
              replace, create, destroy, announce, hold>,
  "action_detail": <string>,
  "object": {
    "name": <string>,
    "type": <one of: macro, industry, entity>,
    "sector": <string>
  },
  "summary": <string; one sentence; structural only; NO price move or outcome>,
  "temporal": <one of: instant, short, medium, long>,
  "causal_structure": [{"cause": <string>, "effect": <string>}, ...],
  "uncertainty": <number 0..1, a-priori extraction confidence>
}
Do NOT include event_id or source_text_hash (the caller sets them).
For a policy-rate decision use hold (unchanged) / increase (hike) / decrease (cut)
— never 'adjust' or 'maintain'.
Do NOT mention any market result."""

_ERL_FIELDS = {
    "event_type",
    "actor",
    "action",
    "action_detail",
    "object",
    "summary",
    "temporal",
    "causal_structure",
    "uncertainty",
}


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class LLMClient(Protocol):
    def extract(self, text: str, event_id: str, event_type: str) -> ERL: ...


def _parse_and_validate(content: str, event_id: str, event_type: str, text: str) -> ERL:
    obj = {k: v for k, v in json.loads(content).items() if k in _ERL_FIELDS}
    obj.setdefault("event_type", event_type)
    return ERL.model_validate({**obj, "event_id": event_id, "source_text_hash": text_hash(text)})


# --- OpenAI-compatible client (the universal wheel) -------------------------


class OpenAICompatClient:
    """One OpenAI-compatible provider via the ``openai`` SDK, JSON mode + validation.

    Tracks ``last_usage`` so a router can account tokens against TPM/quotas.
    """

    def __init__(self, provider: Provider, timeout: float = 60.0) -> None:
        from openai import OpenAI

        self.provider = provider
        # max_retries=0: the router owns failover + cooldown. Letting the SDK
        # retry internally (default 2x w/ exponential backoff) multiplies latency
        # and hides rate-limits behind long hangs.
        self._client = OpenAI(
            api_key=provider.api_key, base_url=provider.base_url, timeout=timeout, max_retries=0
        )
        self.last_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    def _chat(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.provider.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        u = resp.usage
        self.last_usage = {
            "prompt_tokens": getattr(u, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(u, "completion_tokens", 0) or 0,
        }
        return resp.choices[0].message.content or ""

    def extract(self, text: str, event_id: str, event_type: str) -> ERL:
        system = SYSTEM_PROMPT + "\n\nJSON schema:\n" + _ERL_SCHEMA_SPEC
        user = f"event_type: {event_type}\nsource text:\n{text}"
        content = self._chat(system, user)
        try:
            return _parse_and_validate(content, event_id, event_type, text)
        except (ValidationError, json.JSONDecodeError):
            # One bounded retry feeding the failure back — no unbounded loop.
            content = self._chat(
                system,
                user
                + "\n\nPrevious reply was invalid. Return ONLY valid JSON matching the schema.",
            )
            return _parse_and_validate(content, event_id, event_type, text)


# --- Policy-aware multi-key router ------------------------------------------


class ProviderRouter(LLMClient):
    """Selects a provider by policy terms and auto-switches keys on failure.

    Selection: highest-priority (lowest number) provider that is not in cooldown
    and has remaining daily quota. On a rate-limit (429) the provider enters a
    cooldown and the next provider is tried. Token/call accounting is per-provider.
    """

    def __init__(self, providers: list[Provider], cooldown_seconds: int = 60) -> None:
        if not providers:
            raise RuntimeError("ProviderRouter needs at least one provider")
        self._order = sorted(providers, key=lambda p: p.priority)
        self._clients = {p.name: OpenAICompatClient(p) for p in providers}
        self._cooldown_seconds = cooldown_seconds
        self._cooldown_until: dict[str, float] = {}
        self.calls: dict[str, int] = {p.name: 0 for p in providers}
        self.tokens: dict[str, int] = {p.name: 0 for p in providers}
        self.served_by: dict[str, int] = {p.name: 0 for p in providers}

    def _available(self, p: Provider) -> bool:
        if self._cooldown_until.get(p.name, 0.0) > time.monotonic():
            return False
        if p.daily_quota is not None and self.calls[p.name] >= p.daily_quota:
            return False
        return True

    def extract(self, text: str, event_id: str, event_type: str) -> ERL:
        from openai import (
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
            BadRequestError,
            RateLimitError,
        )

        failures: list[str] = []
        for p in self._order:
            if not self._available(p):
                continue
            try:
                erl = self._clients[p.name].extract(text, event_id, event_type)
            except RateLimitError:
                self._cooldown_until[p.name] = time.monotonic() + self._cooldown_seconds
                log.warning("router_rate_limited", provider=p.name, cooldown=self._cooldown_seconds)
                failures.append(f"{p.name}: rate_limited")
                continue
            except (ValidationError, json.JSONDecodeError) as e:
                # A provider whose model can't produce schema-valid ERL (common for
                # small free-tier models) is treated as a failover trigger.
                log.warning("router_bad_output", provider=p.name, error=str(e)[:120])
                failures.append(f"{p.name}: invalid_output")
                continue
            except (APITimeoutError, APIConnectionError, BadRequestError, APIStatusError) as e:
                log.warning("router_provider_error", provider=p.name, error=str(e)[:140])
                failures.append(f"{p.name}: {type(e).__name__}")
                continue
            u = self._clients[p.name].last_usage
            self.calls[p.name] += 1
            self.tokens[p.name] += u["prompt_tokens"] + u["completion_tokens"]
            self.served_by[p.name] += 1
            log.info(
                "router_served",
                provider=p.name,
                event_id=event_id,
                cum_calls=self.calls,
                cum_tokens=self.tokens,
            )
            return erl
        raise RuntimeError(f"all providers exhausted for {event_id}: {failures}")


# --- Mock (test fixtures only) ----------------------------------------------


class MockLLMClient:
    """Deterministic, network-free ERL builder for unit-test fixtures only."""

    def extract(self, text: str, event_id: str, event_type: str) -> ERL:
        action = self._infer_action(text, event_type)
        actor, obj, temporal, causal = _TEMPLATE.get(event_type, _TEMPLATE["default"])
        return ERL(
            event_id=event_id,
            event_type=event_type,
            actor=actor,
            action=action,
            action_detail=f"{event_type} release (structural only)",
            object=obj,
            summary=(
                f"{actor.name} {action.value} regarding {obj.name}; "
                "no market outcome described."
            ),
            temporal=temporal,
            causal_structure=causal,
            uncertainty=0.5,
            source_text_hash=text_hash(text),
        )

    @staticmethod
    def _infer_action(text: str, event_type: str) -> ActionType:
        t = text.lower()
        if any(w in t for w in ("cut", "lower", "decrease", "reduce")):
            return ActionType.DECREASE
        if any(w in t for w in ("raise", "hike", "increase", "tighten")):
            return ActionType.INCREASE
        if any(w in t for w in ("hold", "unchanged", "maintain")):
            return ActionType.HOLD
        if any(w in t for w in ("restrict", "limit", "ban")):
            return ActionType.RESTRICT
        return ActionType.ANNOUNCE if event_type in ("CPI", "NFP") else ActionType.HOLD


_FED = Actor(name="Federal Reserve", type=ActorType.CENTRAL_BANK, influence_scope="global")
_BLS = Actor(
    name="Bureau of Labor Statistics", type=ActorType.ORGANIZATION, influence_scope="national"
)
_TEMPLATE: dict[str, tuple] = {
    "FOMC": (
        _FED,
        ERLObject(name="policy interest rate", type=ObjectType.MACRO, sector="macro"),
        TemporalClass.MEDIUM,
        [
            CausalLink(cause="policy rate", effect="borrowing cost"),
            CausalLink(cause="borrowing cost", effect="economic activity"),
        ],
    ),
    "CPI": (
        _BLS,
        ERLObject(name="consumer price index", type=ObjectType.MACRO, sector="macro"),
        TemporalClass.INSTANT,
        [CausalLink(cause="price level", effect="purchasing power")],
    ),
    "NFP": (
        _BLS,
        ERLObject(name="employment situation", type=ObjectType.MACRO, sector="macro"),
        TemporalClass.INSTANT,
        [CausalLink(cause="payroll employment", effect="labor income")],
    ),
    "default": (
        Actor(name="unknown", type=ActorType.ORGANIZATION, influence_scope="unknown"),
        ERLObject(name="unspecified", type=ObjectType.MACRO, sector="unknown"),
        TemporalClass.SHORT,
        [CausalLink(cause="event", effect="economic condition")],
    ),
}


def make_llm_client(provider: str | None = None, mock: bool = False) -> LLMClient:
    """Build a client. ``provider`` ∈ {router, glm, siliconflow, modelscope, openai, mock}.

    ``router`` (default from settings) = all enabled providers with failover;
    a specific name = a single-provider router (same interface, no failover).
    """
    if mock or (provider or "").lower() == "mock":
        return MockLLMClient()
    from aionis.config import settings

    name = (provider or settings.provider or "router").lower()
    if name == "openai":
        return _OpenAIStrictClient()
    providers = build_providers(only_enabled=True)
    if name == "router":
        if not providers:
            raise RuntimeError("no providers configured: add at least one key to .env")
        return ProviderRouter(providers)
    matched = [p for p in providers if p.name == name]
    if not matched:
        raise RuntimeError(
            f"provider {name!r} not available. Configured: {[p.name for p in providers]}"
        )
    return ProviderRouter(matched)


class _OpenAIStrictClient:
    """OpenAI proper via the SDK's strict structured outputs (``.parse``)."""

    def __init__(self) -> None:
        from openai import OpenAI

        from aionis.config import settings

        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not set for provider=openai")
        self._client = OpenAI(api_key=settings.openai_api_key, base_url=settings.llm_base_url)
        self.model = settings.llm_model or settings.openai_model

    def extract(self, text: str, event_id: str, event_type: str) -> ERL:
        resp = self._client.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"event_type: {event_type}\nsource text:\n{text}"},
            ],
            response_format=ERL,
        )
        msg = resp.choices[0].message
        if getattr(msg, "refusal", None):
            raise RuntimeError(f"OpenAI refused: {msg.refusal}")
        parsed = msg.parsed
        if parsed is None:
            raise RuntimeError("OpenAI returned no parsed ERL")
        return parsed.model_copy(
            update={
                "event_id": event_id,
                "event_type": event_type,
                "source_text_hash": text_hash(text),
            }
        )
