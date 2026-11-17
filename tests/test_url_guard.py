"""SSRF guard tests — hermetic (every DNS resolution is faked at the seam).

Pins the OWASP-blueprint behaviors the ingest-host-guard task requires:

* pass 1 — host allowlist close, refusing BEFORE any DNS work;
* pass 2 — every A/AAAA record from ``getaddrinfo`` checked against the
  explicit deny table (mocked: RFC1918 / loopback / CGNAT — the
  ``is_private == False`` miss / IPv4-mapped IPv6 / NAT64);
* scheme gate — http/https only, fail-closed;
* offline smoke — every URL the nine wired fetchers can request today
  passes pass 1 (semantics zero-change proof, no network);
* the aionis-data client's stdlib-only twin guard stays table-in-sync with
  the canonical module and refuses rebound addresses on its own path.

No test here touches the real resolver: ``_url_guard._getaddrinfo`` (and the
client's ``socket.getaddrinfo``) are monkeypatched.
"""
from __future__ import annotations

import ipaddress
import socket
import sys
from pathlib import Path

import pytest

from aionis.ingest import _url_guard as guard
from aionis.ingest import (
    ape_wisdom,
    ark_holdings,
    ff5,
    news_feed,
    news_sentiment_gdelt,
    reddit_sentiment,
    theme_etfs,
    universe,
)

ROOT = Path(__file__).resolve().parent.parent
CLIENT_SRC = ROOT / "clients" / "aionis-data" / "src"
sys.path.insert(0, str(CLIENT_SRC))

import aionis_data  # noqa: E402


def _fake_records(ips: tuple[str, ...], port: int | None) -> list[tuple]:
    out = []
    for ip in ips:
        if ":" in ip:
            out.append((socket.AF_INET6, socket.SOCK_STREAM, 6, "", (ip, port, 0, 0)))
        else:
            out.append((socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)))
    return out


def _dns(monkeypatch: pytest.MonkeyPatch, *ips: str) -> None:
    """Fake the guard's resolver seam to return exactly ``ips``."""

    def fake(host, port, family=0, type=0):  # noqa: A002 — getaddrinfo shape
        return _fake_records(ips, port)

    monkeypatch.setattr(guard, "_getaddrinfo", fake)


# --- pass 1: allowlist close --------------------------------------------------


def test_whitelisted_public_host_passes(monkeypatch) -> None:
    _dns(monkeypatch, "93.184.216.34")
    resolved = guard.assert_safe_url(ape_wisdom.STOCKS_URL, ape_wisdom.ALLOWED_HOSTS)
    assert resolved == ["93.184.216.34"]


def test_host_outside_allowlist_rejected_before_dns(monkeypatch) -> None:
    called: list = []
    monkeypatch.setattr(
        guard, "_getaddrinfo", lambda *a, **k: called.append(a) or []
    )
    with pytest.raises(guard.UrlGuardError, match="allowlist"):
        guard.assert_safe_url("https://attacker.example.com/api", ape_wisdom.ALLOWED_HOSTS)
    assert called == []  # pass 1 refuses BEFORE any DNS work


# --- pass 2: deny table via mocked getaddrinfo --------------------------------


def test_rfc1918_resolved_address_rejected(monkeypatch) -> None:
    _dns(monkeypatch, "10.1.2.3")
    with pytest.raises(guard.UrlGuardError, match="10.0.0.0/8"):
        guard.assert_safe_url(ape_wisdom.STOCKS_URL, ape_wisdom.ALLOWED_HOSTS)


def test_loopback_rejected(monkeypatch) -> None:
    _dns(monkeypatch, "127.0.0.1")
    with pytest.raises(guard.UrlGuardError, match="127.0.0.0/8"):
        guard.assert_safe_url(ape_wisdom.STOCKS_URL, ape_wisdom.ALLOWED_HOSTS)
    # An IP-literal URL is denied by the deny table even if the literal is
    # allowlisted — the deny table outranks the allowlist.
    _dns(monkeypatch, "127.0.0.1")
    with pytest.raises(guard.UrlGuardError):
        guard.assert_safe_url("http://127.0.0.1/x", {"127.0.0.1"})


