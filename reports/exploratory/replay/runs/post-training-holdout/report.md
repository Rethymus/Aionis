<!-- EXPLORATORY REPLAY — not a claim, not a gate (design: reports/design/2026-11-17-replay-training-ignition.md; zero runs/ledger.jsonl writes; research face untouched) -->

# post-training holdout 配对报告（mission【3】holdout-pairing，2026-11-18）

## 臂定义

- **pre 臂（锚，零触碰）**：`runs/v2-validation-5months/`（2026-11-17，v2 冻结配置
  原字节 GLM 臂，raw p、零 lessons、零映射）。本批 git status 实证零文件触碰。
- **post 臂（本批）**：`runs/post-training-holdout/runs/` 五目录（每目录 1 月），
  同 v2 冻结配置原字节（`config-frozen-v2-validation.json`）+ `--params
  params/params-current.json`（Platt a=2.802739 b=−1.617083 **forward-only**，
  manifest `calibration_mapping_applied` 在案）+ `--lessons lessons.md`（6 条注入
  top-3，manifest `lessons_provided=6`）。provider=冻结 glm/glm-4.7-flash（非对比臂
  ——映射/lessons 的对比臂拒用守卫为本批引擎扩展，测试钉）。
- **运行形态**：逐月单月窗，sleep 300 重试纪律；尝试数 2026-01×4 / 02×2 / 03×2 /
  04×3 / 05×1（429/1305/超时=窗闭信号，全部如实）。

## 逐月配对表（y 全 0——如实：本窗五月底全 IC<0）

| 月 | pre p | post p_raw | post p_pre(map_p) | post p(映射后) | \|Δp\|(pre vs post.p) | y |
|---|---|---|---|---|---|---|
| 2026-01 | 0.516667 | 0.55 | 0.5500 | 0.481115 | 0.035552 | 0 |
| 2026-02 | 0.549200 | 0.65 | 0.6500 | 0.550996 | 0.001796 | 0 |
| 2026-03 | 0.520000 | 0.45 | 0.5500 | 0.481115 | 0.038885 | 0 |
| 2026-04 | 0.504065 | 0.30 | 0.7000 | 0.585364 | 0.081299 | 0 |
| 2026-05 | 0.500000 | 0.65 | 0.3500 | 0.346123 | 0.153877 | 0 |

- mean \|Δp\| = **0.062282**；post p_pre vs post p 的差=映射可精确归属分量（均值
  −0.071057，纯映射位移）；pre p 与 post p_pre 的差=模型采样+lessons 效应（不可
  进一步分解——LLM 非逐位可复现，manifest honest_notes 在案）。

## 两臂 Brier 与 Murphy 三分量位移（值桶口径）

| 量 | pre | post | 位移 |
|---|---|---|---|
| BS（mean (p−y)²） | 0.268609 | 0.245799 | **−0.022810** |
| REL（reliability） | 0.268609 | 0.245799 | −0.022810 |
| RES（resolution） | 0.000000 | 0.000000 | 0.000000 |
| UNC（uncertainty） | 0.000000 | 0.000000 | 0.000000 |

恒等式 |BS−(REL−RES+UNC)|：pre −5.55e-17 / post −2.78e-17（<1e-12 ✓；值桶 5/4 个
——post 2026-01 与 2026-03 映射后同值 0.481115 同桶）。

**简并如实注记**：本窗 y≡0 ⇒ π̄=0 ⇒ RES=UNC=0、REL=BS（恒等式仍精确但三分量
退化为单分量）。**「reliability 改善 −0.0228」在此窗=「p 整体向 0 靠拢」的方向性
读数，不可解读为校准技能证据**——基率全同向窗内校准效应与基率运气不可分（同 T2
报告 BSS 退化语义）。真正的三分量判读待 epoch-2 全窗（两尾 y 分布）。

## 分桶位移（固定展示带 0.5/0.6/… 切，n=5 展示口径）

| 月 | pre 带 | post 带 | 位移 |
|---|---|---|---|
| 2026-01 | [0.5,0.6) | <0.5 | 降一带 |
| 2026-02 | [0.5,0.6) | [0.5,0.6) | 不变 |
| 2026-03 | [0.5,0.6) | <0.5 | 降一带 |
| 2026-04 | [0.5,0.6) | [0.5,0.6) | 不变 |
| 2026-05 | [0.5,0.6) | <0.5 | 降一带 |

3/5 月映射后跨 0.5 线。**一致性注记**：post 臂 p<0.5 而 answer=true 可并存
（2026-01）——answer=模型离散选择未被映射改变，p=映射后连续概率，单调映射可跨
0.5 线；此为映射语义的如实呈现非缺陷。

## 如实边界

1. **部分训练**：epoch-1 未吃满（54/120=45%，仅 2016-01..2020-06），映射与 lessons
   蒸馏面均基于该部分窗——本报告是「部分训练后」读数，非「训练完成」读数。
2. **n=5 方向性读数**：五月配对、单 provider、单窗——不构成推断，仅方向读数；
   预注册判据（tuning-log 高水位/方差下限）在本窗**不触发判读**（数据面不足）。
3. 三因混合（采样+lessons+映射）：映射分量经 p_pre_mapping 精确分离（见上），
   另两因在 n=5 下不可分。
4. pre-anchor 零触碰：`git status runs/v2-validation-5months/` = 0 文件变更（本批
   实证）；post 产物独立目录 `runs/post-training-holdout/`。

[holdout-pairing] EXPLORATORY REPLAY — not a claim, not a gate (zero runs/ledger.jsonl writes; research face untouched)
