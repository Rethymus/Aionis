"""Wikipedia universe extender — hermetic (no network; synthetic fixtures only).

The HTML fixtures are HAND-WRITTEN snippets mirroring the structure of the real
Wikipedia "Historical components of the S&P 500" changes table
(Date / Addition / Addition ticker / Removal / Removal ticker / Reason) —
labeled synthetic test data, never real scraped content. Base membership frames
are likewise synthetic. The only network-capable call path
(:func:`fetch_wiki_changes_html`) is monkeypatched everywhere.
"""
from __future__ import annotations

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from aionis.ingest import universe_ext
from aionis.ingest.universe_ext import (
    extend_membership,
    fetch_wiki_changes_html,
    parse_wiki_changes,
    reconcile_full_reconstruction,
    reconcile_overlap,
    reconstruct_monthly_snapshots,
)

# Synthetic page: a decoy table WITHOUT Addition/Removal headers (must be
# ignored — tables are located by header content, not position), then a
# reverse-chronological changes table exercising: a both-in-one row, a
# removal-only row (em-dash NA cells), an ISO date, a footnote-ref date
# ("May 15, 2026[4]"), an addition-only row with an un-normalized share-class
# ticker (BRK/B), and a junk non-date row (dropped, never guessed).
_WIKI_HTML = """
<html><body>
<table class="wikitable">
<tr><th>Ticker</th><th>Company</th></tr>
<tr><td>AAPL</td><td>Apple (decoy table: no Addition/Removal headers)</td></tr>
</table>
<table class="wikitable sortable">
<tr>
  <th>Date</th><th>Addition</th><th>Addition ticker</th>
  <th>Removal</th><th>Removal ticker</th><th>Reason</th>
</tr>
<tr>
  <td>July 10, 2026</td><td>Berkshire New</td><td>BRK/B</td>
  <td>—</td><td>—</td><td>Market cap change</td>
</tr>
<tr>
  <td>May 15, 2026[4]</td><td>Zed Corp</td><td>ZED</td>
  <td>—</td><td>—</td><td>Market cap change</td>
</tr>
<tr>
  <td>2026-04-20</td><td>Iso Systems</td><td>ISO</td>
  <td>—</td><td>—</td><td>Market cap change</td>
</tr>
<tr>
  <td>March 5, 2026</td><td>—</td><td>—</td>
  <td>Baz Corp</td><td>BAZ</td><td>Spun off</td>
</tr>
<tr>
  <td>February 15, 2026</td><td>Foo Inc.</td><td>FOO</td>
  <td>Bar Corp</td><td>BAR</td><td>Index change</td>
</tr>
<tr>
  <td>Not a date</td><td>Junk Co</td><td>JUNK</td>
  <td>—</td><td>—</td><td>Broken row</td>
</tr>
</table>
</body></html>
"""


def _changes(*rows: tuple[str, str, str]) -> pd.DataFrame:
    """Synthetic change log from ``(date, ticker, action)`` tuples."""
    df = pd.DataFrame(rows, columns=["change_date", "ticker", "action"])
    df["change_date"] = pd.to_datetime(df["change_date"]).dt.normalize()
    return df.sort_values(["change_date", "ticker", "action"]).reset_index(drop=True)


def _existing_membership() -> pd.DataFrame:
    """Synthetic pierrebrunelle-style monthly series, CONSISTENT with
    ``_WIKI_HTML``'s change log under the VERIFIED end-of-month convention
    (the M-01 snapshot carries the end-of-M state; base Jan {AAPL, BAR, BAZ}):
    Feb +FOO(02-15) -BAR(02-15); Mar -BAZ(03-05); Apr +ISO(04-20)."""
    months = {
        "2026-01-01": ["AAPL", "BAR", "BAZ"],
        "2026-02-01": ["AAPL", "BAZ", "FOO"],
        "2026-03-01": ["AAPL", "FOO"],
        "2026-04-01": ["AAPL", "FOO", "ISO"],
    }
    rows = [(pd.Timestamp(m), t) for m, ts in months.items() for t in ts]
    return pd.DataFrame(rows, columns=["date", "ticker"])


def _fake_fetch(cache_dir=None, force: bool = False) -> str:
    """Serve the fixture HTML — tests never touch the network."""
    return _WIKI_HTML


