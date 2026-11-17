"""EXPLORATORY REPLAY blackbox engine (replay-training-ignition, round 24).

Design: reports/design/2026-11-17-replay-training-ignition.md (§1 三段式, §2 四条铁律,
§3 y 源与覆盖审计, §4 调参治理, §6 三层执行). This script is the OPS-LANE engine for
the historical black-box replay drill:

- ``--freeze``   write config-frozen.json + SHA256 sidecar + tuning-log.md template
                 (铁律 4: 配置先冻结后观察; record-once — refuses to overwrite).
- ``--tier t0``  climatology baseline over the full window, ZERO LLM. p = p̄
                 (full-window hit-rate climatology) constant ⇒ BSS ≡ 0 BY
                 CONSTRUCTION; non-zero BSS = engine bug (exit 5).
- ``--tier t1``  year-boundary chunked monthly loop: t-round context truncated to
                 strictly t-1 (structural masking, asserted rows ≤ t-1 + per-month
                 context snapshot SHA256) → blackbox reply (GLM via the OpenAI-
                 compatible client, JSON mode temp 0.1, single-line {answer, p}) →
                 y = 1[IC_t > 0] → (p−y)² → monthly records (prompt + reply + error +
                 snapshot SHA + row assertion) → chunk-end bucketing + Wilson CI + BSS
                 via the monthly_review engine functions (SINGLE implementation,
                 verbatim reuse — no re-derivation here).

RED LINES (design §2 铁律 2 + AGENTS.md):
- ZERO writes to runs/ledger.jsonl, state/calibration-months.md, or any research
  face (src/aionis/, scripts/phase_*). The only reads outside reports/ are the
  frozen IC parquet named in the config.
- Everything this script writes lands under --out (default
  reports/exploratory/replay/) and carries the EXPLORATORY REPLAY label:
  not a claim, not a gate.
- Bounded context contract (design §2 铁律 1 + 调研 arXiv:2601.13770): the prompt
  feeds ONLY a self-produced rolling summary of the realized-IC series strictly
  before t — never an open macro narrative or calendar-anchored story. Masking is
  STRUCTURAL, not assumed: GLM is a standard-LLM-class model whose parametric
  look-ahead cannot be assumed away; the mitigation is that the claim targets an
  internal, non-public IC series and the context is bounded + archived (snapshot
  SHA256 + rows ≤ t-1 assertion per month, design §2 铁律 3).
- tuning-log.md template carries the implicit-trial counters (调研 arXiv:2608.27734:
  cumulative change counts per knob class, INCLUDING implicit trials, make the
  training trajectory's search intensity auditable).

Exit codes: 0 ok · 2 usage/config args · 3 config-frozen missing/corrupt ·
4 y-source missing/coverage hole · 5 T0 BSS ≠ 0 · 6 blackbox reply contract
failure · 7 masking assertion failure · 8 freeze overwrite refused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import monthly_review as mr  # same directory — engine functions, single implementation
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "reports" / "exploratory" / "replay"
DESIGN_REF = "reports/design/2026-11-17-replay-training-ignition.md"
EXPLORATORY_LABEL = (
    "EXPLORATORY REPLAY — not a claim, not a gate "
    f"(design: {DESIGN_REF}; zero runs/ledger.jsonl writes; research face untouched)"
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_CONFIG = 3
EXIT_Y_SOURCE = 4
EXIT_T0_BSS = 5
EXIT_LLM_CONTRACT = 6
EXIT_MASKING = 7
EXIT_FREEZE_OVERWRITE = 8

EXIT_CODE_NAMES = {
    EXIT_OK: "ok",
    EXIT_USAGE: "usage/config-args invalid",
    EXIT_CONFIG: "config-frozen missing/corrupt",
    EXIT_Y_SOURCE: "y-source missing/coverage hole",
    EXIT_T0_BSS: "T0 BSS != 0 (engine bug)",
    EXIT_LLM_CONTRACT: "blackbox reply contract failure",
    EXIT_MASKING: "masking assertion failure (future rows in context)",
    EXIT_FREEZE_OVERWRITE: "freeze refused (config exists; record-once)",
}

# Design §1 defaults (owner 2026-11-17; change = NEW freeze, never in-place).
TRAINING_DEFAULT = ("2016-01", "2025-12")
VALIDATION_DEFAULT = ("2026-01", "2026-10")
ONLINE_START_DEFAULT = "2026-11-30"

RECENT_K_DEFAULT = 12          # last-k realized-IC values shown in bounded context
TOP_N_LESSONS_DEFAULT = 3      # injection budget (design §4 可动清单)
CALL_SPACING_S = 2.0           # glm catalog rpm=30 → ~2s spacing keeps ~RPM/2 headroom;
                               # model APIs exempt from the ≥2s host-spacing rule
                               # (AGENTS.md politeness 口径), spacing here is pure
                               # RPM hygiene for the thin direct client.

# v1 单族 default y source: the Phase D confirmatory treatment IC (realized
# rank-IC). Coverage audit 2026-11-17: 2016-01→2026-05 continuous, 125 months,
# zero gaps/NaN (reports/audits/2026-11-17-iterate-round-24.md). Changing the
# y source = NEW freeze (record-once), never a silent swap.
Y_SOURCE_DEFAULT = (
    "runs/results/"
    "d31580630ff35326557dda9f50832c7af3625dd6507e47e252ea01800372a12c/ic_state.parquet"
)

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# T2 provider-contrast arm (mission 2026-11-17): --provider choices. The
# frozen config's provider (glm) stays the default and its BYTES never
# change; a differing --provider is a run-time override recorded in the run
# manifest. Contrast arm red lines: ZERO lessons (identity is GLM-bound —
# structurally refused below), EXPLORATORY REPLAY products only.
PROVIDER_CHOICES = ("glm", "siliconflow")

PROMPT_SYSTEM = """\
You are the blackbox predictor in a calibration replay drill
(EXPLORATORY REPLAY — not a claim, not a gate).

