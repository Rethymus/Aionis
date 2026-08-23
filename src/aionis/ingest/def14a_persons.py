"""Person-level DEF 14A parsing — directors / executive officers (bounded).

v1 (:mod:`aionis.ingest.form_def14a`) shipped the filing STREAM and honestly
deferred person-level parsing — names live inside each proxy's primary HTML
and resolving one document per filing would have cost ~2,800 extra requests
for the full 1,387-filing window. This module is the bounded person-level
lane: it walks only the NEWEST ~150 filings of the panel, resolves each
filing's primary document (filing ``index.json`` -> scored primary-doc pick,
the :mod:`aionis.ingest.form8k` pattern), and extracts directors / executive
officers with CONSERVATIVE, tiered confidence — never a heuristic name guess.

EXTRACTION CONTRACT (confidence tiers, 宁可 null 不猜测):

  * ``section_age_rows`` (HIGH) — the classic proxy summary row
    ``Name (Age) Title Since`` in any of its spellings (``Name (58)``,
    ``Name, 58,``, ``Name, age 58``, or the cell-separated ``Name 58 Title``):
    a 2-4 token capitalized personal name (optional single-letter middle
    initials / Jr/Sr/II/III/IV suffix), a standalone human age bounded
    30-99, and a role word WITNESSED on the same row. The age anchor makes
    false positives vanishingly rare — no company/section/boilerplate phrase
    carries a plausible human age directly after a name-shaped span.
  * ``section_name_roles`` (MEDIUM) — inside a located directors/executives
    section, ``First M. Last`` (middle token = single capital letter, the
    conservative pattern) + a role word on the same row.
  * anything else -> ``persons=[]`` and ``parsed=false``. A document the
    parser cannot read yields an honest NULL, never a fabricated name or a
    guessed role; coverage is reported as-counted over the processed prefix.

Roles come from a fixed canonical vocabulary (ceo / cfo / coo / cto /
chairman / president / vice_president / treasurer / secretary / director /
officer) matched on the person's own row; every shipped person carries >= 1
witnessed role word. Same-name rows within one filing merge (roles union).
Name-token stopwords (Item/Section/Table/months/committees/...) reject
title-case phrases that merely look name-shaped.

REQUEST BUDGET: per filing at most 2 GETs (index.json + primary doc),
idempotent per-accession caches (a rerun makes zero HTTP), explicit 2.1s
sleeps on top of the process-wide >= 2.0s host spacing, and a HARD wall-clock
budget — the loop stops mid-panel and coverage numbers count only what was
processed (never extrapolated).

7-gate: SEC EDGAR public domain (17 U.S.C. §105) — G1✓; PIT via
``filed_date`` — G2✓; immutable (amendments are NEW accessions) — G3✓;
pure-function parser + idempotent caches — G4✓; exploratory display-only —
G5✓; conservative tiers + honest nulls — G6✓; politeness — G7✓. See
``docs/data-intake-edgar-def14a.md``.
"""
from __future__ import annotations

import json
import re
import time
from html import unescape as _unescape
from pathlib import Path

import structlog

from aionis.ingest.form4_efts import _UA, _cache_dir, _get_json, _policy_get

log = structlog.get_logger()

_ARCHIVE_BASE = "https://www.sec.gov/Archives/edgar/data"

# Exhibit-looking document names — the primary proxy doc must not be one of
# these (form8k's guard: the "14a" inside an exhibit name must not fool the
# primary-doc scorer, so the exhibit check runs first).
_EXHIBIT_RE = re.compile(r"(?:ex|dex)\d", re.I)

# Section headings that legally carry the director/officer roster. Each match
# opens a bounded text window. Patterns use ``\\s+`` because fragmented inline-
# XBRL docs break a heading across lines ("Director\nNominee\nAge"); singular/
# plural both accepted. TOC matches are self-cleaning: a TOC window carries no
# Name+age/role rows, so it yields nothing and never lies.
_SECTION_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"directors\s+and\s+executive\s+officers", re.I),
    re.compile(r"information\s+(?:about|on|regarding)\s+(?:our|the)\s+directors", re.I),
    re.compile(r"director\s+nominees?\s+(?:information|as\s+of)", re.I),
    re.compile(r"nominees?\s+for\s+(?:election\s+as\s+)?directors?", re.I),
    re.compile(r"election\s+of\s+directors?", re.I),
    re.compile(r"executive\s+officers?\s+of\s+(?:the|our)\s+company", re.I),
    re.compile(r"our\s+executive\s+officers", re.I),
    re.compile(r"composition\s+of\s+the\s+board", re.I),
)
_WINDOW_CHARS = 18_000
_MAX_WINDOWS = 14
_MAX_OCCURRENCES_PER_PATTERN = 8

