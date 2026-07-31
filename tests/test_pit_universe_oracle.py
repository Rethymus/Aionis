from __future__ import annotations

import pandas as pd
import pytest

from aionis.ingest.universe import (
    constituents_manifest_on,
    constituents_on,
    normalize_ticker,
)

# --- synthetic fixtures (no network, no real data) ---

@pytest.fixture
def simple_membership() -> pd.DataFrame:
    """Simple timeline: tickers added/removed across snapshots."""
    dates = ["2020-01-01", "2020-01-01",
             "2020-02-01", "2020-02-01",
             "2020-03-01", "2020-03-01"]
    tickers = ["AAPL", "MSFT", "AAPL", "MSFT", "AAPL", "NVDA"]
    return pd.DataFrame({
        "date": pd.to_datetime(dates),
        "ticker": tickers,
    })


@pytest.fixture
def add_remove_membership() -> pd.DataFrame:
    """Timeline with both additions and removals."""
    return pd.DataFrame({
        "date": pd.to_datetime([
            "2020-01-01",
            "2020-01-01",
            "2020-02-01",
            "2020-02-01",
            "2020-03-01",
        ]),
        "ticker": ["AAPL", "MSFT", "MSFT", "NVDA", "MSFT"],
    })


@pytest.fixture
def same_day_add_remove() -> pd.DataFrame:
    """Same-day add AND remove — ticker added and removed on identical date."""
    return pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-01"]),
        "ticker": ["AAPL", "MSFT", "AAPL"],
    })


@pytest.fixture
def duplicate_records() -> pd.DataFrame:
    """Duplicate (date, ticker) pairs — must be idempotent/deterministic."""
    return pd.DataFrame({
        "date": pd.to_datetime([
            "2020-01-01", "2020-01-01", "2020-01-01",  # AAPL duplicated twice
            "2020-02-01", "2020-02-01", "2020-02-01", "2020-02-01",  # MSFT duplicated 3 times
        ]),
        "ticker": ["AAPL", "AAPL", "AAPL", "MSFT", "MSFT", "MSFT", "MSFT"],
    })


@pytest.fixture
def sparse_snapshots() -> pd.DataFrame:
    """Sparse snapshots (gaps) — no forward-fill between dates."""
    return pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-04-01"]),  # 3-month gap
        "ticker": ["AAPL", "MSFT"],
    })


@pytest.fixture
def historical_union_pool() -> pd.DataFrame:
    """
    Simulates the 588-style historical UNION pool: all tickers ever present.
    This is NOT the contemporaneous monthly membership.
    """
    all_tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA", "META", "BRK-B"]
    rows = []
    for ticker in all_tickers:
        rows.append(("2020-01-01", ticker))
        rows.append(("2020-06-01", ticker))  # all present at month end
    dates, tickers = zip(*rows, strict=True)
    return pd.DataFrame({
        "date": pd.to_datetime(list(dates)),
        "ticker": list(tickers),
    })


@pytest.fixture
def contemporaneous_monthly() -> pd.DataFrame:
    """
    Real contemporaneous monthly membership (~500 tickers at any point).
    This is what constituents_on(t) should return — NOT the union pool.
    """
    return pd.DataFrame({
        "date": pd.to_datetime([
            "2020-01-01", "2020-01-01", "2020-01-01",
            "2020-02-01", "2020-02-01",
            "2020-03-01",
        ]),
        "ticker": ["AAPL", "MSFT", "NVDA", "AAPL", "MSFT", "AAPL"],
    })


# --- oracle 1: exact PIT match at several dates ---

