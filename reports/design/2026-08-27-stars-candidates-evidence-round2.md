# TASK-DISP-S — 明星证据轮 2：UNVERIFIED 四人 + Southpoint 二壳（data.sec.gov 单源车道）

- **Lane**: 调查（只产证据，零生产改动；Researcher 边界——不改规格、不改代码、不做准入）
- **执行日期**: 2026-08-27
- **工作树**: `F:\ZCodeData\Aionis-wk`（branch `feat/stars-evidence-2` @ base `5475f6d`）
- **上游依据**: 任务书 `tasks/active/TASK-DISP-S-stars-evidence-2.md` + 轮 1 证据
  `reports/design/2026-08-26-stars-candidates-evidence.{md,json}`
- **机器可读版**: 同目录 `2026-08-27-stars-candidates-evidence-round2.json`
- **红线遵守**: 仅访问 `https://data.sec.gov`（一次主机例外也没有）；总请求 7/20；
  相邻请求间隔最小 2.65 s（≥2.5 s 铁律）；UA = 联系式
  `AionisResearch owner-reachable@example.com`（沿用仓内 `scripts/build_ticker_metadata.py`
  SEC_UA 约定与轮 1 修正后的格式）。efts/www.sec.gov 全程未触碰（另一 agent 并行车道的保留域）。

---

## (a) 请求账（逐条，含失败；时间均为 UTC）

| n | 时间戳 | URL（host=data.sec.gov） | 结果 | bytes | 与上一请求间隔 |
|---|---|---|---|---|---|
| 1 | 2026-08-27T10:41:21.749 | `/files/company_tickers.json` | 404 | — | — |
| 2 | 2026-08-27T10:41:41.418 | `/company_tickers.json` | 404 | — | 19.67s |
| 3 | 2026-08-27T10:42:17.641 | `/submissions/CIK0001319998.json` | 200 | 43,026 | 36.22s |
| 4 | 2026-08-27T10:42:20.291 | `/submissions/CIK0000819252.json` | 404 | — | 2.65s |
| 5 | 2026-08-27T10:42:57.182 | `/submissions/CIK0000860850.json` | 200 | 1,837 | 36.89s |
| 6 | 2026-08-27T10:42:59.832 | `/submissions/CIK0000881188.json` | 200 | 3,078 | 2.65s |
| 7 | 2026-08-27T10:43:56.578 | `/submissions/CIK0000916324.json` | 404 | — | 56.75s |

预算 7/20（远低于 20 上限，无重试发生，无超时/SSL 故障）。间隔按"上一请求发起时间→下一请求
发起时间"计，脚本强制 ≥2.6 s 下限（实测 2.65 s），满足铁律。

**结构性发现（记入方法边界）**: company_tickers.json 在 data.sec.gov 上**不存在**
（`/files/` 与根路径两个变体均 404；其权威副本在 www.sec.gov/files/，属本车道禁访主机）。
即本轮 lane 内**没有名称→CIK 发现手段**，定位只能依赖既有锚点探针。下文 Baron /
DoubleLine / Bessent 的 verdict 直接受此约束，如实呈现而非硬凑。

---

## (b) 五对象 verdict 总表

判定口径（沿任务书 §1）: 近 8 个报告季（2024-09-30 … 2026-06-30）内 13F-HR 出现情况
→ PASS（活跃连续）/ FAIL（停报/无 13F）/ STILL-UNVERIFIED（工具级证据不足）。Q2-2026 的
法定申报期限为 2026-08-14，早于执行日，故八季窗口已全部封闭，不存在"还没到申报期"歧义。

