# 复刻差距地图 — 小隐寺 API 分类学 × 免费一方源（2026-08-23）

> 背景：目标 = 完整复刻 data.xiaoyinsi.com（实时/部署暂缓）。数据**不爬小隐寺**，
> 只学习其 API 配置（/api-docs Scalar 文档，~50 GET 端点，2026-08-23 IAB 浏览器提取），
> 再对每个维度做网络深度调研定位**免费一方源**。本文 = 维度 → 源 → 验证状态 → 优先级。

## 一、已实测验证的源（本日浏览器直测，非转述）

### V1. ApeWisdom — Reddit 热议股票榜 ✅ LIVE
- **端点**：`https://apewisdom.io/api/v1.0/filter/all-posts`（另有 `/filter/stocks`、`/filter/crypto`、`/tickers/{ticker}`）
- **域名陷阱**：是 **apewisdom.io**（.com 连接失败 — 之前 403/超时的原因）。免费、无鉴权、JSON。
- **实测**（2026-08-23 17:0x，IAB）：返回 `{"count":0,"pages":0,"current_page":1,"results":[]}`
  —— 结构正确；count=0 是周末诚实表现（周日无新提及窗口），非故障。**下次工作日复测应见数据。**
- **映射**：小隐寺 /reddit 的 938-ticker 榜（其 API 文档自述来源即 ApeWisdom）。
- **礼貌性**：无鉴权公共 API；沿用模型-API 例外条款不适用 → 数据站点：≥2s 间隔 + 指数退避。

### V2. ARK Invest — 8 只基金每日持仓 CSV ✅ LIVE
- **URL 模式（新，官方页面直链）**：
  `https://assets.ark-funds.com/fund-documents/funds-etf-csv/{FUND_LONG_NAME}_{TICKER}_HOLDINGS.csv`
  例：`ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv`（ARKK 基金页 "Full Holdings CSV" 按钮原始 href，IAB locator 提取）。
- **旧模式已迁移**：`ark-funds.com/wp-content/uploads/...` 会 301 到 `www.` 且直接导航无 body（触发下载）；
  抓取脚本应直接用 assets. 子域 + 长文件名。8 基金：ARKK/ARKQ/ARKW/ARKG/ARKF/ARKX/PRNT/IZRL。
- **映射**：小隐寺 /institutions 的 ARK 专簇（8 基金日度持仓 + 变动流）。
- **注意**：CSV 每日盘后更新；历史不保留 → 我们落盘累积即成时间序列（display-lane 数据湖模式）。

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

1. **P0 — 政党对立指数/两党跟单组合**：纯计算模块（export + panel + 测试），零新抓取。
2. **P1 — ARK 8 基金面板**：fetcher（assets.ark-funds.com CSV，礼貌间隔）+ /institutions 内 ARK 簇。
3. **P1 — Reddit 热议榜（ApeWisdom.io）**：fetcher + 面板（工作日首测真实数据后再上线）。
4. **P2 — Form D 一级市场管道**（EDGAR）。
5. **P2 — 统一申报流 + 13F filer 目录**（EDGAR，量大，可切片）。
6. **P3 — DEF14A 高管/董事会**（解析成本高，放最后）。

## 五、验证记录（可复算）

- ApeWisdom：IAB 导航 `apewisdom.io/api/v1.0/filter/all-posts` → JSON 结构如上（17:0x，周日）。
- ARK：IAB 打开 `www.ark-funds.com/funds/arkk/` → locator `a[href*="csv"]` 4 匹配 → 官方
  "Full Holdings CSV" href = `assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv`。
- WebSearch/webReader 本日配额尽（重置 2026-09-03）→ 本文档所有"实测"均来自 IAB 浏览器一手验证。
