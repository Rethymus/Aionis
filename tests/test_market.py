from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from aionis.ingest import market


def _series(symbol: str) -> pd.Series:
    return pd.Series([100.0], index=pd.DatetimeIndex(["2024-01-02"]), name=symbol)


def _set_credentials(monkeypatch: pytest.MonkeyPatch, *, tiingo: bool, alpaca: bool) -> None:
    monkeypatch.setattr(market.settings, "tiingo_api_key", "tiingo-key" if tiingo else None)
    monkeypatch.setattr(market.settings, "alpaca_key_id", "alpaca-id" if alpaca else None)
    monkeypatch.setattr(market.settings, "alpaca_secret_key", "alpaca-secret" if alpaca else None)


def _load_phase_b_fetch():
    script_path = Path(__file__).parents[1] / "scripts" / "phase_b_fetch.py"
    spec = importlib.util.spec_from_file_location("phase_b_fetch", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _configure_phase_b(
    monkeypatch: pytest.MonkeyPatch,
    phase_b_fetch: object,
    cache: Path,
    tickers: list[str],
) -> None:
    cache.mkdir()
    (cache / "phase_b_fundamentals.parquet").touch()
    monkeypatch.setattr(phase_b_fetch, "CACHE", cache)
    monkeypatch.setattr(
        phase_b_fetch,
        "build_oos_resolvable_universe",
        lambda: {"tickers": tickers, "ciks": {}},
    )
    monkeypatch.setattr(phase_b_fetch.settings, "tiingo_api_key", "tiingo-key")
    monkeypatch.setattr(phase_b_fetch.settings, "alpaca_key_id", None)
    monkeypatch.setattr(phase_b_fetch.settings, "alpaca_secret_key", None)


def test_fetch_price_series_fails_closed_without_approved_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_credentials(monkeypatch, tiingo=False, alpaca=False)
    monkeypatch.setattr(
        market, "_from_tiingo", lambda *args, **kwargs: pytest.fail("Tiingo called")
    )
    monkeypatch.setattr(
        market, "_from_alpaca", lambda *args, **kwargs: pytest.fail("Alpaca called")
    )

    error = r"missing symbols: \[AAA, BBB\].*configured providers: none"
    with pytest.raises(RuntimeError, match=error):
        market.fetch_price_series(["AAA", "BBB"], "2024-01-01", "2024-01-31")


def test_fetch_price_series_uses_tiingo_then_alpaca_for_missing_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_credentials(monkeypatch, tiingo=True, alpaca=True)
    calls: list[tuple[str, list[str]]] = []

    def tiingo(symbols: list[str], *args: object) -> dict[str, pd.Series]:
        calls.append(("Tiingo", symbols))
        return {"AAA": _series("AAA")}

    def alpaca(symbols: list[str], *args: object) -> dict[str, pd.Series]:
        calls.append(("Alpaca", symbols))
        return {"BBB": _series("BBB")}

    monkeypatch.setattr(market, "_from_tiingo", tiingo)
    monkeypatch.setattr(market, "_from_alpaca", alpaca)

    result = market.fetch_price_series(["AAA", "BBB"], "2024-01-01", "2024-01-31")

    assert calls == [("Tiingo", ["AAA", "BBB"]), ("Alpaca", ["BBB"])]
    assert list(result) == ["AAA", "BBB"]


def test_fetch_price_series_reports_symbols_missing_from_both_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_credentials(monkeypatch, tiingo=True, alpaca=True)
    monkeypatch.setattr(market, "_from_tiingo", lambda *args, **kwargs: {})
    monkeypatch.setattr(market, "_from_alpaca", lambda *args, **kwargs: {"AAA": _series("AAA")})

    with pytest.raises(
        RuntimeError,
        match=r"missing symbols: \[BBB\].*configured providers: Tiingo, Alpaca",
    ):
        market.fetch_price_series(["AAA", "BBB"], "2024-01-01", "2024-01-31")


def test_phase_b_completeness_guard_runs_before_final_panel_persist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    phase_b_fetch = _load_phase_b_fetch()
    monkeypatch.setattr(phase_b_fetch.settings, "tiingo_api_key", "tiingo-key")
    monkeypatch.setattr(phase_b_fetch.settings, "alpaca_key_id", None)
    monkeypatch.setattr(phase_b_fetch.settings, "alpaca_secret_key", None)

    with pytest.raises(RuntimeError, match=r"missing symbols: \[BBB\].*Tiingo"):
        phase_b_fetch._require_complete_prices(["AAA", "BBB"], {"AAA": _series("AAA")})


def test_phase_b_main_retains_partial_symbol_cache_but_does_not_write_final_panel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    phase_b_fetch = _load_phase_b_fetch()
    cache = tmp_path / "cache"
    _configure_phase_b(monkeypatch, phase_b_fetch, cache, ["AAA", "BBB"])
    monkeypatch.setattr(
        phase_b_fetch,
        "_from_tiingo",
        lambda symbols, *_args: {"AAA": _series("AAA")},
    )

    with pytest.raises(RuntimeError, match=r"missing symbols: \[BBB\]"):
        phase_b_fetch.main()

    assert (cache / "prices" / "AAA.parquet").exists()
    assert not (cache / "prices" / "BBB.parquet").exists()
    assert not (cache / "phase_b_prices.parquet").exists()


@pytest.mark.parametrize(
    "stale_panel",
    [
        pd.DataFrame({"AAA": [1.0]}),
        pd.DataFrame({"AAA": [1.0], "BBB": [float("nan")]}),
    ],
    ids=["missing-requested-column", "requested-column-all-null"],
)
def test_phase_b_main_rebuilds_incomplete_existing_final_panel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stale_panel: pd.DataFrame,
) -> None:
    phase_b_fetch = _load_phase_b_fetch()
    cache = tmp_path / "cache"
    _configure_phase_b(monkeypatch, phase_b_fetch, cache, ["AAA", "BBB"])
    final_path = cache / "phase_b_prices.parquet"
    stale_panel.to_parquet(final_path)
    prices = cache / "prices"
    prices.mkdir()
    for ticker in ("AAA", "BBB"):
        series = _series(ticker)
        pd.DataFrame({"date": series.index, "adjClose": series.to_numpy()}).to_parquet(
            prices / f"{ticker}.parquet"
        )
    monkeypatch.setattr(
        phase_b_fetch,
        "_from_tiingo",
        lambda *_args: pytest.fail("complete symbol caches should avoid provider calls"),
    )

    phase_b_fetch.main()

    rebuilt = pd.read_parquet(final_path)
    assert list(rebuilt.columns) == ["AAA", "BBB"]
    assert rebuilt.notna().any().all()