| # | 对象 | 定位壳/CIK | 近 8 季 13F-HR | verdict | 改变轮 1? |
|---|---|---|---|---|---|
| 1 | Icahn（Carl Icahn） | 未定位（本轮再排除 2 壳 + 证伪 2 个记忆假设号；累计 5 实体核毕均非载体） | N/A | **STILL-UNVERIFIED** | 结论不变；证据边界显著扩大 |
| 2 | Baron（Ron Baron） | 无法在 lane 内定位（无名称发现端点） | N/A | **STILL-UNVERIFIED** | 结论不变；阻塞原因从"预算耗尽"改为"车道限制" |
| 3 | Gundlach（DoubleLine） | 无法在 lane 内定位 | N/A | **STILL-UNVERIFIED** | 同上 |
| 4 | Bessent（Key Square） | 无法在 lane 内定位 | N/A | **STILL-UNVERIFIED** | 同上 |
| 5 | Southpoint 二壳 CIK 0001319998 | **Southpoint Capital Advisors LP**（DE）——即 Citrone 体系的真实 HR 载体 | **8/8 全部 13F-HR** | **PASS（壳级）→ 列为新 PASS 候选证据** | **是——轮 1 BORDERLINE 的前提被推翻** |

### 每对象证据链

**1) Icahn — STILL-UNVERIFIED**

本轮动作与结果（全部真实工具输出）:

| 探针 | CIK | 权威 entity name | 结果 |
|---|---|---|---|
| 轮 1 遗留命中 A | 0000860850 | `ICAHN HOLDING CORP/NY` | 排除：全史仅 5 行 = SC 13D ×2 + SC 13D/A ×3，任何年份 0 次 13F* |
| 轮 1 遗留命中 B | 0000881188 | `ICAHN & CO INC` | 排除：末次 13F 活动为 2003-09-30 的 13F-NT（2000 年曾有两季 HR 后转 NT 串至今约 23 年空窗） |
| 记忆假设① | 0000819252 | （404，无 EDGAR 档案） | 假设号证伪 |
| 记忆假设② | 0000916324 | （404，无 EDGAR 档案） | 假设号证伪 |

诚实声明: 两张 404 号码来自执行者记忆起点假设（非检索产物），用于消除错误路径并完整记账，
不作任何 CIK 断言来源。合并轮 1 已核实的 0000049578（经纪商壳）与 0000813762（IEP 上市合伙，
非 13F 主载体），Icahn 企业族累计五个实名实体 + 一个既存两壳命中全部验毕，**均非活跃 13F-HR
申报壳**。但在 data.sec.gov 单源车道内无法穷举族内其余候选壳（无名称发现端点），因此"存在某
个活跃载体"既未被证实也未被证伪 → 按纪律停在 STILL-UNVERIFIED（绝不猜 CIK 入档）。

**2) Baron（Ron Baron）— STILL-UNVERIFIED**

阻塞是结构性的: 本 lane 唯一的名称→CIK 手段（company_tickers.json）在允许主机上不存在
（见 (a) #1/#2），而 browse-edgar 类名称检索端点在被禁主机上。手中没有任何可辩护的 Baron
系起点 CIK，按"绝不猜 CIK"纪律不发起盲探。上下文注（一般知识，假设级，不影响判定）:
Baron 系以注册基金复合体为主，权益持仓披露走 §16/登记基金报告体系的可能性高——即便完成
取证，形态也未必是 13F-HR 连续串，PASS 概率偏低但未经实证不预设结论。

**3) Gundlach（DoubleLine）— STILL-UNVERIFIED**

同构阻塞: lane 内无名称发现手段，无可辩护起点 CIK，不猜号。上下文注（一般知识，假设级）:
固收为主的管理人通常不经 13F 报权益持仓（承轮 1 备注），PASS 先验概率低；实证留待 efts/www
车道恢复后处理。

**4) Bessent（Key Square Group）— STILL-UNVERIFIED**

同构阻塞。上下文注（一般知识，假设级，承轮 1）: Bessent 自 2025 年起任美国财政部长、外部
资管业务此前已收缩/清盘处置，方向上大概率 FAIL，但本轮无工具级证据，保持 UNVERIFIED，
不接受公开报道替代申报数据作判定输入。

**5) Southpoint 二壳 0001319998 — PASS（壳级）★ 本轮唯一实质裁定进展**

拉取成功且档案完整（recent 数组回溯至 2005-03-08 filed，窗口无截断风险）:

- 身份: `Southpoint Capital Advisors LP`（DE；entityType=other；与主壳
  0001378377 `Southpoint Capital Advisors LLC` 为同名分立法人——LP 变体；轮 1 已确认
  双壳同址同电话）。
- **近 8 季序列（8/8 连续，全部 13F-HR，代理 tag 0001012975）**:

| 报告季 | form | filed |
|---|---|---|
| 2024-09-30 | 13F-HR | 2024-11-14 |
| 2024-12-31 | 13F-HR | 2025-02-14 |
| 2025-03-31 | 13F-HR | 2025-05-15 |
| 2025-06-30 | 13F-HR | 2025-08-14 |
| 2025-09-30 | 13F-HR | 2025-11-14 |
| 2025-12-31 | 13F-HR | 2026-02-17 |
| 2026-03-31 | 13F-HR | 2026-05-15 |
| 2026-06-30 | 13F-HR | 2026-08-14 |

- 长程背景: 该壳自 2005-12-31 报告季起申报，within-window 累计 83 次 13F-HR +
  3 次 13F-HR/A（修订发生在 2006/2018/2021 各一次，不影响连续性），另有大量 SC 13G/G-A
  共同申报行——一个健康的长期存续申报壳。
- 一句话证据串: `data.sec.gov/submissions/CIK0001319998.json name="Southpoint Capital Advisors LP"; reportDate 2024-09-30..2026-06-30 各季度恰有 13F-HR（filed 2024-11-14/2025-02-14/2025-05-15/2025-08-14/2025-11-14/2026-02-17/2026-05-15/2026-08-14）; 窗口累计 HR=83。`

对轮 1 的修订: 轮 1 SOUTHPOINT=BORDERLINE 的两条理由分别是"主壳 LLC 近 ≥12 季纯 13F-NT"
和"第二壳核验被预算截断"。本轮证明**Citrone 体系的持仓信息一直由 LP 壳连续承载**（20 年不断），
NT-only 现象只属于 LLC 壳——第二壳并非空窗死壳，而是正确载体。"入册即空壳行"的担忧因此被
解除。verdict 由 BORDERLINE 升格为壳级 PASS。

---

## (c) 新 PASS 候选证据（只列证据，不做准入）

- 候选: **Southpoint Capital Advisors LP（Rob Citrone），CIK 0001319998**
  ——近 8 季 13F-HR 8/8 连续（最新 2026-06-30 / filed 2026-08-14），壳级判据完全满足。
- 明示不准入: 准入仍须走规格 §2-4 裁决。集成层至少要裁决三件事，均超出本 lane 职权:
  1. 双壳归属选择——注册字典应指向 LP 壳（HR 载体）、还是把两个 CIK 关联为同一管理人条目
     （LLC 只发 NT，面板管线只消费 HR，混用会产生空行或重复行）;
  2. 与现有在册 40 的去重语义（Citrone 目前不在册，无冲突，但要防未来双录）;
  3. zh_name/category 建议——本轮依轮 1 先例不对 BORDERLINE/升级项出中文名建议，维持轮 1
     "届时另行评估"的处理。
- 提醒: 若准入采纳，等于 net delta 再 +1（轮 1 的 +2 候选之上），同时 Pershing Q2 NT-only
  观察项仍构成潜在 -1 自然减员位（承轮 1 §e，状态未复核）。

## (d) 诚实边界

- Baron / DoubleLine / Key Square 三者本轮 zero 新工具证据——不是样本弱，是 lane 结构性
  无法触达（名称发现端点在禁访主机）。STILL-UNVERIFIED 为合法且诚实的落点；切勿事后把
  "没查到"误读成"查过没有"。
- Icahn 同理: 五实体排除 ≠ 族内无载体；"个人申报壳未定位"仍是唯一准确表述。
- company_tickers 两个 404 是端点存在性事实（非网络故障），已作为方法边界写进报告正文，
  不影响已获得结果的效力（submissions 端点在该主机上工作正常）。
- 纯调查声明: 本轮零 ledger/frozen/config/prereg/OOS 接触; 零生产代码/导出/前端改动;
  fetch 脚本留在系统临时目录（不入仓库）; commit 仅含本文件与配对 JSON。

### 交付物

1. 本文件: `reports/design/2026-08-27-stars-candidates-evidence-round2.md`
2. 机器可读版: `reports/design/2026-08-27-stars-candidates-evidence-round2.json`
3. 原子 commit（仅含上述两文件，不 push）