# Canonical role vocabulary, display order. `_roles_in_line` collects every
# pattern that matches; a specific chief-role (ceo/cfo/coo/cto) subsumes the
# generic "officer" so a row never double-counts as both.
_ROLE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ceo", re.compile(r"chief executive officer|\bceo\b", re.I)),
    ("cfo", re.compile(r"chief financial officer|\bcfo\b", re.I)),
    ("coo", re.compile(r"chief operating officer|\bcoo\b", re.I)),
    ("cto", re.compile(r"chief technology officer|\bcto\b", re.I)),
    ("chairman", re.compile(
        r"\bchairman\b|\bchairwoman\b|\bchairperson\b|\bchair of the board\b", re.I,
    )),
    # "Vice President" must not register as a plain President (fixed-width
    # lookbehind excludes the "vice " prefix; the vice_president arm catches it).
    ("president", re.compile(r"(?<!vice )\bpresident\b", re.I)),
    ("vice_president", re.compile(r"vice president|\bevp\b|\bsvp\b|\bvp\b", re.I)),
    ("treasurer", re.compile(r"\btreasurer\b", re.I)),
    ("secretary", re.compile(r"\bsecretary\b", re.I)),
    ("director", re.compile(r"\bdirectors?\b", re.I)),
    ("officer", re.compile(r"\bofficers?\b|\bcontroller\b", re.I)),
)
ROLE_ORDER: tuple[str, ...] = tuple(k for k, _ in _ROLE_PATTERNS)
_CHIEF_ROLES = frozenset({"ceo", "cfo", "coo", "cto"})
_DIRECTOR_ROLES = frozenset({"director", "chairman"})

# "Advisor to the Chief Executive Officer" is NOT a CEO — a chief-role match
# whose immediate prefix reads advisor/consultant/assistant/deputy/reports-to
# is rejected (the person keeps whatever other roles the row witnesses).
_GUARD_BEFORE = re.compile(
    r"(advisor|consultant|assistant|deputy|reports?\s+to)\s+(?:to\s+|the\s+)?$", re.I,
)

# Title-case tokens that are NOT personal names in proxy context. Every token
# of a candidate name must clear this list (defense on top of the age/role
# anchors — TOC streams like "Executive Officers 33" and "Risk Factors 8" die
# here, as do committee/section/month spans).
_NAME_STOPWORDS = frozenset("""
accounting amendment amendments annual april august audit authority beneficial
benefits biographical board box california certain chair chairman committee
commission company companies compensation contents controller corporate
corp corporation date december delinquencies delaware director directors
disability division election employees executives factors february fiduciary
filing finance fiscal floor form friday governance guidelines held hereby
herein household http https impeachment independence indemnification
information insurance january july june leadership liabilities litigation llc
long-term march may meeting materials members membership monday name nasdaq
nevada november notice nyse october officers other ownership parties page
part plan proposal proposals proxy questions record regarding regulation
report resources relationships rules saturday schedule section securities
september services shareholder shareholders since software statement stock
stockholders strategy structure summary sunday suite table technology
thursday title transactions tuesday treasurer undefined usa voting wednesday
web www year
""".split())

# Title words that may GLUE onto the front of a matched name span ("President
# Heather Atkinson (45)") — stripped while >= 2 name tokens remain. Distinct
# from stopwords: a leading title token is layout noise, not a bad span.
_TITLE_PREFIX_WORDS = frozenset("""
advisor age assistant chief chairman chair corporate deputy director executive
financial founder global head independent medical nominee officer operating
position positions president secretary senior trustee treasurer vice
""".split())

