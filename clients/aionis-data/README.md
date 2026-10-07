# aionis-data

> **OWNER GATE（业主门）**：`uv build` 打包与 **PyPI 发布均未授权**——命名与发布策略
> 是业主决策（审计轮 221 / 波 8 指令明确"不执行任何对外发布"）。本目录只是仓库内的
> 客户端实现与测试；本地检视性构建可以，分发不行。

Aionis 公开数据 API（committed 面板 JSON 镜像，56 端点）的只读 Python 客户端——
OSAP `openassetpricing` 式便利层。**零第三方依赖**（stdlib urllib）。

公开 API 基址：<https://rethymus.github.io/Aionis/api/v1/>（目录：`/api-docs`）。
所有数据为展示层研究输出（PolyForm-Noncommercial-1.0.0）；本客户端不可能产生
样本外信号——这个项目的 null 就是产品。

## Vignette

```python
from aionis_data import claims, ic_series, panels, panel

# 1) 全部预注册主张（数字逐位来自 committed evidence_matrix 面板）
for key, c in claims().items():
    est = c.get("mean_diff", c.get("combined_ic"))
    print(f"{key:>8}: {est:+.4f}  CI [{c['ci_lo']:+.4f}, {c['ci_hi']:+.4f}]"
          f"  ledger #{c['ledger_row']}  prereg={c['prereg_doc']}")
#        B: -0.0008  CI [-0.0106, +0.0090]  ledger #28  prereg=docs/phase-b-preregistration.md
#       ...

# 2) 已实现 Track C 月度 rank-IC 序列
series = [(m, ic) for m, ic in
          __import__("aionis_data").combined_index()]
print(len(series), "realized months")

# 3) 任意面板 + 目录元数据（逐端点 license/as-of 溯源）
health = panel("data_health")
catalog = panels()          # 56 endpoints, status/freshness/as_of/license/source
```

离线/测试用法——注入 loader，测试零网络：

```python
from aionis_data import AionisDataClient
client = AionisDataClient(fetch_json=lambda url: my_cache[url])  # url -> parsed json
client.claims()
```

## API 一览

| 函数/方法 | 返回 | 数据源面板 |
|---|---|---|
| `panels()` | 56 个目录端点元数据（license/freshness/as_of/source） | `catalog.json` |
| `panel(key)` | 任意面板原样 JSON | `panels/<key>.json` |
| `claims()` | 5 个预注册主张（估计/CI/账本行/prereg 路径/config sig） | `evidence_matrix` |
| `ic_series()` | Track C 已实现月度 IC 行（month/us/cn/combined，null=未决） | `ic_monthly` |
| `combined_index()` | 便利：`[(month, ic)]` 非空月 | 同上 |

## 开发

```bash
# 根仓库内测试（hermetic，零网络；fixtures 驱动）
uv run pytest tests/test_aionis_data_client.py -q
```

许可：PolyForm-Noncommercial-1.0.0（与主仓一致，ADR-013）。
