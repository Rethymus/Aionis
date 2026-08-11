# 范式 α 迁移清单 — ECD 效度论证链落地（逐文件 spec，业主审后分批执行）

> 上游决策：业主 2026-08-12 选 **范式 α**（见 `2026-08-12-terminal-ia-paradigm-shift.md`）。
> 本文档是**逐文件迁移规范**，业主审通过后我分批 commit。**纯展示层 `web/src/`，0 ledger /
> frozen panel / config / OOS / data 改动**。遵循 `aionis-terminal-ia-paradigm-ecd`。

## 0. 核心原则（每一步都校验）

1. **消灭一切编号** ①②③④⑤⑥ / L0-L4 / ①-⑥ role。
2. **弃用中文角色词** 定调/定标/佐证/问责/定向/边界 → 改用**科学论证词**：语境 / 证据 / 效度 / 裁决 / 守卫。
3. **不删数据、不删组件**——只重组 nav 分组、i18n key 文案、header tagline、overview 可视化。
4. **4 个 hub 路由（regime/picks/confirmation/track）保持 URL 不变**（软重定向友好，业主前两轮要求可回退）。
5. **每个面板头加 provenance 角标位**（as_of 已存在；本批只确保 header 统一渲染它，不新建数据）。

## 1. α 链段 → 路由 → 组件映射（权威表）

| α 链段（zh / en） | 旧 hub | 路由（URL 不变） | 内含 tabs/组件 | 不变数据 |
|---|---|---|---|---|
| **语境 / Context** | 旧"① 定调" | `/regime` | market · positioning(COT) · taco · macro(ThemeSlice) | ✓ |
| **证据 / Evidence** | 旧"② 定标"+ "③ 佐证"合并 | `/picks`（核心证据）+ `/confirmation`（独立佐证源） | picks · sectors · conviction · factors(ThemeSlice) ‖ smartmoney · insiders · reddit · news(ThemeSlice) | ✓ |
| **估计量 / Estimand** | （无独立路由，由 picks+IC 共同定义） | 概念段，在 overview 可视化 | — | — |
| **效度 / Validity** | 旧"④ 问责"前半 | `/track` | calibration · power-floor · model-health · cost(ThemeSlice net_cost) | ✓ |
| **裁决 / Verdict** | （并入 track 与 themes） | `/track#evidence` + `/themes` | evidence-wall · themes(method) · bps-sweep | ✓ |
| **守卫 / Guard** | 旧"⑥ 边界" + 角标 | `/discipline` + 每面板角标 | discipline(PIT/embargo/H6) · evidence | ✓ |

> **关键重组**：旧"佐证(confirmation)"与"定标(picks)"在 α 里同属**证据段**（一个是模型核心证据、
> 一个是独立佐证源），但**保持两个路由**——URL 不变、可回退；只是 nav 分组 label 从"②/③ 定标佐证"
> 改成"证据（核心）/ 证据（佐证）"或合并为一个 Evidence 组下两条。**推荐：合并为一个 `证据 / Evidence`
> nav 组，内含 2 条目（核心证据 → /picks，独立佐证 → /confirmation）**——这样 nav 从 5 组降到 4 组，
> 且消灭"定标 vs 佐证"的人为分裂。

## 2. 最终 nav 结构（4 组 + 总览 + 参考，全无编号）

```
总览 / Overview                    → /dashboard
───────
语境 / Context                     → /regime
证据 / Evidence                    → /picks        (核心证据)
        └ 独立佐证 / Corroboration → /confirmation (佐证源)
效度 / Validity                    → /track        (校准·功率·漂移·成本)
守卫 / Guard                       → /discipline   (PIT·embargo·H6·证据墙)
───────
参考 / Reference                   → 研究方法外链
```

## 3. `dict.ts` 文案改写（59 处编号/角色词）—— 最敏感，逐类列

### 3a. nav.group.* （`dict.ts:8-17` zh / `429-438` en）
| key | 旧值 | 新值（zh） | 新值（en） |
|---|---|---|---|
| `nav.group.regime` | `① 定调 · 市场制度` | `语境 · 市场制度` | `Context · market regime` |
| `nav.group.picks` | `② 定标 · 选股决策` | `证据 · 核心证据` | `Evidence · core` |
| `nav.group.confirm` | `③ 佐证 · 另类信号` | `证据 · 独立佐证` | `Evidence · corroboration` |
| `nav.group.track` | `④ 问责 · 诚实业绩` | `效度 · 测量可信度` | `Validity · measurement trust` |
| `nav.group.discipline` | `反泄漏纪律（已并入问责）` | `守卫 · 反泄漏纪律` | `Guard · anti-leakage` |
| `nav.group.themes` | `研究架构（已并入…）` | `研究方法 · 论证链全貌` | `Method · the full argument chain` |

