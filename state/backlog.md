# state/backlog.md — candidates, not committed

> Add ideas here during a sprint; evaluate at milestone boundaries. Do NOT interrupt the current
> task. See `WORKFLOW.md` §6 (freeze rules).
>
> 2026-09-21 轮 99 刷新：已完成项移入文末"已完成"区。owner-gated 研究项的权威清单在
> `tasks/active/TASK-RES-*.md`，此处只留指针。

## 开放候选

- **Phase B OOS panel.** `scripts/phase_b_run.py` predates the schema-2 OOS-persistence wiring;
  pass `oos_state` / `oos_base` to `save_run` + a solo B rerun so all 4 phases demo the fit charts.
  **S** task.（与 blockers 的 uv.lock sig 处置联动——先裁 sig 再跑 rerun。）
- **E2 build (LLM macro-causal, cutoff-controlled).** Blocked on TASK-STRAT owner decision.
  See `../docs/phase-e2-preregistration.md`, `../decisions/ADR-005-e2-underpowered-e3-forward-live.md`.
- **E3 forward-live launch.** The only POWERED zero-leak path; calendar-gated（9-30/10-31 影子窗，
  10-01 04:05 自动化已武装）。See `../docs/phase-e3-preregistration.md`.
- **Earnings as abstain / event-study event.** Zero-LLM abstention table (RD-08) covers
  FOMC/CPI/NFP/13D but NOT earnings; `earnings_8k_forward.py` exists so the PIT path is open.
  **BLOCKED until**: E3 headline HOLD lifted AND new owner-approved pre-registration/config
  (new event type = scope expansion; 7-gate; new ledger row). Never mutate B/C/D/E1. **M**.
- **SIC vintage.** SIC is current-snapshot (mild lookahead for reclassifiers); low priority
  (small effect). **M** task.
- **evals/cases golden fixtures.** Slot in once E3 forward-live produces commit/reveal fixtures.
- ~~**Slice 2 review LOW×5 cleanup（advisory）。**~~ **完成清账（10-05 轮 184）**：docstring 首跑注记
  ×3、structlog `forward_persist_real_ledger` warning、`persist_snapshot` DRY 均已在早前轮落地；
  最后一项 `keyfn = str.upper` 别名化简本轮落地（行为等价，forward 电池 EXIT=0）。

- ~~**i18n 字典按语言拆块（轮 201 候选）。**~~ **完成（10-06 轮 201，375064b19）**：每路由 -95KB；dict-zh 静态/dict-en 动态；audit+3 契约适配。

- **恢复道"仅重试软败步骤"策略（反思四 §一.3）。** 23:53 恢复道在 ok_committed 时 SKIP——软败步骤的
  数据最坏陈旧 24h+（如 GDELT 源缓存夜）。变更为"软败步骤选择性重跑"影响通道核心语义（幂等性/记账/
  push 边界），需 owner 对通道策略表态后专轮设计。**M**。

<!-- 以下五条=2026-11-12 iterate 轮 backlog-candidates-register 登记（研究面/代码级候选，
     全部不上施工：研究面须 mission 指名+预注册+config_committed，见各条触发条件） -->

- **purgedcv effective_n_trials / min_track_record_length（DSR n_trials 升级 + SR 最短跟踪记录）。**
  安装版 purgedcv 0.1.2 顶层已导出两函数名（2026-11-12 实测 `import purgedcv; dir()`；License MIT），
  能力在但语义属**研究面**（DSR/SPA 判定族=src/aionis/eval/ 面）。**触发条件：mission 明确指名研究面** +
  新预注册（N 计数口径随 config 冻结入 prereg 附录）+ `config_committed` ledger 行——三者缺一不上施工。
  来源：iterate 轮外向调研条目 2；与前沿吸收 #10（DSR 试验计数通缩+minTRL）同族。
- **langextract 结构化抽取辅助试点。** Apache-2.0（白名单内），但 extraction 面属研究管线
  （src/aionis/extraction/）——**试点限 tests/fixtures 标注层**（labeled fixture 合规域），绝不入真实
  抽取管线；扩至真实抽取须预注册 + mission 指名 + 新 ledger 行。来源：iterate 轮外向调研条目 3。
- **Harvey-Liu-Zhu t≥3.0 门槛入 docs/RESULTS.md（稳健性并列呈现）。** 多重检验视角与既有两尾预注册
  判定**并列呈现**候选，append-only 勘误语义，**不改判定门**（主检验=预注册两尾不变，HLZ 仅附录
  视角）。触发条件：业主对 RESULTS.md 呈现面点头。来源：iterate 轮外向调研条目 4。
- **fja05680/sp500 PIT 成员双源对照。** constituents_on 单源的双源审计候选（scripts/ 审计类，不改
  研究管线）；**只认 MIT 原仓**，fork/转载不认。**M**。触发条件：审计轮 mission 指名。来源：iterate
  轮外向调研条目 4。