# A candidate personal name: First [I.] [I.] Last [Last2] [suffix] — 2-4
# capitalized word tokens, up to two single-letter middle initials, optional
# Jr/Sr/II/III/IV suffix. Greedy trailing tokens make the leftmost match take
# the longest span (a mid-name restart cannot truncate "Mary Jane Anne Smith").
_NAME_TOKEN = r"[A-Z][a-z]{1,24}"
_NAME_CORE = (
    rf"{_NAME_TOKEN}(?:\s+[A-Z]\.){{0,2}}(?:\s+{_NAME_TOKEN}){{1,3}}"
    r"(?:\s+(?:Jr|Sr|II|III|IV|V)\.?)?"
)

# HIGH tier — name anchored by a standalone human age (bounded 30-99 in code).
_AGE_PAREN_RE = re.compile(rf"\b({_NAME_CORE})\s*[(,]\s*(\d{{2}})\s*[),]")
_AGE_WORD_RE = re.compile(rf"\b({_NAME_CORE})\s*,?\s+age\s+(\d{{2}})\b", re.I)
_AGE_CELL_RE = re.compile(rf"\b({_NAME_CORE})\s+(\d{{2}})\b")

# MEDIUM tier — single-letter middle token required (inherently conservative:
# "Securities and Exchange Commission" style spans never match), role word on
# the same row.
_NAME_MI_RE = re.compile(
    rf"\b({_NAME_TOKEN}\s+[A-Z]\.(?:\s+{_NAME_TOKEN}){{1,2}}"
    r"(?:\s+(?:Jr|Sr|II|III|IV)\.?)?)\b"
)

_MIN_AGE, _MAX_AGE = 30, 99
_MAX_PERSONS_PER_FILING = 80  # noise guard: beyond this the parse is dropped

_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.I | re.S)
_BLOCK_RE = re.compile(r"</?(?:tr|p|div|br|h[1-6]|li|table|section|ul|ol)\b[^>]*>", re.I)
_CELL_RE = re.compile(r"</t[dh]>", re.I)
_TAG_RE = re.compile(r"<[^>]+>")


def _html_to_text(html: str) -> str:
    """Flatten proxy HTML to line-structured text (pure function).

    Block/table tags break lines; cell tags join with a space so a table row
    survives as ONE line (``John A. Smith 58 Director since 2019``) — the
    shape both tiers parse. Entities decoded; blank lines dropped."""
    if not html:
        return ""
    s = _SCRIPT_STYLE_RE.sub(" ", html)
    s = _BLOCK_RE.sub("\n", s)
    s = _CELL_RE.sub(" ", s)
    s = _TAG_RE.sub(" ", s)
    s = _unescape(s)
    lines = (re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in s.split("\n"))
    return "\n".join(ln for ln in lines if ln)


def _name_ok(name: str) -> bool:
    """Every word token of the candidate must clear the stopword list."""
    tokens = [t for t in re.split(r"[\s.,]+", name) if t]
    if not tokens:
        return False
    return all(t.lower() not in _NAME_STOPWORDS for t in tokens)


def _clean_name(name: str) -> str:
    """Strip LEADING layout/title tokens ("Chief Financial Officer Heather
    Atkinson" -> "Heather Atkinson"; "Directors Steve Cominsky" -> "Steve
    Cominsky") while >= 2 name tokens remain. A stopword/token that ends up
    MID-name still rejects the span in :func:`_name_ok` — only leading glue
    is forgiven. Suffix (Jr./III) tokens never stripped."""
    tokens = name.split()
    strip = _TITLE_PREFIX_WORDS | _NAME_STOPWORDS
    while len(tokens) > 2 and tokens[0].lower() in strip:
        tokens = tokens[1:]
    return " ".join(tokens)


def _roles_in_line(line: str) -> list[str]:
    """Canonical roles witnessed on the row, display order (may be [])."""
    roles: list[str] = []
    for key, rx in _ROLE_PATTERNS:
        if key in _CHIEF_ROLES:
            # A guarded chief-role needs at least one UNGUARDED occurrence.
            if any(
                not _GUARD_BEFORE.search(line[: m.start()]) for m in rx.finditer(line)
            ):
                roles.append(key)
        elif rx.search(line):
            roles.append(key)
    if any(r in roles for r in _CHIEF_ROLES):
        roles = [r for r in roles if r != "officer"]
    return roles


