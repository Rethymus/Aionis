# Apple 动效工程规格研究 → Aionis 实现映射（2026-09-03）

> 业主命题：深研 Apple 的动效/阻尼/毛玻璃在**细节层**如何做到"细腻丝滑"，并落地到本项目。
> 本文全部参数均一手溯源（Apple 官方文档原始 JSON / WebKit 源码 / Flutter 物理移植 /
> Crossref），无凭记忆引用；凡不可一手核实处明确标注 UNVERIFIED。
> 实现落点：`web/src/app/globals.css`（运动令牌）、`ui/frosted-scroll-area.tsx`、
> `ui/reveal.tsx`、`components/back-to-top.tsx`、`components/theme-fade.tsx`。

## 1. HIG Motion——Apple 文档化的只有原则，没有数字

一手抓取 HIG Motion 页（developer.apple.com/design/human-interface-guidelines/motion）：
全文**没有任何时长或缓动曲线数值**。仅有数值：游戏"30–60 fps 帧率"、visionOS"避免
~0.2 Hz 震荡（人对此频率敏感）"。原则（原文要点）：动效要有目的；动效可关闭；反馈动效
**跟随手势**；简短而精准；高频交互避免动效；让用户可取消。

→ 对本项目的约束：一切动效必须 `prefers-reduced-motion` 可关（已全量遵守）、
入场简短（0.3–0.7s）、跟随手势（橡皮筋正是"follows people's gestures"的直译）。

## 2. 弹簧参数的官方语义（UISpringTimingParameters）

Apple 文档原始 JSON：阻尼比 = `damping / (2 * sqrt(stiffness * mass))`；ζ=1
临界阻尼（更少震荡）、ζ→0 欠阻尼（更多震荡）。mass/stiffness/damping 的**默认数值
官方从未文档化（UNVERIFIED）**——民间流传的"Apple 默认值"皆无一手出处。

## 3. SwiftUI 预设值（声明 tokens 一手读取，非民间记忆）

| 预设 | 官方声明 | 语义 |
|---|---|---|
| `.spring()` 默认 | `response 0.5, dampingFraction 0.825, blendDuration 0` | dampingFraction = "临界阻尼所需量的估计占比"（ζ=0.825 → ~1% 过冲后回收） |
| `.smooth(duration: 0.5)` | baseBounce **0** | 临界阻尼滑翔（ζ=1） |
| `.snappy(duration: 0.5)` | baseBounce **0.15** | ζ≈0.85 |
| `.bouncy(duration: 0.5)` | baseBounce **0.3** | ζ≈0.7 |

→ 本项目令牌对齐：`--ease-apple-smooth`(ζ1/0.5s)、`--ease-apple-spring`(ζ0.825/0.5s)、
`--ease-apple-snappy`(ζ0.85/0.5s，按文档值修正过初版 0.3s 偏差)、`--ease-apple-gentle`(ζ1/0.7s 大面板)。
duration 语义 = "感知/沉降时长"，非动画总时长。

## 4. 惯性滚动减速

`UIScrollView.decelerationRate`：normal/fast 常量 Apple 未公布数值；React Native
文档一手引用 **normal 0.998 / fast 0.99**（每帧速度乘子，社区逆向）。→ 浏览器原生滚
动自带等价惯性（本项目不动原生 wheel 滚动，仅边缘过滚接管——见 §6）。

## 5. scrollViewWillEndDragging——可干预落点

文档原文：velocity 以"points per millisecond"（Apple 笔误级表述）；targetContentOffset
"可更改以调整最终停点"；**无闭式公式文档化（UNVERIFIED）**。

## 6. 橡皮筋过滚（本项目橡皮筋阻尼的依据）

一手可用公式（originell gist 注明 chpwn/Grant Paul；Flutter BouncingScrollPhysics
移植同一物理）：**`b = d·(1 − 1/((x·c/d) + 1))`，c = 0.55**，d = 视口维度，x = 手指
超出距离——**渐近阻尼**（越拉越拽），无需人为硬上限。Flutter 一手：normal 档起始
摩擦因子 0.52。WebKit 源码（ScrollElasticityController.mm 老分支）：
stiffness 20 / amplitude 0.31 / period 1.6。
→ 已按此公式重写 `FrostedScrollArea` 边缘过滚（替换初版线性累加+±48 硬帽的近似）。

## 7. 毛玻璃材质——Apple 只给配方不给半径

Material JSON 仅定性（ultraThin/thin/regular/thick）。逆向工程（Oskar Groth，
NSVisualEffectView）：Apple 管线 **1/4 分辨率采样、saturate 1.8、brightness 0.02、
bleed 10**；逐材质半径封装在 CoreUI .car 内（UNVERIFIED per-material）。民间
`blur(20px) saturate(180%)` 无出处。Bjango：CSS blur半径=2×标准差（换算用）。
→ 本项目分级近似：下拉（最强 material）blur(16px) **saturate(1.8)**（对齐逆向
管线）；滚动表头/滑条 blur(8px) 轻材质。

## 8. CSS linear()——网页承载真弹簧的机制

Baseline 2023-12：Chrome/Edge 113、Firefox 112、Safari 17.2（developer.chrome.com
+ MDN 一手）。Chrome 官方示例即弹跳曲线；Josh Comeau：值 >1 = 过冲，~11 点机械感、
~50 点弹簧感。→ 本项目 48 点 ODE 采样 + `@supports` 渐进（旧引擎回退近似 bezier）。

## 9. 实现映射表（本项目动效 ↔ 依据）

| 动效 | 实现 | 依据 |
|---|---|---|
| 区块入场 Reveal | opacity=smooth(ζ1/0.5s) + transform=spring(ζ0.825/0.5s) 60ms 层叠 | §1 原则 + §3 spring 默认 |
| 导航下拉 | 半透明卡底 blur(16)/saturate(1.8) + fade/smooth + rise/spring(0.7s settle) | §7 材质管线 + §3 |
| BackToTop | 常驻挂载，进出 spring(ζ0.825) | §1"可取消/简短" + §3 |
| frost 表滚动区 | 560px 视口+隐藏原生滚动条+JS 钉住表头 | §5 手势跟随 + 轮 48 CSS 门禁教训 |
| 边缘橡皮筋 | iOS 公式（§6）阻尼拖拽 + spring 回弹；reduced-motion 关闭 | §1"跟随手势/可取消" + §6 |
| 滑条淡入淡出 | snappy（§3 文档值） | §1 简短精准 |
| 主题切换全页过渡 | .theme-fade 0.35s 色彩过渡 400ms | §1 原则（无常数依据,工程惯例） |
| 滚动惯性 | 浏览器原生（未接管） | §4 原生等价 |

## 10. UNVERIFIED 清单（诚实边界）

FEDS 弹簧质量/刚度/阻尼默认数值；iOS 橡皮筋平方变体公式；逐材质 blur 半径；
scrollViewWillEndDragging 闭式公式；HIG 页之外任何"Apple 用 X ms"的说法。
