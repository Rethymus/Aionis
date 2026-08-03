# qlib 双区域 POC — Option A 可行性证据报告

> 日期：2026-08-03
> 类型：POC 证据报告（研究证据，**非 ADR、非决策**）
> 状态：不修改任何冻结 spec / pre-registration / ledger / config / 结果。
> 触发：Option A（双市场 rank-IC + 条件化特征 + 入手/跑路仪表盘）辩论 → 独立批判者 REJECT
> 裁决 → 辩护/裁断 agent 因 proxy `[1210]` 缺失 → owner 授权 2 天 qlib POC（可逆、不碰冻结面）
> 以**证据替代口舌**。
> 证据口径：`[F]` 源码/运行时直接支持；`[I]` 推断。

## 0. 一句话裁决

qlib 双区域**可行，带实证背书的门**。批判者 REJECT 的 "vaporware / 捏造 / 当日快照" 根基被
源码实证抽掉；但其 #1（baostock G3）被**验证并强化**为**结构性不可合规**——Option A′ 须把
A 股基本面源从 baostock 换成 filed-date 键源（cninfo / Tushare-`ann_date` / 自建 EDGAR 等价物）
或降为 exploratory-only。

## 1. 背景（辩论 → POC）

owner 愿景：双市场（美股 S&P 500 + A 股）+ 双目标（rank-IC + 入手/跑路）。orchestrator 提议
**Option A**（rank-IC 为唯一证伪锚；板块/宏观/跨市场传染作条件化特征；入手/跑路降为非主张
探索性仪表盘；A 股经 qlib 双区域挂载 + `index-constitution` + 7-gate 审 baostock）。

独立批判者（`oh-my-claudecode:critic`, opus，唯一跑通的独立 agent）下 **REJECT**：指控 baostock
违 G3、qlib POC 未跑（feasibility vaporware）、Track B 冻结面污染、条件化 rank-IC 多重检验、
仪表盘无问责、Diebold-Yilmaz 包"捏造"等。辩护/裁断 agent 因 `[1210]` proxy 故障 5 次失败
（同步 spawn 3 次 + 后台执行 2 次）。owner 授权用 qlib POC（合成数据、可逆、不碰冻结面）取证。

## 2. 五条硬证据

### 2.1 qlib 双区域特性存在 `[F]`
- `qlib/constant.py:10-11`：`REG_CN = "cn"` / `REG_US = "us"`（+ `REG_TW`）。
- `qlib/config.py:317-322`：`REG_CN:` / `REG_US:` 区域配置块；`:160` `"pit_provider": "LocalPITProvider"`。
- `scripts/data_collector/cn_index/collector.py:328/356`：`class CSI300Index` / `class CSI500Index`，
  从 `csindex.com.cn` **历史调入/调出公告**重建成分（**非当日快照**）。
- `scripts/data_collector/pit/collector.py:12`：`import baostock as bs`（qlib 的 A 股 PIT 采集器）。
- → 批判者 **#2 / #8 / #10** 的 vaporware / 捏造 / 当日快照**实证为假**。

### 2.2 cp313 集成门 `[F]`
- pyqlib 0.9.7 wheel 仅 `cp38…cp312`；Aionis 实际跑 **Python 3.13.7**（`requires-python=">=3.10"`）。
- 绕过已验：miniconda 3.11 隔离 venv，`IMPORT_OK 0.9.7`（`REG_CN/US` + `DatasetH` + `RobustZScoreNorm`
  全可导入）。
- → Option A′ 新增门：**qlib 跑 ≤3.12 隔离 venv/进程**（或 Aionis 降级）。原方案/POC 文档未标；
  **部分验证批判者 #2 "可行性未证"**。

### 2.3 RobustZScoreNorm 泄漏陷阱实证确认 + 折内钉修复有效 `[F]`
合成运行时（5 股 × 100 bdate；train N(0,1)，test N(5,1)）：

| fit 切片 | TRAIN z-median | 判读 |
|---|---:|---|
| CLEAN（仅 train，折内钉） | **+0.0000** | 正确，无泄漏 |
| LEAKY（train+test） | **−0.3453** | train 统计被 test 污染，系统性偏移 |
| TEST（CLEAN 归一化下） | +3.0000 | OOD，正确 |

- 源码 `qlib/data/dataset/processor.py:198-199` 自带警告："`fit_end_time` **must not** include any
  information from the test data!!!"。
- → **陷阱真实；折内钉 `fit_start/end`（surgery ①）修复有效。** Aionis 能无泄漏用 qlib，前提是
  正确钉折内训练段。

### 2.4 DatasetH 手术点 ③ 需真实接线 `[F]`
- 最小合成测试用错构造器：`DataHandlerLP(loader=...)` 在 0.9.7 抛 `TypeError`（`DataHandler.__init__() got
  an unexpected keyword argument 'loader'`）。
- 非不可行——与 [`qlib-fork-vs-library-poc.md`](design/2026-08-02-qlib-fork-vs-library-poc.md) 手术点 ③
  "3h 子类化 `DatasetH`" 估计一致。待正式 POC-A 接 `purgedcv` 折索引。

### 2.5 baostock G3 结构性不可合规 `[F]`（关键）
- `baostock/evaluation/season_index.py:245/589`：`query_profit_data(code, year=None, quarter=None)` /
  `query_balance_data(code, year=None, quarter=None)`。
- **纯 (year, quarter) 期末键；无 as-of / 无 vintage / 无 pubDate 入参。** 对比 Aionis 美股侧 EDGAR
  经 `edgartools` 是 **filed-date 键**（`features/fundamentals.py:pit_align`, `align_on="filed"`，真 PIT）。
