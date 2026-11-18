"""epoch-1 校准聚合器（EXPLORATORY REPLAY，calibration-aggregate，2026-11-18）。

只读聚合 T1 月级断点记录（runs/t1-monthly-advance/runs/*-t1/month-records.jsonl，
非 header 月记录），输出 Murphy 三分量分解校准报告到
reports/exploratory/replay/epoch1-calibration.md。零账本零冻结面零研究管线写入；
调参可判定口径（铁律 1）：只许动 reliability/resolution，uncertainty 是数据不变量。

Murphy 分解（binary y；**预报值桶**上精确恒等）：
    BS  = mean (p-y)^2
    REL = Σ_b (n_b/N)(p̄_b − ȳ_b)²        reliability：分桶条件偏差（越大越差）
    RES = Σ_b (n_b/N)(ȳ_b − π̄)²          resolution：桶间 ȳ 对基率的离散（越大越好）
    UNC = π̄(1−π̄)                          uncertainty：基率方差（数据不变量）
    恒等式：BS = REL − RES + UNC（本脚本逐次运行断言 <1e-12）。
    恒等式精确成立的充要形态：**每个不同预报值自成一桶**（桶内 p 恒定 ⇒ 桶内
    散布 ε≡0；会话实测教训：把 5 个等数分位桶直接当分解桶，桶内 p 散布+协方差
    项使恒等式残差 ~6e-4 甚至为负——故分解口径=值桶，分位五桶仅作展示口径）。
    注意 mission 简写「Brier=三者之和」：resolution 是**负向**进入和式——
    三分量构成 BS，但好的预报器要 REL→0、RES→大。

桶切分双口径：
- 分解口径（REL/RES/UNC/恒等式）：**值桶**（每个 distinct p 一桶，本集 23 桶）——
  数学精确，逐月 resolution 位移（LOO）也在值桶口径上算。
- 展示口径（五桶表/ECE）：按 p 升序**保并列**分位切分（切边只落不同 p 值间，
  桶容量近似等数）——展示 ONLY（沿 monthly_review.calibration_bucket_summary
  「presentation buckets ONLY，无 p 调整、无阈值建议」纪律）；该口径下
  BS ≠ REL−RES+UNC 精确成立（桶内散布残差如实注记），不用于分解判读。
isotonic **不拟合**：sklearn 文档明示 ~1000 样本以下
isotonic 不可靠（本集 54..120 月远低于阈值；同
src/aionis/eval/score_calibration.py 的 null-模型过拟合哲学）——「isotonic」仅作
分位桶切分展示口径的名称出现，本聚合不含任何 isotonic 拟合。

逐月 resolution 位移（LOO）：ΔRES_i = RES_全 − RES_去 i（其余月保持原桶归属，
仅把月 i 移出后按 N−1 重算）——正=该月对 resolution 是正贡献，负=去掉它
resolution 反而升（判读逐月拖累面）。

分年 BSS 基准：vs **T0 冻结基率 p̄₀ = 62/120 = 0.5167**（T0 构造断言工件
runs/20261116-175239-t0，训练窗 120 月 y=1 计 62）——BSS_year =
1 − BS_year / (p̄₀(1−p̄₀))；引擎原口径（in-sample p̄ 的 _bss_components，
monthly_review.py:1123 逐字公式）另列一行作连续性参考。

退出码：0 报告已写 · 3 无月记录（空态）/数据校验失败（不编造数字）。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ADVANCE_ROOT_DEFAULT = (REPO_ROOT / "reports" / "exploratory" / "replay" / "runs"
                        / "t1-monthly-advance")
OUT_DEFAULT = REPO_ROOT / "reports" / "exploratory" / "replay" / "epoch1-calibration.md"

T0_PBAR = 62 / 120  # T0 冻结基率（runs/20261116-175239-t0：y=1 计 62/120 = 0.5167）
BS_REF_T0 = T0_PBAR * (1 - T0_PBAR)
N_BINS = 5
WORST_N = 12

EXPLORATORY_LABEL = (
    "EXPLORATORY REPLAY — not a claim, not a gate "
    "(zero runs/ledger.jsonl writes; research face untouched)"
)


class AggregateError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


# ---------------------------------------------------------------------------
# data intake（只读；去重=首见优先，重复如实列出）
# ---------------------------------------------------------------------------

def load_month_records(advance_root: Path) -> tuple[list[dict], list[str]]:
    """advance 根 → [(month, p, y, answer, err, run_dir), …]（按月序）+ 重复月注记。

    目录布局兼容 scripts/t1_advance.py._advance_run_dirs 双层扫描（runs/ 优先 +
    根层直放）；同月多记录=重复成功，首见优先入样、全部列出不去除（诚实证据面）。
    """
    candidates: list[Path] = []
    for parent in (advance_root / "runs", advance_root):
        if parent.is_dir():
            candidates.extend(
                p for p in parent.iterdir() if p.is_dir() and p.name.endswith("-t1")
            )
    by_month: dict[str, dict] = {}
    dup_dirs: list[str] = []
    for run_dir in sorted(candidates):
        recs_path = run_dir / "month-records.jsonl"
        if not recs_path.exists():
            continue
        for line in recs_path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict) or "_header" in rec:
                continue
            month = rec.get("month")
            if not month:
                continue
            if month in by_month:
                dup_dirs.append(f"{month}:{run_dir.name}")
                continue
            by_month[month] = {**rec, "_run_dir": run_dir.name}
    if not by_month:
        raise AggregateError(
            f"no month records under {advance_root} — nothing to aggregate (exit 3)")
    records = [by_month[m] for m in sorted(by_month)]
    return records, dup_dirs


# ---------------------------------------------------------------------------
# Murphy decomposition（等数分位五桶；恒等式断言）
# ---------------------------------------------------------------------------

def _value_bins(p: list[float]) -> list[list[int]]:
    """**分解口径桶**：每个 distinct p 值自成一桶（元素=原下标，按值升序）。

    桶内 p 恒定 ⇒ Murphy 恒等式 BS = REL − RES + UNC 精确成立（桶内散布 ε≡0，
    会话实测：分位五桶直接当分解桶时残差 ~6e-4 且可为负——见模块 docstring）。
    """
    groups: dict[float, list[int]] = {}
    for i, v in enumerate(p):
        groups.setdefault(v, []).append(i)
    return [groups[v] for v in sorted(groups)]


def _quantile_bins(p: list[float]) -> list[list[int]]:
    """**展示口径桶**：N_BINS 个保并列分位桶（元素=原下标）。

    切边只落在**不同 p 值之间**（桶边界=距理想分位点最近的组边界）——并列 p 值
    永不被劈进相邻桶，桶容量近似等数、如实展示聚类（monthly_review 反聚类注记
    同源）。仅用于五桶表/ECE 展示；**不用于** Murphy 分解（桶内 p 不恒定，
    恒等式在该口径下不精确——见模块 docstring）。
    """
    n = len(p)
    order = sorted(range(n), key=lambda i: (p[i], i))
    groups: list[list[int]] = []
    for i in order:
        if groups and p[i] == p[groups[-1][0]]:
            groups[-1].append(i)
        else:
            groups.append([i])
    cum = [0]
    for g in groups:
        cum.append(cum[-1] + len(g))
    bins: list[list[int]] = []
    start_g = 0
    for b in range(1, N_BINS):
        ideal = n * b / N_BINS
        best_g = min(
            range(start_g, len(groups)),
            key=lambda g: (abs(cum[g + 1] - ideal), g),
        )
        end_g = best_g + 1
        bins.append([i for g in groups[start_g:end_g] for i in g])
        start_g = end_g
    bins.append([i for g in groups[start_g:] for i in g])
    return [b for b in bins if b]


def murphy_decompose(p: list[float], y: list[float],
                     bins: list[list[int]] | None = None) -> dict:
    """Murphy 三分量 + BS + 桶统计（**值桶口径**，恒等式 |BS−(REL−RES+UNC)|<1e-12
    断言）。bins 缺省=值桶；传入自定义桶仅在桶内 p 恒定时恒等式才精确（测试用）。"""
    n = len(p)
    if n == 0:
        raise AggregateError("empty sample")
    bs = sum((pi - yi) ** 2 for pi, yi in zip(p, y, strict=True)) / n
    pi_bar = sum(y) / n
    unc = pi_bar * (1 - pi_bar)
    if bins is None:
        bins = _value_bins(p)
    rel = 0.0
    res = 0.0
    bucket_rows: list[dict] = []
    for b, idxs in enumerate(bins, start=1):
        nb = len(idxs)
        p_bar_b = sum(p[i] for i in idxs) / nb
        y_bar_b = sum(y[i] for i in idxs) / nb
        rel += (nb / n) * (p_bar_b - y_bar_b) ** 2
        res += (nb / n) * (y_bar_b - pi_bar) ** 2
        bucket_rows.append({
            "bin": b, "idxs": idxs, "n": nb,
            "p_min": min(p[i] for i in idxs), "p_max": max(p[i] for i in idxs),
            "p_bar": p_bar_b, "y_bar": y_bar_b,
        })
    if abs(bs - (rel - res + unc)) > 1e-12:
        raise AggregateError(
            f"Murphy identity violated: bs={bs!r} rel={rel!r} res={res!r} unc={unc!r}")
    return {"n": n, "bs": bs, "rel": rel, "res": res, "unc": unc,
            "pi_bar": pi_bar, "bins": bins, "bucket_rows": bucket_rows}


def ece_display(p: list[float], y: list[float],
                bins: list[list[int]]) -> float:
    """ECE（展示口径桶）：Σ_b (n_b/N)|p̄_b − ȳ_b|。裸值不单独判读（调研注记）。"""
    n = len(p)
    total = 0.0
    for idxs in bins:
        nb = len(idxs)
        p_bar_b = sum(p[i] for i in idxs) / nb
        y_bar_b = sum(y[i] for i in idxs) / nb
        total += (nb / n) * abs(p_bar_b - y_bar_b)
    return total


def loo_resolution_delta(p: list[float], y: list[float],
                         bins: list[list[int]]) -> list[float]:
    """逐月 ΔRES_i = RES_全 − RES_去 i（其余月保持原桶，样本 N−1 重算）。"""
    full = murphy_decompose(p, y, bins)["res"]
    n = len(p)
    pi_bar = sum(y) / n
    out: list[float] = []
    for i in range(n):
        res_i = 0.0
        for idxs in bins:
            keep = [j for j in idxs if j != i]
            if not keep:
                continue  # 该月独桶被移空：桶消失，对 RES 无贡献
            nb = len(keep)
            y_bar_b = sum(y[j] for j in keep) / nb
            res_i += (nb / (n - 1)) * (y_bar_b - pi_bar) ** 2
        out.append(full - res_i)
    return out


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def build_report(records: list[dict], dup_dirs: list[str]) -> str:
    months = [r["month"] for r in records]
    p = [float(r["p"]) for r in records]
    y = [float(r["y"]) for r in records]
    for r, pv, yv in zip(records, p, y, strict=True):
        if not (0.0 <= pv <= 1.0):
            raise AggregateError(f"{r['month']}: p out of range: {pv!r}")
        if yv not in (0.0, 1.0):
            raise AggregateError(f"{r['month']}: y not binary: {yv!r}")
        if not r.get("masking_ok", False):
            raise AggregateError(f"{r['month']}: masking_ok false — refusing to aggregate")
    # 引擎逐月 err 字段交叉核验（err=(p−y)² 应逐值一致）
    for r in records:
        err_expected = (float(r["p"]) - float(r["y"])) ** 2
        if abs(float(r["err"]) - err_expected) > 1e-9:
            raise AggregateError(
                f"{r['month']}: engine err {r['err']!r} != (p-y)^2 {err_expected!r}")

    m = murphy_decompose(p, y)  # 值桶口径（恒等式精确）
    dbins = _quantile_bins(p)  # 展示口径（五桶保并列）
    ece = ece_display(p, y, dbins)
    # 展示口径残差（桶内 p 散布+桶内协方差项 W+X）——如实注记，不用于分解判读
    rel_d = 0.0
    res_d = 0.0
    for idxs in dbins:
        nb = len(idxs)
        pb = sum(p[i] for i in idxs) / nb
        yb = sum(y[i] for i in idxs) / nb
        rel_d += (nb / m["n"]) * (pb - yb) ** 2
        res_d += (nb / m["n"]) * (yb - m["pi_bar"]) ** 2
    resid_display = m["bs"] - (rel_d - res_d + m["unc"])
    dres = loo_resolution_delta(p, y, m["bins"])
    span = f"{months[0]}..{months[-1]}"

    lines: list[str] = []
    w = lines.append
    w(f"<!-- {EXPLORATORY_LABEL} -->")
    w("")
    w("# epoch-1 校准聚合（Murphy 三分量分解）— T1 月级断点记录")
    w("")
    w(f"- 样本：**{m['n']}/{120}** 月（{span}；断点态：2020-07 窗耗尽 de27fe0660，"
      "2021-2025 零月记录待续跑——本报告是断点快照，非终局）")
    w("- 数据：`runs/t1-monthly-advance/runs/*-t1/month-records.jsonl` 非 header 月记录"
      "（去重=首见优先；逐值 `err=(p−y)²` 与引擎记录交叉核验一致；`masking_ok` "
      f"{m['n']}/{m['n']} 真）")
    if dup_dirs:
        w(f"- 重复成功月（首见入样，全部列出）：{', '.join(dup_dirs)}")
    else:
        w("- 重复成功月：无")
    w("- 聚合器：`scripts/epoch1_calibration.py`（只读；零账本/零冻结面/零研究管线）")
    w("")
    w("## 口径（铁律 1 可判定面：只许动 REL/RES，UNC 是数据不变量）")
    w("")
    w("- Murphy 分解（binary y）：**BS = REL − RES + UNC**（mission 简写「三者之和」"
      "的精确形式——resolution **负向**进入：")
    w("  REL=Σ(n_b/N)(p̄_b−ȳ_b)² 分桶条件偏差，越大越差；"
      "RES=Σ(n_b/N)(ȳ_b−π̄)² 桶间 ȳ 对基率离散，越大越好；"
      "UNC=π̄(1−π̄) 基率方差，数据不变量）。")
    w(f"- **分解口径 = 值桶**（每个 distinct p 自成一桶，本集 {len(m['bins'])} 桶）——"
      "桶内 p 恒定是恒等式精确成立的条件（等数分位桶直接当分解桶时桶内散布+桶内"
      "协方差项使恒等式残差 ~1e-4 级且可为负，会话实测 +6e-4/−2.5e-3 两例）；"
      "恒等式断言 <1e-12 逐次运行。逐月 resolution 位移同在值桶口径。")
    w("- **展示口径 = 五桶**：按 p 升序保并列分位切分（切边只落不同 p 值之间，桶容量"
      "近似等数；**展示 ONLY**：无 p 调整、无阈值建议，沿 "
      "monthly_review.calibration_bucket_summary 纪律）。该口径下三分量和与 BS 差"
      f"桶内散布残差 {resid_display:+.2e}（如实注记，不作分解判读）。")
    w("- **isotonic 不拟合**：sklearn 文档明示 ~1000 样本以下 isotonic 不可靠"
      f"（本集 {m['n']} 月、全计划 120 月均远低于阈值；同 "
      "src/aionis/eval/score_calibration.py null-过拟合哲学）——「isotonic」仅作"
      "分位桶切分展示口径名称出现，本聚合零 isotonic 拟合。")
    w("- 分年 BSS 基准 = **T0 冻结基率 p̄₀=62/120=0.5167**（runs/20261116-175239-t0）："
      "BSS = 1 − BS/(p̄₀(1−p̄₀))，BS_ref=0.249722；引擎原口径"
      "（in-sample p̄，monthly_review.py:1123 `_bss_components` 逐字公式）另列参考行。")
    w("- 调研注记（口径为何三分量）：sklearn 文档警告 brier_score_loss 单标量混合三义；"
      "arXiv:2610.25846 实证 ECE 可「奖励贴基率而分辨力差」——故以三分量+分桶展示"
      "替代裸 ECE/Brier 判读（ECE 仍列，作五桶一阶面）。")
    w("")
    w("## 总量")
    w("")
    w("| 量 | 值 | 判读 |")
    w("|---|---|---|")
    w(f"| BS（Brier，全样） | {m['bs']:.6f} | 越小越好 |")
    w(f"| REL（reliability） | {m['rel']:.6f} | →0 好；调参可动 |")
    w(f"| RES（resolution） | {m['res']:.6f} | 越大越好；调参可动 |")
    w(f"| UNC（uncertainty） | {m['unc']:.6f} | 数据不变量（π̄={m['pi_bar']:.4f}） |")
    w(f"| 恒等式核验 |BS−(REL−RES+UNC)| | "
      f"{abs(m['bs'] - (m['rel'] - m['res'] + m['unc'])):.2e} | 值桶口径 <1e-12 ✓ |")
    w(f"| ECE（五桶展示口径一阶） | {ece:.6f} | 裸值不单独判读（调研注记） |")
    engine_bss = 1 - m["bs"] / m["unc"] if m["unc"] != 0 else None
    if engine_bss is not None:
        w(f"| BSS（引擎口径，in-sample p̄ 基准） | {engine_bss:.6f} | "
          "monthly_review.py:1123 同式 |")
    bss_t0 = 1 - m["bs"] / BS_REF_T0
    w(f"| BSS（vs T0 p̄₀=0.5167 冻结基准） | {bss_t0:.6f} | 分年表同基准 |")
    w("")
    w("## 五桶表（保并列分位，展示口径；分解判读用上表值桶三分量）")
    w("")
    w("| 桶 | p 范围 | n | p̄ | ȳ | |p̄−ȳ| | (p̄−ȳ)²·n/N 贡献 |")
    w("|---|---|---|---|---|---|---|")
    for b, idxs in enumerate(dbins, start=1):
        nb = len(idxs)
        pb = sum(p[i] for i in idxs) / nb
        yb = sum(y[i] for i in idxs) / nb
        contrib = (nb / m["n"]) * (pb - yb) ** 2
        w(f"| {b} | [{min(p[i] for i in idxs):.4f},{max(p[i] for i in idxs):.4f}] "
          f"| {nb} | {pb:.4f} | {yb:.4f} | {abs(pb - yb):.4f} | {contrib:.6f} |")
    w("")
    w("## 分年 BSS vs T0 p̄₀=0.5167（BS_ref=0.249722）")
    w("")
    w("| 年 | n | BS | BSS |")
    w("|---|---|---|---|")
    by_year: dict[str, list[int]] = {}
    for i, mo in enumerate(months):
        by_year.setdefault(mo[:4], []).append(i)
    for yr in sorted(by_year):
        idxs = by_year[yr]
        bs_y = sum((p[i] - y[i]) ** 2 for i in idxs) / len(idxs)
        w(f"| {yr} | {len(idxs)} | {bs_y:.6f} | {1 - bs_y / BS_REF_T0:+.6f} |")
    for yr in [str(v) for v in range(2016, 2026)]:
        if yr not in by_year:
            w(f"| {yr} | 0 | — | —（零月记录，断点待续） |")
    w("")
    w("## 逐月 resolution 位移（值桶口径 LOO：ΔRES_i = RES_全 − RES_去 i，正=正贡献）")
    w("")
    w("| 月 | p | y | \\|p−y\\| | ΔRES |")
    w("|---|---|---|---|---|")
    for i, mo in enumerate(months):
        w(f"| {mo} | {p[i]:.2f} | {y[i]:.0f} | {abs(p[i] - y[i]):.2f} | {dres[i]:+.6f} |")
    w("")
    worst = sorted(range(len(months)), key=lambda i: -(abs(p[i] - y[i])))[:WORST_N]
    w(f"## 最差 {WORST_N} 月（\\|p−y\\| 降序）")
    w("")
    w("| # | 月 | p | y | \\|p−y\\| | (p−y)² |")
    w("|---|---|---|---|---|---|")
    for rank, i in enumerate(worst, start=1):
        w(f"| {rank} | {months[i]} | {p[i]:.2f} | {y[i]:.0f} "
          f"| {abs(p[i] - y[i]):.2f} | {(p[i] - y[i]) ** 2:.4f} |")
    w("")
    w("## 答案分布")
    w("")
    ans = [bool(r["answer"]) for r in records]
    ans_c = Counter(ans)
    y_c = Counter(int(v) for v in y)
    hit = sum(1 for a, yv in zip(ans, y, strict=True) if a == bool(yv))
    w(f"- answer：true {ans_c[True]} / false {ans_c[False]}"
      f"；y：1 {y_c[1]} / 0 {y_c[0]}"
      f"；answer==y（方向命中）{hit}/{len(ans)} = {hit / len(ans):.4f}")
    w("- 2×2（answer × y）：true∧1="
      f"{sum(1 for a, yv in zip(ans, y, strict=True) if a and yv == 1.0)}"
      f" true∧0={sum(1 for a, yv in zip(ans, y, strict=True) if a and yv == 0.0)}"
      f" false∧1={sum(1 for a, yv in zip(ans, y, strict=True) if not a and yv == 1.0)}"
      f" false∧0={sum(1 for a, yv in zip(ans, y, strict=True) if not a and yv == 0.0)}")
    p_c = Counter(f"{pv:.2f}" for pv in p)
    clusters = ", ".join(f"{k}:{v}" for k, v in p_c.most_common(6))
    w(f"- p 值聚类（两位小数 top6，反聚类观察 arXiv:2609.32470 同源）：{clusters}"
      f"（distinct(2dp)={len(p_c)}；全精度 distinct={len(set(p))}=值桶数）")
    coerced = [r["month"] for r in records if r.get("answer_coerced_from_string")]
    w(f"- answer_coerced_from_string：{len(coerced)} 月"
      + (f"（{', '.join(coerced)}）" if coerced else "（无——全部原生布尔答复）"))
    w("")
    w(f"[epoch1-calibration] {EXPLORATORY_LABEL}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="epoch-1 校准聚合器（Murphy 三分量，"
                                 "EXPLORATORY REPLAY 只读）")
    ap.add_argument("--advance-root", default=str(ADVANCE_ROOT_DEFAULT))
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--stdout", action="store_true", help="打印报告而不写文件")
    args = ap.parse_args(argv)
    try:
        records, dup_dirs = load_month_records(Path(args.advance_root))
        report = build_report(records, dup_dirs)
    except AggregateError as exc:
        print(f"[epoch1-calibration] EXIT 3: {exc}", file=sys.stderr)
        return 3
    if args.stdout:
        print(report)
    else:
        out = Path(args.out)
        out.write_text(report, encoding="utf-8")
        print(f"[epoch1-calibration] wrote {out} "
              f"({len(records)} months,Murphy identity asserted)")
    print(f"[epoch1-calibration] {EXPLORATORY_LABEL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