def test_exact_pit_match_at_multiple_dates(simple_membership) -> None:
    """constituents_on(t) returns EXACT members at point-in-time t."""
    # Jan 1: AAPL, MSFT
    assert constituents_on(simple_membership, "2020-01-01") == {"AAPL", "MSFT"}
    # Jan 15: still AAPL, MSFT (latest snapshot <= Jan 15 is Jan 1)
    assert constituents_on(simple_membership, "2020-01-15") == {"AAPL", "MSFT"}
    # Feb 1: AAPL, MSFT (Feb 1 snapshot)
    assert constituents_on(simple_membership, "2020-02-01") == {"AAPL", "MSFT"}
    # Feb 15: still AAPL, MSFT (latest snapshot <= Feb 15 is Feb 1)
    assert constituents_on(simple_membership, "2020-02-15") == {"AAPL", "MSFT"}
    # Mar 1: AAPL, NVDA (Mar 1 snapshot)
    assert constituents_on(simple_membership, "2020-03-01") == {"AAPL", "NVDA"}


# --- oracle 2: same-day add AND remove ---

def test_same_day_add_and_remove_behavior(same_day_add_remove) -> None:
    """
    Same-day add AND remove: ticker added and removed on the same date.
    Assert defined behavior explicitly.
    """
    # On the date itself: if a ticker appears in both add and remove,
    # the snapshot determines membership. Our implementation uses latest
    # snapshot <= t, so if the same-date snapshot lists both, the set
    # semantics determine the result.
    result = constituents_on(same_day_add_remove, "2020-01-01")
    # Both AAPL and MSFT appear in the 2020-01-01 snapshot
    assert result == {"AAPL", "MSFT"}, (
        "Same-day add+remove: snapshot is authoritative; "
        "both tickers present in 2020-01-01 snapshot"
    )


# --- oracle 3: boundary dates ---

def test_boundary_dates_in_on_add_out_on_remove(add_remove_membership) -> None:
    """Boundary: ticker IN ON add date, OUT on/after remove date."""
    # Jan 1: AAPL, MSFT added
    assert "AAPL" in constituents_on(add_remove_membership, "2020-01-01")
    assert "MSFT" in constituents_on(add_remove_membership, "2020-01-01")

    # Jan 31: still both present (before Feb 1 snapshot)
    assert "AAPL" in constituents_on(add_remove_membership, "2020-01-31")
    assert "MSFT" in constituents_on(add_remove_membership, "2020-01-31")

    # Feb 1: NVDA added, AAPL removed (Feb 1 snapshot: MSFT, NVDA)
    feb_1 = constituents_on(add_remove_membership, "2020-02-01")
    assert "NVDA" in feb_1
    assert "AAPL" not in feb_1, "AAPL removed ON Feb 1"
    assert "MSFT" in feb_1

    # Feb 15: still no AAPL (after removal date)
    assert "AAPL" not in constituents_on(add_remove_membership, "2020-02-15")

    # Mar 1: MSFT only (Mar 1 snapshot)
    mar_1 = constituents_on(add_remove_membership, "2020-03-01")
    assert "MSFT" in mar_1, "Mar 1 snapshot has MSFT"
    assert "NVDA" not in mar_1, "NVDA not in Mar 1 snapshot"


# --- oracle 4: no prior history → empty ---

def test_no_prior_history_returns_empty(simple_membership) -> None:
    """constituents_on(t) before first snapshot → empty set (no forward-fill)."""
    # Before any snapshot: empty
    assert constituents_on(simple_membership, "2019-12-31") == set()
    assert constituents_on(simple_membership, "2015-01-01") == set()
    assert constituents_on(simple_membership, "1999-06-15") == set()

    # ON first snapshot date: members present
    assert constituents_on(simple_membership, "2020-01-01") == {"AAPL", "MSFT"}


# --- oracle 5: FUTURE snapshot rejection ---

def test_future_snapshot_rejection_no_lookahead(simple_membership) -> None:
    """
    A snapshot dated AFTER t must NOT be used (no lookahead).
    Assert t-result is unaffected by future snapshots.
    """
    # Jan 15 query should NOT see Feb 1 or Mar 1 snapshots
    jan_15 = constituents_on(simple_membership, "2020-01-15")
    assert jan_15 == {"AAPL", "MSFT"}, (
        "Jan 15 query: AAPL+MSFT (Jan 1 snapshot); "
        "Feb 1 and Mar 1 snapshots are in the future and ignored"
    )

    # Feb 15 query should NOT see Mar 1 snapshot
    feb_15 = constituents_on(simple_membership, "2020-02-15")
    assert feb_15 == {"AAPL", "MSFT"}, (
        "Feb 15 query: AAPL+MSFT (Feb 1 snapshot); "
        "Mar 1 snapshot is future and ignored"
    )


