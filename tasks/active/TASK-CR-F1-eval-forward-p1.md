# TASK-CR-F1 — code-review P1 修复:eval/forward lane(P1-1 / P1-2 / P1-4)

- Lane:research/eval 代码修复(不触碰任何冻结产物;不跑研究脚本;全部改动配回归测试)
- 背景:`docs/code-review/SUMMARY.md` 15 条 P1,主线已逐条对照当前 HEAD 核实,本任务承接 eval/forward lane 的 3 条。工作仓:git worktree(分支 agent/f1 已检出)。**不 push、不删 worktree、不跑 next build/研究脚本。**

## P1-1 `src/aionis/eval/multiple_testing.py::harvey_liu_haircut`(主线已核实存活)

`p_raw = stats.norm.sf(z_obs)` 在 z_obs ≳ 38 时**下溢为 0.0** → `p_bonf = min(1, n_trials*0.0) = 0.0` → `z_bonf = ppf(1.0) = +inf` → `haircut_sharpe = +inf`,`haircut_pct = -inf`,`survives_bonferroni = True`。原审查判词:"灾难性消零 → +Infinity 且 survives=true(与自述结论相反)"。现有注释只处理了 p_bonf 饱和到 1 的 -inf 分支,没处理下溢分支。

修法要求(诚实呈现,不造精度):
- 检测 `p_raw == 0.0`(下溢);此时返回 `haircut_sharpe=None`、`haircut_pct=None`、新增字段 `p_raw_underflow=True`,保留 `z_obs/se/survives_bonferroni=True`(0.0 ≤ alpha 成立,技能存活是真实的,只是 haircut 数值不可计算)——**绝不返回 ±Infinity 冒充数值**。
- 回归测试:构造足够大的 sharpe/se 比触发下溢,断言上述字段;再加一个 p_bonf 饱和=1 的用例断言 -inf 分支的现有行为(已有注释语义)保持不变。

## P1-2 `scripts/phase_c_run.py` VIX 锚 sha 钉错文件(需你追踪裁定)

原发现:"冻结 config 的 VIX 锚钉错文件:实际输入未入 sha256"。当前 `shas` dict 钉了 `vix_cls.parquet`,但需你**追踪 VIX surprise 的实际构建输入**(grep VIX_KIND / vix surprise 的读取代码):若实际读取的是别的文件(或除 parquet 外还读别的),把 sha 钉改到真实输入集合(可新增 key,不删既有 key——ledger 契约只增不改);若核实当前已正确,如实记录"已修复/误报"并跳过。

## P1-4 `src/aionis/eval/forward_commit_runner.py` provider_cutoff 回退(部分修复,你裁定)

现状:line 278-279 已有注释"Use real provider_cutoff (owner-provided), not faked",且 `provider_cutoff_policy` 参数管道已接(AUD-06)。遗留问题:policy 要求真实 cutoff 而调用方未提供时,仍**静默回退 predict_ts**。先读 `src/aionis/eval/forward_live_readiness.py` 与 AUD-06 相关契约:若 readiness 已在外层强制,则**不改生产路径**,只补一个测试钉住"policy 严格要求 + 未提供 cutoff"的行为语义;若外层没管,则把回退改为 fail-closed(ValueError)并更新对应测试。改动最小化。

## 验证与提交

```bash
uv run pytest -q tests/ -x            # 全套(worktree 需先 uv sync --all-extras)
uv run ruff check src/aionis/eval/ scripts/phase_c_run.py
```

全套 pytest exit 0、ruff 净后**单原子 commit**(分支 agent/f1),报告:每条的裁定结果(修/已修/误报+证据)、新增/修改的测试清单、pytest 实际输出摘要。
