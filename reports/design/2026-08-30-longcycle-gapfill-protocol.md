# 长周期查漏补缺任务协议（Gap-Fill Long-Cycle Protocol）v1

- **日期**: 2026-08-30（轮 45 首轮执行验证）
- **命题来源**: 业主 2026-08-30 —「设计一个长周期性质的查漏补缺任务，需要结合视觉能力
  探查一些代码上未能发现的问题，以及结合专业学科知识判断当前设计的潜在改进空间，
  打磨细节彰显项目的本质」
- **性质**: 超长期循环任务（与轮 ㉝ 起的"查漏补缺+视觉持续优化"系列同族），本协议把
  该系列的隐式做法**显式化为可复用协议**，供后续轮次直接执行。
- **边界铁律**（每轮开场重申）: display/docs lane 优先；**0 ledger / 0 frozen config /
  0 prereg / 0 OOS**；研究面触碰必须预注册级业主 GO；每轮收尾按正典（build→目视→删 out；
  无残留进程）。

## 0. 项目本质（所有打磨的对齐锚）

Aionis = **可证伪、反泄漏的量化研究 harness**。四相 confirmatory 零结果 + Track C 联合
confirmatory 零结果（IC −0.0088，CI 跨零）是**预期成果而非失败**。因此"打磨细节彰显本质"
的判据是：每一处修改是否让「主张—冻结—证据—不确定性」这条链更**诚实、更可核验、更难被
误读**。凡让数字更"好看"的修改都是方向错误。

## 1. 三通道方法学

### 通道 A — 视觉探查（代码看不见的问题）

代码审查/pytest 覆盖逻辑正确性，但看不见：隐形描边、布局挤压、图表空渲染、真实运行时
的框架契约失败。已验证的管线（轮 45 实战）：

1. **构建与伺服**: `node scripts/build-api.mjs && npx next build`（web/）→
   `python -m http.server <port>`（out/）。Streamlit 走 `uv run streamlit run dashboard/app.py
   --server.headless true`。
2. **截图**: Chrome headless — `chrome --headless=new --disable-gpu --hide-scrollbars
   --window-size=1440,3200 --virtual-time-budget=20000 --screenshot=out.png URL`。
   - 明色主题：先经种子页 `__light.html`（`localStorage.setItem('theme','light')` 后
     `location.replace(target)`），种子页放 out/ 内随收尾删除。
   - **Streamlit 例外**: websocket 渲染在 virtual-time 下不完成（白屏假象）——必须真实
     浏览器（`cmd /c start msedge.exe --new-window URL`）+ computer-use 截图/AX 树。
3. **像素地面真值**（对抗视觉模型幻觉的第一道防线，Python/PIL）:
   - 内容密度切片图（16 片非背景像素占比）→ 发现"页面过短=未渲染"或空洞区；
   - 描边色计数（按目标色 ± 容差数像素）→ 直接证明图表线条是否可见（轮 45 用它证明
     轮 44 navy 修复在明暗双主题成立）；
   - 文本级实测：SSG HTML 剥 script/style 后 grep 渲染垃圾（undefined/NaN/[object Object]）
     与关键统计值在墙。
4. **视觉模型审图纪律**（第二道防线）:
   - 全页开放式审查 = 幻觉温床（轮 45 两实测 + 轮 ㉔/㉖ 历史病理一致）；**只对裁剪区
     （≤1/3 页高）提问，只问二元/具体视觉判断**（"CI whisker 是否可见？"），不让它转写
     中文文本、不做开放式"找问题"。
   - 每条视觉模型主张必须交叉核验：DOM/AX 树（get_app_state 读真实元素文本）、像素
     统计、或代码回读。无核验不立项。
5. **AX 树作为 Streamlit 的"DOM 实测"**: `get_app_state` 返回全部渲染元素文本——traceback
   、caption、表格行全部可读，比截图 OCR 可靠一个量级（轮 45 靠它抓到两层运行时崩溃）。

### 通道 B — 学科知识审查（量化/统计语义）

对照 `docs/RESULTS.md` + 冻结账本逐项核对**呈现层语义**：

- **统计语言**: IC/CI/p/t 的语义链是否自洽（例：森林图 derived-t=−0.70 与 p_hac=0.484
  互证）；σ 与 SE 的区分（随机游走带用月 σ 非 SE）；ECE 分档的语境披露。
- **命名纪律**: 已废除概念的遗留词（发表线废除后的 "publishable"）在显示层的残留——
  schema 字段名冻结不动（业主门），显示文案改为当前语义（null-precision gate）。
- **指标命名精确性**: 作用于 IC 序列的 mean/σ·√12 是**年化 IC-IR**，不是 Sharpe（真正的
  Sharpe 在 strategy 面板）——凡把信号一致性指标标成策略收益指标的地方都是误导。
- **账实对账**: 显示层的计数/断言与账本实测核对（轮 45 实例：horizon 视图硬编码
  "3 confirmatory nulls" 而账本是 B/C/D/E1 四相 8 格）。
- **框架运行时契约**: pytest 从仓库根导入掩盖的启动路径差异（sys.path）、框架版本升级
  引入的新强制（Streamlit 1.59 duplicate element ID）、pandas Styler 对 None 的格式化——
  这类只有**真实启动**才暴露。

