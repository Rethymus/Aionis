# 设计报告：个人训练法（校准飞轮三环）与渐进自治梯 —— 定夺轮定案稿

- **日期**：2026-11-14。**角色**：方案综合决策员（iterate 轮 9 候选清单的定夺交付物）。
- **证据**：外向调研 7 条采纳 + 5 条拒绝（全量见任务书）；向内核证 24 命令全绿基线；本会话决策员亲手复核锚点（见附录 A）。
- **状态**：**定案稿（施工前）**。施工后由施工员在附录 B「as-built 勘误区」追加实测行号与漂移记录，本文正文不回改（append-only 纪律）。
- **性质**：纯运维面设计。0 ledger 写 / 0 frozen config / 0 OOS / 研究管线零改动——本报告本身即本轮红线承诺的载体。

---

## 0. 执行摘要

三主线的基础设施比主题预设更齐备（内证 verdict）：逐条 Brier 对账（`reconcile_predictions`）、bounded `{answer,p}` 协议+四态解析、lessons 四件套（契约门/四操作/聚合视图）、`--propose` 七卡、attempt-cap/三分类分诊/backup 回滚构件全部在位且实测绿。真正的空白恰是三件，全部可施工：

1. **分桶聚合统计不存在**（`reconcile_predictions` 只逐条对账）→ 训练法环 1a「校准聚合器」；
2. **L0-L3 自治梯未入册**（全仓 grep 零命中，但构件齐备只需引用）→ B 线「渐进自治梯」runbook 节；
3. **ExpeL / verbalized-confidence 文献全仓 grep 零命中** → 本报告补齐文献锚（不再单独开 backlog 索引条目，锚集中在本文与 runbook 节内）。

本轮五条目（docs 先 code 后）：本报告 → 自治梯 runbook 入册 → 校准聚合器 → 校准反馈注入 → insight 钩子。

---

## 1. 红线（全部条目共同约束，违者即废）

以下每条均本会话亲手复核或在任务书两路证据中确证：

1. **研究管线零改动**：`src/aionis/`、`scripts/phase_*`、`runs/ledger.jsonl`（71 行，末行 2026-10-09 forward_prediction_committed）零触碰（内证 `git log` 核实零近期改动）。
2. **训练 = 提示词/经验级条件化**：GLM 池内（GLM/SiliconFlow/ModelScope only，AGENTS.md provider 约束；`.env` key 名集合内证复核无违池残留），零微调、零 SDK、零外部 API。一切 SFT/RLHF/GRPO/CalibSFT 式改权重 = 拒绝面（§7）。
3. **阈值与处置语义永不出现在 LLM prompt**：三带先例 `scripts/monthly_review.py:993-1001`（docstring 原文 "Three-band threshold semantics live HERE in the code rule gate, NEVER in any LLM prompt"——本会话 Read :975-1049 全文复核）。校准反馈注入文本只含事实统计。
4. **p 永远由月末会话自行 verbalize**：judgments/facts 分账 `monthly_review.py:988-992`；引擎绝不代填、绝不重标、绝不「自动调 p」。insight 片段同受此约束。
5. **呈现 ≠ 校准**：聚合器定位为**记录性分桶命中呈现**——不调整 p、不建议阈值、不做拟合、不做统计显著性声称。锚：#15 口径（backlog:210 延伸索引⑤ RouteLLM「n=1 月度样本禁阈值拟合」；backlog :50-58 窗口「月度小样本对账仅记录性校准，禁任何统计显著性声称」）；runbook 已拒 `sklearn CalibrationDisplay`（分箱校准语义与月度 p 轨迹错位，本会话 sed 380-390 窗口亲读）；runbook「lessons 首跑预演注记」诚实边界条（arXiv:2611.11480 过自信实证 → 仅记录轨迹，**首跑勿因 p 偏高偏低临时引入校准**——本会话 sed 400-435 窗口亲读）。
6. **首月 = 基线采集期**：`grep -c "prediction:" state/backlog.md` = 0、`grep -c "outcome:"` = 0（本会话亲手复核双零；runbook 首跑预演注记 (a) 同口径：预测接线 2026-11-12 起、首批 due 2026-11 月末）。空账本 = 诚实 `none yet (baseline collection month)`，**不造基线、不造示例数据入真实文件**（mock 仅限测试 fixture，AGENTS.md）。晋级门槛只入册「形」（§3），数值待基线数据后由业主定标。
7. **L2 三互锁 + 先入册后启用**：attempt-cap（runbook:89 `SKIP:attempt-cap` 3 次锁死、:646 一带 push 失败锁定+恢复路径——本会话 grep/sed 亲核）+ 审计轨迹 + 一键回滚（backup ok / push_only_recovery / retry_soft，本会话 `--status` 实测在位）；晋级门槛量化**先入册后启用**。
8. **token 红线**：LLM 调用面维持两班不变（runbook:234「23:35 夜报单会话 + 月末复盘会话」）；月度面唯一 LLM 面 = 月末单场复盘会话（runbook 调用面表，:340-346 窗口亲读）。一切新环节 rides 既有单场，**零新增会话/进程/依赖**。
9. **零新依赖**：分桶 Wilson CI 用在册 statsmodels `proportion_confint`（本会话项目环境实跑：3/5 → (0.2307, 0.8824)，1/1 → (0.2065, 1.0)）。

