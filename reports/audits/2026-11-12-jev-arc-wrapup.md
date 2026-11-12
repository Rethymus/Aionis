# 2026-11-12 Jev 弧线收官报告（定夺框架条目 4，本轮交付物）

> append-only；勘误只追加不回改。素材=定夺框架条目 4 交办 + 本会话实测收敛事实；
> 命名承 `reports/audits/2026-11-12-iterate-round{,-2}.md` 惯例。引用源：
> `state/backlog.md`、`reports/audits/2026-11-12-iterate-round{,-2}.md`、
> `scripts/monthly_review.py`、`docs/ops-local-refresh.md`（文中行号除特别注明外
> 均为 2026-11-12 收官时点实读值，含本轮两处 append 后的顺移）。

## 一、四轮弧线表（消歧 → 协议 → 深化 → 收官）

| 轮 | 日期 | commit（实证） | 落点（实读） | 语义 |
|---|---|---|---|---|
| 消歧 | 轮 130-续 | `db10a085a1`（2026-11-11 22:08） | 三落点：backlog 名词指认资料区（现 :98 起）/ `docs/ops-local-refresh.md:286` 判别/生成分层小节 / `iterate-round.md:7` Jev 专题章 | Jev=TypeSafe System One 判别式决策模型，与 JEPA 无关；判别/生成分层止步命名，不宣称认知架构 |
| 协议 | 轮 131 | `b298469235`（pickaxe 实证，见下勘误） | `monthly_review.py`：{answer,p} bounded question 契约 + `parse_bounded_answer` :1286-1309 三态兜底 + `render_card` prediction 槽 p 不代填 :958-969 + `reconcile_predictions` Brier 式对账 :981-1042 | 预先枚举+只回选项+置信度的运维层同构；引擎绝不代填 p；format-miss 诚实降级、原文留档 |
| 深化 | 轮 131-续（五条） | `df5416a893`（GLM 枚举注记+成本对照+阅读索引①②）/ `a129199e3d`（延伸索引④⑤⑥）/ `bdece20155`（judgments/facts 分账）/ `d3333a3bf`（预枚举 A\|B\|C） | `ops-local-refresh.md:314` GLM 枚举注记、`:327` 成本对照；backlog 延伸索引④⑤⑥（现 :129-147）；`monthly_review.py:963`/:991-1004/:1024-1041 分账呈现、`:1277-1283` 预枚举常量 | 一手同形支撑 + 量化成本对照 + 判断/事实分账 + 协议选项集闭合（A\|B\|C） |
| 收官 | 轮 131-续（本报告） | 本轮三件施工（§五） | 本报告 + OTel GenAI 命名锚注记（`ops-local-refresh.md:346-362`）+ backlog 前沿四条（:77 小节，条目 14-17） | 弧线关账：采纳/不采纳双清单、在飞/已推送收敛、待业主区 |

**勘误（交办素材 commit 归属修正，append-only）**：交办将 `df5416a893` 归协议轮——
pickaxe 实证（`git log -S"parse_bounded_answer"` 与 `-S"def reconcile_predictions"` 双证）
协议实现 commit 为 **`b298469235`**（round 131，迭代轮 2 条目 4-5）；`df5416a893` 主题为
iterate 轮 2 条目 1-3（RLCD 锚+取向差异+阅读索引①②+:697 勘误），且「GLM json_object
枚举协议」字符串 pickaxe 证实随 `df5416a893` 入库（与 `5a0c3642dd` 入册表述一致）——
弧线表按实证修正归属。

## 二、前沿采纳/不采纳双清单

### 采纳侧（backlog-frontier 四条，仅索引不装包；已入册 `state/backlog.md:77` 小节）

1. **uv lock --check**——doctor 第 9 层候选（high）；lockfile 与 pyproject 脱钩即报错，
   护 H6 version-pinned 语义与 1308 限额续跑后环境一致性；uv 已在工具链零新依赖
   （本会话 `uv lock --check` 实跑 exit=0）。详见 `backlog.md:83`。
2. **river PageHinkley**——medium；限审计/呈现面变点提示，n=1 禁检测拟合、
   min_instances 不调参红线注记随条目。详见 `backlog.md:89`。
3. **duckdb 跨源 SQL 对账**——medium；限 `uvx` 一次性 CLI，不入 pyproject、不常驻。详见 `backlog.md:93`。
4. **ty 类型检查**——low；低 churn 模块试点前须业主点头，不得入门禁。详见 `backlog.md:95`。

任何装包须业主点头（§四.3）。

### 不采纳侧（rejected 八条，含理由；理由为定夺框架条目 4 素材给定）

| # | 条目 | 理由 |
|---|---|---|
| 1 | Langfuse | 服务型长驻——违「无后台长驻进程」红线 |
| 2 | Phoenix | 服务型长驻——同上 |
| 3 | Opik | 服务型长驻——同上 |
| 4 | inspect_ai | 调用面无增量——bounded question 枚举协议已覆盖运维评测面 |
| 5 | promptfoo | 调用面无增量——同上 |
| 6 | popmon / NannyML（合并一条） | 停更——不引维护停滞轮子 |
| 7 | Letta | 记忆自改写语义——违 `state/handoff.md` 轮次账本 append-only（勘误只追加不回改）红线 |
| 8 | LiteLLM | 换路由无增量——`ProviderRouter`（`src/aionis/extraction/providers.py`）已有 RPM/TPM+cooldown+幂等盘缓存（Option A，2026-08-03） |

边界说明：本清单**排除在册 13 条**（`backlog.md:63-75`——那是登记待裁定面，非 rejected）
与**已落地机制**（{answer,p} 协议、ProviderRouter、幂等盘缓存等已落地者不进候选清
单）。八条拒绝由均为红线/架构/维护性判定，不涉许可证判定。

