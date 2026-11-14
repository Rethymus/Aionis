# iterate 轮 14 交付报告（2026-11-15；首决分支 B：轮 13 未收尾不双写，代码条目降级设计稿入报告；章节由各条目按其交办触碰点续写，append-only）

## 三、frontier-citation-anchors 就绪块（框架④；S；分支 B=预检+定稿落本节，backlog 纯追加归 post-close 派单）

### 首决与边界实况

- 分支 B 实证：动工前 `uv run python scripts/ops_local_refresh.py --status` → `ok_committed`（2026-11-13 晚 95a841a9e3，非运行中）；`git status --short --branch` → M×4（docs/ops-local-refresh.md、state/backlog.md、state/current.md、state/handoff.md）+ ??×2（scripts/anchor_guard.py、tests/test_anchor_guard.py），`git rev-list --count origin/main..HEAD` → **0**。轮 13 四条目确为工作树未提交态——本轮**不触碰 state/backlog.md**（轮 13 未提交文件，绝不双写），backlog 纯追加顺延 post-close。
- 改前零命中预检（真增量留证，沿轮 12/13 先例）：`git grep -i -e 2607.23802 -e argoproj -e kayenta -e 2508.06433 -e MemP 6f587cf91e` → **零命中 rc=1**。
- ㉝ 编号可用性辨明：`git show 6f587cf91e:state/backlog.md | grep -n ㉝` → 零命中 rc=1（登记落点内 ㉝=0，可用）。全仓另有 4 处 ㉝ 命中均系 2026-08 长周期轮号 33 的历史标记（reports/design/2026-08-30-longcycle-gapfill-protocol.md:7、state/current.md:717、state/handoff.md:607、state/handoff.md:712），与延伸索引 ID 域不同、不冲突。
- 一手复核（本会话实跑，全部与交办数字吻合）：`gh api repos/argoproj/argo-rollouts --jq '{license,stars,pushed_at,archived}'` → Apache-2.0 / 3623★ / pushed 2026-11-13 / archived=false；`gh api repos/Netflix/kayenta …` → Apache-2.0 / **archived=true** / pushed 2025-12-20 / 1304★；`gh api repos/zjunlp/MemP …` → MIT / 42★ / pushed 2026-01-30 / archived=false，repo description 自带「[ACL 2026]」；fox_fetch `arxiv.org/abs/2607.23802` → 标题「From RLVR to RLSVR: Task Transformation Induces Self-Verifiable Rewards for Open-Ended LLM Self-Improvement」、Comments=**COLM 2026**、摘要原文 task transformation→verifiable proxy environments；fox_fetch `arxiv.org/abs/2508.06433` → 标题「Memp: Exploring Agent Procedural Memory」、Comments=**ACL 2026 Findings**、摘要原文 Build/Retrieval/Update + continuously updates, corrects, and **deprecates**；fox_fetch `argo-rollouts.readthedocs.io/en/latest/features/analysis/` → 原文「Completed runs are considered **Successful, Failed, or Inconclusive**…continue, abort, or pause」+ Kayenta 在 metric provider 历史清单在列。

### 就绪块（post-close 追加 state/backlog.md 用，围栏内逐字节可拷贝）

