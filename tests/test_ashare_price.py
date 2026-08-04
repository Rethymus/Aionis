"""Hermetic tests for the baostock A-share price ingest adapter.

baostock is mocked via ``sys.modules`` — no real network, no baostock.com login.
Exercises the tidy-long transform, G3 adjustflag pass-through, G6 suspension
NaN'ing, G7 single-session login/logout, and fail-closed auth/query errors.
"""
from __future__ import annotations

import sys
import types

import pandas as pd
import pytest

from aionis.ingest import ashare_price

_FIELDS = ["date", "code", "open", "high", "low", "close", "volume", "tradestatus"]


class _FakeResult:
    """Mimics baostock ResultData: ``error_code``, ``fields``, ``next``, ``get_row_data``."""

    def __init__(self, rows: list[list[str]], error_code: str = "0") -> None:
        self._rows = rows
        self.fields = list(_FIELDS)
        self.error_code = error_code
        self._i = -1

    def next(self) -> bool:
        self._i += 1
        return self._i < len(self._rows)

    def get_row_data(self) -> list[str]:
        return list(self._rows[self._i])


class _FakeBaostock:
    """Records login/logout + queries; serves canned rows per code."""

    def __init__(self, data_by_code: dict[str, list[list[str]]]) -> None:
        self.data_by_code = data_by_code
        self.login_calls = 0
        self.logout_calls = 0
        self.queries: list[tuple[str, dict]] = []

    def login(self) -> types.SimpleNamespace:
        self.login_calls += 1
        return types.SimpleNamespace(error_code="0", error_msg="success")

    def logout(self) -> None:
        self.logout_calls += 1

    def query_history_k_data_plus(self, code: str, **kwargs: object) -> _FakeResult:
        self.queries.append((code, dict(kwargs)))
        return _FakeResult(self.data_by_code.get(code, []))


@pytest.fixture
def _mock_baostock(monkeypatch):
    """Install a fresh fake baostock module; return it for per-test data setup."""

    fake = _FakeBaostock(data_by_code={})
    mod = types.ModuleType("baostock")
    mod.login = fake.login  # type: ignore[attr-defined]
    mod.logout = fake.logout  # type: ignore[attr-defined]
    # Delegate via a wrapper so tests can rebind fake.query_history_k_data_plus
    # (the lookup happens fresh each call, so instance-attribute rebinding works).
    mod.query_history_k_data_plus = (  # type: ignore[attr-defined]
        lambda *a, **kw: fake.query_history_k_data_plus(*a, **kw)
    )
    monkeypatch.setitem(sys.modules, "baostock", mod)
    return fake


def test_tidy_long_shape_and_suspension_nan(_mock_baostock):
    # Arrange: two codes; sh.600000 has one suspended day (tradestatus "0").
    _mock_baostock.data_by_code = {
        "sh.600000": [
            ["2020-01-02", "sh.600000", "10.0", "10.5", "9.8", "10.2", "1000", "1"],
            ["2020-01-03", "sh.600000", "0", "0", "0", "0", "0", "0"],  # suspended
        ],
        "sz.000001": [
            ["2020-01-02", "sz.000001", "20.0", "20.5", "19.9", "20.1", "500", "1"],
        ],
    }

    # Act
    df = ashare_price.fetch_ashare_prices(
        ["sh.600000", "sz.000001"], "2020-01-02", "2020-01-03", pause=0
    )

    # Assert: tidy long shape
    assert list(df.columns) == ashare_price._COLUMNS
    assert len(df) == 3
    assert set(df["ticker"]) == {"sh.600000", "sz.000001"}

    # Suspended row's OHLCV is NaN; trading rows keep values
    suspended = df[(df["ticker"] == "sh.600000") & (df["tradestatus"] == "0")].iloc[0]
    assert pd.isna(suspended["close"])
    assert pd.isna(suspended["volume"])
    trading = df[(df["ticker"] == "sh.600000") & (df["tradestatus"] == "1")].iloc[0]
    assert trading["close"] == pytest.approx(10.2)


def test_adjustflag_passes_through_default_and_custom(_mock_baostock):
    # Arrange
    _mock_baostock.data_by_code = {
        "sh.600000": [["2020-01-02", "sh.600000", "10", "10", "10", "10", "1", "1"]],
    }

    # Act — default (raw, G3 方案 A)
    ashare_price.fetch_ashare_prices(["sh.600000"], "2020-01-02", "2020-01-02", pause=0)
    assert _mock_baostock.queries[0][1]["adjustflag"] == "3"

    # Act — explicit forward-adjusted (a different frozen series = new ledger row)
    ashare_price.fetch_ashare_prices(
        ["sh.600000"], "2020-01-02", "2020-01-02", adjustflag="1", pause=0
    )
    assert _mock_baostock.queries[1][1]["adjustflag"] == "1"


def test_single_login_logout_session_across_batch(_mock_baostock):
    # Arrange: one login spans the whole batch; logout always fires (finally).
    _mock_baostock.data_by_code = {
        "sh.600000": [["2020-01-02", "sh.600000", "10", "10", "10", "10", "1", "1"]],
        "sz.000001": [["2020-01-02", "sz.000001", "20", "20", "20", "20", "1", "1"]],
    }

    # Act
    ashare_price.fetch_ashare_prices(
        ["sh.600000", "sz.000001"], "2020-01-02", "2020-01-02", pause=0
    )

    # Assert
    assert _mock_baostock.login_calls == 1
    assert _mock_baostock.logout_calls == 1


def test_logout_fires_even_on_query_error(_mock_baostock):
    # Arrange: second code raises; logout must still run (G7 session hygiene).
    _mock_baostock.data_by_code = {
        "sh.600000": [["2020-01-02", "sh.600000", "10", "10", "10", "10", "1", "1"]],
    }

    class _BoomResult(_FakeResult):
        def __init__(self) -> None:
            super().__init__(rows=[])
            self.error_code = "1"
            self.error_msg = "bad code"

    original = _mock_baostock.query_history_k_data_plus

    def _flaky(code, **kwargs):
        if code == "sz.000001":
            return _BoomResult()
        return original(code, **kwargs)

    _mock_baostock.query_history_k_data_plus = _flaky  # type: ignore[assignment]

    # Act / Assert
    with pytest.raises(RuntimeError, match="baostock query failed"):
        ashare_price.fetch_ashare_prices(
            ["sh.600000", "sz.000001"], "2020-01-02", "2020-01-02", pause=0
        )
    assert _mock_baostock.logout_calls == 1


def test_empty_result_returns_typed_empty_frame(_mock_baostock):
    # Arrange: code with no rows
    _mock_baostock.data_by_code = {"sh.600000": []}

    # Act
    df = ashare_price.fetch_ashare_prices(["sh.600000"], "2020-01-02", "2020-01-02", pause=0)

    # Assert
    assert df.empty
    assert list(df.columns) == ashare_price._COLUMNS
