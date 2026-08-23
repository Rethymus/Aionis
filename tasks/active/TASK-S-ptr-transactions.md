# TASK-S: PTR 交易级解析（D4 已开：业主"彻底对齐颗粒度"指令）

> 优先级：高（竞品王牌特性）。worktree：`F:\ZCodeData\Aionis-ws`（分支 feat/ptr-transactions，已建，node_modules junction 已挂）。基于 main ca3074f+。
> 派发背景：2026-08-23 四代理齐死于配额[1308]；本文件 = 代理 S 的完整规格，供配额重置后重派或新 session 接手。

## 铁律 #0（业主明令）
**绝不请求/爬取 data.xiaoyinsi.com 或任何竞品站**。数据一律一手公共源（= 众议院书记官 PTR PDF，公共域）。

## 背景
竞品 /congress 是交易级（34,313 笔：申报人/党派/标的/方向/金额区间/披露延迟⚠/交易日）；Aionis 是申报流级（874 份 PTR）。**salvage 分支 `agent/politician`（a2f719b 尽调 + 0b7867a ingest + 70f8ad2 模块）已有 PTR PDF 交易级解析器**——曾实测 813 笔/42 议员（ticker/金额区间/方向/党派 join/迟报 26）。

## 任务
1. 读 salvage（不合并分支）：`git -C F:/ZCodeData/Aionis log --stat agent/politician` 摸清文件清单后逐文件 `git show agent/politician:<path>` 读。判断直接移植/适配（注意主线 politician_trades 已换 House bulk FD.xml 源，两代口径要对齐）。
2. 移植解析器：PDF（politician_trades.json 的 doc_url）→ 交易行（ticker/资产描述/类型/方向 buy|sell_partial|sell_full/金额法定区间/交易日）→ 党派 join 复用 9aea9e0 选区+姓氏双重佐证。解析失败诚实计数不静默丢。
3. 有界真跑：先抽 20 份 PDF 验证解析器仍工作（PDF 格式可能变过），工作再全量 2026 年（~359 份）；≥2s 礼貌；PDF cache 幂等；60 分钟硬上限。
4. 导出新面板 `politician_trades_tx.json`（不破坏现有申报流级面板与契约）：{status, as_of, total, n_members, by_party, late_filings(>45天), parse_failures, transactions:[{member, party, office, ticker, asset, type, direction, amount_range, transaction_date, filing_date, days_late, doc_url}]} + methodology（解析边界）；`_API_LICENSE` 注册；日期降序。
5. 前端：/congress 加"交易明细"区（stream-kit：党派/方向/迟报 FilterPills + 分页 + 计数头；金额区间徽章；⚠ days_late>45）；**/stock/[ticker] 加政客交易 join**（ticker 反查近 8 笔 + "全部→/congress"出口，与机构持有者卡同型）。i18n zh/en。
6. 测试：交易面板契约（字段/方向枚举/days_late=两日期差/parse_failures 调和）+ hermetic 解析器测试（真跑遇到的代表性 PDF 文本 fixture，禁臆造格式）。
7. 7-gate：docs/data-intake-congress-stock-act.md 增补交易级段（公共域/礼貌账/解析边界）。

## 通用铁律
只改自己 worktree（兄弟目录 Aionis-ws）；禁 rm -rf；禁 next build（tsc/eslint 用 F:/ZCodeData/Aionis/web/node_modules/.bin）；pytest 全套 0 失败（PYTHONPATH=F:/ZCodeData/Aionis-ws/src + 主仓 .venv python）；ruff（--exclude docs/code-review）净；无 mock；0 ledger/frozen/config/prereg/OOS；增量提交（Conventional Commits）。交付报告：commit/移植结论/抽样成功率/全量结果（笔数/议员/党派/迟报/失败/ticker 覆盖）/stock join 覆盖/四项验证结果。