def test_cgnat_rejected_despite_is_private_false(monkeypatch) -> None:
    # The single-check alternative this task rejected: is_private misses
    # carrier-grade NAT — pinned here so a future Python "fix" gets noticed.
    assert ipaddress.ip_address("100.64.0.1").is_private is False
    _dns(monkeypatch, "100.64.0.1")
    with pytest.raises(guard.UrlGuardError, match="100.64.0.0/10"):
        guard.assert_safe_url(ape_wisdom.STOCKS_URL, ape_wisdom.ALLOWED_HOSTS)


def test_mapped_ipv6_normalized_then_rejected(monkeypatch) -> None:
    _dns(monkeypatch, "::ffff:127.0.0.1")
    with pytest.raises(guard.UrlGuardError, match="::ffff:0:0/96"):
        guard.assert_safe_url(ape_wisdom.STOCKS_URL, ape_wisdom.ALLOWED_HOSTS)
    # NAT64 well-known prefix denied as-is.
    _dns(monkeypatch, "64:ff9b::127.0.0.1")
    with pytest.raises(guard.UrlGuardError, match="64:ff9b::/96"):
        guard.assert_safe_url(ape_wisdom.STOCKS_URL, ape_wisdom.ALLOWED_HOSTS)
    # Normalization ("normalize before you compare"): the embedded IPv4 is
    # unwrapped as an additional view; both views classify as denied.
    addr = ipaddress.ip_address("::ffff:10.2.3.4")
    assert addr.ipv4_mapped == ipaddress.ip_address("10.2.3.4")
    with pytest.raises(guard.UrlGuardError):
        guard.assert_resolved_ip_allowed("::ffff:10.2.3.4")


def test_every_resolved_record_checked_mixed_families(monkeypatch) -> None:
    # getaddrinfo (AF_UNSPEC) can return A + AAAA together; ONE bad record
    # among them refuses the request — the "all records, every IP" contract.
    _dns(monkeypatch, "93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946", "192.168.1.10")
    with pytest.raises(guard.UrlGuardError, match="192.168.0.0/16"):
        guard.assert_safe_url(ape_wisdom.STOCKS_URL, ape_wisdom.ALLOWED_HOSTS)


def test_dns_failure_and_empty_resolution_fail_closed(monkeypatch) -> None:
    def boom(host, port, family=0, type=0):  # noqa: A002
        raise OSError("resolver unreachable")

    monkeypatch.setattr(guard, "_getaddrinfo", boom)
    with pytest.raises(guard.UrlGuardError, match="fail closed"):
        guard.assert_safe_url(ape_wisdom.STOCKS_URL, ape_wisdom.ALLOWED_HOSTS)
    monkeypatch.setattr(guard, "_getaddrinfo", lambda *a, **k: [])
    with pytest.raises(guard.UrlGuardError, match="zero addresses"):
        guard.assert_safe_url(ape_wisdom.STOCKS_URL, ape_wisdom.ALLOWED_HOSTS)


# --- scheme gate --------------------------------------------------------------


def test_non_http_schemes_rejected() -> None:
    for url in (
        "ftp://apewisdom.io/x",
        "file:///etc/passwd",
        "gopher://apewisdom.io/x",
        "data:text/plain,hi",
    ):
        with pytest.raises(guard.UrlGuardError, match="scheme"):
            guard.assert_safe_url(url, ape_wisdom.ALLOWED_HOSTS)


# --- smoke: all nine wired fetchers pass pass 1 offline (zero semantics change)


