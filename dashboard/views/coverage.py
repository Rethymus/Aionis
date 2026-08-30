"""Coverage view — universe metrics."""
from __future__ import annotations

import streamlit as st

from dashboard.views.data_loading import _coverage


def view_coverage() -> None:
    cov = _coverage()
    st.subheader("Coverage")
    c1, c2, c3 = st.columns(3)
    c1.metric("S&P 500 PIT universe (clean)", cov["clean"])
    c2.metric("resolvable superset", cov["total"])
    c3.metric("monthly Jaccard (hanshof vs pierrebrunelle)", f"{cov['jaccard']:.3f}")
    st.caption(f"reuse-dropped tickers: {cov['dropped']}")
    st.caption(f"source: {cov.get('source', 'ledger')}")