Each turn gives ONE claim about month t and a BOUNDED context: rolling statistics
of the realized rank-IC series STRICTLY BEFORE t (self-produced; the engine
asserts every context row is < t). Hard rules:
- Reply with a SINGLE LINE of JSON, exactly:
  {"answer": <true|false>, "p": <number between 0 and 1>}
- "answer" = your judgment on the claim; "p" = your probability that your answer
  is correct.
- Use ONLY the provided bounded context. The realized rank-IC is an internal,
  project-computed quantity no external corpus contains: do NOT substitute macro
  narratives, market memory, or calendar reasoning for it.
- No prose outside the JSON. No tools. No follow-up questions.
"""

# Token-based template (no str.format brace-escaping traps): @CLAIM@ @MONTH@
# @CONTEXT@ @TOPN@ @LESSONS@.
PROMPT_USER_TEMPLATE = """\
Claim: @CLAIM@   (due month: @MONTH@; you answer at the t-1 information boundary)

Bounded context — realized rank-IC history strictly before @MONTH@ (self-produced):
@CONTEXT@

Active lessons (top-@TOPN@, distilled from EARLIER chunks only; never future data):
@LESSONS@

Answer now with a single line of JSON: {"answer": <true|false>, "p": <0..1>}
"""

TUNING_LOG_TEMPLATE = """\
# tuning-log — 训练期调参日志（EXPLORATORY REPLAY，append-only）

> 纪律（设计 §4）：年界检查点内逐轮不调参；每条 delta 记 旧值/新值/依据轮次区间。
> 隐式试验计数（arXiv:2608.27734 口径）：每旋钮类累计改动次数——**含未落 delta 的
> 隐式试错**（改了又改回、prompt 微调重试）——训练轨迹搜索强度可审计。

## 隐式试验计数器（累计，逐次 +1，含隐式试错）

- prompt_template: 0
- bucket_cuts: 0
- top_n_lessons: 0
- bounded_context: 0
- thresholds: 0

## 调参 delta 表（append-only，不回改；写错=文末勘误行）

