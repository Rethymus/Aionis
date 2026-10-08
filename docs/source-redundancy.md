# 数据源冗余映射与切换 Runbook（Source Redundancy Map）

> 状态：**v1.0 · 2026-10-08 · 审计轮 221 §C 失效预演第 3 项的对策兑现**（预演场景：
> 数据源单点断供——Tiingo/Alpaca key 过期或 API 破坏性变更）。本文逐源盘清**真实的**
> 备役现状（以内建代码路径为准，非愿望清单），给出断供剧本的切换动作，并对**无备役**
> 的源如实声明。与 `ops-local-refresh.md`（通道失败模式表）、`ops-offsite-backup.md`
> （数据史灾备）互为补充：那两份管"断供后怎么办"，本文管"哪里会断、断了切到哪"。

## 0. 代码级备役（已内建，无需人工）

| 链路 | 内建行为 | 代码位置 | 语义 |
|---|---|---|---|
| **美股价格** | Tiingo 主 → **Alpaca 自动补缺** → 仍缺则 fail-closed（点名 provider 与缺失符号） | `src/aionis/ingest/market.py::fetch_price_series` | 逐符号兜底；两源皆有 key 时单源断供**自动**消化 |
| **LLM 池** | priority 序 glm→siliconflow→modelscope，429/失败进 cooldown 自动切换；日配额跳过 | `src/aionis/extraction/llm_client.py::ProviderRouter` | 单 provider 断供自动降级；**模型退役**处置见 §3 剧本 E（轮 232 已实战一次） |
| **面板级韧性** | 任一 fetcher 软败=面板**诚实保留**旧数据（retain），staleness 绊网（周一 Issue）+ 快照审计（夜跑改史报警）双守卫 | 通道 STEPS（soft）+ `staleness-check.yml` + `data_snapshot_audit.py` | 断供不毁数据，只停新鲜度并**可见** |

## 1. 逐源备役清单

| 源 | 角色 | 失去即影响 | 备役 | 备役性质 |
|---|---|---|---|---|
| **Tiingo** | 美股日行情主源（研究+显示） | 价格全停 | **Alpaca**（内建） | ✅ 自动 |
| **Alpaca** | 价格兜底 + 成交量（`_volume_from_alpaca`，Track B） | 兜底失效+CN 成交量 | Tiingo（价格部分互为对向） | ✅ 价格自动；⚠️ 美股**成交量仅此一家** |
| **FRED API** | 显示宏观数据 + VIXCLS | 宏观面板/市场卡停更 | ALFRED 端点（`fetch_dff_vintages` 走 vintage 通道） | ⚠️ **同一机构双端点**——非独立冗余，Fed 全停则双断 |
| **SEC EDGAR** | 申报全家桶（13D/G·4·8-K·DEF14A·D·13F·IPO·流） | 申报面板全停 | 无（官方唯一源）；politeness+断点续跑把限流降为软败 | ❌ 无备役（可靠性历史高） |
| **GDELT** | 新闻情绪史（2017→，**不可重取**） | 新闻面板停更 | 无替代源；已实证其**间歇伺服缓存批次**（轮 211：fetch 后最新 seendate>2 天即 exit 3 STALE-SOURCE → 通道记软败 → 面板诚实 retain） | ❌ 无备役（有**检测**无替代） |
| **CFTC COT** | 持仓面板 | 周更停 | 无 | ❌ 无备役（源节奏慢=低风险） |
| **baostock** | A 股 CSI300 价格/成交量（Track B+E3 CN 腿） | **A 股全停+E3 CN 腿断** | 无内建；AKShare 等替代存在但**未接**（接入=新数据源走 7 门准入） | ❌ 无备役（E3 关键依赖，见 §4） |
| **Wikipedia** | CSI300 成分续造（E3 步 ⓪a） | 成分过期→E3 fail-closed | 对账门 ok:false 即中止（防错数据入面板） | ❌ 无备役（有守门） |
| **ARK / Reddit RSS** | 持仓/情绪面板 | 单面板停更 | 无 | ❌ 无备役（低风险） |
| **S&P PIT 宇宙** | 研究宇宙（MIT 重建仓库快照） | 宇宙冻结（研究历史不受影响） | 两份独立重建（hanshof / pierrebrunelle）已比对使用 | ✅ 双快照 |
| **LLM 池（3 provider）** | extraction/E2 假设生成 | 池降级到单家 | 内建 router 故障转移；**模型退役**按 §3-E | ✅ 自动+剧本 |

## 2. 断供剧本（Switch Runbook）

**A. Tiingo key 失效/配额尽**
症状：`tiingo_fetch_failed` 日志、market.py 自动落 Alpaca（研究不中断）；显示价格步骤软败。
动作：①`just check` 确认无红；②Tiingo 控制台查 key/配额；③仅当 Alpaca 也失效才停抓取——
价格面板 retain + 绊网可见，**绝不**临时接未过 7 门准入的第三源。

**B. FRED key 失效**
症状：宏观/VIX 步骤连软败；ALFRED vintage 通道同样失效（同 key）。动作：续 key（免费）；
期间面板诚实 retain。**Fed 双端点同停**视为机构级事件：停抓取、保缓存、记 blockers。

**C. GDELT 长期停供（>2 周）**
既有防线：轮 211 的 exit-3 检测+retain。动作：①确认非我方解析（直查 GDELT 简单查询）；
②新闻面板 as_of 冻结如实公示；③**历史不可重取**——这是 B2 异地备份（业主门 #1）覆盖
的最重要资产之一；④恢复后 fetch 自动增量续。

**D. EDGAR 限流/改版**
既有防线：≥2s 间隔+退避+断点续跑。改版破坏解析器：解析器修复=代码轮；期间该申报族
面板 retain。**不得**为抢数据降礼貌参数。

**E. LLM 模型退役（已实战：轮 232）**
症状：HTTP 400 `Model id …` 秒回。动作：①列现役 `GET /v1/models`（带 key）；②挑同档
继任（token 纪律：小激活参数优先）；③改 `providers.py` 目录项+注记退役原因与日期；
④单调用终验（JSON 模式往返）；⑤`pytest tests/test_reproducibility_capsule.py`（provider
按名引用，不受 model id 影响）。

**F. baostock 断供（E3 风险点）**
症状：CN 价格/成交量步软败 → E3 CN 腿材料化失败。动作：①E3 步 ⓪b 价格覆盖检查
residual gap 非空即**中止**（fail-closed 是设计，不补跑捏造）；②替代源（如 AKShare）
**须先过 7 门准入**（业主可见提案），不临时接；③10-31 证据包如实记 NOT-APPLICABLE。

## 3. 与守卫体系的联动

断供的第一道信号不是本文，而是：夜跑 SUMMARY 的 soft_fails → 夜报自动化 23:35 班 →
staleness 绊网 Issue → 月报五步。本文提供的是**确认断供后**的处置顺序与"哪些能切、
哪些只能 retain"的预期管理。

## 4. 诚实边界

1. "FRED↔ALFRED 双通道"**不是**独立冗余——同一机构两端点，本文如实降级标注（审计
   预演原文的措辞过于乐观）。
2. 真正无备役且**不可重取**的只有 GDELT 历史；EDGAR/baostock 无备役但数据理论可回补
   （EDGAR 全史公开；baostock 同）。
3. 接任何新备役源（AKShare、CBOE 直连等）= 新数据源 = **7 门准入 + 白名单**，
   不在断供现场临时决策——这是反泄漏纪律的一部分。
