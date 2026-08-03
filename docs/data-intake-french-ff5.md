# 数据接入 7 门落表 — French FF5 日频因子 + FRED DFF（RES-02）

> 状态：**v0.1 · 2026-08-03 · RES-02（BASELINE-FF5-001）数据准入记录**。
> 依据 `docs/data-intake-rubric.md` 的 7 门清单；判定矩阵：**G1 + G2 过 + G3 已验证** → 可
> confirmatory；**G1 + G2 过 + G3 不可证** → 快照冻结 + **exploratory**；任一门不过 → 仅
> exploratory 或 REJECT。
> **Owner 签注：待签（见 §8）— 未签注前本数据不得进入任何 confirmatory 路径。**

---

## 1. 数据源

| 项 | FF5（Fama-French 5 因子，日频） | DFF（联邦基金有效利率，日频） |
|---|---|---|
| Provider | Kenneth French Data Library（Tuck, Dartmouth） | FRED / ALFRED（US Federal Reserve） |
| 文件 | `F-F_Research_Data_5_Factors_2x3_daily_CSV.zip`（bulk ZIP） | ALFRED series `DFF` observations JSON |
| URL | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_daily_CSV.zip | https://api.stlouisfed.org/fred/series/observations |
| 频率 | 日（月频仅作交叉核对，不接入） | 日（工作日） |
| 用途 | 股票特定滚动 beta 的因子侧输入（`aionis.ingest.ff5`） | ΔDFF（as-of）作为 `beta_dff` 的因子侧输入（`aionis.ingest.macro_dff`） |
| 复用 | `src/aionis/eval/ff5_residual.py` 的 fetch/parse 模式（bulk ZIP + 百分比→小数） | `src/aionis/features/macro_surprise.py` 的 ALFRED vintage as-of 模式 |

## 2. 7 门判定

### G1 — License allowlist

- **FF5**：French Data Library = **免费学术使用**，**不在** MIT / Apache-2.0 / BSD / CC0 /
  CC-BY-4.0 白名单（`docs/data-license-allowlist.md`）→ **G1 不通过（非白名单）**。
  - 后果：FF5 侧特征**仅 exploratory**，绝不可 confirmatory（trial `mode: exploratory`）。
  - 需要 **owner 签注**（§8）接受该限制后本数据集方可接入（即使仅 exploratory）。
- **DFF**：US 政府公共领域（FRED 数据条款），与 rubric 中 VIX 行同路径 → **G1 通过**，无需
  额外签注。

### G2 — PIT / as-of 时点

- **FF5**：日频因子文件按日发布（d 日值在 d 日美股收盘后公布，**d+1 起可知**）→ 可构造
  as-of 时点 **通过**。消费侧纪律：月末 t 的特征窗口只使用 `date <= t` 的观测；t 月末计算、
  t+1 首个交易日可知（`aionis/features/ff5.py` 的 knowledge-date 不变量测试锁定）。
- **DFF**：ALFRED 每条观测带 `realtime_start`（发布时间）；as-of join 用
  `merge_asof(..., allow_exact_matches=False)`（**严格早于**——同日 16:30 ET 发布的值对 d 日是
  未来信息，d+1 起可知）→ **通过**（与 macro_surprise 同模式）。

### G3 — No-revision contract（无回改契约）

- **FF5**：French **不发布 vintage**，历史值可能被修订 → **不可证**（与
  `ff5_residual.py` 的 leakage 注记一致）。
  - 处置：**首次接入即快照冻结**——`data/cache/ff5_daily_snapshot.csv` + `.sha256`；
    rerun 只读快照（零 HTTP，bit-identical，H6）；**上游修订 = 新快照 + 新 ledger 行**，
    绝不静默覆盖。→ 按判定矩阵：**快照冻结 + exploratory**。
- **DFF**：FRED vintage **不可回改**（immutable）→ **通过**（confirmatory-tier）。

### G4 — Reproducibility / snapshot discipline（可复现）

- 快照文件 + sha256 落 `data/cache/`；runner 把 `ff5_daily_snapshot_sha256`、
  `dff_alfred_cache_sha256`、source URL、fetch-ts 写入 run config（owner 签注后由 owner 写入
  ledger 行）→ **通过**。
- 快照 sha256 漂移 → `RuntimeError`（fail closed，G3 防线；`tests/test_ff5_ingest.py` 锁定）。

### G5 — Exploratory-only by default（默认探索性）

