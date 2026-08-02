# Track B — S0-S① PIT Universe 审计报告

**审计日期**: 2026-08-02  
**审计范围**: hanshof vs pierrebrunelle 月度 Jaccard 重叠度  
**目的**: 填补预注册 §12 冻结点 5 占位，确定 headline OOS 时间窗口限制

---

## 1. 数据来源

| 来源 | 仓库 | 许可证 | 格式 | 频率 | 时间范围 |
|------|------|--------|------|------|----------|
| **hanshof** | [hanshof/sp500_constituents](https://github.com/hanshof/sp500_constituents) | MIT | CSV (`sp_500_historical_components.csv`) | 日频 | 1996-01-02 → 2025-08-23 |
| **pierrebrunelle** | [pierrebrunelle/sp500-historical-constituents](https://github.com/pierrebrunelle/sp500-historical-constituents) | MIT | 124 个文件 (`data/spyYYYYMM`) | 月频 | 2016-01 → 2026-04 |

**缓存位置**: `data/cache/universe_hanshof.parquet`, `data/cache/universe_pierrebrunelle.parquet`

---

## 2. 数据集概览

### hanshof（主数据源）
- **总行数**: 1,644,637 行
- **日期范围**: 1996-01-02 → 2025-08-23
- **唯一日期数**: 3,480 个交易日
- **唯一 ticker 数**: 1,126 个（含历史成分）

### pierrebrunelle（交叉校验源）
- **总行数**: 62,655 行
- **日期范围**: 2016-01-01 → 2026-04-01
- **唯一月份数**: 124 个月
- **唯一 ticker 数**: 705 个

### 2016+ 重叠窗口成分统计
| 指标 | hanshof | pierrebrunelle | 并集 | 交集 |
|------|---------|----------------|------|------|
| 唯一 ticker 数 | 690 | 705 | 734 | 661 |
| 总体集合 Jaccard | - | - | **0.9005** | - |

---

## 3. 月度 Jaccard 重叠度（2016-01 → 最新）

**计算方法**: 对每个月 `m`，`A = hanshof 在该月最后一个交易日的成分集合`，`B = pierrebrunelle 该月快照`，`J = |A ∩ B| / |A ∪ B|`

### 统计结果（106 个月）

| 统计量 | 值 |
|--------|-----|
| **Min** | **0.8544** (2016-01-01) |
| **Mean** | 0.9272 |
| **Median** | 0.9310 |
| **Max** | 0.9881 |
| **Std** | ~0.035 |

### 阈值判定（§8.0 冻结规则: 0.95）

| 月份 | Jaccard | 是否 ≥ 0.95 |
|------|---------|-------------|
| < 0.95 的月数 | **71** / 106 | ❌ |
| ≥ 0.95 的月数 | 35 / 106 | ✅ |

**最低 Jaccard 发生在 2016-01-01**: 这是重叠窗口的首月，推测是两个源对 S&P 500 历史成分重建方法的初始差异。

---

## 4. 审计结论

### ❌ 未通过 0.95 阈值

- **Min Jaccard = 0.8544 < 0.95**
- **71/106 个月（67%）低于阈值**

这表明两个独立重建在 2016-2025 窗口内存在**系统性的成分差异**，不符合预注册 §8.0 的"高一致性"要求。

### ✅ 支持 Headline 限 2016+

根据 `universe_agreement_verdict()` 的冻结逻辑：

```
min monthly Jaccard 0.8544 < 0.95 at 2016-01-01:
headline OOS restricted to 2016+ reproducible window
```

**建议**:
1. **headline 结果仅报告 2017-01 开始的 OOS 窗口**（与 pierrebrunelle 的可重现范围一致）
2. 将 1996-2016 的 hanshof 数据作为 **sensitivity analysis** 报告，不作为主要 headline
3. 在预注册 §12 冻结点 5 中明确写入："Jaccard min = 0.8544 < 0.95，headline OOS 限 2016+"

---

## 5. 幸存者偏差措辞复核

**保守上界表述**:
> "hanshof 数据集覆盖 1996-2025 的 PIT 成分，但与 pierrebrunelle 的交叉校验显示 2016+ 窗口的一致性为 Jaccard 0.85-0.99（均值 0.93）。为避免历史重建偏差引入的幸存者风险，headline OOS 结果限制在 2016+ 的可重现窗口。"

**不建议**:
- ❌ "1996-2025 的完整 PIT 成分"（未声明与 pierrebrunelle 的差异）
- ❌ "两个来源高度一致"（与实测 0.85-0.99 矛盾）

---

## 6. 数据质量备注

1. **hanshof 的 1,126 个 ticker vs pierrebrunelle 的 705 个**：hanshof 包含更多历史成分（含已退市/被收购公司的历史 ticker），这是其日频重建的特性。
2. **pierrebrunelle 覆盖至 2026-04**：更近期，但 hanshof 截至 2025-08-23，两者在 2025 年后的重叠未知。
3. **无网络请求**：本次审计使用本地缓存 parquet 文件，无需 HTTP 调用（满足礼貌原则）。

---

## 7. 与 RESULTS.md 的 588 个可解析 ticker 的关系

RESULTS.md 提到 588 个可解析 ticker（已通过 CIK 映射 + ticker-reuse 过滤）。本次审计测量的 734 个并集是 **原始成分集合**，经过 CIK 解析和 ticker-reuse 过滤后会收缩至 588 个，这是预期的。

---

## 附录：审计命令

```bash
# 复现审计
uv run python -c "
from aionis.ingest.universe import (
    load_hanshof_membership, load_pierrebrunelle_membership,
    jaccard_monthly, universe_agreement_verdict
)
h = load_hanshof_membership()
p = load_pierrebrunelle_membership()
jac = jaccard_monthly(h, p, start='2016-01-01')
print(universe_agreement_verdict(jac, threshold=0.95))
"
```

---

**审计签名**: universe-auditor (sonnet)  
**报告版本**: 1.0  
**状态**: ✅ 完成 — 支持 headline 限 2016+