```text
延伸索引㉝（2026-11-15 append，frontier-citation-anchors；仅引用零接入）：arXiv:2607.23802
  「From RLVR to RLSVR: Task Transformation Induces Self-Verifiable Rewards for Open-Ended
  LLM Self-Improvement」（Qinsi Wang et al.，cs.AI，v1 2026-07-26/v2 2026-07-31，Comments=
  COLM 2026——abs 页本日 fox_fetch 一手复核）。核心语义：RLVR 的确定性可验证奖励长期局限于
  数学/代码域，RLSVR 借自监督 pretext-task 思想以**任务变换**把开放任务改造成可验证代理环境
  （verifiable proxy environments），由环境内部规则与交互结果自动生成奖励。协议级映射 ≡ 轮
  14 框架①「insight-quality-gate」质量门（映射落点：三条确定性判据=可证伪 hook/引用对账行
  id 回查/禁复述 retire，全零 LLM）——「任务变换→确定性可验证判据」= 给开放产出补装确定性
  判据再消费的协议级正源，与 parse_bounded_answer 三态兜底/prop: 去重键等在册零 LLM 门同族。
  **不采部分（红线）**：RL 训练循环（策略优化/奖励建模）与 SpyRL 自博弈环境（Who Is the
  Spy? 社交推理投票奖励）全不采——本仓「训练」=提示词/经验级条件化零微调零 SDK；投票奖励
  环境属交互式训练面，与稳态 token 不增烧/无长驻进程红线冲突。**边界注记**：仅协议映射引用
  零接入；零新依赖零 SDK 零框架；研究面零改动。

延伸索引㉞（2026-11-15 append，frontier-citation-anchors；仅引用零接入；双源合一条目沿 ㉕
  Hindsight 多锚合一先例）：github.com/argoproj/argo-rollouts（Apache-2.0，本日 GitHub API
  复核 3623★、pushed 2026-11-13 活跃、archived=false）——AnalysisRun 官方文档本日一手复核
  **三态 verdict 词汇**（Successful/Failed/Inconclusive，结果分别驱动 continue/abort/pause）
  供轮 14 框架②「gate-assessment-bridge」桥的判定词汇表（≈ok/fail/not-enough-data，
  Inconclusive≈数据不足不判→pause，与轮 11 gate 三态同构）；「分析产出证据、晋升单独消费」
  （analysis 决定 rollout 推进而非替代部署本身）与「门绿≠实践健康」两注记必写。历史副锚：
  github.com/Netflix/kayenta（Apache-2.0，本日 GitHub API 复核 **archived=true、pushed
  2025-12-20 停摆**、1304★）——canary 自动判定分析先驱，Argo 官方文档 metric provider 历史
  清单仍列其名（渊源一手可证），沿 ㉗ A-MEM 停更注记先例只入历史锚不引活代码路径。**不采
  部分**：K8s 渐进交付运行时（Rollout/流量切分/自动回滚/CRD）全不采——本仓无服务部署面，
  只取三态判定词汇与「分析与晋升分离」语义；promotion gate 摘要零启用语义（只呈现不启用）。
  **边界注记**：仅引用零接入；零新依赖零 SDK 零框架；研究面零改动。

延伸索引㉟（2026-11-15 append，frontier-citation-anchors；仅引用零接入）：arXiv:2508.06433
  「Memp: Exploring Agent Procedural Memory」（Runnan Fang et al.，cs.CL，v1 2025-08-08/
  v4 2026-04-15，Comments=ACL 2026 Findings——abs 页本日 fox_fetch 一手复核）+ repo
  github.com/zjunlp/MemP（MIT，本日 GitHub API 复核 42★、archived=false、**pushed 2026-01-30
  停更注记**[距本日约 9.5 月未推，沿 ㉗ A-MEM 先例如实注记]）。程序性记忆（step-by-step
  instructions + script-like abstractions）全生命周期 **Build/Retrieval/Update** + 动态
  regimen（continuously updates, corrects, and deprecates）供轮 14 框架③
  「memp-insight-lifecycle」——环 2 片段治理「新登记 vs 既有片段 refinement/deprecate 双
  路径」的全生命周期语义正源；deprecate ≡ 轮 128-续3 UPDATE(supersedes) 写前接替**成对闭环**
  （㉗ A-MEM 供「何时该更新」，Memp 补程序性侧 update/correct/deprecate 三操作）。与在册
  ㉕ Hindsight（陈述性 facts/beliefs）/㉗ A-MEM（笔记型更新语义）/㉛ Mem0（生成侧预检判据）
  不同族=Memp 管程序性维度（步骤/脚本），记忆光谱程序性缺口补齐=真增量。**不采部分**：
  online build 在线构建管线不采（蒸馏沿月末 offline 批量，稳态 token 不增烧）；检索/蒸馏
  实现面（嵌入相似度/迁移实验）不采——判定门零 LLM 零嵌入照守（㉕/㉛ 先例）。**边界注记**：
  仅引用零接入；零新依赖零 SDK 零框架；研究面零改动。
```

### post-close 追加点（交办指定，本轮不执行）

- 落点：`state/backlog.md` 延伸索引尾部纯追加——轮 13 自增 ㉜ 条目（本会话实测 :234 起、尾行
  :259「…研究面零改动。」）之后、空行+「## 前沿吸收」节头（本会话实测 :262）之前，三条各以
  空行分隔；行号会随轮 13 收尾漂移，post-close 以「延伸索引㉜」条目尾行内容定位为准。
- 追加后复核口径：三条 ID（㉝/㉞/㉟）在 backlog 各恰 1 次；`uv run python scripts/ops_local_refresh.py --propose` 实弹 exit 0 零自动写（新条目不含 `key: prop:` 字面串，不误发卡）。

## 四、insight-quality-gate 设计稿（框架①；S；分支 B 降级：本节只落设计稿，post-close 派单施工）

### 4.0 降级判定与现状审计（本会话实跑）

- 降级前提实证：`git diff --quiet scripts/monthly_review.py` → **rc=0**（py==HEAD 零漂移）——该文件的 file:line 锚是轮 13 刚修净锚债（92 处跟改+清零断言）的验证前提，收尾前动代码会令 :1515/:1577/:1858 等锚全数漂移，故代码面降级 post-close。
- 现状锚点实读（与交办逐行一致）：`INSIGHT_HINT` 定义 scripts/monthly_review.py:1515（仅『禁自动调 p』一条提示+IF-THEN 示例口径，**零质量判据**）；render 注入 :1577（`- insight 钩子（环 2·蒸馏）: {INSIGHT_HINT}`，无 resolved 行时 :1579-1580 跳过）。全文件 `grep -i insight` 仅 :1515/:1577/:1579/:1804/:1807 五处——**引擎侧现无任何 insight 解析/判定路径**（片段由月末会话经 --append-lessons-from 写回 state/handoff.md，引擎只读聚合）。
- 设计所依赖的在册锚点（本会话逐一实读）：`lesson_seeds` :1448（seeds dict 组装）；`reconcile_predictions` :1002 + `_collect_prediction_records` :1050（one parser N consumers 先例——resolved 行判定判据=「p 与 y 均在场」）；`parse_bounded_answer` :1422（verdict dict 三态兜底先例：`{"ok": bool, "reason": str, "raw": text[:120]}`）；`feedback_dedup_verdict` :1858（纯函数判定器契约先例：零 LLM 零嵌入+字面比对+诚实缺省）；`active_lessons_view` :1302 + `EVENT_REF_RE` :1270（`month#n` 条目 id 与 retire 集=(supersedes|voids) 引用元组，retire 集构造 :1312-1317）；`append_lessons` :1348（写回通道）；`FOCUS_FEEDBACK_BUDGET_NOTE` :1807（INSIGHT 0-2 条额度注记——focus 行占 1 条）；`promotion_gate_assessment` :2024（轮 11 计算门，只算不启用）。
- 测试现状：`uv run pytest --collect-only -q tests/test_monthly_review.py` → **61 collected**（与交办一致）。

