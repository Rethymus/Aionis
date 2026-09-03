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

---

# 第二批：深研补充发现（研究代理三号，2026-09-03 同日）

> 五项补充主题全部一手或明确标注可信源；UNVERIFIED 处逐条声明。

## 11. 弹簧速度交接——丝滑的本质（可打断/可重定向）

Apple 一手（WWDC23 "Animate with springs"，wwdcnotes.com/wwdc23-10158 逐字）：
- 重定向弹簧"**以被重定向时的速度作为初速**冲向新目标"；
- "SwiftUI 会在手势改变属性时自动追踪速度"；
- "**弹簧是唯一在静态与带初速两种情形下都保持连续性的动画类型**"。

为什么速度不连续=卡顿：从零速度重启动画读作"动画重新开始"，与手指动量相抵
（WWDC23 论证；moro.davidumoru.me/lesson/interruptibility："Gestures should
always use springs. Tweens lose velocity context on interruption"）。

Web 模式：CSS transition 规范内置重定向——"before-change style… updated to
the current time"，即新过渡**从当前动画值续跑**（drafts.csswg.org/css-transitions；
本项目 iter 9a 已 live 实证 0.609→0.048→0 续出）。带速度交接则需 JS：
WAAPI `commitStyles()`（把当前计算值写入 style 后 cancel，
developer.mozilla.org/en-US/docs/Web/API/Animation/commitStyles）+ 逐帧位置差
估速度；半隐式 Euler 积分步：`F = −k(x−target) − c·v; a = F/m; v += a·dt;
x += v·dt`（dt 钳制到 rAF 帧宽）。库默认参考：react-spring
`{mass:1, tension:170, friction:26}`；Framer `{stiffness:100, damping:10, mass:1}`。
→ 本项目结论：CSS 过渡已含"位置重定向"语义；速度交接仅在手势驱动的连续
交互（拖拽流）需要——橡皮筋回弹的手势停顿语义下速度≈0，无需引入 JS 积分器。

## 12. 实测 iOS 系统动画时长表

| 动画 | 实测/通行值 | 来源级别 |
|---|---|---|
| 键盘呼出/收起 | **0.25 s**（历史默认，Apple 建议运行时从通知读取） | SO 1419221 + Apple 建议运行时读 |
| 导航推入/弹出 | **~0.35 s** | SO 7609072 社区实测 |
| 模态表单上滑 | **~0.5 s**（现行精确值 UNVERIFIED——无严格 120fps 逐帧拆解发表） | 社区共识 |
| 通用 iOS 动效体感 | **0.2–0.25 s** | 社区讨论（非测量） |
| 微交互区间共识 | **150–250 ms** | Val Head / NN/g / Material 交叉 |

→ 本项目 0.22–0.5s 过渡全部落在区间内；控制中心/App 切换器无可信逐帧数据
（UNVERIFIED）。最有方法论的参照：gigazine 120fps 键盘逐帧分析（2025-12）。

## 13. 渐进/可变模糊——Apple 键盘顶缘与 Tab 栏的工艺

CSS 无原生梯度模糊（WebKit 有 `linear-blur()` 提案在议：
github.com/WebKit/standards-positions/issues/595）。Web 权威模式 = **N 层堆叠、
逐层递增 backdrop-blur、mask-image 渐变带**（devslovecoffee "Making Apple
progressive blur on the web" 引 App Store/Maps/visionOS 为参照；kennethnym
同型实现）。层数/厚度无发表定数（UNVERIFIED）——实践 4–8 层、指数递增
（1/2/4/8/16px 族）、层间 ~2px 重叠。Chrome 有 border-radius+mask 组合的
边缘伪影 bug（需 1.2× 图像放大规避）。
→ 本项目已按此实现 4 带 18/9/4/1.5px 递增（`globals.css` .frost-edge）。

## 14. Liquid Glass 动态细节与可调项目录

- 定义（WWDC25-219 逐字）："数字元材料，动态弯曲塑形光线……如轻质液体般有机
  地行为与运动"；核心机制 **Lensing**（"动态弯曲、塑形并汇聚光线"）。
- **高光随几何**："如同你对光的预期"地响应形状，随交互移动"勾勒轮廓"，
  并可响应设备运动。
- **亮暗自适应分级**：小元件（导航/标签栏）可独立翻转亮暗；"大元件（菜单/
  侧栏）表面积太大，不翻转"——本项目只对下拉（小元件）用最强材质的分级
  与此一致。
- **Morphing**：玻璃在控件间"动态形变"；变大时"材质特性变化以模拟更厚更
  实在的材质"；浮现/消失靠"渐变调节光线弯曲"而非淡入淡出。
- **同心圆角**："玻璃控件完美嵌入窗口圆角，全程保持同心"。
- **Web 配方**（kube.io）：置换贴图（R=X/G=Y，128 中性）经 Snell 定律
  （n=1.5）对凸/凹 squircle 高度剖面光线追迹预计算；feDisplacementMap
  scale 可动画（=Apple 的"调节 lensing"）；镜面高光由贴图法线对固定光源
  （默认角 −60°）生成，透明度通常 0.2–0.5，经 feImage+feBlend 合成。
  backdrop-filter: url() 仅 Chrome；FF 缺口见 svgwg #1142。
  参照调参（kube.io 示例）：搜索框 spec 0.20/sat 4/refraction 0.70/blur 1.0；
  滑块 0.40/7/1.00/0；音乐卡 0.40/6/1.00/blur 1.0+渐进模糊。
- 官方落地页：developer.apple.com/documentation/technologyoverviews/adopting-liquid-glass。

## 15. 触觉配对——动效峰值与触觉同步

HIG "Playing haptics"（一手）："当视觉、听觉与触觉反馈和谐一致——如它们在
物理世界通常所是——体验更连贯……**触觉的强度与锐度应与动画的强度与锐度匹配**"；
Impact 触觉"提供 complement 视觉体验的物理隐喻……**视图 snap 到位时的一次
tap**"。→ 网页无 haptics API 的等价物是"动画峰值时刻的视觉确认"——本项目
弹簧回弹落定（如橡皮筋归零）即视觉峰值时刻，无需模拟触觉。

---

## 第二批 UNVERIFIED 补充

SwiftUI `bouncingContinuous` 符号名（iOS 17 实装为 .bouncy/.snappy
duration:bounce: 形态）；Control Center/App 切换器逐帧数据；modal sheet
现行精确时长；NSVisualEffectView 逐材质 blur 强度排序；Liquid Glass 高光
~350 nits 的 HDR 峰值（beta 演示流传，无台架报告）。
