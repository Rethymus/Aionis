"""Hermetic tests for the EXPLORATORY REPLAY blackbox engine
(scripts/replay_blackbox.py — replay-training-ignition, round 24).

Pure-function coverage per the mission: truncation boundary / masking SHA +
row-count assertion / p mapping / bucket aggregation / BSS ≡ 0 — plus the
freeze record-once refusal, versioned params idempotency, year chunking, and a
T1 end-to-end with an INJECTED fake blackbox (zero network, tmp_path only).
The tmp IC parquet is a labeled test fixture, never research-pipeline data.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import monthly_review as mr  # noqa: E402
import replay_blackbox as rb  # noqa: E402

# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------

def _series_months(n: int = 24, start: str = "2016-01") -> dict[str, float]:
    """Deterministic labeled series: alternating magnitudes, sign flips."""
    out: dict[str, float] = {}
    y, m = int(start[:4]), int(start[5:7])
    for i in range(n):
        out[f"{y:04d}-{m:02d}"] = (0.05 * (i + 1)) * (1 if i % 3 else -1)
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


@pytest.fixture()
def ic_parquet(tmp_path: Path) -> Path:
    """Labeled fixture: a frozen-IC parquet shaped exactly like runs/results."""
    series = _series_months()
    idx = pd.to_datetime([f"{m}-28" for m in series])
    df = pd.DataFrame({"ic": list(series.values())}, index=pd.DatetimeIndex(idx, name="date"))
    p = tmp_path / "ic_fixture.parquet"
    df.to_parquet(p)
    return p


def _config(tmp_path: Path, ic_parquet: Path, **kw) -> dict:
    return rb.build_frozen_config(ic_parquet=ic_parquet, provider_model=None, **kw)


# ---------------------------------------------------------------------------
# calendar helpers
# ---------------------------------------------------------------------------

def test_month_range_inclusive_and_errors():
    assert rb.month_range("2016-01", "2016-03") == ["2016-01", "2016-02", "2016-03"]
    assert rb.month_range("2016-12", "2017-02") == ["2016-12", "2017-01", "2017-02"]
    assert rb.month_range("2019-05", "2019-05") == ["2019-05"]
    for bad in (("2019-05", "2019-04"), ("2016-13", "2016-12"), ("201601", "2016-02")):
        with pytest.raises(rb.ReplayError) as ei:
            rb.month_range(*bad)
        assert ei.value.exit_code == rb.EXIT_USAGE


def test_chunk_years_year_boundaries():
    assert rb.chunk_years("2016-03", "2018-05") == [
        ("2016-03", "2016-12"), ("2017-01", "2017-12"), ("2018-01", "2018-05")]
    assert rb.chunk_years("2017-01", "2017-12") == [("2017-01", "2017-12")]
    assert rb.chunk_years("2020-07", "2020-07") == [("2020-07", "2020-07")]
    assert rb.chunk_years("2016-11", "2017-02") == [("2016-11", "2016-12"),
                                                    ("2017-01", "2017-02")]


# ---------------------------------------------------------------------------
# truncation boundary + structural masking (铁律 1/3)
# ---------------------------------------------------------------------------

def test_truncated_context_strict_t_minus_1_boundary():
    series = _series_months(24)  # 2016-01..2017-12
    t = "2018-01"
    ctx = rb.truncated_context(series, t, recent_k=3)
    assert ctx["rows_used"] == 24  # every month strictly before t
    assert all(m < t for m in ctx["months"])
    assert t not in ctx["last_k"] and list(ctx["last_k"]) == ["2017-10", "2017-11", "2017-12"]
    vals = list(series.values())
    assert ctx["mean_ic"] == pytest.approx(sum(vals) / 24)
    assert ctx["hit_rate_ic_pos"] == pytest.approx(sum(1 for v in vals if v > 0) / 24)
    # month at the boundary: t itself never in context
    ctx2 = rb.truncated_context(series, "2017-12", recent_k=12)
    assert ctx2["rows_used"] == 23 and "2017-12" not in ctx2["months"]


def test_truncated_context_before_series_start():
    ctx = rb.truncated_context(_series_months(6), "2015-06", recent_k=12)
    assert ctx["rows_used"] == 0
    assert ctx["mean_ic"] is None and ctx["std_ic"] is None
    assert ctx["hit_rate_ic_pos"] is None and ctx["last_k"] == {}


def test_assert_masking_raises_on_future_or_present_row():
    rb.assert_masking(["2016-01", "2016-02"], "2016-03")  # ok
    for bad_ctx, t in ((["2016-04"], "2016-03"),  # future row
                       (["2016-03"], "2016-03")):  # the month itself is future
        with pytest.raises(rb.ReplayError) as ei:
            rb.assert_masking(bad_ctx, t)
        assert ei.value.exit_code == rb.EXIT_MASKING


def test_snapshot_sha256_stable_and_order_insensitive():
    ctx = rb.truncated_context(_series_months(12), "2017-01", recent_k=12)
    assert rb.snapshot_sha256(ctx) == rb.snapshot_sha256(dict(reversed(list(ctx.items()))))
    altered = dict(ctx)
    altered["mean_ic"] = ctx["mean_ic"] + 1e-9
    assert rb.snapshot_sha256(ctx) != rb.snapshot_sha256(altered)


# ---------------------------------------------------------------------------
# y / p mapping / reply contract (design §3)
# ---------------------------------------------------------------------------

def test_y_from_ic_sign_convention():
    assert rb.y_from_ic(0.001) == 1
    assert rb.y_from_ic(5.0) == 1
    assert rb.y_from_ic(0.0) == 0       # exactly zero → not a positive claim
    assert rb.y_from_ic(-0.001) == 0


def test_map_p_answer_true_is_identity_false_is_1_minus_p():
    assert rb.map_p(True, 0.7) == pytest.approx(0.7)
    assert rb.map_p(False, 0.7) == pytest.approx(0.3)
    assert rb.map_p(True, 1.0) == pytest.approx(1.0)
    assert rb.map_p(False, 0.0) == pytest.approx(1.0)
    # defensive clamp (parser already rejects out-of-range)
    assert rb.map_p(True, 1.5) == pytest.approx(1.0)
    assert rb.map_p(False, -0.2) == pytest.approx(1.0)


def test_parse_blackbox_reply_contract():
    ok = rb.parse_blackbox_reply('{"answer": true, "p": 0.6}')
    assert ok["ok"] and ok["answer"] is True and ok["p"] == pytest.approx(0.6)
    ok2 = rb.parse_blackbox_reply('noise before {"answer": false, "p": 0.2} trailing')
    assert ok2["ok"] and ok2["answer"] is False
    for text, reason in (
            ('{"answer": "yes", "p": 0.5}', "answer-not-bool"),
            ('{"answer": true, "p": 1.5}', "p-out-of-range"),
            ('{"answer": true, "p": "high"}', "p-not-numeric"),
            ('{"p": 0.5}', "format-miss"),
            ("no json at all", "format-miss")):
        r = rb.parse_blackbox_reply(text)
        assert not r["ok"] and r["reason"] == reason, (text, r)


def test_parse_blackbox_reply_string_bool_coercion_logged():
    """Tolerance delta (tuning-log 2026-11-17): exact "true"/"false" strings
    coerce to booleans WITH an explicit marker; anything else stays a miss."""
    r = rb.parse_blackbox_reply('{"answer":"false","p":0.5}')
    assert r["ok"] and r["answer"] is False and r["p"] == pytest.approx(0.5)
    assert r["answer_coerced_from_string"] is True
    r2 = rb.parse_blackbox_reply('{"answer":"true","p":0.7}')
    assert r2["ok"] and r2["answer"] is True
    assert r2["answer_coerced_from_string"] is True
    assert not rb.parse_blackbox_reply('{"answer":"False","p":0.5}')["ok"]
    assert not rb.parse_blackbox_reply('{"answer":"yes","p":0.5}')["ok"]


# ---------------------------------------------------------------------------
# bucket aggregation via the monthly_review engine (single implementation)
# ---------------------------------------------------------------------------

def _resolved() -> list[dict]:
    return [  # p, y pairs probing every presentation path
        {"p": 0.55, "y": 1},   # [0.5,0.6)
        {"p": 0.65, "y": 0},   # [0.6,0.7)
        {"p": 1.0, "y": 1},    # top bucket closed at 1.0
        {"p": 0.45, "y": 0},   # p<0.5 → 分列不计桶
    ]


def test_chunk_summary_lines_uses_monthly_review_engine():
    from statsmodels.stats.proportion import proportion_confint
    lines = rb.chunk_summary_lines(_resolved())
    text = "\n".join(lines)
    # Wilson CI numbers must be the statsmodels numbers (same engine, not a re-derivation)
    lo, hi = proportion_confint(1, 1, method="wilson")
    assert f"p∈[0.5,0.6): n=1、命中 1（1.000）、Wilson 95% CI ({lo:.4f}, {hi:.4f})" in text
    assert "p∈[0.9,1.0]: n=1、命中 1（1.000）" in text
    # engine semantics for p<0.5 rows: 命中 counts y==0 (aligned outcome)
    assert "分列不计桶：p<0.5 已对账 1 条（命中 1）" in text
    # mean Brier matches the manual computation
    mean_brier = sum((r["p"] - r["y"]) ** 2 for r in _resolved()) / 4
    assert f"汇总 mean Brier = {mean_brier:.3f}" in text
    # BSS components line present and equal to the engine values
    bs, bs_base, p_bar, bss = mr._bss_components(_resolved())
    assert f"bs={bs:.6f}、bs_base={bs_base:.6f}" in text
    assert f"BSS={bss:.6f}" in text


# ---------------------------------------------------------------------------
# T0: BSS ≡ 0 constructive + coverage hard-check
# ---------------------------------------------------------------------------

def test_load_ic_series_and_y(tmp_path: Path, ic_parquet: Path):
    series = rb.load_ic_series(ic_parquet)
    assert len(series) == 24 and series["2016-01"] == pytest.approx(-0.05)
    with pytest.raises(rb.ReplayError) as ei:
        rb.load_ic_series(tmp_path / "missing.parquet")
    assert ei.value.exit_code == rb.EXIT_Y_SOURCE


def test_t0_bss_zero_by_construction(tmp_path: Path, ic_parquet: Path):
    series = rb.load_ic_series(ic_parquet)
    result = rb.run_t0(_config(tmp_path, ic_parquet), series, "2016-01", "2017-12",
                       run_dir=tmp_path / "run")
    recs = result["records"]
    assert len(recs) == 24
    p_bar = result["bss_check"]["p_bar"]
    assert all(r["p"] == p_bar for r in recs)          # constant climatology p
    assert abs(result["bss_check"]["bss"]) < 1e-12     # BSS ≡ 0 exact
    # artifacts: header + 24 rows, honest summary, manifest
    lines = (tmp_path / "run" / "month-records.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 25 and json.loads(lines[0])["_header"]["tier"] == "t0"
    summary = (tmp_path / "run" / "t0-summary.md").read_text(encoding="utf-8")
    assert "BSS≡0 构造性断言" in summary and "PASS" in summary
    assert rb.EXPLORATORY_LABEL in summary
    manifest = json.loads((tmp_path / "run" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["tier"] == "t0" and manifest["n_records"] == 24


def test_t0_bss_nonzero_raises_exit5_and_degenerate_base():
    recs = [{"p": 0.7, "y": 1}, {"p": 0.2, "y": 0}, {"p": 0.9, "y": 1}]  # p ≠ p̄
    with pytest.raises(rb.ReplayError) as ei:
        rb.assert_t0_bss_zero(recs)
    assert ei.value.exit_code == rb.EXIT_T0_BSS
    degenerate = [{"p": 0.6, "y": 1}, {"p": 0.6, "y": 1}]  # all y=1 → bs_base=0 → bss None
    with pytest.raises(rb.ReplayError) as ei2:
        rb.assert_t0_bss_zero(degenerate)
    assert ei2.value.exit_code == rb.EXIT_T0_BSS


def test_climatology_records_coverage_hole_exits_4():
    series = _series_months(12)  # 2016-01..2016-12
    with pytest.raises(rb.ReplayError) as ei:
        rb.climatology_records(series, "2016-01", "2017-02", tier="t0")
    assert ei.value.exit_code == rb.EXIT_Y_SOURCE
    assert "2017-01" in ei.value.message


# ---------------------------------------------------------------------------
# freeze: record-once + tuning-log template with implicit-trial counters
# ---------------------------------------------------------------------------

def test_freeze_record_once_and_tuning_log_template(tmp_path: Path, ic_parquet: Path):
    cfg = _config(tmp_path, ic_parquet, recent_k=12, top_n_lessons=3)
    cfg_path, sha = rb.freeze(tmp_path / "out", cfg)
    on_disk = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert on_disk["exploratory"] is True and on_disk["kind"] == "replay-blackbox-config-frozen"
    assert rb.EXPLORATORY_LABEL in on_disk["label"]
    assert on_disk["windows"]["training"] == {"from": "2016-01", "to": "2025-12", "months": 120}
    assert on_disk["windows"]["frozen_validation"] == {"from": "2026-01", "to": "2026-10",
                                                       "months": 10}
    assert on_disk["cut"]["train_to"] == "2025-12" and on_disk["cut"]["val_from"] == "2026-01"
    assert on_disk["provider"]["name"] == "glm" and on_disk["provider"]["temperature"] == 0.1
    assert on_disk["p_mapping"]["rule"] == "p = p_raw if answer is True else 1 - p_raw"
    assert on_disk["injection_budget"]["top_n_lessons"] == 3
    assert on_disk["bucket_cuts"] == list(mr._CALIBRATION_BAND_CUTS)
    assert sha == rb.sha256_file(cfg_path)
    sidecar = (tmp_path / "out" / "config-frozen.sha256").read_text(encoding="utf-8")
    assert sidecar.startswith(sha)
    tuning = (tmp_path / "out" / "tuning-log.md").read_text(encoding="utf-8")
    for knob in ("prompt_template", "bucket_cuts", "top_n_lessons",
                 "bounded_context", "thresholds"):
        assert f"- {knob}: 0" in tuning  # implicit-trial counters seeded at 0
    assert "隐式试验计数" in tuning
    # record-once: second freeze refused, tuning-log untouched
    with pytest.raises(rb.ReplayError) as ei:
        rb.freeze(tmp_path / "out", cfg)
    assert ei.value.exit_code == rb.EXIT_FREEZE_OVERWRITE
    assert (tmp_path / "out" / "tuning-log.md").read_text(encoding="utf-8") == tuning


def test_build_frozen_config_missing_y_source(tmp_path: Path):
    with pytest.raises(rb.ReplayError) as ei:
        rb.build_frozen_config(ic_parquet=tmp_path / "nope.parquet", provider_model=None)
    assert ei.value.exit_code == rb.EXIT_Y_SOURCE


# ---------------------------------------------------------------------------
# params versioning (idempotent, content-addressed)
# ---------------------------------------------------------------------------

def test_version_params_content_addressed_idempotent(tmp_path: Path):
    sha1, p1 = rb.version_params({"top_n_lessons": 2}, tmp_path)
    assert p1.exists() and json.loads(p1.read_text(encoding="utf-8"))["params"] == \
        {"top_n_lessons": 2}
    sha2, p2 = rb.version_params({"top_n_lessons": 2}, tmp_path)
    assert sha1 == sha2 and p1 == p2  # idempotent
    sha3, p3 = rb.version_params({"top_n_lessons": 3, "recent_k": 6}, tmp_path)
    assert sha3 != sha1 and p3 != p1
    assert rb.EXPLORATORY_LABEL in p3.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# prompt assembly: bounded-context contract visible in the archived prompt
# ---------------------------------------------------------------------------

def test_build_prompt_bounded_context_and_top_n_lessons():
    cfg = {"claim_form": {"claim_template": "{month} 月 realized rank-IC 为正"},
           "injection_budget": {"top_n_lessons": 2}}
    ctx = rb.truncated_context(_series_months(24), "2018-01", recent_k=3)
    system, user = rb.build_prompt(cfg, "2018-01", ctx,
                                   [f"lesson{i}" for i in range(5)])
    assert "single line" in system.lower() or "SINGLE LINE" in system
    assert "2018-01 月 realized rank-IC 为正" in user
    assert "months_used=24" in user and "every month < 2018-01" in user
    assert "2017-12=" in user  # newest last_k value present
    for i in range(2):
        assert f"lesson{i}" in user
    assert "lesson2" not in user and "lesson4" not in user  # top-N budget enforced
    assert "@CLAIM@" not in user and "@MONTH@" not in user  # tokens fully replaced


# ---------------------------------------------------------------------------
# T1 end-to-end with an injected fake blackbox (zero network, tmp only)
# ---------------------------------------------------------------------------

def test_t1_fake_blackbox_end_to_end(tmp_path: Path, ic_parquet: Path):
    series = rb.load_ic_series(ic_parquet)
    cfg = _config(tmp_path, ic_parquet)

    def fake_ask(system: str, user: str) -> str:
        month = user.split("due month: ")[1].split(";")[0]
        idx = list(series).index(month)
        if idx % 2 == 0:
            return '{"answer": true, "p": 0.6}'
        return '{"answer": false, "p": 0.3}'

    result = rb.run_t1(cfg, series, "2016-01", "2017-12", tmp_path / "run",
                       ask=fake_ask, lessons=["l1", "l2", "l3", "l4"],
                       params_meta={"sha256": "ab" * 32})
    recs = result["records"]
    assert len(recs) == 24
    for i, rec in enumerate(recs):
        expected_p = 0.6 if i % 2 == 0 else 0.7   # map_p applied to {answer, p}
        assert rec["p"] == pytest.approx(expected_p)
        assert rec["y"] == rb.y_from_ic(series[rec["month"]])
        assert rec["err"] == pytest.approx((rec["p"] - rec["y"]) ** 2)
        assert rec["rows_used"] == list(series).index(rec["month"])
        assert rec["masking_ok"] is True and rec["snapshot_sha256"]
        assert rec["chunk"] == rec["month"][:4]
    # structural masking actually exercised by the loop (not just recorded)
    rb.assert_masking(rb.truncated_context(series, "2017-06", 12)["months"], "2017-06")
    lines = (tmp_path / "run" / "month-records.jsonl").read_text(
        encoding="utf-8").splitlines()
    assert len(lines) == 25 and json.loads(lines[0])["_header"]["tier"] == "t1"
    assert "due month: 2016-01" in json.loads(lines[1])["prompt"]
    summaries = (tmp_path / "run" / "chunk-summaries.md").read_text(encoding="utf-8")
    assert "## chunk 2016 [2016-01..2016-12] — 12 months" in summaries
    assert "## chunk 2017 [2017-01..2017-12] — 12 months" in summaries
    assert "## full window [2016-01..2017-12] — 24 months" in summaries
    assert "Wilson 95% CI" in summaries and "BSS components" in summaries
    manifest = result["manifest"]
    assert manifest["tier"] == "t1" and manifest["chunks"] == [["2016-01", "2016-12"],
                                                              ["2017-01", "2017-12"]]
    assert manifest["lessons_provided"] == 4 and manifest["lessons_injected_top_n"] == 3
    assert manifest["params"] == {"sha256": "ab" * 32}
    assert manifest["honest_notes"] and any("ledger" in n for n in manifest["honest_notes"])


def test_t1_contract_failure_exits_6(tmp_path: Path, ic_parquet: Path):
    series = rb.load_ic_series(ic_parquet)
    cfg = _config(tmp_path, ic_parquet)
    with pytest.raises(rb.ReplayError) as ei:
        rb.run_t1(cfg, series, "2016-01", "2016-02", tmp_path / "run",
                  ask=lambda s, u: '{"answer": "yes", "p": 0.5}')
    assert ei.value.exit_code == rb.EXIT_LLM_CONTRACT
    assert (tmp_path / "run" / "contract-fail-2016-01.txt").exists()


def test_t1_masking_violation_exits_7(tmp_path: Path, ic_parquet: Path, monkeypatch):
    series = rb.load_ic_series(ic_parquet)
    cfg = _config(tmp_path, ic_parquet)
    monkeypatch.setattr(rb, "truncated_context",
                        lambda s, t, k: {"up_to": t, "rows_used": 2,
                                         "months": ["2017-01"],  # future row for t=2016-01
                                         "mean_ic": 0.0, "std_ic": None,
                                         "hit_rate_ic_pos": 0.5, "last_k": {}})
    with pytest.raises(rb.ReplayError) as ei:
        rb.run_t1(cfg, series, "2016-01", "2016-02", tmp_path / "run",
                  ask=lambda s, u: '{"answer": true, "p": 0.5}')
    assert ei.value.exit_code == rb.EXIT_MASKING


# ---------------------------------------------------------------------------
# CLI wiring: exit codes + UTF-8 (main() invoked directly, tmp only)
# ---------------------------------------------------------------------------

def test_main_freeze_then_t0_then_exit_codes(tmp_path: Path, ic_parquet: Path,
                                             capsys):
    out = tmp_path / "out"
    assert rb.main(["--freeze", "--out", str(out),
                    "--ic-parquet", str(ic_parquet)]) == rb.EXIT_OK
    printed = capsys.readouterr().out
    assert rb.EXPLORATORY_LABEL in printed
    assert rb.main(["--freeze", "--out", str(out),
                    "--ic-parquet", str(ic_parquet)]) == rb.EXIT_FREEZE_OVERWRITE
    # t0 without a config → EXIT_CONFIG (3)
    assert rb.main(["--tier", "t0", "--out", str(tmp_path / "empty")]) == rb.EXIT_CONFIG
    # t0 with the frozen config → EXIT_OK, coverage checked against the fixture
    assert rb.main(["--tier", "t0", "--out", str(out), "--from", "2016-01",
                    "--to", "2017-12"]) == rb.EXIT_OK
    t0_out = capsys.readouterr().out
    assert "BSS≡0 PASS" in t0_out
    # coverage hole via CLI → EXIT_Y_SOURCE (4)
    assert rb.main(["--tier", "t0", "--out", str(out), "--from", "2016-01",
                    "--to", "2019-12"]) == rb.EXIT_Y_SOURCE


def test_main_t1_params_and_lessons_validation(tmp_path: Path, ic_parquet: Path):
    out = tmp_path / "out"
    rb.freeze(out, _config(tmp_path, ic_parquet))
    bad = tmp_path / "params.json"
    bad.write_text("{not json", encoding="utf-8")
    assert rb.main(["--tier", "t1", "--out", str(out), "--from", "2016-01",
                    "--to", "2016-03", "--params", str(bad)]) == rb.EXIT_USAGE
    arr = tmp_path / "lessons.json"
    arr.write_text('["a", 2]', encoding="utf-8")
    assert rb.main(["--tier", "t1", "--out", str(out), "--from", "2016-01",
                    "--to", "2016-03", "--lessons", str(arr)]) == rb.EXIT_USAGE


# ---------------------------------------------------------------------------
# T2 provider-contrast arm: --provider resolution + zero-lessons red line
# ---------------------------------------------------------------------------

def test_provider_resolution_default_and_override():
    # No CLI flag → frozen provider (glm), no override marker.
    assert rb.resolve_effective_provider("glm", None) == ("glm", None)
    # Explicit flag EQUAL to the frozen name → still no override marker.
    assert rb.resolve_effective_provider("glm", "glm") == ("glm", None)
    # Differing flag → run-time override meta (frozen bytes untouched).
    name, meta = rb.resolve_effective_provider("glm", "siliconflow")
    assert name == "siliconflow"
    assert meta["kind"] == "provider-contrast-override"
    assert meta["from_frozen"] == "glm" and meta["to"] == "siliconflow"
    assert "ZERO lessons" in meta["note"] and "EXPLORATORY REPLAY" in meta["note"]


def test_main_provider_contrast_refuses_lessons(tmp_path: Path, ic_parquet: Path):
    out = tmp_path / "out"
    rb.freeze(out, _config(tmp_path, ic_parquet))
    lessons = tmp_path / "lessons.json"
    lessons.write_text('["some lesson"]', encoding="utf-8")
    # Contrast arm red line: --lessons + differing --provider → EXIT_USAGE,
    # refused BEFORE any provider/network work.
    assert rb.main(["--tier", "t1", "--out", str(out), "--from", "2016-01",
                    "--to", "2016-03", "--provider", "siliconflow",
                    "--lessons", str(lessons)]) == rb.EXIT_USAGE


# ---------------------------------------------------------------------------
# holdout-pairing（2026-11-18）: --params calibration_mapping forward-only 应用
# + --lessons .md 编号条目装载
# ---------------------------------------------------------------------------

def test_t1_calibration_mapping_applied_and_recorded(tmp_path: Path, ic_parquet: Path):
    series = rb.load_ic_series(ic_parquet)
    cfg = _config(tmp_path, ic_parquet)

    def fake_ask(system: str, user: str) -> str:
        month = user.split("due month: ")[1].split(";")[0]
        idx = list(series).index(month)
        return '{"answer": true, "p": 0.6}' if idx % 2 == 0 else \
            '{"answer": false, "p": 0.3}'

    mapping = (2.0, -1.0)
    result = rb.run_t1(cfg, series, "2016-01", "2016-03", tmp_path / "run",
                       ask=fake_ask, mapping=mapping)
    recs = result["records"]
    assert len(recs) == 3
    for i, rec in enumerate(recs):
        base = rb.map_p(rec["answer"], rec["p_raw"])
        expected = 1.0 / (1.0 + math.exp(-(mapping[0] * base + mapping[1])))
        assert rec["p"] == pytest.approx(expected)
        assert rec["p_raw"] == (0.6 if i % 2 == 0 else 0.3)  # p_raw 语义不变
        assert rec["p_pre_mapping"] == pytest.approx(base)
        assert rec["err"] == pytest.approx((rec["p"] - rec["y"]) ** 2)
    assert recs[0]["p"] == pytest.approx(0.549834, abs=1e-5)   # σ(2·0.6−1)
    assert recs[1]["p"] == pytest.approx(0.598688, abs=1e-5)   # σ(2·0.7−1)
    # 无映射对照：记录形状零变化（epoch-1 历史逐字节兼容）
    result0 = rb.run_t1(cfg, series, "2016-01", "2016-02", tmp_path / "run0",
                        ask=fake_ask)
    assert all("p_pre_mapping" not in r for r in result0["records"])
    assert all("p_pre_mapping" in r for r in recs)


def test_t1_calibration_mapping_rejected_non_monotone(tmp_path: Path, ic_parquet: Path):
    series = rb.load_ic_series(ic_parquet)
    cfg = _config(tmp_path, ic_parquet)
    with pytest.raises(rb.ReplayError) as ei:
        rb.run_t1(cfg, series, "2016-01", "2016-02", tmp_path / "run",
                  ask=lambda s, u: '{"answer": true, "p": 0.6}',
                  mapping=(-1.0, 0.0))
    assert ei.value.exit_code == rb.EXIT_USAGE


def test_load_lessons_md_numbered_entries(tmp_path: Path):
    md = tmp_path / "lessons.md"
    md.write_text(
        "# lessons 库\n\n**准入判据**（元说明，非条目）\n\n"
        "1. **端点置信慎用**——端点值慎用。\n"
        "   〔数据面：2017-02、2017-05〕\n"
        "2. **高置信带**——频率差约 0.09，同类情境收半档。〔2016-05、2016-10〕\n",
        encoding="utf-8")
    lessons = rb.load_lessons_file(md)
    assert len(lessons) == 2
    assert lessons[0].startswith("1. **端点置信慎用**") and "数据面" in lessons[0]
    assert lessons[1].startswith("2. **高置信带**")
    empty = tmp_path / "empty.md"
    empty.write_text("# 无编号条目的文档\n\n正文段落。\n", encoding="utf-8")
    with pytest.raises(rb.ReplayError) as ei:
        rb.load_lessons_file(empty)
    assert ei.value.exit_code == rb.EXIT_USAGE


def test_main_provider_contrast_refuses_mapping(tmp_path: Path, ic_parquet: Path):
    out = tmp_path / "out"
    rb.freeze(out, _config(tmp_path, ic_parquet))
    params = tmp_path / "params.json"
    params.write_text(json.dumps(
        {"kind": "replay-params-current",
         "calibration_mapping": {"a": 2.0, "b": -1.0}}), encoding="utf-8")
    # 对比臂红线：映射随冻结 provider 输出拟合——--provider 差异臂必须 identity。
    assert rb.main(["--tier", "t1", "--out", str(out), "--from", "2016-01",
                    "--to", "2016-03", "--provider", "siliconflow",
                    "--params", str(params)]) == rb.EXIT_USAGE