### 4.1 判定器规格（纯函数，零 LLM 零嵌入零 I/O）

**函数**：`insight_quality_verdict(head_line: str, body_lines: list[str], review_month: str, resolved_ids: set[str], retired_texts: list[str]) -> dict`——纯函数（输入全部由调用方传入，函数自身零文件读取零网络零嵌入，沿 feedback_dedup_verdict :1858 纯输入契约；verdict 键形沿 parse_bounded_answer :1422）。

**范围标记**（三条新正则，模块级常量，post-close 落码）：
- `_INSIGHT_ENTRY_RE = ^\s*[-*]\s*event:\s*ADD\b.*\binsight\b`——判定「哪条 entries 是 insight 候选」（只看 ADD，UPDATE/DELETE/NONE 永不参评）；
- `_INSIGHT_HOOK_RE = \bhook=(\S[^；;|]*)`——hook 令牌提取；
- `_INSIGHT_REF_RE = \bref=(\d{4}-\d{2})#(\d+)`——对账行引用提取。

**三判据（确定性顺序，first-miss 即停）**：
1. **可证伪 hook（hook-miss）**：`hook=` 令牌缺失/为空，或条目正文无 `IF…THEN` 句式对（关键词结构检查：`re.search(r"\bIF\b[\s\S]*\bTHEN\b", body)`）→ `{"ok": False, "reason": "hook-miss", "raw": head[:120]}`。句式/关键词结构检查=可证伪性的最小确定性代理（有「依据句」+「IF-THEN 骨架」即可证伪 hook 在场；语义真伪不由引擎判）。
2. **引用对账行 id（bad-ref）**：`ref=` 缺失，或引用月份 ≠ review_month，或 `f"{month}#{n}" ∉ resolved_ids`（伪 id）→ `{"ok": False, "reason": "bad-ref", ...}`。`resolved_ids = _resolved_row_ids(_collect_prediction_records(backlog_text), review_month)`——新增纯函数：对 p 与 y 均在场的 resolved 记录按文件序 1-based 编号（`YYYY-MM#1..k`），与 §4 呈现共用同一 id 源（one parser N consumers，零漂移；`_collect_prediction_records` :1050 复用不改动）；**严格当月**（跨月引用一律 bad-ref——沿 dedup 同桶边界先例：跨月时间维度记录互不吞噬，宁严勿宽）。
3. **禁复述已 retire（retire-restatement）**：insight 全文（head+body）经空白归一化后**包含**任一被 retire 条目归一化全文（子串字面比对，零嵌入）→ `{"ok": False, "reason": "retire-restatement", ...}`。retired_texts=retire 集（:1302-1317 同款 EVENT_REF_RE 扫描）所引 `(month, idx)` 条目的归一化全文；**比对对象=retire 段而非 active 段**——active 复述由 feedback_dedup_verdict :1858 同桶键管辖，两门正交不重叠。
4. 三判据全过 → `{"ok": True, "ref": "<month#n>"}`。

**呈现契约（render 侧，§5 新增 insight quality 块）**：
- 合法条目 → 入本月蒸馏候选池（seeds 有效池），呈现 `[month#idx] 合格 insight` 行；
- 不合规条目 → `- insight quality-miss[<reason>] [month#idx]: <head 原文截断>（拒入本月蒸馏候选池）`——**quality-miss 理由行不占 INSIGHT 0-2 条额度**（沿轮 145 dedup 降级不附预算注记先例）；
- **§6 档案呈现零改动**：active lessons 聚合视图照旧全量呈现（引擎不写 handoff、append-only 展示不回改；quality-miss 只过滤 seeds 候选池，非档案删改）。

### 4.2 post-close 触点行号（行号=本会话实读值，落地时以当次实读为准+锚跟改批）

1. `scripts/monthly_review.py`：①`INSIGHT_HINT` :1515 文案更新——追加 envelope 契约句（每条片段 head 行含 `hook=<可证伪依据> ref=<YYYY-MM#n>`+正文 IF-THEN）与 RLSVR 协议映射注记句（prompt 侧 prose 改动，门语义仍在代码侧）；②新增 `_INSIGHT_*` 三正则+`_resolved_row_ids`+`insight_quality_verdict`（建议落位 feedback_dedup_verdict :1858 邻域，同契约家族同区）；③`reconcile_predictions` :1002 resolved 行加 `[YYYY-MM#n]` id 前缀（可引用化，供月末会话按 id 引用）；④`lesson_seeds` :1448/调用链——verdict 在已持有 handoff 文本（prior/retired）与 backlog 文本（resolved ids）的调用层计算，复用既有 `_lessons_blocks`/`_parse_lesson_entries`/retire 扫描，零新增文件读取；seeds 加 `insight_quality` 键（one parser N consumers 口径）；⑤`render_reflexion_section` §5 新增呈现块（:1577 INSIGHT_HINT 行邻域）。
2. `tests/test_monthly_review.py`（61→65）：四态钉见 §4.3。
3. **锚跟改批**（沿轮 12/13 纪律）：本条目落地顺移 :1515 之后行号——python 计数断言+旧值清零+`scripts/anchor_guard.py` 守卫复跑，与收尾派单同批。

