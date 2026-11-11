# Super-Agent 二代施工清单（gen2）——四路证据综合决策报告（2026-11-11，轮 127 决策 / 轮 128 施工）

> 性质：方案综合决策员对四路深耕证据（文章复读落差镜头 / 轮子源码深挖 / 首轮落差盘点 /
> 自进化引擎设计）的取舍与映射，产出**可施工的二代清单**（§5 四条）。
> **红线重申（本报告与全部施工条目共同遵守）**：
> ① 研究管线（`src/aionis/**`、`scripts/phase_*`、`runs/ledger.jsonl` 语义）零改动；
> ② 许可证仅 MIT/Apache/BSD；③ 稳态 token 不增（`--propose` 零 LLM、批处理折叠净降、
> 不新增班次/常驻进程/依赖）；④ 不 force-push、不改写 `main` 历史；⑤ 存疑处保守
> （存疑项一律不入清单、只入 §7 待决区）；⑥ `.github/workflows/` 本轮不动（轮 127 刚加固+
> `tests/test_workflow_yaml_hygiene.py` 钉死，避免无谓 churn）。
> 可触碰面即任务书所列：`scripts/monthly_review.py`、`scripts/ops_local_refresh.py`
> （仅运维面函数）、`scripts/ops_evening_hook.py`、`tests/`（既有四套件+新守卫）、
> `docs/ops-local-refresh.md`、`state/{handoff,current,backlog}.md`、`reports/design/`（新报告）。
> **`docs/ops-skills/` 与 `AGENTS.md` 不在可触碰面**——轮子深挖两项技能库借入因此整体后置（§3）。

## 0. 本轮核验基线（决策员实跑，2026-11-11）

- 四套件基线：`uv run pytest tests/test_ops_fastpath_triage.py
  tests/test_monthly_review_watchdog.py tests/test_ops_deadman.py
  tests/test_monthly_review.py -q` → **82 个结果点全绿无 F/E/s**（17+23+15+27，
  与轮 127 勘误口径一致；pytest 9.1.1 无汇总尾行，逐点清点）。施工以此为绿色起点。
- 关键锚点复核（逐处 Read/grep）：`monthly_review.py` 无 `--propose`（grep 零命中，
  引擎 MVP 确为新代码）；`ops_evening_hook.py` 全文 99 行 grep weekly 零命中
  （落差缺口 3 属实）；`build_night_package`（ops_local_refresh.py:657-678）threads 桶
  为纯列表、refs 五条纯路径（Thread ID/折叠/一跳摘要三缺口属实）；
  `latest_lessons_block`（monthly_review.py:657-668）只回看最新一块（跨月聚合缺口属实）；
  lessons 块头注释（:693-697）只述协议来源、无计划形契约（Delta ① 属实）；
  `render_reflexion_section`（:721-748）无 evidence 行（Delta ② 属实）；
  `scripts/orchestrate_dispatch.py` 存在且 `--task <tasks/active/TASK.md> --lane
  executor|verifier|…`（:192-199，实读 CLI 参数）+ `tasks/templates/DISPATCH-CONTRACT.md`
  + `tasks/{active,completed,rejected}/` 三区俱在（裁决门链条是真实管线，非注释装饰）；
  `runs/ledger.jsonl` 71 行（wc -l 实测，与轮 126「真实 71 行账本」一致）；
  `state/handoff.md` 最新条目=轮 127-续（:2918）→ **下一轮次=128**；
  `.github/workflows/vintage-probe.yml:74` 实读 `secrets.LLM_MODEL || 'glm-4.7-flash'`
  （任务单勘误属实：LLM_MODEL 错配**已修复非延后**，从待决区除名）；
  `.github/workflows/publish-site.yml:46`（pnpm/action-setup@b906aff # v4）与
  `:50`（actions/setup-node@49933ea # v4）node20 残余属实（留在钥匙区不动）。

## 1. 首轮五件套兑现表（round1Landed 复核）