- FF5（G3 不可证）→ 仅 exploratory：BASELINE-FF5-001 `mode: exploratory`，不进 headline；
  **DFF via ALFRED 为 confirmatory-tier**（G2+G3 均过）。→ **通过**（按判定）。

### G6 — Selection / survivorship honesty（选择诚实）

- FF5 是**组合级因子**（市值 / 等权组合收益差，非个股级观测）→ 声明为 scope 限制：滚动暴露
  与交互特征的经济解释**不扩大为因果声明**（对个股 = 暴露估计，非处置效应）。
- DFF 为全市场宏观序列，无 selection 问题。→ **通过**（声明入 `docs/baseline-ladder.md`）。

### G7 — Politeness / ToS（礼貌）

- FF5：bulk ZIP **单次**获取（cache-first；rerun 零 HTTP）；共享 `HttpRequestPolicy`——
  **≥2s host spacing + 有界指数退避 + fail closed**（`tests/test_ff5_ingest.py` 锁定
  sleeps == [2.0, 4.0] 与持久 5xx 不落盘）。
- DFF：走 ALFRED 既有缓存路径（`alfred_DFF.json`），同 politeness 机制。
- 不礼貌 = 被限速/封禁 = 断供 = 数据腐烂（破坏 G4）。→ **通过**。

## 3. 判定矩阵结论

| 数据集 | G1 | G2 | G3 | 结论 |
|---|---|---|---|---|
| **French FF5 日频** | ✗ 非白名单（学术免费） | ✓ 日发布，d+1 可知 | ✗ 无 vintage | **快照冻结 + exploratory**（owner 签注后接入） |
| **FRED DFF** | ✓ 公共领域 | ✓ ALFRED as-of | ✓ vintage 不可回改 | **confirmatory-tier**（同 VIX 路径，无需签注） |

## 4. 落地代码

- `src/aionis/ingest/ff5.py` — FF5 日频获取 + 快照/sha256（G3/G4 冻结；politeness ≥2s；
  无 vintage → exploratory 注记）。
- `src/aionis/ingest/macro_dff.py` — DFF ALFRED vintage as-of（`allow_exact_matches=False`，
  同 macro_surprise 严格纪律；绝不使用当前修订序列）。
- `src/aionis/features/ff5.py` — 股票特定滚动暴露 + 交互（因子侧输入只经 interaction 路径；
  原始市场级因子列不进入 config）。
- `scripts/res_02_baseline_ff5_run.py` — runner（快照-first；RD-13 fail-closed；不写 ledger）。

## 5. 证据（hermetic，无真实网络）

- `uv run pytest tests/test_ff5_ingest.py tests/test_macro_dff.py tests/test_ff5_exposures.py -q` → **PASS**
  （含快照 sha256 不变量、future-truncation、knowledge-date、strictly-before as-of、
  no-lookahead perturb）。
- `uv run ruff check`（相关文件）→ clean。

## 6. 遗留风险

- FF5 无 vintage：即使快照冻结，历史因子值仍是「获取时点的现值」——对探索性暴露估计可接受；
  若未来需要 confirmatory 级别，需替换为带 vintage 的因子源（新 trial + 新 ledger 行）。
- 获取时文件名 / 文档行数若变化：解析器按「首个 8 位日期行」鲁棒定位 + header 软校验 + 失败
  关闭（fail closed），不会静默产出错误因子。

## 7. References

- `docs/data-intake-rubric.md`（7 门矩阵）、`docs/data-license-allowlist.md`（白名单）
- `tasks/active/TASK-RES-02-baseline-ff5.md`（spec；§French 数据 7-gate 准入）
- `src/aionis/eval/ff5_residual.py`（既有 FF5 工具：fetch/parse 复用 + G3 注记）
- `docs/baseline-ladder.md`（BASELINE-FF5-001 设计 + 数据源/PIT/特征说明）

## 8. Owner 签注（待签）

> **状态：PENDING — 未签注前 BASELINE-FF5-001 保持 owner gate（HOLD）状态。**
> 签注即接受：G1（French 学术免费、非白名单许可 → FF5 侧仅 exploratory）与
> G3（无 vintage → 快照冻结）判定；并授权 BASELINE-FF5-001 trial 启动（股票特定滚动暴露/
> 交互设计）。签注后由 Orchestrator 更新本文件状态与 `state/handoff.md`。

```text
Owner:  __________        日期: __________
签注内容: 接受 G1 / G3 判定 + 授权 BASELINE-FF5-001（exploratory）
```