### 4.3 四态测试钉清单（tests/test_monthly_review.py，61→65）

| # | 态 | 构造 | 断言 |
|---|----|------|------|
| 1 | 合法 | `hook=当月 resolved 行 y=0 而 p=0.85 的反例…`+`ref=2026-11#1`（resolved_ids 含 #1）+正文含 IF-THEN+无 retire 重叠 | `{"ok": True, "ref": "2026-11#1"}`；入 seeds 有效池 |
| 2 | 缺 hook | head 行无 `hook=` 令牌（或 hook 为空/正文无 IF-THEN 骨架） | `ok=False, reason="hook-miss"`；render 产出 quality-miss 理由行、不入池 |
| 3 | 伪 id | `ref=2026-11#9`（resolved 仅 #1-2）/`ref=2026-10#1`（跨月）/ref 缺失 | `ok=False, reason="bad-ref"` 三变体各一或参数化 |
| 4 | retire 复述 | insight 正文含某被 retire 条目归一化全文子串 | `ok=False, reason="retire-restatement"`；档案 §6 呈现不变 |
| + | 契约钉 | verdict 键形断言（ok/reason/raw 与 parse_bounded_answer 同形）；quality-miss 行不含预算注记（沿轮 145 负向钉先例） | 2 条 |

### 4.4 参照系与不采部分（本会话 gh api 一手复核）

- **promptfoo**（github.com/promptfoo/promptfoo，MIT，gh api 本日复核 **27154★、pushed 2026-11-14 活跃、archived=false**）：确定性断言分层——判据名+正则/函数+severity 断言表、一个 parser N consumers ≡ 本判定器三判据表+first-miss 顺序+verdict reason 词表；**Node 工具本体不装不引**（零新依赖红线，仓库零 package.json 触碰）。
- **AgentEvolver**（github.com/ModelScope/AgentEvolver，Apache-2.0，gh api 本日复核 **1592★、pushed 2026-04-01、archived=false**[~7.5 月未推，沿停更注记先例如实注记]）：self-attributing 仅协议映射——quality-miss 理由行=证据归因呈现（哪条判据没过、ref 指向哪行）；self-questioning/self-navigating 与 verl 训练框架全不采；**ModelScope 组织与在册 LLM pool 无关注记**（同名不同物：provider 池的 ModelScope 端点与本仓引用无涉，provider 红线不受影响）。
- **RLSVR**（arXiv:2607.23802，COLM 2026；本日已登记 backlog 延伸索引㉝）：任务变换→可验证判据协议映射 ≡ 给 insight 补装确定性判据再消费；RL 训练循环/SpyRL 自博弈环境全不采（红线）。
- **红线重申**：判定器零 LLM 零嵌入零 I/O（纯函数）；lessons 档案 §6 append-only 零回改；promotion gate :2024 唯一晋升门语义不变（本门=蒸馏前质量门，只呈报不晋升、不启用手柄）；引擎不写 handoff（呈报-入册分离）；INSIGHT 0-2 额度注记不被 miss 行膨胀。
- **设计稿边界**：本节为规格非实现——所有函数签名/正则为设计定稿，post-close 落地时以当次实读行号为准并跑锚跟改批；四态钉的构造细节（fixture 文本）由施工员按真实 resolved/retired 数据形态微调，断言语义不变。

## 五、gate-assessment-bridge 设计稿（框架②；S；分支 B 降级：本节只落设计稿，post-close 派单施工）

### 5.0 降级判定与现状审计（本会话实跑）