- API 设计无法提供 PIT 安全申报值；A 股财报修正/更正会静默回改，且 API 层无机制钉住原始值或检测回改。
- → 批判者 **#1 验证并强化**：不是"未证实会回改"，而是**结构性不可合规**（无 as-of 机制）。
  qlib 只证了能**摄入** baostock，没证 baostock **不回改**——后者是数据源属性，源码已证其 API 无 PIT 语义。

## 3. Option A′ 实证背书的门

| # | 门 | 状态 | 出处 |
|---|---|---|---|
| 1 | qlib 跑 ≤3.12 隔离 venv/进程 | ✅ 已验绕过（3.11） | §2.2 |
| 2 | 钉 RobustZScoreNorm 折内 fit_start/end | ✅ 陷阱已证、修复有效 | §2.3 |
| 3 | DatasetH 手术点 ③ 接 purgedcv 折（3h 子类化） | 待 POC-A | §2.4 |
| 4 | **A 股基本面 = filed-date 键源（cninfo/Tushare-`ann_date`/自建），baostock 仅非 headline** | 🆕 G3 强化门 | §2.5 |
| 5 | A 股 = 新 Track C 预注册，绝不污染 Track B 冻结面 | 流程门 | 批判者 #3 |
| 6 | 一次只加一层，对照治理预算 | 流程门 | 批判者 #6 |
| 7 | conditioning = 单个预指定交互 + 显式多重检验预算 | 统计门 | 批判者 #4 |
| 8 | 仪表盘层 = 轻量 PIT 合同 + "探索性/非投资建议" banner | 设计门 | 批判者 #5/#9 |

## 4. 对辩论的影响

- 批判者 **#2 / #8 / #10**（vaporware / 捏造 / 当日快照）：**实证为假**——REJECT 根基被抽。
- 批判者 **#1**（baostock G3）：**验证并强化**——唯一被 POC 证成的承重点，但 Option A′ 换源可解。
- 批判者 **#3 / #6 / #4 / #5 / #9**：流程/设计/统计门，与 POC 无关，继续成立并已纳入 A′ 门。
- **净**：Option A′ **条件-sound**；批判者 REJECT 在 "vaporware" 层面被推翻、在 "G3" 层面被验证但可解。
- **独立性局限**：批判者是真独立 agent；辩护/裁断因 `[1210]` 缺失，由 orchestrator 非独立核查替代
  （已显式做偏向校正：给独立批判者加权、审视自评自利偏差）。完整三方辩论待 proxy 恢复后可补。

## 5. 未解（需后续取证）

- baostock **返回字段**是否含 `pubDate` 可重建 vintage（需一次 `bs.login` 实查；当前仅源码/API 证据，
  已足以判 G3 结构性风险，但若 `pubDate` + 全量历史申报可得，或可部分缓解）。
- A 股 filed-date 键源的 7-gate（[`data-intake-rubric.md`](../docs/data-intake-rubric.md)）：cninfo license/
  可达性、Tushare `ann_date` 的 G1 license/ToS、akshare 回改行为。
- DatasetH 手术点 ③ 真实接线（POC-A 3h）。
- `index-constitution`（MIT，CSI 300/500 PIT 成分）的 7-gate 与 hanshof 交叉校验。

## 6. 不越界声明

- `[F]` 本 POC 在 scratch 目录 `/home/re/code/aionis-qlib-poc/`（**Aionis 仓库外**），合成数据，
  **未 commit、未触冻结面 / ledger / prereg / ADR / config / 结果 / E3**。
- `[F]` 网络操作仅：GitHub clone/raw fetch（qlib 源码）、PyPI 安装（`pyqlib`、`baostock` 包）。**未**连
  baostock.com 数据服务（无 `bs.login`、无数据查询），**未**跑真实 research/confirmatory/forward 脚本，
  **未**观察 E3 outcome。
- `[I]` 本报告是研究证据；owner 未裁决前不构成方向变更。Option A′ 的任何落地都是**新预注册 + 新
  config + 新 ledger 行**，绝不静默修改 B/C/D/E1 或 Track B。

## 7. 引用

### 内部
- [`docs/track-b-preregistration.md`](../docs/track-b-preregistration.md) — Track B 冻结面（§2 S&P 500 only；§10.1 23 特征）。
- [`reports/2026-08-02-strategic-review-coverage-and-alignment.md`](2026-08-02-strategic-review-coverage-and-alignment.md) — 两失调 + 七主题覆盖。
- [`reports/design/2026-08-02-qlib-fork-vs-library-poc.md`](design/2026-08-02-qlib-fork-vs-library-poc.md) — 4 手术点 + RobustZScoreNorm 陷阱（本 POC 实证确认）。
- [`docs/market-driver-framework.md`](../docs/market-driver-framework.md) §2/§8 — regime/timing 作条件/情景层，"不作第二证伪锚"。
- [`docs/data-intake-rubric.md`](../docs/data-intake-rubric.md) — 7 gate（G3 no-revision；EPU 先例）。

### 外部
- `microsoft/qlib`（MIT）— `REG_CN/REG_US`、`LocalPITProvider`、`cn_index/collector.py`（CSI300/500）、`pit/collector.py`（baostock）。
- `pyqlib==0.9.7`（cp38…cp312 wheel）、`baostock==0.9.3`（期末键基本面 API）。

### POC 产物（scratch，仓库外）
- `/home/re/code/aionis-qlib-poc/step2_trap_test.py` — 合成陷阱测试（§2.3 数字来源）。
- `/home/re/code/aionis-qlib-poc/.venv311/` — 3.11 隔离 venv（pyqlib + baostock）。