def _norm_name(name: str) -> str:
    """Merge key: lowercase, punctuation stripped, whitespace collapsed
    ("John A. Smith" == "John A Smith")."""
    return re.sub(r"\s+", " ", re.sub(r"[.,]", "", name).strip()).lower()


def _merge_roles(base: list[str], extra: list[str]) -> list[str]:
    return [r for r in ROLE_ORDER if r in set(base) | set(extra)]


def _extract_from_line(window: str) -> list[tuple[str, str, list[str]]]:
    """(name, tier, roles) triples witnessed on the window's intact LINES.

    HIGH tier (age-anchored rows) first; the middle-initial MEDIUM tier only
    fires on windows where no age anchor matched anywhere. Every person must
    carry >= 1 witnessed role — a name-shaped span without a role word is NOT
    extracted (never guessed)."""
    out: list[tuple[str, str, list[str]]] = []
    high = False
    for line in window.split("\n"):
        roles = _roles_in_line(line)
        if not roles:
            continue
        for rx in (_AGE_PAREN_RE, _AGE_WORD_RE, _AGE_CELL_RE):
            for m in rx.finditer(line):
                if not (_MIN_AGE <= int(m.group(2)) <= _MAX_AGE):
                    continue
                name = _clean_name(m.group(1).strip())
                if _name_ok(name):
                    out.append((name, "section_age_rows", roles))
                    high = True
    if not high:
        for line in window.split("\n"):
            roles = _roles_in_line(line)
            if not roles:
                continue
            for m in _NAME_MI_RE.finditer(line):
                name = _clean_name(m.group(1).strip())
                if _name_ok(name):
                    out.append((name, "section_name_roles", roles))
    return out


def _section_windows(text: str) -> list[str]:
    """Bounded text windows opened at each directors/executives heading."""
    windows: list[str] = []
    for rx in _SECTION_RES:
        n = 0
        for m in rx.finditer(text):
            if n >= _MAX_OCCURRENCES_PER_PATTERN or len(windows) >= _MAX_WINDOWS:
                break
            windows.append(text[m.start(): m.start() + _WINDOW_CHARS])
            n += 1
    return windows


def _extract_from_stream(window: str) -> list[tuple[str, str, list[str]]]:
    """(name, tier, roles) triples from the line-JOINED window stream.

    Many inline-XBRL proxies fragment every word onto its own line, so a
    table row never survives as one line. This pass joins the window into one
    space-separated stream and lets the age anchors DELIMIT the rows: each
    age-anchored candidate's role context is the span from its match end to
    the next candidate's start (capped) — the position where that person's
    Title/Since cells live in the original table. TOC streams survive the
    anchors only as stopworded spans ("Executive Officers 33" dies on the
    stopwords + the 30-99 age bound never sees "33"... when it does, the
    stopword filter is the guard)."""
    stream = re.sub(r"\s+", " ", window)
    cands: list[tuple[int, int, str]] = []
    for rx in (_AGE_PAREN_RE, _AGE_WORD_RE, _AGE_CELL_RE):
        for m in rx.finditer(stream):
            if not (_MIN_AGE <= int(m.group(2)) <= _MAX_AGE):
                continue
            name = _clean_name(m.group(1).strip())
            if _name_ok(name):
                # The cleaned name is a SUFFIX of the matched span — the row
                # delimiter is the cleaned name's start (an absorbed leading
                # "Director"/"Executive Officer" token must not cut the
                # PREVIOUS person's role context short).
                start = m.end(1) - len(name)
                cands.append((start, m.end(), name))
    cands.sort()
    out: list[tuple[str, str, list[str]]] = []
    for i, (_start, end, name) in enumerate(cands):
        nxt = cands[i + 1][0] if i + 1 < len(cands) else end + 200
        ctx = stream[end: min(nxt, end + 200)]
        # The last roster row's context must not run into bios — cut at the
        # first sentence end (roster cells carry no sentence periods).
        sent = re.search(r"\.\s", ctx)
        if sent:
            ctx = ctx[: sent.start()]
        roles = _roles_in_line(ctx)
        if roles:
            out.append((name, "section_age_rows", roles))
    return out


