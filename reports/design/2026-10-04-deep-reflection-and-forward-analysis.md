# 深度反思与前瞻分析（轮 155）— 呈业主

> 方法：44 轮实战（111→154）逐面审计的积累 + 外部情报面（Interop 2026 / Next 16.3 / 金融 UX 2025-2026 趋势）交叉。
> 诚实地回答五个问题：疏漏在哪、什么没把握、什么会先坏、什么值得做、流程怎么更高效。

---

## 一、明显疏漏 / 没意识到的地方

### 1. 数据管线的单机单点故障（最大结构性风险）

晚间通道、10-31 影子月、10-06 满月评估——全部依赖**这一台 Windows 主机**在线。
如果主机硬件故障、网络永久变更、或业主长期出差不带电脑，整条新鲜度管线停摆。
GitHub Actions 兜底因计费退役了；`docs/ops-local-refresh.md` 的备用路径需要手动触发。

**现状**：无第二 runner。无冷备方案。10-01 影子 runbook 因宿主休眠丢失过一次（轮 104 补跑）。
**建议**：文档化"主机不可用 > 48h 的降级 runbook"（手动触发 CI workflow_dispatch / 或者冷备到笔记本）。

### 2. PAT 过期的静默推送失败

通道用业主 PAT 推送。PAT 有过期时间（GitHub 默认 30/60/90 天）——过期后 `git push` 会静默失败（lane 在 `commit_and_push` 的 `push.returncode != 0` 路径中止）。`--doctor` 六层体检检查推送凭据，但**可能不检查 PAT 剩余有效期**。

**建议**：在 doctor 层加 PAT 过期时间检查（`gh api user` 的 200/401 可判存活，但有效期需查 Settings → Developer settings 手动确认）。

### 3. 账本无独立备份

`runs/ledger.jsonl` 是项目的核心审计链——它已被 git 追踪并推送到 GitHub，**但 GitHub 本身不是备份系统**（force-push / 账号被盗 / repo 意外删除均可丢失）。无第二个 remote。

**建议**：周期性（每周/每月）`git push backup`（另一 Git 服务或本地加密盘），低成本高保险。

### 4. 10-31 影子月的 membership 依赖

9-30 影子月 fail-closed 于 `predict_session_not_in_panel`——membership 数据（来自 Wikipedia 修改表）当时已扩展到 2026-09-01。10-31 影子月需要十月末的 membership。如果 Wikipedia 的"2026 年 S&P 500 变更"页面在 10-31 前尚未更新十月变更，`extend_membership` 将无法覆盖到月末 → 再次 fail-closed。

**现状**：轮 104 补跑已证 fail-closed 是合格结论（诚实入册），10-31 证据包将如实呈现。但这意味着**影子月可能连续两次 fail-closed**，headline GO 评估需要两个"readiness PASS"月的判据可能再次无法满足。

**建议**：轮 143 任务书已含此风险的如实呈现；可在 10-31 证据包中将"membership 上游滞后期"列为已知边界条件。

### 5. 每页 4.4MB 传输量

轮 114 的数据：market 页 transfer = 4,631 KiB（其中 JS ~3.5MB）。性能战役解决了 TBT（执行时序），但**传输量未下降**（Next 静态导出预载全部动态 chunk——轮 121 天花板）。对返回访客（有浏览器缓存）无影响，但首次访问在慢网络下仍重。

**根因**：Next 16 静态导出的预载行为 + 1500 页的路由树。
**缓解路径**：`next/dynamic` 已做；进一步需 `loading.tsx` 流式或 PPR（部分预渲染）——但 PPR 与 `output: 'export'` 不兼容。此为框架层限制，非项目层可解。

### 6. Streamlit 无认证

仪表盘读取冻结研究结果。目前仅本地运行——安全。但如果未来通过网络暴露（Streamlit Cloud / 反向代理），研究结果将公开可访问。

**建议**：文档化"Streamlit 仅限本地运行"的边界（实际上 docstring 已暗示，但显式声明更安全）。

---

## 二、没把握 / 低置信度的部分

| 项 | 不确定什么 | 风险 |
|---|---|---|
| **10-31 readiness** | membership 上游（Wikipedia）十月更新是否及时 | 连续两次 fail-closed → headline GO 判据无法满足 |
| **PR #99058 修复范围** | 是否覆盖路由组 + Windows 场景 | 合并后本地 404 可能未归零（需实测） |
| **VT 实际 UX 效果** | 采纳了但未做用户级 A/B | 纯理论收益 |
| **Speculation Rules 命中率** | 合成探针无法验证（CDP 限制）；人工验证待业主 | 预渲染可能实际从未命中 |
| **Next 16.3 Instant Navigations** | 与本仓 Speculation Rules + VT 的交互未调查 | 可能重复/冲突 |
| **npm audit 完整性** | `--prod` 只查生产依赖；devDependencies 的 browserslist 高危**已由 overrides 覆盖**（全量 audit 也应归零） | devDeps 供应链风险残留（构建机面） |

---

## 三、方案失效的最可能断裂点（按概率 × 影响排序）

| # | 断裂点 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| 1 | **主机不可用**（硬件/网络/出差） | 中 | **全部新鲜度停摆** | 降级 runbook（建议文档化） |
| 2 | **上游数据源格式漂移**（EDGAR/Wikipedia/Sina/Tiingo 改版） | 中 | 对应面板停更 | 优雅降级设计内（retain committed）；格式变化需代码修 |
| 3 | **PAT 过期** | 中高（时间必然） | 推送静默失败 | doctor 检查；建议加有效期提醒 |
| 4 | **Next.js 升级破坏静态导出** | 低中（每次大版本） | 构建失败/预取 404 | 已锁 16.3.8；升级时全量回归 |
| 5 | **GLM 配额/停服**（10-31 forward trigger 期间） | 中 | 边缘提取降级 | 自愈+缓存+快速软失败（轮 149 预案） |
| 6 | **GitHub Pages 政策变更** | 低 | 全站部署停 | 可迁移 CF Pages（架构已有文档） |

