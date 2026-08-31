"""Health check probe compliance tests (TDD).

Asserts that only approved data sources are probed, per CLAUDE.md constraints.
Tests are hermetic — no network calls (all requests mocked).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

# Blocked sources that must NOT appear in health_check probe list
BLOCKED_SOURCES = [
    "akshare",  # blocked: not in approved sources list
    "EastMoney",  # blocked: not in approved sources list
    "yfinance",  # blocked: IP-blocked per CLAUDE.md
    "Yahoo",  # blocked: IP-blocked per CLAUDE.md
    "Stooq",  # blocked: per CLAUDE.md
    "BLS",  # blocked: per CLAUDE.md
]

# Approved sources that MUST remain
APPROVED_HTTP_SOURCES = [
    "EDGAR",  # approved
    "FRED",  # approved
    "GitHub",  # approved (raw-redirect)
    "Tiingo",  # approved (prices)
    "Alpaca",  # approved (prices backup)
]


class TestHealthCheckProbes:
    def test_script_contains_no_blocked_source_references(self) -> None:
        """The executable health-check surface must not reference blocked sources."""
        script = (Path(__file__).parents[1] / "scripts" / "health_check.py").read_text()
        for blocked in BLOCKED_SOURCES:
            assert blocked.lower() not in script.lower(), (
                f"Blocked source '{blocked}' referenced in scripts/health_check.py"
            )

    def test_data_sources_contains_no_blocked_entries(self) -> None:
        """DATA_SOURCES list must not contain blocked sources like akshare/EastMoney."""
        from scripts.health_check import DATA_SOURCES

        source_names = [name for name, _, _ in DATA_SOURCES]

        for blocked in BLOCKED_SOURCES:
            assert not any(
                blocked.lower() in name.lower() for name in source_names
            ), f"Blocked source '{blocked}' found in DATA_SOURCES: {source_names}"

    def test_approved_sources_present(self) -> None:
        """All approved sources must be present in health check."""
        from scripts.health_check import DATA_SOURCES

        source_names = [name for name, _, _ in DATA_SOURCES]

        # Must have EDGAR, FRED, and GitHub raw
        assert any("EDGAR" in name for name in source_names), \
            "EDGAR missing from DATA_SOURCES"
        assert any("FRED" in name for name in source_names), \
            "FRED missing from DATA_SOURCES"
        assert any("GitHub" in name for name in source_names), \
            "GitHub raw-redirect missing from DATA_SOURCES"

    def test_no_http_policy_import(self) -> None:
        """health_check must stay standalone (no http_policy integration)."""
        import scripts.health_check as hc_module

        # Verify the module does not import http_policy
        assert "http_policy" not in dir(hc_module), \
            "health_check should NOT import http_policy (must stay standalone)"

    @patch("scripts.health_check.requests.get")
    def test_gap_enforcement(self, mock_get: patch) -> None:
        """Verify polite gap enforcement exists (MIN_GAP_S + _gap function)."""
        from scripts.health_check import MIN_GAP_S, _gap

        # Must have at least 2.0s polite floor
        assert MIN_GAP_S >= 2.0, f"MIN_GAP_S={MIN_GAP_S} < 2.0s politeness floor"

        # _gap function must be defined
        assert callable(_gap), "_gap() function must exist for rate limiting"

    def test_wheel_repos_no_blocked_sources(self) -> None:
        """WHEEL_REPOS must not reference blocked data source repos."""
        from scripts.health_check import WHEEL_REPOS

        for repo in WHEEL_REPOS:
            # akfamily/akshare is blocked but was in WHEEL_REPOS
            assert repo != "akfamily/akshare", \
                "Blocked repo 'akfamily/akshare' found in WHEEL_REPOS"

    def test_health_check_standalone_design(self) -> None:
        """Verify health_check has its own timing/retry (standalone from http_policy)."""
        from scripts.health_check import (
            DATA_SOURCES,
            WHEEL_REPOS,
            probe_alpaca,
            probe_http,
            probe_tiingo,
        )

        # Must have its own probe functions (not delegating to shared policy)
        assert callable(probe_http), "probe_http() must exist"
        assert callable(probe_tiingo), "probe_tiingo() must exist"
        assert callable(probe_alpaca), "probe_alpaca() must exist"

        # Must have data sources and wheel repos defined
        assert len(DATA_SOURCES) >= 3, "Must have at least 3 approved data sources"
        assert len(WHEEL_REPOS) >= 10, "Must have wheel repos defined"
