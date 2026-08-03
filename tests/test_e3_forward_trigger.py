"""Tests for E3 Slice 6 - NYSE month-end scheduler trigger.

Hermetic tests using synthetic calendars/dates where possible. Month-end
detection uses the real pandas_market_calendars XNYS calendar for correctness
verification against known months.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from aionis.eval.forward_live_readiness import (
    MembershipFreshnessContract,
    ProviderCutoffPolicy,
)
from scripts.e3_forward_trigger import (
    _get_nyse_month_end_session,
    _is_month_end_session,
    _load_contracts,
    main,
)


class TestNYSEMonthEndDetection:
    """Test month-end session detection using real XNYS calendar."""

    def test_january_2026_month_end(self):
        """January 2026: last trading day is Jan 30 (Friday)."""
        # Jan 30, 2026 is a Friday - should be month-end
        jan_30 = pd.Timestamp("2026-01-30").normalize()
        assert _is_month_end_session(jan_30) is True

        # Jan 31 is a Saturday - not a trading day
        jan_31 = pd.Timestamp("2026-01-31").normalize()
        assert _is_month_end_session(jan_31) is False

    def test_february_2026_month_end(self):
        """February 2026: last trading day is Feb 27 (Friday)."""
        # Feb 27, 2026 is a Friday - should be month-end
        feb_27 = pd.Timestamp("2026-02-27").normalize()
        assert _is_month_end_session(feb_27) is True

        # Feb 28 is a Saturday - not a trading day
        feb_28 = pd.Timestamp("2026-02-28").normalize()
        assert _is_month_end_session(feb_28) is False

    def test_march_2026_month_end(self):
        """March 2026: last trading day is Mar 31 (Tuesday)."""
        mar_31 = pd.Timestamp("2026-03-31").normalize()
        assert _is_month_end_session(mar_31) is True

    def test_get_month_end_session_for_known_months(self):
        """Verify _get_nyse_month_end_session returns correct session."""
        # January 2026: Jan 30 (Friday)
        jan_result = _get_nyse_month_end_session(pd.Timestamp("2026-01-15"))
        assert jan_result == pd.Timestamp("2026-01-30").normalize()

        # February 2026: Feb 27 (Friday)
        feb_result = _get_nyse_month_end_session(pd.Timestamp("2026-02-15"))
        assert feb_result == pd.Timestamp("2026-02-27").normalize()

        # March 2026: Mar 31 (Tuesday)
        mar_result = _get_nyse_month_end_session(pd.Timestamp("2026-03-15"))
        assert mar_result == pd.Timestamp("2026-03-31").normalize()

    def test_mid_month_is_not_month_end(self):
        """Mid-month dates should not be month-end."""
        jan_15 = pd.Timestamp("2026-01-15").normalize()
        assert _is_month_end_session(jan_15) is False

        feb_15 = pd.Timestamp("2026-02-15").normalize()
        assert _is_month_end_session(feb_15) is False


class TestContractConfig:
    """Test contract config loading and proposed values."""

    def test_load_contracts_from_valid_config(self):
        """Load contracts from a valid config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
membership_freshness_contract:
  max_age_sessions: 22
  authoritative_refresh: null

provider_cutoff_policy:
  block_on_unknown: true
""")
            config_path = Path(f.name)

        try:
            membership, provider = _load_contracts(config_path)

            assert isinstance(membership, MembershipFreshnessContract)
            assert membership.max_age_sessions == 22
            assert membership.authoritative_refresh is None

            assert isinstance(provider, ProviderCutoffPolicy)
            assert provider.block_on_unknown is True
        finally:
            config_path.unlink()

    def test_load_contracts_missing_required_field(self):
        """Fail when max_age_sessions is missing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
membership_freshness_contract:
  authoritative_refresh: null

provider_cutoff_policy:
  block_on_unknown: true
""")
            config_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="max_age_sessions is required"):
                _load_contracts(config_path)
        finally:
            config_path.unlink()

    def test_load_contracts_missing_config_file(self):
        """Fail when config file does not exist."""
        config_path = Path("/nonexistent/config.yaml")

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            _load_contracts(config_path)


class TestTriggerMain:
    """Test the main trigger logic."""

    def test_no_op_when_not_month_end(self):
        """Trigger should no-op (return early) when not month-end."""
        # Jan 15 is not month-end
        jan_15 = pd.Timestamp("2026-01-15").normalize()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "contracts.yaml"
            # Write a valid config
            config_path.write_text("""
membership_freshness_contract:
  max_age_sessions: 22
provider_cutoff_policy:
  block_on_unknown: true
