<!-- EXPLORATORY REPLAY — not a claim, not a gate (design: reports/design/2026-11-17-replay-training-ignition.md; zero runs/ledger.jsonl writes; research face untouched) -->

# T1 断点记录（t1-training-run 批，2026-11-17 02:40 收档）

## 完成面

- **T0 伴生件（本批内完成）**：`runs/20261116-175239-t0/`——训练窗 2016-01→2025-12
  120 月，恒 p̄=0.5167（y=1 计 62/120），BSS≡0 构造断言 PASS exit 0 零 LLM。
  （注：p̄=0.5167 为引擎输出；62/120=0.5167 ✓）——供 T1 并排报告的 T0 基准。
- **前置批（上一批）**：T0 全实际覆盖窗 125 月（runs/20261116-173833-t0）已提交 ae6f6128b3。

## 受阻面：T1 训练期 2016-01→2025-12 逐月推演——0/10 块完成，零月回答

GLM（glm-4.7-flash，冻结 config provider 钉定）持续不可用，10 次尝试全部中止于
月 1（留档 10 个 header-only 断点目录 runs/20261116-*t1/，manifest 未生成=诚实断点）：

| 时点(本地) | 错误 |
|---|---|
| 02:03:36 | 429 code 1305 平台过载（「该模型当前访问量过大」） |
| 02:04:17 | 429 code 1305 |
| 02:07:43 | Request timed out（240s 客户端超时） |
| 02:08:09→02:18→02:24→02:27→02:34→02:36（后台驱动 12 次计划，5 次实跑后业主向升级前人工停止） | 1305 / 1302「您的账户已达到速率限制」/ timeout 交替 |

**判别探针（一手实测）**：glm-4.7-flash 最小探针 5 次 4 失败 1 瞬通（02:02:36 OK，
其后 02:07/02:12/02:17/02:38 全败）；**siliconflow 探针 OK 1.4s 契约完美**
（Qwen2.5-7B-Instruct，独立配额池）；modelscope 403「complete your profile」账户
资料问题不可用。fox_stats 账本：quotaWindow usedPct=**100%**（snapshot 16:56Z
stale）、today total=70.8M tokens/384 requests——GLM 侧限速与业主自身会话额度共享池。

## 处置：按交办预案「如实记录断点续跑，绝不重跑到通过」收档升级业主

- 冻结 config **零改动**（provider=glm/model/窗口/切点全原样）——恢复后**无需 re-freeze**。
- tuning-log.md 零 delta 零检查点条目（检查点从块 1 完成才开始，未到达）；lessons 零蒸馏。
- **续跑协议**：GLM 恢复后逐块串行 `--tier t1 --from Y-01 --to Y-12`（2016→2025 十块），
  块间检查点（调参 delta 或无-delta 观察）落 tuning-log.md，lessons 跨块注入；
  断点目录 10 个保留为诚实证据，不删除不复用。
- 业主可决项：等配额窗口重置后本批内续跑 / 授权临时切换 provider（siliconflow 现可用、
  独立配额，但冻结 config 钉 glm=设计 T1=GLM，切换须业主点头+新 freeze 或披露式覆盖）/
  延后至后续批次。

## 协议 A 执行时间线（业主 2026-11-17 批复：A 加边界败则降 C；B 不采）

- **02:42→05:36 判别探针 12 次（业主帽：3h 或 12 次先到）**：#1-#6 败（1305/超时/1302
  交替）、#7 04:25:56 过（窗口瞬开→块 1 至月 2016-02 契约失败中止）、#8 04:33 败、
  #9 04:50 过（块 1 数月后 1302 中止）、#10 04:55 败、#11 05:12 过（块 1 数月后 1302
  中止）、#12 05:36 过（块 1 数月后 1302 中止）。**模式定性**：探针/突发小调用可通，
  12 连调所需的突发额度不足以覆盖整块——每 ~17 分钟一个解锁窗，窗内 3-8 调后硬锁。
- **检查点 delta ①（唯一）**：月 2016-02 契约失败（answer 字符串布尔）→
  scripts/replay_blackbox.py 契约容错（精确小写 "true"/"false" 强制转布尔+逐回复
  answer_coerced_from_string 非静默标记）commit beb32cd42a+tests 24 passed；tuning-log
  thresholds 计数器 0→1。
- **05:42 业主帽到（12 探针/3h）→按 ④ 降级 C 收档**：0/10 块完成如实入档；
  lessons 库空态（零完成块=零蒸馏证据面）+掩蔽证明汇总模板+校准曲线模板落盘
  （蒸馏四件套不依赖 T1 的部分）；T1 列后续批次续跑候选——续跑协议见上节。
