"""Phase B results interface — where run artifacts live and how to read/write them.

This is the stable ``预留接口`` (reserved interface) the run script wires into: it
defines a single artifact layout under ``runs/results/<config_sig>/`` so the
dashboard (``dashboard/app.py``) and any future tooling read from one place. The
run script (``scripts/phase_b_run.py``) is left untouched here — the parent wires
:func:`save_run` in as a single call once an arm_state-vs-arm_base OOS run lands.

Reuses, not hand-rolls:
  * ``pandas`` + ``pyarrow`` (already deps) for parquet round-trips of the IC
    series — the same wheels the eval pipeline uses.
  * the *layout pattern* of ``mlflow`` (Apache-2.0, verified): one directory per
    run, keyed by a config signature, holding param/meta JSON + binary artifacts.
    We do not depend on mlflow; the ledger already plays the role of the poor-
    man's tracking store.

Artifact layout (``runs/results/<config_sig>/``)::

    ic_state.parquet      monthly rank-IC series, arm_state (filed)   [Series, idx=date]
    ic_base.parquet       monthly rank-IC series, arm_base (end+lag)  [Series, idx=date]
    summary_state.json    rank_ic_summary(ic_state)  — mean_ic, t_hac, ci_half, n
    summary_base.json     rank_ic_summary(ic_base)
    differential.json     arm_state - arm_base differential + CI (pre-reg §1/§7)
    controls.json         lag_shift + placebo control differentials (pre-reg §5)
    config.json           the frozen config that produced this run
    meta.json             ts, config_sig, h6_deterministic, aionis version, schema

Optional (schema 2; written only when the run supplies them — dashboard v2 reads
them for fit-scatter / quantile / turnover charts)::

    oos_state.parquet     per-ticker OOS score panel (treatment) [date, ticker, score, y_fwd_ret]
    oos_base.parquet      per-ticker OOS score panel (base)      [date, ticker, score, y_fwd_ret]
    ls_returns.parquet    monthly long-short return series       [Series, idx=date]

The publishability gate (pre-reg §7) is a 95% CI half-width < 0.015; the
dashboard draws that as a horizontal band — see ``dashboard/app.py``.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import structlog

log = structlog.get_logger()

# ``src/aionis/reporting/results.py`` -> project root is three parents up.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNS_DIR = _PROJECT_ROOT / "runs"
DEFAULT_RESULTS_DIR = DEFAULT_RUNS_DIR / "results"
DEFAULT_LEDGER = DEFAULT_RUNS_DIR / "ledger.jsonl"

_IC_COL = "ic"  # parquet column name for the rank-IC series


# ----------------------------------------------------------------------------
# path helpers
# ----------------------------------------------------------------------------


def results_dir(base: Path | str | None = None) -> Path:
    """Root directory of all run artifacts (``runs/results`` by default).

    ``base`` overrides the project ``runs`` dir for hermetic tests / alt roots.
    """
    if base is not None:
        return Path(base) / "results"
    return DEFAULT_RESULTS_DIR


def run_dir(config_sig: str, base: Path | str | None = None) -> Path:
    """Per-run artifact directory ``<results>/results/<config_sig>/``."""
    if not config_sig or not isinstance(config_sig, str):
        raise ValueError(f"config_sig must be a non-empty string, got {config_sig!r}.")
    # sanitize: keep it filesystem-safe (config signatures are hex hashes, but
    # be defensive against a caller passing a free-form sig).
    safe = "".join(c for c in config_sig if c.isalnum() or c in "-_") or "unknown"
    return results_dir(base) / safe


def _write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_ic(path: Path, ic: pd.Series) -> None:
    """Persist a rank-IC series as parquet, preserving the date index."""
    if not isinstance(ic, pd.Series):
        raise TypeError(f"ic must be a pandas Series, got {type(ic).__name__}.")
    frame = ic.rename(_IC_COL).to_frame()
    # keep the index name round-trippable (rank_ic_monthly returns month-end dates)
    if frame.index.name is None:
        frame.index.name = "date"
    frame.to_parquet(path)


def _read_ic(path: Path) -> pd.Series:
    frame = pd.read_parquet(path)
    return frame[_IC_COL].rename(None)


# ----------------------------------------------------------------------------
# save / load — the stable interface the run script wires in
# ----------------------------------------------------------------------------


def save_run(
    config_sig: str,
    *,
    ic_state: pd.Series,
    ic_base: pd.Series,
    summary_state: dict,
    summary_base: dict,
    differential: dict,
    controls: dict,
    config: dict,
    h6_deterministic: bool,
    base: Path | str | None = None,
    oos_state: pd.DataFrame | None = None,
    oos_base: pd.DataFrame | None = None,
    ls_returns: pd.Series | None = None,
) -> Path:
    """Persist ONE Phase B run to ``runs/results/<config_sig>/`` and return that dir.

    Args:
        config_sig: the frozen-config signature (matches ``ledger.jsonl`` rows).
        ic_state / ic_base: monthly rank-IC series for arm_state (filed) and
            arm_base (period-end+lag) — the output of ``eval.rank_ic``.
        summary_state / summary_base: ``rank_ic_summary`` dicts (mean_ic, ci_half, ...).
        differential: the arm_state - arm_base differential with CI
            (``mean_diff``, ``ci_lo``, ``ci_hi``, ``n``, ...).
        controls: ``{lag_shift: {...}, placebo: {...}}`` control differentials
            (pre-reg §5). Each carries its own ``mean_diff`` + CI.
        config: the frozen config that produced this run.
        h6_deterministic: the Phase-B determinism flag (bit-identical re-run).
        base: override the ``runs`` dir (hermetic tests).
        oos_state / oos_base: OPTIONAL per-ticker OOS score panels
            ``[date, ticker, score, y_fwd_ret]`` for the treatment / base arms.
            Persisted as ``oos_state.parquet`` / ``oos_base.parquet`` when not None
            (schema 2); dashboard v2 renders fit-scatter / quantile / turnover from
            them. Omitting them leaves the run dir unchanged (schema-1 callers).
        ls_returns: OPTIONAL monthly long-short return series; persisted as
            ``ls_returns.parquet`` when not None.

    The ``config_sig`` (and thus the run's directory) depends ONLY on ``config``;
    these optional panels are additive artifacts and never feed the config sha256.
    """
    d = run_dir(config_sig, base)
    d.mkdir(parents=True, exist_ok=True)
    _write_ic(d / "ic_state.parquet", ic_state)
    _write_ic(d / "ic_base.parquet", ic_base)
    _write_json(d / "summary_state.json", summary_state)
    _write_json(d / "summary_base.json", summary_base)
    _write_json(d / "differential.json", differential)
    _write_json(d / "controls.json", controls)
    _write_json(d / "config.json", config)
    # schema-2 additive artifacts (dashboard v2 score panels); written only when
    # the run supplies them, so schema-1 callers leave the dir untouched.
    if oos_state is not None:
        oos_state.to_parquet(d / "oos_state.parquet")
    if oos_base is not None:
        oos_base.to_parquet(d / "oos_base.parquet")
    if ls_returns is not None:
        _write_ic(d / "ls_returns.parquet", ls_returns)
    _write_json(
        d / "meta.json",
        {
            "ts": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "config_sig": config_sig,
            "h6_deterministic": bool(h6_deterministic),
            "aionis_version": _project_version(),
            "schema": 2,
        },
    )
    log.info(
        "results_saved",
        config_sig=config_sig,
        n_ic_state=len(ic_state),
        n_ic_base=len(ic_base),
        dir=str(d),
    )
    return d


def load_run(config_sig: str, base: Path | str | None = None) -> dict:
    """Inverse of :func:`save_run` — load all artifacts for one run.

    Returns a dict with keys: ``config_sig``, ``ts``, ``h6_deterministic``,
    ``ic_state``, ``ic_base``, ``summary_state``, ``summary_base``,
    ``differential``, ``controls``, ``config``, plus the schema-2 additive
    panels ``oos_state`` / ``oos_base`` / ``ls_returns`` — which are ``None`` when
    the run predates schema 2 (or simply did not supply them), so old runs degrade
    gracefully. Raises ``FileNotFoundError`` if the run directory or its
    ``meta.json`` is absent.
    """
    d = run_dir(config_sig, base)
    meta_path = d / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No Phase B results at {d} (missing meta.json).")
    meta = _read_json(meta_path)
    oos_state_path = d / "oos_state.parquet"
    oos_base_path = d / "oos_base.parquet"
    ls_returns_path = d / "ls_returns.parquet"
    return {
        "config_sig": config_sig,
        "ts": meta.get("ts"),
        "h6_deterministic": bool(meta.get("h6_deterministic", False)),
        "ic_state": _read_ic(d / "ic_state.parquet"),
        "ic_base": _read_ic(d / "ic_base.parquet"),
        "summary_state": _read_json(d / "summary_state.json"),
        "summary_base": _read_json(d / "summary_base.json"),
        "differential": _read_json(d / "differential.json"),
        "controls": _read_json(d / "controls.json"),
        "config": _read_json(d / "config.json"),
        "oos_state": pd.read_parquet(oos_state_path) if oos_state_path.exists() else None,
        "oos_base": pd.read_parquet(oos_base_path) if oos_base_path.exists() else None,
        "ls_returns": _read_ic(ls_returns_path) if ls_returns_path.exists() else None,
    }


# ----------------------------------------------------------------------------
# list_runs — scan results dirs + reconcile with the ledger
# ----------------------------------------------------------------------------


def read_ledger(ledger: Path | str | None = None) -> list[dict]:
    """Read ``runs/ledger.jsonl`` defensively (read-only; skips malformed lines).

    The ledger is heterogeneous: early Phase A rows carry ``config_sig`` +
    ``results`` arrays; Phase B rows carry typed ``event`` keys. Callers branch
    on the presence of ``event`` vs ``config_sig``.
    """
    path = Path(ledger) if ledger is not None else DEFAULT_LEDGER
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            # append-only ledger: never let one bad row abort the scan.
            log.warning("ledger_skip_malformed_line", ledger=str(path))
    return rows


def list_runs(
    base: Path | str | None = None,
    ledger: Path | str | None = None,
) -> list[dict]:
    """One summary dict per Phase B result dir, enriched with ledger reconciliation.

    Each entry: ``config_sig``, ``ts`` (artifact ts), ``h6_deterministic``,
    ``mean_diff`` / ``ci_lo`` / ``ci_hi`` / ``n`` (from ``differential.json``),
    ``n_ic_state`` (months of IC), and ``ledger`` (``{"n_entries", "latest_ts",
    "latest_event"}`` or ``None`` if the sig is absent from the ledger).

    Sorted newest-first by artifact ``ts``.
    """
    root = results_dir(base)
    if not root.exists():
        return []
    # index ledger rows by config_sig (only rows that carry one).
    ledger_rows = read_ledger(ledger)
    by_sig: dict[str, list[dict]] = {}
    for row in ledger_rows:
        sig = row.get("config_sig")
        if sig:
            by_sig.setdefault(sig, []).append(row)

    out: list[dict] = []
    for d in sorted(root.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta_path = d / "meta.json"
        if not meta_path.exists():
            continue
        meta = _read_json(meta_path)
        diff = _read_json(d / "differential.json") if (d / "differential.json").exists() else {}
        ic_state_path = d / "ic_state.parquet"
        n_ic = 0
        if ic_state_path.exists():
            try:
                n_ic = len(_read_ic(ic_state_path))
            except Exception:  # noqa: BLE001 — corrupt artifact must not abort the scan
                n_ic = 0
        sig = meta.get("config_sig", d.name)
        entries = by_sig.get(sig, [])
        ledger_info = None
        if entries:
            latest = max(entries, key=lambda r: r.get("ts", ""))
            ledger_info = {
                "n_entries": len(entries),
                "latest_ts": latest.get("ts"),
                "latest_event": latest.get("event"),
            }
        out.append(
            {
                "config_sig": sig,
                "ts": meta.get("ts"),
                "h6_deterministic": bool(meta.get("h6_deterministic", False)),
                "mean_diff": diff.get("mean_diff"),
                "ci_lo": diff.get("ci_lo"),
                "ci_hi": diff.get("ci_hi"),
                "n": diff.get("n"),
                "n_ic_state": n_ic,
                "ledger": ledger_info,
            }
        )
    out.sort(key=lambda r: r.get("ts") or "", reverse=True)
    return out


# ----------------------------------------------------------------------------
# internals + tiny self-test
# ----------------------------------------------------------------------------


def _project_version() -> str:
    try:
        from importlib.metadata import version

        return version("aionis")
    except Exception:  # noqa: BLE001 — version is informational only
        return "0.0.0+local"


def self_test(base: Path | str | None = None) -> dict:
    """Round-trip a synthetic run through save/load/list (hermetic if ``base`` set).

    Run as ``uv run python -m aionis.reporting.results``. Returns the loaded dict
    so callers can assert on it; prints a one-line summary.
    """
    import numpy as np

    rng = np.random.default_rng(0)
    months = pd.date_range("2017-01-31", periods=24, freq="ME")
    ic_state = pd.Series(rng.normal(0.02, 0.05, len(months)), index=months, name="ic")
    ic_state.index.name = "date"
    ic_base = pd.Series(rng.normal(0.005, 0.05, len(months)), index=months, name="ic")
    ic_base.index.name = "date"
    sig = "selftest0001"
    save_run(
        sig,
        ic_state=ic_state,
        ic_base=ic_base,
        summary_state={"mean_ic": float(ic_state.mean()), "ci_half": 0.014, "n": 24},
        summary_base={"mean_ic": float(ic_base.mean()), "ci_half": 0.020, "n": 24},
        differential={"mean_diff": 0.015, "ci_lo": -0.002, "ci_hi": 0.032, "n": 24},
        controls={"lag_shift": {"mean_diff": 0.001}, "placebo": {"mean_diff": 0.0}},
        config={"horizon_sessions": 21, "note": "self_test synthetic"},
        h6_deterministic=True,
        base=base,
    )
    loaded = load_run(sig, base=base)
    runs = list_runs(base=base)
    print(
        f"[self_test] saved+loaded sig={sig}; "
        f"mean_diff={loaded['differential']['mean_diff']:.4f}; "
        f"list_runs={len(runs)} entry(ies)"
    )
    return loaded


if __name__ == "__main__":  # pragma: no cover — manual smoke
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        self_test(tmp)
