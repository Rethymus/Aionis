# Track C 预注册骨架（A 股 + 条件化 rank-IC）— **PROPOSED v0.1 草案**

> 日期：2026-08-03
> 类型：预注册**骨架草案**（**PROPOSED，非冻结**；多处 TBD 待 T1 + owner 决策）
> 状态：不触冻结面 / ledger；未运行任何 confirmatory/forward 脚本；未观察任何 outcome。
> 关联：[`track-b-preregistration.md`](../../docs/track-b-preregistration.md)（文体范式 + 共享统计门）、
> [`2026-08-03-qlib-dualregion-poc.md`](../2026-08-03-qlib-dualregion-poc.md)（可行性 + 8 门）、
> [`2026-08-03-conditional-rank-ic-multiplicity.md`](2026-08-03-conditional-rank-ic-multiplicity.md)（gate 7）、
> [`theory-of-computable-reality.md`](../../docs/theory-of-computable-reality.md) §3.1（meso/macro/global 层）、
> [`market-driver-framework.md`](../../docs/market-driver-framework.md) §2/§8（regime 作条件/情景层）。

## 0. 与 B/C/D/E1 + Track B 的关系（新预注册线，绝不污染）

Track C 是**全新预注册线**，与 B/C/D/E1 + Track B 冻结面完全隔离（同 Track B §0 铁律）：新 config = 新
ledger 行；不重写历史；null-favored（前沿共识 Profit Mirage / Alpha Illusion / Lopez-Lira 2025）。

## 1. 单一可证伪 claim（两尾、预注册、null-favored）— **PROPOSED**

> 把"美股 + A 股"双区域统一打分后的 top-quantile 组合，在 **chronological walk-forward** 月频横截面
> rank-IC 上，是否显著优于 price-only baseline？**conditioning = 单个预指定交互项**（treatment × regime），
> 非多个事后子组（见 multiplicity 笔记 §1）。
>
> - null = 下注热门（月频已定价 / 因子 alpha 为泄漏 artifact / 交易成本侵蚀）。
> - 双尾：正 = 双区域增量有效；负 = 更差（过拟合/噪声）；CI 跨 0 = null（紧则可发表）。
> - 等价门（J-T，复用 ADR-010）：RCIₖ ⊂ [−SESOI,+SESOI]。

⚠️ **regime 的具体定义（meso 板块 / macro 市场 / global 跨市场传染）待 owner 冻结**——必须 PIT 构造
（`market-driver-framework.md:178-181` TACO 范式），否则 regime 定义泄漏（批判者 M1）。

## 2. Universe（双区域 PIT）— 部分确认

- **美股**：S&P 500 PIT（`hanshof/sp500_constituents` MIT 主 + `pierrebrunelle` 校验），2016+（沿用 Track B §2 实测 min Jaccard 0.8544 → headline 限 2016+）。✅ 复用 Track B。
- **A 股**：CSI 300/500 PIT（`index-constitution` MIT，`constituents_at(date)`）。⚠️ **待 7-gate 完整审计**（G2 PIT 成分重建方式、G4 snapshot、G7 politeness）—— POC 已查 MIT license + 历史 constituents_at API；深度 7-gate 待 T1/后续。
- 幸存者偏差：经 PIT 成分缓解，**不可根除**（无免费退市 PIT）。headline = 保守上界。

## 3. Features（七大主题映射）— **⚠️ TBD，待 T1（A 股源决策）**

| 主题 | 美股（复用 Track B §3） | A 股 |
|---|---|---|
| ① 行情/价格 | Tiingo+Alpaca ✅ | **✅ 方向**：baostock 价格（MIT，`tradestatus`停牌 + `adjustflag`/`query_adjust_factor`复权因子 + `query_all_stock(date)`历史含退市 → survivorship/停牌/复权均 PIT-able；**价格交易所定、不类基本面回改 → G3 低危**）或 qlib+AKShare 采集器（MIT，commit `83d089b` 2026-05，但 current-code discovery 需用 baostock 历史成分补退市 survivorship）。qlib+TuShare（PR #2067，显式 L/D/P survivorship-free）作 fallback（G1 paid/ToS）。 |
| ② 宏观 | ALFRED vintage ✅ | **✅ 部分**：**ALFRED/OECD 中国序列**（GDP/CPI，如 `CHNGDPNQDSMEI`，**vintage 跟踪 → PIT-safe**，复用现有 `macro_surprise.py`/FRED 适配器）= **headline-OK**。**NBS 直取**（M2/社融/NBS-only）→ GDP/CPI **经证实大幅回改**（Sinclair/Holz：单年 GDP 可上修 16.8%、普查 benchmark 回溯、实际 GDP 系统性上偏；NBS 无公开 vintage API、latest-only）→ **G3 高危 → snapshot+exploratory**（EPU 先例）。复用 `mbk-dev/nbsc`（NBS 访问，latest-only，须 snapshot 冻结）。 |
| ③ 基本面 | EDGAR filed-date PIT ✅ | **✅ 解决方向：cninfo（巨潮，CSRC 官方 = A 股 EDGAR 等价）**——申报日原生 + as-filed PDF + 修订=新公告（revision-transparent，G3 优于 Tushare）；经 OSS 爬虫（`alicexl/a-share-financials` PDF→结构化 / `rollysys/use_cninfo`，**license 待验**）+ Aionis PIT 适配。baostock reject（G3 结构性失败）；Tushare fallback（G1 付费/ToS）。见 [`ashare-fundamentals-source.md`](2026-08-03-ashare-fundamentals-source.md)。 |
| ④ 新闻情绪 | E3 闭集 13D/8-K（受控 ablation） | **TBD**（A 股公告情绪：仅 exploratory） |
| ⑤ 风险 | alphalens/pyfolio ✅ | 复用 |
| ⑥ 回测净成本 | FINSABER ✅ | 复用 |
| ⑦ 市场结构 | FF5 + Amihud ✅ | **TBD**（A 股 FF 等价：CH-CN 因子可得性） |

