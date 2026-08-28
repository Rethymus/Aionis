# TASK-CR-F3 — code-review P1 修复:features/scripts/tests lane(P1-6 / P1-7 / P1-11)

- Lane:features/scripts/tests 代码修复(不触碰冻结产物;不跑研究脚本;全部改动配回归测试)
- 工作仓:git worktree(分支 agent/f3 已检出)。**不 push、不删 worktree。**

## P1-6 `src/aionis/features/panel_alignment.py` PIT 恒真式 no-op + 死断言(本批最重;主线已核实)

两个叠加缺陷(当前 HEAD 实测):
1. "PIT 过滤" `fund_df.merge(groupby(ticker)["filed_date"].max().rename("_max_filed")).query("filed_date <= _max_filed")` —— `_max_filed` 是该 ticker 的**全局最大**申报日,`filed_date <= _max_filed` 对每一行恒真 → **过滤是 no-op**;
2. 随后 `fund_cols` 排除了 `filed_date` 再合并 → `if "filed_date" in panel.columns` 永假 → `_assert_pit_boundary` **死代码**。

净效果:面板可能把 row_date 之后才申报的基本面带进当期特征(恰是 anti-leakage 红线)。

修法要求:
- 实现真 PIT:对每个 (row_date, ticker),只保留 `filed_date <= row_date` 的记录中 `filed_date` 最大的一条(merge_asof 或 sort+groupby 均可,确定性优先);无满足记录 → 该 (row_date,ticker) 基本面列为 null(诚实缺失)。
- 断言复活:在合并**前**对 fund_pit 断言 `filed_date <= 对应 row_date`(不要依赖 panel 带不带 filed_date 列);保留既有 `_assert_pit_boundary` 若它有别的调用语义。
- 回归测试(hermetic 合成帧,不需要真实数据):
  a. 两笔申报:filed 2020-01-10 与 2020-03-20,row_date=2020-02-01 → 必须用到 01-10 那笔(修复前会取 03-20);
  b. row_date 早于首笔 filed → 基本面为 null;
  c. 同日多 ticker 混合;
  d. 断言路径真的会触发(构造违规输入,验证 raise)。
- 先 grep 本函数的消费方(phase 管道哪个脚本调用),在报告中写明影响面;**不改任何冻结产物,不重跑研究**。

## P1-7 `scripts/track_b_a_run.py` config 绑定仅注释(主线已核实存活)

现状:注释写 "config #41/#42" 但无机制绑定(不计算配置 sha、不校验 ledger、不钉数据指纹)。最小诚实修法:运行时对特征列集+面板文件计算 sha256,写入输出摘要与 stdout(`[track_b] config_sha256=...`),若面板文件缺失则照既有模式 fail;**不引入 ledger 写入**(那是更大改动,超出本修复)。测试:hermetic 小面板帧跑函数路径,断言 sha 字段存在且稳定。

## P1-11 `tests/test_macro_headline.py` 4× `pytest.skip` 占位(lines 175-187,主线已核实存活)

违反仓库 DoD("No placeholder / test.skip")。四个测试都是 "Requires full ALFRED mock fixture - deferred"。修法:构造**最小 hermetic ALFRED 夹具**(只需要被测函数消费的字段形状;查 `conftest.py` 与被测 import 的 fixture 形状),替换 skip 为真实断言;若某测试确因缺失基础设施无法 hermetic 化,先与任务书冲突时选择:重写为对纯函数层的等价断言(不 mock 网络,只造输入帧)。**交付时 tests/ 内不允许残留 skip**。

## 验证与提交

```bash
uv run pytest -q tests/ -x            # 全套(worktree 需先 uv sync --all-extras)
uv run ruff check src/aionis/features/panel_alignment.py scripts/track_b_a_run.py tests/test_macro_headline.py
```

全套 pytest exit 0(0 skip 增量)、ruff 净后**单原子 commit**(分支 agent/f3),报告:P1-6 消费方影响面、每条修复说明、测试清单、pytest 实际输出摘要(含 passed/skip 计数变化)。