| 日期 | 检查点(年界) | 旋钮类 | 旧值 | 新值 | 依据轮次区间 | 计数器变化 |
|---|---|---|---|---|---|---|
"""


class ReplayError(Exception):
    """Carries the semantic exit code (⑦ 退出码语义化)."""

    def __init__(self, exit_code: int, message: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.message = message


# ---------------------------------------------------------------------------
# pure calendar / series helpers
# ---------------------------------------------------------------------------

def _check_month(ym: str, what: str) -> str:
    if not isinstance(ym, str) or not MONTH_RE.match(ym):
        raise ReplayError(EXIT_USAGE, f"{what} must be YYYY-MM, got {ym!r}")
    return ym


def month_range(from_ym: str, to_ym: str) -> list[str]:
    """Inclusive monthly 'YYYY-MM' list; invalid or reversed → EXIT_USAGE."""
    _check_month(from_ym, "--from")
    _check_month(to_ym, "--to")
    if from_ym > to_ym:
        raise ReplayError(EXIT_USAGE, f"window reversed: {from_ym} > {to_ym}")
    y, m = int(from_ym[:4]), int(from_ym[5:7])
    out = []
    while f"{y:04d}-{m:02d}" <= to_ym:
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def chunk_years(from_ym: str, to_ym: str) -> list[tuple[str, str]]:
    """年界分块 (design §6): split the window at every calendar-year boundary."""
    chunks: list[list[str]] = []
    for m in month_range(from_ym, to_ym):
        if not chunks or chunks[-1][1][:4] != m[:4]:
            chunks.append([m, m])
        else:
            chunks[-1][1] = m
    return [(a, b) for a, b in chunks]


def load_ic_series(parquet_path: Path) -> dict[str, float]:
    """Frozen-IC parquet → {'YYYY-MM': ic}. Missing/NaN/duplicates → EXIT_Y_SOURCE."""
    if not parquet_path.exists():
        raise ReplayError(EXIT_Y_SOURCE, f"y-source parquet missing: {parquet_path}")
    df = pd.read_parquet(parquet_path)
    if "ic" not in df.columns:
        raise ReplayError(EXIT_Y_SOURCE,
                          f"y-source parquet lacks 'ic' column: {list(df.columns)}")
    idx = pd.to_datetime(df.index)
    months = [f"{t.year:04d}-{t.month:02d}" for t in idx]
    if len(months) != len(set(months)):
        raise ReplayError(EXIT_Y_SOURCE, "y-source parquet has duplicate months")
    series = {m: float(v)
              for m, v in zip(months, df["ic"].tolist(), strict=True)}
    if any(m != m for m in series.values()):  # NaN check (NaN != NaN)
        raise ReplayError(EXIT_Y_SOURCE, "y-source parquet has NaN ic values")
    return series


def y_from_ic(ic: float) -> int:
    """y = 1[IC_t > 0] (design §3); exactly-zero IC → 0 (no positive claim)."""
    return 1 if ic > 0 else 0


def truncated_context(series: dict[str, float], t: str, recent_k: int) -> dict:
    """BOUNDED context (design §2 铁律 1 + arXiv:2601.13770): ONLY months < t.

    Self-produced rolling stats of the realized-IC series — no macro narrative,
    no calendar-anchored story. rows_used is asserted against the series by
    assert_masking(); the caller archives snapshot_sha256(context) per month.
    """
    prior = {m: v for m, v in sorted(series.items()) if m < t}
    vals = list(prior.values())
    n = len(vals)
    mean_ic = sum(vals) / n if n else None
    std_ic = ((sum((v - mean_ic) ** 2 for v in vals) / (n - 1)) ** 0.5
              if n >= 2 else None)
    hit_rate = (sum(1 for v in vals if v > 0) / n) if n else None
    return {
        "up_to": t,
        "rows_used": n,
        "months": list(prior.keys()),
        "mean_ic": mean_ic,
        "std_ic": std_ic,
        "hit_rate_ic_pos": hit_rate,
        "last_k": dict(list(prior.items())[-recent_k:]),
    }


def assert_masking(context_months: list[str], t: str) -> None:
    """行数断言 (design §2 铁律 3): every context month must be strictly < t.

    Violation → EXIT_MASKING. This is the STRUCTURAL masking guarantee — the
    archive (snapshot SHA + rows_used) makes 'didn't peek' auditable, not assumed.
    """
    bad = [m for m in context_months if m >= t]
    if bad:
        raise ReplayError(
            EXIT_MASKING,
            f"context for {t} contains {len(bad)} non-prior month(s), "
            f"e.g. {bad[:3]} — masking assertion failed (rows must be ≤ t-1)")


def snapshot_sha256(context: dict) -> str:
    """SHA256 of the canonical JSON of the month's bounded context (掩蔽证明)."""
    return sha256_hex(context)


def sha256_hex(obj) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# reply contract + p mapping (design §3 p 映射)
# ---------------------------------------------------------------------------

def parse_blackbox_reply(text: str) -> dict:
    """Parse the single-line {answer, p} contract. Extends
    monthly_review.parse_bounded_answer with the replay-specific strictness that
    answer must be a JSON boolean (probe-grade honesty: unparsable ⇒ format-miss
    marker, raw text stays on record, nothing invented). Tolerance delta
    (tuning-log 2026-11-17, chunk-2016 checkpoint): a JSON string "true"/"false"
    is coerced to the boolean with an explicit answer_coerced_from_string marker
    on the returned dict — the model's intent is unambiguous, and the coercion is
    logged, never silent."""
    r = mr.parse_bounded_answer(text)
    if r.get("ok") and not isinstance(r["answer"], bool):
        if r["answer"] in ("true", "false"):
            return {"ok": True, "answer": r["answer"] == "true", "p": r["p"],
                    "answer_coerced_from_string": True}
        return {"ok": False, "reason": "answer-not-bool", "raw": r.get("raw", "")}
    return r


def map_p(answer: bool, p: float) -> float:
    """p 映射 (design §3): p = p_raw if answer is True else 1 − p_raw.

    After mapping, p = P(claim true) = P(IC_t > 0) — the calibration target.
    Defensive clamp to [0, 1] (the parser already rejects out-of-range p).
    """
    p = min(1.0, max(0.0, float(p)))
    return p if answer else 1.0 - p


# ---------------------------------------------------------------------------
# climatology aggregation + T0 (design §6 T0: BSS ≡ 0 constructive)
# ---------------------------------------------------------------------------

def climatology_records(series: dict[str, float], from_ym: str, to_ym: str,
                        tier: str) -> list[dict]:
    """Coverage hard-check + y/err per month. Missing y in window → EXIT_Y_SOURCE
    (a silently-shrunken window would falsify the drill; exit code, not a skip)."""
    months = month_range(from_ym, to_ym)
    missing = [m for m in months if m not in series]
    if missing:
        raise ReplayError(
            EXIT_Y_SOURCE,
            f"y-source coverage hole in [{from_ym}..{to_ym}]: {len(missing)} month(s) "
            f"missing, first={missing[0]} last={missing[-1]} — freeze a config whose "
            "y source covers the window (audit: reports/audits/2026-11-17-iterate-round-24.md)")
    p_bar = (sum(y_from_ic(series[m]) for m in months) / len(months))
    return [{
        "month": m,
        "tier": tier,
        "p": p_bar,
        "y": y_from_ic(series[m]),
        "err": (p_bar - y_from_ic(series[m])) ** 2,
        "label": EXPLORATORY_LABEL,
    } for m in months]