---

## 2. 个人训练法（A 线）：RLCD → 三环飞轮

总图：RLCD（arXiv:2307.12950，runbook:304-305 已入册「判别器反馈即改进信号」）在个人运维域的落地形态 = 三环飞轮：**聚合（地基）→ 注入（反馈）→ 蒸馏（经验）**。零梯度、零微调，全部 rides 既有月末单场会话与确定性代码面。

### 环 1a：calibration-aggregator（地基，代码，本轮施工）

- **落点**：`scripts/monthly_review.py`，`reconcile_predictions`（:978-1039）旁。
- **实现要点**：
  - 抽出共析核 `_collect_prediction_records(backlog_text)`（现 :1006-1019 的解析循环原样上提），`reconcile_predictions` 渲染输出**保持逐字节不变**（既有测试钉 + 新增「refactor 前后输出不变」钉）；
  - 新增纯函数 `calibration_bucket_summary(records)`：p 分桶 `[0.5,0.6)/[0.6,0.7)/[0.7,0.8)/[0.8,0.9)/[0.9,1.0]` → 每桶 n / 命中数 / 命中率 + **Wilson 95% CI**（`statsmodels.stats.proportion.proportion_confint(method="wilson")`）+ **汇总 mean Brier**（与 :1034 逐条 `(p−y)²` 同口径取均值）；
  - p<0.5、p 缺失、pending 未对账行**如实分列不计桶**（诚实缺省，不混入命中率）；桶界 = 固定呈现常量（沿 :998-1001 "Band cuts are FIXED presentation constants" 先例）。
- **反聚集呈现**（arXiv:2609.32470 警示落地）：每桶附 p 原值种类计数（例「p=0.8 出现 4 次，占该桶 2/3」）——防把 verbalized 置先验聚集误读为校准良好；**不重标 p**（重标仅呈现侧永远禁止，judgments/facts 红线）。
- **空态**：0 条 resolved → 单行 `none yet (baseline collection month)`，不输出空桶表格。
- **测试钉**（`tests/test_monthly_review.py` 同套件，hermetic fixture）：空账本空态、1/1 宽 CI（数值断言 (0.2065, 1.0)——即「小样本禁拟合」的量化体现）、桶边界归属（0.6 ∈ [0.6,0.7)）、汇总 Brier = 逐条均值、reconcile 渲染逐字节不变。
- **文献锚**：arXiv:2305.14975（EMNLP 2023，Just Ask for Calibration）——RLHF-LM 的 verbalized confidence 通常比 conditional probabilities/logprob 校准更好（ECE 相对降约 50%）→ 既有 `prediction（p=…）` verbalized 路线**确证为正确选型**；宽 Wilson CI = 首月小样本禁阈值拟合的量化依据。**不取 GLM logprob 当置信度**（本文结论即更差，且池内 provider logprob 支持不一——backlog 延伸索引④ 限定同向）。
- **注记（防混引）**：任务书所指 RLVP 原文多路检索未定位唯一 arXiv 条目；命中的 arXiv:2607.07435 系 RL 优化器同名缩写、非校准文献，**不混引**——该脉络由 2305.14975 + 2511.14275 + 2610.18614 等效文献群覆盖。

### 环 1b：calibration-feedback-injection（注入，代码，本轮施工）

- **落点**：`lesson_seeds`（:1309-1325，确定性事实收集）加 `calibration_feedback` 键（**数据源 = 环 1a 聚合器输出**）→ `render_reflexion_section`（:1328-1346）新增一节「校准事实（呈现≠校准）」。
- **语义边界**：只注入确定性事实统计，例：「你的 p∈[0.7,0.8) 历史命中 3/5，Wilson 95% CI [0.23,0.88]——CI 宽即小样本，禁据此调 p 或定阈值」。后半句是**禁令重申**（红线 3/4/5 的呈现），不是阈值/处置建议；一切处置语义留在代码侧。
- **空态**：首月渲染 `none yet (baseline collection month)`，不造基线。
- **边界**：不加新 CLI 旗标（rides `--lessons` 既有渲染链）；零 LLM、零网络。
- **测试**：空态渲染、有数据渲染、注入文本无祈使式处置语义（负向断言：不含「调 p 至 / 建议阈值取 X」类字样；禁令重申行按固定字面钉）。

### 环 2：expel-insight-hook（蒸馏，代码，本轮施工）