""")

            result = main(
                run_date=jan_15,
                config_path=config_path,
                cache_dir=Path(tmpdir) / "cache",
                runs_dir=Path(tmpdir) / "runs",
            )

            # Should return early without calling forward_commit_runner
            assert result == {"committed": False, "is_month_end": False}

    @patch.dict(os.environ, {"PHASE_E3_NO_LEDGER": "1"})
    @patch("scripts.e3_forward_trigger.forward_commit_main")
    def test_shadow_mode_no_ledger_writes(self, mock_forward_main):
        """In shadow mode, forward_commit_main is called but no ledger writes."""
        mock_forward_main.return_value = {"committed": True, "config_sha256": "abc123"}

        # Jan 30, 2026 IS month-end
        jan_30 = pd.Timestamp("2026-01-30").normalize()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "contracts.yaml"
            config_path.write_text("""
membership_freshness_contract:
  max_age_sessions: 22
provider_cutoff_policy:
  block_on_unknown: true
""")

            result = main(
                run_date=jan_30,
                config_path=config_path,
                cache_dir=Path(tmpdir) / "cache",
                runs_dir=Path(tmpdir) / "runs",
            )

            # Verify forward_commit_main was called with correct arguments
            mock_forward_main.assert_called_once()
            call_kwargs = mock_forward_main.call_args.kwargs
            assert call_kwargs["enforce_live_readiness"] is True
            assert call_kwargs["membership_freshness_contract"].max_age_sessions == 22
            assert call_kwargs["provider_cutoff_policy"].block_on_unknown is True

            # Verify result
            assert result["committed"] is True
            assert result["config_sha256"] == "abc123"

    @patch.dict(os.environ, {"PHASE_E3_NO_LEDGER": "1"})
    @patch("scripts.e3_forward_trigger.forward_commit_main")
    def test_contracts_fail_closed_when_missing(self, mock_forward_main):
        """Trigger fails closed when contracts config is missing."""
        jan_30 = pd.Timestamp("2026-01-30").normalize()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.yaml"

            result = main(
                run_date=jan_30,
                config_path=config_path,
                cache_dir=Path(tmpdir) / "cache",
                runs_dir=Path(tmpdir) / "runs",
            )

            # Should not call forward_commit_main
            mock_forward_main.assert_not_called()

            # Should return error
            assert result["committed"] is False
            assert result["contracts_missing"] is True
            assert "error" in result

    @patch.dict(os.environ, {"PHASE_E3_NO_LEDGER": "1"})
    @patch("scripts.e3_forward_trigger.forward_commit_main")
    def test_readiness_gate_blocks_commit(self, mock_forward_main):
        """When readiness gate fails, commit is not performed."""
        # Simulate readiness failure
        mock_forward_main.return_value = {
            "committed": False,
            "readiness_failed": True,
            "reason_code": "membership_freshness_contract_violated",
            "manifest": {},
        }

        jan_30 = pd.Timestamp("2026-01-30").normalize()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "contracts.yaml"
            config_path.write_text("""
membership_freshness_contract:
  max_age_sessions: 22
provider_cutoff_policy:
  block_on_unknown: true
""")

            result = main(
                run_date=jan_30,
                config_path=config_path,
                cache_dir=Path(tmpdir) / "cache",
                runs_dir=Path(tmpdir) / "runs",
            )

            # forward_commit_main was called but readiness blocked it
            mock_forward_main.assert_called_once()
            assert result["committed"] is False
            assert result["readiness_failed"] is True
            assert result["reason_code"] == "membership_freshness_contract_violated"


class TestFrozenContractValues:
    """Test that the frozen config values are present and marked."""

    def test_config_has_frozen_marker(self):
        """Verify the actual config file is marked FROZEN (owner ratified)."""
        config_path = Path("config/e3_live_contracts.yaml")
        if not config_path.exists():
            pytest.skip("Config file not found (not created yet)")

        content = config_path.read_text()

        # Should be marked FROZEN (owner ratified 2026-08-03, D2)
        assert "FROZEN" in content
        assert "owner ratified" in content.lower()

    def test_config_has_required_contracts(self):
        """Verify the actual config has both required contracts."""
        config_path = Path("config/e3_live_contracts.yaml")
        if not config_path.exists():
            pytest.skip("Config file not found (not created yet)")

        contracts = _load_contracts(config_path)

        # Verify both contracts are present
        assert isinstance(contracts[0], MembershipFreshnessContract)
        assert isinstance(contracts[1], ProviderCutoffPolicy)

        # Verify frozen values
        assert contracts[0].max_age_sessions == 22
        assert contracts[1].block_on_unknown is True
