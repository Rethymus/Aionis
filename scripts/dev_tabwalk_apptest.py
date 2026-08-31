"""Round-46 tab walk (protocol channel A): headless AppTest over all 11 tabs.

st.tabs renders every tab's code on each rerun, so one AppTest.run() executes
the full app; uncaught exceptions surface in at.exception. Also exercises the
event-study selectbox interaction (13D -> earnings) and asserts the honest
degradation warnings for this machine's cache state (no 13D events parquet,
no prices parquet, no runs/forward/).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from streamlit.testing.v1 import AppTest


def main() -> int:
    at = AppTest.from_file("dashboard/app.py", default_timeout=600)
    at.run()

    failures: list[str] = []

    # 1) the script must run to completion, no uncaught exception
    if at.exception:
        failures.append(f"uncaught exceptions: {[e.value for e in at.exception]}")

    # 2) all 11 tabs present
    labels = [t.label for t in at.tabs]
    expected = ["Overview", "Fit Quality", "Volatility", "Curve Evolution",
                "Event Study", "Uncertainty", "Horizon Robustness", "Coverage",
                "Strategy Return", "Forward IC", "Run history"]
    if labels != expected:
        failures.append(f"tabs mismatch: {labels}")

    caps = [c.value for c in at.caption]
    mds = [m.value for m in at.markdown]
    infos = [i.value for i in at.info]
    warns = [w.value for w in at.warning]

    joined_caps = " | ".join(caps)
    joined_md = " | ".join(mds)

    # 3) overview honesty markers
    if "4/4 NULL (95% CI brackets 0)" not in joined_caps:
        failures.append("overview null summary caption missing")
    if "precision-gate" not in joined_caps:
        failures.append("precision-gate caption missing")
    if "publishable" in joined_caps or "publishable" in joined_md:
        failures.append("retired 'publishable' wording still on-wall")

    # 4) headline table numbers were byte-verified against the ledger in the
    #    round-45 AX-tree walk; here we assert the table exists at all.
    dfs = [d for d in at.dataframe]
    if not dfs:
        failures.append("headline dataframe missing")

    # 5) horizon tab: 4-phase markers. The chart title lives inside the plotly
    #    spec (on-wall verified in round 45); here assert the captions and the
    #    plotly elements exist.
    if not any("8/8 exploratory cells" in c and "4 frozen" in c for c in caps):
        failures.append("horizon 8/8 caption missing")
    if not any("The 4 confirmatory nulls (B/C/D/E1)" in c for c in caps):
        failures.append("horizon 4-phase lead caption missing")

    # 6) coverage: ledger-sourced provenance caption
    if not any(c.startswith("source: ledger") for c in caps):
        failures.append(f"coverage ledger-source caption missing; caps={caps}")

    # 7) strategy tab: None-safe formatting rendered (no exception already
    #    guaranteed by (1)); DSR caption present
    if not any("DSR deflation" in c for c in caps):
        failures.append("strategy DSR caption missing")

    # 8) event study: machine-state-aware honest rendering.
    #    - 13D events cache PRESENT (2026-08-31 build, 2,877 rows): the real
    #      path must render — `event-car-real` plotly chart + survival caption,
    #      and NO event-tab degradation warning is expected. (The long
    #      "DEMO: synthetic data" warning in `warns` belongs to the uncertainty
    #      tab — same wording, different view.)
    #    - cache ABSENT: expect the honest degradation warning (compute-failed
    #      or no-events) exactly as round-46/47 pinned.
    events_cache = Path("data") / "cache" / "phase_d_13d_events.parquet"
    # Real path's end-marker caption: "N of M 13D events survived the
    # session/window filter ..." — renders only after the CAR chart succeeds.
    real_cap = any("13D events survived the session/window filter" in c for c in caps)
    if events_cache.exists():
        if not real_cap:
            failures.append(
                f"event-study real-path survival caption missing (cache present); warns={warns}"
            )
        if any("event-study compute failed" in w for w in warns):
            failures.append(f"event-study compute failed despite cache present; warns={warns}")
    else:
        if not any("13D" in w or "event" in w.lower() for w in warns):
            failures.append(f"event-study honest warning missing; warns={warns}")

    # 9) event-study selectbox interaction: switch to earnings and rerun
    sbs = [s for s in at.selectbox if s.key == "event_type_real"]
    if not sbs:
        failures.append("event_type_real selectbox missing")
    else:
        sbs[0].set_value("earnings").run()
        if at.exception:
            failures.append(f"exception after earnings switch: {[e.value for e in at.exception]}")

    # 10) forward IC: honest absence info on this machine
    if not any("No forward runs yet" in i for i in infos):
        failures.append(f"forward-ic absence info missing; infos={infos}")

    print("=== TAB WALK RESULT ===")
    if failures:
        for f in failures:
            print("FAIL:", f)
        return 1
    print("ALL CHECKS PASS")
    print("warnings:", warns)
    print("infos:", infos[:4])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