def assert_t0_bss_zero(records: list[dict]) -> dict:
    """T0's constructive expectation (design §6): model p IS p̄ ⇒ BSS ≡ 0.
    Non-zero → engine bug → EXIT_T0_BSS. Uses mr._bss_components verbatim so the
    gate, the monthly snapshot, and T0 read ONE implementation."""
    comp = mr._bss_components(records)
    if comp is None:
        raise ReplayError(EXIT_T0_BSS, "no rows to score — T0 window empty?")
    bs, bs_base, p_bar, bss = comp
    if bss is None or abs(bss) > 1e-12:
        raise ReplayError(
            EXIT_T0_BSS,
            f"T0 BSS={bss} must be ≡ 0 by construction (bs={bs} bs_base={bs_base} "
            f"p̄={p_bar}) — engine bug")
    return {"bs": bs, "bs_base": bs_base, "p_bar": p_bar, "bss": bss}


# ---------------------------------------------------------------------------
# chunk-end aggregation: monthly_review engine functions (single implementation)
# ---------------------------------------------------------------------------

def chunk_summary_lines(records: list[dict]) -> list[str]:
    """分桶 + Wilson CI + Brier (mr.calibration_bucket_summary) + BSS components
    (mr._bss_components) — the SAME engine the gate and monthly snapshot read."""
    lines = list(mr.calibration_bucket_summary(records))
    comp = mr._bss_components(records)
    if comp is not None:
        bs, bs_base, p_bar, bss = comp
        tail = (f"BSS={bss:.6f}" if bss is not None
                else f"BSS 无定义（p̄={p_bar:.4f} 退化，诚实降级不造假分）")
        lines.append(f"  - BSS components: bs={bs:.6f}、bs_base={bs_base:.6f}、{tail}")
    return lines


# ---------------------------------------------------------------------------
# prompt assembly (bounded context contract)
# ---------------------------------------------------------------------------

def _fmt(v: float | None) -> str:
    return "n/a (no prior rows)" if v is None else f"{v:+.6f}"


def build_prompt(config: dict, month: str, context: dict,
                 lessons: list[str]) -> tuple[str, str]:
    """Assemble (system, user) from the FROZEN templates. Deterministic; the
    context block carries rows_used + the masking assertion text so the archived
    prompt itself is the masking evidence."""
    last = context["last_k"]
    ctx_lines = [
        f"- months_used={context['rows_used']} (engine-asserted: every month < {month})",
        f"- mean_ic={_fmt(context['mean_ic'])}  std_ic={_fmt(context['std_ic'])}  "
        f"hit_rate_ic_pos={_fmt(context['hit_rate_ic_pos'])}",
        "- last_k (oldest→newest): "
        + (", ".join(f"{m}={v:+.4f}" for m, v in last.items())
           if last else "(empty — series starts at this month)"),
    ]
    top_n = int(config["injection_budget"]["top_n_lessons"])
    lesson_lines = [f"- {s}" for s in lessons[:top_n]] or ["- (none)"]
    user = (PROMPT_USER_TEMPLATE
            .replace("@CLAIM@", config["claim_form"]["claim_template"].format(month=month))
            .replace("@MONTH@", month)
            .replace("@CONTEXT@", "\n".join(ctx_lines))
            .replace("@TOPN@", str(top_n))
            .replace("@LESSONS@", "\n".join(lesson_lines)))
    return PROMPT_SYSTEM, user


# ---------------------------------------------------------------------------
# freeze (铁律 4: 配置先冻结后观察) + params versioning
# ---------------------------------------------------------------------------

