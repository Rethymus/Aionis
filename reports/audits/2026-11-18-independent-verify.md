<!-- EXPLORATORY REPLAY — not a claim, not a gate (zero runs/ledger.jsonl writes; research face untouched) -->

# independent-verify 独立核验报告（mission【5】，2026-11-18）

核验员纪律：**只验不修**——本批零代码/零配置/零历史记录改动，全部检查为只读复算；
发现项如实记录不修复（详见各 CHECK 结论与四臂附录）。

## 核验面与命令（全部本会话实跑）

- 语料：epoch-1=`runs/t1-monthly-advance/`（54 月，去重首见）+ holdout=
  `runs/post-training-holdout/`（5 月）+ epoch2-selective=**0 记录**（SKIPPED.md
  跳过登记在案，目录仅登记文件——如实零记录）。

### CHECK1 y 全量复算 — PASS

冻结 y 源=`runs/results/d3158063…/ic_state.parquet`（sha256 **cb8c0858…** 与冻结
config 记录逐字一致，sha256sum 实算）。引擎同源装载器（`rb.load_ic_series`+
`rb.y_from_ic`）复算全部 **59 条记录**（54+5+0）的 y：**错配 0**。

### CHECK2 掩蔽三键单调性 — PASS

- `rows_used` == 该月在 125 月 IC 序列中的索引（=严格 prior 月数）：**59/59 全符，
  0 错配**。
- `snapshot_sha256`：59/59 在且**互异**；`prompt_sha256`：59/59 在且互异。

### CHECK3 铁律 grep（lessons 零方向词）— PASS（附注记）

- 全文件 grep `利好|利空|看涨|看跌|CPI|非农|降息|加息|方向规律`：**2 命中，均为
  准入判据元说明行**（第 12 行=规则自述「方向规律零准入」、第 25 行=蒸馏自检
  注记），非条目违规。
- **条目级（编号 1-6）命中 = 0** ✓——铁律要求面（教训条目零方向词）满足。

### CHECK4 tuning-log 计数器对平 — PASS

逐旋钮移动链 vs 计数器：thresholds (0→1,1→3)=3 ✓；calibration_mapping (0→1)=1 ✓；
bucket_cuts (0→1)=1 ✓；prompt_template/top_n_lessons/bounded_context=0（零 delta
行一致）✓。delta 行总数 4（2026-11-17 一条+2026-11-18 三条）与表实一致。

### CHECK5 params JSON 合法 — PASS

`kind=replay-params-current`、exploratory=true、a=2.802739 b=−1.617083、a>0、
FORWARD ONLY scope；54 月 (p,y) 按记录在案调用复算 = **系数逐位一致**（本会话
二次实证）。

### CHECK6 账本零污染 — PASS

`grep -icE "replay" runs/ledger.jsonl` = **0 命中**；账本 71 行；`git status
runs/ledger.jsonl` = 0（本周期零触碰）。

## 四臂 y 源并排复算附录（零 LLM 纯复算；**标记性不裁决**）

臂构成（按 mission「B/C/D base + D state」）：phase B=17245a75、phase C=a7fdb48f、
phase D=d3158063（冻结 y 源所在）、各取 ic_base.parquet + phase D ic_state.parquet。
全部 125 月覆盖，epoch-1 54 月零缺失。

| 臂 | 文件 sha8 | 与冻结 y 一致 | Brier(记录 p vs 臂 y) | answer 命中 |
|---|---|---|---|---|
| B_base | a66c7c74 | 46/54 (0.8519) | 0.207530 | 0.6111 |
| C_base | a66c7c74 | 46/54 (0.8519) | 0.207530 | 0.6111 |
| D_base | a66c7c74 | 46/54 (0.8519) | 0.207530 | 0.6111 |
| **D_state（冻结）** | cb8c0858 | **54/54 (1.0000)** | **0.250207** | 0.5370 |

**发现 1（标记）**：B/C/D 三臂 ic_base **字节相同**（sha8 同）——「四臂」实为
**两个独立校准面**（base 面 vs state 面），三目录为同内容副本。
**发现 2（标记）**：base↔state 在 54 月内翻转 **8 个月 y 标签**（14.8%）：2016-01
（base +0.0027/state −0.0130）、2016-10（+0.0050/−0.0667）、2016-11、2016-12、
2017-01、2017-05、2017-07（+0.0678/−0.0391）、2018-03（+0.0701/**−0.0008**≈零交叉）。
**发现 3（标记）**：若换 base 面，epoch-1 Brier 0.250207→0.207530（−0.043）、answer
命中 0.5370→0.6111——**y 源选择自由度对校准读数量级影响显著**。
**不裁决声明**：state vs base 的语义差异属 confirmatory 管线设计问题（state=状态
条件化 IC，base=无条件 IC——命名推断，未读管线实现），冻结记录 record-once 钉定
D-state 合法有效（sha 在案一致）；是否需要业主层澄清=**标记待业主，不在本核验
裁决范围**。本核验零改动。

## 结论

六项 CHECK 全 PASS（CHECK3 附条目级/元说明分层注记）；四臂附录标记 y 源自由度
三发现送业主参考。核验员未修改任何被验对象（本报告文件为唯一新增产物）。

[independent-verify] EXPLORATORY REPLAY — not a claim, not a gate (zero runs/ledger.jsonl writes; research face untouched)
