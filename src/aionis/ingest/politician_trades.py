"""STOCK Act congressional trading — House PTR filing stream (display-only).

尽调结论（2026-08-21，真实探针留证于 docs/data-intake-congress-stock-act.md）：

* **House（clerk.house.gov）**：无官方 JSON API。搜索页是 ASP.NET 表单
  （``ViewSearch`` 携带 ``__RequestVerificationToken``），POST
  ``ViewMemberSearchResult`` 返回 HTML 表格：Name（含 PTR PDF 链接）/
  Office（州+选区）/Filing Year/Filing（``PTR Original`` 等）。**交易明细
  （资产/金额/日期）只在 PDF 内**，列表级仅年粒度、无申报日。
* **Senate（efdsearch.senate.gov）**：Akamai ``Access Denied``（普通 GET 即
  403），一手不可达——诚实披露为 blocked，不引入第三方绕过。

v1 = **House PTR 申报流级**：议员、选区、申报类型、年度、PDF 原文链。
不解析 PDF、不编造金额/日期/ticker；迟报天数（>45 天 STOCK Act 法定线）
在列表级数据下不可计算——如实不展示。

7-gate: U.S. House Clerk = federal public domain — G1✓；PIT = 申报年度
（列表级最细粒度，弱于 filed-date——methodology 披露）— G2 部分通过；
immutable PDF 存档 — G3✓；exploratory display-only — G5✓；礼貌
GET→POST 两请求/年 + 幂等缓存 — G7✓。
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests
import structlog

from aionis.ingest.form4_efts import _UA, _cache_dir
from aionis.ingest.http_policy import RetryPolicy
from aionis.ingest.universe import _HTTP_POLICY

log = structlog.get_logger()

_SEARCH_URL = "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewSearch"
_RESULT_URL = (
    "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewMemberSearchResult"
)
_PDF_BASE = "https://disclosures-clerk.house.gov/FinancialDisclosure/"

_TOKEN_RE = re.compile(
    r'name="__RequestVerificationToken"[^>]*value="([^"]+)"'
)
_ROW_RE = re.compile(
    r'<td data-label="Name"[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>\s*</td>\s*'
    r'<td data-label="Office"[^>]*>(.*?)</td>\s*'
    r'<td data-label="Filing Year"[^>]*>(.*?)</td>\s*'
    r'<td data-label="Filing"[^>]*>(.*?)</td>',
    re.S,
)


def parse_house_ptr_html(html: str, *, filing_year: int) -> pd.DataFrame:
    """Parse one ``ViewMemberSearchResult`` HTML page into PTR filings.

    Rows are ``[member, office, filing_type, filing_year, doc_url]``. Pure
    function — hermetic-testable against hand-written fixtures mirroring the
    verified 2026-08-21 response shape. Non-PTR rows (annual reports etc.)
    appear only in other search tabs; the member-search result is PTR-only
    per the verified response, but a defensive ``Filing``-prefix filter keeps
    the contract honest if the source mixes tabs.
    """
    rows: list[dict] = []
    for href, name, office, year, filing in _ROW_RE.findall(html):
        filing_clean = re.sub(r"<[^>]+>", " ", filing).strip()
        if not filing_clean.upper().startswith("PTR"):
            continue
        rows.append({
            "member": re.sub(r"<[^>]+>", " ", name).strip(),
            "office": re.sub(r"<[^>]+>", " ", office).strip(),
            "filing_type": filing_clean,
            "filing_year": int(year.strip() or filing_year),
            "doc_url": href if href.startswith("http") else _PDF_BASE + href,
        })
    return pd.DataFrame(
        rows,
        columns=["member", "office", "filing_type", "filing_year", "doc_url"],
    )


def _policy_request(url: str, op) -> requests.Response:
    """One policy-bound HTTP operation (spacing + bounded retry) — GET or POST.

    ``_policy_get`` is GET-only; the House flow needs a session POST with the
    CSRF token + cookies from the GET, so the operation callable carries the
    method while spacing/retry stay identical (≥2s, transient-only).
    """
    retry = RetryPolicy(max_retries=2, backoff_base=4.0, backoff_mode="linear")
    return _HTTP_POLICY.request(url, op, retry=retry)


def fetch_house_ptr_year(year: int, cache_dir: Path | None = None) -> pd.DataFrame:
    """All House PTR filings indexed for ``year`` (filing-stream level).

    GET ``ViewSearch`` (token + cookies) → POST ``ViewMemberSearchResult``
    → parse. Two polite requests per year; the assembled result is cached per
    year so reruns make no HTTP. Token/cookies live in one ``requests.Session``
    (the CSRF token is bound to the session cookie).
    """
    fp = _cache_dir(cache_dir) / f"house_ptr_{year}.parquet"
    if fp.exists():
        return pd.read_parquet(fp)

    session = requests.Session()
    session.headers.update({"User-Agent": _UA})

    def _get() -> requests.Response:
        return session.get(_SEARCH_URL, timeout=60)

    def _post() -> requests.Response:
        return session.post(
            _RESULT_URL,
            data={
                "LastName": "",
                "FilingYear": str(year),
                "State": "",
                "District": "",
                "__RequestVerificationToken": token,
            },
            timeout=60,
        )

    page = _policy_request(_SEARCH_URL, _get)
    m = _TOKEN_RE.search(page.text)
    if not m:
        raise RuntimeError(
            "House ViewSearch returned no __RequestVerificationToken "
            f"(shape change? status {page.status_code}, len {len(page.text)})"
        )
    token = m.group(1)

    result = _policy_request(_RESULT_URL, _post)
    df = parse_house_ptr_html(result.text, filing_year=year)
    fp.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(fp, index=False)
    log.info("house_ptr_fetched", year=year, filings=len(df))
    return df