### 3b. hub.intro / loop.* （`dict.ts:19-26, 440-447`）
- `overview.loop.title`: `研究闭环 · 四问` → `效度论证链 · 一条主张的旅程`
- `overview.loop.subtitle`: `定调 → 定标 → 佐证 → 问责` → `语境 → 证据 → 效度 → 裁决（守卫横贯）`
- `overview.loop.feedback`: 删去 `④ … ①` 编号 → `裁决回灌语境：每一轮论证收紧下一次主张`
- `regime_hub.intro` / `picks_hub.intro` / `confirmation_hub.intro` / `track_hub.intro` / `discipline_hub.intro`：
  改写首词（定调→语境、定标→证据、佐证→独立佐证、问责→效度、边界→守卫），**正文 science 不变**。

### 3c. 各模块 .role （`dict.ts:27-45, 448-466`）—— 19 处全改
模式：`① 定调 · …` → `语境 · …`；`②/③ 定标/佐证 · …` → `证据/独立佐证 · …`；
`⑤ 问责 · …` → `效度 · …`；`⑥ 边界 · …` → `守卫 · …`。逐条在执行批里改。

### 3d. themes.funnel L0-L4 重映射（`dict.ts:137-156, 558-577` + `themes-funnel.tsx`）
**复用非重写**：L0-L4 结构保留，只把 label 从"漏斗层"重映射为"论证链段"：
- L0 → `语境层 / Context`（不改 desc 实质）
- L1 → `证据 · 特征层 / Evidence · signals`
- L2 → `估计量 · 模型产出 / Estimand · model output`
- L3 → `效度 · 验证 / Validity · is it luck`
- L4 → `裁决 · 成本净值 / Verdict · net of cost`
`themes-funnel.tsx` 的 `LAYERS[].titleKey/descKey` 指向新 key；`n:0..4` 数字保留为内部 id（不显示编号符号）。

## 4. overview 重设计（`overview.tsx` FunnelCards）

`FunnelCards`（`overview.tsx:185-286`）从"四枢纽卡 ①-④"改为**论证链横向可视化**：
- 4 张卡重排为 **语境 → 证据 → 效度 → 裁决**，去掉 `n: "①".."④"` 角标，改用箭头 `→` 连接（复用现有
  ArrowRightIcon，已 import）。
- 卡的 stat（VIX / top pick / filings / ECE）保留——它们正好是各段的代表量。
- 底部 `overview.loop.feedback` 横条改"守卫带"：PIT · embargo · H6 · provenance 四个徽章横贯（视觉上
  表达 Guard 横护全链，而非独立第 5 卡）。
- 守卫（discipline）从独立卡移到底部横条 + nav 独立组（双重可达）。

## 5. app-sidebar.tsx（`app-sidebar.tsx:28-54`）

navRegime/navPicks/navConfirm/navTrack 四组 → 按本清单 §2 重组为 **Context / Evidence(含 corroboration 子项) /
Validity / Guard**。`NavMain` 组件不变（支持 items 数组，confirmation 作 picks 组的第二条目即可）。

## 6. hub 路由 header（4 文件 `regime/picks/confirmation/track/page.tsx`）

每个 header 的 `<p>` 从 `t("nav.group.X")` + `t("X_hub.intro")` 改为新 key。**tab 内容、组件、hash 路由全不变**。

## 7. 独立路由（calibration/power-floor/model-health/sectors/conviction/smartmoney/insiders/reddit/positioning/taco/market/evidence）

**这些 URL 保留可达**（防外链断裂 + 可回退），但**从主 nav 移除**（它们已是 hub 的 tab 内容，主 nav 不该
重复列出）。若业主坚持全部保留在 nav，则归入对应 α 段的子菜单——**默认移除主 nav、靠 hub tab 可达**。

## 8. 执行批次（每批 tsc+build 绿 → commit → 待续）

| 批 | 内容 | 风险 | 可回退 |
|---|---|---|---|
| **B1** | `dict.ts` 文案改写（59 key，zh+en） | 低（纯文案） | git revert |
| **B2** | `app-sidebar.tsx` + 4 hub `page.tsx` header 重分组 | 低 | git revert |
| **B3** | `overview.tsx` FunnelCards → 论证链可视化 + 守卫横条 | 中（布局） | git revert |
| **B4** | `themes-funnel.tsx` + `themes-view.tsx` L0-L4 重映射 + `theme-slice.tsx` 注释更新 | 低 | git revert |
| **B5** | 独立路由从主 nav 移除（保留 URL） | 低 | git revert |

每批：`tsc --noEmit` + `next build` 双绿才 commit；Conventional Commits；**不碰** Python/ledger/config/data。

## 9. 待业主确认（执行前最小必要）

1. **§2 nav 合并 confirmation 进 Evidence 组**（推荐）vs 保持独立第 5 组？
2. **§7 独立路由移出主 nav**（推荐，靠 hub tab 可达）vs 全部留主 nav 作子菜单？
3. **§4 守卫**：底部横条 + 独立 nav 组（推荐，双重可达）vs 只留其一？

回答后我从 B1 开始。**不回答我可按推荐默认推进**（§2 合并 / §7 移除主 nav / §4 双重可达）。
