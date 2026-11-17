"""Outbound URL guard (SSRF hardening) for the ingest fetchers — fail-closed.

Blueprint: OWASP SSRF Prevention Cheat Sheet, three rules in order:

1. **Allowlist first.** Every wired fetcher passes its own pinned set of
   endpoint hosts; a URL whose host is not in that set is refused before any
   DNS work. The nine wired call sites (ape_wisdom / ark_holdings / ff5 /
   news_feed / news_sentiment_gdelt / reddit_sentiment / theme_etfs /
   universe [shared choke point also serves universe_ext's Wikipedia fetch] /
   clients/aionis-data) mechanically close over their existing hardcoded
   endpoint domains — semantics zero-change for today's URLs.

2. **Validate every resolved address, immediately before the request.** A
   hostname that passes the name check is resolved via ``socket.getaddrinfo``
   (``AF_UNSPEC`` → all A + AAAA records) and EVERY returned address must be
   outside the deny table. This is the OWASP DNS-rebinding defense: a second,
   unvalidated DNS lookup between validation and connection is the classic
   bypass, so validation here happens against the same resolution the
   connection is about to use — narrowed, see the honesty note below.

3. **Explicit deny table, not ``is_private``.** ``ipaddress`` reports
   ``100.64.0.1`` (carrier-grade NAT) as ``is_private == False`` — pinned by
   test — so a single ``is_private`` gate would pass CGNAT payloads. The
   table below is the mission-pinned set: v4 127/8, 0/8, 10/8, 172.16/12,
   192.168/16, 169.254/16 (cloud metadata), 100.64/10, 224/4; v6 fc00::/7,
   fe80::/10, ::ffff:0:0/96 (IPv4-mapped), 64:ff9b::/96 (NAT64).
   "Normalize before you compare": IPv4-mapped IPv6 forms are additionally
   reduced to their embedded IPv4 via ``ipaddress`` before the membership
   tests.

Scheme gate: ``http``/``https`` only; anything else (``ftp:``, ``file:``,
``gopher:``, …) is refused — fail-closed.

Honest limits (do not overstate): this guard resolves the hostname itself,
but the subsequent ``requests``/``urllib`` connect performs its OWN
resolution — a TOCTOU window remains between the two lookups. This wiring
narrows that window and blocks hostname→private-address cases; it does NOT
eliminate the race. Pinning the validated IP and connecting to it directly
was deliberately rejected: for nine static endpoint domains it is
over-engineering and would change request behavior (virtual-host routing,
TLS SNI), violating the semantics-zero-change red line of this change.
"""
from __future__ import annotations

import ipaddress
import socket
import urllib.parse
from collections.abc import Iterable

import structlog

log = structlog.get_logger()

ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})

# Mission-pinned deny table — explicit networks, ordered as specified in the
# task. Do NOT collapse into is_private/is_global shortcuts (CGNAT pin above).
DENIED_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = tuple(
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
    """Outbound URL refused by the SSRF guard (fail-closed)."""


# Module seam so hermetic tests can fake DNS (no real lookups in the suite).
_getaddrinfo = socket.getaddrinfo


def _denied_network_for(
    addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
    for net in DENIED_NETWORKS:
        if addr in net:
            return net
    return None


def assert_resolved_ip_allowed(ip_text: str) -> None:
    """Deny-table check for ONE address — after normalization.

    Normalization ("normalize before you compare"): an IPv4-mapped IPv6
    (``::ffff:a.b.c.d``) is tested both as the IPv6 form (caught by the
    ``::ffff:0:0/96`` row) and as its embedded IPv4 address, so e.g.
    ``::ffff:10.0.0.1`` also matches the ``10.0.0.0/8`` row. Raises
    :class:`UrlGuardError` if any normalized view is denied.
    """
    addr = ipaddress.ip_address(ip_text)  # ValueError on malformed input
    candidates: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = [addr]
    mapped = addr.ipv4_mapped if isinstance(addr, ipaddress.IPv6Address) else None
    if mapped is not None:
        candidates.append(mapped)
    for cand in candidates:
        net = _denied_network_for(cand)
        if net is not None:
            raise UrlGuardError(
                f"address {ip_text!r} (normalized {cand}) is inside denied network {net}"
            )


def _check_scheme_and_host(
    url: str, allowed_hosts: frozenset[str]
) -> tuple[str, str, int | None]:
    try:
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname  # lowercased; brackets stripped for v6 literals
        port = parts.port  # raises ValueError on out-of-range ports
    except ValueError as exc:
        raise UrlGuardError(f"unparseable URL {url!r}: {exc}") from exc
    if parts.scheme not in ALLOWED_SCHEMES:
        raise UrlGuardError(
            f"scheme {parts.scheme!r} not in {sorted(ALLOWED_SCHEMES)} — fail closed"
        )
    if not host:
        raise UrlGuardError(f"URL {url!r} carries no host")
    if host not in allowed_hosts:
        raise UrlGuardError(
            f"host {host!r} not in this fetcher's allowlist {sorted(allowed_hosts)}"
        )
    return parts.scheme, host, port


def assert_scheme_host_allowed(url: str, allowed_hosts: Iterable[str]) -> str:
    """Pass 1 only (scheme + host allowlist) — NO DNS.

    Offline seam: lets hermetic tests prove the wired fetchers' existing URL
    constants pass the mechanical allowlist close without resolving anything.
    Returns the validated hostname.
    """
    _scheme, host, _port = _check_scheme_and_host(url, frozenset(allowed_hosts))
    return host


def assert_safe_url(url: str, allowed_hosts: Iterable[str]) -> list[str]:
    """Pass 1 + pass 2: allowlist the host, then validate EVERY A/AAAA record.

    Raises :class:`UrlGuardError` on any refusal — fail-closed, including on
    DNS resolution failure. Returns the validated addresses (for callers that
    want to log them).
    """
    allowed = frozenset(allowed_hosts)
    _scheme, host, port = _check_scheme_and_host(url, allowed)
    try:
        records = _getaddrinfo(
            host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
        )
    except OSError as exc:
        log.warning("outbound_url_denied", host=host, reason="dns_failure", error=str(exc))
        raise UrlGuardError(
            f"DNS resolution failed for allowlisted host {host!r} ({exc!r}) — fail closed"
        ) from exc
    addresses = [rec[4][0] for rec in records]  # sockaddr[0]: v4 and v6 alike
    if not addresses:
        log.warning("outbound_url_denied", host=host, reason="empty_resolution")
        raise UrlGuardError(f"host {host!r} resolved to zero addresses — fail closed")
    for ip_text in addresses:
        try:
            assert_resolved_ip_allowed(ip_text)
        except UrlGuardError as exc:
            log.warning("outbound_url_denied", host=host, url=url, reason=str(exc))
            raise
    return addresses


__all__ = [
    "ALLOWED_SCHEMES",
    "DENIED_NETWORKS",
    "UrlGuardError",
    "assert_resolved_ip_allowed",
    "assert_safe_url",
    "assert_scheme_host_allowed",
]
