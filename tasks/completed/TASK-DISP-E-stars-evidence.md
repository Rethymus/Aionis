# TASK-DISP-E — 明星投资人"+3"候选考察：证据报告（只查证据，不做策展决定）

**Lane**: display / 数据核查。**优先级**: P1（post-parity roadmap H3 残余："明星投资人 40 vs 43，
诚实 −3 待合规候选"）。
**工作目录**: worktree `F:\ZCodeData\Aionis-we`（分支 `feat/stars-evidence`，junction 已挂，LF ledger 已预拷）。
**授权**: 业主常设多 agent 指令。

## 0. 背景

终端明星投资人面板 = 40 位诚实策展（5 位停报实体曾如实剔除）。差距地图记录
"明星能否 +3 只看是否有人通过诚实策展门槛——绝不凑数"。你的任务是产出**候选证据报告**：
哪些知名投资人在最新季度仍在正常申报 13F、身份可核验、有可靠中文名——把判断材料备齐。
**你绝不修改任何策展名单/导出代码；策展裁决在主线集成时按 DESIGN 规格（并行产出中）执行。**

## 1. 前置事实核查（第一步）

- 读 `web/src/data/aionis/form13f.json` 的 managers 列表：现役 40 位是谁（名字+CIK+最新季）。
- grep 策展配置的真实落点（CURATED 列表/类别标签/中文别名的代码位置——大概率在
  form13f 相关 ingest 或 export 侧），搞清"新增一位"需要动哪些数据点（CIK、name、zh_name、
  category）。
- 排除名单：5 个停报实体档案在哪（注释/git 历史 `4405724` K 轮），它们的剔除理由是什么。

## 2. 候选池（起点名单，可增删但要给理由）

非在册 + 未被排除过的公众投资人，每类挑最可能仍活跃的 ~8-12 人考察，例如：
Bill Ackman (Pershing Square) / Seth Klarman (Baupost) / Chase Coleman (Tiger Global) /
Phil Tiger?（已含则跳过）/ Andreas Halvorsen (Viking) / Ole Andreas Halvorsen 同人勿重 /
Steve Mandel (Lone Pine) / John Griffin (Blue Ridge) / Ryan Israel (PersHINGing?) 等——
**以你 EDGAR 实证为准**，设计文档若已就位（DESIGN agent 并行产出
`reports/design/*stars-curation-bar*`）以其初稿为准做筛选，没就位则按下述字段自建表格。

## 3. 每个候选必须实证的字段（EDGAR 礼貌查询）

| 字段 | 来源 | 说明 |
|---|---|---|
| CIK | EDGAR full-text/company search | 10 位零填充 |
| 最新 13F-HR 申报期与 filed 日 | EFTS/browse-edgar（带 CIK 可用） | 是否 ≥2026-Q2 正常申报 |
| 近 8 季申报连续性 | 同上 | 有无断报（断报=停报嫌疑） |
| 实体名 verbatim + 类型 | filing 头 | 与常见译名对上 |
| 公众知名度证据 | 一般知识+官方页 | 无需抓媒体 |
| 中文名建议 | 项目已有惯例（zh aliases 在策展数据里） | 给出建议供采纳 |
| 建议类别 | 七分类（value/growth/activist/quant/macro/china/other） | 附一句归类理由 |

礼貌铁律：≥2.1s 间隔 + 退避；总请求预算 ≤60，逐条记账写入报告。

## 4. 交付物

1. `reports/design/2026-08-26-stars-candidates-evidence.md` —— 证据表（上表全字段）+
   明确的 PASS/FAIL/BORDERLINE 建议 + 每条判断的证据链。
2. `reports/design/2026-08-26-stars-candidates-evidence.json` —— 同内容的机器可读版
   （候选→字段→证据），供集成时程序化核对。
3. 分支上一个原子 commit（仅上述两文件）；**不改任何生产代码/导出/前端**。

## 5. 铁律

纯调查 lane；0 ledger/frozen/config/prereg/OOS；真实 EDGAR 数据（不编造申报期）；
不 push；不动主仓工作树；junction 目录永不 rm -rf。

## 6. 报告格式

(a) 现役 40 名单确认与策展配置落点；(b) 考察了几个候选（请求数记账）；(c) PASS/FAIL/BORDERLINE
各几人、名字清单；(d) 中文名/类别建议摘要；(e) 两份文件路径 + commit hash；
(f) 若全部 FAIL 也如实交付——诚实空结果是合法结果。