- 弃档注记：15 个 t1 尝试目录全保留（10 pre-fix+5 post-fix），header-only 或数月
  partial，manifest 未生成=诚实断点；零月记录被复用或拼接（每块从月 1 重答=断点语义
  非重跑到通过）。

## 协议演进注记（2026-11-17 主会话裁决：块级→月级断点累积）

原协议「每块从月 1 重答」在 GLM 窗口节奏（~18min 一窗、窗内 3-8 调）下不可达
（块=12 连调 > 单窗容量，块 1 四次尝试全中止的根因）。裁决：T1 改**月级断点累积**
——逐月独立调用（`--from m --to m`），成功调用累积于 `runs/t1-monthly-advance/`，
同月失败重试不产生拼接记录（每次成功调用=独立完整记录，零拼接零复用不变）；
年界检查点（调参判读，LLM 语义）在 12 个月齐后由后续批次触发，零 LLM 循环只积累
月记录不越权调参。设计 §4「调参只在年界检查点」语义不变——检查点触发时点后移
到月记录齐备。铁律不变：校准拟合非方向命中/掩蔽证明/EXPLORATORY/零账本。

## 推进器使用说明（t1-advance-formalize，2026-11-17 append）

月级断点累积已由 `scripts/t1_advance.py` 正式化（主会话后台循环 exec_68ca17cc
同参）：读 `t1-monthly-plan.txt`（120 月清单，必须与冻结 config-frozen.json 训练窗
逐月一致，不一致=exit 4 拒跑）→ 逐月调用 replay_blackbox 单月窗（`--from m --to m`，
冻结 config 原字节、provider=glm 钉定、零 lessons）→ 成功月记录落
`runs/t1-monthly-advance/<ts>-t1/` → 计数并语义化退出。

```bash
# 只读状态（数 advance 目录月记录 vs 计划，永不调用引擎）
uv run python scripts/t1_advance.py --status

# 推进一次（从断点月起逐月；GLM 失败即停=窗口耗尽信号，绝不重跑到通过）
uv run python scripts/t1_advance.py                # 全量推进至窗口耗尽/计划完成
uv run python scripts/t1_advance.py --stop-after 3 # 每次至多 3 个新月（礼貌阀门）
```

退出码：**0** 计划完成（或完成后的幂等 no-op 再入）· **1** 部分推进（--stop-after
预算到、仍有待办月）· **2** 窗口耗尽（引擎调用失败中止——1305/1302/超时即窗口
信号；零推进或推进后遇失败均归此码，stdout 注明本次推进数）· **3** 计划/配置参数错
· **4** 计划与冻结训练窗不一致。幂等语义沿晚间通道先例：已齐月记录的月份跳过
（断点=首缺月），计划全齐后重复触发=只读 no-op exit 0；无常驻进程、无锁——每次
调用是短命进程，重复触发只是廉价 no-op。

**年界检查点**仍是后续批次的人工/主会话语义动作（12 个月齐后判读 tuning-log、
蒸馏 lessons）——推进器只积累月记录，不越权调参（铁律：调参只在年界检查点）。

### Windows 计划任务挂载模板（形态沿晚间通道先例；**挂载动作待业主执行，本批不代做**）

晚间通道先例（docs/ops-local-refresh.md）：每日多次重复触发 + StartWhenAvailable
开机补跑 + 幂等 guard 让多余触发变 no-op。t1_advance 同款形态（示例：晚间
19:35–23:35 每 2 小时一触，每触至多 1 新月=每窗口节奏一次有效调用，GLM 限速下
自然退避；频率与帽值由业主定夺）：

```powershell
# 管理员 PowerShell —— 业主执行；命令形参可按窗口节奏调整
$act = New-ScheduledTaskAction -Execute "F:\ZCodeData\Aionis\.venv\Scripts\python.exe" `
  -Argument "F:\ZCodeData\Aionis\scripts\t1_advance.py --stop-after 1" `
  -WorkingDirectory "F:\ZCodeData\Aionis"
$trg = @(19,21,23) | ForEach-Object {
  New-ScheduledTaskTrigger -Daily -At "$($_):35" }
$set = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "Aionis T1 monthly advance" -Action $act -Trigger $trg -Settings $set
```

- `--stop-after 1`：每触发至多推进 1 个月（贴 GLM「窗内 3-8 调后硬锁」实测节奏的
  保守取值；业主可去掉该阀改全量推进）。退出码 2（窗口耗尽）在 Task Scheduler 里
  只是「上次运行结果 0x2」——不是故障，是诚实断点信号，等下一触发再试。
- 卸载：`Unregister-ScheduledTask -TaskName "Aionis T1 monthly advance"`。
- 计划完成后（`--status` 显示 120/120）触发变只读 no-op，可留着或卸载由业主定。