- 降级前提同①：`git diff --quiet scripts/monthly_review.py` → **rc=0**（py==HEAD 零漂移维持，动工前 `--status` ok_committed）。
- 审计 grep 实证（与交办逐行一致）：`grep -n promotion_gate_assessment` 全文件恰 4 处——def **:2053**、注释引用恰 **:1102**/**:1890** 两处（compute-only, owner key 语义句）、:2074（函数体内部 notes 表常量装配）——**零外部调用零渲染**＝「gate 输出当前无人消费」成立；本桥=该函数首个消费方。`GATE_SCOPE_NOTE` :2048（只算不启用：钥匙在业主；与 OOS 判定零关系）。
- gate 返回形状实读（:2053-2200）：`{"state": "met"|"not-met"|"not-enough-data", "items": [{axis, metric, threshold, verdict, reason}]×4 轴, "notes": [GATE_SCOPE_NOTE, ANYTIME_MONITORING_NOTE]}`；per-axis verdicts=pass/fail/undetermined/not-enough-data；overall 归并实读 :2193-2200（轴含 undetermined 或 not-enough-data → state=not-enough-data；否则含 fail → not-met；否则 met；返回行 :2200）；阈值=业主定标 INPUTS 参数传入、绝不内嵌魔数（gate docstring 原文契约）；`ANYTIME_MONITORING_NOTE` :2045（anytime 局限如实注记；gate 内 statsmodels 惰性导入 :2065）。
- `run_weekly` def **:568**，返回 `("\n".join(lines) + "\n", (1 if findings else 0))` 于 **:655**；尾部现行末节=「## Findings requiring human attention」:652-654。现有 run_weekly 实弹测试挂点：tests/test_monthly_review_propose.py:276、tests/test_monthly_review_watchdog.py:72/:95。
- 三套件现状（collect-only 实测）：monthly=61 / propose=34 / watchdog=25（合计 120，与轮 12 收官账逐字吻合）。

### 5.1 一行摘要格式（定稿）与三态映射

**新常量 `GATE_BRIDGE_NOTE`**（两注记合一条常量，GATE_SCOPE_NOTE :2048 邻域落位）：

> 分析产出证据、晋升单独消费——门绿≠实践健康（Argo 实况案例：analysis passed 而 canary 仍 broken）；三态 verdict 词汇沿 Argo AnalysisRun 完成态 Successful/Failed/Inconclusive ≈ ok/fail/not-enough-data（Inconclusive=数据不足不判，环 2 降级+gate not-enough-data 同族）；摘要只呈现零启用——自动晋升决策绝不实现，L2 钥匙在业主（GATE_SCOPE_NOTE 钥匙语义不变）

**两注记全文**（设计定稿，各自语义）：
1. **「分析产出证据、晋升单独消费」**——gate 四轴的 metric/reason 是证据呈现（算什么、判什么、为什么）；晋升是另一个独立消费动作，由业主单独读取 gate 输出裁决；摘要行永不触发任何晋升/处置动作。Argo 同构：analysis 决定 rollout continue/abort/pause 而非替代部署本身。
2. **「门绿≠实践健康」**——四轴全 pass（门绿）仅说明数学判据当前达标，不等于运维实践健康（Argo 实况案例：analysis passed 而 canary 仍 broken——度量通过≠交付健康）；摘要呈现即为防读者把门绿误读为实践健康。

**三态映射表**（gate overall state ↔ Argo AnalysisRun 完成态，本会话 Argo 官方文档一手复核原文「Completed runs are considered Successful, Failed, or Inconclusive…continue, abort, or pause」）：

| gate state（:2193-2200 归并规则） | Argo 词汇 | 简写 | 语义 |
|----|----|----|----|
| `met` | Successful | ok | 全轴可算且达标 |
| `not-met` | Failed | fail | 全轴定标、数据足、有轴客观不达标 |
| `not-enough-data`（含轴 undetermined 归并） | Inconclusive | not-enough-data | 数据不足不判/未定标不造阈值——环 2 降级+gate not-enough-data 同族 |

**新纯函数**：`promotion_gate_summary_line(records: list[dict], thresholds: dict | None = None) -> str`——零 LLM 零 I/O，内部调 `promotion_gate_assessment` :2053（首消费方）；`thresholds=None` 缺省=全轴 honest 未定标→state=not-enough-data（沿 gate「阈值=业主定标 INPUTS」契约，不嵌魔数不造阈值）。

**一行模板（定稿）**：

> `- promotion gate assessment（round 14 桥·只呈现零启用）: gate=not-enough-data［Argo: Inconclusive≈数据不足不判］ | 轴判定 N:not-enough-data X:not-enough-data Y:not-enough-data M:not-enough-data | {GATE_BRIDGE_NOTE}`

三态词形替换规则：`gate=<state>［Argo: <映射词>≈<简写语义>］`按映射表逐态替换；轴判定段=四轴 `{axis}:{verdict}` 空格连接（verdict 取 per-axis 原词 pass/fail/undetermined/not-enough-data，不二次翻译）。

**插入点**：run_weekly 尾部 Findings 节（:652-654）后、`return` :655 前——`lines.append("")` + 摘要行一行；**退出码语义零改动**（摘要永不计入 findings，`1 if findings else 0` 原样——零启用语义的代码侧体现）。

### 5.2 post-close 触点行号（行号=本会话实读值，落地时以当次实读为准+锚跟改批）

1. `scripts/monthly_review.py`：①`GATE_BRIDGE_NOTE` 常量+`promotion_gate_summary_line` 纯函数（落位 promotion_gate_assessment :2200 返回行后邻域，同 gate 家族同区）；②`run_weekly` :655 `return` 前插入空行+摘要行（数据源 `records=_collect_prediction_records(backlog_text)`——backlog 文本读取复用既有路径、parser 复用 :1050 零新解析；thresholds 参数由 run_weekly 签名透传缺省 None，业主定标后接线的挂钩位）。
2. 测试钉（三态+零启用负向钉，挂 monthly/watchdog 现有套件——propose.py:276 与 watchdog.py:72/:95 已有 run_weekly 实弹路径可复用）：①ok 态（构造全轴可算且达标的 records+显式 thresholds → 行含 `gate=met` 与 Successful 映射）；②not-enough-data 态（thresholds=None 缺省或零 resolved → `gate=not-enough-data` 与 Inconclusive）；③fail 态（构造客观不达标+阈值入参 → `gate=not-met` 与 Failed 映射）；④负向钉（行含「只呈现零启用」+两注记全文在册；run_weekly 退出码不受摘要影响——findings 空则 0）。
3. 锚跟改批同①：:568 之后行号顺移——python 计数断言+旧值清零+`scripts/anchor_guard.py` 守卫复跑，与收尾派单同批。

### 5.3 参照系与不采部分

- **Argo Rollouts**（Apache-2.0/3623★/pushed 2026-11-13 活跃，本日 backlog 延伸索引㉞ 已登记）：AnalysisRun 完成态三态词汇=呈现层词汇表借用；**K8s 渐进交付运行时全不采**（同 ㉞ 不采部分）；Kayenta 历史副锚（archived=true、pushed 2025-12-20）同 ㉞ 只入历史。
- **与①正交**：本桥=晋升面呈现桥，质量门①=蒸馏前判定器——两门正交不重叠；`promotion_gate_assessment` 唯一晋升门语义不变（EVOLUTION_SCOPE_NOTE :1890 在册句「判定门唯一=promotion gate 且只算不启用，钥匙在业主」——本桥不改该句、不碰该门内部）。
- **红线重申**：零启用（摘要只呈现；自动晋升决策绝不实现，L2 钥匙在业主）；退出码零改动；零新依赖（statsmodels proportion_confint 已在 gate 内部惰性导入 :2065，桥零新 import）；摘要挂 --weekly 输出尾部=值班呈现面——不新增班次、不新增 LLM 会话、不触碰研究面。
- **设计稿边界**：同 §4.4——规格非实现，post-close 以当次实读行号为准并跑锚跟改批；三态钉的 fixture records/thresholds 构造细节由施工员按 gate 真实轴语义微调，断言语义（三态映射+两注记+退出码不变）不变。

## 六、memp-insight-lifecycle 设计稿（框架③；M；分支 B 降级：本节只落设计稿，post-close 派单施工；四条目中唯一横跨 ops 契约文档+引擎两面并需与轮 128-续语义对设计）

### 6.0 降级判定与现状审计（本会话实跑）

- 降级原因双实证：①docs 落点 `docs/ops-local-refresh.md` 为轮 13 未提交文件（`git status` M 在列——`git diff --quiet scripts/monthly_review.py docs/ops-local-refresh.md` rc=1 即 runbook 有轮 13 未提交改动；py 单独 `--quiet` 本会话前验 rc=0 零漂移）；②代码面同①②（待轮 13 收尾）。
- 现状实读：环 2 片段写回契约=四操作事件词 `EVENT_OP_RE` **:1269**（`ADD|UPDATE|DELETE|NONE`）+lessons 块格式节 `docs/ops-local-refresh.md` **:400-415**（计划形契约/`event:` 行/`evidence:` 行三 bullet，本会话实读）——**无「新登记 vs 既有片段 refinement/deprecate」生命周期指引**（月末会话拿到的是四操作语法、无裁决路径指引）；`INSIGHT_HINT` :1515 现行仅 ADD 语义（0-2 条新抽 IF-THEN）。NONE 先例在册：render :1563 契约行「写回按 event: NONE[重复已录]/UPDATE 定档——写入方裁决，零 LLM 零嵌入判重」（轮 145）。轮 128-续3 UPDATE(supersedes) 在册：`active_lessons_view` :1302-1327（retire 集+「its own replacement carries the lesson forward」语义）。
- 参照源一手复核（本会话实跑）：**Memory-R1** = arXiv:2508.19828「Memory-R1: Enhancing Large Language Model Agents to Manage and Utilize Memories via Reinforcement Learning」（cs.CL，v1 2025-08-27/v5 2026-01-14，abs 页本日 fox_fetch 一手复核：Memory Manager 学 **ADD/UPDATE/DELETE/NOOP** 结构化操作+Answer Agent+outcome-driven RL **PPO/GRPO**+三基准 **LoCoMo/MSC/LongMemEval**）+ repo github.com/yansikuan/memory-r1（**Apache-2.0，gh api 本日复核 134★、pushed 2026-11-07、archived=false**——与交办逐字吻合；作者 Sikuan Yan=仓主 yansikuan 同名互证身份）。Memp=backlog 延伸索引㉟（本报告 §三已登记）。

### 6.1 双路径指引文本（定稿，post-close 追加 lessons 块格式节 :400-415 尾部为第四 bullet）

> - **片段生命周期双路径（Memp 协议映射+Memory-R1 outcome 门控；轮 14 框架③）**：月末会话抽片段前先裁决路径——**路径 A 新登记**：本月 resolved 对账行支撑的新教训 → `event: ADD`，每条带 `hook=<可证伪依据> ref=<YYYY-MM#n>` 信封（质量门①三判据把关）；**路径 B 既有片段处置**：新 outcome 证据指向既有片段时 → refinement=`event: UPDATE`（`supersedes month=YYYY-MM#条目`，修正形接替、replacement 携教训前行）或 deprecate=`event: DELETE`（`voids month=YYYY-MM#条目`，废弃退役）；无证据变化 → `event: NONE`（重复已录不重写，轮 145 先例）。**片段保留/晋升须引用月度 resolved 对账 outcome 证据（`ref=`）而非自评**（Memory-R1 outcome 门控协议映射）；UPDATE/DELETE 的 `month#条目` 目标必须真实存在（伪 id=quality-miss，与①第二判据同一 gate）。prose 由会话 LLM 生成，门零 LLM。

### 6.2 deprecate×supersedes 闭环设计（写侧×读侧配对，轮 128-续语义零改动）

| Memp 操作 | 在册事件词 | 读侧消费（在册，零改动） | 轮 14 gate 校验（post-close） |
|----|----|----|----|
| update / correct | `event: UPDATE`（supersedes month=M#n，轮 128-续3） | `active_lessons_view` :1302 retire 该 id、replacement 携教训前行 | 目标 id 存在性（伪 id→quality-miss，复用①bad-ref）+outcome `ref=` 在场（Memory-R1 门控） |
| deprecate | `event: DELETE`（voids month=M#n） | 同 retire 集（`EVENT_REF_RE` :1270） | 同上；被 retire 条目全文进 retire 段=①第三判据比对对象 |
| new registration | `event: ADD`+①信封 | §6 archive 全量呈现 | ①三判据（hook/伪 id/禁复述 retire） |
| no-op | `event: NONE`（轮 145；Memory-R1 NOOP 词汇对齐） | 旧条照旧呈现 | 无新校验（重复已录不重写） |

- **闭环三段**：写侧（会话按 6.1 指引产出引用式标记，不改旧块字节）× 归并侧（`active_lessons_view` retire 集消费标记——在册零改动）× 读侧防回潮（①第三判据禁复述 retire 段——被废弃教训不得以新 ADD 名义复活）。轮 128-续 A-MEM 供「何时该更新」时机语义、Memp 补 update/correct/deprecate 三操作词汇、Memory-R1 供 outcome 证据门控——**同一闭环的写侧/读侧两半在本条目合拢**。
- 引擎侧识别复用：deprecate/UPDATE 识别零新解析循环（`EVENT_REF_RE` :1270 与①retire 扫描复用）；quality-miss 词表零新增（目标不存在=复用 bad-ref，复活复述=复用 retire-restatement——语义细分入 reason detail，不改①四态词表）。

### 6.3 offline 边界注记（不采部分）

- **online build 不采**：Memp 在线 Build/Retrieval 管线与 Memory-R1 RL 训练闭环（PPO/GRPO fine-tuning、152 QA 训练对）全不采——蒸馏保持月末 offline 批量（稳态 1 LLM 会话/晚红线；无后台长驻进程红线）。
- **评测基建不采**：LoCoMo/MSC/LongMemEval 三基准评测基建不采（本仓判定面=月度 resolved 对账 outcome，非外部 QA 基准；n=1 月度样本禁统计拟合）。
- **红线重申**：prose 由会话 LLM 生成、门零 LLM 零嵌入零 I/O（沿①②判定器契约）；lessons 档案 append-only 引用式标记零回改（轮 128-续语义与四操作本体 `EVENT_OP_RE` :1269 零改动，本条目只加指引与校验）；引擎不写 handoff（呈报-入册分离）；INSIGHT 0-2 额度注记（`FOCUS_FEEDBACK_BUDGET_NOTE` :1807）不被双路径指引膨胀。

### 6.4 post-close 触点行号（行号=本会话实读值，落地时以当次实读为准+锚跟改批）

1. `docs/ops-local-refresh.md` lessons 块格式节（:400-415 实读值；**轮 13 未提交文件——post-close 轮 13 收尾后追加**）：§6.1 双路径指引 bullet 一条（三既有 bullet 之后）。
2. `scripts/monthly_review.py`：①`INSIGHT_HINT` :1515 文案扩双路径一句（prompt 侧 prose）；②gate 扩展（沿 §4 判定器）：UPDATE/DELETE 类条目目标 id 存在性+outcome `ref=` 在场校验（复用 `EVENT_REF_RE` :1270/①bad-ref/retire-restatement 词表，零新增 reason）。
3. `tests/`（挂 monthly 三套件 61/34/25 现状基线）：①lessons 契约头/LESSONS_CONTRACT_NOTE 契约句更新断言；②UPDATE/DELETE 目标伪 id→quality-miss（复用①四态钉架）；③闭环钉：`DELETE(voids)` 后同文新 ADD 复述 → retire-restatement 开火（写侧读侧配对实证）；④NONE/NOOP 注记断言（轮 145 四操作 fixture 扩一句）。
4. 锚跟改批同①②：runbook :400 节系轮 13 锚批触碰面（`scripts/anchor_guard.py` 守卫覆盖域）+py 行号顺移——python 计数断言+旧值清零+守卫复跑，与收尾派单同批。

### 6.5 参照系与不采部分

- **Memory-R1**（arXiv:2508.19828+yansikuan/memory-r1，Apache-2.0/134★/pushed 2026-11-07 活跃/archived=false）：outcome 门控协议+ADD/UPDATE/DELETE/NOOP 词汇=协议级只读参照；**PPO/GRPO 训练实现与 LoCoMo/MSC/LongMemEval 评测基建绝不采**（RL 训练循环红线同 RLSVR ㉝；零新依赖零 SDK）。
- **Memp**（㉟，ACL 2026 Findings+MIT）：Build/Retrieval/Update 全生命周期+update/correct/deprecate 动态 regimen=词汇正源；online build 不采（§6.3）。
- **三门正交**：①第三判据=读侧防回潮、②桥=晋升面呈现、③=写侧生命周期指引——各司其职；promotion gate :2024 唯一晋升门语义与四操作本体零改动。
- **设计稿边界**：同 §4.4/§5.3——规格非实现；docs 落点行号为轮 13 未提交工作树实读值，post-close 以收尾后实读为准。

## 七、复核修复勘误（append-only，2026-11-14 独立复核轮；沿轮 8 §7+轮 10/11 hunk errata 先例——上文原句不回改，以此节承载）

1. **（high）handoff 简写锚自伤 live pin——已行内修复**：轮 148-151 收尾段原写「propose.py:276/watchdog.py:72/:95」系简写锚字面（propose.py 全树不存在），致 `uv run pytest -q tests/test_anchor_guard.py` 4 passed 1 FAILED（live pin 抓获新增 lost ('state/handoff.md', 2966, 'propose.py', 276)）、守卫 lost 2→3——违 tests/test_anchor_guard.py 拦截契约（Any NEW drifted/lost anchor fails the pin）与轮 147-续 handoff :2962「本叙事避免再植同款锚字面防自伤 live pin」告诫（如实：植入时未复跑守卫，evidence 行亦未记守卫复跑）。修复=未提交行内改全名「tests/test_monthly_review_propose.py:276 与 tests/test_monthly_review_watchdog.py:72/:95」（该行从未提交、无已提交字节史可勘误，行内改+本节双留痕）；修复后实跑：`uv run pytest -q tests/test_anchor_guard.py`=**5 passed [100%]**、`uv run python scripts/anchor_guard.py` summary explicit=87 hit=85 drifted=0 lost=2 基线恢复（余两 lost=轮 13 冻结 KNOWN_BAD：handoff :2922 prompts.py 第 113 行/:2936 iterate-round-2.md 简写名）rc=0、`uv run ruff check` All checks passed。**二阶陷阱如实**：evidence 行复述修复时简写字面再植（「简写锚 propose.py:276/watchdog.py:72/:95 行内改全名…」同句含毒锚）被终验电池抓获（守卫 lost 3/pytest 红——:2968 propose.py:276 lost），改「propose.py 第 276 行形」写法破字面后终验复绿（**lost=2**/pytest 5 passed/守卫 explicit=89 hit=87 drifted=0）；报告非守卫账本（守卫只读两 ledger）本节字面留档不设防。
2. **（medium）:2024→:2053 三处勘误**：本报告 :73（§四.0 在册锚点表）/:117（§四.4 红线重申）/:212（§6.5 三门正交）三处引 promotion_gate_assessment 为 **:2024**——实测 def 在 scripts/monthly_review.py:**2053**（`grep -n "def promotion_gate_assessment"`→2053），:2024 实为轮 11 注释横幅首行（# iterate round 11 — promotion-gate-function…）。§五 :125 与 commit message、current.md 之 :2053 正确。post-close 施工以 **:2053** 为准；已推送原文不回改。
3. **（low）「恰 4 处」→「恰 3 处」**：:125 计数失实——promotion_gate_assessment 符号串实测恰 **3** 处（:1102/:1890/:2053）；:2074 系 GATE_SCOPE_NOTE 装配行（原 grep 双模式 `promotion_gate_assessment\|GATE_SCOPE_NOTE` 所致误计），不含该符号串。结论「零外部调用零渲染」核实仍成立（3 处=def+两注释，零调用）。
4. **（low）「五处」→「六处」**：:72 `grep -i insight` 漏计 :1580（「insight 步跳过」折行）——实测**六行**（:1515/:1577/:1579/:1580/:1804/:1807）。实质结论「引擎侧无 insight 解析/判定路径」仍成立（全部为常量定义/render 注入/预算注记注释）。
5. **（low）日期命名注记**：报告文件名/handoff 条头 **2026-11-15**、current (11-15)，而提交 adb7062328 时间戳 Sat **2026-11-14** 16:43 +0800（`git show` 实测）；轮 10-12 报告均按提交当日命名（2026-11-14-iterate-round-10/11/12.md）。本文件名系定夺产出 deliverable_path 固定值（`.zcode/workflow-drafts/迭代轮-14…定夺清单` 交付路径），已推送不可改名（改名破坏交付路径与引用）；「按提交日命名」约定是否统一请业主确认。
6. **例行核查归属注记（复核 notLanded 尾项回应）**：轮 14 无独立例行核查节——本轮核查=分散逐条目实跑（--status×4/预检 git grep/gh api×6/fox_fetch×4/--collect-only 61/34/25/py `git diff --quiet`/守卫 pytest+script+ruff[本轮复核修复后补]），无 --doctor/gh run list/全量 pytest 之本轮专项实跑（统一门禁全绿系收尾交办陈述=脚本侧实跑）。归属请业主确认：若例行核查应为独立条目/报告专节（沿轮 11 报告例行核查节先例），下轮按框架项 5 单列落节。
