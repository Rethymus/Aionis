"""Hermetic tests for the FF5 daily factor ingest (RES-02).

Covers: robust ZIP/CSV parsing (doc-line skipping, percent→decimal, column
order), snapshot-first fetch (G3/G4: cache hit = zero HTTP, sha256 drift =
hard error), politeness (>=2s spacing + bounded exponential retry through the
shared policy) and fail-closed behavior. No real network: the ZIP is built in
memory and requests.get is monkeypatched.
"""

from __future__ import annotations

import io
import threading
import zipfile
from dataclasses import dataclass, field

import pandas as pd
import pytest
import requests

from aionis.ingest.ff5 import (
    ALL_COLS,
    FACTOR_COLS,
    FF5_DAILY_ZIP_URL,
    RF_COL,
    fetch_ff5_daily_snapshot,
    parse_ff5_daily_csv,
    sha256_bytes,
    snapshot_sha256,
)
from aionis.ingest.http_policy import (
    HostSpacingPolicy,
    HttpRequestPolicy,
    HTTPStatusError,
    RetryPolicy,
)

# --- fixtures -----------------------------------------------------------------

_ROWS = [
    "20240102,0.12,-0.05,0.03,0.01,-0.02,0.0002",
    "20240103,0.08,0.10,-0.04,0.02,0.01,0.0002",
    "20240104,-0.15,0.02,0.05,-0.01,0.00,0.0002",
    "20240105,0.20,-0.03,-0.02,0.00,0.03,0.0002",
]


def _ff5_zip_bytes(doc_lines: str = "This file was created by daily_factors.sas\n\n") -> bytes:
    """In-memory French-shaped bulk ZIP (doc lines + blank + header + data)."""
    csv = (
        f"{doc_lines}\n"
        "Mkt-RF,SMB,HML,RMW,CMA,RF\n"
        + "\n".join(_ROWS)
        + "\n"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("F-F_Research_Data_5_Factors_2x3_daily.csv", csv)
    return buf.getvalue()


class FakeTime:
    def __init__(self, initial: float = 0.0) -> None:
        self.value = initial
        self.sleeps: list[float] = []
        self._lock = threading.Lock()

    def monotonic(self) -> float:
        with self._lock:
            return self.value

    def sleep(self, seconds: float) -> None:
        with self._lock:
            self.sleeps.append(seconds)
            self.value += seconds


@dataclass
class FakeResponse:
    status_code: int
    content: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)


def _install_get(monkeypatch: pytest.MonkeyPatch, resp: FakeResponse) -> list[dict]:
    """Monkeypatch requests.get with a canned response; record call kwargs."""
    calls: list[dict] = []

    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        calls.append({"url": url, **kwargs})
        return resp

    monkeypatch.setattr(requests, "get", fake_get)
    return calls


def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("network call attempted in offline test")

    monkeypatch.setattr(requests, "get", _boom)


# --- parsing ------------------------------------------------------------------


def test_parse_ff5_daily_csv_columns_dates_and_decimal_scale() -> None:
    df = parse_ff5_daily_csv(_ff5_zip_bytes())

    assert list(df.columns) == list(ALL_COLS)
    assert list(df["date"]) == [
        pd.Timestamp("2024-01-02"),
        pd.Timestamp("2024-01-03"),
        pd.Timestamp("2024-01-04"),
        pd.Timestamp("2024-01-05"),
    ]
    # percent -> decimal (0.12% -> 0.0012)
    assert df["mkt_rf"].tolist() == pytest.approx([0.0012, 0.0008, -0.0015, 0.0020])
    assert df["smb"].tolist() == pytest.approx([-0.0005, 0.0010, 0.0002, -0.0003])
    assert df["hml"].tolist() == pytest.approx([0.0003, -0.0004, 0.0005, -0.0002])
    assert df["rmw"].tolist() == pytest.approx([0.0001, 0.0002, -0.0001, 0.0000])
    assert df["cma"].tolist() == pytest.approx([-0.0002, 0.0001, 0.0000, 0.0003])
    assert df[RF_COL].tolist() == pytest.approx([0.000002] * 4)
    assert df["date"].is_monotonic_increasing


def test_parse_skips_arbitrary_doc_lines_and_finds_data_by_8_digit_dates() -> None:
    docs = (
        "line one of the description\n"
        "line two of the description\n"
        "line three of the description\n"
        "\n"
        "a stray non-header line\n"
    )
    df = parse_ff5_daily_csv(_ff5_zip_bytes(doc_lines=docs))
    assert len(df) == len(_ROWS)
    assert df["mkt_rf"].iloc[0] == pytest.approx(0.0012)


def test_parse_skips_copyright_footer_after_data_rows() -> None:
    """2026-era French files carry a 'Copyright ...' footer after the data rows;
    the parser must drop those rows instead of failing date coercion."""
    csv = (
        "This file was created by using the 202605 CRSP database.\n"
        "The Tbill return is the simple daily rate that, over the number of"
        " trading days\n"
        "compounds to 1-month TBill rate.\n"
        "\n"
        "Mkt-RF,SMB,HML,RMW,CMA,RF\n"
        + "\n".join(_ROWS)
        + "\n"
        "Copyright 2026 Eugene F. Fama and Kenneth R. French\n"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("F-F_Research_Data_5_Factors_2x3_daily.csv", csv)
    df = parse_ff5_daily_csv(buf.getvalue())
    assert len(df) == len(_ROWS)
    assert df["date"].iloc[-1] == pd.Timestamp("2024-01-05")
    assert df["mkt_rf"].iloc[0] == pytest.approx(0.0012)


def test_parse_rejects_zip_without_csv() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "nothing to see")
    with pytest.raises(ValueError, match="exactly one CSV"):
        parse_ff5_daily_csv(buf.getvalue())