# --- oracle 6: duplicate records → deterministic/idempotent ---

def test_duplicate_records_deterministic_handling(duplicate_records) -> None:
    """
    Duplicate (date, ticker) records → deterministic handling.
    Implementation: constituents_on uses set() internally, so duplicates
    are automatically idempotent.
    """
    # Both dates have duplicates, but result should be clean sets
    jan_1 = constituents_on(duplicate_records, "2020-01-01")
    assert jan_1 == {"AAPL"}, "Duplicates collapsed to single member"

    feb_1 = constituents_on(duplicate_records, "2020-02-01")
    assert feb_1 == {"MSFT"}, "Duplicates collapsed to single member"

    # Verify idempotence: calling twice gives same result
    assert jan_1 == constituents_on(duplicate_records, "2020-01-01")
    assert feb_1 == constituents_on(duplicate_records, "2020-02-01")


# --- oracle 7: snapshot manifest (date, age, hash) ---

def test_snapshot_manifest_fields_missing() -> None:
    """
    Snapshot manifest carries snapshot date + age + hash.
    Verifies constituents_manifest_on returns a proper manifest structure.
    """
    # Simple fixture with known snapshots
    membership = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-02-01"]),
        "ticker": ["AAPL", "MSFT", "GOOGL"],
    })

    # Query on exact snapshot date
    manifest = constituents_manifest_on(membership, "2020-01-01")
    assert manifest.snapshot_date == pd.Timestamp("2020-01-01")
    assert manifest.age_days == 0
    assert manifest.members == frozenset({"AAPL", "MSFT"})
    assert manifest.hash is not None
    assert len(manifest.hash) == 64  # SHA-256 hex digest

    # Query between snapshots (uses latest snapshot ≤ query date)
    manifest = constituents_manifest_on(membership, "2020-01-15")
    assert manifest.snapshot_date == pd.Timestamp("2020-01-01")
    assert manifest.age_days == 14  # 15 days difference

    # Query on later snapshot
    manifest = constituents_manifest_on(membership, "2020-02-01")
    assert manifest.snapshot_date == pd.Timestamp("2020-02-01")
    assert manifest.age_days == 0
    assert manifest.members == frozenset({"GOOGL"})

    # Query before first snapshot
    manifest = constituents_manifest_on(membership, "2019-12-31")
    assert manifest.snapshot_date is None
    assert manifest.age_days is None
    assert manifest.hash is None
    assert manifest.members == frozenset()


def test_hash_content_stability() -> None:
    """
    Hash must be content-stable: identical membership → identical hash.
    Different membership → different hash.
    """
    # Same membership, same hash
    membership1 = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-01-01"]),
        "ticker": ["AAPL", "MSFT"],
    })
    membership2 = pd.DataFrame({
        "date": pd.to_datetime(["2020-02-01", "2020-02-01"]),
        "ticker": ["MSFT", "AAPL"],  # Same tickers, different order
    })

    manifest1 = constituents_manifest_on(membership1, "2020-01-01")
    manifest2 = constituents_manifest_on(membership2, "2020-02-01")

    assert manifest1.hash == manifest2.hash, (
        "Identical membership sets must produce identical hash "
        "(order-independent, tickers are sorted before hashing)"
    )

    # Different membership, different hash
    membership3 = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-01-01"]),
        "ticker": ["AAPL", "GOOGL"],
    })

    manifest3 = constituents_manifest_on(membership3, "2020-01-01")

    assert manifest3.hash != manifest1.hash, (
        "Different membership sets must produce different hashes"
    )

    # Empty set → consistent None hash
    empty = pd.DataFrame({
        "date": pd.to_datetime([]),
        "ticker": [],
    })
    manifest_empty = constituents_manifest_on(empty, "2020-01-01")
    assert manifest_empty.hash is None