**gate 4 已解（方向）**：cninfo 路径可行（A 股 EDGAR 等价，as-filed + 申报日 + revision-transparent）。进 headline 前须落实 G1（爬虫 license + cninfo ToS）+ G7（礼貌抓取 ≥2s+backoff）+ G4（snapshot+sha256）+ PDF 解析覆盖 + 历史深度。见 [`ashare-fundamentals-source.md`](2026-08-03-ashare-fundamentals-source.md)。

## 4. Learner — 复用

LightGBM frozen（同全家族）+ `lambdarank`（RD-15，bin_count=5）。零改动。

## 5. Validation（chronological walk-forward）— 复用 + 一个开放设计

- `purged_walk_forward_splits(expanding=True, min_train_months=60, embargo=21)` + `assert_chronological_split`（RD-03）。✅ 复用 Track B §5。
- ⚠️ **开放设计**：双区域是**联合折叠**（同一时间窗同时含美股+A股，regime 跨市场）还是**分区域独立折叠**？
  - 联合：捕捉跨市场传染（global 层），但区域间样本量/交易日历不同（A 股 T+1、涨跌停、停牌）。
  - 独立：干净，但失去传染信号。
  - **待 owner 决策**（影响 regime 定义与条件化交互）。

## 6. Horizon — 复用
h=21 confirmatory（h=10/42 exploratory）。同 Track B §6。

## 7. SESOI / 等价门 — 复用 ADR-010
SESOI ±0.010，looks {60,90,120}，J-T RCI levels 99.44/97.64/95.00%，n_trials=30，HAC SE。应用于**交互项差分**的 rank-IC 序列。

## 8. Multiplicity — 见 multiplicity 笔记
conditioning = **单个预指定交互项**（预算 1，非 K）；n_trials=30 沿用；DSR/haircut/SPA（purgedcv/arch/YannickKae）；Deflated-RankICIR 待 license（haiku 核查中）。

## 9. Baseline — 复用
price-only S1（momentum/reversal/vol/liquidity）+ 等权。DM 检验对象 = 组合收益 loss（H-1 复审纠正）。

## 10. frozen config — **TBD（冻结前不跑 OOS）**
待 §3 features（T1）+ §5 折设计 + §1 regime 定义都 owner 冻结后，才写 config sha256 入 ledger（config_committed BEFORE result）。

## 11. 显式 non-goals
- 不做日内/衍生品/加密；只月频横截面选股（双区域 PIT）。
- 不做 learned world model（判别式 LightGBM + structural-only LLM）。
- **regime/timing 不作第二证伪锚**（`market-driver-framework.md` §2/§8）——只作条件/情景层。
- **A 股基本面若无可过 7-gate 的 filed-date 源 → A 股降为 exploratory-only**（不进 headline），Track C headline 收窄为"美股 rank-IC + A 股 exploratory 条件化"。
- "入手/跑路"仪表盘 = 非主张探索层（轻量 PIT 合同 + "探索性/非投资建议" banner），不作证伪 claim。

## 12. owner-decision 点（flagged，待冻结前裁断）
1. **A 股基本面源**（T1 结果）——headline 可行 vs exploratory-only。
2. **双区域折设计**（联合 vs 独立）。
3. **regime PIT 定义**（meso/macro/global 各用什么 PIT 指标 + TACO as-of 固定窗参数）。
4. **A 股价格 PIT 源** + 中国宏观 vintage 处置（G3）。
5. SESOI/horizon/bin_count 沿用 Track B？（默认沿用）
6. qlib 双区域挂载是否进 Track C（gate 1/2/3 POC 已验可行性，但 ≤3.12 隔离 venv + DatasetH 手术点③接线是实装工作）。

## 13. 不越界声明（PROPOSED）
- 本骨架是 **PROPOSED 草案**；多处 TBD；未触冻结面/ledger/prereg/ADR/config/结果/E3。
- 未运行 confirmatory/strategy/horizon/forward 脚本；未观察任何 outcome。
- Track C 的任何落地都是**新预注册 + 新 config + 新 ledger 行**，绝不静默修改 B/C/D/E1 或 Track B。
- Owner 未冻结前，不构成方向承诺。
