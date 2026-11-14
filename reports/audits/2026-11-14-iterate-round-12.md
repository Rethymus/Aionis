# iterate 轮 12 交付报告（2026-11-14；五条目：frontier-citation-anchors ㉕-㉛ / anchor-errata-batch / overdue-outcome-watch / feedback-dedup-contract / cross-month-evolution）

> 轮次=handoff 轮 142-146（自轮 141 顺延，核对最新号条款）。**发布失败复核（本报告即补写）**：
> 首次收尾后本文件缺失且零 git 历史（`ls` No such file + `git log --all` 零输出，本补写会话
> 实测）——与轮 10 报告同款成因（轮 139 块在册先例：发布失败=文件缺失/零 git 历史→本批
> 补写）；轮 12 收尾会话已在 handoff 轮 142-146 块与 current 如实注记「轮 12 报告尚未成稿
> 待后续条目」，非静默丢失。本报告全部事实取自五条目施工会话与收尾会话的一手记录。

## 一、例行核查（施工+收尾会话实跑清单）

- `--status`：动工前后每条目前后均 ok_committed（95a841a9e3、2026-11-13T19:26:55 收工、
  pushed、非 running）——晚间通道全程未运行，代码条目时点前提满足。
- `git status`：动工时 main==origin/main 零领先落后、树净；收尾后复验同态。
- `uv run ruff check`（全仓）：All checks passed（每代码条目一轮+收尾复跑，共 4 次）。
- 三套件 `uv run pytest -q tests/test_monthly_review.py tests/test_monthly_review_propose.py
  tests/test_monthly_review_watchdog.py`：每代码条目后实跑，终态 **exit=0 [100%] 120 用例**
  （monthly 61 / propose 34 / watchdog 25）。
- `--weekly` / `--lessons --month 2026-11` 实弹：rc=0（双零账本→三新呈现面全诚实缺省，
  见 §八）。
- `grep -c "prediction:" / "outcome:" state/backlog.md`：**0/0** 双零，每条目前后复核不变。
- **未跑项如实注记**：`--doctor`、`gh run list`、全量 `uv run pytest -q` 本轮未跑（沿
  「门禁=交办点名面」最小充分纪律；三套件为交办点名的验收面）。

## 二、frontier-citation-anchors（轮 142；backlog 延伸索引 ㉕-㉛ 七锚纯增 57/0）

七新源逐一（格式沿 ⑬-㉔ 在册款：仅引用零接入+一手源行+adaptation 口径+映射+边界注记）：

- **㉕ Hindsight 三位一体领衔**：arXiv:2512.12818「Hindsight is 20/20: Building Agent Memory
  that Retains, Recalls, and Reflects」（cs.CL 2025-12-14，abs 页 fox_fetch 一手复核；四逻辑
  网络 world facts/agent experiences/entity summaries/evolving beliefs 区分 evidence 与
  inference、三操作 retain/recall/reflect）+ repo vectorize-io/hindsight（MIT，gh api 本日
  复核 **60917★**[交办 60916★系调研时值，正常漂移]、pushed 2026-11-13 活跃）+官博。三锚
  映射：facts-beliefs 分离≡环1b facts-only（CALIBRATION_FEEDBACK_NOTE）；retain/recall/
  reflect≡三环（聚合→注入→蒸馏）同构；去重前置过滤≡prop: 去重键+UPDATE(supersedes) 写前
  语义。边界：权重/API=provider 红线（合规≠接入资格）；去重实现须零 LLM 零嵌入。
