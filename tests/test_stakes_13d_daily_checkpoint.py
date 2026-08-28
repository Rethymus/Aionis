"""Hermetic tests for the per-day checkpoint of the 13D daily-index walk.

NO NETWORK — the HTTP layer (``_policy_get``) is monkeypatched to an
in-memory fake while the REAL ``fetch_daily_crawler_index`` runs, so the raw
per-day index caches and checkpoint fingerprinting behave exactly as in
production. The fakes are labeled unit-test fixtures only (never used in the
research pipeline).

Premise check (task §0, recorded): EDGAR daily crawler indexes are date-keyed
immutable archives — ``_daily_index_url`` builds
``daily-index/{year}/QTR{q}/crawler.{yyyymmdd}.idx``, a per-date file under
EDGAR's /Archives/ tree that pins its own "Last Data Received" header, and the
module's raw-text cache already treats each day as permanent — so per-day
cached parse rows stay valid long-term. One honest mutation window remains:
the CURRENT day's file can still grow during EDGAR's dissemination window
(the cron captures it mid-window at 18:00 ET). The checkpoint therefore stores
each day's sha256 fingerprint of the raw index text and reuses rows only
while the local raw cache still hashes to it (disk-only verification: zero
requests, zero parsing); a mismatch recomputes exactly that day.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from datetime import date, datetime

import pytest

import aionis.ingest.stakes_13d_daily_index as mod

# Mon 2026-08-03 .. Fri 2026-08-07 — five consecutive business days.
START = date(2026, 8, 3)
END = date(2026, 8, 7)
MARKERS = ["mon", "tue", "wed", "thu", "fri"]
DAYS = list(zip(MARKERS, [date(2026, 8, 3 + i) for i in range(5)], strict=True))
CHECKPOINT = "sc13d_daily_checkpoint.json"


def _idx(marker: str, d: date) -> str:
    """One minimal EDGAR-shaped day index: header + exactly one SC 13D row."""
    i = MARKERS.index(marker) + 1
    return (
        "Description:           Daily Crawler Index of EDGAR Dissemination Feed\n"
        f"Last Data Received:    {d:%b} {d.day}, {d.year}\n"
        "Comments:              webmaster@sec.gov\n"
        "\n"
        "Company Name                Form Type     CIK      Date       Filename\n"
        "-------------------------------------------------------------------\n"
        f"{marker.upper()} ACQUISITION CORP   SCHEDULE 13D   {1332550 + i}   "
        f"{d:%Y%m%d}   https://www.sec.gov/Archives/edgar/data/{1332550 + i}/"
        f"000{i:03d}/\n"
    )


def _texts() -> dict[date, str]:
    return {d: _idx(m, d) for m, d in DAYS}


class _FakeResp:
    def __init__(self, text: str) -> None:
        self.text = text


def _fake_policy_get(
    texts: dict[date, str], calls: list[date], fail_on: frozenset[date] = frozenset()
) -> Callable[..., _FakeResp]:
    """In-memory stand-in for ``_policy_get``; records requested days in order."""
    url_date = re.compile(r"crawler\.(\d{8})\.idx")

    def _get(url: str, **_: object) -> _FakeResp:
        d = datetime.strptime(url_date.search(url).group(1), "%Y%m%d").date()
        calls.append(d)
        if d in fail_on:
            raise RuntimeError(f"simulated EDGAR failure on {d}")
        return _FakeResp(texts[d])

    return _get


def test_checkpoint_persist_and_rerun_is_zero_parse_zero_request(tmp_path, monkeypatch) -> None:
    texts = _texts()
    calls: list[date] = []
    monkeypatch.setattr(mod, "_policy_get", _fake_policy_get(texts, calls))
    rows1 = mod.fetch_recent_13d_daily(START, END, tmp_path)
    assert len(calls) == 5  # cold walk fetches every business day once

    cp = json.loads((tmp_path / CHECKPOINT).read_text(encoding="utf-8"))
    assert cp["version"] == 1
    assert set(cp["days"]) == {str(d) for _, d in DAYS}
    # Every entry's fingerprint links to the cached raw day-index text.
    for _, d in DAYS:
        raw = (tmp_path / f"daily_idx_{d:%Y%m%d}.txt").read_text()
        entry = cp["days"][str(d)]
        assert entry["fingerprint"] == hashlib.sha256(raw.encode("utf-8")).hexdigest()
        assert entry["rows"] == mod.parse_daily_13d(raw)

    # Rerun over the same window: every day is a checkpoint hit — zero
    # requests AND zero parses.
    calls2: list[date] = []
    parsed: list[str] = []
    monkeypatch.setattr(mod, "_policy_get", _fake_policy_get(texts, calls2))
    real_parse = mod.parse_daily_13d

    def _counting(text: str) -> list[dict]:
        parsed.append(text)
        return real_parse(text)

    monkeypatch.setattr(mod, "parse_daily_13d", _counting)
    rows2 = mod.fetch_recent_13d_daily(START, END, tmp_path)

    assert calls2 == []
    assert parsed == []
    assert rows2 == rows1


def test_interrupted_walk_resumes_without_reparsing_cached_days(tmp_path, monkeypatch) -> None:
    texts = _texts()
    by_marker = {m: _idx(m, d) for m, d in DAYS}

    # ONE-SHOT reference: fresh dir, full uninterrupted walk.
    ref_dir = tmp_path / "ref"
    ref_dir.mkdir()
    monkeypatch.setattr(mod, "_policy_get", _fake_policy_get(texts, []))
    rows_ref = mod.fetch_recent_13d_daily(START, END, ref_dir)

    # The checkpoint-free path (pre-change behavior) must produce the
    # byte-identical aggregate the script serializes.
    free_dir = tmp_path / "free"
    free_dir.mkdir()
    monkeypatch.setattr(mod, "_policy_get", _fake_policy_get(texts, []))
    rows_free = mod.fetch_recent_13d_daily(START, END, free_dir, use_checkpoint=False)
    assert json.dumps(rows_free, indent=2) == json.dumps(rows_ref, indent=2)

    # RUN 1 — killed mid-walk: parsing WED raises (parse sits outside the
    # per-day fetch-resilience guard, so it propagates like a hard kill).
    kill_dir = tmp_path / "kill"
    kill_dir.mkdir()
    monkeypatch.setattr(mod, "_policy_get", _fake_policy_get(texts, []))
    real_parse = mod.parse_daily_13d

    def _boom(text: str) -> list[dict]:
        if text == by_marker["wed"]:
            raise RuntimeError("simulated mid-walk kill")
        return real_parse(text)

    monkeypatch.setattr(mod, "parse_daily_13d", _boom)
    with pytest.raises(RuntimeError, match="mid-walk kill"):
        mod.fetch_recent_13d_daily(START, END, kill_dir)
    # Mon + Tue were persisted before the kill; Wed–Fri have no entries yet.
    cp = json.loads((kill_dir / CHECKPOINT).read_text(encoding="utf-8"))
    assert set(cp["days"]) == {"2026-08-03", "2026-08-04"}

    # RUN 2 — resume: Mon/Tue are reused (zero requests, zero parses). Even
    # Wed needs no request — its raw index was cached by run 1 before the
    # kill — so only Thu/Fri reach the (fake) network.
    calls2: list[date] = []
    parsed2: list[str] = []
    monkeypatch.setattr(mod, "_policy_get", _fake_policy_get(texts, calls2))

    def _counting(text: str) -> list[dict]:
        parsed2.append(text)
        return real_parse(text)

    monkeypatch.setattr(mod, "parse_daily_13d", _counting)
    rows2 = mod.fetch_recent_13d_daily(START, END, kill_dir)

    assert calls2 == [date(2026, 8, 6), date(2026, 8, 7)]
    assert parsed2 == [by_marker["wed"], by_marker["thu"], by_marker["fri"]]
    # Resumed aggregate is byte-identical to the one-shot walk.
    assert json.dumps(rows2, indent=2) == json.dumps(rows_ref, indent=2)


def test_fingerprint_mismatch_recomputes_only_that_day(tmp_path, monkeypatch) -> None:
    """Same-day mutation window: a raw day-index that changed under the
    checkpoint (the current day's file grew) must be recomputed, not trusted
    — with zero requests when the changed text is already cached locally."""
    texts = _texts()
    monkeypatch.setattr(mod, "_policy_get", _fake_policy_get(texts, []))
    mod.fetch_recent_13d_daily(START, END, tmp_path)

    # Mon's index "grows" after the checkpoint captured it.
    raw_mon = tmp_path / "daily_idx_20260803.txt"
    grown = raw_mon.read_text() + (
        "LATE EVENING CORP   SCHEDULE 13D   1332999   20260803   "
        "https://www.sec.gov/Archives/edgar/data/1332999/000999/\n"
    )
    raw_mon.write_text(grown)

    calls2: list[date] = []
    parsed2: list[str] = []
    monkeypatch.setattr(mod, "_policy_get", _fake_policy_get(texts, calls2))
    real_parse = mod.parse_daily_13d

    def _counting(text: str) -> list[dict]:
        parsed2.append(text)
        return real_parse(text)

    monkeypatch.setattr(mod, "parse_daily_13d", _counting)
    rows2 = mod.fetch_recent_13d_daily(START, END, tmp_path)

    assert calls2 == []  # mismatch detected from disk alone
    assert parsed2 == [grown]  # only Mon's day recomputed
    late = [r for r in rows2 if r["target"] == "LATE EVENING CORP"]
    assert len(late) == 1 and late[0]["date"] == "2026-08-03"
    # The checkpoint now links to the grown text.
    cp = json.loads((tmp_path / CHECKPOINT).read_text(encoding="utf-8"))
    assert cp["days"]["2026-08-03"]["fingerprint"] == hashlib.sha256(
        grown.encode("utf-8")
    ).hexdigest()
    assert len(cp["days"]["2026-08-03"]["rows"]) == 2


def test_failed_day_gets_no_checkpoint_entry_and_is_gap_filled(tmp_path, monkeypatch) -> None:
    texts = _texts()
    # Run 1: THU's fetch fails (EDGAR 403/5xx analogue) — day skipped, NOT
    # checkpointed, so the next run retries exactly the missing day.
    calls1: list[date] = []
    monkeypatch.setattr(
        mod, "_policy_get", _fake_policy_get(texts, calls1, fail_on=frozenset({date(2026, 8, 6)}))
    )
    rows1 = mod.fetch_recent_13d_daily(START, END, tmp_path)
    cp = json.loads((tmp_path / CHECKPOINT).read_text(encoding="utf-8"))
    assert set(cp["days"]) == {"2026-08-03", "2026-08-04", "2026-08-05", "2026-08-07"}
    assert all(r["target"] != "THU ACQUISITION CORP" for r in rows1)

    # Run 2: only THU is requested/parsed; cached days are untouched.
    calls2: list[date] = []
    parsed2: list[str] = []
    monkeypatch.setattr(mod, "_policy_get", _fake_policy_get(texts, calls2))
    real_parse = mod.parse_daily_13d

    def _counting(text: str) -> list[dict]:
        parsed2.append(text)
        return real_parse(text)

    monkeypatch.setattr(mod, "parse_daily_13d", _counting)
    rows2 = mod.fetch_recent_13d_daily(START, END, tmp_path)
    assert calls2 == [date(2026, 8, 6)]
    assert parsed2 == [_idx("thu", date(2026, 8, 6))]
    assert any(r["target"] == "THU ACQUISITION CORP" for r in rows2)

    # And the healed result equals a clean one-shot walk.
    ref_dir = tmp_path / "ref"
    ref_dir.mkdir()
    monkeypatch.setattr(mod, "_policy_get", _fake_policy_get(texts, []))
    rows_ref = mod.fetch_recent_13d_daily(START, END, ref_dir)
    assert json.dumps(rows2, indent=2) == json.dumps(rows_ref, indent=2)


@pytest.mark.parametrize("junk", ["{not json!!", '{"version": 99, "days": {}}'])
def test_corrupt_or_foreign_checkpoint_is_rebuilt_not_fatal(tmp_path, monkeypatch, junk) -> None:
    texts = _texts()
    (tmp_path / CHECKPOINT).write_text(junk, encoding="utf-8")
    calls: list[date] = []
    monkeypatch.setattr(mod, "_policy_get", _fake_policy_get(texts, calls))
    rows = mod.fetch_recent_13d_daily(START, END, tmp_path)

    assert len(calls) == 5  # degraded to a full recompute, no crash
    assert len(rows) == 5
    cp = json.loads((tmp_path / CHECKPOINT).read_text(encoding="utf-8"))
    assert cp["version"] == 1 and len(cp["days"]) == 5