def _snap(df: pd.DataFrame, date: str) -> set[str]:
    return set(df.loc[df["date"] == pd.Timestamp(date), "ticker"])


# --- parse ---

def test_parse_long_frame_actions_and_junk_dropped() -> None:
    changes = parse_wiki_changes(_WIKI_HTML)
    assert list(changes.columns) == ["change_date", "ticker", "action"]
    got = {(str(d.date()), t, a) for d, t, a in changes.itertuples(index=False, name=None)}
    assert got == {
        ("2026-02-15", "FOO", "added"),      # both-in-one row: addition half
        ("2026-02-15", "BAR", "removed"),    # both-in-one row: removal half
        ("2026-03-05", "BAZ", "removed"),    # removal-only row
        ("2026-04-20", "ISO", "added"),      # ISO date format
        ("2026-05-15", "ZED", "added"),      # footnote-ref date "[4]"
        ("2026-07-10", "BRK-B", "added"),    # addition-only row, normalized
    }
    assert "JUNK" not in set(changes["ticker"])  # junk date row DROPPED
    assert "AAPL" not in set(changes["ticker"])  # decoy table (no headers) ignored
    assert set(changes["action"]) <= {"added", "removed"}


def test_parse_normalizes_share_class_separators() -> None:
    changes = parse_wiki_changes(_WIKI_HTML)
    july = changes[changes["change_date"] == pd.Timestamp("2026-07-10")]
    assert list(july["ticker"]) == ["BRK-B"]  # BRK/B -> BRK-B
    assert "/" not in "".join(changes["ticker"]) and "." not in "".join(changes["ticker"])


# --- reconstruct: effective-date semantics (end-of-month state per month file) ---

def test_reconstruct_mid_month_change_hits_own_month() -> None:
    """pierrebrunelle convention (verified vs the 124 overlap months): the
    M-01 snapshot carries the END-of-M state, so a mid-May change appears in
    the 2026-05-01 snapshot, not June's."""
    base = pd.DataFrame({
        "date": [pd.Timestamp("2026-04-01")],
        "ticker": ["AAPL"],
    })
    changes = _changes(("2026-05-15", "ZED", "added"))
    out = reconstruct_monthly_snapshots(changes, "2026-04", "2026-06", base)
    assert list(pd.unique(out["date"])) == [
        pd.Timestamp("2026-05-01"), pd.Timestamp("2026-06-01"),
    ]
    assert _snap(out, "2026-05-01") == {"AAPL", "ZED"}  # change effective IN May
    assert _snap(out, "2026-06-01") == {"AAPL", "ZED"}  # carried forward


def test_reconstruct_month_start_boundary_repeat_and_removal() -> None:
    base = pd.DataFrame({
        "date": [pd.Timestamp("2026-04-01")] * 2,
        "ticker": ["AAPL", "BAR"],
    })
    changes = _changes(
        ("2026-05-01", "XYZ", "added"),    # exactly a month start: IN May's snapshot
        ("2026-05-20", "BAR", "removed"),  # mid-month: also IN May's snapshot
    )
    out = reconstruct_monthly_snapshots(changes, "2026-04", "2026-07", base)
    assert _snap(out, "2026-05-01") == {"AAPL", "XYZ"}  # end-of-May state
    assert _snap(out, "2026-06-01") == {"AAPL", "XYZ"}  # carried forward
    assert _snap(out, "2026-07-01") == {"AAPL", "XYZ"}  # no-change repeat


def test_reconstruct_same_date_same_ticker_rename_row_is_noop() -> None:
    """A rename/successor row (same date, same ticker both added AND removed —
    e.g. 2019-03-19 'Added Fox Corporation (FOXA) / Removed 21st Century Fox
    (FOXA)') keeps membership CONTINUOUS: neither side applies."""
    base = pd.DataFrame({
        "date": [pd.Timestamp("2026-04-01")] * 2,
        "ticker": ["AAPL", "FOXA"],
    })
    changes = _changes(
        ("2026-05-10", "FOXA", "added"),    # rename row: both sides ...
        ("2026-05-10", "FOXA", "removed"),  # ... same ticker, same date
        ("2026-05-20", "ZED", "added"),
    )
    out = reconstruct_monthly_snapshots(changes, "2026-04", "2026-06", base)
    assert _snap(out, "2026-05-01") == {"AAPL", "FOXA", "ZED"}  # FOXA continuous
    assert _snap(out, "2026-06-01") == {"AAPL", "FOXA", "ZED"}


