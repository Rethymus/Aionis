# Track C power analysis — SESOI / look-schedule 选项决策包

> 状态：**PROPOSED · 2026-08-05 · opus Orchestrator 起草 · 业主审阅**。ledger #49 confirmatory 已入账
> （combined IC −0.0088 null，J-T look-1 NOT_EQUIVALENT）。本包用 prospective power analysis 揭示一个
> **设计级发现**并给出 3 个选项。**不写 ledger、不触冻结面**——这些都是业主选择后的执行动作。
>
> 证据：`scripts/track_c_power_analysis.py` + `runs/track_c_confirmatory_power_analysis.json`（待 sonnet
> review `reports/audits/2026-08-05-power-analysis-review.md` 核验方法论）。

---

## 摘要：look-1 NOT_EQUIVALENT 不是局部保守，是结构性必然

confirmatory #49 跑出 look-1 NOT_EQUIVALENT 后，最自然的问题是"look-2/3 能否宣布等价？"。
power analysis 用 ledger #49 的真实 IC 噪声（σ≈0.106，lag-1 ρ≈0.07，校准自 observed se_hac=0.0126 @ n=71）
投影了 J-T 60/90/120 look schedule 在 SESOI ±0.010 下的可达性：

| Look | z | n_min（宣布等价） | P(equiv) bootstrap | RCI half med |
|---|---:|---:|---:|---:|
| 1 (n=60) | 2.772 | **869 月（72.5 年）** | 0.0000 | 0.037 |
| 2 (n=90) | 2.263 | **580 月（48.3 年）** | 0.0000 | 0.025 |
| 3 (n=120) | 1.960 | **435 月（36.2 年）** | 0.0000 | 0.019 |

**结论**：即便 look-3（最终 look，n=120）的 RCI half-width（0.019）也是 SESOI（0.010）的 ~2 倍。
宣布等价需 ~36+ 年月频数据。**E3 forward-live 即使点火，也无法在本研究周期内达等价宣告**。

这是月频 rank-IC 噪声地板（σ≈0.10）与 ±0.010 SESOI 的数学必然，**非 bug、非数据不足、非工程缺陷**。

---

## 1. 这是"不乐观"吗？（诚实判读）

**部分是**：原设计的"confirmatory 等价宣告"目标在 SESOI ±0.010 + 120 月 look horizon 下不可达。
look-1 NOT_EQUIVALENT 不是"等 look-2 就好"，而是"整个 schedule 都会 NOT_EQUIVALENT"。

**但不是"失败"**：
- 点估计 null（−0.0088）+ 全部 14 条 exploratory null → treatment 无 alpha 的证据很强
- 反泄漏纪律端到端演示（config 先于结果 + H6 真实数据证明）= 主贡献，不变
- power-limit 披露本身就是方法学贡献（" equivalence testing 在月频 rank-IC 的 power floor"）

**未触发"调整重测"**：重测不会改变噪声地板。需调整的是 **SESOI 或 framing**（业主决策）。

---

## 2. 业主的 3 个选项

### 选项 A（推荐）—— 接受 reframing：null + 纪律 + power-limit

- **不动冻结面**：SESOI、look schedule、#48/#49 全部不变
- draft v1.0 的贡献叙事改为：① 反泄漏纪律作为研究对象（主贡献）；② 15 条 null 点估计（强证据）；
  ③ **power-limit 披露**（J-T 60/90/120 在 ±0.010 下的 power floor = 36+ 年，诚实的方法学发现）
- 收益：诚实、零冻结面改动、可发表（"we pre-registered an equivalence test; the point estimate is null
  across 15 configurations; the test is underpowered to declare strict equivalence at ±0.010 within 120 months;
  the discipline held end-to-end"）
- 代价：放弃"等价已宣告"的强 claim（但该 claim 本就不可达）

### 选项 B —— 拓宽 SESOI 到 ±0.025（新 amendment #49b）

- look-3 (n=120) 的 RCI half 0.019 < 0.025 → **可达等价宣告**（若 true |IC|≈0）
- 需要：新 ledger 行 amendment（#49b），拓宽 `sesoi_rank_ic` 从 0.010 到 0.025，同步改 ADR-010 + prereg §7
- 收益：look-3 可宣布 EQUIVALENT（更强的等价 claim）
- 代价：**等价意义减弱**（±0.025 = 2.5% 月 IC，经济上仍小但不如 ±1% 严格）；post-hoc 改 SESOI 有
  "moving goalposts" 嫌疑（需诚实披露：原 SESOI 0.010 在 power analysis 后 deemed infeasible）
- bootstrap 投影：look-3 P(equiv) at SESOI 0.025 ≈ ?（待补算，大概率 > 0.5）

### 选项 C —— 延长 look horizon 到 n=435+（36 年）

- 新 amendment 加 look-4 (n=435)，look-3 z=1.960 + n=435 → RCI half ≈ 0.010 ≈ SESOI
- 收益：spec-faithful 保持 ±0.010
- 代价：**不可行**（需 36 年 forward-live；E3 当前 NO-GO；本研究周期内无法完成）

---

## 3. 推荐

**选项 A（accept reframing）**。理由：
1. **诚实优先**：power analysis 揭示 ±0.010 在月频 rank-IC 不可达，诚实披露比拓宽 SESOI（post-hoc）
   更符合反泄漏纪律
2. **贡献不减**：主贡献（反泄漏纪律）+ 15 条 null + power-limit 披露 = 完整可发表单元
3. **零冻结面风险**：不动 SESOI / look / ADR，无 post-hoc "moving goalposts" 嫌疑
4. **E3 决策简化**：若接受 A，E3 forward-live 的目的从"达等价宣告"降级为"延续 null OOS 积累"
   （可选，非必需）

选项 B 的拓宽 SESOI 有 post-hoc 风险（即使 power analysis 支撑），除非业主认为"±0.025 经济上仍可接受"
且接受"原 SESOI deemed infeasible"的披露代价。

选项 C 不可行，列出仅为完整性。

---

## 4. 签注后的执行（若业主选 A，零额外动作）

- A：本 brief + power analysis artifact + draft §6（已写）= 收束。draft v1.0-draft → 可定稿。
- B：我起草 amendment #49b（拓宽 SESOI 0.010→0.025）+ 同步 ADR-010/prereg §7 + 补 bootstrap at 0.025 +
  重跑 J-T 门 at 新 SESOI → 新 ledger 行 → 重 sediment confirmatory（look-3 或达 EQUIVALENT）。
- C：不执行（列出而已）。

---

## 5. 不越界声明（PROPOSED）

- `[F]` 本包是决策文档；未写 ledger；未改 SESOI / look schedule / ADR / prereg / config。
- `[F]` power analysis 用 gitignored artifact（ledger #49 IC series），不改 frozen surface。
- `[I]` sonnet review of power analysis methodology 待回报（`reports/audits/2026-08-05-power-analysis-review.md`）；
  若 review REQUEST CHANGES，数字可能调整但"结构性欠功率"结论大概率不变（n_min 量级稳定）。
