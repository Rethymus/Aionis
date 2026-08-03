# 2026-08-03 citation-integrity-audit.md — 引用完整性审计 + 外部轮子复用裁决

> 产出: 4 个并行验证 agent(按难度分层: haiku ×2 / sonnet ×2)审计全部 arXiv 引用与外部仓库。
> 方法: 每个条目实抓 arxiv.org/abs/ 页面 + 搜索代码可用性; 许可证按
> `docs/data-license-allowlist.md`(MIT/Apache/BSD) 判定可复用性。文档修正已应用
> (`docs/frontier_positioning.md`), 见下文 §3。

## 1. 结论摘要

- **11/11 全部引用真实存在、年份无误,无一条编造或张冠李戴。**
- 1 处措辞过度引申 (`2504.14765` "functional lookahead bias" / `market_impact` 不在摘要) + 1 处意译未锚定 + 3 处裸 ID —— 全部修正。
- **外部轮子复用面: 唯一合规可复用 = `purgedcv`(MIT, 已安装已锁定已使用)**; 其余外部仓库全部被 7-gate 拒于门外(无 LICENSE / 无仓库 / 链接失效)。
- **FINSABER (`waylonli/FINSABER`) = Apache-2.0, 通过白名单** —— 且正是 Track B 正在集成的轮子(工作树已有 `src/aionis/eval/finsaber_mount.py`), 本审计为其提供了外部验证证据。

## 2. 逐条目裁决

### 2.1 高相关(直接支撑 null-favored / 反泄漏论证)

| arXiv | 标题(实际) | 验证 | 可复用代码/许可 |
|---|---|---|---|
| 2601.13770 | Look-Ahead-Bench (Benhenda 2026) | ✅ 完全相符 | `benstaf/lookaheadbench` **无 LICENSE → 保留所有权利 → 不可复用** |
| 2605.23959 | When Alpha Disappears: One-Switch Benchmark (Zhang et al. 2026) | ✅ 实质相符(文档原为意译) | 无代码链接 |
| 2504.14765 | The Memorization Problem (Lopez-Lira/Tang/Zhu 2025) | ✅ 作者年份匹配, **措辞过度引申已修正** | 无代码; 论文 CC BY-NC-ND 4.0(限制性 → 仅引用) |
| 2510.07920 | Profit Mirage (Li et al. 2025) | ✅ **"51-62% Sharpe decay" 逐字核实** (§2.1.3: 51.48%–62.23%) | 无公开仓库; FinLake-Bench 声称发布但链接未找到 |
| 2605.16895 | The Alpha Illusion (Ye et al. 2026) | ✅ 相符 | **代码链接已失效** (github.com/hj1650782738/Trading 404) |
| 2505.07078 | Can LLM-based Investing Outperform Long-Run? = **FINSABER** (Li et al. 2025, KDD'26) | ✅ 相符 | **`waylonli/FINSABER` Apache-2.0 ✅ 可复用** (157★, V2 数据 HF) |
| 2512.23847 | Detecting Lookahead Bias in LLM Forecasts (Gao et al. 2025) — **LAP test** | ✅ 逐字相符 | 无仓库; 文档 §2.4 审计工具引用成立 |
| 2605.24564 | FinCAD: Summoning the Oracle to Slay It (Li/Wang/Ma 2026) | ✅ 相符 | 无公开代码 |
| 2607.04958 | Look-Ahead-Freedom as Temporal Non-Interference (Fonseca 2026) | ✅ 相符 | artifact 声称存在, 链接未验证 |

### 2.2 中相关(因果/时序,非泄漏主线)

| arXiv | 标题(实际) | 验证 | 可复用代码/许可 |
|---|---|---|---|
| 2411.06391 | CausalStock (NeurIPS 2024) | ✅ 相符 | **无官方仓库** |
| 2406.16964 | Are LMs Actually Useful for TS Forecasting? (Tan et al., NeurIPS'24 Spotlight) | ✅ 逐字相符 | 无代码链接 |
| 2502.04592 | CAMEF (SIGKDD 2025) | ✅ 相符 | `lakebodhi/CAMEF` **无 LICENSE → 不可复用** |

### 2.3 外部 GitHub 仓库(非 arXiv)

| 仓库 | 裁决 |
|---|---|
| `eslazarev/purged-cross-validation` | ✅ **MIT, 活跃, wheel 已安装** (`robustness` extra, pinned `>=0.1.2`, 可导入) — 文档"已确认复用"断言核实为真 |
| `ElMonstroDelBrest/ChaosAI` | 文档 §2C 引用其 "标准横截面 OOS 协议泄漏 +7 Sharpe" — 未做许可证审计(不打算复用, 仅引用) |
| `mr-sharath/KAIROS` (E2 引用) | 未验证(不在 4 个已验证 ID 中, 为 GitHub 引用) — 留待 E2 定稿前核 |

## 3. 文档修正(已应用)

`docs/frontier_positioning.md`:
- L62-65: "prove LLM weights encode post-t outcomes... ('functional lookahead bias')" → 改为摘要实际表述(recall-level memorization / instruction-boundary fails / anonymization leaks), 并显式注明该术语非原文。
- L49: "Point-in-time one-switch audit" → 锚定实际标题 "When Alpha Disappears: A One-Switch Benchmark..."。
- L35-36: 3 个裸 ID → 补全 `arxiv.org/abs/` URL 前缀。

## 4. 复用准入纪律生效的证据

7-gate 前哨审计(license/PIT/no-revision/snapshot/exploratory/selection/politeness)在本批中拦截了全部不合规候选:
- `lookaheadbench`(高相关, 唯一有代码的) — 无 LICENSE → 拒
- `CAMEF`(有代码+数据) — 无 LICENSE → 拒
- Alpha Illusion 代码 — 链接失效 → 拒
- `2504.14765` — CC BY-NC-ND → 仅引用
- **通过: `purgedcv`(MIT) + `FINSABER`(Apache-2.0, Track B 集成中)**

## 5. 遗留(非阻塞)

- Profit Mirage FinLake-Bench 与 `2607.04958` artifact 链接声称存在但未定位 → 如需用作记忆探针, 可邮件索取或自建等价探针。
- `mr-sharath/KAIROS` 未验证 → 建议 E2 定稿前核。
- FINSABER Apache-2.0 的挂接已在 Track B lane 推进(`finsaber_mount.py` 在树), 本审计确认其许可证合规。