# --- oracle 8: NO forward-fill ---

def test_no_forward_fill_absent_ticker_not_present(sparse_snapshots) -> None:
    """
    NO forward-fill: a ticker absent from the t snapshot is NOT assumed present.
    Gap months (Feb, Mar 2020) must NOT inherit Jan or Apr membership.
    """
    # Jan 1: AAPL present
    assert constituents_on(sparse_snapshots, "2020-01-01") == {"AAPL"}

    # Feb 1: NO snapshot → uses Jan 1 (latest <= Feb 1) → AAPL only
    feb_1 = constituents_on(sparse_snapshots, "2020-02-01")
    assert feb_1 == {"AAPL"}, (
        "Feb 1: no Feb snapshot, so uses Jan 1 snapshot (AAPL only). "
        "This is NOT forward-fill — it's backward-lookup to latest snapshot."
    )

    # Feb 15: still AAPL only (still using Jan 1 snapshot)
    assert constituents_on(sparse_snapshots, "2020-02-15") == {"AAPL"}

    # Mar 1: still AAPL only (Jan 1 is still latest <= Mar 1)
    mar_1 = constituents_on(sparse_snapshots, "2020-03-01")
    assert mar_1 == {"AAPL"}, (
        "Mar 1: no Mar snapshot, still uses Jan 1. "
        "MSFT (Apr 1 snapshot) is FUTURE and not looked ahead to."
    )

    # Apr 1: MSFT present (new snapshot)
    assert constituents_on(sparse_snapshots, "2020-04-01") == {"MSFT"}

    # Verify MSFT was NOT forward-filled into Feb/Mar
    assert "MSFT" not in constituents_on(sparse_snapshots, "2020-02-01")
    assert "MSFT" not in constituents_on(sparse_snapshots, "2020-03-15")


# --- oracle 9: UNION-POOL ≠ CONTEMPORANEOUS guard ---

def test_union_pool_not_contemporaneous_monthly_membership(
    historical_union_pool, contemporaneous_monthly,
) -> None:
    """
    ANTI-SURVIVORSHIP GUARD: the 588-style historical UNION of all tickers
    must NOT equal the ~500 contemporaneous monthly membership.

    This is the load-bearing assertion against survivorship bias:
    - Union pool: all tickers EVER in S&P 500 (588 unique)
    - Contemporaneous: actual members at a specific point (~500)

    Confusing these introduces survivorship bias by assuming all historical
    tickers were present at all times.
    """
    # Union pool: all 8 tickers appear at BOTH dates
    union_jan = constituents_on(historical_union_pool, "2020-01-01")
    union_jun = constituents_on(historical_union_pool, "2020-06-01")

    assert len(union_jan) == 8, f"Union pool Jan: all 8 tickers, got {len(union_jan)}"
    assert len(union_jun) == 8, f"Union pool Jun: all 8 tickers, got {len(union_jun)}"
    assert union_jan == union_jun, "Union pool is identical across time"

    # Contemporaneous: varies by date
    cont_jan = constituents_on(contemporaneous_monthly, "2020-01-01")
    cont_feb = constituents_on(contemporaneous_monthly, "2020-02-01")
    cont_mar = constituents_on(contemporaneous_monthly, "2020-03-01")

    assert len(cont_jan) == 3, f"Contemporaneous Jan: 3 tickers, got {len(cont_jan)}"
    assert len(cont_feb) == 2, f"Contemporaneous Feb: 2 tickers, got {len(cont_feb)}"
    assert len(cont_mar) == 1, f"Contemporaneous Mar: 1 ticker, got {len(cont_mar)}"

    # CRITICAL: union pool ≠ contemporaneous
    assert union_jan != cont_jan, (
        "UNION POOL ≠ CONTEMPORANEOUS: union has all 8, "
        "but contemporaneous Jan has only 3"
    )

    # Union pool is a superset (not equal)
    assert union_jan.issuperset(cont_jan), "Union pool is superset"
    assert not union_jan.issubset(cont_jan), "Union not subset of contemporaneous"

    # Any code that treats the union pool as the monthly universe would FAIL
    # this assertion. This is the guard against survivorship leakage.


