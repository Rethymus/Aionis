# Track Adaptive 预注册 — 自适应（扩窗/在线重训）rank-IC vs 冻结基线（PROPOSED，未冻结）

> **命名澄清**：本 "Track Adaptive" 与既有冻结的 **Track B（七主题选股平台，`docs/track-b-preregistration.md`，
> FROZEN 2026-08-02）无关**——后者是另一条已 `config_committed` 的研究线。本预注册用 "Track Adaptive"
> 避免撞名。分析文档 `reports/design/2026-08-08-live-adaptive-calibration-analysis.md` 中的 "Track B"
> 是该文档对该路径的临时标签，即此处的 Track Adaptive。
>
> **状态：PROPOSED — 未冻结。** 在 owner 审阅 + `config_committed`（sha256 入 ledger）之前，
> **禁止**在任何 OOS 数据上跑自适应 learner。这是反泄漏硬锚（`config_committed BEFORE result`）。
> 本预注册由 owner 2026-08-08 显式授权（"真的要走 Track B"——指此自适应路径），反转了 2026-08-05
> option A 中 "勿追新 alpha" 对**该特定路径**的否决——但**仅限**有纪律的 Track Adaptive（预注册 +
> 多重检验预算 + 与 Track C 硬隔离）。无纪律的 alpha-chasing / rerun-to-significance 仍禁。

## 0. 与既有Track的关系（新研究线，绝不污染）

Track Adaptive 是**独立新研究线**。它**复用** Track C 的冻结 learner + PIT universe 作为**比较器**（baseline），
但**绝不修改** B/C/D/E1/Track C 任一冻结面（ledger 行 / prereg / ADR / config / OOS 产物）。
Track Adaptive 有自己的 `config_committed` 行、自己的 OOS 窗口、自己的 IC 序列。
Track C climax（ledger #49 null）不变。

## 1. 单一可证伪 claim（两尾、预注册、**null-expected**）

**H0（两尾）**：扩窗重训（adaptive）learner 的月频截面 rank-IC 与**冻结** Track-C 基线**无可靠差异**。

- 估计量：`IC_diff = mean(IC_adaptive) − mean(IC_frozen)`，月频，HAC SE。
- 方向：**两尾**（更新可能改善 *或* 恶化 IC；不接受单方向救场）。
- **诚实预期 = null**：power floor σ(IC)≈0.10（`ic_pure_noise_bound.py`）+ Gu-Kelly-Xiu 2020
  发现"更新频率的非主导性"（最佳月 OOS R² 1.08–1.80%，模型类 > 更新频率）→ 更新大概率不改善 IC。
- **价值定位**：Track Adaptive 的贡献是**有纪律的自适应基建 + 诚实跟踪**（证明更新安全、可复现、
  多重检验受控），**不是**制造正 IC。null 是预期可发表结果。

### 1.1 为何不是"救 equivalence"

Track C 的 null 已坐实（#49）。Track Adaptive 不"救"它——它问的是一个**新问题**："更新机制本身
有没有增量？" 若 IC_diff 的 CI 跨零（预期），则"更新无增量"成为**第二条独立 null**，
强化（而非削弱）power-floor 结论。

## 2. Universe（复用 Track C PIT，配对比较）

- 复用 Track C 的 PIT 双区域 universe（`constituents_on`，US S&P 500 + CN），保证与冻结基线
  **同 universe**（干净配对比较）。
- OOS 窗口与 Track C 的 OOS 对齐（使 IC_frozen 可直接配对）；扩窗重训的"扩"从窗口起点开始。
  **待 owner 冻结**具体起止（§10）。

## 3. Features（复用冻结集——隔离"更新"这一变量）

- 复用 Track C 冻结的 feature_cols（41 列 asymmetric，frozen #48）。**禁止**借 Track Adaptive
  加新特征——那会混淆"更新"与"新特征"两个变量。Track Adaptive 唯一的 treatment 是**重训 cadence**。

## 4. Learner + 更新机制（**Track Adaptive 的 treatment 变量**）

- **Learner**：LightGBM（复用冻结，相同超参，避免混淆）。
- **更新机制（默认方案 A）**：**扩窗重训**（expanding-window refit，GKX 2020 标准）——每个 OOS
  月初，用截至该点（purge+embargo 之后）的所有 realized 数据重训，再预测下月。
- **替代（owner 可选）**：B = 在线梯度提升（river/online GBM）；C = 滚动窗（rolling，固定窗长）。
  默认 A（最简、最易无泄漏复现；GKX 先例）。
- **反泄漏硬要求**：每次重训的 fit 数据必须**严格该预测点之前**，且 forward-return 标签经
  **purge + embargo**（复用 PurgedGroupKFold + embargo=21 既有契约），杜绝标签泄漏。

## 5. Validation（chronological walk-forward，配对）

- chronological walk-forward；IC_adaptive 与 IC_frozen 在**同一 OOS 月、同 universe** 上配对。
- 配对差 `d_t = IC_adaptive_t − IC_frozen_t`；HAC 回归 `d_t ~ 1`（Newey-West）给 mean + SE + CI。
- **H6 确定性**：n_jobs=1，seed=0，version-pinned；IC_adaptive 序列跨 run bit-identical（asserted）。

