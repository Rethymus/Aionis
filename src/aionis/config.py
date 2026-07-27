"""Project configuration: symbols, event sources, horizon, model pins, paths.

All experiment-defining constants live here so the pre-registered protocol is in
one auditable place. Override the LLM/market/window values via env or by editing
this module before unblinding test metrics.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Market universe (US sector ETFs + benchmark) ----------------------------
SECTOR_ETFS: tuple[str, ...] = (
    "XLK",  # Technology
    "XLE",  # Energy
    "XLV",  # Health Care
    "XLF",  # Financials
    "XLY",  # Consumer Discretionary
    "XLP",  # Consumer Staples
    "XLI",  # Industrials
    "XLB",  # Materials
    "XLU",  # Utilities
    "XLRE",  # Real Estate
    "XLC",  # Communication Services (inception ~2014-06)
)
BENCHMARK = "SPY"
ALL_SYMBOLS: tuple[str, ...] = SECTOR_ETFS + (BENCHMARK,)

# --- Scheduled macro events (the controlled event set) -----------------------
# FRED release IDs for the scheduled prints we treat as events.
FRED_RELEASES: dict[str, int] = {
    "CPI": 10,  # Consumer Price Index
    "NFP": 50,  # Employment Situation (Nonfarm Payrolls)
}
# FOMC dates come from the Fed's published calendar, not FRED.
ECONOMIC_EVENT_TYPES: tuple[str, ...] = ("FOMC", "CPI", "NFP")

# FOMC statement release time (ET). CPI/NFP release at 08:30 ET (pre-open).
FOMC_RELEASE_TIME_ET = "14:00"
MACRO_PRINT_TIME_ET = "08:30"

# --- Experiment window + horizon ---------------------------------------------
DEFAULT_START = "2010-01-01"
DEFAULT_END = "2025-12-31"

# Headline horizon: h=1 trading session. No label overlap => cleanest statistics.
# h>1 is exploratory (Phase 4) and MUST use purged+embargoed CV.
HORIZON = 1

# --- Model pins (override via env) -------------------------------------------
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL_LOCAL = "BAAI/bge-small-en-v1.5"  # 384-dim, CPU-friendly


class Settings(BaseSettings):
    """Runtime settings, loaded from .env / environment.

    OPENAI_API_KEY and FRED_API_KEY are read with the standard names so they
    also satisfy the underlying SDKs directly. Both are optional at import time;
    a missing key raises a clear error only in the phase that needs it.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Reused as the bearer key for any OpenAI-compatible endpoint (OpenAI, GLM).
    openai_api_key: str | None = None
    fred_api_key: str | None = None
    openai_model: str = DEFAULT_OPENAI_MODEL
    # Additional OpenAI-compatible providers (multi-key policy router).
    modelscope_api_key: str | None = None
    siliconflow_api_key: str | None = None
    # Tiingo: free-tier EOD daily prices for ~30k US stocks + ETFs (covers the
    # cross-section we need when Yahoo/Stooq are IP-blocked). Get a token at
    # tiingo.com, set TIINGO_API_KEY in .env. Polite-only (rate-limit under burst).
    tiingo_api_key: str | None = None
    # Alpaca: independent backup price source on a separate host. Same key/secret
    # authenticates the paper-trading API; we use the market-data endpoint
    # (data.alpaca.markets) for historical adjusted daily bars (US stocks + ETFs).
    # Set ALPACA_KEY_ID / ALPACA_SECRET_KEY in .env.
    alpaca_key_id: str | None = None
    alpaca_secret_key: str | None = None

    # LLM provider for ERL extraction. "glm" routes through the OpenAI-compatible
    # ZhipuAI endpoint via JSON mode (requests-based, no SDK dependency).
    provider: str = "openai"
    llm_base_url: str | None = None
    llm_model: str | None = None  # overrides openai_model when set

    data_dir: Path = Path("data")
    runs_dir: Path = Path("runs")

    def snapshot_path(self, name: str) -> Path:
        return self.data_dir / "snapshots" / name

    def cache_path(self, name: str) -> Path:
        return self.data_dir / "cache" / name

    def ensure_dirs(self) -> None:
        for d in (
            self.data_dir,
            self.runs_dir,
            self.data_dir / "snapshots",
            self.data_dir / "cache",
            self.data_dir / "erl",
        ):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
