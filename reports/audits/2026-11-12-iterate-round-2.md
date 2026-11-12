# 2026-11-12 iterate round 2 — 审计报告（aionis-iterate 长周期迭代轮交付物）

> 本报告为按名复跑 aionis-iterate 的长周期迭代轮 2（2026-11-12）交付载体：各施工
> 条目独立章节随落地逐节 append（append-only，勘误只追加）。本条目：
> `runbook-layering-citations-append`（定夺框架条 3 差量落点）。

## runbook-layering-citations-append（判别层/生成层小节补引，docs-only）

**条目语义**：分层小节本体已落地（commit db10a085a1，轮 130-续），本条目仅补
引用注记——③已落地只补引不重做。

### 落地内容

`docs/ops-local-refresh.md`「判别层/生成层分层」小节尾 append 一条 bullet
「引用锚与取向注记」（原行 286-303 逐字节未动，`git diff` 仅新增块）：

1. **RLCD 学术锚**：arXiv:2307.12950（Yang et al.，ICLR 2024），判别器反馈=
   改进信号——Jev 消歧报告（`reports/audits/2026-11-12-iterate-round.md` Jev
   章节同构点 2）的机器化依据；官方无公开代码 repo，仅文档引用。
2. **外部旁证**：Luo 2025（PMC12736879，Sensors）——确定性结构作 LLM 护栏
   （procedural guardrails）为既有模式，仅借模式、非同构证据。
3. **取向差异注记**：多数 2025 实践把 LLM 放快环（System 1 快环）+外部确定性
   控制当 System 2；Aionis 相反——判别=本地确定性规则引擎占值班环，生成=
   月末单场 LLM 会话（出环）；引用外部文献一律以本取向为准，勿按外部取向
   倒读本分层。

### 引用核验（施工会话实抓，2026-11-12）

- **arXiv:2307.12950**：实抓 `https://arxiv.org/abs/2307.12950`，标题
  「RLCD: Reinforcement Learning from Contrastive Distillation for Language
  Model Alignment」，作者 Kevin Yang, Dan Klein, Asli Celikyilmaz, Nanyun Peng,
  Yuandong Tian，ICLR 2024；摘要证实偏好模型（判别器）训练→经 RL 改进基座
  LLM——「判别器反馈=改进信号」机制成立。
- **PMC12736879**：实抓 PMC 页 + Europe PMC REST API
  （`PMCID:PMC12736879&resultType=core`），标题「Sensing User Intent: An
  LLM-Powered Agent for On-the-Fly Personalized Virtual Space Construction
  from UAV Sensor Data」，Sensors（Basel）2025（DOI 10.3390/s25247610），
  正文证实「a deterministic Finite State Machine (FSM) to enforce procedural
  guardrails」——「确定性结构作 LLM 护栏」旁证成立。
- **对条目素材的两处勘误（如实记录）**：
  1. 素材称「Luo et al. 2025」——Europe PMC 作者表实测 **n_authors=1**
     （Sanbi Luo，firstPub 2025-12-15），系**独著**；runbook 按「Luo 2025
     （独著）」落笔，避免独著挂 et al.。
  2. 素材称「多数 2025 实践把 LLM 当 System1 快环+外部控制当 System2」——该
     表述成立（神经快环/符号慢裁决的实践取向），但**旁证文献本身**按 Kahneman
     快慢轴取 FSM=System 1 / LLM=System 2，与本节命名**同向**；真实取向差异在
     **环位**：其 LLM 在交互环内作复杂意图推理，Aionis 的 LLM 完全出值班环
     （月末单场）。runbook 注记把此差别写入（防引用注记自身成为误引陷阱）。

### 边界（条目不做清单，逐条未做）

- 未重写小节、未回改原行（原 286-303 行字节未动）。
- 未做任何 RL/训练环节、未引入外部判别 API（仍守 provider 红线与本地判别层）。
- 未触碰 `state/`（轮次入册由 Orchestrator 按轮次账本流程处理）；未提交
  commit（统一门禁后由轮次流程统一处置）。

### 通道状态

- 动工前 `uv run python scripts/ops_local_refresh.py --status`：`ok_committed`
  （2026-11-11T19:35:04 完成），未在运行——符合动工前置条件。
- docs-only 条目，无代码改动，无单测适用项。

## backlog-reading-indices-append（阅读索引+同批指认，state/backlog.md）

**落地内容**（append-only，git diff 仅新增块）：backlog 名词指认区追加 ①两条
CC0-1.0 阅读索引（awesome-system-one / awesome-jev，注明「仅索引不装条目」，
license allowlist ACCEPTED 表在册）；②Jeva null-aware 延伸研读（arXiv
2610.18773 + typesafe-sdk MIT 只读不引——接入仍违 provider 红线）；③
Microsoft-Decision-1 实体指认（2026-10-09 官方发布，与 JEPA 无关同 Jev 防混读；
其 Foundry API 不采）。同时把 :697→:698 行号勘误以 append-only 注记补入。