| 首轮交付物 | 状态 | 本轮复核证据 |
|---|---|---|
| design-report-verdict | **已落地** | `reports/design/2026-11-11-super-agent-integration.md` 存在（215 行，本轮全文复读）：§1 laneFailing=false（:10-18）、§5 钥匙区三条（:195-201）、§6 核验清单（:203-215） |
| ops-failure-matrix-cadence | **已落地** | `docs/ops-local-refresh.md:184-247`：Fast Path 三分类表（:193-211）、处置矩阵六行（:213-222）、四档节奏表（:224-231）、super-agent 三映射含投机执行红线（:233-247） |
| nightly-fastpath-triage | **已落地** | `ops_local_refresh.py`：classify_run_row（:522-540）、_gh_run_rows/_gh_jobs_signature 只读探针（:555-609）、triage_ci/triage_state（:612-654）、build_night_package（:657-678）、do_run 成败两路径写包（:953/:961）、--triage CLI（:1294）；`ops_evening_hook.py:69` SKIP 路径零网络刷新包 |
| review-watchdog-reflexion | **已落地** | `monthly_review.py`：WATCHDOG_WORKFLOWS 恰 7（:405-408）、classify_workflow（:439-467）、ledger_spot_check（:470-519）、spin_detection（:522-562）、run_weekly（:565-637，billing 归并 :593-599）、Reflexion 循环（:640-748）、CLI（:772-786） |
| lane-marker-deadman | **已落地** | `ops_local_refresh.py`：marker_deadman（:1128）、collect_layers/doctor 八层（:1166/:1255）；远端镜像 staleness-check.yml（VERIFICATION-PENDING 如实标注，解锁日首跑核验——§7） |

首轮遗留的**闭环缺口**（落差盘点七条 cadenceGaps）不由本表掩盖：其中缺口 1/2/3/6
（复盘不回流 backlog、backlog 无重估、--weekly 无固定载体、改进提案无固定入口）
正是 §4 引擎 MVP 的存在理由；缺口 4（lessons 首块未写入）是时间事实（2026-11 月底
23:35 会话首次真实执行），§5 条目 4 保证首块落地即带正确契约；缺口 5（远端半边
verification-pending）与缺口 7（钥匙区盯守）均系业主钥匙/事件门，§7 不动。

## 2. 概念落差表（landed / partial / untouched 全列 + 翻案裁决）

| 概念（出处） | 首轮态 | gen2 裁决 | 承接条目 |
|---|---|---|---|
| Router/Worker 双层分工（文1/2/3） | landed | 维持；轮 128 handoff 记「本轮 Router 未亲自施工」自证行（纪律→可审计事实） | 条目 1（记录规范） |
| 事件驱动两级过滤 Fast/Slow Path（文1/4） | landed | 无新施工；唯一收尾=12-03 vintage 首跑复验后清 code-defect 桶（事件门，§7） | — |
| Watchdog 独立控制回路（文1/2） | landed | 工程侧无待办；解锁日首跑核验 staleness marker-deadman job（远端半边唯一未验项，§7） | — |
| Inline & Spill 上下文卫生（文1/2/4） | landed | 维持「月报/ADR/设计报告路径引用不内联」准则 | — |
| 异步任务链（文2/3） | landed | 维持零新框架判定 | — |
| **Thread 稳定 ID 归组**（文1/4） | partial | **施工**：night_package threads 桶赋稳定 ID，handoff 轮次/月评引用同款 ID | **条目 2 + 条目 1** |
| **批处理 Batching**（文1/4） | partial | **施工**：platform-failure 桶折叠计数 N× 一行，夜报 token 净降 | **条目 2** |
| **链式召回 Chain of Recall**（文1/4） | partial | **施工**：refs 条目「路径+一句话最新状态」一跳摘要 | **条目 2** |
| 投机执行（文1/2/4） | partial（全量不采纳） | **窄域翻案成立但本轮不收编**：零 LLM 确定性预草（handoff_draft.md）落在
runbook :244 红线开门的形态内；因 rounds 预算克制（当日已两次触顶）+「少而实」，
记为 §7 后续候选，不占本轮条目 | —（§7 候选） |
| Watchdog「模型判断目标偏离」半边（文1） | partial | **施工**：月末 lessons 会话加有界问题（spin/persistent 是否原地打转，一行结论），
不新增班次 | **条目 4** |
| 多对多订阅冲突可见性（文4） | untouched | 不入本轮（支撑强度次于三个 partial）；-wj lane 漂移只读检查记 §7 后续候选 | —（§7 候选） |
| 文章4 增量机制入册（文4） | untouched（正文已证可读） | **入册在本报告**（§3/§2 即勘误记录）；对首轮报告 §2 的 in-place 追加注
超出本轮可触碰面（`reports/design/`（新报告）），列 §7 待触碰面点头项 | —（§7） |