def parse_def14a_persons(html: str) -> dict:
    """Parse directors/executive officers out of one DEF 14A primary document.

    Returns ``{"persons": [{"name", "roles"}...], "parsed": bool, "method":
    "section_age_rows" | "section_name_roles" | ""}``. ``parsed`` is True iff
    at least one person survived the conservative tiers; an unreadable
    document returns the honest empty result — a null, never a guess. Pure
    function (deterministic on the doc bytes)."""
    empty = {"persons": [], "parsed": False, "method": ""}
    text = _html_to_text(html)
    if not text:
        return empty
    merged: dict[str, dict] = {}
    tiers: set[str] = set()
    for window in _section_windows(text):
        for name, tier, roles in _extract_from_line(window):
            key = _norm_name(name)
            if key in merged:
                merged[key]["roles"] = _merge_roles(merged[key]["roles"], roles)
            else:
                merged[key] = {"name": name, "roles": list(roles)}
            tiers.add(tier)
        # Fragmented-layout pass: same Name+age rows, reconstructed from the
        # line-joined stream (anchors delimit the rows).
        for name, tier, roles in _extract_from_stream(window):
            key = _norm_name(name)
            if key in merged:
                merged[key]["roles"] = _merge_roles(merged[key]["roles"], roles)
            else:
                merged[key] = {"name": name, "roles": list(roles)}
            tiers.add(tier)
    if len(merged) > _MAX_PERSONS_PER_FILING:
        # Pathological flatten (whole doc one line, everything matches): the
        # parse is noise, not signal — drop it honestly.
        log.info("def14a_persons_noise_guard", n=len(merged))
        return empty
    persons = list(merged.values())
    method = (
        "section_age_rows" if "section_age_rows" in tiers
        else "section_name_roles" if "section_name_roles" in tiers
        else ""
    )
    return {"persons": persons, "parsed": bool(persons), "method": method}


# --- primary-document resolution (form8k pattern, DEF 14A conventions) ------


def _pick_def14a_doc(index_json: dict, accession: str) -> str | None:
    """Primary proxy document filename from a filing ``index.json``.

    Scored, never "shortest wins": 0 = proxy conventions (a ``def14a`` /
    ``proxy`` substring, or EDGAR issuer-date machine naming
    ``abc-20260815.htm``), 1 = other non-exhibit ``.htm(l)``, 2 = ``R\\d+``
    XBRL rendering, 3 = exhibit (``ex99.htm``). Lowest score wins, shortest
    name breaks exact ties. Falls back to the accession ``.txt``."""
    items: list[dict] = []
    directory = index_json.get("directory") if isinstance(index_json, dict) else None
    if isinstance(directory, dict):
        raw = directory.get("item", [])
        items = raw if isinstance(raw, list) else [raw]
    elif isinstance(index_json, dict) and isinstance(index_json.get("items"), list):
        items = index_json["items"]

    names = [str(it.get("name", "")) for it in items if isinstance(it, dict)]

    def _score(n: str) -> int:
        low = n.lower()
        if _EXHIBIT_RE.search(low):
            return 3
        if re.match(r"r\d", low):
            return 2
        if "def14a" in low or "proxy" in low or re.match(r"^[a-z][a-z0-9]*-\d{8}\.html?$", low):
            return 0
        return 1

    htms = [
        n for n in names
        if n.lower().endswith((".htm", ".html")) and "index" not in n.lower()
    ]
    if htms:
        return min(htms, key=lambda n: (_score(n), len(n)))
    no_dash = accession.replace("-", "")
    return next(
        (n for n in names if no_dash in n and n.lower().endswith(".txt")), None,
    )


def _doc_url(issuer_cik: int, accession: str, filename: str) -> str:
    return f"{_ARCHIVE_BASE}/{int(issuer_cik)}/{accession.replace('-', '')}/{filename}"