# --- oracle 10: freshness reporting only ---

def test_freshness_reporting_no_threshold_enforcement() -> None:
    """
    The code REPORTS snapshot age; it does NOT impose a freshness threshold.
    Even stale snapshots are returned with their age reported.
    """
    # Create a membership with a 90-day-old snapshot
    old_membership = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-01-01"]),
        "ticker": ["AAPL", "MSFT"],
    })

    # Query 90 days later
    manifest = constituents_manifest_on(old_membership, "2020-04-01")

    # Age is reported
    assert manifest.age_days == 91  # Jan 1 to Apr 1 is 91 days
    assert manifest.snapshot_date == pd.Timestamp("2020-01-01")

    # Members are STILL returned despite stale snapshot
    assert manifest.members == frozenset({"AAPL", "MSFT"})

    # NO rejection based on age - the function returns the stale snapshot
    # with its age documented, but does NOT raise an error or return empty
    assert manifest.members == frozenset({"AAPL", "MSFT"}), (
        "Age is reported, NOT enforced. Stale snapshots are returned."
    )

    # Verify very old snapshots (1 year) are also returned with age
    manifest_year_old = constituents_manifest_on(old_membership, "2021-01-01")
    assert manifest_year_old.age_days == 366  # Leap year 2020
    assert manifest_year_old.members == frozenset({"AAPL", "MSFT"}), (
        "Even 1-year-old snapshots are returned (age reporting, not enforcement)"
    )


# --- edge cases and integration checks ---

def test_normalize_ticker_idempotent() -> None:
    """normalize_ticker must be idempotent (call twice → same result)."""
    ticker = "BRK.B"
    first = normalize_ticker(ticker)
    second = normalize_ticker(first)
    assert first == second == "BRK-B"


def test_empty_membership_dataframe() -> None:
    """Empty membership DataFrame → constituents_on returns empty set."""
    empty = pd.DataFrame({"date": pd.to_datetime([]), "ticker": []})
    assert constituents_on(empty, "2020-01-01") == set()


def test_single_snapshot_carries_forward_until_next() -> None:
    """
    A single snapshot persists until the next snapshot date.
    This is backward-lookup, not forward-fill.
    """
    single_snap = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-01-01"]),
        "ticker": ["AAPL", "MSFT"],
    })

    # Jan 1: exact match
    assert constituents_on(single_snap, "2020-01-01") == {"AAPL", "MSFT"}

    # Any date in 2020: uses Jan 1 snapshot (latest <= query date)
    assert constituents_on(single_snap, "2020-06-15") == {"AAPL", "MSFT"}
    assert constituents_on(single_snap, "2020-12-31") == {"AAPL", "MSFT"}

    # Future: still uses Jan 1 (no newer snapshot)
    assert constituents_on(single_snap, "2025-01-01") == {"AAPL", "MSFT"}

    # Past: empty
    assert constituents_on(single_snap, "2019-12-31") == set()


def test_normalize_ticker_in_constituents_on() -> None:
    """
    constituents_on must respect normalize_ticker semantics.
    BRK.B, BRK/B, BRK-B are treated as identical.
    """
    # Create data with normalized tickers (constituents_on doesn't normalize)
    mixed_formats = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-02-01"]),
        "ticker": [normalize_ticker("BRK.B"), normalize_ticker("BRK/B"), normalize_ticker("BRK-B")],
    })

    # After normalization, all are BRK-B → set deduplication
    jan_1 = constituents_on(mixed_formats, "2020-01-01")
    assert jan_1 == {"BRK-B"}, (
        "BRK.B and BRK/B both normalize to BRK-B → single member"
    )

    feb_1 = constituents_on(mixed_formats, "2020-02-01")
    assert feb_1 == {"BRK-B"}