## line-ref-erratum-append（轮 1 报告行号勘误）

**落地内容**：reports/audits/2026-11-12-iterate-round.md :14 邻域 append-only
勘误段——`monthly_review.py:697` 行号过时，def 实读 :698（原句保留）。

## bounded-question-prob-contract（{answer, p} 契约，round 131 代码面）

**⚠ 复活链抢救注记（如实）**：本条目与下一条目由原施工员链执行时，三次在
同一点遭遇 `Subagent turn failed: Model creation failed`（dwfrun-473d08ee →
resume → dwfrun-7a642a78 amend 复活，均死于第 4 条施工的 ask；同期迭代轮 3
运行正常，病灶特定于该链的会话恢复）。按业主「不盲目重试」纪律，剩余工作由
主会话内联完成，独立复核由单会话复核员补位。

**落地内容**（scripts/monthly_review.py，主会话实施）：
1. `WATCHDOG_BOUNDED_QUESTION` 升级——回答格式钉为单行 JSON
   `{"answer": true|false|短枚举, "p": 0..1}`（Jev/System One 校准概率协议的
   运维层同构）；契约句内联「p 仅记录轨迹、禁统计显著性声称、禁再校准拟合」。
2. 新 `parse_bounded_answer(text)`——纯解析零 LLM：取首个含双键的 JSON 对象；
   p 非数值/出 [0,1] 域分别记 `p-not-numeric`/`p-out-of-range`，无 JSON 记
   `format-miss`，原文前 120 字节保留在案——不补猜、不发明。
3. `render_reflexion_section` 补一行格式指引（不合法回答判 format-miss 原文
   保留）。

## brier-prediction-reconciliation（Brier 式预测对账，round 131 代码面）

**落地内容**（scripts/monthly_review.py，主会话实施）：
1. `render_card` 新增 prediction 槽：`{claim, due_month, p?}`——**p 默认
   「待月末会话填写」**，确定性引擎绝不代填概率（诚实边界原文照守）；槽内
   铭刻对账记法 `→ outcome: y=0|1 (YYYY-MM-DD)`。
2. 新 `reconcile_predictions(backlog_text, now_month)`——RLCD「预测误差=改进
   信号」的机器可核对版：resolved（p 已填+outcome 已记）算 (p−y)² 与方向
   命中；pending（due 已过无 outcome）与未填 p 如实分列；内联算术零依赖
   （sklearn 未引入，单月样本禁统计拟合）。
3. `proposal_reconciliation` 接线——--weekly §4 同一只读扫描顺带产出预测
   对账行（`stats["prediction_records"]`）。

## routine-env-zero-error（例行环境/零报错核查，停用令口径）

- pytest 全量：EXIT=0（本会话两次复跑；Windows 重定向下无摘要尾行属已知，
  以退出码为权威判据）。
- ruff：`All checks passed!`（scripts/monthly_review.py +
  tests/test_monthly_review_propose.py + 全仓）。
- 新增测试 9 个：propose 套件 20→29（parse 契约 5：合法/首双键 JSON/
  format-miss 保留原文/p 越界/p 非数值 + 卡槽 2：默认未填省略/含记法 +
  对账 2：四态三分/空账本）——三 monthly 套件合跑 81 全绿。
- Actions 停用令合规与恢复清单：在册未动（docs/ops-local-refresh.md billing
  playbook 节）。

## 待业主区（只列不动）

billing 解锁（→恢复清单 enable ×6→首验）/ 冻结通道真推 / -wj 账本裁决 /
Track C d6_go。

## round2-lows 复核记（2026-11-12 轮 132 append-only 补记，上文零回改）

- **交办假设锚「reconcile_predictions 报告锚 :981-1042」——查无对应物（如实）**：
  本报告全篇 grep（`981|1042|:963|991|1024`）零行号命中；`reconcile_predictions`
  仅 :101 按函数名提及、无行号锚。原始指向无法从本报告定位，故不补映射、不虚构。
- **本报告自身行号引用复核（现仍准，无需勘误）**：①:15「原行 286-303」系历史
  字节域陈述——`git show df5416a893~1:docs/ops-local-refresh.md` 实测 :286=分层
  小节标题、:303=「不引入外部判别 API」bullet 尾，该域至今未移（本轮两处 append
  均在其后）；②:70/:74-75 `monthly_review.py:697→:698` 勘误锚仍准（位于本轮
  删除点 :978 之前，不受顺移影响）。
- **关联顺移注记（供引用他文者）**：轮 132 round2-lows 删除
  `monthly_review.py:978` `PREDICTION_LINE_RE` 死变量（删除前全仓 grep 单点命中
  定义自身、零消费方）后，该文件 :978 之后锚点统一 −3（例：`reconcile_predictions`
  def :981→:978、`WATCHDOG_BOUNDED_QUESTION` :1277→:1274、`parse_bounded_answer`
  :1286→:1283）。