def build_frozen_config(*, ic_parquet: Path, provider_model: str | None,
                        training: tuple[str, str] = TRAINING_DEFAULT,
                        validation: tuple[str, str] = VALIDATION_DEFAULT,
                        online_start: str = ONLINE_START_DEFAULT,
                        recent_k: int = RECENT_K_DEFAULT,
                        top_n_lessons: int = TOP_N_LESSONS_DEFAULT) -> dict:
    if not ic_parquet.exists():
        raise ReplayError(EXIT_Y_SOURCE, f"y-source parquet missing: {ic_parquet}")
    try:
        rel = str(ic_parquet.resolve().relative_to(REPO_ROOT))
    except ValueError:
        rel = str(ic_parquet.resolve())  # outside the repo (test fixture) — record as-is
    return {
        "kind": "replay-blackbox-config-frozen",
        "exploratory": True,
        "label": EXPLORATORY_LABEL,
        "design_ref": DESIGN_REF,
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "windows": {
            "training": {"from": training[0], "to": training[1],
                         "months": len(month_range(*training))},
            "frozen_validation": {"from": validation[0], "to": validation[1],
                                  "months": len(month_range(*validation))},
            "online_start": online_start,
        },
        "cut": {"train_to": training[1], "val_from": validation[0],
                "note": "改动须在看到任何 y 之前（设计 §1）；改窗口/切点=重新 freeze"},
        "provider": {"name": "glm", "model_at_freeze": provider_model,
                     "temperature": 0.1, "json_mode": True,
                     "reply_contract": 'single-line JSON {"answer": bool, "p": float 0..1}; '
                                       "p = P(answer correct)",
                     "model_note": ("model id is settings-pinned (fail-closed); "
                                    "the run manifest records the model actually used")},
        "claim_form": {"claim_template": "{month} 月 realized rank-IC 为正",
                       "due": "t", "answered_at": "t-1", "v1_single_family": True},
        "p_mapping": {"rule": "p = p_raw if answer is True else 1 - p_raw",
                      "semantics": "after mapping, p = P(IC_t > 0) — the calibration target"},
        "y_source": {"kind": "ic_parquet", "path": rel, "column": "ic",
                     "sha256_at_freeze": sha256_file(ic_parquet),
                     "note": "confirmatory 冻结产物；更换 y 源=重新 freeze（record-once）"},
        "bounded_context": {
            "contract": "ONLY a self-produced rolling summary of the realized-IC series "
                        "strictly before t; NO open macro narrative, NO calendar-anchored "
                        "narrative (arXiv:2601.13770 look-ahead tightening)",
            "masking": "structural, not assumed: rows ≤ t-1 asserted (exit 7 on violation) "
                       "+ per-month context snapshot SHA256 archived (design §2 铁律 3); "
                       "GLM is standard-LLM-class whose parametric look-ahead cannot be "
                       "assumed away — mitigation = the claim targets an internal, "
                       "non-public IC series + bounded self-produced context",
            "recent_k": recent_k,
            "fields": ["rows_used", "mean_ic", "std_ic", "hit_rate_ic_pos", "last_k"],
        },
        "injection_budget": {"top_n_lessons": top_n_lessons,
                             "source": "--lessons JSON list (v1: externally driven; "
                                       "cross-chunk accumulation outside the engine)"},
        "prompt_template": {"system": PROMPT_SYSTEM, "user": PROMPT_USER_TEMPLATE},
        "bucket_cuts": list(mr._CALIBRATION_BAND_CUTS),
        "aggregation": {"engine": "scripts/monthly_review.py "
                                  "calibration_bucket_summary/_bss_components "
                                  "(single implementation, verbatim reuse)"},
        "tuning_log": {"template": "tuning-log.md",
                       "knobs": ["prompt_template", "bucket_cuts", "top_n_lessons",
                                 "bounded_context", "thresholds"],
                       "implicit_trial_counter": "arXiv:2608.27734 — cumulative change "
                                                 "counts per knob class, incl. implicit trials"},
        "engine_discipline": {
            "zero_ledger_writes": True,
            "utf8_reconfigure": True,
            "exit_codes": {str(k): v for k, v in EXIT_CODE_NAMES.items()},
            "llm_note": "engine arithmetic deterministic; LLM replies NOT bit-reproducible "
                        "— archive-only, no recompute (design §2 铁律 3 诚实注记)",
        },
    }


