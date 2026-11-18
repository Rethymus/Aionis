<!-- EXPLORATORY REPLAY — not a claim, not a gate; round wrap-up report (audit lane) -->

# iterate 轮 26 收尾报告（2026-11-18，epoch1-complete/calibration-aggregate/tuning-verdict/holdout-pairing/epoch2-selective/independent-verify 六批）

动工前 `test -f reports/audits/2026-11-18-iterate-round-26.md` = NOT-EXISTS 实证 ✓。

## ① epoch-1 终态（非 120/120，剩余清单如实）

- 终态 **54/120**（`t1_advance.py --status` 本会话多时点实跑，最后时点断点月
  2020-07）：2016 12/12、2017 12/12、2018 12/12、2019 12/12、2020 6/12（01-06）、
  2021-2025 各 0/12。
- **剩余 66 月清单**：2020-07..2020-12（6）；2021-01..2021-12（12）；2022 全 12；
  2023 全 12；2024 全 12；2025 全 12。
- 驱动轨迹：业主侧 T1-ADVANCE-2 循环（bash PID 6808/19664）自轮 25 的 3/120 推至
  **52/120**（监控期 sleep 300 轮询 81 周期陪跑，~18-22min GLM 窗口节奏）；循环
  2026-11-18 ~18:48 按 8 连败帽死/耗尽（PIDs 消失实查+无接替驱动甄别）→ 施工员按
  mission 接管：`t1_advance.py --stop-after 1` 同参（冻结 config 原字节/provider=glm
  钉定/零 lessons）推 2020-05/06 首试连过至 54/120；2020-07 六连败（sleep 300×6/月
  纪律用尽）=**窗耗尽如实断点**，不重跑到通过。监控期+接管期全部 run 目录（成功
  月记录+header-only 断点失败目录）全量入档 6 个 `chore(replay)` commit。

## ② 校准聚合（calibration-aggregate）

`scripts/epoch1_calibration.py`（持久只读聚合器）→
`reports/exploratory/replay/epoch1-calibration.md`（54/120 断点快照）：

- **Murphy 三分量（值桶口径，恒等式残差实测 0.0）**：BS=0.250207、REL=0.099590、
  RES=0.099040、UNC=0.249657（π̄=0.5185）；ECE（五桶展示口径）0.114187。
- 分年 BSS vs T0 p̄₀=0.5167：2016 −0.051644 / 2017 +0.068465 / 2018 −0.142749 /
  2019 +0.126695 / 2020H1 −0.018999；2021-25 零记录标断点。
- 口径发现（如实）：等数分位五桶直接当分解桶时恒等式残差 ~1e-4 级且可为负（实测
  +6e-4/−2.5e-3 两例）——分解判读固定**值桶口径**（23 distinct p 各成一桶），五桶
  仅展示口径（保并列切边，残差 −2.46e-03 注记）；isotonic 零拟合（sklearn ~1000
  样本警告注记）。
- 逐月 resolution 位移（值桶 LOO 54 行）+最差 12 月（|p−y| 降序：2016-10、
  2017-05、2016-05、2016-12、2018-02、2017-01、2018-11、2018-03、2017-07、
  2018-05、2018-10、2019-12）+答案分布（answer true 43/false 11，方向命中 29/54；
  p 聚类 0.60×8/0.50×6/0.55×6/0.85×5）。

## ③ 调参裁决实录（tuning-verdict）

三文件落档（commit aafd86aa1a）：`params/params-current.json` 新建+tuning-log
delta ②③④+lessons.md 6 条。

- **delta ② calibration_mapping（新旋钮注册 0→1）**：Platt p′=σ(a·p+b)，
  a=2.802739 b=−1.617083（sklearn 1.9.0 `C=inf lbfgs`，全训月 54 对 (p,y)，
  seed=0）；保序核验 a>0+Spearman=1.000000+构造性证明（值桶分区不变⇒RES 映射前后
  相等 0.099040）=铁律 1 天然满足；bootstrap CI95（2000 次 2000/2000 收敛）
  a∈[−1.002502, 9.874640] b∈[−6.002006, 0.761656]——CI 宽=54 点小样本如实报区间
  （a 符号 95% 内不定）；FORWARD ONLY，epoch-1 历史零回填。
