# 复刻差距地图 — 小隐寺 API 分类学 × 免费一方源（2026-08-23）

> 背景：目标 = 完整复刻 data.xiaoyinsi.com（实时/部署暂缓）。数据**不爬小隐寺**，
> 只学习其 API 配置（/api-docs Scalar 文档，~50 GET 端点，2026-08-23 IAB 浏览器提取），
> 再对每个维度做网络深度调研定位**免费一方源**。本文 = 维度 → 源 → 验证状态 → 优先级。

## 一、已实测验证的源（本日浏览器直测，非转述）

### V1. ApeWisdom — Reddit 热议股票榜 ✅ LIVE → **管道已建（同日 P1 落地）**
- **端点**：`https://apewisdom.io/api/v1.0/filter/stocks`（免鉴权 JSON；`filter/all-posts` 与 `filter/crypto` 返回诚实零信封——空是口径不是故障）
- **域名陷阱**：是 **apewisdom.io**（.com 连接失败 — 之前 403/超时的原因）。
- **实测**（2026-08-23）：`filter/stocks` 实时返回 NVDA 居首的榜单（envelope 声明 count:290/pages:3）。**分页已死**：`?page=N` 与路径 `/N` 均回 `current_page:1`（浏览器逐一验证）→ ingest 信封 `current_page` 回显检测 + `served_pages`/`pagination_ok` 字段，面板披露"可见=声明 290 的前 100"。
- **已交付**：`ingest/ape_wisdom.py` + `scripts/ape_wisdom_fetch.py` + `reddit_trending.json` + /reddit 热议榜板块（rank/提及/24hΔ，与自有 Atom 采集面板共存）+ 契约测试。
- **礼貌性**：数据站点条款：≥2s 间隔 + 指数退避。

### V2. ARK Invest — 8 只基金每日持仓 CSV ✅ LIVE → **管道已建（同日 P1 落地）**
- **URL 模式（官方页面直链，浏览器逐页提取 live DOM 钉入代码）**：
  `https://assets.ark-funds.com/fund-documents/funds-etf-csv/{FUND_LONG_NAME}_{TICKER}_HOLDINGS.csv`
  （基金页为 JS 壳——raw HTML 无 href；长名含 `TECH._&_` 类不可猜标点 + ARKF/ARKX 两处 2025 更名）。
- **已交付**：`ingest/ark_holdings.py` + fetcher + `ark.json` + /institutions ARK 家族板块（8 基金卡权重条 + 家族共振表：AMD/PLTR/AMZN/NVDA 各 5 基金同持）+ 契约测试。8/8 基金 331 仓位 @ 2026-08-21。
- **注意**：CSV 每日盘后更新；历史不保留 → 本地日快照累积即时间序列（display-lane 数据湖模式）。

## 二、既有免费源可直接覆盖的维度（无需新源）

| 小隐寺维度 | 一方源 | 状态 |
|---|---|---|
| 一级市场（Form D 融资） | SEC EDGAR Form D（公有领域，full-text + submissions API） | 源已知，未建管道 |
| 13F 申报人目录（~9k filers） | EDGAR `browse-edgar` 13F 类目分页 | 源已知，未建目录 |
| 统一 SEC 申报流（8-K/10-K/10-Q/13F/13D/S-1/3/4/5/DEF14A） | EDGAR daily index（我们已在用：13D/13G/4 均走此路） | 部分已建（form4/stakes13g） |
| 高管人级档案 + 董事会分析 | DEF14A 委托书（EDGAR） | 未建 |
| 政党对立指数 + 两党跟单组合 | **我们自己的 `politician_trades_tx.json`（2,812 笔，94 议员）— 纯计算，零新数据** | 数据已就绪 ✅ |

## 三、明确不追（商业数据 / 内容产品）

- TACO 卫星（商业付费数据）— 已有决策记录。
- 韩国散户杠杆指数 — 一方源未定位（其自述来源不公开）；如后续定位到免费源再议。
- 12 主题 ETF 榜 — 标准行情范畴，display 层可后补。
- 书架/知识图谱 — 小隐寺自有内容产品，非数据 API，不复刻。

## 四、建设优先级（display-lane，display-only 约束不变）

1. **P0 — 政党对立指数/两党跟单组合** ✅ 已上线（party_index，纯计算）。
2. **P1 — ARK 8 基金面板** ✅ 已上线（ark.json + /institutions ARK 家族板块）。
3. **P1 — Reddit 热议榜（ApeWisdom.io）** ✅ 已上线（reddit_trending.json + /reddit 板块；分页失效如实披露）。
4. **P2 — Form D 一级市场管道**（EDGAR）— 下一个。
5. **P2 — 统一申报流 + 13F filer 目录**（EDGAR，量大，可切片）。
6. **P3 — DEF14A 高管/董事会**（解析成本高，放最后）。

## 五、验证记录（可复算）

- ApeWisdom：IAB 导航 `apewisdom.io/api/v1.0/filter/all-posts` → JSON 结构如上（17:0x，周日）。
- ARK：IAB 打开 `www.ark-funds.com/funds/arkk/` → locator `a[href*="csv"]` 4 匹配 → 官方
  "Full Holdings CSV" href = `assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv`。
- WebSearch/webReader 本日配额尽（重置 2026-09-03）→ 本文档所有"实测"均来自 IAB 浏览器一手验证。