### 通道 C — 本质打磨（优先级裁决）

发现池按此排序取舍：**诚实性修正 > 可核验性增强 > 运行时可用性 > 视觉/文案一致性 >
美学**。例：修"publishable"遗留词（诚实性）优先于任何配色微调。

## 2. 轮 45 首轮执行记录（协议的验证样本）

**发现与修复**（全部 display lane，0 ledger/frozen/prereg/OOS）：

| # | 发现 | 通道 | 修复 |
|---|---|---|---|
| 1 | Streamlit v1 正典启动命令 `uv run streamlit run dashboard/app.py` **ModuleNotFoundError**——streamlit 只把脚本目录入 sys.path，`dashboard.views.*` 绝对导入不可解析；pytest 从根导入掩盖 | A(AX)+B | app.py 仓库根 sys.path 引导 + pyproject per-file-ignore E402 |
| 2 | `StreamlitDuplicateElementId`：`_cumulative_ic_chart` 在 fit/evolution 双调用同参 → Streamlit 1.59 强制拒绝 → **脚本在 Curve Evolution 崩溃，后 7 标签未渲染** | A(AX 树) | 全部 22 个 `st.plotly_chart` 调用点加唯一 key |
| 3 | 修 #2 后暴露第二层：strategy.py `df.style.format("{:.3f}")` 遇 None 单元格 `TypeError` → Strategy/Forward/Run history 三标签死 | A(AX 树) | None-guard 格式化函数（"—" 占位） |
| 4 | horizon 视图硬编码 **B/C/D 三相**："3 confirmatory nulls"、"/6 cells"——账本实测是 B/C/D/E1 四相 8 格全 null（E1 加入扫描晚于视图编写） | B(账实对账) | 四相化 + 8/8 格 + 图表加 phase E1 |
| 5 | "publishable/publishability/publishable-as-null" 显示文案 = 2026-08-15 已废除的发表线遗留语义，与 NULL-is-intended 框架相抵 | B(命名纪律)+C | 显示文案 → null-precision gate（schema 字段名不动，README 注明 legacy） |
| 6 | IC 序列上的 mean/σ·√12 被标为 "Annualized Sharpe"——量化语义上是**年化 IC-IR** | B(指标命名) | 重标 + st.metric help 披露语义边界 + caption |
| 7 | app.py 自称 "dashboard v2" 与刚退役的 v2 演示面撞名；README 停留在"Phase B/4 视图"时代（实际 11 标签 B/C/D/E1） | C | 标题/文档字符串去版本号 + README 全量重写为如实视图清单 |
| 8 | web 终端 11 研究页 × 双主题：文本级零渲染垃圾、关键统计值全在墙、轮 44 描边修复像素级成立、atlas 森林图/热力图/分差带视觉核验通过 | A(像素+视觉) | 无需修复（记录为基线） |

**验证**: dashboard 相关 73 测试全绿 + ruff dashboard lane 干净 + 全套 pytest（后台回归）
+ 真实浏览器 AX 树终验（11 标签全渲染、无 traceback、新文案上墙、horizon 四相在墙）。

**未立项（如实记录）**: 视觉模型对密集中文页的开放式报告全部判幻觉（转写错误、
重复计数、臆造元素），零采信——验证了"小裁剪+二元问题+DOM 交叉核验"纪律的必要性。

## 3. 后续轮次的轮换建议（长周期节奏）

1. **每轮开场**: 读 state → git status → `uv run pytest -q` 基线 → 选 1-2 个通道深耕
   （不必三通道全开）。
2. **通道轮换池**:
   - web 研究五页（dashboard/track/atlas/power-floor/model-health）× 双主题像素+视觉复审；
   - Streamlit 其余标签逐个 AX 树走查（event/coverage/history 尚未逐标签核过）；
   - i18n 字典 zh/en 语义等价抽查（统计术语的英文对应是否学科正确）；
   - `docs/` 逐文档与账本对账（RESULTS.md 已多轮核过，优先 08 索引与 rubric 文档）;
   - 导出面板 ↔ 显示层字段语义漂移扫描（export_terminal_data 7285 行 vs web 类型契约）。
3. **停止条件**: 单轮 ≤2 个 P1 级修复；连续两轮零新发现 → 通道降频为月度巡检。
4. **升级路径**: 凡涉及研究面（ledger/frozen/config/prereg/OOS）的发现**只记录不动手**，
   进 backlog 待预注册级业主 GO。

## 4. 已知工具病理备忘（每轮重读，省重踩）

- Chrome headless 相对路径截图会写失败（拒绝访问）——`--screenshot` 必须绝对路径。
- CDN 传图给视觉模型必须**原样传反斜杠路径**（改正斜杠破坏签名 → 1210 错误）。
- Streamlit 改模块后必须**重启服务进程**（sys.modules 缓存，浏览器 F5 不重载已导入模块）。
- `--virtual-time-budget` 对 websocket 应用（Streamlit）无效，白屏是假象。
- Edge 启动走 `cmd /c start`（MCP open_application 对 Windows 名称解析不稳）。
