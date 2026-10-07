# Web 终端性能战役总结（轮 111~125，2026-10-02）— 呈业主

> 方法论：每轮均为「研究（一手源）→ 实施 → 本地 basePath-junction A/B 双跑实测 →
> 协议 §4 视觉/DOM 闭环 → 发布 → 线上多跑取中位 → 入册」；null 结果与正收益
> 同等入册。全部原始数据：`reports/audits/2026-10-02-lighthouse-wcag-audit.md`
> （逐轮附录）+ gitignored 的 `runs/lh*.json`。

## 一、上线优化（12 项）

| # | 优化 | 轮 | 效果（线上中位） |
|---|---|---|---|
| 1 | sitemap.xml + robots.txt（1501 URL，.html 形态） | 111 | SEO 100；双 200 |
| 2 | WCAG 修复（frost 滑条装饰化/对比度令牌/内容即名） | 112 | atlas a11y 89→**100** |
| 3 | atlas content-visibility（下折三区块） | 112 | 战役首刀（-32% 线上） |
| 4 | market LazyMount+dynamic（四张 recharts 卡） | 114 | TBT **-42%**（本地 -38% 线上中位） |
| 5 | `/` 直渲 dashboard（redirect 壳退役）+ 壳层上提 | 116 | redirect 链路税（~2.4s）结构性消除 |
| 6 | Speculation Rules 全站 hover 预渲染（/Aionis/* moderate） | 117 | Chrome 官方"静态多页站理想用例"；全页在墙 |
| 7 | atlas divergence 手术式 SVG 拆分（表格留 SSR） | 118 | atlas 线上 3,280→1,879 |
| 8 | atlas claims 同款拆分（程序化逐行切片） | 119 | atlas 线上 →**1,349**（战役累计 **-72%**，4,820 起） |
| 9 | /track、/regime per-tab dynamic | 121 | 各 -11%（线上 858/753） |
| 10 | /calibration 图表级拆分 | 122 | **-40%**（线上中位 425） |
| 11 | /track 复用红利（零新代码） | 123 | 线上 858→**333（-61%）** |
| 12 | /confirmation per-tab dynamic | 124 | 本地 -28%（线上未证，保留） |

**健康页（≈壳层地板 230~310ms，不动）**：dashboard、heatmap、shelf、
power-floor、discipline、quarterly、evidence、model-health。

## 二、如实入册的 null / 否决（11 组）

| 项 | 轮 | 结果 |
|---|---|---|
| ci.yml uv 缓存 | 111 | 冷装 22s vs 缓存 21s——null，回滚+数据入册 |
| cv 扩展 dashboard | 113 | 前置 null（TBT 220ms 无天花板） |
| cv 扩展 market | 113 | 实测 TBT +20%——containment 微害，回滚 |
| 框架级优化（⌘K 懒挂载等） | 116 | 消融定界：壳层地板 250ms、⌘K 份额≈0——null |
| atlas 整块 LazyMount | 115 | 天花板仅 -10% 对 SSR 内容损失——内容优先否决 |
| picks cv | 120 | 1,840~2,190 vs 1,747——null 偏害回滚 |
| picks 行级拆分 | 120 | 评估过不修（内容优先张力） |
| confirmation 线上复现 | 124 | 本地 -28% 线上未证——保留+分野入册 |
| smart-money 单图拆分 | 125 | **净害 +300ms**（4 跑+对照页证无争用）——回滚 |
| home LCP（/redirect） | 115 | 查明根因→简报三选项→轮 116 选项 B 落地（先否后成） |
| 本地双峰归因 | 116 | 首判"伺服伪影"撤销——真因=TBT 交付交错敏感性 |

## 三、四条实测边界（工具选择规则）

1. **cv 阈值 ≈ 万级 DOM**：content-visibility 仅在布局/绘制密集且 DOM 足够大时
   获益（atlas 7,162 有效；picks 2,345 无效；market 脚本密集微害）。
2. **静态导出预载天花板**：Next 静态导出预载路由全部动态 chunk——transfer/主线程
   不因拆分下降，收益仅来自执行时序移出 TBT 窗（纯时序收益在线上会被网络窗方差
   吸收，见边界 3）。
3. **本地/线上分野**：本地 A/B 是裁决仪器；线上必须多跑取中位（单跑网络慢窗可
   伪影 ±2s）；结构性拆分线上可复现，纯时序型未必（confirmation）。
4. **图表主导性判定**：图表级 dynamic 拆分仅在图表为页面主导成本时获益
   （calibration/market ✓；表格主导页上的单小图 ✗ 净害）。

## 四、方法论沉淀

- **逐字切片纪律**：SVG/JSX 迁移一律程序化按行切片或逐字 diff 校验（轮 118
  PanelFrame 三处偏差、轮 125 两次 tsc 拦截均由此防住）。
- **复用扇出优先**：排队新工程前先查组件复用面（轮 123 零代码 -61%）。
- **对照页纪律**：性能测量异常时先跑同窗对照页排除宿主争用（轮 115/125）。
- **staged 完整性**：多 pathspec 的 git add 出错即整条失败——提交前后双验
  （轮 116 事故的教训）。
- **诚实报告**：null 与正收益同表；估算上限与实收并列（轮 118/119）。

## 五、第二战役：载荷减重（轮 192-201，2026-10-05/06）

> 触发：2026-03 起传 CWV 全站计分（慢页拖全站）→ 1,503 页全量 JS 画像发现
> **共享数据 chunk 2.70MB 挂在每一个路由（含 404）**——barrel 把全部面板内联。

| # | 迁出面板 | 大小 | 轮 | 消费方（专用 chunk 自担） |
|---|---|---|---|---|
| 1 | PTR 交易流 | 1.33MB | 192 | congress/overview/stock |
| 2 | IPO 窗口 + PTR 申报索引 | 379+273KB | 193 | ipo/overview、congress |
| 3 | 统一申报流 | 249KB | 194 | annual/quarterly/events/overview/stakes |
| 4 | Form D 滚动窗 | 176KB | 195 | ipo |
| 5 | DEF 14A 代理窗 | 174KB | 196 | executives |
| 6 | picks 回测 + SC 13G 流 | 149+147KB | 198 | picks、stakes/smart-money/overview |
| 7 | i18n 字典按语言拆块 | 185→90KB | 201 | 全路由（en 表 95.8KB 仅 en 用户动态加载） |

**实测总账**：每路由 JS 载荷 **3.81→~1.59MB（-58%）**；共享数据 chunk
2.70MB→570KB（-79%）；剩余为框架地板（react-dom ~390KB、base-ui/components
265KB）+ 570KB barrel（44 面板 <100KB 长尾）。

**守卫（防回胖）**：
- `test_barrel_Json_import_weight_ceiling`——index.ts 直载 >100KB 面板 JSON 即 CI 红；
- i18n 审计门随双文件化保持 1301/1301 对称 + 0 孤儿；
- 3 个 Python 契约改读 dict-zh/dict-en 双文件。

**方法论沉淀（本战役新增）**：
- **全站画像优先于逐页优化**：1,503 页 × 逐 script 求和的一次性脚本找到了
  逐页 Lighthouse 永远不会归因的"每路由隐藏税"（共享 chunk）。
- **专用模块模式七连复用**：stock-universe.ts 模式迭代七次零设计变更；
  词边界 grep/replace 是硬纪律（轮 196 `aionis.def14a` 前缀碰撞
  `aionis.def14aPersons`，tsc 拦截）。
- **交叉类型终止符**：`} & T;` 不是 `};`——AST/文本工具对交叉类型必须
  显式终止符匹配（轮 198 首轮脚本安全失败）。
- **动态语言表的 SSR 决定论**：默认语静态导入保持 prerender 决定论，
  非默认语动态 import + 缓存 promise（浏览器实测三路径：切换/重载保持/切回）。

### 第二战役的用户侧协议级实测（2026-10-07 轮 219 补录）

> bundle 数学之外的真传输数字（浏览器 performance API，全新鲜加载、
> 零缓存命中、GH Pages 真网络）：

| 页 | 总传输 | 资源数 | DCL | 全 load |
|---|---|---|---|---|
| /dashboard.html | **793KB** | 59 | 1.23s | 3.49s（含 Worker 价格尾巴） |
| /stock/AAPL.html（紧随其后） | **215KB 新鲜**（共享块 2.6MB 走缓存） | 70 | 0.81s | 1.93s |

diet 前同页等价传输 ≈3.8-4.5MB 级 → **首页 ~5 倍传输削减 + 跨页缓存使
后续页只付增量**。第二战役至此从 bundle 数学升级为协议级实测结论。

## 六、未竟事项

- Interop 2026 / Baseline 全量外部扫描（搜索配额 2026-10-03 18:50 UTC 恢复后）。
- Speculation Rules activationStart>0 命中实测（需脚本化 UI 轮）。
- `/` 落地页简报的业主裁决追认（选项 B 已按建议落地，可回退）。
- license 白名单 ISC/matplotlib 两行（轮 95 遗留业主裁决）。

边界：display lane 全程；0 ledger / 0 frozen / 0 prereg / 0 OOS。
