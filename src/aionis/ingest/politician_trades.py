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

import bisect
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
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


# =============================================================================
# v2 — TRANSACTION-LEVEL PTR PDF parsing (ported from salvage agent/politician
# 0b7867a/70f8ad2, never merged; revived 2026-08-23 by owner D4 granularity
# gate). The filing-stream section above stays untouched — this section adds
# per-transaction extraction from the PTR PDFs the filing stream links to.
#
# Verified live by the salvage branch (813 trades / 42 members, 2026-08-22):
# e-filed PTR PDFs are digitally native, encrypted with the PDF Standard
# Security Handler (/V 2 /R 3 — RC4, EMPTY user password), and recoverable
# with the Python standard library ONLY (MD5 key derivation per ISO 32000
# Algorithms 3.2/3.4 + a tiny RC4 + zlib + the embedded ToUnicode CMaps).
# No new dependency.
#
# Honesty invariants (this panel's contract):
# * ``extract_ptr_text`` returns "" for scanned/image PDFs — the caller
#   counts them as unparsed, never fabricates rows.
# * ``parse_ptr_transactions`` counts every date-pair+$ anchor as a row
#   CANDIDATE; candidates - parsed rows = parse failures (never silently
#   dropped).
# =============================================================================

# Owner codes printed ahead of the asset when the filer is not the member
# themselves (salvage, verified live: SP = spouse). Self rows carry no code —
# the owner group is OPTIONAL here (the salvage row regex made it mandatory,
# which would silently drop self-filed rows).
_OWNER_CODES = ("SP", "JT", "DC")

# Deterministic row CORE, right-anchored: the e-filed table emits the asset
# class tag, the transaction type letter (P/S/E/…, with an optional
# "(partial)"/"(full)" qualifier), the transacted date, the notification date,
# and the statutory $ band — each on its own line/cell, in THIS order
# (verified live 2026-08-23 on three filings: 20033705/20033762/20033830).
# The band may split across two lines ("$15,001 -\n$50,000") or be
# open-ended ("$50,000,001+").
_PTR_ROW_CORE_RE = re.compile(
    r"\[\s?([A-Z]{1,4})\s?\]\s+"      # asset-class tag cell ([ST]/[CS]/[GS]…)
    r"([A-Z])"                          # transaction type letter
    r"(?:\s*\((partial|full)\))?\s+"  # optional qualifier
    r"(\d{2}/\d{2}/\d{4})\s+"         # date of transaction
    r"(\d{2}/\d{2}/\d{4})\s+"         # notification date (in PDF)
    r"\$\s?([\d,]+)"                    # band min
    r"(?:\s*-\s*\$\s?([\d,]+)|\s*\+)?",  # band max | open-ended "+"
    re.S,
)

# Candidate anchor (superset of cores): type + two dates + $ amount WITHOUT
# requiring the asset-class tag — page-split rows lose their tag and land
# here as HONEST parse failures. ``candidates - rows - excluded`` is the
# disclosed parse-failure count; nothing is silently dropped.
_PTR_ROW_CANDIDATE_RE = re.compile(
    r"\b([A-Z])(?:\s*\((partial|full)\))?\s+"
    r"(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+\$",
    re.S,
)

# Kept transaction-type letters. E = exchange (verified live, e.g. "Mandatory
# Exchange" rows) — NOT a buy/sell, excluded from rows and counted separately.
_PTR_TYPES_KEPT = {"P", "S"}

# Line/cell classifiers for the backward walk above a row core. The e-filed
# footer between rows renders as marker cells ("F…S :", "New", "S…O :",
# "D :") each on its own line with their values below; page breaks re-emit
# the table header block ("ID/Owner/Asset/…/$200?"). All of these STOP the
# asset-name walk — they are never swallowed into an asset name.
_FOOTER_MARKER_RES = (
    re.compile(r"^F\s+S\s*:?\s*$"),
    re.compile(r"^S\s+O\s*:?\s*$"),
    re.compile(r"^D\s*:?\s*$"),
    re.compile(r"^New$"),
)
# Value-bearing footer markers: the cell line directly BELOW one of these is
# its VALUE (e.g. the brokerage-account annotation under "S O :") — never an
# asset-name line (verified live; the asset name follows the value, or the
# footer ends). "F S :"'s value is the "New" cell itself.
_VALUE_BEARING_MARKER_RES = (
    re.compile(r"^S\s+O\s*:?\s*$"),
    re.compile(r"^D\s*:?\s*$"),
)
_PAGE_HEADER_LINES = {
    "ID", "Owner", "Asset", "Transaction", "Type", "Date", "Notification",
    "Amount", "Cap.", "Gains >", "$200?",
}
_AMOUNT_LINE_RE = re.compile(r"^\$\s?[\d,]+\s*[-+]?\s*$")
_DATE_LINE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_TICKER_LINE_RE = re.compile(r"^\(\s*([A-Z.]{1,8})\s*\)$")
_ASSET_MAX_LINES = 2  # wrapped asset names span at most 2 lines (verified)