**翻案裁决记录**（勘误凭据=本报告，非 in-place 改首轮报告）：
1. **文章4「不引用」→ 翻案为「可引用、参与判定」**：首轮因微信验证拦截页标 partial
   （integration.md:127-134）；复读实证正文完全可读（fox_fetch 全文 + 轮 127-续
   runbook :238 复核实测 curl HTTP 200/js_content×18）。其增量（Thread 多对多、
   投机执行=「备好草稿你过目即发」、批处理 Prefill 并行）正是条目 2/§7 候选的出处。
2. **投机执行「全量不采纳」→ 窄域子形态翻案**（零 token 确定性预草值得做），
   但本轮不落地（预算克制），见上行表。
3. **Reflexion「仅借鉴不实现」→ 事实翻案待追认**：轮 126-续3（handoff.md:2915）
   已在 ops 层落地教训循环（协议借 noahshinn/reflexion MIT，只借协议不装包）。
   首轮 :153 的「与研究证伪纪律冲突」顾虑只适用于研究层自我进化；ops 层教训循环
   与研究证伪纪律无交集。研究层仍禁，运维层已采纳——以本行追认，§3 表同。
4. **SEAL 仓址勘误**：官仓=Continual-Intelligence/SEAL（MIT，1880★），mit-han-lab
   非 SEAL 作者仓（404）；后续引用一律用前者（§3）。

## 3. 轮子深挖采纳表（borrow / adopt / reject）

| 轮子 | 许可证（深挖 gh api 实测） | 裁决 | 承接 |
|---|---|---|---|
| noahshinn/Reflexion | MIT（3416★，stale 非 archived） | **borrow-protocol，本轮施工**：Delta ① 计划形契约头（prompts.py:113 移植进 lessons 块头）+ Delta ② evidence: 行（原始轨迹的 Inline/Spill 化） | **条目 4** |
| mem0ai/mem0 | Apache-2.0（68777★，活跃） | **borrow-protocol，本轮施工**：仅取四操作裁决分类学（ADD/UPDATE/DELETE/NONE + 同义→NONE），跨月教训去重/接替=引用式标记；本体（向量库+服务栈）维持首轮拒绝 | **条目 4** |
| mineDojo/Voyager | MIT（7320★） | **borrow-protocol，裁决入册、施工后置**：技能库协议（验证门=真实修好≥2 次才升格、命名冲突版本化=append-only 同构、纯规则签名匹配不引 embedding）成立，但载体 `docs/ops-skills/*.md` 与 `AGENTS.md` 指针行**不在本轮可触碰面**——整体列 §7 后续候选（含 AI 资源落点：从 handoff 轮 118/126、5a1075f650、轮 244/245 抽初稿） | —（§7 候选） |
| OpenHands/OpenHands | MIT（93168★，活跃） | **borrow-protocol，裁决入册、施工后置**：frontmatter 三键格式层（name/description/triggers）与 Voyager 共用载体；同样卡在可触碰面 | —（§7 候选，与 Voyager 同批） |
| Continual-Intelligence/SEAL | MIT（1880★） | **reject 维持并加码**：机制域=RL 自编辑权重，Aionis 无训练面；协议层抽象（改写→验证→固化）已有原生等价且更严（config_committed-BEFORE-result+ADR+处置矩阵）；源码核验后连协议借鉴价值也归零。产出仅仓址勘误（§2 翻案 4） | — |
| letta-ai/letta | Apache-2.0（复核） | **reject 维持**：`letta server` 常驻服务+外置状态存储，与 mem0 同类拒绝；不占 pick 名额 | — |
| **adopt-dep** | — | **本轮零新依赖**（无任何 adopt-dep）：全部借入均为协议/模板/规则级，零包、零服务、零进程。`uv.lock`/`pyproject.toml` 不动 | — |

## 4. 自进化引擎 MVP 设计（signal → audit → proposal → 业主裁决门 → 落地 → 验证 → 沉淀）

**定位**：运维/开发层自进化引擎，研究管线零触碰。Aionis 不缺审计、不缺沉淀，缺的是
中间两环：**「审计发现→结构化提案」**与**「提案→落地→验证的闭环追踪」**。引擎=
在 `monthly_review.py` 上加一个 `--propose` 模式把既有六环串成循环，**不新建任何
并行机制、不新增任何 LLM 调用点**。

