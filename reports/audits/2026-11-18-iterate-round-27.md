# iterate 轮 27 施工会话报告（2026-11-18 深夜→11-19 凌晨，五条目+收尾）

> 条目：schtasks-mount / archive-cleanup-execute / xny-provisional / billing-gha-skip /
> t1-accel-batch。全部 docs+运维 lane，**0 ledger 写 / 0 frozen config 字节 / 0 OOS /
> 研究面零改动**；EXPLORATORY REPLAY 语义全程（零 runs/ledger.jsonl 触碰）。

## 一、四钥匙处置表

| # | 条目 | 处置 | 结果 |
|---|---|---|---|
| ① | schtasks-mount | **executed** | 计划任务 `\Aionis T1 monthly advance` 注册成功，三连验证全过（详见 §一①） |
| ② | archive-cleanup-execute | **executed** | 提案表 10 文件全部处置：6 tracked git rm + 4 untracked 对象层归档后删（详见 §一②） |
| ③ | xny-provisional | **registered（PROVISIONAL 未生效）** | 四轴候选值落设计文档附录+tuning-log 登记行；零自动化解锁（详见 §一③） |
| ④ | billing-gha-skip | **honest-skip（零变更）** | billing=业主付款动作 ZCode 无代付能力；doctor ci=paused 预期态实证（详见 §一④） |

### ① schtasks-mount（executed 实录）

- **路径纪律**：PowerShell `Register-ScheduledTask`（schtasks CLI 无 StartWhenAvailable
  旗标，未退回 CLI）。挂载时点 2026-11-18 23:21:23。
- **任务定义 XML**（`schtasks //query //tn "\Aionis T1 monthly advance" //xml` 导出实读）：
  Trigger=`MSFT_TaskTimeTrigger`，StartBoundary=2026-11-18T23:21:23+08:00，Repetition
  仅含 `<Interval>PT30M</Interval>` **无 Duration**（=无限重复，Microsoft schema 正式
  表示）；Settings=`StartWhenAvailable true` / `MultipleInstancesPolicy IgnoreNew` /
  `DisallowStartIfOnBatteries=false`+`StopIfGoingOnBatteries=false`（电池允许）/
  `ExecutionTimeLimit PT1H`；Action=`C:\Windows\System32\wscript.exe` +
  `//B "F:\ZCodeData\Aionis\data\ops\t1_advance_hidden.vbs"`。
- **查询输出**（LIST //fo）：任务名在册、模式=就绪、下次运行 2026/11/18 23:51:23
  （30 分钟节奏生效）。
- **手动 `//run`（23:22:02）**：运行 ~10 分钟后 State=Ready，**LastTaskResult = 2**
  ——退出码 2（窗口耗尽）显示 0x2 不是故障=PASS 语义正确（诚实断点信号）。
- **偏离注记**：交办模板 `-RepetitionDuration ([TimeSpan]::MaxValue)` 字面量被 CIM
  序列化为 `P99999999DT23H59M59S` 遭 scheduler XML schema 拒收（实错 HRESULT
  0x80041318）；改用 Repetition 无 Duration=无限重复，语义等价，`StopAtDurationEnd`
  显式 false。
- **隐藏 vbs**：`data/ops/t1_advance_hidden.vbs`（gitignored，新建）沿晚间通道先例
  （内部绝对路径+`sh.CurrentDirectory`），新增退出码传播 `rc=sh.Run(...)+WScript.Quit rc`
  使 python 退出码成为任务上次运行结果（0x2 可观测的前提）。
- **载体**：t1-breakpoint.md『已挂载』节 +48 行（初稿「总 66/120→67/120」加总笔误
  就地修正为 54/120→55/120——4×12+6/4×12+7，与 epoch1-calibration 54/120 互证，
  勘误注记在案；修正发生于收档提交前，未触已提交历史）。

### ② archive-cleanup-execute（执行清单，逐文件）

