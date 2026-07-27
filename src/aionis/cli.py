"""Aionis CLI. Subcommands are wired as their phase is implemented."""

from __future__ import annotations

import argparse
import sys

import pandas as pd
import structlog

from aionis import __version__
from aionis.config import ALL_SYMBOLS, DEFAULT_END, DEFAULT_START, SECTOR_ETFS, settings

log = structlog.get_logger()


def _cmd_ingest(args: argparse.Namespace) -> int:
    from aionis.features.alignment import nyse_sessions
    from aionis.ingest.events import fetch_events, load_events_csv
    from aionis.ingest.market import fetch_prices, save_snapshot

    settings.ensure_dirs()
    symbols = args.symbols.split(",") if args.symbols else list(ALL_SYMBOLS)
    sessions = nyse_sessions(args.start, args.end)

    log.info("ingest_market", symbols=symbols, start=args.start, end=args.end)
    prices = fetch_prices(symbols, args.start, args.end, expected_sessions=sessions)
    price_path = settings.snapshot_path(f"prices_{args.start}_{args.end}.parquet")
    save_snapshot(prices, price_path)

    if args.events_csv:
        log.info("ingest_events_csv", path=args.events_csv)
        events = load_events_csv(args.events_csv)
    else:
        log.info("ingest_events", types=args.event_types)
        events = fetch_events(args.start, args.end, settings.fred_api_key, args.event_types)

    event_path = settings.snapshot_path(f"events_{args.start}_{args.end}.parquet")
    save_snapshot(events, event_path)
    log.info("ingest_done", prices=str(price_path), events=str(event_path), n_events=len(events))
    return 0


def _build_dm_from_snapshot(args: argparse.Namespace):
    from aionis.features.design_matrix import build_design_matrix
    from aionis.ingest.market import load_snapshot

    prices = load_snapshot(settings.snapshot_path(f"prices_{args.start}_{args.end}.parquet"))
    events = load_snapshot(settings.snapshot_path(f"events_{args.start}_{args.end}.parquet"))
    sessions = pd.DatetimeIndex(prices.index)
    symbols = [s for s in SECTOR_ETFS if s in prices.columns]
    dm = build_design_matrix(events, prices, sessions, symbols, horizon=args.horizon)
    return dm, symbols


def _build_synthetic_dm(args: argparse.Namespace):
    from aionis.features.alignment import nyse_sessions
    from aionis.features.design_matrix import build_design_matrix
    from aionis.synthetic import make_synthetic_events, make_synthetic_prices

    sessions = nyse_sessions(args.start, args.end)
    symbols = list(SECTOR_ETFS)
    prices = make_synthetic_prices(sessions, symbols + ["SPY"], seed=11)
    events = make_synthetic_events(sessions, n=args.synthetic_events, seed=23)
    dm = build_design_matrix(events, prices, sessions, symbols, horizon=args.horizon)
    return dm, symbols


