# 数据接入 7 门 — baostock 证监会行业分类（A 股行业级 sector 元数据）

> **状态**：**v0.1 · 2026-08-20** · display-only metadata module。
> **范围**：baostock `query_stock_industry`（证监会行业分类）通过 7 门强制清单评估。
> 本模块**仅服务终端展示层**（picks / sector_breakdown / stock_universe 的 CN sector
> 分组），**绝不进研究管线**（`features/` / `eval/` / `ingest/` 研究面）。
> **引用**：主 rubric 见 `docs/data-intake-rubric.md`；格式参照
> `docs/data-intake-edgar-form4.md`；姊妹文档（价格面）见
> `docs/data-intake-ashare-price-baostock.md`。

---

## 数据源概述

**baostock（证券宝）** 是免费、匿名的中国证券数据平台（socket 协议，
`public-api.baostock.com:10030`，PyPI 客户端 `baostock==0.9.3`，纯 Python，唯一依赖
`pandas>=0.18.0`）。默认登录即匿名：`login(user_id='anonymous', password='123456')`
（源码 `baostock/login/loginout.py` 验证）；`set_API_key` 为可选增强，本模块不使用。

`query_stock_industry(code="", date="")` 返回字段（2026-08-20 实测，全市场 5,542 行、
84 个行业）：

| 字段 | 含义 | 实测样例 |
|---|---|---|
| `updateDate` | 该分类记录的生效/更新日 | `2026-08-17` |
| `code` | 证券代码（与 OOS panel 的 CN ticker 同格式） | `sh.688041` |
| `code_name` | 证券简称 | `海光信息` |
| `industry` | 证监会行业（门类代码+名称拼接） | `C39计算机、通信和其他电子设备制造业` |
| `industryClassification` | 分类体系（唯一值） | `证监会行业分类` |

底层分类为**证监会《上市公司行业分类指引》**（CSRC 公布的公共监管标准）；
每股的行业归属是事实性映射（非创作性表达），与本项目既有 CN ticker+name
（GitHub listing，"raw factual data, not copyrightable" 先例）同一事实数据立场。

---

## G1 — License allowlist（许可协议白名单）

### 结论：✓ **PASS（display-only 通道，附两条 caveat）**

- **规则**：仅 MIT / Apache-2.0 / BSD-2/3-Clause / CC0 / CC-BY-4.0（数据）。
- **客户端包证据（2026-08-20 直接下载官方分发验证，非转述）**：
  - PyPI 页面（pypi.org/project/baostock）：License 栏 = **"BSD License"**；
  - `baostock-0.9.3.tar.gz` 的 `setup.py`：`license='BSD License'` +
    `'License :: OSI Approved :: BSD License'` classifier；
  - `baostock-0.9.3-py3-none-any.whl` 的 `METADATA`：`License: BSD License` + 同
    classifier。三处一致，作者自declare，BSD 在 Aionis 白名单（MIT/Apache/BSD）。
- **Caveat 1（license 文本缺位）**：sdist/wheel 内**未捆绑 LICENSE 全文**（metadata
  `license_files = null`），2-clause vs 3-clause 无法从制品确证。**两种变体均在白名
  列**，判定不受影响，但如实记录。
- **Caveat 2（数据侧 = vendor display-only 层）**：baostock 服务端数据无显式开源
  数据 license。官网（SPA，正文不可静态抓取）自述"免费、开源的证券数据平台（无需
  注册）"（知识库页，搜索引擎索引）；页脚有"免责声明"入口但**本文档撰写时无法读
  取原文**（JS 渲染）。尽调搜索（免责声明/使用条款/商用）未发现任何禁止性条款；已
  找到的《隐私政策》《用户服务协议》属"交易技术商城"账户体系，非匿名数据 API。
  **处置**：数据侧按 **vendor ToS display-only** 分层——与 Tiingo/Alpaca/Reddit 在
  `api_catalog` license 映射中的既有层完全一致：仅缓存派生的每股行业字符串用于终
  端分组展示，**不再分发原始数据集**，绝不进研究管线。
- **更正记录（重要）**：姊妹文档 `data-intake-ashare-price-baostock.md`（2026-08-04）
  记载 "PyPI 元数据 `License: MIT License`" 并引用 GitHub `baidstock/bs_stock`
  LICENSE=MIT。**2026-08-20 验证：该 GitHub repo 返回 404（不存在）**，且官方 PyPI
  分发（sdist+wheel）均声明 **BSD**。权威源 = PyPI 官方分发 = BSD。MIT 与 BSD 都在
  白名单，两份文档的 G1 结论（PASS）不变，但旧文档的 MIT 引用应在主线更正（本
  任务文件边界不含该文档，故在此记录移交）。

