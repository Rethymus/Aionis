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
* **党派目录（join 源）**：``https://www.house.gov/representatives``
  （全体现任议员 HTML 目录，公共域，1 请求缓存）——姓名/州-选区/党派
  （R/D）。join 键 = **选区码 + 姓氏双重佐证**（防候选人/前议员错配：
  FD 行姓氏与该选区现任议员姓氏不一致 → 诚实 null）。

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


_STATE_ABBR: dict[str, str] = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
    "Puerto Rico": "PR", "Guam": "GU", "American Samoa": "AS",
    "U.S. Virgin Islands": "VI", "Northern Mariana Islands": "MP",
}

_ORDINALS = {
    "1st": "01", "2nd": "02", "3rd": "03", "4th": "04", "5th": "05",
    "6th": "06", "7th": "07", "8th": "08", "9th": "09", "10th": "10",
    "11th": "11", "12th": "12", "13th": "13", "14th": "14", "15th": "15",
    "16th": "16", "17th": "17", "18th": "18", "19th": "19", "20th": "20",
    "21st": "21", "22nd": "22", "23rd": "23", "24th": "24", "25th": "25",
    "26th": "26", "27th": "27", "28th": "28", "29th": "29", "30th": "30",
    "31st": "31", "32nd": "32", "33rd": "33", "34th": "34", "35th": "35",
    "36th": "36", "37th": "37", "38th": "38", "39th": "39", "40th": "40",
    "41st": "41", "42nd": "42", "43rd": "43", "44th": "44", "45th": "45",
    "46th": "46", "47th": "47", "48th": "48", "49th": "49", "50th": "50",
    "51st": "51", "52nd": "52",
}

_TABLE_RE = re.compile(
    r'<table class="table"[^>]*>.*?<caption[^>]*>\s*(.*?)\s*</caption>(.*?)</table>',
    re.S,
)
# The directory page ships TWO row orders (verified 2026-08-22): the
# by-state tables put the NAME cell first with the district spelled in full
# ("Alabama 4th"), other tables put the bare ORDINAL first ("4th"). Both are
# parsed; the union is deduplicated by office+name.
_DIR_ROW_NAME_FIRST_RE = re.compile(
    r'<a href="https://[^"]+\.house\.gov/?">([^<]+)</a>\s*</td>\s*'
    r"<td[^>]*>\s*([A-Za-z. ]*?\d{1,2}(?:st|nd|rd|th)|[A-Za-z. ]*?At[ -]Large)\s*</td>\s*"
    r"<td[^>]*>\s*([RDIL])\s*</td>",
)
_DIR_ROW_ORDINAL_FIRST_RE = re.compile(
    r'<td[^>]*>\s*(\d{1,2}(?:st|nd|rd|th)|At[ -]Large)\s*</td>\s*'
    r'<td[^>]*>\s*<a href="https://[^"]+\.house\.gov/?">([^<]+)</a>\s*</td>\s*'
    r"<td[^>]*>\s*([RDIL])\s*</td>",
)


def _office_code(state: str, district: str) -> str | None:
    """``("Alabama", "4th")`` / ``("Alabama", "Alabama 4th")`` -> ``"AL04"``.

    At-large districts ("At Large" / "Alaska At Large") -> ``"AK00"``. The
    ordinal is the last whitespace token, so both bare and state-prefixed
    spellings work; the state always comes from the table caption.
    """
    abbr = _STATE_ABBR.get(state.strip())
    if not abbr:
        return None
    tokens = district.strip().split()
    if not tokens:
        return None
    if tokens[-1].lower() in {"large", "-large"}:
        return f"{abbr}00"
    ordinal = _ORDINALS.get(tokens[-1])
    return f"{abbr}{ordinal}" if ordinal else None


def parse_house_directory_html(html: str) -> pd.DataFrame:
    """Parse house.gov/representatives into ``[name, office, party]``.

    One row per CURRENT voting/delegate member: ``"Aderholt, Robert"`` /
    ``"AL04"`` / ``"R"``. Both row orders on the page are parsed and the
    union deduplicated by office+name. Pure function — hermetic-testable
    against hand-written fixtures mirroring the verified 2026-08-22 shape.
    """
    seen: set[tuple[str, str]] = set()
    rows: list[dict] = []
    for state, body in _TABLE_RE.findall(html):
        pairs: list[tuple[str, str, str]] = []
        pairs.extend(
            (name, district, party)
            for name, district, party in _DIR_ROW_NAME_FIRST_RE.findall(body)
        )
        pairs.extend(
            (name, district, party)
            for district, name, party in _DIR_ROW_ORDINAL_FIRST_RE.findall(body)
        )
        for name, district, party in pairs:
            office = _office_code(state.strip(), district)
            key = (name.strip(), office or "")
            if not office or key in seen:
                continue
            seen.add(key)
            rows.append({
                "name": name.strip(),
                "office": office,
                "party": party.strip().upper(),
            })
    return pd.DataFrame(rows, columns=["name", "office", "party"])


def join_party(
    members: pd.DataFrame, directory: pd.DataFrame,
) -> list[str | None]:
    """Party per FD filing row — office match + LAST-NAME corroboration.

    The FD index also carries candidate/former-member filers whose StateDst
    names a district they do not currently hold; attributing the incumbent's
    party to them would be fabrication. So a party is linked only when the
    filing's last name matches the directory's last name for that office.
    Exact string match (casefold) only — no fuzzy guesswork. Pure function.
    """
    by_office: dict[str, list[tuple[str, str]]] = {}
    for _, r in directory.iterrows():
        by_office.setdefault(str(r["office"]), []).append(
            (str(r["name"]).split(",")[0].strip().casefold(), str(r["party"]))
        )
    out: list[str | None] = []
    for _, r in members.iterrows():
        last = str(r["member"]).split(",")[0].strip().casefold()
        cands = by_office.get(str(r["office"]), [])
        hits = {p for ln, p in cands if ln == last}
        out.append(hits.pop() if len(hits) == 1 else None)
    return out


def fetch_house_directory(cache_dir: Path | None = None) -> pd.DataFrame:
    """Current-member directory from house.gov (ONE polite cached request)."""
    fp = _cache_dir(cache_dir) / "house_directory.parquet"
    if fp.exists():
        return pd.read_parquet(fp)
    resp = _policy_get(
        "https://www.house.gov/representatives",
        total_attempts=3,
        backoff_base=4,
        backoff_mode="linear",
        headers={"User-Agent": _UA},
        timeout=120,
    )
    df = parse_house_directory_html(resp.text)
    fp.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(fp, index=False)
    log.info("house_directory_fetched", members=len(df))
    return df


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
