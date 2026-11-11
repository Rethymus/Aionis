# 长周期维护工作流固化与残项清偿 — gen3 固化轮决策报告（2026-11-11）

本轮由动态工作流 **dwfrun-79aad24e**（长周期维护工作流固化与残项清偿）产出：主会话定夺清单四条，施工由派发链交施工员逐条执行，统一门禁由业主侧脚本执行（全绿后收尾推送）。本报告为该轮正式交付物与决策记录。**如实注记**：定夺清单漏列「写报告」条目，本报告由收尾会话按主会话裁决（选项 a）补写——内容全部取自本轮真实施工与实测，非事后修饰。

---

## 0. 主会话定夺清单（四条，全部落地）

| # | id | 内容 | 触碰面 | 量级 | 提交 |
|---|----|----|--------|------|------|
| 1 | refs-mention-propose | 夜报包 refs 月评摘要句补 `--propose` 旗标 | `scripts/ops_local_refresh.py:760-764` | S | `5a5486d9d7` |
| 2 | baseline-drift-note | 2430 基线漂移 append-only 注记 | `reports/audits/2026-11-11-env-testpipeline-round.md` 文末 | S | `d49e3a129e` |
| 3 | weixin-corrigendum | 微信文「正文不可读」append-only 勘误 | `reports/design/2026-11-11-super-agent-integration.md` §2 文章 4 后 | S | `b5ed3877ec` |
| 4 | cadence-wiring | 四档节奏接线：按名复跑 aionis-iterate 入册 | `docs/ops-local-refresh.md` 节奏表与行为准则节之间 | S | `0027f40c48` |

施工记录入册 `state/handoff.md` 轮 129-续~续4 + `state/current.md` 头部 active 条目（`b805643cc5`）。

## 1. 残项清偿表（三残项，核对员证据 + 施工会话实测）

| 残项 | 核对员证据 | 清偿落点 |
|------|-----------|---------|
| ①refs-mention-propose | `scripts/ops_local_refresh.py:760-764` 摘要句仅列 3 旗标；实读 `scripts/monthly_review.py:1255-1292` CLI 共 7 参数（--month/--out/--repo/--weekly/--propose/--lessons/--append-lessons-from），`--propose` 已落地未提 | 摘要句扩为四旗标（补「--propose 确定性提案（S/M/L 卡，零 LLM 零网络）」）；无测试钉该文本，lane 套件 43 全绿（exit 0）+ ruff 0 验证 |
| ②baseline-2430-timestamp | 轮 127 的 **2430/174 为决策时点基线**（提交 `15cfcba7f4`），当前实测漂移；`git diff 15cfcba7f4..HEAD` 双重核实 | env-testpipeline 报告文末追加「## 漂移注记（append-only）」：截至 `390d7d7002` 实测 **2482/176（+52/+2）**，构成=propose +20 / hygiene +23 / lane 40→43 / watchdog 23→25 / fastpath 17→21（+2 文件=两个新套件）；施工会话 `uv run pytest --collect-only -q tests/` 逐文件求和复测逐项吻合，`git diff 390d7d7002..HEAD -- tests/` 为空 |
| ③weixin-corrigendum | 首轮报告 §2 文章 4「partial/正文不可读」前提被两轮实测推翻（轮 127 curl HTTP 200/5.05MB+js_content×18+fox_fetch 全文；Gen-2 fox_fetch 全文含四机制） | 设计报告 §2 文章 4 条目后追加 append-only 勘误段（diff 16+0，原句 :80-82/:127-131/:229 保留）；施工会话**三读** fox_fetch 再次得全文，四机制逐一实证（Inline&Spill 含链式召回 / Thread 多对多订阅 / Fast Path-Slow Path 两级过滤与路由直通 / 投机执行）；结论影响=出处可验证性上调，首轮取舍（不引用）不变 |

## 2. 骨架固化：aionis-iterate 项目级保存工作流