- **delta ③ bucket_cuts（0→1）**：展示口径=保并列分位五桶+分解口径=值桶双口径
  （残差显式注记）。
- **delta ④ thresholds（1→3，预注册）**：epoch-2 判据两行——**高水位**=epoch-1
  最小值桶 REL 0.099590 只紧不松永不回放宽；**方差下限**=分年 BSS std(ddof=0)
  0.093891（5 块基线，2020H1 部分年块带重算规则）低于即判读作废重审
  （2611.14539 方差稀释博弈调研）。
- **fresh-eyes 复核（只审不改）**：三问逐项（会坏：斜率 CI 含负值/部分年块基线/
  RES 伪装收益防；噪声拟合：lessons ③④小样弱先验如实；违铁律：逐项核对全过）；
  单会话自评形态如实注记待独立复核员。**弃用行 A-D**：top_n_lessons（lessons 库
  空转零证据）/prompt 改写（零新契约失败）/X-N-Y-M（数据不足+业主钥匙）/1 参数
  温度缩放（自由度无据）。
- lessons.md：6 条校准教训入库（活跃 6/8≤8，条目级零方向词 grep 实证，逐条带
  (p,y) 数据面月份）。

## ④ holdout 配对（holdout-pairing）

引擎最小扩展（commit 5aa9bb7aa9）：`--params calibration_mapping` 前向应用
（p′=σ(a·map_p+b)，p_raw 语义不变，`p_pre_mapping` 仅映射启用时新增=无映射记录
逐字节兼容）+`--lessons` .md 编号条目装载+对比臂拒映射守卫；测试 26→30 passed。

五窗实跑（v2 冻结配置原字节+params+lessons，逐月+sleep 300 纪律）：尝试数
2026-01×4/02×2/03×2/04×3/05×1 全过；manifest 实证 lessons_provided=6 top_n=3+
calibration_mapping_applied。

**配对表（pre=v2-validation-5months vs post；Murphy 位移加粗）**：

| 量 | pre | post | 位移 |
|---|---|---|---|
| mean \|Δp\| | — | — | 0.062282（逐月 0.0356/0.0018/0.0389/0.0813/0.1539） |
| BS | 0.268609 | 0.245799 | −0.022810 |
| **REL** | 0.268609 | 0.245799 | **−0.022810** |
| **RES** | 0.000000 | 0.000000 | **0.000000** |
| **UNC** | 0.000000 | 0.000000 | **0.000000** |
| 恒等式残差 | −5.55e-17 | −2.78e-17 | <1e-12 ✓ |

**如实注记**：本窗五月底 y≡0 ⇒ π̄=0 ⇒ RES=UNC=0、REL=BS 三分量退化为单分量——
「reliability 改善 −0.0228」=「p 整体向 0 靠拢」的方向性读数，非校准技能证据
（基率全同向窗内校准效应与基率运气不可分，同 T2 报告 BSS 退化语义）；部分训练
标注（epoch-1 54/120=45%）；映射分量经 p_pre_mapping 精确分离（均值 −0.071057），
采样+lessons 分量 n=5 不可分。pre-anchor `v2-validation-5months/` 零触碰
（git status=0 实证）。

## ⑤ epoch-2 选择性重答——SKIPPED（epoch2-selective）

门槛实跑核验：`t1_advance.py --status` 实测 **54/120 < 100 月线** → 按 mission
规则**跳过重答**（窗当时开但「或」关系单项成立）；零引擎调用零 LLM 消耗。
登记=`runs/t1-epoch2-selective/SKIPPED.md`（后续协议六项：≥100 月触发/最差 12 月
清单/命令形 [config-frozen.json 训练窗件]/通缩注记四项强制/禁止回填/双判据先行）
+tuning-log append 登记（零 thresholds 计数变化）。

**通缩注记（预置，未来执行批强制携带）**：epoch-2=暴力搜索非预注册假设——任何
in-sample 改善**只作诊断不作主张**；必须附 (a) 2608.27734 trial-count 通缩+
(b) 有效独立样本数折扣+(c) 2608.23808 审计层「改善-噪声不可分」+(d) 三因不可分
（p_pre_mapping 分离映射分量）。

## ⑥ 独立核验（independent-verify）