**输入信号（全部已有，零新采集）**：
1. 夜报 SUMMARY（`monthly_review.py:99-140` 已解析）+ `night_package.json`
   （`ops_local_refresh.py:660-678`——条目 2 后带 Thread 稳定 ID）；
2. doctor 八层（`ops_local_refresh.py:1166-1254`，L7 site-repo drift=billing 盲区）；
3. `--weekly` 三查（工作流分诊 :405-467 / ledger 抽查 :470-519 / spin :522-562）；
4. 月度确定性指标（`lesson_seeds` :705-718：persistent_soft_fails/missing_weekdays/
   spin_findings/push_only——条目 4 后加 watchdog 有界问题键）；
5. backlog 老化（`state/backlog.md` 候选区条目 >90 天未动）。

**循环六环与裁决门图**：

```
夜报包(--triage, 带thread:ID) ─┐
doctor 八层(含 L7 billing 盲区) ─┤
--weekly 三查(分诊/ledger/spin) ─┼→ ① 审计（既有，零新采集）
月度 lesson_seeds(确定性事实)  ─┤        │
backlog 候选区老化扫描         ─┘        ▼
                              ② --propose 确定性规则表（零 LLM，条目 3）
                                 信号×阈值 → 提案卡片(S/M/L) + 证据指针
                                 (run.log 行/工作流名/doctor 层/thread:ID)
                                 + 去重键；同键已提案→输出「时间戳刷新指令」
                                          │  卡片 stdout/--out（引擎不写 backlog）
                                          ▼
                          人工/月末会话粘贴 → state/backlog.md 候选区
                          （沿用「candidates, not committed」头部纪律）
                                          │
                        ══════ ③ 业主裁决门（不可绕过，真实关卡）══════
                        里程碑边界（WORKFLOW §6）accept / defer / reject：
                        accept → tasks/active/<TASK>.md（RD-01 契约）
                        reject → tasks/rejected/；defer → 留候选区
                                          │ accept
                                          ▼
                        orchestrate_dispatch.py --task <TASK> --lane
                        executor（scripts/orchestrate_dispatch.py:192-199，
                        既有派发器，DISPATCH-CONTRACT 模板既有）
                                          │
                        ④ Engineer 单任务施工（AGENTS.md 边界：不扩 scope）
                                          │
                        ⑤ 验证 = pytest+ruff 全绿 + doctor/--weekly 复检
                           + 新查「提案闭环对账」：提案卡→tasks/ 状态→
                           completed 证据链一致性（并入 --weekly 一节，
                           与 ledger_spot_check 同款只读风格）
                           attempt-cap：同提案施工连续 2 轮验证失败
                           → 卡片标 BLOCKED 呈报（对齐 AGENTS.md
                           「2 failed fix rounds → escalate」，不无限迭代）
                                          │
                        ⑥ 沉淀 = --append-lessons-from append-only 写回
                           handoff（轮 126 既有；条目 4 后带 event 裁决行）
                                          └→ 注入下一循环（handoff read-first）
```

**守护**（引擎设计全文的五条 + 本轮收紧一条）：
1. 反泄漏红线：引擎整体在 ops/docs lane；提案内容若涉研究面（新数据源/新事件类/α 变更）
   → 卡片强制标注「7-gate+预注册+新 ledger 行+业主研究门」，引擎只呈报不执行；
   display-only 红线（workers/prices）同理。
2. token 预算上限：`--propose` 确定性规则、零 LLM；全引擎唯一 LLM 面维持既有两班
   （23:35 夜报单会话 + 月末复盘会话）——这是排除 ADAS/OpenEvolve 式进化搜索的直接理由。
3. attempt-cap：2 轮失败→BLOCKED 呈报，不无限迭代（既有纪律的卡片化）。
4. 业主裁决门不可绕过：**本轮收紧**——引擎对 `state/backlog.md` **只读**
   （原设计的「已提案→自动更新时间戳」降级为输出刷新指令，由月末会话/人工执行）；
   引擎无 git push、无 ledger 写、无 frozen config 触碰权限。
5. 幂等与去重：同信号+同规则已提案 → 输出刷新指令而非重复卡片，杜绝提案洪水。
6. 无新进程/新班次/新调度：`--propose` 由月末会话前确定性执行（四档节奏表写明，条目 1）。