def test_all_wired_fetcher_urls_pass_allowlist() -> None:
    """Semantics zero-change proof: every URL the nine wired call sites can
    request today passes pass 1 (scheme + host allowlist) — offline, no DNS.
    """
    ok = guard.assert_scheme_host_allowed
    # 1. ape_wisdom — main endpoint + sibling probes + pagination form.
    for url in (
        ape_wisdom.STOCKS_URL,
        ape_wisdom.STOCKS_URL + "?page=2",
        ape_wisdom.BASE + "/filter/all-posts",
        ape_wisdom.BASE + "/filter/crypto",
    ):
        ok(url, ape_wisdom.ALLOWED_HOSTS)
    # 2. ark_holdings — all eight pinned fund CSV endpoints.
    for url in ark_holdings.FUND_CSV_URLS.values():
        ok(url, ark_holdings.ALLOWED_HOSTS)
    # 3. ff5 — pinned bulk ZIP.
    ok(ff5.FF5_DAILY_ZIP_URL, ff5.ALLOWED_HOSTS)
    # 4/5. the two api.gdeltproject.org consumers (news_feed imports the
    # endpoint constant + allowlist from news_sentiment_gdelt).
    gdelt_query = news_sentiment_gdelt._GDELT_DOC_URL + "?query=x&mode=artlist&format=json"
    ok(gdelt_query, news_sentiment_gdelt.ALLOWED_HOSTS)
    ok(gdelt_query, news_feed.ALLOWED_HOSTS)
    # 6. reddit_sentiment — the RSS feed URL shape built in _pull_posts_rss.
    ok(
        f"https://www.reddit.com/r/stocks/new.rss?limit={reddit_sentiment._RSS_LIMIT}",
        reddit_sentiment.ALLOWED_HOSTS,
    )
    # 7. theme_etfs — iShares direct CSVs + Global X fund pages + the dated
    # Global X CSV href shape extracted from those pages (_GX_CSV_RE).
    for spec in theme_etfs.FUND_DEFS.values():
        if "page" in spec:
            ok(spec["page"], theme_etfs.ALLOWED_HOSTS)
        if "url" in spec:
            ok(spec["url"], theme_etfs.ALLOWED_HOSTS)
    ok(
        "https://assets.globalxetfs.com/funds/holdings/"
        "icln_full-holdings_20260101.csv",
        theme_etfs.ALLOWED_HOSTS,
    )
    # 8. universe — its two pinned sources (the guard is wired at these two
    # call sites, NOT in the shared _policy_get helper, which also serves
    # many non-universe modules — see the ALLOWED_HOSTS note in universe.py).
    ok(universe._HANSHOF_URL, universe.ALLOWED_HOSTS)
    ok(universe._PB_TARBALL, universe.ALLOWED_HOSTS)
    # 9. aionis-data client — the pinned panel-mirror surface.
    ok(aionis_data.DEFAULT_BASE_URL + "/catalog.json", aionis_data._ALLOW_HOSTS)
    ok(
        aionis_data.DEFAULT_BASE_URL + "/panels/data_health.json",
        aionis_data._ALLOW_HOSTS,
    )


# --- the client's stdlib-only twin guard ---------------------------------------


def test_client_guard_tables_in_sync_with_canonical() -> None:
    assert aionis_data._DENIED_NETWORKS == guard.DENIED_NETWORKS
    assert aionis_data._ALLOW_SCHEMES == guard.ALLOWED_SCHEMES


def test_client_default_fetch_refuses_rebound_loopback(monkeypatch) -> None:
    # The client's own network exit (_default_fetch_json) refuses a host that
    # rebinds to loopback — DNS faked through the socket module seam.
    monkeypatch.setattr(
        aionis_data.socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )
    with pytest.raises(aionis_data.UrlGuardError, match="127.0.0.0/8"):
        aionis_data._default_fetch_json(aionis_data.DEFAULT_BASE_URL + "/catalog.json")


def test_client_guard_refuses_empty_resolution(monkeypatch) -> None:
    # Zero-address resolution (e.g. OS buffer-pressure shapes) is refused,
    # NOT passed — the twin guard stays aligned with the canonical one.
    monkeypatch.setattr(aionis_data.socket, "getaddrinfo", lambda *a, **k: [])
    with pytest.raises(aionis_data.UrlGuardError, match="zero addresses"):
        aionis_data._assert_safe_url(aionis_data.DEFAULT_BASE_URL + "/catalog.json")


def test_client_guard_allows_public_resolution(monkeypatch) -> None:
    monkeypatch.setattr(
        aionis_data.socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("185.199.108.153", 443))],
    )
    aionis_data._assert_safe_url(aionis_data.DEFAULT_BASE_URL + "/catalog.json")
