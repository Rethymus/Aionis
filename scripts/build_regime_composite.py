"""Build the regime_state composite (macro + global layers; meso deferred) + TACO normalize.

Loads the two cached regime layers, z-scores each (past-only), equal-weights, and applies
TACO expanding-as-of σ normalization -> the daily regime_state series. EXPLORATORY (2-layer;
meso/shenwan deferred). Writes data/cache/regime_composite.parquet (gitignored); NEVER ledger.

Run: uv run python scripts/build_regime_composite.py
"""

from __future__ import annotations

import hashlib
import os

import pandas as pd

from aionis.config import settings
from aionis.features.regime_composite import regime_composite

CACHE = settings.data_dir / "cache"
MACRO_PATH = CACHE / "regime_macro.parquet"
GLOBAL_PATH = CACHE / "regime_global_dy.parquet"
MESO_PATH = CACHE / "regime_meso.parquet"
OUT_PATH = CACHE / "regime_composite.parquet"


def _load_date_indexed(path: str | os.PathLike, value_col: str) -> pd.Series:
    """Load a cached regime layer as a date-indexed Series (handle date-as-column or index)."""
    df = pd.read_parquet(path)
    if "date" in df.columns:
        s = pd.Series(df[value_col].to_numpy(), index=pd.to_datetime(df["date"]))
    else:
        # date is the index (e.g. the global layer was saved with a DatetimeIndex).
        s = pd.Series(df[value_col].to_numpy(), index=pd.to_datetime(df.index))
    s.name = value_col
    return s


def main() -> None:
    if not MACRO_PATH.exists():
        raise SystemExit(
            f"[ERROR] {MACRO_PATH} missing — run scripts/build_regime_macro.py first."
        )
    if not GLOBAL_PATH.exists():
        raise SystemExit(
            f"[ERROR] {GLOBAL_PATH} missing — run scripts/build_regime_global.py first."
        )

    macro = _load_date_indexed(MACRO_PATH, "macro_regime")
    glob = _load_date_indexed(GLOBAL_PATH, "total_spillover")
    layers = {"macro": macro, "global": glob}
    if MESO_PATH.exists():
        meso = _load_date_indexed(MESO_PATH, "meso_regime")
        layers["meso"] = meso
        print(f"[S] meso: n={len(meso)} ({meso.index.min()}..{meso.index.max()})", flush=True)
    else:
        print("[S] meso: NOT FOUND -> 2-layer composite (macro+global)", flush=True)
    print(
        f"[S] macro: n={len(macro)} ({macro.index.min()}..{macro.index.max()}) | "
        f"global: n={len(glob)} ({glob.index.min()}..{glob.index.max()})",
        flush=True,
    )

    # 3-layer composite when meso present (else 2-layer). Equal-weight z-scored + TACO.
    regime = regime_composite(layers)
    print(
        f"[S] regime_state: n={len(regime)} | valid={int(regime.notna().sum())} | "
        f"range {regime.index.min()}..{regime.index.max()}",
        flush=True,
    )
    if regime.notna().sum():
        print(
            f"[S]   mean={regime.mean():.4f} std={regime.std():.4f} "
            f"min={regime.min():.4f} max={regime.max():.4f}",
            flush=True,
        )

    out = regime.to_frame(name="regime_state")
    out.index.name = "date"
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT_PATH)
    sha = hashlib.sha256(OUT_PATH.read_bytes()).hexdigest()
    print(
        f"[S] wrote {OUT_PATH} | file sha256={sha[:16]} | "
        f"MB={OUT_PATH.stat().st_size / 1e6:.2f}",
        flush=True,
    )
    print(
        "[S] CAVEAT: composite includes meso=US-only (CN shenwan fetch deferred) -> the "
        "meso layer is partial. Confirmatory Track C claim needs full US+CN meso + new ledger row.",
        flush=True,
    )


if __name__ == "__main__":
    main()