def _rc4(key: bytes, data: bytes) -> bytes:
    """RC4 — the only cipher the clerk's PDFs use (/V 2, no AES marker)."""
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) % 256
        S[i], S[j] = S[j], S[i]
    out = bytearray()
    i = j = 0
    for b in data:
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        out.append(b ^ S[(S[i] + S[j]) % 256])
    return bytes(out)


# ISO 32000 Table 23 padding string (empty user password -> just the pad).
_PW_PAD = bytes.fromhex("28BF4E5E4E758A4164004E56FFFA01082E2E00B6D0683E802F0CA9FE6453697A")


def _file_key_r3(o: bytes, p: int, file_id: bytes, length_bits: int) -> bytes:
    """Standard security handler file key, R>=3 (ISO 32000 Algorithm 3.2)."""
    h = hashlib.md5(
        _PW_PAD + o + p.to_bytes(4, "little", signed=True) + file_id
    )
    d = h.digest()
    for _ in range(50):
        d = hashlib.md5(d[: length_bits // 8]).digest()
    return d[: length_bits // 8]


def _object_key(fkey: bytes, num: int, gen: int, length_bits: int) -> bytes:
    """Per-object RC4 key (Algorithm 3.1)."""
    h = hashlib.md5(
        fkey + num.to_bytes(3, "little") + gen.to_bytes(2, "little")
    )
    return h.digest()[: min(length_bits // 8 + 5, 16)]


def _parse_cmap(text: str) -> dict[int, str]:
    """ToUnicode bfchar/bfrange -> {cid: unicode string}."""
    m: dict[int, str] = {}
    for block in re.findall(r"beginbfchar(.*?)endbfchar", text, re.S):
        for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            m[int(src, 16)] = "".join(
                chr(int(dst[i : i + 4], 16))
                for i in range(0, len(dst) - len(dst) % 4, 4)
            )
    for block in re.findall(r"beginbfrange(.*?)endbfrange", text, re.S):
        for lo, hi, base in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block
        ):
            b = int(base, 16)
            for c in range(int(lo, 16), int(hi, 16) + 1):
                m[c] = chr(b + c - int(lo, 16))
    return m


def extract_ptr_text(pdf_bytes: bytes) -> str:
    """Linearize the text of one (encrypted or plain) e-filed PTR PDF.

    Steps: locate the /Encrypt dict (Standard, R3, RC4 — empty user password;
    unencrypted files skip decryption), RC4+zlib-recover every stream, build
    per-font ToUnicode maps, then walk page content (including Form XObjects,
    where the transaction table lives) emitting decoded show-string runs.
    Returns "" when the PDF has no text layer (scanned image) — the caller
    counts it as unparsed, never fabricates.
    """
    raw = pdf_bytes

    # object table: last occurrence wins (incremental-update semantics).
    obj_start: dict[int, tuple[int, int]] = {}
    for m in re.finditer(rb"(?:^|\r?\n)(\d+)\s+(\d+)\s+obj\b", raw):
        obj_start[int(m.group(1))] = (int(m.group(2)), m.end())

    def body_of(num: int) -> bytes:
        hit = obj_start.get(num)
        if hit is None:
            return b""
        end = raw.find(b"endobj", hit[1])
        return raw[hit[1] : end if end != -1 else len(raw)]

    fkey: bytes | None = None
    nbits = 128
    enc = re.search(
        rb"/Filter\s*/Standard[^>]*?/R\s*(\d+)[^>]*?/Length\s*(\d+)[^>]*?/P\s*(-?\d+)[^>]*?/O\s*<([0-9A-Fa-f]+)>",
        raw,
    )
    if enc and int(enc.group(1)) >= 3:
        nbits = int(enc.group(2))
        p = int(enc.group(3))
        o = bytes.fromhex(enc.group(4).decode())
        idm = re.search(rb"/ID\s*\[\s*<([0-9A-Fa-f]+)>", raw)
        file_id = bytes.fromhex(idm.group(1).decode()) if idm else b""
        fkey = _file_key_r3(o, p, file_id, nbits)

    def stream_of(num: int) -> bytes:
        body = body_of(num)
        sm = re.search(rb">>\s*stream\r?\n", body)
        if not sm:
            return b""
        data = body[sm.end() :]
        cut = data.rfind(b"endstream")
        data = data[:cut].rstrip(b"\r\n") if cut != -1 else data.rstrip(b"\r\n")
        if fkey is not None:
            gen = obj_start.get(num, (0, 0))[0]
            data = _rc4(_object_key(fkey, num, gen, nbits), data)
        try:
            import zlib

            data = zlib.decompress(data)
        except zlib.error:
            pass  # not flate-compressed (rare; keep raw)
        return data

    # font object -> cmap
    cmaps: dict[int, dict[int, str]] = {}
    for num in obj_start:
        body = body_of(num)
        if b"/ToUnicode" not in body:
            continue
        tu = re.search(rb"/ToUnicode\s+(\d+)\s+\d+\s+R", body)
        if tu:
            cm = _parse_cmap(stream_of(int(tu.group(1))).decode("latin-1", "ignore"))
            if cm:
                cmaps[num] = cm
    if not cmaps:
        return ""  # no text fonts -> scanned/image PDF

    def decode_hex(hx: str, cmap: dict[int, str]) -> str:
        step = 4 if len(hx) % 4 == 0 else 2  # Identity-H uses 2-byte CIDs
        return "".join(
            cmap.get(int(hx[i : i + step], 16), "") for i in range(0, len(hx), step)
        )

    chunks: list[str] = []

    def walk_content(content: str, fonts: dict[str, dict[int, str]]) -> None:
        cur: dict[int, str] = {}
        token_re = re.compile(
            r"/(\w+)\s+[\d.]+\s+Tf"                 # font select
            r"|<([0-9A-Fa-f]+)>\s*Tj"               # hex show
            r"|\[((?:[^\\\[\]]|\\.)*)\]\s*TJ"        # array show
            r"|\(((?:[^()\\]|\\.)*)\)\s*Tj"          # literal show
            r"|\bT\*|\bET"                          # line breaks
        )
        for tok in token_re.finditer(content):
            g = tok.groups()
            if g[0] is not None:
                cur = fonts.get(g[0], {})
            elif g[1] is not None:
                chunks.append(decode_hex(g[1], cur))
            elif g[2] is not None:
                for hx in re.findall(r"<([0-9A-Fa-f]+)>", g[2]):
                    chunks.append(decode_hex(hx, cur))
                for lit in re.findall(r"\(((?:[^()\\]|\\.)*)\)", g[2]):
                    chunks.append(lit)
            elif g[3] is not None:
                chunks.append(g[3])
            else:
                chunks.append("\n")

    def fonts_from(body: bytes) -> dict[str, dict[int, str]]:
        fonts: dict[str, dict[int, str]] = {}
        fm = re.search(rb"/Font\s*<<(.*?)>>", body, re.S)
        if fm:
            for name, ref in re.findall(rb"/(\w+)\s+(\d+)\s+\d+\s+R", fm.group(1)):
                cmap = cmaps.get(int(ref))
                if cmap:
                    fonts[name.decode("latin-1")] = cmap
        return fonts

    # pages in document order
    page_nums = [
        int(m.group(1))
        for m in re.finditer(rb"/Kids\s*\[(.*?)\]", raw, re.S)
        for m2 in re.finditer(rb"(\d+)\s+\d+\s+R", m.group(1))
        for m in [m2]
    ]
    if not page_nums:  # no /Kids found — fall back to /Type /Page scan
        page_nums = [
            num
            for num in obj_start
            if re.sub(rb"\s+", b" ", body_of(num))[:120].startswith(b"<< /Type /Page ")
        ]
    for num in page_nums:
        body = body_of(num)
        if not body:
            continue
        fonts = fonts_from(body)
        contents = []
        cm = re.search(rb"/Contents\s+(\d+)\s+\d+\s+R", body)
        if cm:
            contents.append(stream_of(int(cm.group(1))).decode("latin-1", "ignore"))
        # Form XObjects carry the transaction table on page 1 of e-filed PTRs.
        for _name, ref in re.findall(rb"/(\w+)\s+(\d+)\s+\d+\s+R", body):
            fobj = int(ref)
            fbody = body_of(fobj)
            if b"/Subtype /Form" not in fbody:
                continue
            ffont = re.search(rb"/Font\s*<<(.*?)>>", fbody, re.S)
            for fname, fref in (
                re.findall(rb"/(\w+)\s+(\d+)\s+\d+\s+R", ffont.group(1))
                if ffont
                else []
            ):
                if int(fref) in cmaps:
                    fonts.setdefault(fname.decode("latin-1"), cmaps[int(fref)])
            contents.append(stream_of(fobj).decode("latin-1", "ignore"))
        for content in contents:
            walk_content(content, fonts)

    return "".join(chunks)


@dataclass(frozen=True)
class PtrTransaction:
    """One transaction row of a PTR, as parsed from the PDF text layer."""

    owner: str | None          # SP/JT/DC when the filer is not the member; None = self
    asset: str                 # asset description (ticker stripped)
    ticker: str                # uppercase ticker or "" when the PDF carries none
    asset_class: str           # raw bracket tag ("S"); never guessed into a label here
    direction: str             # "buy" | "sell_partial" | "sell_full"
    raw_type: str              # as printed ("P", "S", "S (partial)")
    date_transacted: date      # from the PDF row
    date_notified: date        # notification date printed in the PDF row
    range_min: float | None    # statutory band min (USD)
    range_max: float | None    # band max; None = open-ended "$X+"
    amount_range: str          # raw band text ("$15,001 - $50,000")


@dataclass(frozen=True)
class PtrParseResult:
    """Rows + the honest reconciliation counters behind them.

    ``n_candidates`` counts type+date+date+$ anchors (every table row ends in
    one, including page-split rows); ``n_excluded`` counts parsed cores whose
    transaction type is not P/S (e.g. E = exchange — disclosed, not silently
    dropped). Parse failures = ``n_candidates - len(rows) - n_excluded``.
    """

    rows: list[PtrTransaction]
    n_candidates: int
    n_excluded: int = 0


def _direction(tx_code: str, qualifier: str | None) -> str:
    """P -> buy; S -> sell_full / sell_partial (per the printed qualifier)."""
    if tx_code == "P":
        return "buy"
    return "sell_partial" if qualifier == "partial" else "sell_full"


def _raw_type(tx_code: str, qualifier: str | None) -> str:
    return f"{tx_code} ({qualifier})" if qualifier else tx_code


def _line_kind(line: str) -> str:
    """Classify one extracted cell-line for the backward asset walk."""
    s = line.strip()
    if not s:
        return "empty"
    if any(r.fullmatch(s) for r in _FOOTER_MARKER_RES):
        return "footer"
    if s in _PAGE_HEADER_LINES:
        return "header"
    if _AMOUNT_LINE_RE.fullmatch(s):
        return "amount"
    if _DATE_LINE_RE.fullmatch(s):
        return "date"
    if s in _OWNER_CODES:
        return "owner"
    return "text"


def parse_ptr_transactions(text: str) -> PtrParseResult:
    """Parse PTR transaction rows from extracted PDF text (line-per-cell).

    Right-anchored algorithm (calibrated 2026-08-23 on live 2026 filings):
    the deterministic row core ``[tag] type date date $band`` is matched
    first; the asset name / ticker / owner cells are then recovered by
    walking the line-per-cell text BACKWARD from the tag, stopping at footer
    markers ("F…S :", "New", "S…O :", "D :"), re-emitted page headers,
    amounts, dates, or an owner code. A left-anchored single regex (the
    salvage approach) swallows inter-row footer/page-header text into asset
    names whenever the Owner column is empty (self-filed rows — the 2026
    norm).

    Honest counting: ``n_candidates`` counts type+dates+$ anchors (every
    table row ends in one, including page-split rows that lost their tag);
    rows whose type is not P/S (e.g. E = exchange) are excluded and counted
    in ``n_excluded``; ``candidates - rows - excluded`` is the parse-failure
    count the panel discloses. Nothing is silently dropped.
    """
    clean = text.replace("\x00", " ")
    lines = clean.split("\n")
    # char-offset -> line-index map for the backward walk
    starts: list[int] = []
    pos = 0
    for ln in lines:
        starts.append(pos)
        pos += len(ln) + 1

    def line_at(char_idx: int) -> int:
        return bisect.bisect_right(starts, char_idx) - 1

    n_candidates = len(_PTR_ROW_CANDIDATE_RE.findall(clean))
    rows: list[PtrTransaction] = []
    n_excluded = 0
    for m in _PTR_ROW_CORE_RE.finditer(clean):
        (aclass, tcode, qual, d_tran, d_notif, lo, hi) = m.groups()
        try:
            dt = datetime.strptime(d_tran, "%m/%d/%Y").date()
            dn = datetime.strptime(d_notif, "%m/%d/%Y").date()
        except ValueError:
            continue
        # Sanity: a trade cannot be notified before it happened (noise match).
        if dt > dn:
            continue
        if tcode not in _PTR_TYPES_KEPT:
            n_excluded += 1
            continue

        # Backward walk over the cells above the tag: (TICKER)? name{1,2}
        # (OWNER)? — stop at footer/header/amount/date/empty cells; a text
        # cell directly below a value-bearing footer marker ("S O :"/"D :")
        # is the footer's VALUE, never an asset-name line.
        i = line_at(m.start()) - 1
        ticker = ""
        owner: str | None = None
        name_lines: list[str] = []
        while i >= 0 and len(name_lines) < _ASSET_MAX_LINES + 1:
            kind = _line_kind(lines[i])
            if kind == "empty":
                i -= 1
                continue
            if kind == "owner":
                owner = lines[i].strip()
                break
            if kind == "text":
                tk = _TICKER_LINE_RE.fullmatch(lines[i].strip())
                if tk and not name_lines:
                    ticker = tk.group(1)
                    i -= 1
                    continue
                if i > 0 and any(
                    r.fullmatch(lines[i - 1].strip()) for r in _VALUE_BEARING_MARKER_RES
                ):
                    break  # this text cell is the footer value, not the name
                name_lines.append(lines[i].strip())
                i -= 1
                continue
            break  # footer / header / amount / date cell ends the walk
        name_lines = name_lines[:_ASSET_MAX_LINES]
        name = re.sub(r"\s+", " ", " ".join(reversed(name_lines))).strip(" -–,")
        if not name or not any(c.isalpha() for c in name):
            continue  # no asset name recovered — falls through to failures

        # Wrapped names usually put the ticker on its own cell line (captured
        # above); single-line names carry it inline — extract it there too,
        # GATED on the stock asset-class + a security-type keyword so phrases
        # like "Annuity (RILA)" are never lifted as tickers.
        if not ticker and aclass == "ST":
            tk_inline = re.search(r"\(([A-Z][A-Z.]{0,7})\)\s*$", name)
            if tk_inline and any(
                k in name.lower() for k in (
                    "stock", "share", "ordinary", "common", "class", "corp",
                    "inc", "ltd", "plc", "adr", "ads",
                )
            ):
                ticker = tk_inline.group(1)
                name = name[: tk_inline.start()].strip(" -–,")

        lo_v = float(lo.replace(",", ""))
        hi_v = float(hi.replace(",", "")) if hi else None
        amount_range = (
            f"${int(lo_v):,}+" if hi_v is None else f"${int(lo_v):,} - ${int(hi_v):,}"
        )
        rows.append(PtrTransaction(
            owner=owner,
            asset=name,
            ticker=ticker,
            asset_class=aclass,
            direction=_direction(tcode, qual),
            raw_type=_raw_type(tcode, qual),
            date_transacted=dt,
            date_notified=dn,
            range_min=lo_v,
            range_max=hi_v,
            amount_range=amount_range,
        ))
    return PtrParseResult(
        rows=rows, n_candidates=n_candidates, n_excluded=n_excluded,
    )


def _doc_id_from_url(doc_url: str) -> tuple[str, str]:
    """``.../ptr-pdfs/{year}/{DocID}.pdf`` -> ``(year, DocID)``."""
    m = re.search(r"/ptr-pdfs/(\d{4})/([^/]+)\.pdf$", doc_url)
    if not m:
        raise ValueError(f"not a House PTR pdf url: {doc_url}")
    return m.group(1), m.group(2)


def fetch_ptr_pdf(doc_url: str, cache_dir: Path | None = None) -> bytes:
    """One PTR PDF by its clerk permalink (idempotent; cached per DocID).

    Politeness: one ``_policy_get`` per uncached file (>=2s host spacing +
    bounded linear backoff; 4xx is permanent — counted, never retried past).
    """
    year, doc_id = _doc_id_from_url(doc_url)
    fp = _cache_dir(cache_dir) / f"house_ptr_pdf_{year}_{doc_id}.pdf"
    if fp.exists():
        return fp.read_bytes()
    resp = _policy_get(
        doc_url,
        total_attempts=4,
        backoff_base=4,
        backoff_mode="linear",
        headers={"User-Agent": _UA},
        timeout=60,
    )
    fp.write_bytes(resp.content)
    return resp.content