---

## G2 — PIT / as-of 时点（point-in-time）

### 结论：✓ **PASS（display 用途；as-of 可构造）**

- **规则**：每条观测带「当时可知」timestamp；t 时刻的值不得依赖 >t 的信息。
- **机制（2026-08-20 实测）**：
  - 每行自带 `updateDate`（分类生效日）——观测级 as-of 时戳存在；
  - `date` 参数触发**服务端 backward as-of 查询**：`date="2016-01-01"` 返回
    `updateDate=2015-12-28` 的行；`date="2020-06-30"` 返回 `updateDate=2020-06-29`
    的行；`date="2026-08-19"` 返回 `updateDate=2026-08-17` 的行。即历史截面可按日
    重构，PIT 对齐在原则上可构造（`merge_asof` backward on `updateDate`）。
- **本模块的实际用法（诚实框定）**：展示层取**当前表**（`date=""`），即
  "as of max(updateDate)" 的今日快照，用于今日终端分组——**不**与任何历史研究截面
  做 join（那才会引入 lookahead）。快照时点由 `updateDate` + cache 的 mtime 双重可
  溯源。
- **通过**：display 用途下无 lookahead 面；若未来要研究面使用，必须改用逐日 as-of
  查询并过新 7-gate（见"升格路径"）。

---

## G3 — No-revision contract（无回改契约）

### 结论：⚠ **CONDITIONAL（不可证 → 快照纪律）**

- **规则**：provider 不得追溯重算历史；若不可证：首次接入即快照 + sha256 = 冻结真相。
- **机制**：
  - 行业分类是**缓变维度**：上市公司行业变更时 `updateDate` 前移（证监会每季度/
    按公告调整）。历史 `date` 查询可回放，但 provider 是否**重写**历史行无法从外部
  证伪（与 EPU 同型的 G3 盲区）。
  - **缓解（本模块落地）**：全量拉取落 `data/cache/cn_industry.parquet`（幂等
    cache，gitignored regenerable artifact）；每次 `--no-cache` 刷新 = 新快照版本，
    行级 `updateDate` 保留在 cache 内供审计。展示层不写 ledger（G5），所以快照纪律
    表现为：cache 即冻结真相、刷新即显式重建。
- **判定**：与价格面文档（G3 CONDITIONAL，方案 A 冻结快照）同一姿态；display-only
  通道下可接受。

---

## G4 — Reproducibility / snapshot discipline（可复现）

### 结论：✓ **PASS**

- 全 cache 路径：`data/cache/cn_industry.parquet` 存在时零网络读取（幂等）；
  `--no-cache` 强制重拉。cache 含 `updateDate` 列，任何消费者可核对快照时点。
- 拉取日志打印行数 + `updateDate` max，运行可审计。
- 失败优雅降级：baostock 不可用/未安装时，CN sector 回退到既有板块 tier
  （非静默——构建日志与 methodology 字符串披露回退计数）。

---

## G5 — Exploratory-only by default（默认探索性）

### 结论：✓ **ENFORCED（display-only，永不进 confirmatory）**

- 本模块是**展示层元数据**（terminal sector 分组），与 `form4.json`、`cot.json`
  同层。红线（AGENTS.md）：research module 不得消费；live/current 数据只服务终端
  显示层。行业分类同理——**只进 `build_ticker_metadata.py` 展示管线**。
- **绝不**写 `runs/ledger.jsonl`（display lane 无 ledger 行）；**绝不**进 frozen
  config / prereg / OOS 特征。
- 代码层面：baostock 为 lazy import（沿 `ingest/ashare_price.py:_require_baostock`
  先例），Intentionally 非核心依赖；研究管线无法意外引入。

---

## G6 — Selection / survivorship honesty（选择 / 幸存者诚实）

### 结论：✓ **PASS（附回退披露）**

- 全量拉取覆盖**全部 A 股含已退市**（实测 5,542 行，含邯郸钢铁 sh.600001 等退市
  行），非幸存者截面的今日快照——与 `constituents_on` 的 PIT 语境不同的是，这里
  分组对象本就是"今日已知全部证券"。
- 退市/无分类行 `industry` 为空 → **回退到板块 tier**（创业板/科创板/…），回退计
  数打印进构建日志；methodology 字符串披露该回退的存在。
- 证监会行业分类是监管标准映射，非"被讨论度"类 selection-biased 数据；但仍按纪律
  声明：分组仅服务展示语境，非定价真值。

