"""T1 月级推进器（EXPLORATORY REPLAY，t1-advance-formalize，2026-11-17）。

主会话后台循环（exec_68ca17cc）同参正式化：读 `t1-monthly-plan.txt` 进度 →
逐月独立调用 replay_blackbox（`--from m --to m`，冻结 config-frozen.json 原字节，
provider=glm 冻结钉定，零 lessons——年界检查点调参是后续批次的活，本工具只积累
月记录不越权）→ 月记录计数 → 退出码语义化。

协议（t1-breakpoint.md「协议演进注记」裁决，铁律不变）：
- 月级断点累积：成功调用落 `runs/t1-monthly-advance/<ts>-t1/`，每次成功调用 =
  独立完整记录；零拼接零复用——已齐月记录的月份跳过，不重答（断点语义非
  重跑到通过）。
- 幂等：计划全齐后再跑 = 只读 no-op 退出 0（晚间通道 marker-guard 同款语义）；
  无锁、无常驻进程——一次调用一个短命进程，schtasks 重复触发只是廉价 no-op。

退出码：0 计划完成（含 no-op 再入）· 1 部分推进（本次新增 ≥1 月记录且未遇引擎
失败，仍有待办）· 2 窗口耗尽（引擎调用失败中止——GLM 限速/超时即窗口信号；
本次零推进或推进后遇失败均归此码，stdout 注明本次推进数）· 3 计划/配置参数错
· 4 计划与冻结 config 训练窗不一致。

--status：只读模式（数 advance 目录月记录 vs 计划），永不调用引擎。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_ROOT = REPO_ROOT / "reports" / "exploratory" / "replay"
ENGINE = REPO_ROOT / "scripts" / "replay_blackbox.py"
PLAN_DEFAULT = REPLAY_ROOT / "t1-monthly-plan.txt"
CONFIG_DEFAULT = REPLAY_ROOT / "config-frozen.json"
ADVANCE_ROOT_DEFAULT = REPLAY_ROOT / "runs" / "t1-monthly-advance"

EXIT_OK = 0            # 计划完成（或已完成后 no-op 再入）
EXIT_PARTIAL = 1       # 部分推进（新增≥1 月记录，无引擎失败，仍有待办）
EXIT_WINDOW = 2        # 窗口耗尽（引擎失败中止）
EXIT_USAGE = 3         # 计划/配置参数错
EXIT_PLAN_MISMATCH = 4 # 计划与冻结 config 训练窗不一致

EXIT_CODE_NAMES = {
    EXIT_OK: "complete (or idempotent no-op)",
    EXIT_PARTIAL: "partial advance (progress, no failure, months pending)",
    EXIT_WINDOW: "window exhausted (engine invocation failed)",
    EXIT_USAGE: "plan/config args invalid",
    EXIT_PLAN_MISMATCH: "plan disagrees with frozen config training window",
}

EXPLORATORY_LABEL = (
    "EXPLORATORY REPLAY — not a claim, not a gate "
    "(zero runs/ledger.jsonl writes; research face untouched)"
)

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class AdvanceError(Exception):
    def __init__(self, exit_code: int, message: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.message = message


# ---------------------------------------------------------------------------
# pure: plan generation / parsing
# ---------------------------------------------------------------------------

def plan_months(from_ym: str, to_ym: str) -> list[str]:
    """Inclusive monthly list YYYY-MM (T1 训练窗计划生成；自算，勿与引擎耦合）."""
    for what, ym in (("--from", from_ym), ("--to", to_ym)):
        if not isinstance(ym, str) or not MONTH_RE.match(ym):
            raise AdvanceError(EXIT_USAGE, f"{what} must be YYYY-MM, got {ym!r}")
    if from_ym > to_ym:
        raise AdvanceError(EXIT_USAGE, f"window reversed: {from_ym} > {to_ym}")
    out: list[str] = []
    y, m = int(from_ym[:4]), int(from_ym[5:7])
    while f"{y:04d}-{m:02d}" <= to_ym:
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def parse_plan(text: str) -> list[str]:
    """计划文件 → 有序月列表。空行/尾空白容忍；非月行/重复/乱序 → EXIT_USAGE
    （计划是被 freeze 语义引用的输入，静默修复=篡改）。"""
    months = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not months:
        raise AdvanceError(EXIT_USAGE, "plan file is empty")
    for m in months:
        if not MONTH_RE.match(m):
            raise AdvanceError(EXIT_USAGE, f"plan line not YYYY-MM: {m!r}")
    if len(set(months)) != len(months):
        raise AdvanceError(EXIT_USAGE, "plan has duplicate months")
    if months != sorted(months):
        raise AdvanceError(EXIT_USAGE, "plan is not sorted ascending")
    return months


def check_plan_against_config(plan: list[str], config_path: Path) -> None:
    """计划必须逐月等于冻结 config 训练窗（防拿错计划/改窗后的错位续跑）。"""
    if not config_path.exists():
        raise AdvanceError(EXIT_USAGE, f"config-frozen missing: {config_path}")
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    if cfg.get("kind") != "replay-blackbox-config-frozen" or not cfg.get("exploratory"):
        raise AdvanceError(EXIT_USAGE, f"not an exploratory replay config: {config_path}")
    tr = cfg["windows"]["training"]
    expected = plan_months(tr["from"], tr["to"])
    if plan != expected:
        raise AdvanceError(
            EXIT_PLAN_MISMATCH,
            f"plan {plan[0]}..{plan[-1]} ({len(plan)}m) != frozen training window "
            f"{tr['from']}..{tr['to']} ({len(expected)}m) — regenerate the plan or "
            "point --config at the freeze the plan belongs to")


# ---------------------------------------------------------------------------
# pure: progress parsing (advance 目录月记录 vs 计划)
# ---------------------------------------------------------------------------

def _advance_run_dirs(advance_root: Path) -> list[Path]:
    """advance 根下全部 ``*-t1`` run 目录——引擎真实布局是
    ``<advance_root>/runs/<ts>-t1/``（replay_blackbox ``_cmd_run`` 拼 ``runs/``），
    兼容旧式根层直放 ``<advance_root>/<ts>-t1/``。"""
    candidates: list[Path] = []
    for parent in (advance_root / "runs", advance_root):
        if parent.is_dir():
            candidates.extend(
                p for p in parent.iterdir() if p.is_dir() and p.name.endswith("-t1")
            )
    return sorted(candidates)


def scan_progress(advance_root: Path) -> dict[str, list[str]]:
    """advance 根 → {month: [run_dir_name, …]}（每目录内非 header 月记录 ≥1 才计）。

    只读；header-only 断点目录（诚实证据）不产生完成计数。同月多目录=重复成功，
    如实列出不去重（计数面取 presence，展示面保留全部）。
    """
    done: dict[str, list[str]] = {}
    if not advance_root.exists():
        return done
    for run_dir in _advance_run_dirs(advance_root):
        recs_path = run_dir / "month-records.jsonl"
        if not recs_path.exists():
            continue
        for line in recs_path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            month = rec.get("month") if isinstance(rec, dict) else None
            if month and "_header" not in rec:
                done.setdefault(month, []).append(run_dir.name)
    return done


def next_pending(plan: list[str], progress: dict[str, list[str]]) -> list[str]:
    """断点判定：计划中尚无月记录的月份，保持计划顺序（首缺月=续跑点）。"""
    return [m for m in plan if m not in progress]


def is_complete(plan: list[str], progress: dict[str, list[str]]) -> bool:
    return not next_pending(plan, progress)


# ---------------------------------------------------------------------------
# advance core (engine invoker injected — tests pass fakes, zero network)
# ---------------------------------------------------------------------------

def run_advance(months_todo: list[str], invoke, *,
                stop_after: int | None = None) -> dict:
    """逐月推进核心。``invoke(month)`` 跑一次 replay_blackbox 单月调用，返回
    (exit_code:int)。引擎失败=窗口耗尽信号：立即停（不重试到通过——铁律）。
    返回 {exit_code, advanced:[…], failed:month|None, engine_exit:int|None}。"""
    advanced: list[str] = []
    for month in months_todo:
        if stop_after is not None and len(advanced) >= stop_after:
            return {"exit_code": EXIT_PARTIAL if advanced else EXIT_WINDOW,
                    "advanced": advanced, "failed": None, "engine_exit": None,
                    "stop_reason": "stop-after budget"}
        code = invoke(month)
        if code != 0:
            return {"exit_code": EXIT_WINDOW, "advanced": advanced,
                    "failed": month, "engine_exit": code,
                    "stop_reason": "engine invocation failed"}
        advanced.append(month)
    return {"exit_code": EXIT_OK, "advanced": advanced, "failed": None,
            "engine_exit": None, "stop_reason": "plan complete"}


def _invoke_engine(month: str, *, config: Path, advance_root: Path) -> int:
    """一次单月引擎调用（短命子进程；--from m --to m，冻结 config 原字节）。
    argv-list 形态、无 shell；月份在 sink 处再过一次 MONTH_RE（计划解析已保证，
    此处防御性复验使不变式就地可见）。"""
    if not MONTH_RE.match(month):
        raise AdvanceError(EXIT_USAGE,
                           f"refusing to invoke engine for non-month {month!r}")
    advance_root.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [sys.executable, str(ENGINE), "--tier", "t1",
         "--config", str(config), "--out", str(advance_root),
         "--from", month, "--to", month],
        check=False,
    )
    return proc.returncode


# ---------------------------------------------------------------------------
# status (read-only) + CLI
# ---------------------------------------------------------------------------

def status_lines(plan: list[str], progress: dict[str, list[str]]) -> list[str]:
    pending = next_pending(plan, progress)
    done_n = len(plan) - len(pending)
    lines = [
        f"<!-- {EXPLORATORY_LABEL} -->",
        f"# T1 advance status — {done_n}/{len(plan)} months have records",
        f"- plan window: {plan[0]}..{plan[-1]} | pending: {len(pending)}",
    ]
    if pending:
        lines.append(f"- next month (breakpoint): {pending[0]}")
    else:
        lines.append("- plan COMPLETE (further invocations are read-only no-ops)")
    dups = {m: d for m, d in progress.items() if len(d) > 1}
    if dups:
        dups_txt = ", ".join(f"{m}:{len(d)}" for m, d in sorted(dups.items()))
        lines.append(f"- duplicate-success months (listed, not deduped): {dups_txt}")
    outside = sorted(set(progress) - set(plan))
    if outside:
        lines.append(f"- records OUTSIDE the plan (not counted): {outside}")
    by_year: dict[str, list[int]] = {}
    for m in plan:
        by_year.setdefault(m[:4], []).append(0 if m in pending else 1)
    lines.append("")
    lines.append("| 年块 | 月记录/计划 |")
    lines.append("|---|---|")
    for y in sorted(by_year):
        rows = by_year[y]
        lines.append(f"| {y} | {sum(rows)}/{len(rows)} |")
    return lines


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="T1 月级推进器（EXPLORATORY REPLAY；"
                                "读计划→逐月单月调用→计数→语义化退出码）")
    p.add_argument("--status", action="store_true",
                   help="read-only: count advance month-records vs plan (no engine)")
    p.add_argument("--plan", default=str(PLAN_DEFAULT))
    p.add_argument("--config", default=str(CONFIG_DEFAULT))
    p.add_argument("--advance-root", default=str(ADVANCE_ROOT_DEFAULT))
    p.add_argument("--stop-after", type=int, default=None,
                   help="advance at most N new months this invocation (politeness "
                        "valve; default unlimited)")
    p.add_argument("--spacing-s", type=float, default=8.0,
                   help="sleep between monthly engine invocations (default 8s)")
    args = p.parse_args(argv)
    plan_path = Path(args.plan)
    try:
        if not plan_path.exists():
            raise AdvanceError(EXIT_USAGE, f"plan file missing: {plan_path}")
        plan = parse_plan(plan_path.read_text(encoding="utf-8"))
        check_plan_against_config(plan, Path(args.config))
        advance_root = Path(args.advance_root)
        if args.status:
            progress = scan_progress(advance_root)
            print("\n".join(status_lines(plan, progress)))
            print(f"[t1-advance] {EXPLORATORY_LABEL}")
            return EXIT_OK
        progress = scan_progress(advance_root)
        todo = next_pending(plan, progress)
        if not todo:
            print(f"[t1-advance] plan already complete ({len(plan)} months) — "
                  "read-only no-op, exit 0")
            return EXIT_OK

        def invoke(month: str) -> int:
            code = _invoke_engine(month, config=Path(args.config),
                                  advance_root=advance_root)
            time.sleep(args.spacing_s)
            return code

        result = run_advance(todo, invoke, stop_after=args.stop_after)
        n_new = len(result["advanced"])
        if result["advanced"]:
            print(f"[t1-advance] advanced {n_new} month(s): "
                  f"{result['advanced'][0]}..{result['advanced'][-1]}")
        if result["exit_code"] == EXIT_OK:
            print(f"[t1-advance] PLAN COMPLETE: {len(plan)}/{len(plan)} months")
        elif result["exit_code"] == EXIT_WINDOW and result["failed"] is not None:
            print(f"[t1-advance] WINDOW EXHAUSTED at {result['failed']} "
                  f"(engine exit {result['engine_exit']}); advanced this "
                  f"invocation: {n_new} — honest breakpoint, no retry-to-pass")
        elif result["exit_code"] == EXIT_PARTIAL:
            print("[t1-advance] partial: stop-after budget reached with pending "
                 "months remaining")
        print(f"[t1-advance] {EXPLORATORY_LABEL}")
        return result["exit_code"]
    except AdvanceError as exc:
        print(f"[t1-advance] EXIT {exc.exit_code} "
              f"({EXIT_CODE_NAMES.get(exc.exit_code, '?')}): {exc.message}",
              file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
