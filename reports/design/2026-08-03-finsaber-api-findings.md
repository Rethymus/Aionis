# FINSABER 真实 API 发现（mount② 净成本回测集成 scope）

> 日期：2026-08-03
> 来源：直接 clone `waylonli/FINSABER`（main 分支，FINSABER-2）+ 读 README + examples/custom_dataset_example.py。
> 代理路径（finsaber-research ×2）因跨上下文/[1210] 屡失，故编排者亲自 clone 读取，持久化于此。
> 许可证：**Apache-2.0**（permissive，合规）。

## 仓库

- `https://github.com/waylonli/FINSABER`（KDD 2026 Datasets & Benchmarks Track，oral）。
- **PyPI 可装**：`pip install finsaber`（最干净的复用路径）。
- `finsaber/` 包：`data_util/`、`finsaber_bt.py`、`finsaber.py`、`strategy/{selection,timing,timing_llm}/`、`toolkit/`。
- FINSABER-2 = 包化回测框架：data loaders / execution models / metrics / result writers / selectors / strategy interfaces；含显式执行时点、复权 OHLC、slippage、liquidity caps、结构化产物、LLM 成本核算。

## 核心 API（从 custom_dataset_example.py 实证）

```python
from finsaber.data_util import FinsaberDataset
from finsaber.finsaber_bt import FINSABERBt
from finsaber.strategy.timing import BuyAndHoldStrategy

# 数据集：dict[date] -> {price: {ticker: {open, high, low, close, adjusted_close, volume}},
#                         news: {ticker: []}, filing_k: {}, filing_q: {}}
dataset = FinsaberDataset(data={...})

config = {
    "data_loader": dataset,
    "tickers": ["DEMO"],
    "date_from": "2024-01-02", "date_to": "2024-02-05",
    "setup_name": "...",
    "save_results": False,
    "silence": True,
    # slippage / liquidity / LLM-cost 配置项（README 列出，需读 finsaber_bt.py 确认精确字段名）
}
result = FINSABERBt(config).run_iterative_tickers(BuyAndHoldStrategy)
# result: {ticker: {"total_return": ..., ...metrics...}}
```

## Aionis 适配路径（mount② 集成 scope）

1. **装 dep**：`uv add finsaber`（Apache-2.0，permissive 合规）。
2. **构建 FinsaberDataset**：从 Aionis 的 `data/cache/phase_b_prices.parquet`（adjClose + volume）。FINSABER 需 OHLCV（open/high/low/close/adjusted_close/volume）；Aionis 仅 adjClose+volume → **近似**（open=high=low=close=adjusted_close=adjClose）或补抓 OHLC。news/filings 空字典。
3. **暴露 OOS scores**：`fit_track_b_baseline` 当前返回 ic_series + 月度收益，**未返回 per-(date×ticker) scores**。需扩展其 `all_scores` 到 `TrackBBaselineResult`（additive），以驱动 Strategy 选股。
4. **写 Strategy 类**：读 OOS scores → 月末 top-quantile 选股 + next-open 执行（复用 FINSABER execution_model，勿自造）。
5. **跑 `FINSABERBt(config).run_iterative_tickers(ScoreStrategy)`** → net metrics（total_return / Sharpe / max_drawdown / turnover / slippage cost / capacity；LLM cost=0 price-only）。
6. **存 `site/mount_metrics.json`** 加 `net_cost` 节 + 站点「回测净成本」卡。

## 评估

- **可行**：API 清晰，PyPI 可装，Apache-2.0；custom_dataset_example 直接示范了"Aionis 场景"（自带数据）。
- **代价**：中等偏重——装 dep + 暴露 scores + OHLCV 近似/补抓 + 写 Strategy + 跑。敏感点：扩展 fit_track_b_baseline（ignite 代码）+ 加 dep（pyproject）。
- **价值**：补全七主题⑥（净成本），把 gross Sharpe（~0.9）对照 net Sharpe（扣 next-open/slippage/liquidity 后）——诚实可交易性边界。
- **风险**：FINSABER-2 slippage/liquidity 精确 config 字段名需读 `finsaber_bt.py` 确认（README 列概念，字段名未在 example 完整示出）。

## 当前状态

- mounts ⑤（tearsheet/empyrical）+ ⑦（FF5/statsmodels）已上站点。
- mount②（FINSABER 净成本）：**API 已摸清（本文档），集成 scope 明确，待实施**。