**MVP 边界**：IN = `--propose`（5 类信号×规则表、stdout/--out、去重）+ 提案闭环对账节
并入 `--weekly` + `--weekly` 默认落盘锚点（治落差缺口 3 的「exit 1 无落盘可追溯」）
+ hermetic 测试（规则映射/去重/边界：无信号时零提案）。OUT（明确不做）= 自动施工/
自动提交、LLM 生成提案、新调度班次或常驻进程、研究面改动、ADAS/OpenEvolve 式架构搜索、
mem0/letta 类外置记忆。

## 5. gen2 施工清单（4 条；文档在前、代码在后；执行顺序即列表顺序）

### 条目 1（S，docs）`ops-cadence-gen2-wiring` — 四档节奏表接入 gen2 与引擎 + handoff 轮次记录规范

- **为什么**：落差缺口 1/3/6（月度产出不回流 backlog、--weekly 无固定触发载体与落盘锚点、
  改进提案无固定入口）+ 决策框架第 2 点——机制必须长在既有节奏里，不长新班次。
- **做什么**：`docs/ops-local-refresh.md` 四档节奏表（:224-231）更新——
  ① 每周档写明固定载体=每周五晚 23:35 夜报班前置确定性步 `--weekly`（零 LLM、exit 码
  进夜报正文；默认落盘锚点由条目 3 的代码默认值承载）+ 夜报班提示词模板补一行的说明
  （ZCode 工作区自动化配置非仓库文件，工程侧零代码）；
  ② 每月档写明 `--propose` 前置步（确定性提案，产物人工/月末会话粘贴 backlog 候选区）
  + 月末会话对四档机制本身的有界复盘问题（与条目 4 watchdog 问题同款形态）；
  ③ handoff 轮次记录规范：轮次条目引用 thread: 稳定 ID 续写（thread:ci-red /
  thread:guard-fail / thread:platform-billing / thread:ledger-anomaly / thread:spin），
  把「按类续写」从人工纪律变成机器可查；④ 稳态 token 预算声明入册
  （引擎跑在既有班次内、折叠净降、零新班次）。
- **touchpoints**：`docs/ops-local-refresh.md`（:224-231 节奏表 + :233-247 行为准则节
  补 thread:ID 规范）；`state/current.md` + `state/handoff.md`（轮 128 收尾记录，DoD 惯例）。
- **验收**：节奏表四档各条有载体与责任面；grep 本文件 thread: 五 ID 在册。

### 条目 2（S，code）`night-package-threading` — Thread 稳定 ID + platform-failure 折叠 + refs 一跳摘要

- **为什么**：复读 partial 三项（文1/4），同一函数面；Thread ID=条目 3 引擎提案去重键的
  基底；折叠直接降稳态 token（批处理分摊推理的 Aionis 对应）；refs 一跳=月末会话
  少一次工具往返（链式召回）。
- **做什么**：`ops_local_refresh.py` `triage_state`（:631-654）输出升维——platform 桶
  折叠为单行计数（`N× platform-failure → §5 钥匙区`，不再逐 workflow 列 ci: 行）；
  code/infra 桶条目挂 thread ID（`thread:ci-red:<wf>` / `thread:guard-fail:<step>`）；
  `build_night_package`（:657-678）refs 五条从纯路径升级为「路径+一句话最新状态」
  （monthly_reports 带上月 SUMMARY 一行、design_report 带本 gen2 报告一行——
  lessons 块的 latest_lessons_block 引用上月块已是同款，补齐即闭环）。
- **touchpoints**：`scripts/ops_local_refresh.py`（triage_state/build_night_package
  两个运维面函数）；`tests/test_ops_fastpath_triage.py`（:129-141 现有形状 pin 扩展：
  threads 带 ID、platform 折叠行、refs{path,status} 形状断言）。
- **验收**：新套件绿；`--triage` 对当前真实 marker 实弹输出形状与 persisted 一致。

### 条目 3（M，code）`propose-engine-mvp` — monthly_review.py --propose + --weekly 闭环对账（引擎六环的 ②⑤ 环）

- **为什么**：§4 全文；引擎是四路证据共同指向的最大增量（落差缺口 1/2/6 的机制解），
  且只增强 `monthly_review.py` 既有面、零新系统。
