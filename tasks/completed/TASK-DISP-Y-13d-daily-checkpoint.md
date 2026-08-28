# TASK-DISP-Y — 13D 日更抓取按日检查点（可续跑化，根治静默杀类别）

**Lane**: display / 数据抓取 lane。**工作目录**: worktree `F:/ZCodeData/Aionis-wz`
（分支 `agent-y/13d-daily-checkpoint`）。**优先级**: P1。

## 0. 背景（主线已确诊，你负责实现）

`scripts/stakes_13d_daily_fetch.py`（走查 `src/aionis/ingest/stakes_13d_daily_index.py::fetch_recent_13d_daily`）
扫 2024-12-17→今的 EDGAR 日索引（08-28 实证 619 日、好窗口 ~18.5min、CPU 解析密集），
**结尾一次性写** `data/cache/sc13d_daily_aggregate.json`——超时=零产出。已两次咬人：
本地轮 21/22 的 900s 帽 + CI 步 15min 帽（`continue-on-error` 掩盖），smart_money 停 08-21
两轮；CI 帽现已提到 40min（`92fbda0`），但"长任务无检查点"的缺陷类别仍在。

**前提核查（你先做并写进执行记录）**：EDGAR 日索引是按日期归档的不可变文件
（同一天的 crawler index 事后不再变化）——若属实，按日缓存解析行永久有效；若不属实
（例如同日文件会追加），改为"缓存行带日索引内容指纹，指纹变了才重算"，并如实记录证据。

## 1. 实现方案

1. 按日检查点：解析完一天 → 追加写入 sidecar `data/cache/sc13d_daily_checkpoint.json`
   （{date: rows}，或你评估后更稳的分片方案）。重跑时先载入检查点，**已缓存日零重解析
   零请求**，只补缺失日。
2. 最终聚合物 `sc13d_daily_aggregate.json` 的内容与现状**逐字节等价**（同一输入序列下）；
   检查点仅是中间态持久化。
3. 礼貌纪律不变：只对真正抓取的日子保持 ≥2s 间隔。
4. 幂等/可续跑语义写进脚本 docstring（对齐 `form_ipo_price_parse.py` 的写法）。

## 2. 测试（hermetic，禁止网络）

- 检查点保存/载入/跳过语义；模拟中途超时（monkeypatch 第 N 天抛异常）后重跑：
  已缓存日不被重新解析（计数器断言）、最终聚合与一次跑完逐字节一致。
- 前提核查结论进测试注释。
- 存量相关套件全绿（找到 13D/13G 相关测试文件跑之）。

## 3. 验收与边界

- `uv sync --all-extras` → 新测试 + 相关存量套件绿 + 触及文件 ruff 净。
- **不要**跑真网络抓取验证（主线集成时验证）；不要改导出端/前端/CI yml。
- 零 ledger/frozen/config/prereg/OOS；不 push；不碰 `docs/code-review/` 与 `state/`。
- 交付：1-2 个原子 commit（feat+test）。收尾把"## 执行记录（DEV-Y）"追加到主仓
  `F:\ZCodeData\Aionis\tasks\active\TASK-DISP-Y-13d-daily-checkpoint.md` 末尾。

## 执行记录（DEV-Y）

**状态：完成。** worktree `F:/ZCodeData/Aionis-wz`，分支 `agent-y/13d-daily-checkpoint`，
commits `5dc913e`（feat: module+script）+ `8764496`（test）。未 push，工作树干净。

### 前提核查结论（§0）——属实（按日归档不可变），但保留一个如实记录的窗口

证据（全部来自代码阅读，零网络）：
- `stakes_13d_daily_index.py` L30/L43-44：URL 为
  `https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{q}/crawler.{yyyymmdd}.idx`
  ——日期键控、按年/季归档的 `/Archives/` 文件，URL 是日期的纯函数，无"latest"别名。
- 该文件自带 `Last Data Received: {date}` 钉死头（测试 fixture L19 镜像了真实格式）。
- 本模块生产语义早已押注按日永久：`fetch_daily_crawler_index`（L51-70 原行号）把当日
  原文永久缓存为 `daily_idx_{yyyymmdd}.txt`，重跑原样返回。