def freeze(out_dir: Path, config: dict) -> tuple[Path, str]:
    """Write config-frozen.json (+SHA256 sidecar) + tuning-log.md template.
    Refuses overwrite (record-once: a changed config is a NEW config file)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = out_dir / "config-frozen.json"
    if cfg_path.exists():
        raise ReplayError(
            EXIT_FREEZE_OVERWRITE,
            f"{cfg_path} already exists — a changed config is a NEW freeze "
            "(record-once); point --out/--config at a fresh directory")
    cfg_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    sha = sha256_file(cfg_path)
    (out_dir / "config-frozen.sha256").write_text(f"{sha}  config-frozen.json\n",
                                                  encoding="utf-8")
    tuning = out_dir / "tuning-log.md"
    if not tuning.exists():
        tuning.write_text(TUNING_LOG_TEMPLATE, encoding="utf-8")
    return cfg_path, sha


def version_params(params: dict, out_dir: Path) -> tuple[str, Path]:
    """--params 版本化: content-addressed params/<sha8>.json (idempotent)."""
    payload = {"kind": "replay-params-versioned", "label": EXPLORATORY_LABEL,
               "params": params}
    sha = sha256_hex(payload)
    pdir = out_dir / "params"
    pdir.mkdir(parents=True, exist_ok=True)
    path = pdir / f"{sha[:8]}.json"
    if not path.exists():
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    return sha, path


# ---------------------------------------------------------------------------
# tier runners
# ---------------------------------------------------------------------------

def _write_jsonl_header(path: Path, tier: str, config_sha: str) -> None:
    path.write_text(json.dumps({
        "_header": {"kind": "replay-month-records", "exploratory": True,
                    "label": EXPLORATORY_LABEL, "tier": tier,
                    "config_sha256": config_sha},
    }, ensure_ascii=False) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, rec: dict) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def run_t0(config: dict, series: dict[str, float], from_ym: str, to_ym: str,
           run_dir: Path) -> dict:
    """T0 climatology, full window, ZERO LLM (design §6)."""
    records = climatology_records(series, from_ym, to_ym, tier="t0")
    bss_check = assert_t0_bss_zero(records)
    run_dir.mkdir(parents=True, exist_ok=True)
    jsonl = run_dir / "month-records.jsonl"
    _write_jsonl_header(jsonl, "t0", "")
    for rec in records:
        _append_jsonl(jsonl, rec)
    lines = [
        f"<!-- {EXPLORATORY_LABEL} -->",
        f"# T0 climatology run — window [{from_ym}..{to_ym}] ({len(records)} months)",
        f"- p̄ = {bss_check['p_bar']:.6f} (constant over the window; full-window "
        "hit-rate climatology)",
        "",
        *chunk_summary_lines(records),
        "",
        f"- BSS≡0 构造性断言: bss={bss_check['bss']:.12f} → PASS（非零=引擎 bug，exit 5）",
    ]
    (run_dir / "t0-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "kind": "replay-run-manifest", "exploratory": True, "label": EXPLORATORY_LABEL,
        "tier": "t0", "window": {"from": from_ym, "to": to_ym, "months": len(records)},
        "n_records": len(records), "p_bar": bss_check["p_bar"],
        "bss_check": {k: (v if v is not None else None)
                      for k, v in bss_check.items()},
        "honest_notes": ["BSS≡0 is constructive (model p ≡ p̄), NOT skill",
                         "zero runs/ledger.jsonl writes", "zero LLM calls"],
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"records": records, "run_dir": run_dir, "manifest": manifest,
            "bss_check": bss_check}


def run_t1(config: dict, series: dict[str, float], from_ym: str, to_ym: str,
           run_dir: Path, *, ask: Callable[[str, str], str],
           lessons: list[str] | None = None,
           params_meta: dict | None = None) -> dict:
    """T1 year-boundary chunked monthly loop (design §6), injected ask() (the
    real GLM wrapper lives in _make_ask; tests inject fakes — zero network)."""
    lessons = list(lessons or [])
    months_all = month_range(from_ym, to_ym)
    missing = [m for m in months_all if m not in series]
    if missing:
        raise ReplayError(EXIT_Y_SOURCE,
                          f"T1 window [{from_ym}..{to_ym}] missing y for "
                          f"{len(missing)} month(s), first={missing[0]}")
    run_dir.mkdir(parents=True, exist_ok=True)
    jsonl = run_dir / "month-records.jsonl"
    _write_jsonl_header(jsonl, "t1", "")
    summaries: list[str] = [
        f"<!-- {EXPLORATORY_LABEL} -->",
        f"# T1 chunked replay — window [{from_ym}..{to_ym}] "
        f"({len(chunk_years(from_ym, to_ym))} year-chunks, {len(months_all)} months)",
        "",
    ]
    all_records: list[dict] = []
    for cf, ct in chunk_years(from_ym, to_ym):
        chunk_records: list[dict] = []
        for month in month_range(cf, ct):
            context = truncated_context(series, month,
                                        int(config["bounded_context"]["recent_k"]))
            assert_masking(context["months"], month)
            snap = snapshot_sha256(context)
            system, user = build_prompt(config, month, context, lessons)
            raw = ask(system, user)
            reply = parse_blackbox_reply(raw)
            if not reply.get("ok"):
                (run_dir / f"contract-fail-{month}.txt").write_text(
                    raw or "", encoding="utf-8")
                raise ReplayError(
                    EXIT_LLM_CONTRACT,
                    f"reply contract failure for {month}: reason={reply.get('reason')} "
                    f"raw[:120]={reply.get('raw', '')!r}")
            p = map_p(reply["answer"], reply["p"])
            y = y_from_ic(series[month])
            rec = {
                "month": month, "tier": "t1", "chunk": cf[:4],
                "claim": config["claim_form"]["claim_template"].format(month=month),
                "answer": reply["answer"], "p_raw": reply["p"], "p": p, "y": y,
                "err": (p - y) ** 2,
                "rows_used": context["rows_used"],
                "masking_ok": True,
                "snapshot_sha256": snap,
                "prompt_sha256": sha256_hex({"system": system, "user": user}),
                "prompt": user,
                "reply_raw": raw,
                "label": EXPLORATORY_LABEL,
            }
            _append_jsonl(jsonl, rec)
            chunk_records.append(rec)
        summaries.append(f"## chunk {cf[:4]} [{cf}..{ct}] — {len(chunk_records)} months")
        summaries.extend(chunk_summary_lines(chunk_records))
        summaries.append("")
        all_records.extend(chunk_records)
    # full-window section (same engine, whole run)
    summaries.append(f"## full window [{from_ym}..{to_ym}] — {len(all_records)} months")
    summaries.extend(chunk_summary_lines(all_records))
    (run_dir / "chunk-summaries.md").write_text("\n".join(summaries) + "\n",
                                                encoding="utf-8")
    manifest = {
        "kind": "replay-run-manifest", "exploratory": True, "label": EXPLORATORY_LABEL,
        "tier": "t1", "window": {"from": from_ym, "to": to_ym, "months": len(all_records)},
        "chunks": [list(c) for c in chunk_years(from_ym, to_ym)],
        "n_records": len(all_records),
        "params": params_meta or {},
        "lessons_provided": len(lessons),
        "lessons_injected_top_n": int(config["injection_budget"]["top_n_lessons"]),
        "honest_notes": [
            "engine arithmetic deterministic; LLM replies NOT bit-reproducible "
            "(archive-only, no recompute — design §2 铁律 3)",
            "masking structural: rows ≤ t-1 asserted per month + snapshot SHA256 archived",
            "zero runs/ledger.jsonl writes",
        ],
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"records": all_records, "run_dir": run_dir, "manifest": manifest}


# ---------------------------------------------------------------------------
# real GLM ask wrapper (lazy imports — module stays importable without settings)
# ---------------------------------------------------------------------------

def resolve_effective_provider(frozen_name: str,
                               cli_provider: str | None) -> tuple[str, dict | None]:
    """--provider resolution (T2 contrast arm): the frozen config's provider is
    the default; an explicit --provider that DIFFERS from the frozen name is a
    run-time override — the frozen config bytes are never touched, and the
    override is recorded in the manifest for honest side-by-side reading."""
    if cli_provider is None or cli_provider == frozen_name:
        return frozen_name, None
    return cli_provider, {
        "kind": "provider-contrast-override",
        "from_frozen": frozen_name,
        "to": cli_provider,
        "note": ("T2 provider-contrast arm: run-time override of the frozen "
                 "provider for the execution only; config-frozen bytes "
                 "untouched (same config_sha256 as the GLM arm); contrast "
                 "arm carries ZERO lessons (lessons identity is GLM-bound); "
                 "EXPLORATORY REPLAY — not a claim, not a gate"),
    }


def _make_ask(config: dict,
              provider_name: str | None = None) -> tuple[Callable[[str, str], str], dict, str]:
    """LLM ask via the OpenAI-compatible client, JSON mode temp 0.1 (the client
    pins both), bounded single retry + token accounting — llm_memory_probe 先例.
    ``provider_name`` overrides the frozen config's provider (T2 contrast)."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from aionis.extraction.llm_client import OpenAICompatClient
    from aionis.extraction.providers import build_providers

    name = provider_name or config["provider"]["name"]
    provs = [p for p in build_providers(only_enabled=True)
             if p.name == name and p.api_key]
    if not provs:
        raise ReplayError(EXIT_LLM_CONTRACT,
                          f"provider {name!r} unavailable (no api key / disabled)")
    prov = provs[0]
    client = OpenAICompatClient(prov, timeout=240.0)
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "n_calls": 0}

    def ask(system: str, user: str) -> str:
        raw, err = "", None
        for _attempt in (1, 2):  # bounded single retry (token discipline)
            try:
                raw = client._chat(system, user)  # noqa: SLF001 — deliberately thin
                err = None
                break
            except Exception as exc:  # noqa: BLE001 — log & bounded retry
                err = str(exc)[:120]
                time.sleep(CALL_SPACING_S)
        if err is not None:
            raise ReplayError(EXIT_LLM_CONTRACT,
                              f"provider call failed twice: {err}")
        u = getattr(client, "last_usage", {})
        usage["prompt_tokens"] += int(u.get("prompt_tokens", 0) or 0)
        usage["completion_tokens"] += int(u.get("completion_tokens", 0) or 0)
        usage["n_calls"] += 1
        time.sleep(CALL_SPACING_S)
        return raw

    return ask, usage, prov.model


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_config(path: Path) -> dict:
    if not path.exists():
        raise ReplayError(EXIT_CONFIG, f"config-frozen.json missing: {path} "
                                       "(run --freeze first)")
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ReplayError(EXIT_CONFIG, f"config-frozen.json corrupt: {exc}") from exc
    if cfg.get("kind") != "replay-blackbox-config-frozen":
        raise ReplayError(EXIT_CONFIG, f"not a replay config: kind={cfg.get('kind')!r}")
    if not cfg.get("exploratory"):
        raise ReplayError(EXIT_CONFIG, "config lacks exploratory=true — refusing to run")
    return cfg


