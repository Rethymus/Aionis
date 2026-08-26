# TASK-DISP-H2 — /stock 实时价格面（display-only Worker 通路）

**Lane**: display（纯前端）。**优先级**: P1（post-parity roadmap H2）。
**工作目录**: worktree `F:\ZCodeData\Aionis-wa`（分支 `feat/stock-live-chart`，已建好 junction）。
**授权**: 业主 2026-08-26"多 agent 分工开发"指令。

## 0. 目标

参照站有、我们有意缺席的最后一块视觉模块：`/stock/[ticker]` 页的**实时价格图**。
现有 `workers/prices/` Cloudflare Worker 已经服务实时报价（页面 header pill 已显示
"N 秒前 · 价格 涨跌%"）。本任务把同样的 display-only 数据升级为一张小型走势图。

## 1. 前置核查（第一步必须做，结论写进报告）

1. 读 `workers/prices/`（wrangler.toml + src），确认 Worker API 的真实形状：
   - 只有最新 quote 还是有历史/日内序列端点？
   - 免费数据源（Tiingo IEX / Alpaca feed=iex）能给什么粒度？
   - 本地如何配置 Worker URL（`.env` / settings / 环境变量名实测）——页面 hook 在哪读它。
2. 读 `web/src/lib/live-prices.ts`（或同名 hook）与 `/stock` 页消费点。
3. **按核查结果三选一（诚实优先，禁止编造）**：
   - (a) Worker 有日内序列端点 → 直接渲染序列，标注 "display-only · 来源/延迟"；
   - (b) Worker 只有最新 quote → 渲染**本页打开以来的累计 tick 序列**（客户端真实采样累加，
     明确标注 "自页面打开起 N 个采样点"，刷新清零是诚实行为不是 bug）+ header pill 保持现状；
   - (c) 两者都不可行 → **停下来在报告里说明**，不要硬造一个假图表。

## 2. 交付物

- 新组件 `web/src/components/stock-view/live-price-chart.tsx`（命名可按代码库惯例微调）：
  面积图/折线，色用 `var(--up)/var(--down)` 涨跌约定体系（绝不硬编码语义色）；
  follow 项目格式层 `lib/format.ts`；显示来源 + as-of + "display-only" 徽章文案。
- 接入 `/stock/[ticker]` 视图合理位置（评分区之下、机构持有者区之上，或按视觉判断）。
- i18n：zh/en 新键 namespace 建议 `stock.live.*`（两语言键集严格对称）。
- 若触发绘制依赖：只用已有 recharts（376KB chunk 已被 stock 页加载，零新增成本优先）；
  引入新依赖需在报告中给出强理由。
- **0 Python 改动。0 ledger/frozen/config/prereg/OOS。**

## 3. 反泄漏铁律

- live 价格是 **DISPLAY ONLY**：新组件绝不允许被 `src/aionis/` 下任何研究模块 import；
  不落盘、不进任何面板 JSON、不进 gitignored 数据文件。这条线写在你改动文件的顶部注释里。
- Worker 不可达/超时：静默降级到现状（header pill 的既有降级行为），不得渲染错误占位满屏。

## 4. 验证（worktree 内可跑的子集）

```bash
cd F:\ZCodeData\Aionis-wa\web
npx tsc --noEmit          # 必须 exit 0
npx eslint src --max-warnings 33   # 0 error（33 条存量警告基数）
```

i18n 对称性自查：对比 zh/en 两个 dict 的新增键集合完全一致（grep 或临时 node 脚本皆可）。
build 归主线集成时统一跑（Turbopack 拒绝跨根 symlink node_modules——worktree 内 build 必败，别试）。

## 5. 工作纪律

- 小步增量 commit（Conventional Commits，如 `feat(display): ...`），只在本分支。
- 不要 push。不要动主仓 `F:\ZCodeData\Aionis` 的工作树。不要碰 docs/code-review/。
- 清理任何进程前先想 junction 铁律（绝不对含 junction 的目录 rm -rf）。

## 6. 报告格式

(a) Worker API 核查结论（端点/形状/env 名）；(b) 三选一裁决与理由；(c) 文件清单 +
每文件一句话；(d) 验证命令输出摘要（exit code）；(e) 你声明的冲突面（预期只有 dict.ts 追加键
与 stock-view 插入点）；(f) i18n 键清单 zh/en 对照。