def test_parse_rejects_missing_data_rows() -> None:
    csv = "Mkt-RF,SMB,HML,RMW,CMA,RF\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("F-F_Research_Data_5_Factors_2x3_daily.csv", csv)
    with pytest.raises(ValueError, match="no YYYYMMDD data rows"):
        parse_ff5_daily_csv(buf.getvalue())


def test_parse_drops_rows_with_missing_values_and_keeps_rest() -> None:
    rows = [
        "20240102,0.12,-0.05,0.03,0.01,-0.02,0.0002",
        "20240103,0.08,0.10,-0.04,0.02,0.01,",  # RF missing -> row dropped
        "20240104,-0.15,0.02,0.05,-0.01,0.00,0.0002",
    ]
    csv = "Mkt-RF,SMB,HML,RMW,CMA,RF\n" + "\n".join(rows) + "\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("F-F_Research_Data_5_Factors_2x3_daily.csv", csv)
    df = parse_ff5_daily_csv(buf.getvalue())
    assert len(df) == 2
    assert pd.Timestamp("2024-01-03") not in set(df["date"])


def test_parse_rejects_all_missing_values() -> None:
    rows = [
        "20240102,,,,,,",
        "20240103,,,,,,",
    ]
    csv = "Mkt-RF,SMB,HML,RMW,CMA,RF\n" + "\n".join(rows) + "\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("F-F_Research_Data_5_Factors_2x3_daily.csv", csv)
    with pytest.raises(ValueError, match="zero valid rows"):
        parse_ff5_daily_csv(buf.getvalue())


# --- snapshot discipline (G3/G4) ----------------------------------------------


def test_fetch_writes_snapshot_and_sha256_then_cache_hit_is_offline(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    zip_bytes = _ff5_zip_bytes()
    calls = _install_get(monkeypatch, FakeResponse(200, zip_bytes))

    df1, sha1 = fetch_ff5_daily_snapshot(tmp_path)

    csv_path = tmp_path / "ff5_daily_snapshot.csv"
    sha_path = tmp_path / "ff5_daily_snapshot.sha256"
    assert csv_path.exists() and sha_path.exists()
    assert sha1 == sha256_bytes(csv_path.read_bytes())
    assert sha_path.read_text().strip() == sha1
    assert sha1 == snapshot_sha256(csv_path)
    assert len(df1) == len(_ROWS)
    assert calls and calls[0]["url"] == FF5_DAILY_ZIP_URL

    # Cache hit: zero HTTP, bit-identical snapshot (H6), same sha.
    _no_network(monkeypatch)
    df2, sha2 = fetch_ff5_daily_snapshot(tmp_path)
    assert sha2 == sha1
    pd.testing.assert_frame_equal(df2, df1)


def test_snapshot_sha256_drift_raises(tmp_path) -> None:
    csv_path = tmp_path / "ff5_daily_snapshot.csv"
    sha_path = tmp_path / "ff5_daily_snapshot.sha256"
    csv_path.write_text("date,mkt_rf\n2024-01-02,0.0012\n")
    sha_path.write_text("f" * 64 + "\n")  # deliberately wrong recorded sha
    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        fetch_ff5_daily_snapshot(tmp_path)


# --- politeness + bounded retry (G7) ------------------------------------------


def test_fetch_uses_politeness_and_bounded_retry(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeTime()
    zip_bytes = _ff5_zip_bytes()
    responses = iter(
        [FakeResponse(429), FakeResponse(429), FakeResponse(200, zip_bytes)]
    )

    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        return next(responses)

    monkeypatch.setattr(requests, "get", fake_get)
    policy = HttpRequestPolicy(
        clock=fake.monotonic,
        sleeper=fake.sleep,
        spacing=HostSpacingPolicy(clock=fake.monotonic, sleeper=fake.sleep),
        retry=RetryPolicy(max_retries=3, backoff_base=2.0),
    )

    df, sha = fetch_ff5_daily_snapshot(tmp_path, policy=policy)

    # >=2s host spacing on every request slot + exponential backoff (2s, 4s).
    assert fake.sleeps == [2.0, 4.0]
    assert len(df) == len(_ROWS)
    assert sha == snapshot_sha256(tmp_path / "ff5_daily_snapshot.csv")


def test_fetch_fails_closed_on_persistent_5xx(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeTime()
    responses = iter([FakeResponse(500)] * 4)

    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        return next(responses)

    monkeypatch.setattr(requests, "get", fake_get)
    policy = HttpRequestPolicy(
        clock=fake.monotonic,
        sleeper=fake.sleep,
        spacing=HostSpacingPolicy(clock=fake.monotonic, sleeper=fake.sleep),
        retry=RetryPolicy(max_retries=3, backoff_base=2.0),
    )

    with pytest.raises(HTTPStatusError):
        fetch_ff5_daily_snapshot(tmp_path, policy=policy)
    assert not (tmp_path / "ff5_daily_snapshot.csv").exists()  # no partial snapshot
    assert fake.sleeps == [2.0, 4.0, 8.0]  # bounded: 3 backoff sleeps, then raise


def test_snapshot_columns_are_the_stock_specific_factor_set() -> None:
    df = parse_ff5_daily_csv(_ff5_zip_bytes())
    assert set(FACTOR_COLS) == {"mkt_rf", "smb", "hml", "rmw", "cma"}
    assert RF_COL == "rf"
    assert set(df.columns) == {"date", *FACTOR_COLS, RF_COL}
