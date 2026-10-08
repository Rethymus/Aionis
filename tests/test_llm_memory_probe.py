"""Hermetic tests for scripts/llm_memory_probe.py (pure core; no LLM calls)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "llm_memory_probe.py"


def _load():
    spec = importlib.util.spec_from_file_location("llm_memory_probe", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def probe():
    return _load()


def _toy_panel() -> pd.DataFrame:
    # two months; AAA wins month 2 (+50%), BBB loses (-25%), CCC flat
    data = [
        ("2020-01-31", "AAA", 10.0), ("2020-01-31", "BBB", 20.0), ("2020-01-31", "CCC", 30.0),
        ("2020-02-28", "AAA", 15.0), ("2020-02-28", "BBB", 15.0), ("2020-02-28", "CCC", 30.0),
    ]
    return pd.DataFrame(data, columns=["date", "ticker", "close"])


def test_monthly_winners_top1_and_window(probe) -> None:
    w = probe.monthly_winners(_toy_panel(), start_ym="2020-01", end_ym="2020-02")
    assert set(w) == {"2020-02"}  # first month has no prev close
    assert w["2020-02"]["ticker"] == "AAA"
    assert w["2020-02"]["ret"] == pytest.approx(0.5)
    assert w["2020-02"]["n_tickers"] == 3


def test_sample_months_deterministic_and_bounded(probe) -> None:
    winners = {f"2021-{m:02d}": {"ticker": "X"} for m in range(1, 13)}
    a = probe.sample_months(winners, 4, seed=0)
    b = probe.sample_months(winners, 4, seed=0)
    c = probe.sample_months(winners, 4, seed=1)
    assert a == b, "sampling must be deterministic for fixed seed"
    assert len(a) == 4 and a == sorted(a)
    assert a != c or len(c) == 4  # seed shifts the sample (or trivially same size)
    assert all("2021-" in ym for ym in a)


def test_score_answer_hit_refusal_noanswer_and_parse(probe) -> None:
    hit = probe.score_answer(json.dumps({"ticker": "TPR"}), "TPR")
    assert hit["hit"] and hit["status"] == "answered"
    wrong = probe.score_answer(json.dumps({"ticker": "AAPL"}), "TPR")
    assert not wrong["hit"] and wrong["status"] == "answered"
    refuse = probe.score_answer(json.dumps({"ticker": "unknown"}), "TPR")
    assert refuse["status"] == "refusal" and not refuse["hit"]
    # empty raw or API error is NO-ANSWER, not a refusal (honesty: an errored
    # call says nothing about the model's memory)
    empty = probe.score_answer("", "TPR")
    assert empty["status"] == "no_answer" and not empty["refusal"]
    errored = probe.score_answer("", "TPR", error="Error 400 model id")
    assert errored["status"] == "no_answer"
    garbage = probe.score_answer("Tesla had a huge month", "TSLA")
    assert garbage["status"] == "refusal" and not garbage["hit"]  # non-JSON


def test_build_question_mentions_month_and_json(probe) -> None:
    system, user = probe.build_question("2020-10")
    assert "2020-10" in user and "ticker" in system.lower()
    assert "JSON" in system


def test_summarize_math_three_states(probe) -> None:
    rows = [
        {"status": "answered", "hit": True},
        {"status": "answered", "hit": False},
        {"status": "refusal", "hit": False},
        {"status": "no_answer", "hit": False},
    ]
    s = probe.summarize({"glm": rows})
    assert s["glm"]["n_questions"] == 4
    assert s["glm"]["refusals"] == 1
    assert s["glm"]["no_answer_api"] == 1
    assert s["glm"]["top1_hits"] == 1
    assert s["glm"]["hit_rate_answered"] == pytest.approx(0.5)


def test_score_answer_top5_variants(probe) -> None:
    good = probe.score_answer_top5(
        json.dumps({"tickers": ["AAPL", "TPR", "MSFT", "NVDA", "TSLA"]}), "TPR")
    assert good["status"] == "answered" and good["top5_hit"]
    assert not good["top1_hit"]  # truth present but not first
    first = probe.score_answer_top5(
        json.dumps({"tickers": ["TPR", "AAPL", "MSFT", "NVDA", "TSLA"]}), "TPR")
    assert first["top1_hit"] and first["top5_hit"]
    lower = probe.score_answer_top5(
        json.dumps({"tickers": ["aapl", "tpr"]}), "TPR")
    assert lower["top5_hit"]  # case-insensitive
    miss = probe.score_answer_top5(
        json.dumps({"tickers": ["AAPL", "MSFT", "NVDA"]}), "TPR")
    assert not miss["top5_hit"] and miss["status"] == "answered"
    refuse = probe.score_answer_top5(json.dumps({"tickers": []}), "TPR")
    assert refuse["status"] == "refusal" and not refuse["top5_hit"]
    noans = probe.score_answer_top5("", "TPR", error="Error 400")
    assert noans["status"] == "no_answer"


def test_build_question_top5_mode(probe) -> None:
    system, user = probe.build_question("2020-10", mode="top5")
    assert "5 candidate" in user.lower() and "tickers" in system
    system1, _ = probe.build_question("2020-10", mode="top1")
    assert "ticker" in system1 and "JSON" in system1


def test_summarize_includes_top5_when_present(probe) -> None:
    rows = [
        {"refusal": False, "hit": False, "top5_hit": True},
        {"refusal": False, "hit": False, "top5_hit": False},
        {"refusal": False, "hit": False},  # legacy top1-only row
    ]
    s = probe.summarize({"glm": rows})
    assert s["glm"]["top5_hits"] == 1
