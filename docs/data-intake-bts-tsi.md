# 数据接入 7 门 — BTS 货运 TSI（freight_taco / /taco 页 FreightProxySection）

> **状态**：**v0.1 · 2026-08-23** · exploratory-only display module。
> **范围**：参照站 TACO 卫星数据（Trucking Activity Co. 商业卡车计数）废除豁免后的**公共域降级等价物**——美国交通统计局（BTS）运输服务指数（Freight TSI，月频）为主源 + FRED/BLS CES 卡车运输就业为辅助。所有数据源进 Aionis 前必须全部过 `docs/data-intake-rubric.md` 的 7 门。
> **引用**：同构先例 = `docs/data-intake-etf-holdings.md`（theme_etfs）、`src/aionis/ingest/vix.py`（FRED 适配器纪律）。
> **铁律 #0**：全程未请求 参照站 或任何竞品站；口径差异在面板 methodology 与降级口径卡中如实披露，**绝不冒充卫星数据**。

---

## 数据源概述（2026-08-23 实测验证）

| 角色 | 源 | 端点 | 实测状态 |
|------|----|------|----------|
| **主源** | BTS（美国交通统计局）第一方 Socrata 发行 | `https://data.bts.gov/resource/bw6n-ddqk.json?$select=obs_date,tsi_freight&$order=obs_date ASC` | ✓ 可用：318 行（2000-01 → 2026-06），最新 2026-06 = 134.9 |
| 辅助 | BLS CES 卡车运输就业（经 FRED `CES4348400001`） | FRED observations API（项目既有适配器） | ✓ 可用：439 行（1990-01 → 2026-07），最新 1465.1k |
| 已验证镜像（记录备查，未消费） | FRED `TSIFRGHT`（BTS TSI 的 FRED 转载） | FRED series API | ✓ 可用但**滞后 BTS 直连约 1 个月**（截至 2026-08-23 实时窗口只到 2026-05）——故取 BTS 直连为主源 |

**关键源考古发现（诚实记录）**：

1. **`www.bts.gov` 网页层被 Akamai 机器人门挡**（非浏览器客户端 HTTP 403，两次实测：TSI 页 + 旧 legacy `TSI-Data.txt` 直链均 403）——不可作为程序化通道。
2. **`data.bts.gov`（Socrata）是 BTS 的第一方程序化发行面**，开放访问（dataset `bw6n-ddqk`，attribution "Bureau of Transportation Statistics"）；FRED `TSIFRGHT` 的 notes 字段本身也指向该 dataset——两个独立通道交叉验证同一主源。
3. **FRED 铁路车皮装载量假设订正**：任务假设"旧 AAR 系列已停更"——实测**不成立**，`RAILFRTCARLOADS`（月频，AAR/BTS）在 FRED 活着（2000-01 → 2026-05）。BTS 数据集内同样含 `rail_frt_carloads` 月度列（至 2026-06）。未采用为本面板数据（五模式综合的 TSI 已覆盖铁路维度），但**如实记录其在场**。
4. **Cass Freight Index 等商业货运指标**：商业订阅数据，无许可路径，按 G1 剔除——与卫星 TACO 同类处理。

---

## G1 — License allowlist（许可协议白名单）

### 结论：✓ **PASS**

- **规则**：仅 MIT / Apache-2.0 / BSD / CC0 / CC-BY-4.0（数据）或等价开放数据。
- **BTS TSI**：美国联邦政府机构作品，**public domain**（17 U.S.C. §105）；BTS 数据政策明示可自由使用/再分发。API catalog 注册 license = `"U.S. Bureau of Transportation Statistics — public domain"`。
- **BLS CES（经 FRED）**：美国劳工统计局作品，public domain；FRED 条款为 permissive（项目既有使用先例：VIXCLS/CPI/DFF）。注册口径同上（源描述中注明 via FRED）。
- **边界（诚实）**：商业原版（Trucking Activity Co. 卫星计数、Cass）**不采用**——正是本面板存在的原因（无许可路径），在面板 `degradation.commercial_original` 字段如实留名。

---

## G2 — PIT / as-of 时点（point-in-time）

### 结论：✓ **PASS（display 语义）**

- **机制**：每行观测自带参考月（Socrata `obs_date` / FRED `date`）；面板 `as_of` = 最新 TSI 参考月（当前 2026-06）。
- **边界（诚实）**：这是 **display-only** 面板——不进研究管线，故不要求 ALFRED vintage 追踪。TSI 的发布滞后约 1 个月（月中发布上月前一个月的值），`data_health` 归类 `cadence`（随源节奏推进）。

---

## G3 — No-revision contract（无回改契约）