- **文献锚**：arXiv:2308.10144（ExpeL，AAAI 2024；repo github.com/Andrewzh112/ExpeL Apache-2.0，调研 gh api 实跑核实）——零梯度「经验蒸馏」原典，证明**不改权重的经验级训练**有文献正源。**不引入**其 Faiss 向量检索与环境训练代码；注入面用确定性文本索引。
- **机制**：`--lessons` 输出新增**有界一行提示**（Reflexion §5 seeds 区）：「月末会话请从本月 resolved 对账行 + active lessons 聚合抽 0-2 条 IF-THEN policy 片段（经 `--append-lessons-from` 写回）；片段禁含『自动调 p』指令」。
- **输入面已在位**：reconcile resolved 行（:1036-1038 渲染形态）+ `active_lessons_view`（:1163）聚合。
- **产出通道已在位**：`--append-lessons-from`（:1209 `append_lessons` 计划形契约 + exit 3 契约门 + EVENT_OP_RE 四操作 ADD/UPDATE/DELETE/NONE）。零新增班次，rides 月末单场复盘会话。
- **示例片段（模板口径，表达纪律而非调 p）**：「IF 高带预测（p>0.8 表达）THEN 须附可证伪依据（历史命中 2/6 事实引用）」。
- **测试**：提示行渲染存在、空态降级（无 resolved 行 → 「本月无 resolved 对账行，insight 步跳过」）、提示行含禁令字面。

### 环 3（远期索引，本轮不施工——防止漏判与再议）

- **verbalized 概率分布**（arXiv:2511.14275，prompting-only 部分）：下月预测模板分布化——每 claim 要求 p(发生)+p(不发生) 成对表达或归一化分布；`parse_bounded_answer`（:1283）加 `p-not-normalized` 校验态；与 few-shot 校准条件化（注入历史同类 claim 的 (p,y) 对账行）组合。**排 ExpeL 环节之后另轮施工**；RL 优化臂 = 拒绝面。
- **Agent Workflow Memory**（arXiv:2409.07429，repo Apache-2.0）：runbook 记忆化远期参考（从多次成功的软败恢复序列抽「重试升级顺序」候选供 L2 引用）——L1→L2 之间，本轮仅此索引。
- **SelfCheckGPT 采样一致性**：rejected（k 倍 token 违单场预算红线）；仅业主显式扩预算时重议。

---

## 3. 渐进自治梯（B 线）：runbook 入册全文蓝本

> 本节即 `automation-ladder-runbook` 条目的入册内容蓝本；施工员据此落 `docs/ops-local-refresh.md` 新节「渐进自治梯」（引用既有锚，不重复展开）。

### 3.1 分级表

| 级 | 定义 | 状态 | 判据/互锁 |
|---|---|---|---|
| **L0 呈现** | 确定性信息呈现：夜报包、`--status`、`--doctor`、runbook 注记。零动作 | 在位 | 无（纯只读） |
| **L1 自动候选** | 引擎只建议、人裁决：`--propose` 七卡（零 LLM 零网络、引擎对 backlog/tasks 只读、「绝不自动写」声明）+ `--triage` 三分类分诊（ops_local_refresh.py 纯规则：platform-failure/infra-transient/code-defect） | **现状（在位）** | 只读 + 人工采纳门 |
| **L2 校准达标后·可逆运维决策自动执行** | 合格面三件：软败重试升级（retry_soft 先例）/ 分诊带动作（triage 结论→预设处置映射）/ propose 自动派发候选（disposition 行→orchestrate_dispatch 派发路径） | **未启用（先入册后启用）** | 三互锁（3.3）+ 量化门槛（3.4）+ 业主扳键 |
| **L3 业主定义** | 待定义 | 未定义 | 待业主区 |

### 3.2 合格决策面与永不合格面

**L2 合格面**（统一四判据：可逆 + 低害 + 有审计轨迹 + 一键回滚）：
1. 软败重试升级（`retry_soft` 既有先例）；
2. 分诊带动作（`--triage` 结论映射到预设处置，处置集封闭枚举）；
3. propose 自动派发候选（卡片 disposition 行的派发路径自动化，仍不写 backlog/tasks 本体）。

**永不合格面**（无论校准几级达标，永不自动执行；同构 OpenAI Operator System Card 的 ask-for-consent 硬类别 + 证券买卖 fully restrict——「分级表必须有硬禁区」的外部工程佐证）：
1. **研究管线**（`src/aionis/`、`scripts/phase_*`、dashboard 研究面）；
2. **`runs/ledger.jsonl` 写入与一切 frozen config 变更**（config_committed BEFORE result 红线，AGENTS.md）；
3. **业主钥匙面**（`.env`、billing、推送凭证）；
4. **交易执行/下单**——Aionis 阶梯**永不含**（量化项目特有条款）。

边界纪律：「运维面低风险」**不得滑坡成研究面豁免**——Operator 完全禁止面证明分级表不允许全局放开。

### 3.3 L2 三互锁（缺一即不许启用）

1. **attempt-cap**：3 次失败锁死等次日或人工（runbook:89 `SKIP:attempt-cap`、:646 一带 push 失败锁定+恢复路径先例）；
2. **审计轨迹**：每次自动执行写 handoff 审计行（触发信号 / 所执行动作 / 回滚点三要素）；
3. **一键回滚**：backup ok + `push_only_recovery`（`--status` 实测在位）；revert 路径随入册写死。

### 3.4 晋级门槛（形先入册，数值待基线后业主定标）

L1→L2 需**同时**满足（X/N/Y/M 数值待首月基线数据后由业主入册——当前 resolved 对账记录 = 0 条，如实注记，**不凭空造阈值**）：