def fetch_def14a_doc(
    issuer_cik: int, accession: str, cache_dir: Path | None = None,
    request_counter: list[int] | None = None,
) -> tuple[str, str | None]:
    """Primary proxy document text for ``(issuer_cik, accession)``.

    Idempotent (index + doc cached separately — a rerun makes zero HTTP).
    At most 2 GETs per filing, each preceded by an explicit 2.1s sleep on top
    of the process-wide >= 2.0s host spacing. Returns ``(text, doc_filename)``
    — ``("", None)`` when the index lists nothing usable (logged, not raised).
    ``request_counter`` (if given) records one element per real HTTP GET."""
    cik10 = f"{int(issuer_cik):010d}"
    no_dash = accession.replace("-", "")
    doc_fp = _cache_dir(cache_dir) / f"def14ap_doc_{cik10}_{no_dash}.bin"
    name_fp = doc_fp.with_suffix(".docname")
    if doc_fp.exists():
        name = name_fp.read_text() if name_fp.exists() else ""
        return doc_fp.read_text(encoding="utf-8", errors="replace"), name or None

    idx_fp = _cache_dir(cache_dir) / f"def14ap_index_{cik10}_{no_dash}.json"
    if idx_fp.exists():
        idx = json.loads(idx_fp.read_text())
    else:
        time.sleep(2.1)  # explicit politeness ON TOP of the >=2.0s host spacing
        if request_counter is not None:
            request_counter.append(1)
        idx = _get_json(f"{_ARCHIVE_BASE}/{cik10}/{no_dash}/index.json")
        idx_fp.write_text(json.dumps(idx))

    doc = _pick_def14a_doc(idx, accession)
    if not doc:
        log.warning("def14a_persons_no_doc_in_index", issuer_cik=issuer_cik, accession=accession)
        return "", None

    time.sleep(2.1)
    if request_counter is not None:
        request_counter.append(1)
    text = _policy_get(
        _doc_url(issuer_cik, accession, doc),
        total_attempts=4,
        backoff_base=4,
        backoff_mode="linear",
        headers={"User-Agent": _UA},
        timeout=60,
    ).text
    doc_fp.write_text(text, encoding="utf-8", errors="replace")
    name_fp.write_text(doc)
    return text, doc


def fetch_def14a_persons(
    filings: list[dict], *, limit: int = 150, budget_seconds: float = 2700.0,
    cache_dir: Path | None = None,
) -> dict:
    """Bounded person-level parse over the NEWEST ``limit`` DEF 14A filings.

    ``filings`` are rows of the panel aggregate (``issuer_cik`` / ``accession``
    / ``company`` / ``ticker`` / ``filed_date``), newest-first. The loop stops
    the moment the hard wall-clock budget (default 45 min) expires — coverage
    downstream counts only the processed prefix, never an extrapolation.
    Per-filing failures are recorded honestly (``error`` key), never guessed
    around. Idempotent: cached accessions are re-parsed from disk with zero
    HTTP. Returns ``{"n_target", "n_processed", "budget_seconds", "budget_hit",
    "n_requests", "results": {accession: filing-record}}`` where each filing
    record carries ``persons`` / ``parsed`` / ``method`` (+ ``doc_url`` and
    ``error`` when applicable)."""
    t0 = time.monotonic()
    requests: list[int] = []
    results: dict[str, dict] = {}
    budget_hit = False
    rows = list(filings)[:limit]
    for row in rows:
        if time.monotonic() - t0 > budget_seconds:
            budget_hit = True
            log.info("def14a_persons_budget_hit", processed=len(results), target=len(rows))
            break
        cik = str(row.get("issuer_cik") or "").strip()
        accession = str(row.get("accession") or "").strip()
        rec = {
            "company": str(row.get("company", "")),
            "ticker": str(row.get("ticker", "")),
            "issuer_cik": cik,
            "filed_date": str(row.get("filed_date", "")),
            "persons": [],
            "parsed": False,
            "method": "",
        }
        if cik and accession:
            try:
                text, doc = fetch_def14a_doc(int(cik), accession, cache_dir, requests)
                if text:
                    rec.update(parse_def14a_persons(text))
                    if doc:
                        rec["doc_url"] = _doc_url(int(cik), accession, doc)
                else:
                    rec["error"] = "no_primary_doc_in_index"
            except Exception as exc:  # bounded per-filing failure, honest record
                log.warning(
                    "def14a_persons_fetch_failed",
                    accession=accession, error=str(exc)[:200],
                )
                rec["error"] = "doc_fetch_failed"
        else:
            rec["error"] = "missing_cik_or_accession"
        results[accession or f"{rec['company']}-{rec['filed_date']}"] = rec
    return {
        "n_target": len(rows),
        "n_processed": len(results),
        "budget_seconds": budget_seconds,
        "budget_hit": budget_hit,
        "n_requests": len(requests),
        "results": results,
    }