- **如实记录的例外**：当天文件是 CURRENT 传播流（模块 docstring L5），在 EDGAR 传播窗口
  内仍会增长；CI cron 为 22:00 UTC = 18:00 ET（`refresh-terminal-data.yml` L18），即窗口
  中段抓"今天"。天关闭后不可变 ⇒ 按日缓存解析行长期有效。
- **防御取两者**：检查点每行带原文 sha256 指纹；重跑对**本地已缓存原文**做哈希比对
  （纯磁盘、零请求零解析），一致才复用行，不一致（当天文件长了/缓存被截断）只重算该日。
  本地原文缺失时降级为一次礼貌重取再验指纹。另一调用方 `filing_stream.py` L351 同 walk
  同解析器，默认开启检查点安全共享同一 sidecar，输出不变。

### 方案（§1）

- sidecar `data/cache/sc13d_daily_checkpoint.json`：`{"version":1,"days":{iso:
  {"fingerprint":sha256,"rows":[...]}}}`；每解析完一天即原子落盘（tmp+`Path.replace`）。
  载入防御式：缺失/损坏/版本不符 → `{}` 全量重建（从 raw 缓存，零额外请求）。
- walk 重构：检查点命中 → 指纹校验（磁盘）→ 复用行（**零解析零请求**）；原文缺失 →
  一次礼貌重取验指纹；无条目 → 原路径抓取+解析+落盘；抓取失败日**不写**条目 → 下轮只补
  缺失日。`use_checkpoint=False` 恢复旧行为（输出相同），`force=True` 忽略并重建 sidecar。
- 最终聚合物与现状逐字节等价：行来源（新解析 vs JSON 往返）不影响
  `json.dumps(rows, indent=2)` 字节——测试逐字节断言（含 dict 键序）。
- 礼貌纪律：间隔仍在 `_policy_get` 内，未触碰；检查点命中天然零请求，间隔只对实际抓取日
  生效。脚本 docstring 对齐 `form_ipo_price_parse.py` 幂等/可续跑写法 + 新增 checkpoint
  覆盖数打印；`--help` 冒烟通过（未跑真 walk，§3 边界遵守）。

### 测试与验收数字（§2/§3）

- 新增 `tests/test_stakes_13d_daily_checkpoint.py`：6 例全绿（含 1 参数化 ×2）——
  持久化/载入/指纹链接；全缓存重跑零请求零解析（计数器断言）；中断续跑（第 3 天 parse
  抛异常，位于 per-day 容错 try 之外=硬杀模拟）→ Mon/Tue 不重解析不重请求、Wed 连请求都
  不需要（raw 缓存已在杀前落盘）、仅 Thu/Fri 触网，最终聚合物与一次跑完**逐字节一致**
  且与 `use_checkpoint=False` 路径逐字节一致；指纹漂移只重算当日（零请求）；失败日不入
  检查点、下轮单独补齐后与干净单跑逐字节一致；损坏/异版本 sidecar 降级重建不致命。
- 存量套件全绿：13D/13G 家族 + 聚合物消费方共 9 文件 **172 passed**（
  `test_stakes_13d_daily_index` / `_13d` / `_efts` / `_signal` / `_13g` / `_pct` /
  `test_web_terminal_data` / `test_export_terminal_data` + 新文件）。
- `uv sync --all-extras` OK；`uv run ruff check` 触及 3 文件 **All checks passed**（修了
  UP035 `Callable`→`collections.abc`、B905 `zip(strict=True)`）。
- 未动：导出端/前端/CI yml/ledger/frozen/config/prereg/OOS/`docs/code-review/`/`state/`。
  零网络（测试全 monkeypatch `_policy_get`，真实 per-day 缓存逻辑照跑）。

### 偏离与边界说明

- 任务书 §0 二选一（{date:rows} 或指纹）：选了**指纹版**——前提"事后不可变"成立，但
  当天窗口真实存在（cron 18:00 ET 在传播窗口内），指纹是覆盖该分支的最稳实现，成本仅
  每日一次磁盘哈希（619 日 <1s）。这不是对前提的否定，是把"当天"例外显式化。
- 已知遗留（现状即有，未扩大）：18:00 ET 抓"今天"若传播窗口未关，当天原文被永久钉在
  部分快照（raw 缓存老问题）；指纹机制使其**可检测可修复**（删该日 raw+条目即重算），
  根治需调 cron 时间/加 refresh 参数——超出本任务边界，留给主线决策。