**最先坏的**：不是代码 bug（四十四轮审计后代码面极健壮），而是**基础设施层**——主机不可用 > PAT 过期 > 上游格式变更。这三者的共同特征是**都不在代码控制范围内**。

---

## 四、亮眼功能建议（按投入/回报排序）

### A. 自选股 Watchlist（最高性价比）

**现有数据**：冻结评分（picks.json）+ 实时价格（Worker）+ 全股票页（1500 页）。
**做法**：客户端 localStorage 保存用户自选 ticker 列表 → /picks 和 /stock/[ticker] 页显示自选标记（星标）→ /dashboard 侧边栏显示自选价格实时浮层（Worker 已有 30s TTL 端点）。
**为什么亮眼**：这是金融终端最核心的用户粘性功能——"我的股票"永远比"全部股票"更令人回访。
**成本**：~1 天（localStorage hook + 星标 UI + 侧边栏组件）。
**边界**：纯客户端 localStorage，零服务端状态，零反泄漏风险。

### B. 数据新鲜度 ticker（信任可视化）

**现有数据**：data_health.json 的 per-panel as_of（每晚更新）。
**做法**：web 终端顶部导航栏加一个紧凑的"数据水位"指示器——绿色圆点 + "as of Xh ago"，hover 展开逐面板 as_of 明细。
**为什么亮眼**：反泄漏卖点的可视化兑现——"你能看到我有多新鲜"，是信任锚。
**成本**：~半天（组件 + data_health 面板接线）。
**边界**：display lane。

### C. 交互式 IC 探索器（atlas 升级）

**现有**：atlas 页静态 SVG（确定性设计，防泄漏）。
**做法**：SVG 图表加 hover tooltip（逐月 IC 值 + 区间着色 + in-band 标记）。**不改变数据**，只加交互层——静态 SVG 保留为打印/无 JS 降级。
**为什么亮眼**：研究深度的交互展示——"你能探索每一个月的 IC 值"。
**成本**：~1-2 天（tooltip 组件 + 数据接线）。
**边界**：display lane；数据不变，仅加交互。

### D. 引用导出/分享（provenance 链条可携带）

**现有**：每个面板/图表的 as-of 水位 + 账本行号。
**做法**：每个面板卡加"复制引用"按钮——生成一段 markdown（面板名 + as_of + 账本行 sha256 链接）到剪贴板。
**为什么亮眼**：把反泄漏的可信度变成**可分享的社交货币**——"这是我的数据出处，你可以自己查账"。
**成本**：~半天。
**边界**：display lane。

---

## 五、全流程效率改进

### 当前流程（已优化项 ✓）

- `/` 直渲 dashboard ✓（轮 116，redirect 税消除）
- 搜索为主要导航（home search + ⌘K 共享索引）✓
- Speculation Rules hover 预渲染 ✓（轮 117）
- VT 页面切换过渡 ✓（轮 134）
- sitemap/robots SEO ✓（轮 111/145）

### 可改进项

| 改进 | 做法 | 效果 |
|---|---|---|
| **stock → picks 回链** | /stock/[ticker] 页显示"该股在 Top 10 Picks 中的排名与评分"（如果存在）——反向促进 picks → stock 的已有链接 | 用户发现某股后想看排名，当前需手动回 picks 页 |
| **atlas → track 深链** | atlas 的 verdict 卡点击直接跳到 /track#evidence（已实现）/track#calibration（可加） | 减少从结论到证据的导航层级 |
| **面板 ↔ 原始账本交叉链接** | 每个面板卡加"查看账本行"链接（ledger_audit.json 已有行号映射） | 可信度即时验证 |
| **键盘导航一致性** | ⌘K 面板已支持；但 tab 切换（/track、/regime 的多 tab 页）无键盘快捷键 | 键盘用户的效率 |

---

## 六、外部情报面结论

| 源 | 发现 | 本仓行动 |
|---|---|---|
| **Next 16.3 stable** | "Instant Navigations" 新特性 | **调查项**：与本仓 Speculation Rules + VT 可能重叠/互补 |
| **Next 16.4 canary** | RSC 404 修复未见 | 观察项维持（PR #99058 追踪） |
| **金融 UX 2025-2026** | 实时流/交互分析/agentic workspace | 实时流已有（Worker）；交互分析=亮点功能 C；agentic 与反泄漏纪律正交 |
| **OpenBB WorkspaceBench** | agentic finance workspace 评估 | 本仓的静态 frozen 设计是**故意的**（防泄漏）；交互分析在 display 层可行 |

---

## 七、总结

**最需要警惕的**：不是代码（四十四轮审计后极健壮），而是**基础设施层的三件事**——主机不可用、PAT 过期、上游数据源变更。三者均不在代码控制范围内，文档化降级路径是当前最高性价比的防御。

**最值得做的功能**：Watchlist（用户粘性）> 数据新鲜度 ticker（信任可视化）> 交互式 IC 探索器（研究深度展示）> 引用导出（可信度社交货币）。

**流程效率的瓶颈**：不在导航（已优化），在**交叉链接密度**——面板间的语义关联（stock→picks 排名、atlas→track 证据链、面板→账本行）还可以更密。

---

*边界：本分析为读+搜+写文档，不改代码/配置/测试。轮 155 docs lane；0 ledger/0 frozen/0 OOS。*
