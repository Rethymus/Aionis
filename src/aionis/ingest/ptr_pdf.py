"""House PTR PDF decryption + transaction-row parser (salvage revival, TASK-S).

Revived 2026-08-23 from the ``agent/politician`` salvage branch (commits
a2f719b/0b7867a, 2026-08-22 round) into a standalone module so the live
filing-stream panel (``politician_trades.json``, House bulk FD.xml chain)
can gain TRANSACTION-level granularity without touching that chain.

Stack (all pure stdlib — no pypdf): ISO 32000 Algorithms 3.2/3.4 RC4 key
derivation for the Standard Security Handler (/V 2 /R 3, empty user
password — every e-filed House PTR), embedded ToUnicode CMap recovery, a
streaming row regex with sane-date filters and honest skip counting.

House Clerk PTR PDFs: U.S. Government public domain (17 U.S.C. §105);
fetched politely (>=2s host spacing) with per-DocID idempotent disk cache.
DISPLAY LANE ONLY — never enters features/eval/OOS, never touches the ledger.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import structlog

from aionis.config import settings
from aionis.ingest.http_policy import HTTPStatusError
from aionis.ingest.universe import _policy_get

log = structlog.get_logger()

_UA = "Aionis research politician-trades contact@example.com"
_PTR_PDF_URL = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc_id}.pdf"

def _rc4(key: bytes, data: bytes) -> bytes:
    """RC4 (the only cipher the clerk's PDFs use — /V 2, no AES marker)."""
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
            for fname, fref in re.findall(
                rb"/(\w+)\s+(\d+)\s+\d+\s+R", re.search(rb"/Font\s*<<(.*?)>>", fbody, re.S).group(1)
            ) if re.search(rb"/Font\s*<<(.*?)>>", fbody, re.S) else []:
                if int(fref) in cmaps:
                    fonts.setdefault(fname.decode("latin-1"), cmaps[int(fref)])
            contents.append(stream_of(fobj).decode("latin-1", "ignore"))
        for content in contents:
            walk_content(content, fonts)

    return "".join(chunks)


@dataclass(frozen=True)
class PtrTransaction:
    """One transaction row of a PTR (buy or sell only — exchanges skipped)."""

    owner: str
    asset: str
    ticker: str
    tx_type: str  # canonical "buy" | "sell"
    raw_type: str  # as printed ("P", "S", "S (partial)", ...)
    date_transacted: date
    date_disclosed: date
    range_min: float | None
    range_max: float | None


_TYPE_RE = r"(P|S(?:\s*\((?:partial|full)\)?)?)"
_DATE_RE = r"(\d{2}/\d{2}/\d{4})"
_AMOUNT_RE = r"(\$\s?[\d,]+\s*(?:-\s*\$?\s?[\d,]+|\+))"
# Anchor: [asset-type code] + type + transacted + disclosed + amount. The
# e-filed table emits exactly this sequence per row (verified on live 2026
# filings); chunk between anchors = owner code + asset name (+ ticker).
_ROW_ANCHOR_RE = re.compile(
    rf"\[([A-Z]{{1,4}})\]\s*{_TYPE_RE}\s*{_DATE_RE}\s*{_DATE_RE}\s*{_AMOUNT_RE}",
    re.S,
)


def _range_values(amount: str) -> tuple[float | None, float | None]:
    """'$15,001 - $50,000' -> (15001.0, 50000.0); '$50,000,001+' -> (50000001.0, None)."""
    nums = [float(n.replace(",", "")) for n in re.findall(r"[\d,]{3,}", amount)]
    if not nums:
        return None, None
    if len(nums) == 1:
        return nums[0], None
    return nums[0], nums[1]


def parse_ptr_rows(text: str) -> list[PtrTransaction]:
    """Parse PTR transaction rows from extracted PDF text (line-per-cell).

    The extraction yields each table cell on its own line (owner code, asset
    name — possibly wrapped, with the ticker as a parenthetical — the [TYPE]
    asset tag, the single-letter transaction type with an optional
    "(partial)", transacted date, notification date, and a $min - $max range
    that may split across two lines). A streaming regex over the whole text
    with whitespace bridging newlines is more robust than per-line matching.
    Rows whose transaction type is not Purchase/Sale (exchanges etc.) are
    skipped and counted, mirroring the original contract.
    """
    clean = text.replace("\x00", " ")
    row_re = re.compile(
        r"\b(SP|JT|DC)\s+"                       # owner code
        r"(.{3,140}?)\s*"                          # asset name (lazy, may wrap)
        r"\[([A-Z]{1,4})\]\s*"                   # asset type tag
        r"\b([SP])(?:\s*\(partial\))?\s+"       # txn type (P/S, maybe partial)
        r"(\d{2}/\d{2}/\d{4})\s+"               # transacted date
        r"(\d{2}/\d{2}/\d{4})\s+"               # notification date
        r"\$([\d,]+)"                             # min dollar amount
        r"\s*-?\s*"
        r"\$([\d,]+)",                            # max
        re.S,
    )
    rows: list[PtrTransaction] = []
    skipped = 0
    for m in row_re.finditer(clean):
        owner, asset, _asset_tag, ttype, d_tran, d_notif, lo, hi = m.groups()
        # Filter noise matches: the asset name must contain a letter and the
        # dates must be sane (transacted <= notified).
        try:
            dt = datetime.strptime(d_tran, "%m/%d/%Y").date()
            dn = datetime.strptime(d_notif, "%m/%d/%Y").date()
        except ValueError:
            skipped += 1
            continue
        if dt > dn:
            skipped += 1
            continue
        tk = re.search(r"\(([A-Z.]{1,6})\)", asset)
        ticker = tk.group(1).replace(".", "-") if tk else ""
        name = re.sub(r"\s+", " ", asset.replace(f"({tk.group(1)})", "") if tk else asset).strip(" -–")
        rows.append(PtrTransaction(
            owner=owner,
            asset=name,
            ticker=ticker,
            tx_type="buy" if ttype == "P" else "sell",
            raw_type=ttype,
            date_transacted=dt,
            date_disclosed=dn,
            range_min=float(lo.replace(",", "")),
            range_max=float(hi.replace(",", "")),
        ))
    n_total = len(rows) + skipped
    if n_total:
        log.info("stockact_ptr_rows_parsed", n=len(rows), skipped=skipped)
    else:
        log.info("stockact_ptr_rows_parsed", n=0, skipped=skipped)
    return rows


def _cache_dir(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_polite(url: str) -> bytes:
    """One polite GET (>=2s host spacing, linear backoff, permanent-4xx fast)."""
    try:
        return _policy_get(
            url,
            total_attempts=4,
            backoff_base=4,
            backoff_mode="linear",
            headers={"User-Agent": _UA},
            timeout=60,
        ).content
    except HTTPStatusError as exc:
        if 400 <= exc.status_code < 500 and exc.status_code != 429:
            raise RuntimeError(f"{exc.status_code} permanent error for {url}") from exc
        raise RuntimeError(f"fetch failed for {url}: {exc}") from exc




def fetch_ptr_pdf(doc_id: str, year: int, cache_dir: Path | None = None) -> bytes:
    """One PTR PDF by DocID (idempotent; cached per DocID)."""
    fp = _cache_dir(cache_dir) / f"politician_trades_ptr_{year}_{doc_id}.pdf"
    if fp.exists():
        return fp.read_bytes()
    blob = _get_polite(_PTR_PDF_URL.format(year=year, doc_id=doc_id))
    fp.write_bytes(blob)
    return blob


def ptr_pdf_url(doc_id: str, year: int) -> str:
    """Clerk permalink for one PTR (the panel's primary-source直链)."""
    return _PTR_PDF_URL.format(year=year, doc_id=doc_id)