def test_reconcile_full_classifies_only_known_deviations() -> None:
    """A divergence covered by the VERIFIED closed deviation list is classified
    (ok stays True, fully reported); anything else still hard-fails."""
    # WLTW/new is on the verified list (upstream labels the company WTW).
    # Dated inside the rebuild window (the base is the 2026-01 snapshot).
    row = ('<tr><td>January 5, 2026</td><td>Willis Towers</td><td>WLTW</td>'
           '<td>—</td><td>—</td><td>Index change</td></tr>\n')
    html = _WIKI_HTML.replace("</table>", row + "</table>")
    existing = _existing_membership()  # carries no WLTW anywhere
    report = reconcile_full_reconstruction(parse_wiki_changes(html), existing)
    assert report["ok"] is True
    assert report["mismatches"] == []
    ticks = {(c["ticker"], c["side"]) for c in report["classified_deviations"]}
    assert ("WLTW", "new") in ticks
    # GHOST/new is NOT on the list -> hard fail with the ticker named.
    row2 = ('<tr><td>January 5, 2026</td><td>Ghost Inc</td><td>GHOST</td>'
            '<td>—</td><td>—</td><td>Index change</td></tr>\n')
    html2 = _WIKI_HTML.replace("</table>", row2 + "</table>")
    report2 = reconcile_full_reconstruction(parse_wiki_changes(html2), existing)
    assert report2["ok"] is False
    assert any("GHOST" in m["only_in_new"] for m in report2["mismatches"])


def test_reconstruct_requires_base_at_start_month() -> None:
    base = pd.DataFrame({
        "date": [pd.Timestamp("2026-03-01")],
        "ticker": ["AAPL"],
    })
    with pytest.raises(ValueError, match="start_month"):
        reconstruct_monthly_snapshots(_changes(), "2026-04", "2026-06", base)


# --- reconcile ---

def test_reconcile_full_reconstruction_pass() -> None:
    report = reconcile_full_reconstruction(parse_wiki_changes(_WIKI_HTML),
                                           _existing_membership())
    assert report["ok"] is True
    assert report["months_checked"] == 4  # 2016-01-style base month + 3 rebuilt
    assert report["mismatches"] == []


def test_reconcile_full_reconstruction_fail_lists_the_ticker() -> None:
    existing = pd.concat([
        _existing_membership(),
        pd.DataFrame({"date": [pd.Timestamp("2026-03-01")], "ticker": ["GHOST"]}),
    ], ignore_index=True)
    report = reconcile_full_reconstruction(parse_wiki_changes(_WIKI_HTML), existing)
    assert report["ok"] is False
    assert report["months_checked"] == 4
    assert report["mismatches"] == [{
        "month": "2026-03-01", "only_in_existing": ["GHOST"], "only_in_new": [],
    }]


def test_reconcile_overlap_reports_without_raising() -> None:
    new = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01"] * 2),
        "ticker": ["A", "B"],
    })
    existing = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01"] * 2),
        "ticker": ["A", "C"],
    })
    report = reconcile_overlap(new, existing)  # no exception on disagreement
    assert report == {
        "months_checked": 1,
        "mismatches": [{"month": "2026-01-01",
                        "only_in_existing": ["C"], "only_in_new": ["B"]}],
        "ok": False,
    }
    assert reconcile_overlap(new, new)["ok"] is True


# --- extend_membership (parquet-level; fetch monkeypatched -> zero network) ---

@pytest.fixture
def existing_pq(tmp_path, monkeypatch):
    pq = tmp_path / "universe_pierrebrunelle.parquet"
    _existing_membership().to_parquet(pq)
    monkeypatch.setattr(universe_ext, "fetch_wiki_changes_html", _fake_fetch)
    return pq


