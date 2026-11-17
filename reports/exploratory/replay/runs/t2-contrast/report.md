<!-- EXPLORATORY REPLAY — not a claim, not a gate (design: reports/design/2026-11-17-replay-training-ignition.md; zero runs/ledger.jsonl writes; research face untouched) -->

# T2 provider-contrast arm — 冻结验证五窗 GLM vs SiliconFlow 分歧表

任务：t2-provider-contrast（2026-11-17）。`scripts/replay_blackbox.py --provider siliconflow`
运行时覆盖（默认 glm 不变；`--provider` 与冻结名相同时零 override 标记），复用 **v2
validation 冻结配置原字节**（`config-frozen-v2-validation.json`，两臂同
`config_sha256=257165bf24570694…`，运行后复钉一致），五窗 2026-01→2026-05 逐月单窗执行，
产物落本目录 `runs/<ts>-t1/`。GLM 臂 = 既有 `runs/v2-validation-5months/`（四窗一次通过 +
01 探针记录并入）。

## 分歧表（逐月；y 两臂引擎确定性一致，逐月断言相等）

| month | GLM answer/p | SF answer/p | y | Δp = p_glm−p_sf | answer 分歧 |
|---|---|---|---|---|---|
| 2026-01 | true / 0.5167 | true / 0.5167 | 0 | +0.0000 | no |
| 2026-02 | true / 0.5492 | true / 0.5124 | 0 | +0.0368 | no |
| 2026-03 | true / 0.5200 | true / 0.5100 | 0 | +0.0100 | no |
| 2026-04 | true / 0.5041 | **false / 0.3500** | 0 | **+0.1541** | **YES** |
| 2026-05 | true / 0.5000 | true / 0.5000 | 0 | +0.0000 | no |

- **answer 分歧率：1/5 = 20%**（唯一分歧 2026-04：SF 答 false、p_raw=0.65 → 映射
  p=0.35；GLM 答 true、p=0.5041）。
- **p 差分布**：Δp 均值 +0.0402（GLM 系统性略高）、|Δp| 均值 0.0402、最大 0.1541（即
  2026-04 单月；其余四月 |Δp|≤0.0368，其中 01/05 完全一致——两者都贴着 0.5167/0.5 气候值）。

## 两臂各自 Brier / BSS 并排

| 臂 | Brier（5 月均值） | 引擎口径 BSS | 辅助：vs 气候值技巧分* |
|---|---|---|---|
| GLM (glm-4.7-flash) | 0.268609 | **无定义**（五月 y 全 0 → p̄y=0 退化基；引擎诚实降级原话「BSS 无定义（p̄ 退化，诚实降级不造假分）」，两臂同因） | 1 − 0.268609/0.266945 = **−0.006236** |
| SiliconFlow (Qwen/Qwen2.5-7B-Instruct) | 0.232419 | **无定义**（同上） | 1 − 0.232419/0.266945 = **+0.129336** |

\* 辅助列公式（两臂同式同基，本报告自算，非引擎语义）：基 = 训练窗气候值 p̄=0.516667
（T0 伴生 run 20261116-175239），Brier_clim = mean((0.516667−y)²) = 0.266945（y 全 0）。
引擎口径 BSS 因 y≡0 基退化无定义，故并列此辅助列仅为可读性，**不构成任何一方更优的判断**：
SF 更低 Brier 完全由 2026-04 单月 answer 翻转贡献（|Δ|=0.1541），n=5、y 全 0 的窗口里属
噪声带内单点效应。两臂 p 全部落在 [0.35, 0.55]（气候值附近）= v2 收敛诚实成立的读数在
第二供应商上方向一致。

## 执行与红线记录（如实）

- 探针：2026-01 首试即过（siliconflow 当晚可用，独立配额），**12 次帽退避循环备而未用，
  零降级、零重试**；五窗共 5 次 LLM 调用，tokens p/c = 2968/77（各月 592-595/13-18）。
- 零 lessons：GLM 臂 `lessons_provided=0`；对照臂引擎**结构性拒绝** `--lessons` 与差异
  `--provider` 组合（EXIT_USAGE，tests/test_replay_blackbox.py 钉）——lessons 身份 GLM
  绑定红线落在代码层，非仅操作层。lessons.md 零写入。
- 参数零调：v2 冻结字节零改动（运行前 sidecar、运行后 sha 复钉均 257165bf…）；对照臂
  仅运行时覆盖，manifest 记 `provider_override{from_frozen: glm, to: siliconflow}` +
  `provider_used{name, model}`。
- 契约与掩蔽：五窗零 contract-fail 文件、零 `answer_coerced_from_string` 标记、逐月
  `masking_ok=true`（行 ≤ t-1 断言 + context snapshot SHA256 随月记录在案）。
- 产物边界：本目录（`reports/exploratory/replay/runs/t2-contrast/`）内 5 个 run 目录 +
  本报告；零 runs/ledger.jsonl 写入、零研究面触碰。

## 逐窗 run 目录

| month | run dir（t2-contrast/runs/） |
|---|---|
| 2026-01 | 20261117-124949-t1（兼探针） |
| 2026-02 | 20261117-125015-t1 |
| 2026-03 | 20261117-125038-t1 |
| 2026-04 | 20261117-125102-t1 |
| 2026-05 | 20261117-125129-t1 |

> 呈现≠校准（引擎口径）：本表为记录性呈现，禁据此调 p、定阈值或选供应商。