def _cmd_freeze(args: argparse.Namespace, out_dir: Path) -> int:
    provider_model = None
    try:  # best-effort: record the settings-pinned model id at freeze time
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from aionis.extraction.providers import build_providers
        for p in build_providers(only_enabled=True):
            if p.name == "glm" and p.api_key:
                provider_model = p.model
                break
    except Exception:  # noqa: BLE001 — freeze must work without settings/env
        provider_model = None
    cfg = build_frozen_config(ic_parquet=Path(args.ic_parquet),
                              provider_model=provider_model)
    cfg_path, sha = freeze(out_dir, cfg)
    print(f"[replay] frozen config : {cfg_path}")
    print(f"[replay] SHA256        : {sha}   (sidecar config-frozen.sha256; "
          "record this in the report)")
    print(f"[replay] tuning-log    : {out_dir / 'tuning-log.md'} "
          "(implicit-trial counters seeded at 0)")
    print(f"[replay] {EXPLORATORY_LABEL}")
    return EXIT_OK


def _cmd_run(args: argparse.Namespace, out_dir: Path) -> int:
    config_path = Path(args.config) if args.config else out_dir / "config-frozen.json"
    cfg = _load_config(config_path)
    config_sha = sha256_file(config_path)
    y_src = cfg["y_source"]
    series = load_ic_series(REPO_ROOT / y_src["path"])
    from_ym = args.from_ym or cfg["windows"]["training"]["from"]
    to_ym = args.to_ym or cfg["windows"]["training"]["to"]
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = out_dir / "runs" / f"{run_ts}-{args.tier}"
    if args.tier == "t0":
        result = run_t0(cfg, series, from_ym, to_ym, run_dir)
        p_bar = result["bss_check"]["p_bar"]
        print(f"[replay] T0 climatology [{from_ym}..{to_ym}]: {len(result['records'])} "
              f"months, p̄={p_bar:.4f}, BSS≡0 PASS → {run_dir}")
    else:
        params_meta: dict = {}
        if args.params:
            try:
                params = json.loads(Path(args.params).read_text(encoding="utf-8"))
            except ValueError as exc:
                raise ReplayError(EXIT_USAGE, f"--params not valid JSON: {exc}") from exc
            if not isinstance(params, dict):
                raise ReplayError(EXIT_USAGE, "--params must be a JSON object")
            sha, ppath = version_params(params, out_dir)
            params_meta = {"sha256": sha, "path": str(ppath), "params": params}
        lessons: list[str] = []
        if args.lessons:
            try:
                lessons = json.loads(Path(args.lessons).read_text(encoding="utf-8"))
            except ValueError as exc:
                raise ReplayError(EXIT_USAGE, f"--lessons not valid JSON: {exc}") from exc
            if not isinstance(lessons, list) or not all(isinstance(s, str) for s in lessons):
                raise ReplayError(EXIT_USAGE, "--lessons must be a JSON array of strings")
        effective_provider, provider_override = resolve_effective_provider(
            cfg["provider"]["name"], args.provider)
        if provider_override and lessons:
            raise ReplayError(
                EXIT_USAGE,
                "--lessons refused on a --provider contrast arm: ZERO lessons "
                "(lessons identity is GLM-bound; T2 contrast arm red line)")
        ask, usage, model = _make_ask(cfg, provider_name=effective_provider)
        result = run_t1(cfg, series, from_ym, to_ym, run_dir, ask=ask,
                        lessons=lessons, params_meta=params_meta)
        manifest = result["manifest"]
        manifest["config_sha256"] = config_sha
        manifest["provider_used"] = {"name": effective_provider, "model": model}
        if provider_override:
            manifest["provider_override"] = provider_override
        manifest["token_usage"] = usage
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[replay] T1 replay [{from_ym}..{to_ym}]: {len(result['records'])} months, "
              f"{usage['n_calls']} LLM calls, tokens p/c={usage['prompt_tokens']}/"
              f"{usage['completion_tokens']} → {run_dir}")
        if provider_override:
            print(f"[replay] provider-contrast override: {provider_override['from_frozen']} "
                  f"→ {effective_provider} (frozen config bytes untouched; zero lessons)")
    print(f"[replay] {EXPLORATORY_LABEL}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # ⑦ UTF-8 reconfigure (GBK console)
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true",
                       help="write config-frozen.json + SHA256 sidecar + tuning-log "
                            "template (record-once, refuses overwrite)")
    group.add_argument("--tier", choices=["t0", "t1"],
                       help="t0 climatology (zero LLM) | t1 year-chunked LLM replay")
    parser.add_argument("--from", dest="from_ym", default=None,
                        help="window start YYYY-MM (default: config training window)")
    parser.add_argument("--to", dest="to_ym", default=None,
                        help="window end YYYY-MM (default: config training window)")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="replay artifact root (default reports/exploratory/replay)")
    parser.add_argument("--config", default=None,
                        help="config-frozen.json path (default <out>/config-frozen.json)")
    parser.add_argument("--params", default=None,
                        help="T1: versioned params JSON (--from/--to/--params 注入)")
    parser.add_argument("--lessons", default=None,
                        help="T1: JSON array of lesson strings (injected top-N)")
    parser.add_argument("--provider", choices=list(PROVIDER_CHOICES), default=None,
                        help="provider override for the execution (default: the "
                             "frozen config's provider, glm — unchanged; a differing "
                             "--provider marks a T2 provider-contrast arm: same frozen "
                             "config bytes, ZERO lessons, EXPLORATORY REPLAY only)")
    parser.add_argument("--ic-parquet", dest="ic_parquet", default=Y_SOURCE_DEFAULT,
                        help="FREEZE-TIME y source selection (frozen thereafter; "
                             "default = Phase D confirmatory treatment IC)")
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    try:
        if args.freeze:
            return _cmd_freeze(args, out_dir)
        return _cmd_run(args, out_dir)
    except ReplayError as exc:
        print(f"[replay] EXIT {exc.exit_code} ({EXIT_CODE_NAMES.get(exc.exit_code, '?')}): "
              f"{exc.message}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
