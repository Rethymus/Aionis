"""Run history view — ledger display."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.views.data_loading import _ledger_rows


def view_run_history() -> None:
    st.subheader("Run history (ledger)")
    rows = _ledger_rows()
    if not rows:
        st.info("Ledger empty.")
        return
    show = [{"ts": r.get("ts", "")[:19], "event": r.get("event"),
             "phase": r.get("phase"), "sig": str(r.get("config_sig", ""))[:12]}
            for r in rows[-30:]]
    st.dataframe(pd.DataFrame(show[::-1]), use_container_width=True, hide_index=True)