def test_extend_membership_dry_run_writes_nothing(existing_pq) -> None:
    before = existing_pq.read_bytes()
    summary = extend_membership(cache_dir=existing_pq.parent, dry_run=True,
                                now=pd.Timestamp("2026-06-10"))
    assert summary["ok"] is True and summary["dry_run"] is True
    assert summary["n_new_months"] == 2
    assert summary["new_months"] == ["2026-05-01", "2026-06-01"]
    assert summary.get("written") is False
    assert existing_pq.read_bytes() == before  # NOTHING written


def test_extend_membership_appends_and_preserves_original_rows(existing_pq) -> None:
    original = _existing_membership()
    summary = extend_membership(cache_dir=existing_pq.parent,
                                now=pd.Timestamp("2026-06-10"))
    assert summary["ok"] is True and summary["written"] is True
    after = pd.read_parquet(existing_pq)
    # append-only: the first len(original) rows are bit-identical
    assert_frame_equal(original, after.iloc[: len(original)].reset_index(drop=True),
                       check_exact=True)
    # ZED added 2026-05-15 -> end-of-May state lands in the 05-01 snapshot
    assert _snap(after, "2026-05-01") == {"AAPL", "FOO", "ISO", "ZED"}
    assert _snap(after, "2026-06-01") == {"AAPL", "FOO", "ISO", "ZED"}
    assert summary["rows_after"] == len(original) + 4 + 4


def test_extend_membership_gate_failure_leaves_parquet_untouched(tmp_path,
                                                                 monkeypatch) -> None:
    pq = tmp_path / "universe_pierrebrunelle.parquet"
    tampered = pd.concat([
        _existing_membership(),
        pd.DataFrame({"date": [pd.Timestamp("2026-03-01")], "ticker": ["GHOST"]}),
    ], ignore_index=True)
    tampered.to_parquet(pq)
    monkeypatch.setattr(universe_ext, "fetch_wiki_changes_html", _fake_fetch)
    before = pq.read_bytes()
    summary = extend_membership(cache_dir=tmp_path, now=pd.Timestamp("2026-06-10"))
    assert summary["ok"] is False
    assert summary["reconcile"]["ok"] is False
    assert "written" not in summary  # failed BEFORE any write
    assert pq.read_bytes() == before  # parquet untouched


def test_extend_membership_up_to_date_is_a_noop(existing_pq) -> None:
    before = existing_pq.read_bytes()
    summary = extend_membership(cache_dir=existing_pq.parent,
                                now=pd.Timestamp("2026-04-15"))
    assert summary["ok"] is True and summary["up_to_date"] is True
    assert summary["n_new_months"] == 0
    assert existing_pq.read_bytes() == before


# --- fetch_wiki_changes_html (cache + declared UA; HTTP faked) ---

class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.status_code = 200
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_fetch_html_cache_hit_is_zero_http(tmp_path, monkeypatch) -> None:
    (tmp_path / "wiki_spy_changes.html").write_text(_WIKI_HTML, encoding="utf-8")

    def _no_http(url, **kwargs):
        raise AssertionError("cache hit must make zero HTTP calls")

    monkeypatch.setattr(universe_ext, "_policy_get", _no_http)
    assert fetch_wiki_changes_html(tmp_path) == _WIKI_HTML


def test_fetch_html_single_polite_get_declares_ua_and_caches(tmp_path,
                                                             monkeypatch) -> None:
    calls = []

    def _fake_get(url, **kwargs):
        calls.append((url, kwargs.get("headers")))
        return _FakeResponse("<html>fetched</html>")

    monkeypatch.setattr(universe_ext, "_policy_get", _fake_get)
    assert fetch_wiki_changes_html(tmp_path) == "<html>fetched</html>"
    assert calls == [(universe_ext.WIKI_URL,
                      {"User-Agent": "Aionis research universe-ext contact@example.com"})]
    # raw HTML cached -> a second call is a cache hit (no further HTTP)
    assert fetch_wiki_changes_html(tmp_path) == "<html>fetched</html>"
    assert (tmp_path / "wiki_spy_changes.html").read_text(
        encoding="utf-8") == "<html>fetched</html>"
    assert len(calls) == 1
    # force=True bypasses the cache and re-fetches
    assert fetch_wiki_changes_html(tmp_path, force=True) == "<html>fetched</html>"
    assert len(calls) == 2