def _cmd_eval_priceonly(args: argparse.Namespace) -> int:
    from aionis.eval.evaluate import cross_validate
    from aionis.models.baselines import BASELINES
    from aionis.models.learners import LEARNERS

    dm, symbols = _build_synthetic_dm(args) if args.synthetic else _build_dm_from_snapshot(args)
    log.info(
        "design_matrix", rows=len(dm), events=dm.n_events, symbols=symbols, horizon=args.horizon
    )

    models = {**BASELINES, **LEARNERS}
    result = cross_validate(dm, models, n_splits=args.n_splits, horizon=args.horizon)
    result.metrics["up_baseline"] = result.metrics["up_baseline"].iloc[0]
    print("\n=== Phase 1: price-only + naive baselines (the number ERL must beat) ===")
    print(result.metrics.round(4).to_string())
    print(f"\nOOS samples: {len(result.oos)} | events: {dm.n_events}")
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    from aionis.extraction.extract import erls_to_records, extract_erls
    from aionis.extraction.llm_client import make_llm_client
    from aionis.features.alignment import nyse_sessions
    from aionis.ingest.event_text import fetch_event_text
    from aionis.ingest.market import load_snapshot
    from aionis.synthetic import make_synthetic_event_text, make_synthetic_events

    settings.ensure_dirs()
    cache_dir = settings.data_dir / "erl"

    if args.synthetic:
        sessions = nyse_sessions(args.start, args.end)
        events = make_synthetic_events(sessions, n=args.synthetic_events, seed=23)
        text_df = make_synthetic_event_text(events, seed=9)
    else:
        events = load_snapshot(settings.snapshot_path(f"events_{args.start}_{args.end}.parquet"))
        text_df = fetch_event_text(events)

    client = make_llm_client(provider=args.provider, mock=args.mock)
    erls = extract_erls(events, text_df, client, cache_dir)
    records = erls_to_records(erls)
    out_path = settings.snapshot_path(f"erl_{args.start}_{args.end}.parquet")
    records.to_parquet(out_path)
    log.info(
        "extract_saved",
        path=str(out_path),
        n=len(records),
        mock=args.mock,
        synthetic=args.synthetic,
    )
    if args.show and len(records):
        print(
            records[["event_id", "event_type", "action", "temporal", "uncertainty"]]
            .head(20)
            .to_string()
        )
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    from aionis.eval.compare import compare_treatment, format_table
    from aionis.eval.controls import make_neutral_erls, shuffled_vectors
    from aionis.extraction.extract import extract_erls, load_erl_cache
    from aionis.extraction.llm_client import make_llm_client
    from aionis.features.alignment import nyse_sessions
    from aionis.features.design_matrix import build_design_matrix
    from aionis.features.event_vector import build_event_vectors, make_embedder
    from aionis.ingest.market import load_snapshot
    from aionis.models.learners import LEARNERS
    from aionis.reporting.run_log import log_run
    from aionis.synthetic import (
        make_synthetic_event_text,
        make_synthetic_events,
        make_synthetic_prices,
    )

    settings.ensure_dirs()
    embargo = pd.Timedelta(days=max(1, args.horizon))
    embedder = make_embedder(provider=args.embedder)

    if args.synthetic:
        sessions = nyse_sessions(args.start, args.end)
        symbols = list(SECTOR_ETFS)
        prices = make_synthetic_prices(sessions, symbols + ["SPY"], seed=11)
        events = make_synthetic_events(sessions, n=args.synthetic_events, seed=23)
        text_df = make_synthetic_event_text(events, seed=9)
        client = make_llm_client(mock=True)
        erls = extract_erls(events, text_df, client, settings.data_dir / "erl")
    else:
        prices = load_snapshot(settings.snapshot_path(f"prices_{args.start}_{args.end}.parquet"))
        events = load_snapshot(settings.snapshot_path(f"events_{args.start}_{args.end}.parquet"))
        sessions = pd.DatetimeIndex(prices.index)
        symbols = [s for s in SECTOR_ETFS if s in prices.columns]
        erls = load_erl_cache(settings.data_dir / "erl")
        if not erls:
            raise RuntimeError("no cached ERLs; run `aionis extract` first")

    # Restrict to events that actually have a cached ERL so price-only and all
    # treatment matrices share the SAME event set (prevents an asymmetric row
    # drop from confounding the with-vs-without ablation).
    before = events["event_id"].nunique()
    events = events[events["event_id"].isin(erls)].reset_index(drop=True)
    dropped = before - events["event_id"].nunique()
    if dropped:
        log.warning("events_without_erl_dropped", dropped=int(dropped),
                    kept=int(events["event_id"].nunique()))

    # Scope the ERL dict to the PANEL before building vectors. build_event_vectors
    # fits PCA on every ERL it receives, so passing the full cache would make the
    # panel's event vectors — and thus the headline — depend on unrelated cached
    # ERLs and DRIFT as the cache grows (observed: +0.0475 -> -0.0041 across two
    # runs as extraction finished). Panel-scoping makes every run self-contained
    # and bit-reproducible (combined with the GLM embedding cache).
    panel_erls = {eid: erls[eid] for eid in events["event_id"].unique()}
    real_vec = build_event_vectors(panel_erls, embedder, pca_dim=args.pca_dim)
    neutral_vec = build_event_vectors(make_neutral_erls(events), embedder, pca_dim=args.pca_dim)

    # Optional ALFRED CPI/NFP numeric surprise. Added to EVERY arm (including the
    # price-only baseline) so the ERL lift is incremental over the numeric
    # surprise — the confound guard against "ERL just proxies the data print".
    surprise_vec: pd.DataFrame | None = None
    if args.with_surprise and not args.synthetic:
        from aionis.features.macro_surprise import build_surprise_features

        surprise_vec = build_surprise_features(events, settings.fred_api_key)
        log.info(
            "surprise_features",
            n_events=len(surprise_vec),
            n_with_surprise=int(surprise_vec["has_surprise"].sum()),
        )

    def _augment(extra: pd.DataFrame | None) -> pd.DataFrame | None:
        if surprise_vec is None:
            return extra
        if extra is None:
            return surprise_vec
        return extra.join(surprise_vec)  # both indexed by event_id, disjoint columns

    price_dm = build_design_matrix(
        events, prices, sessions, symbols, horizon=args.horizon, extra_features=_augment(None)
    )
    erl_dm = build_design_matrix(
        events, prices, sessions, symbols, horizon=args.horizon, extra_features=_augment(real_vec)
    )
    neutral_dm = build_design_matrix(
        events, prices, sessions, symbols, horizon=args.horizon,
        extra_features=_augment(neutral_vec),
    )
    shuffled_dm = build_design_matrix(
        events,
        prices,
        sessions,
        symbols,
        horizon=args.horizon,
        extra_features=_augment(shuffled_vectors(real_vec)),
    )

    log.info(
        "comparison_design",
        rows=len(price_dm),
        events=price_dm.n_events,
        symbols=symbols,
        horizon=args.horizon,
        erls=len(erls),
    )

    results = []
    for name, fn in LEARNERS.items():
        for treat_name, dm in (("ERL", erl_dm), ("neutral", neutral_dm), ("shuffled", shuffled_dm)):
            r = compare_treatment(
                price_dm, dm, name, fn, args.horizon, args.n_splits, embargo,
                pit_cutoff=args.pit_cutoff,
            )
            r.treatment = treat_name
            results.append(r)

    print("\n=== Phase 3: with-ERL vs price-only (+ control gates) ===")
    print("DA_lift = treatment DA - price-only DA. Real ERL must beat; neutral/shuffled must not.")
    print(format_table(results))

    log_run(
        settings.runs_dir,
        config={
            "horizon": args.horizon,
            "n_splits": args.n_splits,
            "symbols": symbols,
            "start": args.start,
            "end": args.end,
            "synthetic": args.synthetic,
            "embedder": args.embedder,
            "with_surprise": args.with_surprise,
            "pit_cutoff": args.pit_cutoff,
        },
        results=[
            {
                "treatment": r.treatment,
                "learner": r.learner,
                "da_lift": r.da_lift,
                "ci_lo": r.ci_lo,
                "ci_hi": r.ci_hi,
                "dm_p": r.dm_p,
                "dm_p_mbb": r.dm_p_mbb,
                "sharpe": r.sharpe,
                "dsr": r.dsr,
                "pbo": r.pbo,
                "pit": r.pit,
                "n": r.n_clusters,
            }
            for r in results
        ],
        notes="pre-registered primary: pooled DA lift (ERL vs price-only), cluster-robust CI",
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aionis", description="Aionis MVP experiment runner")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    ing = sub.add_parser("ingest", help="Phase 0: fetch market + event snapshots")
    ing.add_argument("--start", default=DEFAULT_START)
    ing.add_argument("--end", default=DEFAULT_END)
    ing.add_argument(
        "--symbols", default=None, help=f"comma list (default: {','.join(ALL_SYMBOLS)})"
    )
    ing.add_argument("--event-types", nargs="+", default=["FOMC", "CPI", "NFP"])
    ing.add_argument("--events-csv", default=None, help="deterministic FOMC/event date override")
    ing.set_defaults(func=_cmd_ingest)

    ep = sub.add_parser("eval-priceonly", help="Phase 1: price-only + baselines benchmark")
    ep.add_argument("--start", default=DEFAULT_START)
    ep.add_argument("--end", default=DEFAULT_END)
    ep.add_argument("--horizon", type=int, default=1)
    ep.add_argument("--n-splits", type=int, default=5)
    ep.add_argument(
        "--synthetic", action="store_true", help="run on synthetic data (no keys needed)"
    )
    ep.add_argument("--synthetic-events", type=int, default=60)
    ep.set_defaults(func=_cmd_eval_priceonly)

    ex = sub.add_parser("extract", help="Phase 2: text -> ERL (GLM / OpenAI / --mock)")
    ex.add_argument("--start", default=DEFAULT_START)
    ex.add_argument("--end", default=DEFAULT_END)
    ex.add_argument(
        "--provider",
        choices=["router", "glm", "siliconflow", "modelscope", "openai", "mock"],
        default=None,
        help="LLM provider (router=multi-key policy failover; default from .env PROVIDER)",
    )
    ex.add_argument(
        "--mock", action="store_true", help="use the deterministic offline MockLLMClient"
    )
    ex.add_argument(
        "--synthetic", action="store_true", help="generate synthetic events/text (no ingest needed)"
    )
    ex.add_argument("--synthetic-events", type=int, default=60)
    ex.add_argument("--show", action="store_true", help="print a sample of extracted ERLs")
    ex.set_defaults(func=_cmd_extract)

    cmp = sub.add_parser("compare", help="Phase 3: with-ERL vs price-only + control gates")
    cmp.add_argument("--start", default=DEFAULT_START)
    cmp.add_argument("--end", default=DEFAULT_END)
    cmp.add_argument("--horizon", type=int, default=1)
    cmp.add_argument("--n-splits", type=int, default=5)
    cmp.add_argument(
        "--embedder", choices=["glm", "bge", "hash"], default="glm",
        help="event-text embedder: glm=API real semantic (low-mem), bge=local real, hash=test-only",
    )
    cmp.add_argument(
        "--pca-dim", type=int, default=None,
        help="PCA-reduce embeddings to this many components (recommended ~16-32 to avoid overfit)",
    )
    cmp.add_argument(
        "--with-surprise", action="store_true",
        help="add ALFRED CPI/NFP numeric surprise to ALL arms so the ERL lift is "
        "incremental over the numeric data print (confound guard)",
    )
    cmp.add_argument(
        "--pit-cutoff", default=None,
        help="LLM training-data cutoff YYYY-MM-DD; runs the memorization audit "
        "(pre/post-cutoff DA-lift gap with bootstrap CI)",
    )
    cmp.add_argument(
        "--synthetic", action="store_true", help="synthetic events/prices/text (no ingest needed)"
    )
    cmp.add_argument("--synthetic-events", type=int, default=60)
    cmp.set_defaults(func=_cmd_compare)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
