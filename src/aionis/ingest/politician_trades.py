"""STOCK Act congressional trading — House PTR filing stream (display-only).

尽调结论（2026-08-21，两路独立探针交叉验证——本主线 + 并发 session 的
`docs/data-intake-stockact.md`（agent/politician a2f719b））：

* **House 批量索引（v1 数据路径）**：
  ``https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{YYYY}FD.zip``
  — 日更重发的全年申报索引 ZIP（2026 实测 56KB，Last-Modified 当日），
  内含 ``{YYYY}FD.xml``：每件披露的 ``Prefix/Last/First/Suffix/
  FilingType/StateDst/Year/FilingDate/DocID``。``FilingType == "P"`` 即
  PTR（2026 年 359 件）。**FilingDate 为真实申报日（M/D/YYYY）**——比
  搜索 UI 的年粒度强一档。PTR 原件直链：
  ``public_disc/ptr-pdfs/{YYYY}/{DocID}.pdf``。
* **House 搜索 UI（备用路径，已验证但不用）**：CSRF-token POST 返回
  HTML 行（无申报日字段）。
* **Senate（efdsearch.senate.gov）**：Akamai ``Access Denied``——诚实
  披露为 blocked，不引入第三方绕过。

v1 = **House PTR 申报流级**：议员、选区、申报日、年度、PDF 原文链。
交易明细（资产/金额/交易日期）只在 PDF 内，不解析；迟报天数（45 天
法定线）需交易日期，不可计算——如实不展示。

7-gate: U.S. House Clerk = federal public domain — G1✓；PIT = FilingDate
（申报日）— G2✓；G3 条件通过（ZIP 日更重发不可证伪 → 幂等 cache 即
冻结快照 + 修正件为追加式新 DocID）；exploratory display-only — G5✓；
礼貌 1 请求/年 — G7✓。
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd
import structlog

from aionis.ingest.form4_efts import _UA, _cache_dir
from aionis.ingest.universe import _policy_get

log = structlog.get_logger()

_FD_ZIP_URL = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
_PTR_PDF_URL = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc_id}.pdf"

_PTR_TYPE = "P"  # FilingType code for Periodic Transaction Reports


def _norm_date(raw: str) -> str | None:
    """``"6/11/2026"`` -> ``"2026-06-11"`` (M/D/YYYY as filed). None if blank."""
    raw = (raw or "").strip()
    if not raw:
        return None
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    if not m:
        return None
    mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{y:04d}-{mo:02d}-{d:02d}"


def _full_name(prefix: str, last: str, first: str, suffix: str) -> str:
    parts = [p.strip() for p in (prefix, first) if p and p.strip()]
    name = f"{last.strip()}, {' '.join(parts)}".strip(", ")
    if suffix and suffix.strip():
        name = f"{name}, {suffix.strip()}"
    return name


def parse_fd_xml(xml_text: str, *, filing_year: int) -> pd.DataFrame:
    """Parse one ``{YYYY}FD.xml`` bulk index into PTR filings.

    Rows are ``[member, office, filing_type, filing_date, filing_year,
    doc_url]`` — only ``FilingType == "P"`` (PTR) rows are kept; every other
    disclosure class (annual/extension/candidate/...) is dropped. Pure
    function — hermetic-testable against hand-written fixtures mirroring the
    verified 2026-08-21 response shape.
    """
    rows: list[dict] = []
    root = ElementTree.fromstring(xml_text)
    for m in root.iter("Member"):
        def _t(tag: str, m=m) -> str:
            node = m.find(tag)
            return (node.text or "").strip() if node is not None else ""

        if _t("FilingType") != _PTR_TYPE:
            continue
        doc_id = _t("DocID")
        if not doc_id:
            continue
        rows.append({
            "member": _full_name(_t("Prefix"), _t("Last"), _t("First"), _t("Suffix")),
            "office": _t("StateDst"),
            "filing_type": "PTR",
            "filing_date": _norm_date(_t("FilingDate")),
            "filing_year": int(_t("Year") or filing_year),
            "doc_url": _PTR_PDF_URL.format(year=filing_year, doc_id=doc_id),
        })
    return pd.DataFrame(
        rows,
        columns=["member", "office", "filing_type", "filing_date", "filing_year", "doc_url"],
    )


def fetch_house_ptr_year(year: int, cache_dir: Path | None = None) -> pd.DataFrame:
    """All House PTR filings indexed for ``year`` (filing-stream level).

    ONE polite request per year (the bulk FD.zip), cached as parquet so
    reruns make no HTTP — the cache is also the G3 freeze-snapshot of a
    source that re-emits its ZIP daily.
    """
    fp = _cache_dir(cache_dir) / f"house_ptr_{year}.parquet"
    if fp.exists():
        return pd.read_parquet(fp)

    url = _FD_ZIP_URL.format(year=year)
    resp = _policy_get(
        url,
        total_attempts=3,
        backoff_base=4,
        backoff_mode="linear",
        headers={"User-Agent": _UA},
        timeout=120,
    )
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xml_name = next(
            (n for n in zf.namelist() if n.lower().endswith(".xml")), None,
        )
        if not xml_name:
            raise RuntimeError(f"FD.zip for {year} contains no XML index: {zf.namelist()}")
        xml_text = zf.read(xml_name).decode("utf-8-sig", errors="replace")

    df = parse_fd_xml(xml_text, filing_year=year)
    fp.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(fp, index=False)
    log.info("house_ptr_fetched", year=year, filings=len(df))
    return df