- a) 汇总 mean Brier < X，连续 M 个月；
- b) resolved 对账记录累计 n ≥ N；
- c) 各桶 Wilson 95% CI 上界 < Y（样本量足以让 CI 收窄到可用）；
- d) 期间零 insight 违例（无「自动调 p」类指令混入 lessons）；
- e) **业主显式扳键**（待业主区：L2 启用钥匙）。

**口径同构锚**：arXiv:2610.18614——晋级看「对月末**结局**校准的置信」（Brier 分桶 + 样本量门槛），不看单条建议自评；trust/abstain/handoff 三态 ≈ 自动执行 / 跳过待人工 / 上抛业主（只借评价口径，不借其 per-step 实施粒度——Aionis 是月度粒度）。

### 3.5 工程同构三原则（Anthropic「Building effective agents」2024-12 原文口径）

1. **最简起步、按需增复杂度**（"find the simplest solution possible, and only increase complexity when needed"）→ L0 起步、逐级晋级不跳级；
2. **checkpoint + stopping conditions**（"pause for human feedback at checkpoints … maximum number of iterations to maintain control"）→ L2 attempt-cap + 人工 checkpoint 互锁的直接工程先例；
3. **evaluator-optimizer**（每步拿环境 ground truth 反馈再迭代）→ 校准飞轮结构同构。

**边界**：不因此引入 Claude Agent SDK / MCP / 任何框架组件（provider 红线 + 零新依赖）；引用锚定 2024-12 原文（页面 2026-05 已加注指向 Managed Agents）。

---

## 4. 首月基线采集期声明（2026-11 = 基线月）

- `prediction:` 记录 0 条 / `outcome:` 记录 0 条（本会话 `grep -c` 亲手复核双零；runbook 首跑预演注记 (a) 同口径）。
- 聚合器 / 注入 / insight 三件**首跑全部空态 = 预期，不是缺陷**；不造基线、不造示例数据入真实文件（mock 仅限 hermetic 测试 fixture）。
- 首批 (p,y) 对账行将在 2026-11 月末会话后首次出现——那之后聚合器才有第一行真实输出；在此之前一切输出为 `none yet (baseline collection month)`。
- **晋级门槛数值在基线数据存在前不入册**（只入册 §3.4 之形），避免凭空造阈值（RouteLLM n=1 禁拟合锚，backlog:210）。
- 反乐观预期入册（arXiv:2609.32470）：off-the-shelf 大模型 verbalized 置信系统性聚集于少数高值（过自信）——首月读数若呈聚集，按预期解读，勿解读为「校准良好」或「需要立即干预」。

---

## 5. 待业主区（只列不动）

1. **L2 启用钥匙**：§3.4 门槛数值定标（X/N/Y/M）+ 扳键时点。
2. **L3 定义权**：L3 归业主定义，本设计不预填。
3. **billing 解锁**（doctor L7 根因、Actions 恢复）——既有在册项（state/current.md 待业主区）。
4. **ZCode 工作区月末提示词模板 {answer,p} 同步确认**（iterate 轮 7 星报 a，仍待）。
5. **装包/接入裁决类**（johantor-brain 已判与「无后台长驻」红线结构性冲突永不引入；jgrep 维持原判）——既有在册项。

---

## 6. 实施顺序（本轮五条目，docs 先 code 后）

1. `design-report`（本文；决策员已落盘，施工员收官时补附录 B as-built）；
2. `automation-ladder-runbook`（§3 蓝本落 runbook）；
3. `calibration-aggregator`（环 1a）；
4. `calibration-feedback-injection`（环 1b，数据源=环 1a，**同文件同 PR 面可并施工**）；
5. `expel-insight-hook`（环 2，依赖环 1a 的 records 面）。

**今晚通道条款**：决策时点（2026-11-14 白天）`--status` = ok_committed（95a841a9e3，2026-11-13T19:26 收工，11-14 晚间通道未点火=非 running）；施工员动 code 前复跑 `--status`，若 running 则 3/4/5 后置，docs 条目照常。

**收官门禁**（动 code 时）：`uv run ruff check` 净 + monthly 三套件 pytest 全绿 + `--lessons`/`--propose` 实弹 exit 0 + `grep -c "prediction:" state/backlog.md` 复核计数不变（0，除非月末会话已真实写入）。

---

## 7. 拒绝面（研究判据，防再议）

- **一切改权重训练**：CalibSFT（2609.32470 方法体）、GRPO-RL（2610.18614 方法体）、2511.14275 RL 臂、任何 SFT/RLHF 式概率训练——违「零微调」红线。
- **GLM logprob 当置信度**：2305.14975 结论 verbalized 更好 + 池内 provider logprob 支持不一。
- **typesafe-sdk / Jev API 接入**：provider 红线（池仅 GLM/SiliconFlow/ModelScope）+ 业主明言「不需要跑 Jev」。
- **SelfCheckGPT 近期引入**：k 倍 token 违单场预算红线；业主显式扩预算时重议。
- **DirEAG（2608.20717）**：面向数学推理的多步证据后处理，月度二元预测分桶用不上 = 过度工程。
- **新装第三方校准库（netcal 等）**：零新依赖；statsmodels `proportion_confint` 已覆盖（本会话实跑验证）。
- **RLVP 混引**：未定位唯一校准文献条目；arXiv:2607.07435 系同名缩写的 RL 优化器，不混引（§2 环 1a 注记）。

