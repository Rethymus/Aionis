# TASK-CR-F2 — code-review P1 修复:ingest/data lane(P1-8 / P1-9)

- Lane:ingest/data 代码修复(不触碰冻结产物;全部改动配回归测试)
- 工作仓:git worktree(分支 agent/f2 已检出)。**不 push、不删 worktree、不跑真实抓取。**

## P1-8 `src/aionis/ingest/csi300_constituents.py::_parse_opt_in_opt_out_to_long`(主线已核实存活)

现状:`dates = pd.date_range(start=opt_in, end=opt_out, freq="D")` 闭区间——**剔除日(opt_out)当天仍生成成员行**。docstring 语义:"opt-out date is exact"(t > snapshot 查不到未来,但闭区间让 opt_out 当日仍在册)。指数剔除的 PIT 语义应当是 opt_out 日已不在指数内(半开区间 [opt_in, opt_out))。

修法要求:
- 改为半开语义:`pd.date_range(start=opt_in, end=opt_out - pd.Timedelta(days=1), freq="D")`(opt_in==opt_out 的畸形区间已被上游 `if opt_out < opt_in: continue` 防御,但 opt_in==opt_out-1 之类边界要测)。
- docstring 明确写死语义:"membership days are [opt_in, opt_out)——剔除日当天起不再是指數成员"。
- 回归测试:构造 opt_in=2020-01-01 / opt_out=2020-06-15,断言 06-15 **不在**成员集、06-14 在;NaT opt-out 封顶 snapshot 的行为保持;opt_in==opt_out 退化区间行为定死(空成员期)。
- **消费方核查**:grep 谁在用该 long 表(CN panel/universe 构建),确认无消费方依赖"剔除日仍在册"的旧语义;若有,如实报告并停在测试层(不改生产),把矛盾留给主线裁决。

## P1-9 `scripts/build_cn_price_panel.py` ever-member 池(需你调查后裁定)

原发现:"面板未做 PIT CSI300 成员过滤——横截面=历史 ever-member 池"。现状:源 parquet 本身是 `ashare_prices_csi300.parquet`(成员域在源侧),pivot 后未按 (date, ticker) PIT 过滤。**先调查**:
1. 谁消费 `cn_price_panel.parquet`(grep 全仓);消费方是否已有自己的 PIT 成员过滤(mask_panel_to_pit / universe_hanshof / membership 参数)?
2. 若消费方已按日过滤 → 本条判"误报/已在下游修复",只补一个说明性测试钉住"wide 面板是 ever-member 池"的事实+下游过滤责任,不改生产行为。
3. 若确无任何下游 PIT 过滤 → 在本脚本加 (date,ticker) 级 CSI300 成员过滤(读 csi300 long 表),配回归测试。
**改动最小化,调查结论写入报告。**

## 验证与提交

```bash
uv run pytest -q tests/ -x            # 全套(worktree 需先 uv sync --all-extras)
uv run ruff check src/aionis/ingest/ scripts/build_cn_price_panel.py
```

全套 pytest exit 0、ruff 净后**单原子 commit**(分支 agent/f2),报告:每条裁定+证据、消费方调查结论、测试清单、pytest 实际输出摘要。