三轮实战骨架（super-agent 整合两代 + 整备轮，均 2026-11-11）由主会话保存为项目级保存工作流 **`aionis-iterate`**（`.zcode/workflows/aionis-iterate.dwf.ts`，428 行，本轮实测在册）：

- **参数**：`mission`（必填，本轮主题）/ `deliverable_path`（可选，交付报告落盘路径，默认 `reports/audits/iterate-round.md`）——骨架 :10/:14 实测。
- **形状**（骨架头部声明实测）：并行采集（外向调研 ×1 + 向内核证 ×1）→ **定夺决策洞（需主会话在场）** → 施工 → 门禁（pytest/ruff 实跑+有界修复回环）→ 提交推送 → 独立复核（只审不改+有界回环）→ 报告交付。
- **whenToUse**（骨架自述实测）：`/goal` 继续/迭代/优化/深耕类指令、`--propose` 引擎产出待落地提案卡、值班发现需多轮施工的改进主题。
- 注：`.zcode/workflows/` 为 ZCode 工作区运行时文件，未随本轮 git 提交入册（是否入库属业主决策）；runbook 已载其路径为引用锚点。

## 3. 长周期复跑指引（四档节奏表接线）

「按名复跑」已由口头约定升为节奏表一等公民：`docs/ops-local-refresh.md`（四档节奏表与值班协议行为准则节之间）新增「**长周期迭代：按名复跑 aionis-iterate**」段——触发时机三条（`/goal` 继续类指令 / `--propose` 提案卡积压 / 值班发现多轮施工主题[thread:spin 同款信号]）+ 决策洞语义（裁量与验收需主会话在场，主会话内发起值守、不进夜间无人值守班次）+ 稳态 token（单次消耗大、按需触发不进固定班次，与「零新班次」不冲突）。

## 4. 施工记录（轮 129-续~续4，全部推送至 origin/main）

| 轮次 | 条目 | 提交 | 验证 |
|------|------|------|------|
| 129-续 | refs-mention-propose | `5a5486d9d7` | lane 套件 43 绿（exit 0）+ ruff 0；施工等晚间通道 19:35 `ok_committed`（`8605bd45b3`）后动 lane 脚本 |
| 129-续2 | baseline-drift-note | `d49e3a129e` | collect-only 复测逐项吻合（2482/176/五套件）；落地 diff 6+0 纯追加 |
| 129-续3 | weixin-corrigendum | `b5ed3877ec` | fox_fetch 三读全文+四机制实证；落地 diff 16+0 纯追加 |
| 129-续4 | cadence-wiring | `0027f40c48` | 骨架 :10/:14/:7 实证；落地 diff 12+0 纯插入 |
| 收尾 | state 入册 | `b805643cc5` | handoff 四行 + current active 条目；`git pull --rebase` up to date 后 push 一次成功（`8605bd45b3..b805643cc5`） |

统一门禁（全量 pytest+ruff）由业主侧脚本执行，全绿后收尾（收尾指令原文「门禁已全绿」）。

## 5. 待业主区（只列不动）

1. **GitHub billing 解锁（#2）**——恢复清单见 `docs/ops-local-refresh.md` billing playbook 节（2026-11-11 业主停用令小节 + re-enable checklist）。
2. **冻结通道真推许可**。
3. **`-wj` 账本孤儿 2 行裁决**。

（与 `reports/design/2026-11-11-super-agent-integration.md` §5 / env-testpipeline 报告 §3b 钥匙区一致，本轮零触碰。）

## 6. 红线遵守声明

本轮零触碰：`src/aionis/**`、`scripts/phase_*`、`runs/ledger.jsonl` 语义（0 ledger 写）、冻结配置（0 frozen）、OOS 管线（0 OOS）。零新增依赖/班次/常驻进程；`.zcode/` 未夹带入提交；append-only 勘误不回改任何原句；无占位 TODO/stub。