---

## 附录 A：本会话（决策员）亲手复核清单

| 检查 | 命令/动作 | 结果 |
|---|---|---|
| monthly_review.py 锚 | `grep -n`（reconcile/parse_bounded_answer/lesson_seeds/render_reflexion_section/active_lessons_view/append_lessons/WATCHDOG/八旗标） | reconcile :978、active_lessons_view :1163、append_lessons :1209、WATCHDOG :1274、parse_bounded_answer :1283、lesson_seeds :1309、render_reflexion_section :1328、旗标 :1425-1463，全中 |
| reconcile 全文 | Read :975-1049 | judgments/facts :988-992、三带 NEVER-in-prompt :993-1001、逐条 (p−y)² :1034、解析循环 :1006-1019、返回渲染行列表（records 为局部量→聚合器需共析核） |
| statsmodels Wilson | `uv run python -c "from statsmodels.stats.proportion import proportion_confint; …"` | 3/5 → (0.2307, 0.8824)；1/1 → (0.2065, 1.0)（与内证一致，第一手） |
| backlog 数据面 | `grep -c "prediction:"` / `grep -c "outcome:" state/backlog.md` | 0 / 0 |
| runbook 红线节 | sed 340-346 / 380-390 / 400-412 / 425-435 / 85-92 / 644-650 + grep | 调用面表（唯一 LLM 面=月末单场）、CalibrationDisplay 拒绝、首跑预演注记 (a)(b)+诚实边界（首跑勿临时引入校准）、:89 attempt-cap、:646 一带 push 锁定、RLCD :304-305、节奏表 :230/:234 两班不变 |
| RouteLLM 锚 | `grep -n "RouteLLM" state/backlog.md` | 延伸索引⑤ 在 :210（内证所引 :80 系另一段文字，以 :210 为准） |
| reports/design 目录 | `ls reports/` + `ls reports/design` | 目录在位，命名惯例 `YYYY-MM-DD-<slug>.md`（含 2026-11-13-jev-artifact-map.md） |
| tests 三套件 | `ls tests/ \| grep -i monthly` | test_monthly_review.py / _propose.py / _watchdog.py 在位 |
| 今晚通道 | `uv run python scripts/ops_local_refresh.py --status` | ok_committed 95a841a9e3、2026-11-13T19:26 收工、pushed、backup ok、CI 双 paused(actions-disabled)、retry_soft/push_only_recovery 在位 |
| 轮次 | `head -25 state/current.md` | 顶部 = iterate 轮 8（handoff 136/136-续）→ 本轮顺延约 **137**（施工员核对最新号） |

（外向调研 7 items + 5 rejected、内证 24 命令全量见任务书原文，不在此复制。）

## 附录 B：as-built 勘误区（施工员 append-only 追加，本文正文不回改）

### B.1 design-report 条目收官（2026-11-13 20:50 施工，施工员）——全锚复测与漂移记录