| 提案行 | 文件 | 处置 |
|---|---|---|
| #1 | archive/krx-probes/scratch_krx_probe.py | git rm executed（暂存） |
| #2 | archive/krx-probes/scratch_krx_probe4.py | git rm executed（暂存） |
| #3 | archive/krx-probes/scratch_krx_probe5.py | git rm executed（暂存） |
| #4 | archive/krx-probes/scratch_krx_probe9.py | git rm executed（暂存） |
| #5 | archive/krx-probes/scratch_krx_probe10.py | git rm executed（暂存） |
| #6 | data/cache/audit_r23/scan_links.py | **archived-to-refs→deleted**（blob `7dc18f3f…`） |
| #7 | data/cache/audit_r23/scan_links2.py | **archived-to-refs→deleted**（blob `4c7be22a…`） |
| #8 | data/cache/audit_r23/scan_sentinel.py | **archived-to-refs→deleted**（blob `a3236394…`） |
| #9 | data/cache/audit_tmp/scan.py | **archived-to-refs→deleted**（blob `59b25868…`） |
| #10 | docs/code-review/_sync.py | git rm executed（暂存） |

- **裁决链**：忠实快照被 Mimosa PreToolUse 钩子在全部写入通道拦截（Bash cp=「绕过
  Write/Edit 安全扫描」拒；Write 原内容=「高危·路径穿越」拒——命中的正是 #6-#9
  四文件自身的 HIGH findings）→ **业主升级裁决 (d) git 对象层归档**（纯 plumbing，
  零工作树写入/零 index 触碰/零 gitignore 违规）。
- **归档锚**：四 blob 逐件 BYTE-EXACT（删除前 `sha256sum <文件>` vs
  `git cat-file -p <blob> | sha256sum` 双侧一致实测）；树 f3c5299（audit_r23）/
  5077a37（audit_tmp）/根 f0c1cb9 → 归档 commit `b2fa0fdf510c4630b395f3c8bc02f6559c2f011b`
  （provenance 消息含全 blob SHA+路径+裁决指针）→ `git update-ref
  refs/archive/forensic-scan-2026-11-18`（本地引用默认不 push）。恢复=`git cat-file -p <blob>`。
- **对账注记**：提案标题「11 文件」vs 表行实为 **10 文件/12 findings**（执行按表行）。
- **范围纪律**：audit_r23/audit_tmp 非点名文件（audit_67.py/freshness.py/i18n_check.py/
  def14a_tail.py+全部 JSON 产物）与 krx-probes 余 14 探针+README 原样保留。
- **载体**：提案文件执行记录节 +57 行（reports/audits/2026-11-17-archive-cleanup-proposal.md）。

### ③ xny-provisional（PROVISIONAL 注册）

- **四轴候选值**（业主给定，mission【3】）：X_min=0（BSS>0 即 met；y≡0 简并窗
  BS_base=p̄(1−p̄)=0 ⇒ BSS 无定义不可判如实注记）/ N_min=40 月（训练窗 120 的 1/3
  量级；注册时点 epoch1 快照 54/120 已过线）/ **Y_max=0.90（量纲显式=比例**：各已入桶
  命中率 Wilson 95% CI 上界<0.90，比例上界比比例量纲合法；全命中桶上界恒 1.0=CI
  收窄设计本意 docs/ops-local-refresh.md:772）/ M_min=2 连月（单月=方向性读数不可
  判据，holdout report :67-68 先例）。
- **数据版本锚**：epoch1-calibration.md@1db78970c6 + post-training-holdout/report.md@5aa9bb7aa9
  （两 commit `git show --stat` 实存核验）。
- **方法可用性实测**：`uv run python -I -c` statsmodels **0.14.6**
  `proportion_confint(method='wilson')` 零新依赖（hi(8/10)=0.9433，与轮 141 夹具吻合）；
  anytime 注记锚 arXiv:2610.28979（只借原则，monthly_review.py:2302）。
- **未生效声明**：PROVISIONAL 标签+生效条件=真实 2-3 月数据复核业主终采；
  `promotion_gate_assessment`（monthly_review.py:2330 纯函数）thresholds 形参维持
  未定标理由行态——**零阈值写入、零接线、L2 不启用（L2 钥匙≠定标钥匙）**；
  tuning-log 登记行明确「非调参 delta、thresholds 计数器 3 不变」。
- **载体**：设计文档附录节（reports/design/2026-11-17-replay-training-ignition.md
  +21 行）+ tuning-log.md（+18 行）。

### ④ billing-gha-skip（honest-skip，零变更）