### 结论：⚠ **不适用（如实披露，非 PASS）**

- **事实**：与 VIXCLS 不同，**TSI 会回改**——季调修订（近月）+ 年度基准修订。本模块**不主张** no-revision 契约。
- **替代纪律**：面板永远显示当前发布版；methodology 字段明文 "the TSI IS revised … the panel shows the current published vintage"；缓存信封（`bts_tsi_freight.json`）带 `fetched_at` 时间戳，每次 fetch 是全量重取（非增量），快照可追溯。display-only 语境下回改不影响任何研究声明。
- **辅助序列**：BLS CES 同样有再基准修订（年度），同等披露。

---

## G4 — Reproducibility / snapshot discipline（可复现）

### 结论：✓ **PASS**

- **幂等缓存**：`data/cache/bts_tsi_freight.json`（原始信封：fetched_at/dataset/n_rows/rows）+ `data/cache/alfred_CES4348400001.json`（vix.py 同名约定）；缓存命中零 HTTP。
- **解析纯函数化**：`parse_tsi_rows` / `parse_fred_observations` 为纯函数（hermetic 可测）；fetcher（`scripts/bts_tsi_fetch.py`）与导出器（`export_freight_taco`）共用同一解析器——缓存与 JSON 不会出现行语义分歧。
- **契约测试**：`tests/test_web_terminal_data.py::test_freight_taco_panel_contract`（KPI↔序列对账：MoM 链/YoY 全部由面板自身数据重算钉死）+ `test_freight_taco_registered_in_catalog`（data_health + api_catalog 注册与 license 随行）。

---

## G5 — Exploratory-only 边界

### 结论：✓ **PASS**

- **display-only / exploratory**：仅进终端 `/taco` 页 FreightProxySection 与静态数据 API（`freight_taco.json`）。
- **绝不进研究管线**（features/eval/ingest of research data/OOS）；无 frozen claim 依赖此数据。月度指数绝不 PIT 对齐、绝不作信号。
- 与 ARK/theme_etfs 同级：display lane 模块级纪律写进 `bts_tsi.py` docstring。

---

## G6 — Selection honesty（选择诚实）

### 结论：✓ **PASS（缺口如实记录）**

- **主源选择**：BTS 直连（data.bts.gov）优先于 FRED 转载（TSIFRGHT）——第一方 + 更新鲜（领先 1 个月）。两者为同一 BTS 指数，非"挑好数字"。
- **口径降级披露（本面板的核心诚实义务）**：
  - 原 TACO = 卫星卡车计数（商业、高频、车队粒度）；
  - 等价物 = 月度综合指数（卡车为五种货运模式之一：卡运/铁路/水运/管道/空运）；
  - 面板 `degradation.granularity_lost` 字段逐字披露粒度损失；amber 降级口径卡（/taco 页）+ methodology 双语明示 "NOT satellite data"。
- **辅助序列选择**：`CES4348400001`（卡车运输就业，NAICS 484）是 FRED 上最贴 TACO 卡车主题的公共域序列；辅助缺席时 `truck_employment: null`（诚实空，不伪造）。
- **剔除记录**：Cass Freight Index（商业订阅，G1 剔除）；卫星卡车计数本身（无许可路径，即本面板替代对象）。

---

## G7 — Politeness / rate limit（礼貌抓取）

### 结论：✓ **PASS**

- **稳态请求账**：每 fetch run 共 **2 GET**（data.bts.gov ×1 全量历史 318 行——无分页无逐月请求；api.stlouisfed.org ×1），两主机间 ≥2.1s 显式 sleep；主机内串行由 `HttpRequestPolicy.HostSpacingPolicy(min_interval=2.0)` 强制。缓存命中零请求。
- **有界重试**：共享 FRED/Socrata 适配器（`universe._policy_get`）；UA 带 Aionis-Research 联系方式。
- **源考古请求账（2026-08-23，一次性）**：www.bts.gov 2（均 403 Akamai，即上文发现 1）；data.bts.gov 6（resource 探测 ×4 + dataset 元数据 ×1 + 列验证 ×1）；api.stlouisfed.org 5（TSIFRGHT 元数据 ×1 + 就业序列搜索 ×3 + 铁路停更假设验证 ×1）。全部带间隔。

---

## 结论

**6/7 PASS + G3 如实披露为"不适用"（TSI 可回改，无 no-revision 契约主张；display-only 语境以"永远显示当前发布版 + fetched_at 快照"纪律替代）** — 准入为 **display-only / exploratory**。违反任一门（如把该数据接入研究管线、或把降级口径卡从面板移除而不更新本文档）即失效。