- **测量环境**：HEAD `9c498a54cb`；`git status --short` 实测工作树除本报告（untracked）外零改动；动工前 `uv run python scripts/ops_local_refresh.py --status` = ok_committed（95a841a9e3，2026-11-13T19:26:55 收工，非 running——§6 今晚通道条款满足，docs 条目照常）。
- **代码锚（`scripts/monthly_review.py`，`grep -n` 实测）**：reconcile_predictions :978（函数体 :978-1039，:1039 `return lines_out`）｜judgments/facts 分账 :988-992（"output row separates judgments" :990）｜三带 NEVER-in-prompt :993（"Band cuts are FIXED" :998、docstring 收口 :1001）｜解析循环 :1006-1019（outcome 正则恰在 :1019）｜逐条 (p−y)² :1034｜resolved 渲染行 :1036-1038｜active_lessons_view :1163｜append_lessons :1209｜WATCHDOG_BOUNDED_QUESTION :1274｜parse_bounded_answer :1283｜lesson_seeds :1309（return 收口 :1325）｜render_reflexion_section :1328（{answer,p} 契约渲染 :1344-1346）｜main :1423、八旗标块 :1425-1463（恰八面旗：--month/--out/--repo/--weekly/--propose/--lessons/--append-lessons-from/--verify-bounded，末旗收于 :1463）。**与附录 A / §1 / §2 所引行号逐项一致，零漂移。**
- **runbook 锚（`docs/ops-local-refresh.md`）**：:89 `SKIP:attempt-cap` 3 次锁死（附录 A 所引 85-92 窗内）｜:234 两班不变（23:35 夜报单会话 + 月末复盘会话）｜:304-305 RLCD（arXiv:2307.12950「判别器反馈即改进信号」）｜调用面表 :340-346（唯一 LLM 面 = 月末单场）｜CalibrationDisplay 拒绝 :383（§1 所引 380-390 窗内）｜首跑预演注记窗 400-435（arXiv:2611.11480 :428、「首跑勿因 p 偏高/偏低临时引入校准」恰在 :433）｜:646 一带 push 失败 attempt-cap 锁定 + 交互恢复路径（实测 :646-648）。**零漂移。**
- **backlog 锚（`state/backlog.md`）**：RouteLLM 延伸索引⑤ 实测恰在 :210｜:50-58 窗含「月度小样本对账仅**记录性**校准，禁任何统计显著性声称」｜`grep -c "prediction:" state/backlog.md` = 0、`grep -c "outcome:" state/backlog.md` = 0（双零复核，红线 6 / §4 口径成立）。**零漂移。**
- **ledger 锚**：`wc -l runs/ledger.jsonl` = 71；末行 `"event": "forward_prediction_committed"`、ts 2026-10-09——与红线 1 所述一致。**零漂移。**
- **statsmodels 实跑复测**（`uv run python -c "from statsmodels.stats.proportion import proportion_confint; …"`，method="wilson"）：3/5 → (0.2307242812760129, 0.8823792257673522)、1/1 → (0.2065493143772374, 1.0)——与红线 9 / 附录 A 四舍五入值 (0.2307, 0.8824) / (0.2065, 1.0) 逐位一致。
- **目录/套件在位**：`reports/design/` 含 2026-11-13-jev-artifact-map.md（命名惯例同款 YYYY-MM-DD-<slug>.md）；tests 三套件 test_monthly_review.py / test_monthly_review_propose.py / test_monthly_review_watchdog.py 在位。
- **轮次核对**：`head state/current.md` 顶部块 = 「active (11-13，handoff 轮 136 系)【iterate 轮 8 四条目…】」——与附录 A 末行（顶部 = iterate 轮 8、handoff 136/136-续、本轮顺延约 137）一致；本报告属 iterate 轮 9 候选清单交付物（正文 :3 自述同向，轮 8 已于 9c498a54cb 入册收官）。ledger 轮次号落账归 ledger 批次核对，本条目不代定。
- **门禁（本条目）**：纯 docs（本文件附录 B 追加），0 代码触碰 → 相关单测面不适用；§6 收官门禁（ruff 净 + monthly 三套件 pytest + `--lessons`/`--propose` 实弹 + backlog 计数复核）系「动 code 时」条款，本条目不触发，如实注记**未跑**（backlog 双零计数已含于上文本会话复测）。本条目验证 = 上述全锚复测 + `git status --short`（仅本报告 untracked，无其他工作树扰动）。
- **时点注记**：施工实测时点 2026-11-13 20:50（系统时钟）；报告抬头 2026-11-14 系决策员定案稿自述决策时点，append-only 纪律下不回改。

### B.2 automation-ladder-runbook 条目收官（2026-11-13 21:10 施工，施工员）

- **落点与漂移策略**：新节「渐进自治梯（L0-L3 automation ladder，2026-11-13 入册）」追加于 `docs/ops-local-refresh.md` 文末（原 :695 后），现 :697-735，`git diff --numstat` = **40 0 纯增**；选文末追加正为保本报告附录 A/B.1 所引全部 runbook 锚（≤ :646-648）**零漂移**（实测复核 :89/:230/:340-346/:383/:400-435/:646-648 原行号不动）。行尾 CRLF 一致（735/735）。
- **内证复核**：「自治梯概念全仓零命中」属实——`L0-L3` 全仓仅本报告；「自治」另有 4 处无关用法（code-review 内聚注记、state/current.md:1091 研究方法学 constrained autonomy、reports/design/2026-08-12 综述、本报告），非梯概念、不构成既有入册。
- **新节所引锚全部本会话亲手实测**：`run_propose` monthly_review.py:1042 + 零 LLM 零网络声明 :1445 + 节奏表 :230「引擎对 backlog 只读」；`classify_run_row` ops_local_refresh.py:558-576 + 三桶常量 :542-544（platform-failure/infra-transient/code-defect 逐字）；`render_card` :951 + disposition 行 :972；`scripts/orchestrate_dispatch.py` 实存（ADR-012/dispatch 契约生成器）；`SKIP:attempt-cap` :89、push 锁定+交互恢复 :646-648；RouteLLM ⑤ backlog:210；prediction/outcome 双零；`--status` backup/push_only_recovery/retry_soft 字段复测在位。
- **施工自纠**：首写 L2 行「可维」错字，当轮 grep 自查发现即改回「可逆」（可逆性系合格面核心判据），已改净。
- **发现的既有陈锚（登记不处置——不属本条目触碰面）**：runbook 调用面表（:343）所引 `--propose` 锚「monthly_review.py:1399：zero LLM, zero network」已因 da29c32bd6（run_verify_bounded helper 插入）漂移，声明现址 :1445、`run_propose` 现址 :1042；调用面表行未动，待后续勘误批处置。
- **门禁（本条目）**：纯 docs、0 代码 → ruff/pytest 不适用未跑；验证 = 上述内证复核 + 新节全锚实测 + numstat 40 0 纯增 + CRLF 一致性。

