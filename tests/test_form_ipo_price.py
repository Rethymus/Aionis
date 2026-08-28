"""Bounded 424B4 cover-price parsing — hermetic (no network).

Pins :mod:`aionis.ingest.form_ipo_price` (the stakes_pct-graded second stage
of the /ipo panel): primary-document selection prefers the statutory
``424b4`` file over any other index listing; the cover price is graded
``exact`` / ``low`` / ``none`` — only exact-tier values are ever returned,
draft/range language stays an honest null (never guessed), hypothetical
scenario sentences are skipped entirely, and absurd amounts are rejected.
The per-accession cache is idempotent: a cached ``ok`` row makes ZERO
network calls; failed rows are retried on the next run.

Fixtures are HAND-WRITTEN mimicking live EDGAR filing shapes (cover lines,
index.json directory listings) — no real data, no network, per the project's
mock-in-tests-only policy. Mirrors tests/test_form_ipo.py's offline pattern.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
import requests

from aionis.config import settings
from aionis.ingest import form_ipo_price as fip
from aionis.ingest import universe
from aionis.ingest.http_policy import HttpRequestPolicy

# The walker script (scripts/form_ipo_price_parse.py) is imported exactly the
# way the cron/CLI runs it — scripts/ on sys.path (the
# tests/test_export_terminal_data.py precedent) — so the walker-level pruning
# tests below exercise the REAL main() entry point, hermetically.
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import form_ipo_price_parse as walker  # noqa: E402

ACC = "0001493152-26-039508"
CIK = 1786471


class _Resp:
    def __init__(self, payload=None, text=""):
        self._p = payload
        self.text = text
        self.status_code = 200
        self.headers = {}

    def json(self): return self._p


def _install_policy(monkeypatch):
    now = [0.0]

    def sleep(seconds):
        now[0] += seconds

    monkeypatch.setattr(
        universe,
        "_HTTP_POLICY",
        HttpRequestPolicy(
            clock=lambda: now[0],
            sleeper=sleep,
            retry_exceptions=(requests.RequestException,),
        ),
    )


def _no_network(monkeypatch, url_map):
    """Serve a URL map through the shared policy with fake time;
    any URL outside the map raises (asserts no unexpected request)."""
    calls: list[str] = []

    def fake(url, headers=None, timeout=None):
        calls.append(url)
        if url in url_map:
            return url_map[url]
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(requests, "get", fake)
    _install_policy(monkeypatch)
    return calls


# --- primary-document selection ------------------------------------------------


def test_pick_primary_doc_prefers_424b4_and_skips_exhibits():
    names = [
        "d123456dex991.htm",          # exhibit — never the prospectus
        "d123456d424b4.htm",          # statutory final prospectus — wins
        "xyz-index.html",             # EDGAR chrome — excluded outright
        "image002.jpg",
    ]
    assert fip.pick_primary_doc(names) == "d123456d424b4.htm"


def test_pick_primary_doc_falls_back_to_any_htm():
    # Some filers name the prospectus freely (no '424b4' in the filename).
    assert fip.pick_primary_doc(["tf1234-1 Prospectus.htm"]) == (
        "tf1234-1 Prospectus.htm"
    )


def test_pick_primary_doc_exhibit_only_is_none():
    assert fip.pick_primary_doc(["ex01.htm", "whatever-index.htm"]) is None


# --- graded extraction (exact / low / none) -------------------------------------

_COVER_BOXED = """<html><body><table><tr>
<td>Initial public offering price</td><td>Per Share</td><td>Total</td></tr>
<tr><td></td><td>$   11.00</td><td>$ 124,000,000</td></tr>
</table></body></html>"""

_COVER_LABELLED = (
    "Initial public offering price: $7.50 per share.\n"
    "Underwriting discounts and commissions: $0.53 per share."
)

_COVER_PRICE_TO_PUBLIC = (
    "Price to public(1)                $16.00 per share\n"
    "Underwriting proceeds(1)          $14.88 per share"
)

_NARRATIVE = (
    "...we sold shares of common stock to the underwriters at an initial "
    "public offering price of $11.00 per share..."
)


@pytest.mark.parametrize(
    ("text", "want"),
    [
        (_COVER_BOXED, 11.00),
        (_COVER_LABELLED, 7.50),
        (_COVER_PRICE_TO_PUBLIC, 16.00),
        (_NARRATIVE, 11.00),
    ],
)
def test_exact_tier_on_realistic_cover_shapes(text, want):
    price, conf = fip.extract_offer_price(text)
    assert conf == fip.CONF_EXACT and price == want


_DRAFT_RANGE = (
    "We anticipate that the proposed initial public offering price will be "
    "between $14.00 and $16.00 per share."
)
_DRAFT_RANGE_2 = (
    "the estimated initial public offering price range for this offering "
    "is $10.00 to $12.00 per share"
)
_RANGE_TABLE = (
    "Initial public offering price between $9.00 and $11.00 per share"
)


@pytest.mark.parametrize("text", [_DRAFT_RANGE, _DRAFT_RANGE_2, _RANGE_TABLE])
def test_low_tier_never_returns_a_value(text):
    """Draft/range language near the anchor = low confidence: counted, but the
    value NEVER materializes (honest blank, not a guess)."""
    price, conf = fip.extract_offer_price(text)
    assert conf == fip.CONF_LOW and price is None


_HYPOTHETICAL_ONLY = (
    "If the initial public offering price had been $1.00 higher per share, "
    "we would have received approximately $11.3 million of additional net "
    "proceeds from this offering."
)


def test_hypothetical_scenario_is_not_evidence():
    price, conf = fip.extract_offer_price(_HYPOTHETICAL_ONLY)
    assert conf == fip.CONF_NONE and price is None


def test_no_anchor_at_all_is_none():
    assert fip.extract_offer_price("<html><body>prospectus</body></html>") == (
        None, fip.CONF_NONE,
    )


def test_cover_line_wins_before_later_narrative_par_value_trap():
    """Document-order anchoring: the printed cover number beats later sentences
    mentioning par-value artefacts."""
    text = _COVER_BOXED + "<p>common stock, par value $0.0001 per share</p>"
    price, conf = fip.extract_offer_price(text)
    assert conf == fip.CONF_EXACT and price == 11.00


def test_absurd_amounts_are_rejected():
    junk = "initial public offering price $0.000001 per unit"
    assert fip.extract_offer_price(junk)[1] != fip.CONF_EXACT


# --- export-layer merge gate -----------------------------------------------------


def test_merge_offer_prices_gates_everything_but_exact_in_range():
    rows = [{
        "doc_url": f"https://www.sec.gov/Archives/edgar/data/{CIK}/"
                   f"000149315226039508/{ACC}-index.htm",
    }]
    cache = {
        ACC: {"offer_price": 11.0, "confidence": "exact", "ok": True},
        "0001493152-26-000009": {"offer_price": None, "confidence": "low", "ok": True},
        "0001493152-26-000010": {"offer_price": 99999999.0, "confidence": "exact", "ok": True},
    }
    merged = fip.merge_offer_prices(
        [dict(r) for r in rows] + [{"doc_url": ""}, {"doc_url": ""}],
        cache,
    )
    # NOTE: the two empty-url rows must stay null, not crash.
    assert merged[0]["offer_price"] == 11.0
    assert merged[1]["offer_price"] is None
    # Out-of-envelope even at exact tier → nulled at the export gate.
    empty_cache = {**cache, "0001493152-26-000011":
                   {"offer_price": 5.0, "confidence": "exact"}}
    merged2 = fip.merge_offer_prices(
        [{}, {}, {}, {}],  # blank urls → all null regardless of cache content
        empty_cache,
    )
    assert all(r["offer_price"] is None for r in merged2)
    # And a fresh valid row over the out-of-range entry proves the gate:
    row3 = [{"doc_url": "https://www.sec.gov/Archives/edgar/data/1/2/"
                        "0001493152-26-000010-index.htm"}]
    assert fip.merge_offer_prices(row3, cache)[0]["offer_price"] is None


# --- bounded fetch + idempotency (accession-keyed cache) --------------------------


def _index_payload(*docs):
    return {"directory": {"item": [{"name": d} for d in docs]}}


def test_parse_flow_two_requests_then_cached_zero(monkeypatch, tmp_path):
    doc_url = (
        f"https://www.sec.gov/Archives/edgar/data/{CIK}/000149315226039508/d424.htm"
    )
    idx_url = (
        f"https://www.sec.gov/Archives/edgar/data/{CIK}/000149315226039508/index.json"
    )
    calls = _no_network(monkeypatch, {
        idx_url: _Resp(_index_payload("d424.htm")),
        doc_url: _Resp(text=_COVER_BOXED),
    })

    res = fip.parse_filing_offer_price(CIK, ACC, cache_dir=tmp_path)
    assert res["ok"] is True and res["confidence"] == "exact"
    assert res["offer_price"] == 11.00
    assert len(calls) == 2, "exactly one index.json + one primary document"

    res["form"] = "424B4"
    cache = {ACC: fip.stamp_row(res)}
    meta = {"requests_cumulative": 2}
    fip.save_price_cache(cache, meta=meta, cache_dir=tmp_path)

    # Rerun: the CACHED ok row short-circuits before any network — the runner
    # level guarantees it by skipping cached accessions; the pure parser
    # contract here pins that load sees ok+price with zero further requests.
    loaded = fip.load_price_cache(tmp_path)
    e = loaded[ACC]
    assert e["ok"] and e["confidence"] == "exact" and e["offer_price"] == 11.00
    assert "parsed_at" in e
    assert fip.load_cache_meta(tmp_path) == {"requests_cumulative": 2}

    def explode(url, headers=None, timeout=None):  # any request fails the rerun
        raise AssertionError(f"idempotent rerun made a request: {url}")

    monkeypatch.setattr(requests, "get", explode)
    # The runner-visible guarantee: a cached accession list needs no fetches.
    todo = [acc for acc, v in loaded.items() if not v.get("ok")]
    assert todo == []  # nothing failed ⇒ rerun walk is a ZERO-request no-op


def test_failed_row_is_retried_next_run(monkeypatch, tmp_path):
    state = {"up": False}

    def flaky(url, headers=None, timeout=None):
        if not state["up"]:
            raise RuntimeError("EDGAR down")
        if url.endswith("index.json"):
            return _Resp(_index_payload("d424.htm"))
        return _Resp(text=_COVER_BOXED)

    monkeypatch.setattr(requests, "get", flaky)
    _install_policy(monkeypatch)

    first = fip.parse_filing_offer_price(CIK, ACC, cache_dir=tmp_path)
    assert first["ok"] is False and first["confidence"] is None

    state["up"] = True
    second = fip.parse_filing_offer_price(CIK, ACC, cache_dir=tmp_path)
    assert second["ok"] is True and second["offer_price"] == 11.00


def test_cache_survives_corruption(tmp_path):
    (tmp_path / fip._CACHE_NAME).write_text("{not json")
    assert fip.load_price_cache(tmp_path) == {}
    assert fip.load_cache_meta(tmp_path) == {}


def test_flat_legacy_rows_still_load(tmp_path):
    payload = {
        ACC: {"offer_price": 3.0, "confidence": "exact", "ok": True},
    }
    (tmp_path / fip._CACHE_NAME).write_text(json.dumps(payload))
    assert fip.load_price_cache(tmp_path)[ACC]["offer_price"] == 3.0


# --- window pruning: cache hygiene for the bounded walk (TASK-DISP-W) ------------
#
# The target window only advances at its newest edge, so entries that slid out
# can never re-enter; keeping them lets merge_offer_prices serve stale prices
# to every visible row while the export layer counts only in-window exacts —
# the drift that broke conf["exact"] == offer_price_parsed. Pruning happens on
# EVERY walker persist; these tests pin the pure function and the walker.


def test_prune_drops_out_of_window_exact_none_fail_keeps_window_incl_fail():
    """Slid-out exact/none/FAIL entries are dropped whole; every in-window
    entry survives — including a FAIL, which is still window state (it retries
    on the next walk). The input dict is not mutated."""
    win_exact = {"offer_price": 11.0, "confidence": "exact", "ok": True}
    win_none = {"offer_price": None, "confidence": "none", "ok": True}
    win_fail = {
        "offer_price": None, "confidence": None, "ok": False,
        "error": "RuntimeError: EDGAR down", "issuer_cik": CIK,
    }
    out_exact = {"offer_price": 9.0, "confidence": "exact", "ok": True}
    out_none = {"offer_price": None, "confidence": "none", "ok": True}
    out_fail = {
        "offer_price": None, "confidence": None, "ok": False,
        "error": "ConnectError: timeout", "issuer_cik": CIK,
    }
    cache = {
        "0001493152-26-000001": win_exact,
        "0001493152-26-000002": win_none,
        "0001493152-26-000003": win_fail,
        "0001493152-26-000004": out_exact,
        "0001493152-26-000005": out_none,
        "0001493152-26-000006": out_fail,
    }
    window = {"0001493152-26-000001", "0001493152-26-000002", "0001493152-26-000003"}

    pruned = fip.prune_price_cache_to_target(cache, window)

    assert set(pruned) == window
    assert pruned["0001493152-26-000001"] == win_exact
    assert pruned["0001493152-26-000002"] == win_none
    assert pruned["0001493152-26-000003"] == win_fail  # FAIL kept whole
    # Pure function: the caller's cache (the walker's live dict) is untouched.
    assert set(cache) == set(pruned) | {
        "0001493152-26-000004", "0001493152-26-000005", "0001493152-26-000006",
    }
    assert cache["0001493152-26-000004"] == out_exact


def test_prune_empty_target_yields_empty_cache():
    cache = {ACC: {"offer_price": 11.0, "confidence": "exact", "ok": True}}
    assert fip.prune_price_cache_to_target(cache, set()) == {}
    assert cache == {ACC: {"offer_price": 11.0, "confidence": "exact", "ok": True}}


def test_prune_is_idempotent():
    """Prune(prune(cache)) == prune(cache) — the window only shrinks toward a
    fixed point, so repeated persists cannot lose further entries."""
    keep = {"offer_price": 11.0, "confidence": "exact", "ok": True}
    cache = {
        "0001493152-26-000001": keep,
        "0001493152-26-000004": {"offer_price": 9.0, "confidence": "exact", "ok": True},
    }
    window = {"0001493152-26-000001"}
    once = fip.prune_price_cache_to_target(cache, window)
    twice = fip.prune_price_cache_to_target(once, window)
    assert once == {"0001493152-26-000001": keep}
    assert twice == once


def _seed_price_cache(cache_dir: Path, rows: dict, meta: dict) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    fip.save_price_cache(rows, meta=meta, cache_dir=cache_dir)


def _write_target_parquet(path: Path, priced_newest_first: list[str]) -> None:
    """A minimal aggregate parquet: only priced rows, ordered newest-first
    (the walker's stable sort must reproduce this order)."""
    rows = [
        {
            "accession": acc,
            "issuer_cik": CIK,
            "status": "priced",
            "filed_date": f"2026-08-{20 - i:02d}",
        }
        for i, acc in enumerate(priced_newest_first)
    ]
    pd.DataFrame(rows).to_parquet(path)


def test_walker_walk_saves_cache_pruned_to_target_window(monkeypatch, tmp_path):
    """A real walker.main() run over a cache holding slid-out entries persists
    ONLY the target window: the out-of-window exact vanishes, the in-window
    FAIL is retried, the in-window ok row is never re-fetched."""
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    _install_policy(monkeypatch)  # walker swaps the global policy; restore after

    new_acc = "0001493152-26-000101"    # entering the window — fetched this walk
    retry_acc = "0001493152-26-000102"  # in-window FAIL — retried this walk
    keep_acc = "0001493152-26-000103"   # in-window ok — must NOT be re-fetched
    old_acc = "0001493152-26-000004"    # slid OUT of the window — must vanish
    meta0 = {"requests_cumulative": 40, "walk_cap_requests": 156}
    _seed_price_cache(tmp_path / "cache", {
        retry_acc: {
            "offer_price": None, "confidence": None, "ok": False,
            "error": "RuntimeError: EDGAR down", "issuer_cik": CIK,
        },
        keep_acc: {
            "offer_price": 11.0, "confidence": "exact", "ok": True,
            "issuer_cik": CIK,
        },
        old_acc: {
            "offer_price": 9.0, "confidence": "exact", "ok": True,
            "issuer_cik": CIK,
        },
    }, meta0)
    parquet = tmp_path / "form_ipo_aggregate.parquet"
    _write_target_parquet(parquet, [new_acc, retry_acc, keep_acc])
    monkeypatch.setattr(walker, "PARQUET", str(parquet))

    fetched: list[str] = []

    def fake_parse(cik, accession):
        fetched.append(accession)
        price = 12.0 if accession == new_acc else 7.5
        return {
            "offer_price": price, "confidence": fip.CONF_EXACT, "ok": True,
            "doc": "d123456d424b4.htm", "error": None,
        }

    monkeypatch.setattr(walker, "parse_filing_offer_price", fake_parse)
    monkeypatch.setattr(sys, "argv", ["form_ipo_price_parse.py"])

    walker.main()

    assert fetched == [new_acc, retry_acc]  # ok row skipped, FAIL row retried
    loaded = fip.load_price_cache()
    assert set(loaded) == {new_acc, retry_acc, keep_acc}  # old_acc pruned
    assert loaded[new_acc]["ok"] and loaded[new_acc]["offer_price"] == 12.0
    assert loaded[retry_acc]["ok"] and loaded[retry_acc]["offer_price"] == 7.5
    assert loaded[keep_acc]["offer_price"] == 11.0  # untouched, never re-fetched
    # Live walk: ledger metadata advances honestly (2 reqs x 2 ok fetches).
    meta = fip.load_cache_meta()
    assert meta["requests_cumulative"] == 44
    assert meta["walk_cap_requests"] == 156
    assert meta["last_run"]


def test_walker_dry_pass_prunes_window_and_leaves_meta_untouched(monkeypatch, tmp_path):
    """--max-requests 0 (verify-only dry pass): zero fetches, slid-out entries
    still pruned (cache hygiene), and the _meta ledger header byte-identical —
    the dry pass never claims a walk happened."""
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    _install_policy(monkeypatch)

    keep_acc = "0001493152-26-000103"   # in-window ok
    retry_acc = "0001493152-26-000102"  # in-window FAIL — window state, kept
    none_acc = "0001493152-26-000104"   # in-window honest null
    old_acc = "0001493152-26-000004"    # slid OUT of the window — must vanish
    meta0 = {"requests_cumulative": 40}
    _seed_price_cache(tmp_path / "cache", {
        keep_acc: {
            "offer_price": 11.0, "confidence": "exact", "ok": True,
            "issuer_cik": CIK,
        },
        retry_acc: {
            "offer_price": None, "confidence": None, "ok": False,
            "error": "RuntimeError: EDGAR down", "issuer_cik": CIK,
        },
        none_acc: {
            "offer_price": None, "confidence": "none", "ok": True,
            "issuer_cik": CIK,
        },
        old_acc: {
            "offer_price": 9.0, "confidence": "exact", "ok": True,
            "issuer_cik": CIK,
        },
    }, meta0)
    parquet = tmp_path / "form_ipo_aggregate.parquet"
    _write_target_parquet(parquet, [keep_acc, retry_acc, none_acc])
    monkeypatch.setattr(walker, "PARQUET", str(parquet))

    def explode(cik, accession):
        raise AssertionError(f"dry pass hit the network: {accession}")

    monkeypatch.setattr(walker, "parse_filing_offer_price", explode)
    monkeypatch.setattr(
        sys, "argv", ["form_ipo_price_parse.py", "--max-requests", "0"],
    )

    walker.main()

    loaded = fip.load_price_cache()
    assert set(loaded) == {keep_acc, retry_acc, none_acc}  # old_acc pruned
    assert loaded[retry_acc]["ok"] is False  # FAIL entry kept whole
    assert fip.load_cache_meta() == meta0  # ledger metadata NOT rewritten
