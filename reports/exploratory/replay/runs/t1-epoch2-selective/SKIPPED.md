<!-- EXPLORATORY REPLAY — not a claim, not a gate (design: reports/design/2026-11-17-replay-training-ignition.md; zero runs/ledger.jsonl writes; research face untouched) -->

# epoch-2 选择性重答——SKIPPED 登记（mission【4】epoch2-selective，2026-11-18）

## 门槛核验（本批实跑命令与输出）

- epoch-1 计数面：`uv run python scripts/t1_advance.py --status` →
  **`54/120 months have records`**（断点月 2020-07，窗耗尽 de27fe0660）。
- mission 规则：「窗口关或 epoch-1 <100 月则如实跳过登记后续」——窗当时开
  （holdout-pairing 同日五窗全过），但 **54 < 100 计数面门槛不满足 → 跳过成立**。
- 前置条件核验（已满足但本批不适用）：双判据已预注册于 tuning-log 检查点状态节
  2026-11-18 块（高水位=值桶 REL 0.099590 只紧不松 + 方差下限=分年 BSS std
  0.093891），门槛先行条件 in place。

## 裁决：跳过重答（零引擎调用、零 LLM 消耗、零目录产物除本登记文件）

in-sample 选择性重答（最差 12 月带 params+lessons）在 45% 训练面上进行=对未吃满
的拟合面做二次搜索，trial-count 通缩（2608.27734）与审计折扣（2608.23808）风险
放大——按 mission 门槛如实跳过，登记后续。

## 后续协议（触发后按此执行，无需重开裁决）

1. **触发条件**：epoch-1 记录面 ≥100 月（`t1_advance.py --status` 实测）且窗开；
   或业主明示 override。
2. **重答对象**：epoch1-calibration.md「最差 12 月」清单（|p−y| 降序）：
   2016-10, 2017-05, 2016-05, 2016-12, 2018-02, 2017-01, 2018-11, 2018-03,
   2017-07, 2018-05, 2018-10, 2019-12。
3. **命令形**（逐月单月窗+sleep 300 重试纪律，输出独立目录，pre-anchor 零触碰）：
   `uv run python scripts/replay_blackbox.py --tier t1 --config
   reports/exploratory/replay/config-frozen.json --params
   reports/exploratory/replay/params/params-current.json --lessons
   reports/exploratory/replay/lessons.md --out
   reports/exploratory/replay/runs/t1-epoch2-selective --from <m> --to <m>`
   （注意：config 用 **config-frozen.json** 训练窗冻结件——重答的是 epoch-1 训练月；
    holdout 用 v2-validation 件与本批无关。）
4. **通缩注记（强制，逐项入报告）**：epoch-2=暴力搜索非预注册假设——任何 in-sample
   改善**只作诊断不作主张**；报告必须附 (a) trial-count 通缩注记（12 月×重试=多次
   采样面，2608.27734 口径）；(b) 有效独立样本数折扣声明；(c) 审计层口径
   （2608.23808）的「改善-噪声不可分」注记；(d) 与 holdout-pairing 同款「采样+
   lessons+映射」三因不可分声明（p_pre_mapping 分离映射分量）。
5. **禁止回填**：改善月禁止回填 epoch-1 聚合表（epoch1-calibration.md 与任何已推
   报告的历史数字零改写）；重答记录为独立平行面，与原记录并存不替换。
6. **判读门槛**：预注册双判据（tuning-log）先行；改善若触发判据提升，thresholds
   计数器逐次 +1。

[epoch2-selective] EXPLORATORY REPLAY — not a claim, not a gate (zero runs/ledger.jsonl writes; research face untouched)
