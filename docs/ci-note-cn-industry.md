# CI 接线草案 — CN 行业分类升级（baostock 证监会行业）

> **状态**：**DRAFT · 2026-08-20** · 主线集成时执行，本文档只是草案（worktree 分支
> `agent/cn-industry` 不改 `.github/workflows/`）。
> **关联**：`docs/data-intake-baostock-industry.md`（7-gate PASS，display-only）、
> `scripts/build_ticker_metadata.py`（实现）、`.github/workflows/refresh-terminal-data.yml`。

---

## 现状与目标

- 现有 workflow 第 205 行已运行：
  `uv run python scripts/build_ticker_metadata.py --no-cache`
- 升级后该脚本会**lazy import** baostock 拉取证监会行业分类（CN sector 从板块 tier
  → 行业，tier 保留为 `cn_tier` 列）。baostock **不是** `pyproject.toml` 依赖（沿
  `src/aionis/ingest/ashare_price.py` 的 lazy-import 先例），CI 环境没有它 →
  行业拉取会**优雅降级回 tier**（打印 warn，不失败）。
- 要让 CI 产出行业 sector，需要给该步骤临时挂载 baostock。

## 推荐改法（一行 diff）

```yaml
      - name: Build ticker metadata (names + sectors)
        run: uv run --with baostock python scripts/build_ticker_metadata.py --no-cache
```

`uv run --with baostock` 在运行时临时解析安装（已本地验证可用），**不触碰
`uv.lock`**，与 lazy-import 策略自洽。

### 备选（如果 owner 决定固化依赖）

主线跑 `uv add baostock`（生成 lock 变更 + 单独 commit），然后该步骤保持
`uv run python …` 原样。取舍：

| 方案 | 优点 | 缺点 |
|---|---|---|
| `--with`（推荐） | 零 lock 变更；baostock 保持"展示层可选依赖"定位；失败面最小 | 每次解析一次（秒级）；依赖声明分散在 workflow |
| `uv add` 固化 | 声明集中在 pyproject | baostock 进主 lock（研究 env 也背上它，违背"intentionally not a core dependency"先例） |

## 相关检查项（集成时顺手）

1. **`data/cache/cn_industry.parquet` 生命周期**：gitignored；CI 的 cache tar
   save/restore 会自然带上它，`--no-cache` 每日强制刷新（快照纪律 = G3 缓解）。
2. **`export_terminal_data.py` 的 `data_health` planned 卡**：
   `cn-industry-classification`（"planned, not built; license unverified"）已过时
   ——fetcher 已建、7-gate 已过（BSD，见 intake 文档）。集成时应移出 planned 列表
   或改写为已建成来源行（该文件多 agent 边界重叠，worktree 分支只动了 methodology
   两处字符串，此卡片留给主线）。
3. **姊妹文档 license 更正**：`docs/data-intake-ashare-price-baostock.md` 引用
   GitHub `baidstock/bs_stock`（MIT）——该 repo 404；官方 PyPI 分发 = **BSD**。
   两协议都在白名单、结论不变，但引用应在主线更正（见
   `docs/data-intake-baostock-industry.md` §G1 更正记录）。
4. **契约测试**：`tests/test_web_terminal_data.py::
   test_sector_breakdown_methodology_discloses_classification` 已强化（断言
   CSRC/证监会 披露），CI 无需额外步骤。
5. **降级路径验证**：无 baostock 时（本地默认）构建仍成功（回退 tier），导出
   `sector_breakdown.json` 的 methodology 会如实写出回退——这是 G6 诚实披露的
   一部分，不是错误。

## 边界提醒

- 本升级是 **display-only**：`build_ticker_metadata.py` 产物只被
  `export_terminal_data.py` 的展示层消费；baostock 不得进
  `features/` / `eval/` / `ingest/`（研究面）——AGENTS.md live-data 红线同型。
- ledger / frozen config / prereg：零接触。