- **做什么**：① `--propose` 模式：五类信号×确定性规则表→提案卡片（S/M/L+证据指针
  +thread:ID 去重键；规则示例：spin 命中→「诊断 X 步骤连败根因」；L7/≥2 平台秒红→
  「billing 解锁后 runbook 项」只呈报不催办；persistent≥3 晚→「源冗余剧本核对」；
  backlog 候选 >90 天→「里程碑边界再裁决或销项」；--weekly findings→对应卡片）；
  产物 stdout/--out；对 backlog 候选区**只读**去重（已提案→刷新指令）。② `run_weekly`
  （:565-637）新增「提案闭环对账」节（提案卡→tasks/ 状态→completed 证据链一致性，
  只读、ledger_spot_check 同款风格）。③ `--weekly` 默认落盘锚点
  `runs/ops_local_refresh/<date>/weekly_watchdog.md`（--out 可覆盖；治「exit 1 无默认
  落盘」缺口）。④ research 面提案卡片强制标注「7-gate+预注册+新 ledger 行+业主研究门」。
- **touchpoints**：`scripts/monthly_review.py`（--propose + run_weekly 对账节 + CLI）；
  `tests/test_monthly_review_watchdog.py` 或新 `tests/test_monthly_review_propose.py`
  （规则映射/去重/无信号零提案/闭环对账节断言，注入式 fixture 照 :27-44 桩模式）。
- **验收**：hermetic 新测试绿；`--propose` 对真实仓库实弹一次（当前真实态应产出
  billing 钥匙区只呈报卡 + vintage code-defect 桶清账提醒卡，零自动写）。

### 条目 4（M，code）`lessons-contract-upgrade` — lessons 块契约升级（Reflexion Delta①② + mem0 四操作 + Watchdog 有界问题）

- **为什么**：轮子深挖两个 borrow 的落点 + 复读 Watchdog 模型半边 + 落差缺口 4——
  2026-11 月底首块写入前把契约钉对，避免首块即带旧格式。零依赖（MIT/Apache 协议借入）。