### B.3 calibration-aggregator 条目收官（2026-11-13 21:05 施工，施工员）——环 1a 代码落地

- **落点实测（`scripts/monthly_review.py`，numstat 97/17）**：`_collect_prediction_records` :1026（:978-1024 reconcile 的解析循环原样上提，`import re as _re` 局部导入随迁）；`_CALIBRATION_BAND_CUTS` :1056（固定呈现常量，注释沿三带门纪律）；`calibration_bucket_summary` :1059（记录性分桶呈现：n/命中/命中率+Wilson 95% CI+每桶 p 原值计数+汇总 mean Brier；p<0.5/p 未填/pending/越界分列不计桶；0 resolved=单行 `none yet (baseline collection month)`；`proportion_confint` 惰性导入沿原 :1002 局部导入先例，CLI 启动零 statsmodels 加载）。reconcile_predictions 仍在 :978、渲染分支零触碰。
- **逐字节不变实测**：改码前于 HEAD 9c498a54cb 抓 8 行全类型 fixture 真实输出（resolved 高带×2/边界 0.6/0.5/反带 0.3/未填/pending 未到期/pending 逾期），改码后 `reconcile_predictions(...) == 基准` 实测 **True**，钉为测试 `test_reconcile_rendering_byte_identical_after_ring1a_lift`。
- **内证勘误（如实记）**：本报告 §2 环 1a「既有测试钉 + 新增钉」之前半不确——全 `tests/` grep 实测 reconcile **零既有钉**（命中皆系研究管线 leakage 测试的另一 prediction 概念）；环 1a 新钉即首钉。
- **测试（`tests/test_monthly_review.py` numstat 129/0，+7 钉）**：逐字节不变 / 空态（空列表+仅 pending 双面）/ 1-of-1 宽 CI `(0.2065, 1.0000)` / 桶界（0.5∈[0.5,0.6)、0.6∈[0.6,0.7)、pending 0.7 不入桶、分列行整行钉）/ 顶桶 [0.9,1.0] 闭 1.0 / 3-of-5 Wilson `(0.2307, 0.8824)`（§1 红线 9 statsmodels 锚钉进断言）/ 反聚集 p 原值计数（0.8×2、0.85×1）。首跑一红系**测试夹具自误**（0.75 与 0.8 本属异桶），改夹具 0.85 后全绿——被测函数零改。
- **门禁实跑（§6 动 code 条款）**：`uv run pytest tests/test_monthly_review.py tests/test_monthly_review_propose.py tests/test_monthly_review_watchdog.py -q` → **rc=0**（93 用例零失败）；`uv run ruff check`（全仓）→ All checks passed；`--propose` 实弹 **rc=0**、`--lessons` 实弹 **rc=0**；`grep -c "prediction:"/"outcome:" state/backlog.md` 复核 **0/0** 不变。动 code 前复跑 `--status` = ok_committed（非 running）。
- **行号漂移（+80，reconcile :1039 后全部顺移；本报告 §1/§2/附录 A 所引旧值→现值）**：active_lessons_view 1163→**1243**、append_lessons 1209→**1289**、WATCHDOG_BOUNDED_QUESTION 1274→**1354**、parse_bounded_answer 1283→**1363**、lesson_seeds 1309→**1389**（含 :1309-1325 窗→:1389-1405）、render_reflexion_section 1328→**1408**（:1328-1346 窗→:1408-1426）、--verify-bounded docstring 1384→1464、--propose 零 LLM 声明 1445→**1525**、main 1423→**1503**、旗标块 1425-1463→**1505-1543**（八旗首 --month :1505、末 --verify-bounded :1543，grep 实测）；reconcile :978、三带 :993-1001、judgments/facts :988-992、brier :1034 诸锚（≤1039）**零漂移**。B.2 所记 runbook 自节锚已随实测定正（run_propose 1042→1122、零 LLM 声明 1445→1525；render_card :951/:972 在 reconcile 前不受影响）。

### B.4 calibration-feedback-injection 条目收官（2026-11-13 21:20 施工，施工员）——环 1b 代码落地