- doctor ci 层实跑 = `{"Publish site (gh-pages)": "paused(actions-disabled)",
  "Tests": "paused(actions-disabled)"}`（预期态，口径 docs/ops-local-refresh.md:152）；
  `gh run list` 只读旁证：main 最后 Actions run = Tests 2026-11-11T05:32:08Z failure 3s
  （零步=billing 锁签名）；gh-pages 原生 dynamic 构建 11-16 正常（本地通道+PAT 不受影响）。
- billing playbook（reports/design/2026-11-11-super-agent-integration.md §5）原样待命；
  .github/workflows/ 7 文件在库；**停用令维持、零文件变更**（ZCode 无代付能力）。

## 二、T1 进度（时点快照，权威以 `t1_advance.py --status` 实测为准）

- 挂载验证手动 run：+1 月（2020-07 完整档 `20261118-152203-t1/`；2020-08 尝试
  header-only `20261118-152243-t1/`）→ **55/120**。
- 加速批（23:58:24，`--stop-after 5`）：**EXIT=2 窗口耗尽**（GLM 429 code 1305 双调
  fail-closed），0 月推进——诚实断点未重跑到通过；header-only `20261118-155824-t1/`
  留痕（任务自身 23:51:24 触发留 `20261118-155126-t1/` 同型）。
- 计划任务 30 分钟节奏接管（00:21:23 起；IgnoreNew 竞态缓解+StartWhenAvailable 补跑）；
  本报告收档时点 55/120、断点月 2020-08、待办 65。

## 三、例行核查（本会话实跑）

- **guard 六值**：状态写入前 `uv run python scripts/anchor_guard.py` rc=0 →
  explicit=149 hit=147 drifted=0 lost=2 external=0 semantic=0 bare=578——
  **explicit 149=轮 26 写后基线恒定**，drifted/lost/external/semantic 四判据 0/2/0/0
  与轮 26 一致（lost=2 为轮 26 即有存量非本批新增）；状态写入后复测见 handoff 轮 171。
- **backlog 双零**：`prediction:` 0 / `outcome:` 0（回放产物零账本污染面不变）。
- **doctor**：9/9 layers pass（layer 2 task scheduler: registered=本批挂载任务被识别）。
- **pytest 全量**：`uv run pytest -q` **EXIT=0**（2645 collected=轮 26 基线恒定零新
  测试；汇总行环境抑制 exit 0=权威信号，轮 25 先例）；**ruff 全仓 All checks passed**。

## 四、待业主区（本轮后仅剩四项）

| # | 项 | 现状 | 所需钥匙 |
|---|---|---|---|
| 1 | GitHub billing 解锁 #2 | §5 #1 原样待命 | 业主付款动作（工程侧不可代） |
| 2 | X-N-Y-M 终采 | PROVISIONAL 已注册未生效 | 真实 2-3 月数据复核后业主终采 |
| 3 | Mimosa 扫描面排除配置 | 提案 §2 建议态（现工具 schema 无 exclude 参数实测核对） | 业主择实施路径（exclude 收录/focusFiles 圈定/扫描前清 worktree） |
| 4 | -wj 账本孤儿 2 行裁决 | §5 #3 原样 | 业主一次裁决（归并/弃置均不可逆） |

## 五、边界与如实注记

- 0 ledger 写 / 0 frozen config 字节 / 0 OOS / 研究面零改动；四个运行类动作
  （Register-ScheduledTask、归档 plumbing、手动加速批、验证三连）均为运维/docs 面。
- **enobufs 兼容放行如实注记**：归档 `git commit-tree` 时 Mimosa 钩子报
  scanner_enobufs（未获完整扫描结论）按兼容策略放行一次；本收尾提交批次若同报，
  以实际提交输出为准——**不声称项目安全**；安全性依据=pytest 2645 EXIT=0+ruff 全仓
  净+对平处置表；建议业主择时重跑完整审计。
- 提交批次：feat(ops) 挂载批 / chore(cleanup) 删除批 / docs(design) 定标批 /
  docs(reports) 本报告 / docs(state) 收尾；pull --rebase 后 push。
- `scripts/ops_local_refresh_hidden.vbs` 仍 untracked（轮 26 先例遗留，非本批触碰面，
  随本报告如实留观）。