- **做什么**：① `append_lessons` 头注释（monthly_review.py:693-697）加计划形契约句
  （Reflexion prompts.py:113 移植：教训必须是可执行动作计划「下次 X 触发时做 Y」，
  非事件描述）；② 块模板约定 `event:` 行（mem0 四操作：ADD / UPDATE(supersedes
  month=YYYY-MM#条目) / DELETE(voids month=…) / NONE(重复已录)——append-only 语义下
  UPDATE/DELETE 均为引用式标记，不改旧块字节，与 ledger「新行不覆盖」同构）
  + `evidence:` 行（指向 run.log/审计报告的路径引用，附录式不回填历史块）；
  ③ `latest_lessons_block`（:657-668）扩展为「活跃教训聚合视图」=最新块+未被
  supersede/void 的历史条目（~40 行），替代单块回看；④ `lesson_seeds`（:705-718）
  加 watchdog 有界问题键 + `render_reflexion_section`（:721-748）渲染一行
  （「spin/persistent 是否原地打转或偏离值班目标？」供月末会话一行结论），
  零新增班次；⑤ `--lessons` 会话提示词指引一句（四操作契约+计划形文体）。
- **touchpoints**：`scripts/monthly_review.py`；`tests/test_monthly_review_watchdog.py`
  （多月块 fixture：ADD/UPDATE/DELETE/NONE 各一断言 + 聚合视图断言）；
  `docs/ops-local-refresh.md`（lessons 块格式节一小段，与条目 1 同文件原子落）。
- **验收**：新测试绿；对真实 handoff（尚无 lessons 块）聚合视图=空且不误报。

## 6. 长周期维护安排（决策框架第 2 点）

- **四档接线**（条目 1 落地后）：晚间=分诊+夜报（唯一稳态 LLM 会话，夜报包带 Thread ID
  与折叠行）；每周=周五 `--weekly`（含提案闭环对账节+默认落盘锚点）；每月=`--propose`
  前置 → 月末会话（lessons 有界问题+四操作裁决草案，业主终审）→ 人工粘贴 backlog；
  值班=钥匙区盯守（§7 不动）。
- **稳态 token 预算声明**：LLM 调用面维持既有两班不变（23:35 夜报单会话 + 月末复盘
  会话）；`--propose`/`--weekly`/对账/折叠全部零 LLM；platform 折叠使夜报上下文净降。
  引擎循环「永不停止」≠自主无限制——每环写权限止于候选文件与 state 记录。
- **handoff 轮次规范**：轮 128 起条目引用 thread: ID 续写；`--append-lessons-from`
  首块（2026-11 月底）带条目 4 契约；backlog 候选区提案条目与 tasks/ 三区状态由
  每周对账节持续核对，>90 天未动自动出再裁决提案（backlog 的 deadman，治缺口 2）。

## 7. 待业主钥匙区（只列不动）与本轮不收编项

**待业主钥匙区**（全部维持现状，工程侧零代办）：
1. GitHub billing 解锁 #2（integration.md:199；Tests 13 连红+publish 4 红+staleness 2 红
   全零步签名；解锁后按 handoff 轮 125 顺序重跑滞留红+首验清单
   audits/2026-11-11-env-testpipeline-round.md:86-90）。
2. publish-site 冻结通道真推许可（integration.md:200；`ops_freeze_deploy.py` dry-run
   全过待点头）。
3. -wj 账本孤儿 2 行裁决（integration.md:201；归并/弃置均不可逆）。
4. publish-site.yml:46/:50 node20 钉点重钉授权（本轮实测仍在：pnpm@b906aff # v4 /
   setup-node@49933ea # v4；「不修则解锁后首跑必红」定性不变——本报告 §0 复核）。
5. deploy-pages.yml 删除案点头（DORMANT 补钉不删文件，维持保守）。
6. AGENTS.md DoD 与「环境观察型条件 skip」字面张力（round-59 既定调和形态，非本轮面）。

**事件门（时间未到，不动）**：vintage-probe 2026-12-03 06:23 UTC 首跑复验
（model=glm-4.7-flash + status=stable）；staleness marker-deadman job 解锁日首跑核验。

**本轮不收编的后续候选**（记录在案，待后续轮/触碰面点头，均非业主钥匙）：
- 零 LLM 确定性预草 `runs/ops_local_refresh/<date>/handoff_draft.md`（投机执行窄域
  翻案形态；runbook :244 红线本已开门；23:35 夜报班从 SUMMARY/marker/threads 模板生成）；
- -wj lane 漂移只读检查（`git log main..feat/local-refresh-sweep --oneline` 计数+末次
  提交日+分叉点，进 --weekly；「对方 lane 做了什么」自动呈报，为钥匙区 3 提供实时依据）；
- Voyager+OpenHands 技能库 `docs/ops-skills/*.md`（载体+AGENTS.md 指针行不在本轮
  可触碰面；AI 资源落点：handoff 轮 118/126、5a1075f650、轮 244/245 历史抽取初稿，
  人工核对证据链接后入库）；
- 对首轮报告 integration.md 的三处 in-place 勘误/追认注（§2 翻案 1/3 与文章4 勘误注；
  append-only，需触碰面点头——本轮以本 gen2 报告为勘误凭据）。

## 8. 施工顺序、提交规范与 handoff 轮 128

- **顺序**：条目 1（docs，晚间通道运行风险零）→ 条目 2（基底，供条目 3 消费）→
  条目 3（引擎）→ 条目 4（lessons，独立可后置）。若当日 token 触顶：条目 1+2 为
  必落核心，条目 3/4 可顺延为 128-续/128-续2，以本报告为权威清单，不重开会商。
- **提交规范**：Conventional Commits 原子分批——`docs(ops): ...`（条目 1）/
  `feat(ops): ...`（条目 2）/`feat(ops): ...`（条目 3）/`feat(ops): ...`（条目 4）+
  收尾 `docs(state): ...`（current+handoff 轮 128）。每条独立过 pytest（相关面）+
  ruff；不 `git add -f`、不提交 data/parquet/.env、不 force-push。
- **handoff 轮次**：下一轮次=**128**（本轮复核 handoff.md 最新条目=轮 127-续 :2918；
  施工员开工时自行核对顺延，若期间有他会话插入则顺延为 129 并在 handoff 注明）。
- **DoD**：四条验收全过 + state 双文件更新 + 无 TODO/skip/stub 残留 + 0 ledger 写/
  0 frozen/0 OOS + 无新增班次/进程/依赖。

## 9. 边界声明

本报告为决策 lane 文档：0 ledger 写、0 frozen config、0 OOS 触碰、0 依赖变更；
未运行任何研究管线命令；全部代码证据来自本轮只读复核（§0）。文章复读/轮子深挖/
落差盘点/引擎设计四路材料由任务书给定，本报告只做取舍与映射，未新增无支撑想法。