- **Jev 代码级候选（{answer,p} 输出契约 + --propose 预测陈述字段 + Brier 式月末对账）。** 判别层输出
  附概率陈述、提案卡带预测字段、月末对账命中记录（裁决与两栏分析见
  `reports/audits/2026-11-12-iterate-round.md` Jev 章节）。**诚实边界**：GLM 概率未校准、仅路由用——
  不得作校准概率消费；月度小样本对账仅**记录性**校准，禁任何统计显著性声称。触发条件：mission 指名 +
  预注册（涉 eval 呈现面）；provider 红线不变（不接 Jev API/typesafe-sdk）。来源：iterate 轮 Jev 专题
  （backlog-candidates-register 条）。
  延伸索引⑦（2026-11-13 append，frontier-citation-anchors；仅引用不装包不接入）：arXiv:2611.11480
  「Beyond Ranking: Are Decision Models Calibrated Relevance Scorers?」（cs.IR 2026-11-08，
  fox_fetch 一手复核可达）实测 Jev 原生概率**过自信**（>0.9 分带仅 66% 相关、需 2 参数校准修复）——
  上方「GLM 概率未校准/对账仅记录性/禁显著性声称」诚实边界的独立第三方实证；不接 Jev
  API/typesafe-sdk，provider 红线不变。
  延伸索引⑧（2026-11-13 append，frontier-reading-index；阅读清单锚，不装任何条目不引任何包）：
  awesome-decision-models（github.com/AnotiaWang——hosted APIs/open-weight 模型/runtimes/SDKs/
  applications/benchmarks/papers 分节导航，System One/typed-decisions 域；GitHub API 一手复核
  license spdx=CC0-1.0、715★、pushed 2026-11-13 仍活跃）——按延伸索引① CC0 仅索引用途先例，
  登记为后续 Jev 生态扫描单一入口（在册① awesome-system-one/② awesome-jev 两清单外覆盖面
  最全）。**如实标注**：CC0-1.0 非白名单代码许可（MIT/Apache/BSD），仅限阅读清单域；清单内
  任何条目不得因入册本索引而获得装包资格，装包仍须 7-gate+白名单+业主点头。
  延伸索引⑨（2026-11-13 append，frontier-reading-index；两篇张力论文并列引用锚，不择优偏引）：
  arXiv:2611.12521「Can the Confidence and Decisions of System 1 Models Be Trusted?」
  （cs.LG 2026-11-09）实测 provider confidence=**闭式散度变换**（1−H(p)/ln K；Clef-27B 为
  normalized margin）而非经验准确率，且一请求捆多问引致跨问定向干扰（Tev1-0.8B 二值翻转
  11.7-22.4%）；arXiv:2611.15592「Small Heads, Strong Decisions」（cs.AI 2026-11-11）受控
  同协议重训五种 readout，称一 prompt 读全问与逐问精度**相当**（1.6× 推理加速）——两文对
  「多问捆绑」结论相反（任务域/模型不同），张力如实并列，不据任何一篇改在册协议。补强对象：
  上方「GLM 概率未校准/对账仅记录性/禁显著性声称」诚实边界（12521 系 ⑦ 过自信读数的机制侧
  补强）与 WATCHDOG 单问单发+预枚举设计（`scripts/monthly_review.py:1274-1281`）的独立第三方
  实证/反向佐证；两篇 abs 页本会话 fox_fetch 复核可达。**注记**：不据此对 GLM 三 provider 概率
  作任何校准拟合（n=1 月度 p 记录禁检测拟合在册红线，#15 同款口径；WATCHDOG 常量内
  「禁再校准拟合」措辞同源）。
  延伸索引⑩（2026-11-13 append，frontier-citation-anchors；纯引用锚，不跑分不装包不接入）：
  S1CogBench（arXiv:2611.00911「What System One Decision Models Can and Cannot Do on
  Cognitive Experiments」，cs.CL 2026-10-31，Dengzhe Hou/Kazunori D Yamada；repo=
  github.com/dengzhe-hou/S1CogBench，license spdx=MIT 白名单内，本会话 GitHub API
  复核一手、pushed 2026-11-13 仍活跃）四重外部印证（abs 页+README :46 本会话逐句复核）：
  ①「a fast, well-formed decision does not show that the model used the evidence」——
  **格式合规≠语义合规**，反泄漏核心关切的独立第三方表述；②「aggregate scores hide how
  decisions respond to conditions」——**总分藏条件响应**，逐条对账呈现（A5
  `reconcile_predictions` judgments/facts 分账，`scripts/monthly_review.py:978`）不总分管总
  口径的旁证；③ README :46 逐字：Python 3.12 将内建 float `sum()` 改补偿求和，27 mode 中
  6 个浮点末位漂移、复现 2026-10-26 CPU validation 须逐位回到 3.11——**H6 位一致+uv.lock
  钉版纪律的直接外部实证**（解释器小版本即破位一致，钉版非仪式）；④「speed comes mainly
  from answering without generation」——速度=不生成，判别/生成成本结构对照注记
  （`docs/ops-local-refresh.md:327`）同向印证。**边界注记**：跑分须接 Jev API=违 provider
  红线（池仅 GLM/SiliconFlow/ModelScope），repo 仅引用不克隆不装不跑；读数不构成对 GLM
  三 provider 概率的任何校准拟合动作（#15 同款口径）。
  延伸索引⑪（2026-11-13 append，frontier-citation-anchors；Apache-2.0 登记仅引用，不装插件
  不接入）：johantor/brain（github.com/johantor/brain，license spdx=Apache-2.0 白名单内，
  本会话 GitHub API 复核一手、pushed 2026-11-13 仍活跃）三原则与月度 reflexion/backlog 门禁
  同构（README 本会话逐行复核）：① shadow 起草+人工 keep/pin/forget（README :11-12「drafts
  lessons in shadow mode…you keep, pin or forget each one」）≡ backlog 候选区仅登记不动
  （登记≠采纳，人工门保留）；② 反射输入不存外部文本（:33「cannot plant text that a later
  reflection reads」防注入边界）≡ 引用面不进判定面在册口径；③ 每 reply 计一次 token
  （:30「each reply counted once, subagents included」）≡ per-call 用量记账纪律。
  **边界注记**：仅引用；不装插件不挂 hook；brain 系会话级常驻工具，与 Aionis「无后台长驻
  进程」红线结构性冲突，永不引入。
  延伸索引⑫（2026-11-13 append，frontier-citation-anchors；独立生态总目页登记为 Jev 生态
  扫描第四入口，仅引证不复用）：jevtypesafeai.com/ecosystem（页面自述「independent
  roundup, not official」、source of truth=typesafe.ai，本会话 fox_fetch 一手复核可达；在册
  ① awesome-system-one/② awesome-jev/⑧ awesome-decision-models 三清单外第四扫描入口，
  覆盖 MCP servers/浏览器扩展/CLI/routers/SDK/游戏/providers 网关）。引证两点：
  （a）context compaction 描述「verbatim, no lossy summary」与活文档取舍纪律（append-only
  原文留档、勘误不回改、禁有损摘要重写）同向；（b）jev-loop-detector 四态
  progress/repeating/stuck/escalate 与恢复道惯例同构（推进/重复/卡死/升级）。
  **边界注记**：页面无逐件许可声明，star 数与命令页方自述「approximate—check each repo
  before installing」；页内任何工具装包须逐件 7-gate+许可证白名单+业主点头，入册本索引不
  获得装包资格；页内 jgrep 系外向调研 medium 未圈入项，维持原判不新增。
  延伸索引⑬（2026-11-13 append，frontier-citation-anchors；仅引用零接入）：arXiv:2611.16321
  （决策信息集中中间层——纯架构效率研究；Aionis 系外部 API 消费者，provider 侧架构不可
  触碰、无接入面）。adaptation 口径：仅作 Jev 索引延伸登记（架构类目引用），仓库任何
  「中间层/信息集中」类改动均须 mission 指名+预注册，不入本索引射程。
  **边界注记**：仅引用零接入；零新依赖零 SDK 零框架；provider 红线不变。
  延伸索引⑭（2026-11-13 append，frontier-citation-anchors；仅引用零接入）：arXiv:2611.00496
  （typed 接口生产偏见审计口径）。adaptation 口径：与 bounded answer {answer,p} 固定契约
  同构——「固定形状输出→事后只读审计」纪律（parse_bounded_answer :1363/--verify-bounded
  面），只借审计口径不接入其工具链。
  **边界注记**：仅引用零接入；零新依赖零 SDK 零框架。
  延伸索引⑮（2026-11-13 append，frontier-citation-anchors；仅引用零接入）：arXiv:2611.09264
  （数字轻推可操纵 System One 判决的实证）。adaptation 口径：支持环1b 注入纪律——校准
  反馈只注入 facts only 统计+固定禁令字面（CALIBRATION_FEEDBACK_NOTE
  monthly_review.py:1427；prohibition≠disposition），数字呈现永不作诱导性轻推。
  **边界注记**：仅引用零接入；零新依赖零 SDK 零框架；呈现≠校准红线重申。
  延伸索引⑯（2026-11-13 append，frontier-citation-anchors；仅引用零接入）：arXiv:2611.01015
  （IJev，Jev 生态条目）——延伸索引登记；具体内容待引用时一手复核，本条不转述不装包。
  **边界注记**：仅引用零接入；零新依赖零 SDK 零框架。
  延伸索引⑰（2026-11-13 append，frontier-citation-anchors；仅引用零接入）：arXiv:2610.42148
  （Flide，Jev 生态条目）——延伸索引登记；具体内容待引用时一手复核，本条不转述不装包。
  **边界注记**：仅引用零接入；零新依赖零 SDK 零框架。
  CLE 参照登记（2026-11-13 append，frontier-citation-anchors）：arXiv:2610.33956（continual
  learning 评估）=飞轮验收口径参照（continual learning，运维面 A/B 设想，未开工）——运维面
  「带 active lessons vs 清空 lessons」月度对照设想（非研究面对照）；未开工只登记，启用须
  业主点名+独立 mission。
  延伸索引⑱（2026-11-14 append，frontier-citation-anchors；仅引用零接入）：arXiv:2610.38211
  （RainCheck，high）——BSS 相对 climatology 基线带 95% CI 的报告口径；泄漏感知评估与
  PurgedGroupKFold+embargo 立场第三方同构。adaptation 口径：环1a 校准聚合
  （calibration_bucket_summary :1059 五桶+Wilson 95% CI+mean Brier）报告语言参照——相对
  基线读数带 CI 不裸报点值；PurgedGroupKFold+embargo=在册研究面方法论，仅第三方印证零改动。
  **边界注记**：仅引用零接入；零新依赖零 SDK 零框架；研究面零改动。
  延伸索引⑲（2026-11-14 append，frontier-citation-anchors；仅引用零接入）：arXiv:2610.28979
  （Anytime-Valid，high）——月度连续监控须 anytime 校正+not-enough-data 数学。
  adaptation 口径：环1 月度连续对账（reconcile/Brier/Wilson 面）统计语言远期参照——连续
  监控读数须 anytime 校正、样本不足=如实 not-enough-data 不硬判；当前面零改动，启用须
  业主点名。**边界注记**：仅引用零接入；零新依赖零 SDK 零框架。
  延伸索引⑳（2026-11-14 append，frontier-citation-anchors；仅引用零接入）：arXiv:2609.14138
  （LIMBO，high）——回放非免费、注入须显式预算。adaptation 口径：环2/步 6 INSIGHT 注入
  预算口径锚——反哺行（校准事实入 lessons）占 INSIGHT 0-2 条额度中 1 条（runbook 步 6
  注记行同批落），lessons 重放不无限倾倒。**边界注记**：仅引用零接入；零新依赖零 SDK
  零框架。
  延伸索引㉑（2026-11-14 append，frontier-citation-anchors；仅引用零接入）：arXiv:2611.14465
  （One Curve，medium）——BSS 权重语义=better-than-chance 数学正身+桶级
  |桶均 p−桶命中率| 语言。adaptation 口径：环1a 桶表读数语言参照——桶级差距绝对值呈现；
  BSS 语义仅作理解参照，不作研究面度量改动。**边界注记**：仅引用零接入；零新依赖零 SDK
  零框架。
  延伸索引㉒（2026-11-14 append，frontier-citation-anchors；仅引用零接入）：arXiv:2606.15306
  （LatentGym，medium）——探索/利用分离=环3「注入≠利用」验收观察口径。adaptation
  口径：注入（lessons/insight 进 prompt）与利用（据此改 p/阈值）分离纪律第三方同构；
  A/B 启用须业主点名。**边界注记**：仅引用零接入；零新依赖零 SDK 零框架。
  延伸索引㉓（2026-11-14 append，frontier-citation-anchors；仅引用零接入）：arXiv:2406.07817
  （nci/scores，Apache-2.0——本轮调研唯一一手核实许可证合规仓库）——isotonic/分位桶+
  度量名词表。adaptation 口径：只借度量名词表与分桶口径（环1a 校准聚合语言参照），不装包
  不克隆。**边界注记**：仅引用零接入；零新依赖零 SDK 零框架；白名单内≠装包资格。
  延伸索引㉔（2026-11-14 append，frontier-citation-anchors；仅引用零接入）：arXiv:2610.29288
  （Time-Uniform Dependent CLT，low）——序列依赖 CI 稳健化远期方向，仅 backlog 登记。
  adaptation 口径：环1 序列依赖下 CI 稳健化远期参照，当前 Wilson 面零改动；启用须业主
  点名+独立 mission。**边界注记**：仅引用零接入；零新依赖零 SDK 零框架。
  延伸索引㉕（2026-11-14 append，frontier-citation-anchors；仅引用零接入，三源一位=论文+repo+
  官方博文）：Hindsight——arXiv:2512.12818「Hindsight is 20/20: Building Agent Memory that
  Retains, Recalls, and Reflects」（cs.CL 2025-12-14，abs 页本日 fox_fetch 一手复核可达；四逻辑
  网络 world facts/agent experiences/entity summaries/evolving beliefs 区分 evidence 与 inference、
  三操作 retain/recall/reflect）；repo=github.com/vectorize-io/hindsight（license spdx=MIT 白名单
  内，本日 GitHub API 复核 60917★、pushed 2026-11-13 活跃、未 archive）。三锚映射：①facts-beliefs
  分离 ≡ 呈现面 facts-only 统计与判断分层（环1b CALIBRATION_FEEDBACK_NOTE
  `monthly_review.py:1431` 本日实测；「呈现≠校准」）；②retain/recall/reflect 三操作 ≡ 三环
  聚合→注入→蒸馏（design 报告 §2）同构；③去重前置过滤（写前先查等价）≡ prop: 去重键+`event:`
  UPDATE(supersedes)/NONE 引用式接替（`monthly_review.py:1211` EVENT_OP_RE 本日实测）的写前
  语义。**边界注记**：Hindsight 系 20B 级 backbone 记忆架构，其权重/API=provider 红线（LLM 池仅
  GLM/SiliconFlow/ModelScope，MIT 合规≠接入资格）；若去重语义被点名借鉴，实现须**零 LLM 零
  嵌入**（确定性文本键比对，prop: 同款）；仅引用零接入；零新依赖零 SDK 零框架。
  延伸索引㉖（2026-11-14 append，frontier-citation-anchors；仅引用零接入）：github.com/
  tigerless-labs/agent-memory（license spdx=MIT 白名单内，本日 GitHub API 复核 4317★、pushed
  2026-11-12 活跃）。三映射（语义源=iterate 轮 12 调研一手核实）：①sleep-time 整理道（闲时离线
  整理，整理不在请求路径）≡ 晚间通道离线批处理对照（夜间整理、白天只读消费）；②Markdown 单一
  事实源 ≡ state/*.md 单一事实源纪律（handoff/current/backlog 不双轨不镜像）；③分级读取（按需
  分层加载）≡ night_package refs 一跳摘要分层读取（轮 128-续2）同构。**边界注记**：仅引用零
  接入；零新依赖零 SDK 零框架；不引入其任何服务/常驻组件（无后台长驻进程红线）。
  延伸索引㉗（2026-11-14 append，frontier-citation-anchors；仅引用零接入）：arXiv:2502.12110
  （A-MEM，memory evolution 更新优于追加）；repo=github.com/agiresearch/A-MEM（license spdx=MIT
  白名单内，本日 GitHub API 复核 1214★、**pushed 2025-12-12 起约 11 个月未更新——停更态如实
  注记**）。映射：新记忆触发旧记忆更新而非无限堆叠 ≡ 轮 128-续3 UPDATE(supersedes) 引用式接替
  （`docs/ops-local-refresh.md:386` lessons 块格式节）**成对闭环**——A-MEM 供「何时该更新」的
  语义正源，在册契约供「如何不回改地更新」（append-only 引用式标记，与 ledger 新行不覆盖同构）。
  **边界注记**：仅引用零接入；零新依赖零 SDK 零框架；repo 停更如实注记。
  延伸索引㉘（2026-11-14 append，frontier-citation-anchors；仅引用零接入）：github.com/searls/
  todo_or_die（license spdx=MIT 白名单内，本日 GitHub API 复核 361★、pushed 2026-07-15）——
  **逾期显式爆发+严格时间门**：TODO 带死线、到期未清即运行时显式报错，不让待办无声滑过。映射 ≡
  backlog 老化 deadman 开火（--propose 实弹 5 张先例，轮 128-续2）同族语义：逾期=显式信号非静默
  腐烂。**边界注记**：仅借语义零接入（Ruby gem 非本栈）；零新依赖零 SDK 零框架。
  延伸索引㉙（2026-11-14 append，frontier-citation-anchors；仅引用零接入）：evidentlyai/evidently
  （license spdx=Apache-2.0 白名单内，本日 GitHub API 复核 8062★、pushed 2026-09-29 起约 6 周
  未更新——停更态如实注记）——**reference-vs-current 两窗口呈现范式**：漂移/质量呈现用「参考窗
  vs 当前窗」并列对照，不裸报单窗点值。映射 ≡ 环1a 校准聚合（calibration_bucket_summary
  `monthly_review.py:1060` 本日实测）呈现语言参照：参照对象=基线/climatology（p̄、BS_base），
  当前对象=本月读数，两窗并列。**auto-Tests 自动派生阈值明确不采**（自动阈值=数据拟合，与
  n=1 月度 p 记录禁检测拟合在册红线冲突）。**边界注记**：仅借呈现范式零装包；零新依赖零 SDK
  零框架；研究面零改动。
  延伸索引㉚（2026-11-14 append，frontier-citation-anchors；仅引用零接入）：arXiv:2611.03928
  「Sequential auditing of connected forecast errors under partial observations」（cs.LG
  2026-11-02，abs 页本日 fox_fetch 一手复核可达）——**缺失 outcome 审计停止语义**：评估所需
  true outcome 部分缺失时，审计在「已观测标签足以判定」或「检索预算耗尽」处**显式停止**，缺失
  本身是一等审计事实而非可忽略噪声。远期参照 ≡ 当前 resolved=0 时环2 insight 降级（「本月无
  resolved 对账行，insight 步跳过」）与 L2 gate not-enough-data 三态的同族延伸。adaptation
  口径：远期参照仅登记，启用须业主点名。**边界注记**：仅引用零接入；零新依赖零 SDK 零框架；
  研究面零改动。
  延伸索引㉛（2026-11-14 append，frontier-citation-anchors；仅引用零接入，**真增量登记——写回
  契约已在册不重登**）：arXiv:2504.19413（Mem0 论文侧；mem0ai/mem0 Apache-2.0 四操作写回契约
  已在册=`docs/ops-local-refresh.md:386` lessons 块格式节[轮 128-续3]+reports/design/
  2026-11-11-super-agent-gen2.md:95，本日 grep 复核在册态[在册引用形=mem0ai/mem0 仓库名，论文
  ID 此前未入册]——同 ExpeL 2308.10144 先例不重复登记整源）。真增量仅**生成侧预检两语义**：
  ①无等价才 ADD（写前检索等价记忆，命中即不新增）；②信息量更大才 UPDATE（候选与在册等价但
  信息量更大才接替，否则维持）。映射 ≡ 在册 `event: NONE`（重复已录不重写）的**判据侧**正源
  ——何时判「等价/更优」；adaptation 口径：lesson 写回前确定性预检语义参照。**边界注记**：判据
  实现须**零 LLM 零嵌入**（确定性文本比对）；仅引用零接入；零新依赖零 SDK 零框架。
  延伸索引㉜（2026-11-14 append，frontier-citation-anchors；仅范式引用零代码复制，
  **license=null 如实注记**）：github.com/Cyrene963/hermes-patches（Hermes Agent
  社区补丁合集；本日 GitHub API 复核 203★/23 fork、pushed 2026-11-12 活跃、
  license=null——与轮 12 pitmon 无 LICENSE 拒收先例同判：代码零复制，唯业主点名
  做思路参考故入引用锚）。范式五要素（PATCHES.md 本日一手实读复核，行号为其仓内
  行号）：①五列卡——`| Patch | Surface | Purpose | Evidence | Rollback |`
  （PATCHES.md:28），每补丁一行五格：面/目的/证据/回滚缺一不可；②四级证据标签
  ——Verified working / Partially verified / Code present only / Risk
  （PATCHES.md:7-10），「存在≠生效、部分验证≠已验证」分层如实；③晋升六步门
  （PATCHES.md:102-110）——升至 Verified working 前六步全过，第 3 步
  positive-control（:108，证预期行为真的发生而非函数返回了东西）、第 4 步
  clean-install（:109，净装路径复现）；④HERMES_INDIVIDUAL_PATCH_ALLOWLIST
  消费者挑选（PATCHES.md:19，HERMES_APPLY_INDIVIDUAL_PATCHES=0 可全关）；
  ⑤幂等 apply——先 `git apply --check` 再应用（PATCHES.md:17）。映射 ≡
  ①证据四级分层同构报告「未跑如实注记」纪律（轮 12 报告先例）与环1b facts-only
  分层；②positive-control ≡ 负向钉先例（首版误扫禁令被红面抓获——证「禁令真
  拦得住」而非「测试跑过了」）；③`--check` 先行 ≡ H6 同 sig 重跑位一致（先验
  可应用性再动手）；④ALLOWLIST 挑选 ≡ 装包须业主点名纪律。chain-guard 辨明：
  scripts/hermes-patch-chain-guard.sh（PATCHES.md:65）marker 验证的是「补丁生效
  了」（行为面）而非「补丁打了」（文件面）；commits 频率画像=漂移是常态作业
  （PATCHES.md 开篇「reason about drift, rollback, and upstream merge state」）。
  ast-grep（github.com/ast-grep/ast-grep，license spdx=MIT 白名单内，本日 GitHub
  API 复核 16572★）声明式规则模式注记为**条目 18（runbook `:N` 行号锚→标题锚
  迁移）增强供证**——覆盖缺口实测成立（外向调研条目 1-4）：MD051 只验 markdown
  内 fragment 链接，不验跨文件 file:line 锚。**边界注记**：仅范式引用零代码复制
  零安装零接入；拒收项沿轮 12 先例入本轮报告不入 backlog；零新依赖零 SDK 零框架；
  研究面零改动。

## 前沿吸收（轮 127，2026-11-11；来源=reports/audits/2026-11-11-env-testpipeline-round.md §6b——两路前沿调研中 high 但 L 规模/存疑/触红线者，逐条含来源 URL）

> 实施前逐条过 7-gate（docs/data-intake-rubric.md）与许可证白名单（MIT/Apache/BSD）。

1. **哈希链账本 + 一次性 holdout 回执 + 门合取**（https://arxiv.org/abs/2611.06607；MIT 参考实现 github.com/henryzhangpku/autonomous-quant-researcher）——**触红线**：`runs/ledger.jsonl` 语义零改动、receipt 属 scripts/phase_*。
2. **动量倾斜归因预注册**（https://doi.org/10.1016/j.jfds.2026.100207；SSRN 7010050）——下一 phase 预注册，owner 研究决策。
3. **知识截止/结果感知新门**（https://www.ravenpack.com/blog/insights-and-limitations-in-stock-price-prediction-using-llms；arXiv:2401.03737）——需改 docs/data-intake-rubric.md，非运维轮可触碰面。
4. **purged-CV 第二实现一致性测试**（https://github.com/eslazarev/purged-cross-validation，MIT 64★）——**存疑**：PyPI 可安装性未验证；CPCV/PBO 仅诊断、不作主分割器。
5. **time-machine 时间桩 conftest**（https://adamj.eu/tech/2026/08/03/python-time-machine-o1-freezegun-on；MIT v3.6.0）——8 个 src 模块墙钟语义分批。
6. **pytest-randomly**（https://github.com/pytest-dev/pytest-randomly，MIT v5.1.0）——2430 用例随机序体检 + 豁免治理。
7. **pytest-xdist -n auto --dist loadfile + faulthandler_timeout=300**（https://docs.pytest.org/en/stable/explanation/flaky.html，MIT v3.8.0）——需 H6 位一致豁免组设计。
8. **抽取错误分类学人工审计**（https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6496861）——人工标注成本 L；审计集与 prompt 调整隔离。
9. **组合级 FDR 读数**（https://people.duke.edu/~charvey/Research/Published_Papers/P143_False_and_missed.pdf）——docs/RESULTS.md 报告层，不回溯改 α。
10. **DSR 试验计数通缩 + minTRL**（https://arxiv.org/html/2512.12924v1）——N 随 config 冻结，仅预注册附录。
11. **时序共形区间**（https://arxiv.org/html/2507.05470v1）——稳健性视角，不变更主检验。
12. **actionlint + zizmor 常驻静态校验**（https://github.com/rhysd/actionlint；https://github.com/zizmorcore/zizmor，均 MIT）——二进制未装未跑；如集成 doctor 需条件存在守卫，保守后置。
13. **act 本地 dry-run**（https://github.com/nektos/act，MIT）——解锁前预检工具，不入 repo 依赖。

### 2026-11-12 增补（轮 131-续，定夺框架条目 5；四条真增量候选——仅索引不装包，任何装包须业主点头；研究面若采纳照旧须预注册 + mission 指名）

> 四条与在册 #1-13、2026-11-12 backlog-candidates-register 五条（本文件 :38-57）、延伸索引④⑤⑥
> （:141-160）零重叠——本日实读复核；与 #11 时序共形区间不同族（变点检测≠区间估计）。
> 7-gate（docs/data-intake-rubric.md）与许可证白名单（MIT/Apache/BSD）照旧逐条过。

14. **uv lock --check（doctor 第 9 层候选，high）**——lockfile 与 pyproject 脱钩即报错，护 H6
    version-pinned（uv.lock）语义与 1308 限额续跑后环境一致性；uv 已是项目工具链**零新依赖零新许可证面**
    （来源锚：<https://docs.astral.sh/uv/reference/cli/>——前次调研 fox_fetch 全文核实
    --check/--locked/--frozen 语义，2026-11-12 fetch 复核页面可达；本地 `uv lock --help` 实测
    `--check`="Check if the lockfile is up-to-date"，`uv lock --check` 实跑 exit=0）。落点：
    `scripts/ops_local_refresh.py` `collect_layers()` :1263-1352——本日实读复核 L1-L8 八层，现无锁文件层。
15. **river PageHinkley 变点提示（medium）**——限审计/呈现面「给人看」的变点提示，**不入研究管线**；
    若将来触碰研究面（如 IC 序列变点）须预注册（github.com/online-ml/river，BSD-3-Clause——GitHub API
    已核实 6146★、2026-11-10 活跃）。红线注记：n=1 月度 p 记录**禁检测拟合**；min_instances 等
    量级参数须明示**不调参**。与 #11 时序共形区间不同族（变点检测≠区间估计）。
16. **duckdb 跨源 SQL 对账（medium）**——跨 parquet/CSV/JSON 源一次性 SQL 对账；使用形态限 `uvx`
    一次性 CLI——**不入 pyproject、不常驻进程**（github.com/duckdb/duckdb，MIT——已核实 43028★）。
17. **ty 类型检查（low）**——低 churn 模块试点**前须业主点头**；**不得入门禁**（gate 语义零改动）
    （github.com/astral-sh/ty，MIT——已核实）。

### 2026-11-13 增补（anchor-debt-cleanup 附带根治登记；一条中期候选——仅登记不迁移不装包，任何装包须业主点头）

18. **runbook `:N` 行号锚→标题锚迁移（medium）**——`docs/ops-local-refresh.md` 引用
    `scripts/monthly_review.py` 等的 `:N` 行号锚随代码顺移反复脱靶（根因=删行/加行顺移；
    同类漂移已连续多轮——轮 131-续四处括注刷新、轮 132 删 `PREDICTION_LINE_RE` 后 :978
    之后统一 −3、2026-11-13 本轮八行活锚实测刷新），中期候选=迁移为**标题/符号锚**
    （def 名/节标题/add_argument 旗标名）并配自动巡检：markdownlint MD051
    「Link fragments should be valid」（github.com/DavidAnson/markdownlint，MIT——
    2026-11-13 GitHub API 复核 spdx_id；Rules.md 规则名实测）与 remark-validate-links
    （github.com/remarkjs/remark-validate-links，MIT——同日 API 复核 spdx_id）。
    **仅登记不迁移不装包**；迁移施工须 mission 派单，任何装包须业主点头。

## 名词指认资料（Jev 指认规则；2026-11-12 轮 130-续入册，杜绝 JEPA 混读）

> 本区为名词指认参考，**非任务候选**——propose 引擎不解析本区（`backlog_open_candidates`
> 仅读「开放候选」节内 bullet，prop: 前缀标记扫描本区无命中；`scripts/monthly_review.py:697`
> 解析语义实读证实）。**Jev = TypeSafe 公司 AI System One 判别式决策模型**
> （discriminative decision model；2026-09-15 发布，RLCD 训练）；**与 LeCun 的
> JEPA（Joint-Embedding Predictive Architecture）无关**——两名词不得混读/互替。
> 裁决边界：协议级同构仅采两点（判别/生成分层、预测误差=改进信号），落点 docs+state
> （`docs/ops-local-refresh.md` 值班协议「判别层/生成层分层」小节 +
> `reports/audits/2026-11-12-iterate-round.md` Jev 章节）；「内部世界模型」叙事不采用
> （过度类比贴金）；**代码级 rejected**——无白名单轮子支撑（`docs/data-license-allowlist.md`
> grep 零命中）且接入 Jev API/typesafe-sdk 违 provider 红线（LLM pool =
> GLM/SiliconFlow/ModelScope ONLY，AGENTS.md）；代码级候选见同批
> backlog-candidates-register 条。
>
> **勘误（append-only，2026-11-12 复核）**：上方段内 `scripts/monthly_review.py:697`
> 行号过时——def `backlog_open_candidates` 行号实读 **:698**（2026-11-12 复核；
> :696-697 为空行）。
>
> **延伸阅读索引与同批指认（2026-11-12 append，仅索引不装条目）**：
> ① 阅读索引两清单（均 CC0-1.0，`docs/data-license-allowlist.md` ACCEPTED 表在册）：
> awesome-system-one（github.com/andyrewlee——System One 模型/agent/SDK/benchmark
> 总目）与 awesome-jev（github.com/KennethAshley——Jev 生态 410 条 19 类，评测类
> 含 Brier/ECE 校准条目）；**仅索引用途，不装任何条目、不引任何包**。
> ② Jeva null-aware 延伸研读：arXiv:2610.18773（Jeva: System One Models from
> First Principles，2026-10-13 提交，null-aware 为其四结构要求之首）；参考实现
> typesafe-sdk-python/js（官方仓，MIT）——**只读不引**（接入仍违 provider 红线）。
> ③ **Microsoft-Decision-1 实体指认**：微软决策评分模型（2026-10-09 官方 Command
> Line 博文发布，Qwen3.5-9B 后训练单遍判别决策模型）——与 JEPA 无关，同 Jev
> 指认规则防混读；其 Foundry API 接入与定价模式**不采**（provider 红线 +
> 无关本地运维）。
> ④ **lm-evaluation-harness 枚举打分先例**（github.com/EleutherAI/lm-evaluation-harness，
> MIT——2026-11-12 GitHub API 复核 spdx_id）：multiple_choice 任务类型=选择类任务
> 「枚举打分、零生成」的长期标准实践（logprobs/loglikelihood 打分路径），与
> bounded question 枚举协议同向（协议落点 docs/ops-local-refresh.md 值班协议
> 分层小节）。**限定注记（必录）**：logprobs/loglikelihood 路径在 GLM/
> SiliconFlow/ModelScope 三 provider 上**未验证、不可假定**；显式 {answer,p}
> 文本输出是多花 1-2 token 的稳妥等价物——Aionis 取文本输出路径，解析兜底不变。
> 仅索引不装条目不引包。
> ⑤ **RouteLLM 阈值校准边界**（github.com/lm-sys/RouteLLM，Apache-2.0——
> 2026-11-12 GitHub API 复核 spdx_id）：路由阈值校准需**代表性查询分布**——
> 外部印证 n=1 月度样本禁统计拟合的诚实边界，与本文件上方 2026-11-12 登记候选⑤
> （Jev 代码级候选）的诚实边界（:54-56：GLM 概率未校准、月度小样本对账仅记录性、
> 禁显著性声称）同向。仅索引不装条目不引包。
> ⑥ **「低置信选项反转重问」可选模式备忘**（来源=本索引① awesome-system-one
> 清单 FlexDM-LoRA 2.1 卡原文「re-reads low-confidence answers with options
> reversed」，2026-11-12 抓取复核）：对低置信 bounded 回答把选项取反后重问一次
> 作一致性校验——**待业主点头的可选模式，默认关闭**（重问=该子任务 token 翻倍，
> 且仍限月末单场会话内，不新增会话）；同清单 open-alternative-jev 卡载弱模型
> 选项序翻转敏感度警示（同题选项序翻转 72% vs 21%），故反转重问读数须按一致性
> 证据而非校准证据消费。未经业主点头不实施。

## Owner-gated（预注册级 GO 才可动；权威 spec 在 tasks/active/）

- **Strong-baseline ladder.** RES-01/02/03/10（momentum/FF5-cross-sectional/rank-label/LLM-eval）。
  FF5 另需数据准入（docs/data-intake-french-ff5.md）。
- **Economic-validity lens.** RES-04 next-open / RES-05 turnover-slippage / RES-06 liquidity-borrow /
  RES-07 delisting-capacity。
- **Zero-LLM ablation 扩展.** RES-09。
- **Gold set 后续阶段.** RES-08（stage 1 已冻结 e3-causal-gold-v1）。
- **P1-4 Track A 因子生成器.** 轮 59 裁决 DEFER 至 10 月末（单焦点纪律）。

## 已完成（自本清单销项，证据在 tasks/completed/ 或 state/current.md）

- ~~Horizon-robustness extension（h=10/h=42 已跑，B/C/D/E1 全 null 保持）~~（轮 ㉛ 审计发现已 DONE）。
- ~~SESOI/TOST + sequential gate~~ → AUD-07 + AUD-07B 完成（ADR-010 Amendment）。
- ~~Macro cumulative-preserve test [MEDIUM]~~ → ORCH-01 COMPLETE（8d19b28）。
- ~~LLM extractor evaluation 基建~~ → RD-04/05/06/07/08/11 + RES-10 rewrite 完成。
- ~~本地刷新通道/晚班 token 经济/GBK+NaN 修复~~ → 轮 89/96/97/98 运营化。