---

## G7 — Politeness / ToS（礼貌 / 服务条款）

### 结论：✓ **PASS**

- baostock 是**登录会话型 API**（非逐次 HTTP）——与 `ashare_price.py` 的 G7 解释一
  致：礼貌体现为**单会话 + 批量**。本模块：**一次匿名 login → 一次全量
  `query_stock_industry(code="")`（服务端 2000 行/页自动翻页，由 `rs.next()` 驱
  动）→ logout**。零逐票请求，零轮询。
- 失败处理：login/query 错误码 fail-visible（打印 + 回退 tier），不重试轰炸。
- 匿名账户不给服务方造成账务/配额压力；不使用 API key 通道。

---

## 接入决策汇总

| 门 | 结果 | 说明 |
|---|---|---|
| **G1 — License** | ✓ **PASS**（caveat ×2） | 客户端 = BSD（官方分发三处一致验证）；数据 = vendor display-only 层（同 Tiingo/Alpaca 既有分层）；LICENSE 全文缺位与旧文档 MIT 引用 404 已如实记录。 |
| **G2 — PIT** | ✓ **PASS** | 行级 `updateDate` + `date` 参数服务端 backward as-of（实测）；display 用法 = 今日快照，不做历史 join。 |
| **G3 — No-revision** | ⚠ **CONDITIONAL** | 历史重写不可证伪 → 快照纪律（`cn_industry.parquet` 幂等 cache，刷新 = 新快照）。 |
| **G4 — Reproducibility** | ✓ **PASS** | 全 cache 路径 + `updateDate` 审计列 + 优雅降级。 |
| **G5 — Mode** | ✓ **ENFORCED** | **display-only**；lazy import 非核心依赖；0 ledger / 0 research 面。 |
| **G6 — Selection** | ✓ **PASS** | 全量含退市；空分类回退 tier 并披露。 |
| **G7 — Politeness** | ✓ **PASS** | 单会话单查询批量；匿名；fail-visible。 |

**最终结论**：**通过（display-only 通道）**。CN sector 从板块 tier 升级为证监会行
业分类；tier 保留为 `cn_tier` 附加列；行业缺失时回退 tier。升格为研究面数据需重过
7-gate + 逐日 as-of 重构 + owner 批准（当前无此计划）。

---

## 使用限制与合规声明

1. **Scope**：仅 `scripts/build_ticker_metadata.py` 展示管线消费；终端 sector 字符串
   格式 = `证监会: {industry 原文}`（如 `证监会: C39计算机、通信和其他电子设备制造
   业`），保留门类代码以自证分类体系。
2. **不再分发原始数据集**：cache 为 gitignored 派生工件；终端 JSON 只含每股一条
   行业字符串（展示所必需的最小派生）。
3. **回退语义**：`sector` 为空/缺失行业的 CN 行回退板块 tier；`cn_tier` 列永远保留
   tier（US 行为空串）。
4. **依赖激活**：baostock 不进 `pyproject.toml`（沿 `ashare_price.py` lazy-import
   先例）。真实拉取：`uv run --with baostock python scripts/build_ticker_metadata.py
   --no-cache`；CI 接线草案见 `docs/ci-note-cn-industry.md`。

---

## 文件清单

- `scripts/build_ticker_metadata.py` — 拉取 + 合并 + cache（本 intake 的实现载体）。
- `docs/data-intake-baostock-industry.md` — 本文档（7 门评估）。
- `docs/ci-note-cn-industry.md` — CI 接线草案（主线集成时执行）。
- `data/cache/cn_industry.parquet` — 行业快照（gitignored regenerable）。

---

## 尽调证据存档（2026-08-20）

- PyPI 页面：pypi.org/project/baostock → License "BSD License"（OSI classifier）。
- `files.pythonhosted.org` 官方 sdist `baostock-0.9.3.tar.gz`（sha 同 PyPI 列表）→
  `setup.py`/`PKG-INFO` = BSD。
- 官方 wheel `baostock-0.9.3-py3-none-any.whl` → `METADATA` = BSD。
- 源码级验证：`loginout.py` 默认匿名参数；`contants.py` 服务端点
  `public-api.baostock.com:10030`；`sectorinfo.py` `query_stock_industry(code, date)`
  签名与分页常量（2000/页）。
- 实测（单会话三查询）：全量 5,542 行字段/分布 + `sh.600033` 三时点 as-of 回放。
- GitHub `baidstock/bs_stock` → **404**（`gh api` 验证，2026-08-20）；全部同名
  GitHub repo 均为第三方镜像（非官方，无一致 license）。