`reports/audits/2026-11-18-independent-verify.md`（commit ec0e760885；只验不修）：

- 六 CHECK 全 PASS：①y 全量复算（冻结 ic_state.parquet sha256=cb8c0858…与冻结
  config 逐字一致；59 条记录引擎同源复算错配 0）②掩蔽三键（rows_used==月索引
  59/59；snapshot/prompt sha256 各 59/59 全在互异）③铁律 grep（**条目级**方向词
  0；全文件 2 命中均为准入判据元说明行，分层注记）④tuning-log 计数器逐旋钮对平
  ⑤params 合法+系数复算逐位一致（二次实证）⑥账本零污染（grep replay 0 命中/
  71 行/git 零触碰）。
- **四臂 y 源并排附录（零 LLM；标记性不裁决）**：B/C/D base 三文件字节相同
  （sha8 a66c7c74）=四臂实为两源；base↔state 翻转 **8/54 月** y（14.8%，含零交叉
  月 2018-03 base +0.0701/state −0.0008）；base 面 Brier 0.207530 vs state 面
  0.250207（−0.043）、answer 命中 0.6111 vs 0.5370——y 源选择自由度影响量级显著，
  三发现标记送业主（state/base 语义属 confirmatory 管线设计问题，冻结 record-once
  钉定 D-state 合法）。

## ⑦ 例行核查（本会话实跑）

- guard：状态写入前 **149/147/0/2/0/576**（=轮 25 写后基线恒定）；写入后复测
  **149/147/0/2/0/577**（explicit/hit 零增长=轮 170 条目零新显式锚；bare +1=EOF
  :3026 裸锚自然增长；drifted/lost/external/semantic 四判据 **0/2/0/0 恒定** ✓）。
- backlog 双零：prediction: 0 / outcome: 0 ✓。
- doctor：`ops_local_refresh.py --doctor` **9/9 layers pass**。
- pytest 全量：**2645 collected, EXIT=0 全绿**（轮 25 基线 2640+5；汇总行被环境
  抑制，exit 0=权威信号，collect 分文件求和实证总数）；ruff 全仓 All checks passed。
- 账本：零污染（CHECK6）；冻结 config 字节零动（v2 sha 双钉沿用）；0 OOS；研究面
  零改动（`score_calibration.py` 仅引用公开哲学未触碰）。

## ⑧ 待业主区

1. **schtasks 挂载提醒**：T1 月级推进器计划任务模板在 `t1-breakpoint.md`（挂载动作
   业主执行，本周期未代做）——剩余 66 月（2020-07..2025-12）靠窗口节奏续推，
   `t1_advance.py --status` 为权威计数。
2. **2026-06→10 补算仍悬**（轮 168 遗留）：IC 序列现覆盖 2016-01..2026-05（125 月），
   尾段无行列——confirmatory 管线补算属业主侧（y 源覆盖延伸后 holdout 窗可扩展）。
3. **y 源 base/state 澄清（新增，独立核验标记）**：ic_base vs ic_state 在 54 月面
   翻转 8 个月 y、Brier 位移 −0.043——是否需要语义澄清/文档化属业主裁决（冻结
   record-once 不受影响）。
4. 归档清理提案与 Mimosa 扫描面排除（轮 25 遗留）维持待决。
5. 建议择时重跑完整 Mimosa 审计（本周期 9 次 commit/push 钩子均报 scanner_enobufs
   未获完整扫描结论，按兼容策略放行——安全性依据=全量测试+ruff+六 CHECK，不声称
   安全；沿轮 25 口径如实注记）。

## 边界

六批全部 EXPLORATORY REPLAY 面；0 ledger/0 frozen config 字节/0 OOS/研究管线零
改动；epoch-1 历史记录零回填（映射 forward-only 构造性保证+测试钉）；commit 链：
7cd15aca45/b5380a0e10/d477e35ce9/b925e2f019/4223b152d1/de27fe0660（epoch-1 入档）→
1db78970c6（calibration）→ aafd86aa1a（tuning-verdict）→ 5aa9bb7aa9（holdout）→
906856736c（epoch2-skip）→ ec0e760885（verify）。

[round-26] EXPLORATORY REPLAY — not a claim, not a gate