## 6. Horizon

月频。OOS 月数 n（待冻结，见 §10；预期与 Track C 的 71 月 OOS 对齐以配对）。

## 7. SESOI / 门（两尾，**显式 null-expected**）

- **主门（significance，两尾）**：`|mean(IC_diff)| / SE_hac` 的 HAC p-value；α = 0.05 两尾。
  预期不拒绝 H0（null）。
- **次门（equivalence，若 null）**：IC_diff 的 RCI 是否落在 ±SESOI_diff 内。**注意**：IC_diff 是
  *差值*序列，其 σ 可能小于 IC 本身——SESOI_diff 需冻结时单独定（复用 ±0.010 或基于 IC_diff 实证 σ）。
- **禁止**：若主门不显著就"降级"宣等价救场（rerun-to-significance 禁）。两门都预注册在前。

## 8. Multiplicity（**Track Adaptive 的核心风险——DSR/PBO 预算**）

自适应更新本身是一次次"尝试"；表面改进会被多重检验膨胀。**强制**：

- **记录所有 trial**：每个重训 cycle + 每个超参/机制变体 = 1 trial；`n_trials` 入 config。
- **Deflated Sharpe Ratio**（Bailey-López de Prado 2014）：对任何观察到的 IC 改进按 `n_trials`
  deflate 后才报。**未 deflate 的"改进"不构成 claim**。
- **PBO（Probability of Backtest Overfit）**：对选定的更新机制做 combinatorially-symmetric
  cross-validation，报 PBO（>0.5 = 过拟合高危）。
- **预算**：`n_trials` 预冻结（owner 定上限）；超出预算的新 trial = 新 `config_committed` 行。

## 9. Baseline（冻结 Track-C learner 作为比较器）

- 比较器 = Track C frozen #48 learner 在同 OOS 窗口的 IC 序列（`IC_frozen`，bit-identical 复现）。
- **禁止**重训基线（基线就是"冻结"——那是它的定义）。

## 10. frozen config（**待 owner `config_committed` 冻结**）

预指定（冻结前定，无 outcome 选择）：
- estimand: `IC_diff = mean(IC_adaptive) − mean(IC_frozen)`，HAC，两尾。
- universe + OOS 窗口（与 Track C 配对）。
- feature_cols = Track C frozen #48 的 41 列（**零改动**）。
- 更新机制 = A/B/C（owner 选；默认 A 扩窗重训）+ refit cadence（每月）。
- purge+embargo 参数（复用 Track C）。
- SESOI_diff（次门；需单独冻结）。
- `n_trials` 上限 + DSR/PBO 报告要求。
- H6 seeds + version pin。

`config_committed` 行写入 `runs/ledger.jsonl` **后**才允许首次 OOS 跑。

## 11. 显式 non-goals

- **不**制造正 IC / 不追新 alpha 信号（power floor 禁）。
- **不**修改 Track C/B(七主题)/D/E1 任一冻结面。
- **不**在 OOS 窗口内调超参"追"更好 IC（DSR/PBO 会抓）。
- **不**把自适应 learner 的输出喂进**研究管线**的 confirmatory 估计量（Track Adaptive 是独立估计量）。
  （display 层的自适应——`src/aionis/eval/model_drift.py`——是另一回事，已是 leakage-safe display 工具。）

## 12. owner-decision 点（**PROPOSED，待裁断**）

- **D1**：更新机制选 A（扩窗重训，默认）/ B（在线 GBM）/ C（滚动窗）？
- **D2**：OOS 窗口起止（建议与 Track C 的 71 月 OOS 配对）？
- **D3**：SESOI_diff（次门等价界）取 ±0.010 还是基于 IC_diff 实证 σ？
- **D4**：`n_trials` 预算上限（DSR/PBO 的 N）？
- **D5**：是否要求 PBO 报告（combinatorial CV，计算较重）？
- **D6 GO**：审阅本预注册 → `config_committed` 冻结 → 首次 OOS 跑。

## 13. 不越界声明（PROPOSED，未冻结）

本轮纯新建 `docs/track-adaptive-preregistration.md`（PROPOSED）+ state/memory 更新；**0 ledger / frozen /
prereg / ADR / config / OOS 产物 / E3** 改动；未跑任何 adaptive learner；未观察任何 Track Adaptive OOS
metric；Track C 冻结面（#49 null）完全未触。

## 14. 引用

- Gu-Kelly-Xiu 2020 (RFS) — 扩窗重训先例 + "模型类 > 更新频率"；最佳月 OOS R² 1.08–1.80%。
- Bailey & López de Prado 2014 (JPM) — Deflated Sharpe Ratio；"DSR/PBO 尤适 adaptive 研究"。
- Bailey/Borwein/LdP/Zhu — Probability of Backtest Overfitting。
- `decisions/ADR-010-sesoi-tost-sequential-gate.md` — SESOI/J-T 门（精神复用）。
- `reports/design/2026-08-08-live-adaptive-calibration-analysis.md` — Track A/Adaptive 分析。
- `scripts/ic_pure_noise_bound.py` + `track_c_power_analysis.py` — power floor 证据。
