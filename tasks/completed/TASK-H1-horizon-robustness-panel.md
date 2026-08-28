# TASK-H1 — horizon_robustness 面板垂直切片(ledger 派生导出 + /track 呈现 + 契约测试)

- Lane:display/export 派生(只读 **tracked** `runs/ledger.jsonl`;零研究面接触、零冻结触碰、零新抓取)
- 背景:horizon sweep(h=10/42)历史上已跑完且全胜(B/C/D/E1 四相 null 全部在两个非冻结 horizon 保持——见 `runs/sensitivity_horizon*.log` 与 ledger 两行 `phase:"sensitivity_horizon"` exploratory 行),但结果只存在于 gitignored 日志,终端不可见。本任务把它提升为一等呈现。
- 你是本轮唯一 dev agent(H1),分支 agent/h1 已检出。**不 push、不删 worktree、不跑研究脚本、不碰 runs/(只读)。**

## 先例(必读)

- `scripts/export_terminal_data.py` 的 `_read_ledger`(约 line 432,READ-ONLY 读 ledger 的既有原语)+ `export_ledger_audit`(约 2419,面板注册/类别/data_health 全套先例)+ R1A 刚落地的 `export_score_diagnostics`(grep 定位,最近最完整的垂直切片先例:导出+四注册点+barrel+dict+契约测试)。
- `tests/test_score_diagnostics_panel_contract.py`(契约测试风格)。

## 交付物

### 1. `export_horizon_robustness()`(export_quarto_data.py 同区,或与 ledger_audit 同文件的 terminal 侧——按 score_diagnostics 先例就近)

- 用 `_read_ledger` 取 **latest** `event=="exploratory" and phase=="sensitivity_horizon"` 行(若无 → `_safe_export` 既有守卫跳过,不伪造)。
- 输出 `horizon_robustness.json`,形状(显式、可空字段如实):
```json
{"status":"ok","source_ts":"<ledger行ts,非生成时钟>","frozen_confirmatory_horizon":21,
 "horizons":[10,42],
 "phases":{"B":{"arm_enhanced":"arm_state","h10":{"enhanced_mean_ic":...,"base_mean_ic":...,"mean_diff":...,"ci_lo":...,"ci_hi":...,"dm_p_mbb":...,"null_holds":true},"h42":{...},"null_holds_both":true},
           "C":{...},"D":{...},"E1":{...,"arm_base":"arm_base_self"}},
 "horizon_robust_all":true,
 "null_criterion":"<行内原文>",
 "notes":"<行内原文,截断到 ~500 字符>"}
```
- 数值 `round(float(x),6)`;缺 phase/缺 horizon → 该处如实 null(不猜);E1 的 arm_base 字段保留(B/C/D 无)。

### 2. 四注册点(照 score_diagnostics 先例)

`_safe_export("horizon_robustness", ...)` + data_health manifest 行(类别选 `_DH_FROZEN`——仅 sweep 重跑才变,平时静止,诚实)+ `_dh_as_of` 分支(取 `source_ts`)+ `_API_LICENSE` source 映射("Aionis exploratory ledger row (repo MIT)","horizon-robustness sweep summary of the frozen h=21 nulls")。

### 3. barrel `web/src/data/aionis/index.ts`

显式类型 `HorizonRobustness`(逐字段对照导出形状含 nullability;phases 用 Record<string, ...> 与 CalibrationReliability 风格一致)+ import + `aionis` 注册。

### 4. dict.ts(zh/en 对称,track 块或新块)

`track.horizon.title`(Horizon 稳健性 / Horizon robustness)、`track.horizon.desc`(冻结确认 horizon 为 h=21;探索性 sweep 在 h=10/h=42 重估四相差分,全部 null 保持=冻结零结果对 horizon 不敏感)、`track.horizon.col.phase/diff/ci/dmp/verdict`、`track.horizon.verdict.holds`(null 保持)、`track.horizon.note`(EXPLORATORY 语义:h≠21=changed config,仅 exploratory ledger 行; arm_base 共享与 E1 特例一句带过)、`track.horizon.asof`(数据日期)。插值 `.replace` 模式。

### 5. /track 页呈现(读 `web/src/app/(dashboard)/track/page.tsx` 与其 view 组件结构后决定挂点)

- 一个紧凑 Card:标题+描述+**每个 phase 一行**的表(phase/arm_enhanced/h10 diff 与 CI/h42 diff 与 CI/两 horizon verdict 徽章)+ `horizon_robust_all` 总判定行 + note。verdict 徽章用语义 emerald(信任)不涉涨跌色。
- 挂点自由度:track 页既有 tab 结构内语义最合适的 tab(预计 calibration/validity 族),或页尾独立卡;保持既有 tab 路由/hash 行为不变。

### 6. 契约测试 `tests/test_horizon_robustness_panel_contract.py`(hermetic)

- 合成 ledger 行(测试内构造 tmp ledger?注意 `_read_ledger` 读固定路径——用 monkeypatch 或抽参,照仓内既有测试对 ledger 的处理方式)断言:latest 行选择(两行取新)、字段映射、缺 phase → null、全 null_holds 聚合。
- 真实已提交 `horizon_robustness.json`:status ok、horizons=[10,42]、四相齐、null_holds_both 全 true、与 data_health/api_catalog 注册一致、barrel 注册。
- 生成真实 JSON 并提交(命令:`uv run python -c "import sys; sys.path.insert(0,'scripts'); import export_terminal_data as m; m._safe_export('horizon_robustness', ...)"`,照 score_diagnostics 先例;若该先例生成命令形式不同,以实际为准)。
- 零 skip。

## 验证与提交(worktree 内;0xC0000142/fork 失败=本机已知病理,sleep 30-60 重试)

```bash
uv sync --all-extras
uv run pytest -q tests/test_horizon_robustness_panel_contract.py tests/test_web_terminal_data.py -x
uv run ruff check scripts/export_terminal_data.py scripts/export_quarto_data.py tests/test_horizon_robustness_panel_contract.py
cd web && node node_modules/typescript/bin/tsc --noEmit && node node_modules/eslint/bin/eslint.js src/data/aionis/index.ts src/i18n/dict.ts <你改的track组件文件>
```

全净后单原子 commit(分支 agent/h1)。报告:ledger 行 ts 与四相数字摘要、挂点选择及理由、测试清单、输出摘要。
