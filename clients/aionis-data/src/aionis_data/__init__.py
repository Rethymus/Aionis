"""aionis-data — a read-only Python client for the Aionis public data API.

The deployed research terminal serves every committed panel as a JSON mirror
under ``https://rethymus.github.io/Aionis/api/v1/panels/<key>.json`` with a
catalog at ``/api/v1/catalog.json`` (56 endpoints; per-endpoint license /
provenance / as-of watermarks). This package is the OSAP ``openassetpricing``
-style convenience layer over that surface: claims, the realized IC series,
and arbitrary panels — as plain dicts/lists (no heavy dependencies; wrap in
pandas if you want frames).

Everything served is display-layer research output under
PolyForm-Noncommercial-1.0.0; nothing here can produce an out-of-sample
signal (the harness's nulls are the product).

Quickstart::

    from aionis_data import claims, ic_series, panel

    for key, c in claims().items():
        print(key, c["mean_diff"], f'CI [{c["ci_lo"]:.4f}, {c["ci_hi"]:.4f}]')

    series = [(r["month"], r["combined"]) for r in ic_series()
              if r["combined"] is not None]

    health = panel("data_health")

Offline/testing: inject your own loader — no network in tests::

    from aionis_data import AionisDataClient
    client = AionisDataClient(fetch_json=my_loader)   # my_loader(url) -> obj
"""
from __future__ import annotations

import ipaddress
import json
import socket
import urllib.request
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

DEFAULT_BASE_URL = "https://rethymus.github.io/Aionis/api/v1"
DEFAULT_TIMEOUT_S = 30.0

FetchJson = Callable[[str], Any]


# --- SSRF guard (stdlib-only twin of aionis.ingest._url_guard) ---------------
# This package is dependency-free by design, so the guard is re-implemented
# with the stdlib instead of importing the main repo's module. KEEP IN SYNC
# with src/aionis/ingest/_url_guard.py — the root repo's
# tests/test_url_guard.py pins the two deny tables equal so drift fails CI.

_ALLOW_SCHEMES = frozenset({"http", "https"})
_ALLOW_HOSTS = frozenset({"rethymus.github.io"})  # DEFAULT_BASE_URL's host
_DENIED_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "127.0.0.0/8",  # IPv4 loopback
        "0.0.0.0/8",  # "this network" — 0.0.0.0 reaches loopback on many stacks
        "10.0.0.0/8",  # RFC1918 private
        "172.16.0.0/12",  # RFC1918 private
        "192.168.0.0/16",  # RFC1918 private
        "169.254.0.0/16",  # link-local; 169.254.169.254 = cloud metadata endpoint
        "100.64.0.0/10",  # carrier-grade NAT — is_private is False (pinned test)
        "224.0.0.0/4",  # multicast
        "fc00::/7",  # IPv6 unique-local
        "fe80::/10",  # IPv6 link-local
        "::ffff:0:0/96",  # IPv4-mapped IPv6
        "64:ff9b::/96",  # NAT64 well-known prefix
    )
)


class UrlGuardError(ValueError):
    """Outbound URL refused by the client-side SSRF guard (fail-closed)."""


def _assert_safe_url(url: str) -> None:
    """Dual-pass, fail-closed: scheme + pinned-host allowlist, then EVERY
    A/AAAA record the host resolves to must fall outside the deny table
    (DNS-rebinding defense; IPv4-mapped forms normalized before compare).

    Honest limit: the subsequent ``urlopen`` performs its own resolution, so
    a TOCTOU window remains — this narrows, not eliminates (same stance as
    the canonical guard; see its docstring).
    """
    try:
        parts = urlsplit(url)
        host = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise UrlGuardError(f"unparseable URL {url!r}: {exc}") from exc
    if parts.scheme not in _ALLOW_SCHEMES:
        raise UrlGuardError(f"scheme {parts.scheme!r} not in {sorted(_ALLOW_SCHEMES)}")
    if host not in _ALLOW_HOSTS:
        raise UrlGuardError(f"host {host!r} not in {sorted(_ALLOW_HOSTS)}")
    try:
        records = socket.getaddrinfo(
            host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
        )
    except OSError as exc:
        raise UrlGuardError(f"DNS failure for {host!r} ({exc!r}) — fail closed") from exc
    if not records:
        # An empty resolution (incl. OS buffer-pressure shapes like ENOBUFS
        # surfacing as []) is refused, not passed — aligned with the canonical
        # guard; noted honestly, no absolute-safety claim (TOCTOU remains).
        raise UrlGuardError(f"{host!r} resolved to zero addresses — fail closed")
    for rec in records:
        addr = ipaddress.ip_address(rec[4][0])
        candidates = [addr]
        mapped = addr.ipv4_mapped if isinstance(addr, ipaddress.IPv6Address) else None
        if mapped is not None:
            candidates.append(mapped)
        for cand in candidates:
            for net in _DENIED_NETWORKS:
                if cand in net:
                    raise UrlGuardError(
                        f"{host!r} resolves to denied address {rec[4][0]} ({net})"
                    )