## 三、在飞/已推送区分（演进如实记录）

- **审计时点**（外向调研时）：本地 ahead 4 未推送（`bdece20155`/`d3333a3bf1`/
  `a129199e3d`/`5a0c3642dd`）——交办素材给定。
- **本会话实测（2026-11-12 收官时点）**：`git log origin/main..HEAD` 输出 **0 条**、
  `git status -sb` 无 ahead/behind（本地与 origin 齐平）；`git merge-base --is-ancestor`
  逐一确认 `db10a085a1`、`df5416a893`、`bdece20155`、`d3333a3bf1`、`a129199e3d`、
  `5a0c3642dd`、通道 `3fba104ac9` 均已在 origin/main；弧线全部 commit（含 `b298469235`，
  因齐平+在 HEAD 历史内）随之在 origin。审计时点的 ahead 4 已全部收敛推送。
- **当前在飞**：本轮收官三件施工为工作树未提交态（`docs/ops-local-refresh.md` +17、
  `state/backlog.md` +21、本报告新建），待统一门禁提交——此为演进后的新在飞集，
  如实记录，不与 ahead 4 混读。

## 四、待业主区（钥匙在业主，本报告只列不动）

1. **billing 恢复 / Actions 重启**：恢复清单实读在 `docs/ops-local-refresh.md:400`
   （「恢复清单（业主 billing 解锁后，钥匙在业主）：① `gh workflow enable` …」；
   **勘误**：交办所引 :323-332 与现行文件不符——该区间现为 GLM 枚举注记段，以实读
   :400 为准）。site 滞后实测：gh-pages tip `dbf104f9b6` = 2026-11-02T11:34Z
   （deploy: main@973b389），至 2026-11-12 滞后 **10 天**（审计时点 9 天，随日历 +1）——
   Actions 重启后 Publish site 连带清偿该滞后。
2. **FlexDM 低置信反转重问开启**：`backlog.md:142` ⑥——默认关闭；开启须业主点头
   （该子任务 token 翻倍，仍限月末单场会话内，不新增会话；读数按一致性证据而非
   校准证据消费）。
3. **任何装包裁决**：前沿四条与全部延伸索引条目均仅索引；任何装包（river/duckdb/
   ty 及后续候选）须经业主裁决。`uv lock --check` 不属装包（uv 已在工具链，仅既有
   CLI 旗标），但其第 9 层落库施工仍照常走 mission 派单。

## 五、本轮收官施工记录（append-only）

- **条目 otel-genai-note（外向调研条目 2）**：`docs/ops-local-refresh.md` 分层小节段尾
  append OTel GenAI 语义命名锚注记，现 :346-362（+17 行；「lessons 块格式」小节顺移
  :346→:363）。registry 文档页 fetch 复核可达且每条 GenAI 属性标 "Moved"（新仓名
  404 未核实，已如实注记）；被引代码锚 `monthly_review.py:981-1042`、
  `llm_client.py:122-134` 只读核验、零改动。
- **条目 backlog-frontier（定夺框架条目 5）**：`state/backlog.md` 前沿吸收区 append
  「### 2026-11-12 增补」小节 :77（+21 行；条目 14-17 于 :83/:89/:93/:95）。
  `uv lock --check` 本地实跑 exit=0、`uv lock --help` 旗标语义实测；`collect_layers()`
  实读 L1-L8 无锁文件层；`backlog_open_candidates`（`monthly_review.py:698-713`）实读
  确认 propose 引擎不解析新条目（仅读「开放候选」节 `- ` bullet）。行号顺移注记：
  名词指认资料区 :77→:98、延伸索引④⑤⑥ :96-122→:129-147（+21）。
- **条目 arc-report（定夺框架条目 4）**：本报告新建（本节）。
- 推送收敛与在飞现状见 §三。
- **如实边界补记（轮 132 round2-lows，append-only）**：①交办假设的「iterate-round-2
  含 reconcile_predictions :981-1042 行号锚」经 grep **查无对应物**（该报告仅 :101
  按函数名提及，勘误/边界记已 append 至该报告段尾）；②本报告 §一/§五 所引
  monthly_review.py 行号系删除 `PREDICTION_LINE_RE`（原 :978，全仓 grep 零消费方）
  前时点值——删除后 :978 之后锚点统一 −3（reconcile :981-1042→:978-1039、
  :991-1004→:988-1001、:1024-1041→:1021-1038、WATCHDOG :1277-1283→:1274-1280、
  parse :1286-1309→:1283-1306；:958-969 与 :698-713 在删除点之前不变）。

## 六、lane-ledger-repin 事态核验收尾（定夺框架条目 1，append-only）

原处方「重钉至 11a9d903」经四证据复跑**据实废止**（照做会钉错值弄坏测试，
如实优先于照方抓药）：①通道 `--status`=ok_committed（finished
2026-11-12T18:59:44.99、pushed=true、soft_fails=[]）——已收工；②`git show
3fba104ac9 --numstat -- runs/ledger.jsonl`=空——lane 提交未触 ledger；③ledger
sha256 实算 `ec6d2892…cca10`=`tests/test_web_terminal_data.py:1538` 现钉值
（非 11a9d903），工作树 diff 亦空；⑤`test_ledger_append_only_not_mutated_by_export`
通过（exit 0）。自愈机制=`tidy_ledger()`（`scripts/ops_local_refresh.py:419-431`
+docstring :28-33）丢弃 display-only data_ingest 追加行（reddit_sentiment/
news_feed，CI ephemeral-runner 语义）——审计时点的在飞行行从未入任何 commit，
11a9d903 从未存在于已提交历史。测试钉与 ledger 本体均未触碰（只读）。
详见 handoff 轮 132-续。