- **㉖ tigerless-labs/agent-memory**（MIT 4317★、pushed 2026-11-12）：sleep-time 整理道≡
  晚间通道离线批处理对照；Markdown 单一事实源≡state/*.md 纪律；分级读取≡night_package
  refs 一跳摘要。不引入任何服务/常驻组件（无后台长驻红线）。
- **㉗ A-MEM 2502.12110**（repo MIT 1214★、**pushed 2025-12-12 停更如实注记**）：更新优于
  追加，与轮 128-续3 UPDATE(supersedes) 引用式接替**成对闭环**（A-MEM 供「何时该更新」
  语义正源、在册契约供「如何不回改地更新」）。
- **㉘ searls/todo_or_die**（MIT 361★、pushed 2026-07-15）：逾期显式爆发+严格时间门≡
  backlog 老化 deadman 开火同族（仅借语义零接入，Ruby gem 非本栈）。
- **㉙ evidentlyai/evidently**（Apache-2.0 8062★、**pushed 2026-09-29 停更注记**）：
  reference-vs-current 两窗口呈现范式≡环1a 校准聚合呈现语言；**auto-Tests 自动派生阈值
  明确不采**（数据拟合与 n=1 禁拟合红线冲突）。
- **㉚ arXiv:2611.03928**「Sequential auditing of connected forecast errors under partial
  observations」（cs.LG 2026-11-02，abs 页一手复核）：缺失 outcome 审计**显式停止**语义
  （已观测标签足以判定/检索预算耗尽）≡环2 降级+gate not-enough-data 三态同族远期参照。
- **㉛ Mem0 2504.19413 防重复登记款**：真增量仅**生成侧预检两语义**（无等价才 ADD/信息量
  更大才 UPDATE）；写回契约四操作已在册（docs/ops-local-refresh.md lessons 块格式节+
  gen2 报告 :95，grep 复核在册态、在册引用形=仓库名故论文 ID 零命中）——同 ExpeL
  2308.10144 先例不重登整源；判据实现须零 LLM 零嵌入。

**留证**：七 ID+Hindsight/A-MEM/Evidently 改前全仓 git grep 零命中=真增量；5 repo gh api
一手复核（license/spdx/stars/pushed_at，两停更日期与交办逐字吻合）；2 论文 abs 页复核。

## 三、anchor-errata-batch（轮 143；存量锚债修净+轮 11 报告勘误节）

- **runbook 六处一次修净**（对 HEAD 实测终态值）：:296 :1274→:1355；:297/:342 :1118→
  **:1199**；:323/:344 :1283-1306→:1364-1387；:344 :1309→:1390；:770 :1615-1617→:1639-1641。
- **与交办两处不符、以实测为准（裁定记录）**：①交办称 Budget 注应跟至「:1119」——实测
  Budget 注真值 **:1199**（"# Budget: still the single 23:35 LLM session"）；:1119 实为
  `__main__` 内 ring-1a byte-locked 注释第三锚（git show 6c04ce5737 hunk 辨明，两实体）。
  ②交办称首月剧本节起点「:757」——实测 **:748**（gate 子节 :737-746+空行共 11 行，737+11
  算术与 grep 双证）。
- **轮 11 报告文末 append-only 勘误节**（沿轮 8 §7+轮 10 hunk errata 双先例，:759 原字不
  回改）：§六 :90「runbook :759」→实测 **:770**（偏+11=gate 子节插入顺移未跟、收尾沿用了
  插入前读数）；首月剧本起点 :737→:748 时点注记（轮 10 报告 :9/:12/:131 与 handoff 轮 139
  块「:737-964」引述系各写入时点读数、不回改、再引用 +11 换算）；§六 :78 gate 子节
  :737-746 实测仍有效。
- **辨明未动**：runbook :845/:846 两域（:1599-1600/:1533-1536）系 HEAD 时点标注与指向内容
  已互换错位的**存量语义错位**（非本轮顺移、无歧义新值可刷）——如实留后续勘误批。
- 时点前提核实：monthly_review.py 自轮 11 commit B 后零改动=实测值即终态值。

## 四、overdue-outcome-watch（轮 144；S）

- `overdue_outcome_records` 纯函数（:1077）：判据 `y is None`+`due<now_month` 严格时间门
  （复用 :1012 既有判据口径；宽定义含 p 未填卡，清单行注「待填」）。
- `proposal_reconciliation`（:768）签名加可选 `now_month`（测试时钟可控）；§4 findings 尾
  **独立统计块**：汇总行+逐卡清单行；**零逾期整块不渲染**（todo_or_die 在期卡零噪音）。
- `lesson_seeds` 加 `overdue_outcome_count` 键（复用 pred_records，one parser N consumers）；
  render 逾期提示行 facts-only（零逾期不渲染，沿环 2 降级先例）。
- 红线入 docstring：2611.03928 零查询预算纯呈报（outcome 只随月末真实数据到，绝不提前
  补查）；引擎只读不代记。
- tests +3：三态钉（due=当月 boundary 不算/`due<当月` 无 outcome 计入/有 outcome 不计）；
  套件 50→53。

## 五、feedback-dedup-contract（轮 145；M）

- `_FOCUS_BUCKET_RE`+`feedback_dedup_verdict` 纯函数（:1858）：判重键=**桶区间字面子面
  子串**（如 `p∈[0.9,1.0]`，`_focus_feedback_summary` 同一渲染源）对 active_lessons 各条
  确定性匹配，**零 LLM 零嵌入**；三态返回（None=基线/无 active、[]=异桶保留、非空=命中）。
- 同桶 key 才比对——异桶/无桶字面别类**永不判重**（Hindsight 同键边界：保护跨月时间维度
  记录不互删）；跨月同桶全引用不删。
- render 接线（消费 prior[1]）：同桶命中**无条件降级「刷新提示」**附已有教训 [month#idx]
  引用；旧条 append-only 不删不改；本月事实行仍呈现（写回按 event: NONE/UPDATE 定档——
  写入方裁决）；降级**不附**反哺预算注记（刷新提示不占新 insight 额度）。
- **mem0 信息量升格门（InformationContent 比较）不实现**，仅引用锚——业主点名边界
  （LatentGym A/B 同款）。
- tests +4 四方向；套件 53→57。

## 六、cross-month-evolution（轮 146；M）

- **`_bss_components` 提取（:1100）**：gate X 轴 BSS 数学逐字上提=**单一实现**，gate 改调、
  metric/reason 文案逐字保持；gate 六钉单独复跑全绿=零漂移证据。
- `_bucket_stats`/`calibration_month_snapshot`（快照行=各桶 n/hit+Brier+BSS+p̄；零
  resolved→None 不存档）/`parse_calibration_snapshots`（确定性解析、坏行跳过不猜）/
  `calibration_evolution_lines` 三态（两月→两窗口变化行逐位「命中率 0.500→0.000（n 2→1）」
  +BSS 行+单侧桶如实命名不外推；仅本月→first month, no prior；零→none yet）。
- `EVOLUTION_SCOPE_NOTE` 固定禁令字面：禁趋势拟合/斜率宣称/显著性；不设自动判优/劣门
  （判定门唯一=promotion gate 且只算不启用、钥匙在业主；Evidently auto-Tests 明确不采）。
- lesson_seeds 两键（calibration_snapshot_line/calibration_evolution，读档缺文件容错）+
  render §5 新「跨月校准演进」节（Hindsight ㉕ facts/beliefs 分离锚：p=信念轨迹、
  outcome=事实；快照行人工 append 指引=**呈报-入册分离**，引擎不写 state/ 档案）。
- **新 tracked durable 载体 `state/calibration-months.md`**（append-only registry，
  ADR-006 合规；state/ 原四文件无既有存档可复用实测核实；header 钉行契约+属月判据+
  2026-11 双零基线注记）。
- **选型否决理由**（决策员拍板入 runbook 子节）：否决「backlog git 史重算」——双零 0/0
  无史可挖+append-only 长文本挖史脆；不改 prediction 卡格式（ZCode 月末模板 {answer,p}
  在业主待办区，不耦合）。属月判据=对账月（outcome 到达月）。
- tests +4：快照往返逐位+BSS 与 gate X 轴 parity（<1e-9）+退化月 parse+三态+**负向钉**
  （数据行禁「趋势/斜率/显著/上升通道/下降通道/improving/worsening」七词）+lesson_seeds
  读档两态；套件 57→61。**如实记**：负向钉首版误扫禁令文本（「趋势」在禁令内是
  prohibition 非 claim）被测试红面抓获后修正。

## 七、拒绝维持清单（交办指定入本报告而非 backlog）

调研六条目中拒绝维持原判者（理由源=交办调研会话裁决文本，本报告仅入册不重议）：

| 源 | 拒绝理由 |
|---|---|
| NannyML | repo 停更 + CBPE（置信性能估计）与「n=1 月度 p 记录禁自评/禁拟合」在册红线张力 |
| OpenViking | **AGPL**——许可证白名单（MIT/Apache/BSD）外 |
| TencentDB-Agent-Memory | license=**Other**——白名单外 |
| pitmon | 无 LICENSE 文件、0★ |
| arXiv:2610.07740 | 量级与 Aionis 场景不匹配 |
| RLCD（检索项） | 检索报零维持——在册 RLCD 2305.12950 引用锚（runbook）已覆盖，不新增 |

## 八、锚跟改批总账+门禁终态（施工逐条目+收尾复跑，全本会话实跑）

- **锚跟改批四波共 92 处**（全 python 计数断言落地、每轮旧值 grep 清零验证）：轮 143 勘误
  6 处；轮 144 代码顺移 39 处（含 :1580 残留 2 处抓捕修正）；轮 145 顺移 14 处（含上轮
  head -25 截断漏网补 4 处：:1290→:1330、:1443→:1490、:1047→:1071×2）；轮 146 大顺移
  33 处（含 :785 形态首轮 0 计数修正后落地）。runbook 三新面同步入册：步 5 逾期统计
  bullet+步 6 去重契约 bullet（规则表+三源锚）+「演进视图口径」子节。
- **三套件**：exit=0 [100%] 终态 **120**（monthly 61=50+3+4+4 / propose 34 / watchdog 25）。
- **ruff** 全仓净（×4 轮+复跑）。
- **实弹**：`--weekly` rc=0、`--lessons --month 2026-11` rc=0——真账本双零→overdue 统计块/
  逾期提示行/快照行**全不渲染**、演进节=none yet 态=诚实缺省全路径验证；双零 0/0 不变。
- **--status**：动工前后均 ok_committed（95a841a9e3）。
- **如实注记**：一次三套件合跑现 4 个 watchdog ERROR（tmp 竞态疑似）——单跑与另两轮完整
  合跑均绿，按瞬态记录。

## 九、提交与推送（收尾实录）

| 批 | 类型 | 内容 | 哈希（numstat） |
|---|---|---|---|
| A | docs(frontier) | backlog ㉕-㉛ 七锚 | `421fccbdc3`（57/0） |
| B | docs(ops) | runbook 勘误+三新面+锚批 92 处+轮 11 报告勘误节 | `f5db3c3527`（2 文件 113/41） |
| C | feat(ops) | 三代码条目+tests+state/calibration-months.md 新档 | `98c6dabcd3`（3 文件 547/15） |
| D | docs(state) | handoff 轮 142-146 块+current 顶部新条 | `e27e4565c3`（2 文件 3/0） |

`git pull --rebase` → up to date（零冲突）；`git push` → **一次成功**
（1873f41013..e27e4565c3 main→main）。本报告（补写批）见文末提交行。

边界：docs/state/reports lane+运维面三代码条目指名+新 tracked 载体；0 ledger/0 frozen/
0 OOS/研究面零改动；零装包零新依赖。待业主区不变：billing 解锁/L2 钥匙与定标（gate 只算
不启用）/L3 定义权/ZCode 月末提示词模板 {answer,p} 同步确认。