def _default_fetch_json(url: str, timeout: float = DEFAULT_TIMEOUT_S) -> Any:
    """stdlib-only fetch (requests is available in the main repo; the client
    itself avoids a hard dependency by using urllib — one less intake)."""
    # SSRF guard (fail-closed): pinned host allowlist + resolved-IP deny
    # table — see the stdlib-only twin block above.
    _assert_safe_url(url)
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


class AionisDataClient:
    """Read-only client over the Aionis public panel mirrors.

    ``fetch_json``: callable ``url -> parsed JSON``. Injectable for hermetic
    tests (no network); defaults to a stdlib urllib fetcher.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        fetch_json: FetchJson | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout_s
        if fetch_json is None:
            self._fetch: FetchJson = (
                lambda url: _default_fetch_json(url, timeout_s)
            )
        else:
            self._fetch = fetch_json

    # -- raw surfaces -----------------------------------------------------
    def panels(self) -> list[dict[str, Any]]:
        """Catalog endpoints (the 56 panels with per-endpoint license /
        freshness / as-of / source metadata). Only ``status == available``."""
        catalog = self._fetch(f"{self.base_url}/catalog.json")
        return [e for e in catalog.get("endpoints", [])
                if e.get("status") == "available"]

    def panel(self, key: str) -> Any:
        """Fetch one panel by key, e.g. ``panel("data_health")``."""
        return self._fetch(f"{self.base_url}/panels/{key}.json")

    # -- curated helpers ---------------------------------------------------
    def claims(self) -> dict[str, dict[str, Any]]:
        """The five pre-registered claims (B/C/D/E1/track_c) from the
        committed evidence_matrix panel: estimates, CIs, ledger rows,
        prereg doc paths, config sigs — bit-exact panel values."""
        matrix = self.panel("evidence_matrix")
        return matrix["claims"]

    def ic_series(self) -> list[dict[str, Any]]:
        """Realized Track C combined monthly rank-IC rows
        (``month`` / ``us`` / ``cn`` / ``combined``; null = not yet)."""
        return self.panel("ic_monthly")

    def combined_index(self) -> list[tuple[str, float]]:
        """Convenience: [(month, ic)] over realized (non-null) months."""
        return [(r["month"], float(r["combined"]))
                for r in self.ic_series() if r.get("combined") is not None]


_default_client = AionisDataClient()


def panels() -> list[dict[str, Any]]:
    """Module-level convenience — see :class:`AionisDataClient`."""
    return _default_client.panels()


def panel(key: str) -> Any:
    """Module-level convenience — see :class:`AionisDataClient`."""
    return _default_client.panel(key)


def claims() -> dict[str, dict[str, Any]]:
    """Module-level convenience — see :class:`AionisDataClient`."""
    return _default_client.claims()


def ic_series() -> list[dict[str, Any]]:
    """Module-level convenience — see :class:`AionisDataClient`."""
    return _default_client.ic_series()


def combined_index() -> list[tuple[str, float]]:
    """Module-level convenience — see :class:`AionisDataClient`."""
    return _default_client.combined_index()


__all__ = [
    "AionisDataClient",
    "DEFAULT_BASE_URL",
    "claims",
    "combined_index",
    "ic_series",
    "panel",
    "panels",
]
