# TASK-H5 — model_inventory(SR 11-7 模型清单全集):ledger×冻结目录对账 → /model-health 清单表

- Lane:display/export 派生(runs/ 只读;零网络、零冻结写、零 now())
- 设计依据:`reports/design/2026-08-29-model-card-design.md`(SR 11-7 [B 级]:模型治理=清单+文档+验证;H4 卡片已覆盖"文档",本任务补"**清单**")
- 主线已核实的映射事实(你可直接依赖):
  - 4 个本地目录恰为四相 confirmatory runs:B=17245a75…(freeze 行 27/result 28)、C=a7fdb48f…(29/30)、D=d3158063…(33/34)、E1=ef321e9e…(35/37)
  - 另有 **11 条 config_committed 行无 confirmatory:first 且无本地目录**(track_b×3、baseline_ff5×1、baseline_rank×2、track_c×2 被取代、track_adaptive×3)
  - 每目录含 meta.json(config_sig/h6_deterministic/aionis_version/ts)与 differential.json
- 你是本轮唯一 dev agent(H5),分支 agent/h5 已检出。**不 push、不删 worktree、不跑研究脚本、runs/ 只读。**

## 交付物

### 1. `export_model_inventory()`(export_terminal_data.py,export_model_card 后)

- 用 `_read_ledger_rows` 扫描:`confirmatory:first` 行 → 每行 {phase, config_sig(全), freeze_row=config_committed 同 sig 的行号, result_row, freeze_ts/result_ts, local_dir_present(meta.json 可读), h6_deterministic/aionis_version(读 meta), **diff**(读同目录 differential.json 的 mean_diff/ci_lo/ci_hi/dm_p_mbb/null_holds——以实际键名为准,先读一个实例;缺键如实 null)};
- `config_only`:config_committed 行中 sig 无 confirmatory:first 且无本地目录者 → {phase, config_sig, row, ts}(诚实列示"已提交配置,本地无结果目录"——可能被取代或目录未保留,不猜测原因);
- `summary`:{n_confirmatory_runs(=5), n_local_dirs(=4), n_config_only(=11), all_null_holds(有 diff.null_holds 者全 true?如实)};
- `notes`:SR 11-7 清单语义一句话 + "runs/ 只读;无本地目录=诚实未知而非不存在";
- 数值 round 6 位;可空如实;`MODEL_INVENTORY_VERSION="v1"`;LF;零时钟(时间全取 ledger/meta)。

### 2. 注册四点(data_health `_DH_FROZEN`、as_of=最新 ledger 行 ts、_API_LICENSE 文案"Aionis research artifacts (repo MIT)" / "SR 11-7 style model inventory over the tracked ledger and frozen run directories")+ barrel 显式类型 + dict `inventory.*` zh/en。

### 3. /model-health:Model card 节之后加"Model inventory"节

- 确认 run 表(每相一行):phase/sig 前 12/freeze ts/H6/差分 mean_diff±CI/null 徽章(emerald=holds);本地目录缺失行诚实标注;
- config-only 折叠行(计数+说明一句,不逐行展开——11 行明细在 JSON 可查);
- 双语 i18n。

### 4. 契约测试 `tests/test_model_inventory_contract.py`(hermetic 零 skip)

- 合成 ledger+tmp 目录:行→目录匹配、freeze/result 行号解析、config_only 分类、缺 dir honest null、diff 缺键 null;
- 真实 `model_inventory.json`:runs 恰 5(B/C/D/E1/track_c)、local_dir_present 恰 4 true(主仓现实)、config_only 恰 11、diff 数字与各目录 differential.json 重算一致、注册一致;
- 生成真实面板并提交(命令照 model_card 先例)。**注意:主仓 runs/results 在,生成应成功;双跑 sha 一致写报告。**

## 纪律(违反=失败)

零手写数字;runs/ 只读;禁 Date/random/recharts/新依赖/红绿方向色;零 skip;无投资建议。

## 验证与提交(worktree 内;0xC0000142/fork 失败=本机病理,sleep 30-60 重试)

```bash
uv sync --all-extras
uv run pytest -q tests/test_model_inventory_contract.py tests/test_web_terminal_data.py tests/test_data_health_coverage_contract.py tests/test_model_card_contract.py -x
uv run ruff check scripts/export_terminal_data.py tests/test_model_inventory_contract.py
cd web && node node_modules/typescript/bin/tsc --noEmit && node node_modules/eslint/bin/eslint.js src/data/aionis/index.ts src/i18n/dict.ts <你改的model-health组件>
```

(H2 的 EXPECTED_PANELS 表需同步 +1 行 model_inventory——照 horizon_robustness 先例。)
全净后单原子 commit(分支 agent/h5)。报告:runs/config_only 解析清单、diff 实值摘要、双跑 sha、测试输出。
