"""Hermetic tests for the deterministic proposal engine + closure
reconciliation (scripts/monthly_review.py --propose / weekly section 4).

gen2 item 3 (round 128-续2): existing signals x rule table -> S/M/L proposal
cards with evidence pointers + prop: dedup keys; the engine is READ-ONLY on
state/backlog.md and tasks/ (present keys degrade to refresh instructions,
never duplicate cards, never auto-writes); --weekly gains a proposal-closure
reconciliation section and a default on-disk anchor. Zero network: the git
pickaxe runner is injected (same pattern as the gh fetcher stubs in
test_monthly_review_watchdog.py:27-44).
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import monthly_review as mr  # noqa: E402

NOW = datetime(2026, 11, 11, 12, 0)


def _write_night_package(repo: Path, day: str, threads: dict) -> None:
    d = repo / "runs" / "ops_local_refresh" / day
    d.mkdir(parents=True, exist_ok=True)
    (d / "night_package.json").write_text(
        json.dumps({"date": day, "threads": threads}, ensure_ascii=False),
        encoding="utf-8")


def _write_summary(repo: Path, day: str, persistent: list[str]) -> None:
    d = repo / "runs" / "ops_local_refresh" / day
    d.mkdir(parents=True, exist_ok=True)
    payload = {"date": day, "status": "ok_committed",
               "persistent_soft_fails": persistent}
    (d / "run.log").write_text(
        "[21:38:59] SUMMARY " + json.dumps(payload, ensure_ascii=False) + "\n",
        encoding="utf-8")


def _write_backlog(repo: Path, text: str) -> None:
    d = repo / "state"
    d.mkdir(parents=True, exist_ok=True)
    (d / "backlog.md").write_text(text, encoding="utf-8")


def _write_anchor(repo: Path, day: str, findings: list[str]) -> None:
    d = repo / "runs" / "ops_local_refresh" / day
    d.mkdir(parents=True, exist_ok=True)
    body = ["# Weekly Watchdog — external audit", "",
            "## Findings requiring human attention: "
            f"{len(findings)}", ""]
    body += [f"- {f}" for f in findings] or ["- none — walk away"]
    (d / "weekly_watchdog.md").write_text("\n".join(body) + "\n",
                                          encoding="utf-8")


def _old_date(days: int) -> str:
    return (NOW - timedelta(days=days)).isoformat()


# -------------------------------------------------------- no signal -> zero

def test_propose_no_signals_yields_zero_cards(tmp_path: Path) -> None:
    _write_summary(tmp_path, "2026-11-10", [])
    _write_night_package(tmp_path, "2026-11-10",
                         {"platform-failure": [], "infra-transient": [],
                          "code-defect": []})
    _write_backlog(tmp_path, "# state/backlog.md\n\n## 开放候选\n\n"
                   "- **Fresh idea.** Added yesterday.\n")
    markdown, n = mr.run_propose(
        tmp_path, now=NOW, month="2026-11",
        git_log=lambda repo, needle: _old_date(1))
    assert n == 0
    assert "无提案——无信号或全部已在册" in markdown


# ------------------------------------------------------- rule table mapping

def test_propose_platform_card_from_night_package(tmp_path: Path) -> None:
    _write_night_package(tmp_path, "2026-11-10", {"platform-failure": [
        "thread:platform-billing: 2× platform-failure → §5 钥匙区"]})
    markdown, n = mr.run_propose(tmp_path, now=NOW, month="2026-11")
    assert n == 1
    assert "（key: prop:platform-billing）" in markdown
    assert "thread: thread:platform-billing" in markdown
    assert "只呈报不催办" in markdown
    assert "≥2 工作流同晚平台红 = billing 锁签名" in markdown
    assert "night_package.json: thread:platform-billing: 2×" in markdown


def test_propose_spin_card_from_logs(tmp_path: Path) -> None:
    for day in ("2026-11-04", "2026-11-05"):
        d = tmp_path / "runs" / "ops_local_refresh" / day
        d.mkdir(parents=True)
        (d / "run.log").write_text(
            "[21:38:59] HARD-FAIL: hard-fail step 'cap step': boom\n",
            encoding="utf-8")
    markdown, n = mr.run_propose(tmp_path, now=NOW, month="2026-11")
    assert n == 1
    assert "（key: prop:spin）" in markdown
    assert "thread: thread:spin" in markdown
    assert "原地打转" in markdown


def test_propose_persistent_three_evenings_threshold(tmp_path: Path) -> None:
    for day in ("2026-11-03", "2026-11-04", "2026-11-05"):
        _write_summary(tmp_path, day, ["news_feed_fetch [local superset]"])
    markdown, n = mr.run_propose(tmp_path, now=NOW, month="2026-11")
    assert n == 1
    assert "prop:persistent:news-feed-fetch-local-superset" in markdown
    assert "source-redundancy.md" in markdown
    # two evenings: below threshold -> no card
    tmp2 = tmp_path / "two"  # separate repo root
    for day in ("2026-11-03", "2026-11-04"):
        _write_summary(tmp2, day, ["news_feed_fetch [local superset]"])
    _, n2 = mr.run_propose(tmp2, now=NOW, month="2026-11")
    assert n2 == 0


def test_propose_backlog_aging_over_90_days(tmp_path: Path) -> None:
    _write_backlog(tmp_path, "# b\n\n## 开放候选\n\n"
                   "- **Ancient idea.** From August.\n"
                   "- ~~**Done idea.**~~ 完成清账\n"
                   "- **Fresh idea.** Added yesterday.\n")
    ages = {"**Ancient idea.** From August.": _old_date(120),
            "**Fresh idea.** Added yesterday.": _old_date(2)}
    markdown, n = mr.run_propose(
        tmp_path, now=NOW, month="2026-11",
        git_log=lambda repo, needle: ages.get(needle))
    assert n == 1
    assert "prop:backlog-aging:Ancient-idea-From-August" in markdown
    assert "再裁决" in markdown
    assert "Ancient" in markdown and "git pickaxe" in markdown


def test_propose_backlog_aging_git_unavailable_no_card(tmp_path: Path) -> None:
    """git/history unreachable = aging unknown -> NO card, never a guess."""
    _write_backlog(tmp_path, "# b\n\n## 开放候选\n\n- **Ancient idea.**\n")
    _, n = mr.run_propose(tmp_path, now=NOW, month="2026-11",
                          git_log=lambda repo, needle: None)
    assert n == 0


def test_propose_backlog_aging_tz_aware_commit_date(tmp_path: Path) -> None:
    """Regression (live-fire 2026-11-11): git %cI is offset-aware; the naive
    `now` must not crash the subtraction. 120 days ago in +08:00 still ages."""
    _write_backlog(tmp_path, "# b\n\n## 开放候选\n\n- **Ancient idea.** x\n")
    old = (NOW - timedelta(days=120)).astimezone().isoformat()
    markdown, n = mr.run_propose(
        tmp_path, now=NOW, month="2026-11",
        git_log=lambda repo, needle: old)
    assert n == 1
    assert "prop:backlog-aging:" in markdown


def test_propose_weekly_anchor_findings_map_to_cards(tmp_path: Path) -> None:
    _write_anchor(tmp_path, "2026-11-06", [
        "workflow real red (code-defect): vintage-probe.yml",
        "platform-failure: billing lock — owner key needed",
        "ledger: runs/ledger.jsonl:12: unparseable JSONL",
        "some brand new signal shape",
    ])
    markdown, n = mr.run_propose(tmp_path, now=NOW, month="2026-11")
    assert n == 4
    assert "prop:ci-red:vintage-probe-yml" in markdown
    assert "thread: thread:ci-red:vintage-probe.yml" in markdown
    assert "prop:platform-billing" in markdown
    assert "prop:ledger-anomaly" in markdown
    assert "thread: thread:ledger-anomaly" in markdown
    assert "prop:weekly:" in markdown  # unclassified -> human disposition


def test_propose_same_key_merges_evidence_not_cards(tmp_path: Path) -> None:
    """Spin seen in logs (R1) AND in the weekly anchor (R5) -> ONE card with
    both evidence lines (dedup-by-key is the flood guard)."""
    for day in ("2026-11-04", "2026-11-05"):
        d = tmp_path / "runs" / "ops_local_refresh" / day
        d.mkdir(parents=True)
        (d / "run.log").write_text(
            "[21:38:59] HARD-FAIL: hard-fail step 'cap step': boom\n",
            encoding="utf-8")
    _write_anchor(tmp_path, "2026-11-06",
                  ["spin (原地打转): cap step failing on 2 evenings"])
    markdown, n = mr.run_propose(tmp_path, now=NOW, month="2026-11")
    assert n == 1
    assert markdown.count("（key: prop:spin）") == 1
    assert markdown.count("evidence:") >= 2  # both sources on one card


# --------------------------------------------------- read-only dedup guards

def test_propose_backlog_present_key_degrades_to_refresh(tmp_path: Path) -> None:
    _write_night_package(tmp_path, "2026-11-10", {"platform-failure": [
        "thread:platform-billing: 1× platform-failure → §5 钥匙区"]})
    _write_backlog(tmp_path, "# b\n\n## 开放候选\n\n"
                   "- **[S] billing 钥匙区（只呈报不催办）**"
                   "（key: prop:platform-billing）\n")
    markdown, n = mr.run_propose(tmp_path, now=NOW, month="2026-11")
    assert n == 0  # no duplicate card
    assert "prop:platform-billing 已在 state/backlog.md 候选区在册" \
        in markdown
    assert "只读不代写" in markdown


def test_propose_task_dispatched_key_degrades_to_refresh(tmp_path: Path) -> None:
    _write_night_package(tmp_path, "2026-11-10", {"platform-failure": [
        "thread:platform-billing: 1× platform-failure → §5 钥匙区"]})
    task = tmp_path / "tasks" / "active" / "TASK-X.md"
    task.parent.mkdir(parents=True)
    task.write_text("# TASK-X\n（key: prop:platform-billing）\n",
                    encoding="utf-8")
    markdown, n = mr.run_propose(tmp_path, now=NOW, month="2026-11")
    assert n == 0
    assert "prop:platform-billing 已在 tasks/active/ 在册" in markdown


def test_render_card_research_gate_is_forced_when_flagged() -> None:
    card = {"key": "prop:demo", "size": "M", "thread": None,
            "title": "demo", "action": "do it", "evidence": ["e1"],
            "research": True}
    lines = mr.render_card(card)
    assert any(mr.PROPOSAL_RESEARCH_GATE.split(":")[0] in ln
               for ln in lines)
    plain = mr.render_card({k: v for k, v in card.items()
                            if k != "research"})
    assert not any("research-gate" in ln for ln in plain)


# ------------------------------------------------------- closure recon (§4)

def _write_task(repo: Path, zone: str, name: str, keys: str) -> None:
    d = repo / "tasks" / zone
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(f"# {name}\n{keys}\n", encoding="utf-8")


def test_reconciliation_clean_zero_keys(tmp_path: Path) -> None:
    findings, stats = mr.proposal_reconciliation(tmp_path)
    assert findings == []
    assert stats["backlog_keys"] == 0 and stats["task_keys"] == 0


def test_reconciliation_multi_zone_key_is_drift(tmp_path: Path) -> None:
    _write_task(tmp_path, "active", "A.md", "（key: prop:x）")
    _write_task(tmp_path, "completed", "B.md", "（key: prop:x）")
    findings, stats = mr.proposal_reconciliation(tmp_path)
    assert any("multiple tasks zones" in f for f in findings)
    assert stats["task_keys"] == 1


def test_reconciliation_completed_but_backlog_still_open(tmp_path: Path) -> None:
    _write_backlog(tmp_path, "## 开放候选\n\n"
                   "- **[S] thing**（key: prop:y）\n")
    _write_task(tmp_path, "completed", "C.md", "（key: prop:y）")
    findings, _ = mr.proposal_reconciliation(tmp_path)
    assert any("strike it by hand" in f for f in findings)


def test_reconciliation_completed_and_struck_is_clean(tmp_path: Path) -> None:
    _write_backlog(tmp_path, "## 开放候选\n\n"
                   "- ~~**[S] thing**（key: prop:z）~~ 完成清账\n")
    _write_task(tmp_path, "completed", "D.md", "（key: prop:z）")
    findings, _ = mr.proposal_reconciliation(tmp_path)
    assert findings == []


def test_weekly_report_carries_reconciliation_section(tmp_path: Path) -> None:
    _write_backlog(tmp_path, "## 开放候选\n\n- plain candidate\n")
    report, code = mr.run_weekly(tmp_path, NOW)  # gh unreachable -> unverified
    assert "## 4. Proposal-closure reconciliation" in report
    assert "**OK**" in report
    assert code == 1  # ledger missing in tmp repo is still a finding


# ----------------------------------------------------------------- CLI paths

def test_cli_weekly_writes_default_anchor(tmp_path: Path) -> None:
    buf, err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf), redirect_stderr(err):
        rc = mr.main(["--weekly", "--repo", str(tmp_path)])
    assert rc in (0, 1)
    assert "Weekly Watchdog" in buf.getvalue()
    anchor = (tmp_path / "runs" / "ops_local_refresh"
              / datetime.now().strftime("%Y-%m-%d") / "weekly_watchdog.md")
    assert anchor.is_file()
    assert "Weekly Watchdog" in anchor.read_text(encoding="utf-8")


def test_cli_weekly_out_replaces_anchor(tmp_path: Path) -> None:
    out = tmp_path / "wk.md"
    buf, err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf), redirect_stderr(err):
        mr.main(["--weekly", "--repo", str(tmp_path), "--out", str(out)])
    assert out.is_file()
    anchor = (tmp_path / "runs" / "ops_local_refresh"
              / datetime.now().strftime("%Y-%m-%d") / "weekly_watchdog.md")
    assert not anchor.exists()


def test_cli_propose_end_to_end(tmp_path: Path) -> None:
    _write_night_package(tmp_path, "2026-11-10", {"platform-failure": [
        "thread:platform-billing: 2× platform-failure → §5 钥匙区"]})
    buf, err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf), redirect_stderr(err):
        rc = mr.main(["--propose", "--repo", str(tmp_path)])
    assert rc == 0
    out = buf.getvalue()
    assert "proposal cards — 确定性提案引擎" in out or \
        "--propose" in out.splitlines()[0]
    assert "prop:platform-billing" in out


# --------------------------------------------------------------- round 131
# {answer, p} bounded-question contract (Jev calibrated-probability proto)
# + prediction slot on cards + Brier-style reconciliation (RLCD
# prediction-error leg). Zero LLM: parse/validate/record only, p is never
# invented by the engine (honesty boundary), no recalibration fitting.

def test_parse_bounded_answer_valid() -> None:
    ok = mr.parse_bounded_answer(
        '结论：{"answer": true, "p": 0.8}（本月无打转）')
    assert ok["ok"] is True and ok["answer"] is True and ok["p"] == 0.8


def test_parse_bounded_answer_picks_first_json_with_both_keys() -> None:
    text = '前置 {"noise": 1} 然后 {"answer": "spin-once", "p": 0.35}'
    ok = mr.parse_bounded_answer(text)
    assert ok["ok"] is True and ok["answer"] == "spin-once" and ok["p"] == 0.35


def test_parse_bounded_answer_format_miss_keeps_raw() -> None:
    bad = mr.parse_bounded_answer("就是没打转，感觉挺稳")
    assert bad["ok"] is False and bad["reason"] == "format-miss"
    assert "就是没打转" in bad["raw"]


def test_parse_bounded_answer_rejects_out_of_range_p() -> None:
    bad = mr.parse_bounded_answer('{"answer": true, "p": 1.5}')
    assert bad["ok"] is False and bad["reason"] == "p-out-of-range"
    bad2 = mr.parse_bounded_answer('{"answer": true, "p": "高"}')
    assert bad2["ok"] is False and bad2["reason"] == "p-not-numeric"


def test_bounded_question_contract_mentions_json() -> None:
    assert '"answer"' in mr.WATCHDOG_BOUNDED_QUESTION
    assert '"p"' in mr.WATCHDOG_BOUNDED_QUESTION


def test_render_card_prediction_slot_default_unfilled() -> None:
    card = {"size": "S", "title": "t", "key": "prop:x", "evidence": ["e"],
            "action": "a",
            "prediction": {"claim": "billing 12 月内解锁", "due_month": "2026-12"}}
    lines = mr.render_card(card)
    joined = "\n".join(lines)
    assert "prediction: billing 12 月内解锁" in joined
    assert "待月末会话填写" in joined  # engine never invents p
    assert "due=2026-12" in joined
    assert "(p−y)²" in joined


def test_render_card_no_prediction_slot_omitted() -> None:
    card = {"size": "S", "title": "t", "key": "prop:y", "evidence": ["e"],
            "action": "a"}
    assert not any("prediction:" in ln for ln in mr.render_card(card))


def test_reconcile_predictions_three_states() -> None:
    backlog = (
        "- **[S] A**（key: prop:a）\n"
        "  - prediction: 甲月底前解锁（p=0.7；due=2026-11；对账记法=outcome 行）\n"
        "  - → outcome: y=1 (2026-11-28)\n"
        "- **[S] B**（key: prop:b）\n"
        "  - prediction: 乙季度内回落（p=0.4；due=2026-10；对账记法=outcome 行）\n"
        "  - → outcome: y=0 (2026-11-02)\n"
        "- **[S] C**（key: prop:c）\n"
        "  - prediction: 丙两周内恢复（p=0.9；due=2026-11；对账记法=outcome 行）\n"
        "- **[S] D**（key: prop:d）\n"
        "  - prediction: 丁月底前点头（p=待月末会话填写 0..1；due=2026-12；对账记法=outcome 行）\n"
    )
    out = "\n".join(mr.reconcile_predictions(backlog, "2026-12"))
    assert "(p−y)²=0.090" in out          # (0.7-1)^2，方向命中
    assert "(p−y)²=0.160" in out          # (0.4-0)^2，方向命中（低 p 押不发生）
    assert "resolved" in out
    assert "pending outcome: 丙两周内恢复（p=0.9; due 已过待记 outcome）" in out
    assert "未填 p" in out and "丁月底前点头" in out


def test_reconcile_predictions_empty_backlog() -> None:
    assert mr.reconcile_predictions("", "2026-11") == []