- **落点实测（`scripts/monthly_review.py`，1a+1b 累计 numstat 124/19）**：`lesson_seeds` :1389（docstring 补环 1b 语义 4 行；体内读 `repo/BACKLOG_PATH`——沿 :778-781 缺文件容错先例（is_file 判空串，不报错不造数据），`calibration_feedback` 键=环 1a `calibration_bucket_summary(_collect_prediction_records(backlog_text))` 输出，零 LLM 零网络零新旗标）；`CALIBRATION_FEEDBACK_NOTE` 常量 :1424（固定禁令字面，注释声明「prohibition, never disposition advice」沿三带门 NEVER-in-prompt 契约）；`render_reflexion_section` :1429 体内 §5 区新增「校准事实（呈现≠校准——环 1b 注入，facts only）」节（watchdog 子弹之后、collection anomalies 之前），逐行注入聚合器输出+末行禁令重申。
- **测试（`tests/test_monthly_review.py` 累计 numstat 187/0，+3 钉；本套件 37 用例）**：空账本（无 backlog 文件 tmp repo）→ seeds 键恰为 `["none yet (baseline collection month)"]` 且渲染含节头/空态行/禁令字面三钉；有数据（p=0.8 y=1 + p=0.7 y=0）→ 两桶行 (0.2065, 1.0000)/(0.0000, 0.7935)+mean Brier 0.265（(0.04+0.49)/2）+禁令字面全钉；负向断言双 repo 状态 ×5 禁语（调 p 至/建议阈值取/应调 p/重标 p/校准 p 至）零命中——禁令重申行措辞与禁语集互斥系设计使然（prohibition ≠ disposition）。
- **门禁实跑（§6）**：动 code 前复跑 `--status` = ok_committed；`uv run pytest tests/test_monthly_review.py tests/test_monthly_review_propose.py tests/test_monthly_review_watchdog.py -q` → **rc=0**；`uv run ruff check`（全仓）→ All checks passed；`--lessons` 实弹 **rc=0** 且输出 :75-77 实含新节头+`none yet (baseline collection month)`+禁令字面（真实 backlog 双零→空态如实）；`--propose` 实弹 **rc=0**；`grep -c "prediction:"/"outcome:" state/backlog.md` 复核 **0/0** 不变。
- **行号漂移（环 1b 再 +25，:1390 起顺移；B.3 现值→B.4 现值）**：--verify-bounded docstring 1464→**1489**、--propose 零 LLM 声明 1525→**1550**（runbook 自节锚已随实测定正）、main 1503→**1528**、旗标块 1505-1543→**1530-1568**（八旗首 :1530、末 :1568）；lesson_seeds :1389 / CALIBRATION_FEEDBACK_NOTE :1424 / render_reflexion_section :1429 为 1b 后新实况；:1389 之前诸锚（reconcile :978、_collect :1026、聚合器 :1059、run_propose :1122、render_card :951/:972）**零漂移**。

### B.5 expel-insight-hook 条目收官（2026-11-13 21:35 施工，施工员）——环 2 代码落地，本批五条目代码面收口

- **落点实测（`scripts/monthly_review.py`，1a+1b+2 累计 numstat 145/19）**：`lesson_seeds` :1389 体内新增 `resolved_prediction_rows` 计数键（同一 `pred_records` 面，p 与 y 双填才计）；`INSIGHT_HINT` 常量 :1439（设计报告 §2 环 2 机制句原文+示例口径内联，注释锚 arXiv:2308.10144 协议-only（不引入 Faiss/环境训练代码）与红线 4 judgments/facts）；`render_reflexion_section` :1445 体内校准事实节后新增**一行**钩子——有 resolved 行渲染 `- insight 钩子（环 2·蒸馏）: {INSIGHT_HINT}`（含禁令字面「片段禁含『自动调 p』指令」），零 resolved 渲染降级行「本月无 resolved 对账行，insight 步跳过」。产出通道 rides 既有 `--append-lessons-from`（现址 append_lessons :1289、契约门+EVENT_OP_RE 四操作零改动）、零新增班次/旗标/LLM/网络。
- **如实注记（两处边界取舍）**：① 触碰点「可附拼装 helper」按"可附=可选"未做——输入面（reconcile resolved 行经 --propose 卡、active lessons 经 §6 聚合视图）已在月末会话可读面在位，一行指引足量（最小充分）；② records 不存 outcome 日期（解析循环 :1036-1049 原样上提未动）→ 降级条件为**累计**零 resolved，与设计报告降级字面「无 resolved 行」一致，行的月份归属由月末会话读行自判，如实注记不扩大解析器。
- **测试（`tests/test_monthly_review.py` 累计 numstat 223/0，+2 钉）**：有数据（1 条 resolved）→ `resolved_prediction_rows == 1` + 整行指引钉 + 禁令字面钉；空态双面（空 repo + 仅 pending）→ 计数 0 + 降级行整钉 + `INSIGHT_HINT not in text`（不渲染指引）。
- **门禁实跑（§6）**：动 code 前复跑 `--status` = ok_committed；三套件 `pytest -q` → **rc=0**；`uv run ruff check`（全仓）→ All checks passed；`--lessons` 实弹 **rc=0** 且输出 :78 实为降级行（真实 backlog 双零 resolved → 空态如实，与 §4 基线月声明一致）；`--propose` 实弹 **rc=0**；`grep -c "prediction:"/"outcome:" state/backlog.md` 复核 **0/0** 不变。
- **行号漂移（环 2 再 +21，:1400 起顺移；B.4 现值→B.5 现值）**：CALIBRATION_FEEDBACK_NOTE 1424→**1427**、render_reflexion_section 1429→**1445**、INSIGHT_HINT **:1439**（新增）、--verify-bounded docstring 1489→**1510** 一带、--propose 零 LLM 声明 1550→**1571**（runbook 自节锚第三次定正）、main 1528→**1549**、旗标块 1530-1568→**1551-1589**（八旗首 :1551、末 :1589）；lesson_seeds :1389 与 :1389 之前诸锚（reconcile :978、_collect :1026、聚合器 :1059、run_propose :1122、append_lessons :1289、render_card :951/:972）**零漂移**。
