# 2026-11-13 Jev 落地物索引地图（jev-artifact-map，轮 134-续5 交办）

> 性质：**活文档索引**（durable registry，非一次性仪式，ADR-006）。回答「Jev 弧线
> （轮 130-续 → 131 → 131-续 → 134 系）在仓内每件落地物在哪、谁消费、怎么验证」。
> 钉锚纪律：本图全部行号为**本会话施工前在 HEAD `0a1ce62107` 逐一重测值**（重测
> 命令=逐锚 `sed -n`/`grep -n`，见文末验证记录）；唯一既有地图
> `reports/audits/2026-11-12-jev-arc-wrapup.md` §一的代码锚系 2026-11-12 收官时点
> 实读值，经轮 132 删行整体 −3 漂移（§四），**只能作时点参考**——本图即为此而生。
> 活文档红线：后续编辑者引用本图行号前，须以届时 HEAD 重测；漂移事实记入本图
> 对应节，不回改旧图。红线复述：Jev 专题全程**协议级文档+state 落地、代码级仅
> monthly_review 运维面**（`iterate-round.md:7` 在册裁定），研究管线零触碰。

## 一、仓内落地物主表（26 件，24→26 系 2026-11-13 轮 136 勘误——分面 7+2+10+3+4=26，`grep -c '^| [A-E][0-9]'` 逐表数得；入口行号=HEAD `0a1ce62107` 实测）

### A. 代码面（`scripts/monthly_review.py`，7 件）

| # | 落地物 | 入口（实测） | 轮次/来源 | 验证方式 | 消费方（谁读/谁写） |
|---|---|---|---|---|---|
| A1 | 判别/生成分层注记（event 四选一契约说明） | `scripts/monthly_review.py:1268` | 轮 131-续（`d3333a3bf1`） | `sed -n '1268p'` 实读 | 读=施工员/复核者；写=运维面提交 |
| A2 | `WATCHDOG_BOUNDED_QUESTION` 常量（{answer,p} 有界问题，预枚举 A\|B\|C） | `scripts/monthly_review.py:1274-1281` | 轮 131（`b298469235`）+ 131-续预枚举（`d3333a3bf1`） | `sed -n '1274,1282p'` 实读；tests `tests/test_monthly_review_propose.py:355-362` 断言选项集 | 写=`lesson_seeds`（`:1325` 注入 `watchdog_bounded_question` 键）；读=月末会话 LLM 作答 + tests |
| A3 | `parse_bounded_answer`（三态解析兜底：ok / format-miss 原文留档 / 越界 p 拒收） | `scripts/monthly_review.py:1283-1307` | 轮 131（`b298469235`） | `sed -n '1283,1307p'` 实读；**生产零调用**——全仓 `grep -rn parse_bounded_answer` 仅注释两处（`:1268`/`:1346`）+ 测试四例 | 读/写=`tests/test_monthly_review_propose.py:329/:335/:341/:347`（唯一调用方）；生产调用面=零（设计用途=月末会话回答的解析兜底，月末首跑尚未发生） |
| A4 | `render_card` prediction 槽（p 绝不代填，待月末会话填 0..1） | `scripts/monthly_review.py:951-975`（函数）；prediction 槽 `:958-969` | 轮 131（`b298469235`） | `sed -n '951,977p'` 实读 | 写=`run_propose` 生成提案卡；读=月末会话粘贴回 backlog 候选区 |
| A5 | `reconcile_predictions`（Brier 式对账：resolved 记 (p−y)²，judgments/facts 分账呈现，p>0.6 高带仅自动进候选） | `scripts/monthly_review.py:978-1039`（函数；分账 docstring `:988-1001`，高带呈现 `:1021-1038`） | 轮 131（`b298469235`）+ 131-续分账（`bdece20155`） | `sed -n '978,1042p'` 实读；tests `tests/test_monthly_review_propose.py:385-416` 两例 | 调用方=`scripts/monthly_review.py:787`（`--weekly` 只读扫描 findings 聚合，零写零统计越过逐条平方误差）；读=夜报班人工 |
| A6 | `EVENT_OP_RE`（backlog 条目 event: ADD\|UPDATE\|DELETE\|NONE 四选一契约门） | `scripts/monthly_review.py:1130`（匹配点 `:1155`） | 轮 126 系（gen2 契约，Jev 专题引用为先例面） | `grep -n EVENT_OP_RE` 实读 | 读=`--propose` 提案卡/`--append-lessons-from` 写回路径；写=运维面提交 |
| A7 | `lesson_seeds` + `render_reflexion_section`（确定性月末事实种子 + Reflexion 节渲染，A2 经 `:1325` 注入；`:1346` 为 A3 的注释互引） | `scripts/monthly_review.py:1309-1327`（lesson_seeds）/ `:1328-1366`（render_reflexion_section；下一标记 :1368） | 轮 131 系 | `grep -n` + `sed -n '1309,1366p'` 实读；tests `tests/test_monthly_review_watchdog.py:327-340` | 调用方=`scripts/monthly_review.py:1474/:1478`（`--weekly`/`--lessons` 渲染路径）；读=月末会话/夜报班 |

### B. 测试面（`tests/`，2 件——A3 的唯一调用方）

| # | 落地物 | 入口（实测） | 轮次/来源 | 验证方式 | 消费方 |
|---|---|---|---|---|---|
| B1 | `parse_bounded_answer` 四例（合法/多 JSON 取首个双键/format-miss 原文保留/越界 p 拒收） | `tests/test_monthly_review_propose.py:329-350` | 轮 131 | `grep -n parse_bounded_answer tests/` 实读 | CI 门禁（`uv run pytest`）；改动 A3 必过 |
| B2 | `reconcile_predictions` 两例（三态/空 backlog）+ `WATCHDOG_BOUNDED_QUESTION` 常量断言 | `tests/test_monthly_review_propose.py:355-362, 385-416` | 轮 131/131-续 | 同上 | 同上；改动 A2/A5 必过 |

### C. 文档面（`docs/`，10 件）

| # | 落地物 | 入口（实测） | 轮次/来源 | 验证方式 | 消费方 |
|---|---|---|---|---|---|
| C1 | 判别层/生成层分层小节（值班协议认知固化，专题条目 4） | `docs/ops-local-refresh.md:286` | 轮 130-续（`db10a085a1`） | `sed -n '286p'` 实读 | 读=每会话 doctor/值班协议遵循者 |
| C2 | 「不引入外部判别 API」bullet（Jev API/typesafe-sdk 红线） | `docs/ops-local-refresh.md:299` | 轮 130-续 | `sed -n '299p'` 实读 | 读=施工员红线检查（在册 #2 裁定） |
| C3 | GLM json_object 枚举协议一手注记 | `docs/ops-local-refresh.md:314` | 轮 131-续（`df5416a893`） | `sed -n '314p'` 实读 | 读=A2/A3 协议设计依据 |
| C4 | 判别/生成成本结构对照（量化引用锚） | `docs/ops-local-refresh.md:327` | 轮 131-续（`df5416a893`） | `sed -n '327p'` 实读 | 读=预算/停增烧决策 |
| C5 | OTel GenAI 语义命名锚注记 | `docs/ops-local-refresh.md:346-362` | 轮 131-续收官 | `sed -n '346,362p'` 实读 | 读=观测面命名遵循者 |
| C6 | 跨月累积 p 呈现护栏注记（p-trajectory-presentation；只记录、anytime-valid 绝不构成引入 eval 层重算许可） | `docs/ops-local-refresh.md:363-385` | 2026-11-13 append | `sed -n '363,385p'` 实读（:385 节尾「不采用。」，:386 起为下一节） | 读=A5 消费口径；写=护栏追加者 |
| C7 | lessons 首跑预演注记（月末首块写入前注意事项 a-d） | `docs/ops-local-refresh.md:401` | 2026-11-13（monthend-dryrun） | `sed -n '401p'` 实读 | 读=2026-11 月末首跑者 |
| C8 | arXiv:2611.11480 过自信第三方实证引用（>0.9 分带仅 66% 相关、需 2 参数校准） | `docs/ops-local-refresh.md:428-431` | 轮 134-续3（frontier-citation-anchors） | `sed -n '428,431p'` 实读 | 读=p 仅记录性/禁显著性声称边界的第三方支撑 |
| C9 | arXiv:2611.12966 PIT 违规 50.8% 引用锚（G2 snapshot-vintage 门独立实证） | `docs/data-intake-rubric.md:51` | 轮 134-续3 | `sed -n '51p'` 实读 | 读=7-gate 数据进门复核 |
| C10 | 外部同构先例引用锚节：arXiv:2611.13962（预注册公开哈希）`:55-61` + arXiv:2611.09286（门控解锁复制）`:62-64` + 本图随图追加的「Only facts can block」先例句 `:68-74`（§五） | `docs/08-lessons.md:50-74`（节首 :50，节尾 :74，下一节 :75；:68-74 为本轮追加后的复测值） | 轮 134-续3 + 本轮（§五） | 追加后 `grep -n` 复测（节界 :50/:75、新句 :68） | 读=复盘/审计；写=引用锚追加（仅引用不改流程） |

### D. state 面（`state/backlog.md`，3 件）

| # | 落地物 | 入口（实测） | 轮次/来源 | 验证方式 | 消费方 |
|---|---|---|---|---|---|
| D1 | Jev 代码级候选主条目（{answer,p} 输出契约+预测字段+Brier 对账；2026-11-12 登记、代码级 rejected 但协议级已落地于 A 面） | `state/backlog.md:52-57` | 轮 131 登记候选 | `sed -n '52,57p'` 实读 | 读=`--propose` 七卡生成面/月末会话 |
| D2 | 延伸索引⑦（arXiv:2611.11480 过自信实证，仅引用不装不接） | `state/backlog.md:58-62` | 轮 134-续3 append | `sed -n '58,62p'` 实读；backlog 改后 `--propose` 实弹 exit 0 在册（轮 134-续3） | 读=诚实边界第三方印证；写=引用锚 append |
| D3 | 名词指认资料区（Jev 指认规则，杜绝 JEPA 混读；①-⑥：awesome-system-one 清单①、GLM 官方②、lm-evaluation-harness 枚举打分④`:146`、RouteLLM 阈值校准边界⑤`:154`、低置信选项反转重问⑥`:159-165` 含 open-alternative-jev 选项序翻转警示 72% vs 21%） | `state/backlog.md:115-165`（节首 :115，下一节 :167） | 轮 130-续（`db10a085a1`）+ 131-续延伸 | `grep -n` + `sed -n '115,165p'` 实读 | 读=每次涉 Jev 名词的会话首查 |

### E. 报告/决策面（4 件）

| # | 落地物 | 入口（实测） | 轮次/来源 | 验证方式 | 消费方 |
|---|---|---|---|---|---|
| E1 | Jev 专题章（协议级·文档+state；代码级 rejected 的在册裁定） | `reports/audits/2026-11-12-iterate-round.md:7` | 轮 130-续 | `sed -n '7p'` 实读 | 读=范围裁定遵循者 |
| E2 | Jev 弧线收官报告 §一四轮弧线表（消歧→协议→深化→收官；行号=2026-11-12 时点，见 §四勘误） | `reports/audits/2026-11-12-jev-arc-wrapup.md:9-16` | 轮 131-续收官 | `sed -n '9,16p'` 实读 | 读=弧线回溯入口（时点参考） |
| E3 | frontier-citation-anchors 落点表①（2611.11480 → backlog:58）+ 正文 :61 | `reports/audits/2026-11-13-iterate-round-6.md:61, :83` | 轮 134-续3 | `sed -n '61p;83p'` 实读 | 读=引用锚台账 |
| E4 | ADR-004 Evidence 引用补强（arXiv:2611.03985 掩码≠匿名） | `decisions/ADR-004-llm-structural-only-no-market-impact.md:24` | 轮 134-续3 | `sed -n '24p'` 实读 | 读=LLM 结构面边界裁定 |

## 二、外部同构实证列（四锚，本会话 fox_fetch 逐页一手复核）

### 2.1 首选锚：qkal/Canny（README 一手，MIT，v0.4.0）

「Supervision layer for AI coding agents」：确定性 hooks 挂 Claude Code/Codex CLI，
append-only ledger（`~/.canny/sessions/`），done-gate。唯一规则原文：
**「Facts go to code. Judgments go to Jev. Only facts can block.」**

| Canny 事实 | Aionis 同构物 | 对应落地 |
|---|---|---|
| 确定性 hooks 判定、Jev 仅 advise（「Jev never blocks」） | 值班协议判别层零 LLM 阻断（判别层只由本地确定性代码构成） | C1/C2 |
| facts（账本可证：exit 码、文件变更）与 judgments（口头置信度）分账 | `reconcile_predictions` judgments(p)/facts(y/due) 分账（`bdece20155`） | A5 |
| done-gate=exit 码契约（无 passing check 即拒），概率过线不构成阻断 | exit-3 契约门 + p>0.6 高带仅自动进对账候选、无自动处置 | A5/A6 |
| 「The same session always produces the same verdict, and canny replay proves it from the ledger」 | H6 确定性：same-sig rerun bit-identical（ledger 重放式可证） | 全局红线 |

边界注记：Canny 是**同构先例引用**，不装不接（在册 #2：不引入外部判别 API）。

### 2.2 并列锚：confidence 扰动审计族（两篇，互为张力，如实并列）

- **arXiv:2611.12521**（Delaunay，cs.LG，2026-11-09 提交；abs 页一手复核）：
  *Can the Confidence and Decisions of System 1 Models Be Trusted?*——五发现：
  ①provider confidence 是闭式散度变换（1−H(p)/ln K；Clef-27B 为 normalized
  margin）而非经验准确率；②**一请求捆多问引致跨问干扰**（Tev1-0.8B 二值翻转
  11.7-22.4%）——与 Aionis「月末单场单问」（A2）同向支撑；③≥4B System 1 在语法
  扰动下校准**优于** logprob/JSON 基线（ECE 0.030-0.087 vs 0.144/0.378）——与在册
  2611.11480「过自信」读数**方向相反**，张力如实登记：两文任务域/模型不同，仓内
  立场不押注任何一侧（p 仅记录性、禁显著性声称、禁再校准拟合的诚实边界对两读数
  都成立，C8/D2）；④提示注入防御 AUROC 0.988-0.998；⑤单前向使 512-联盟 XAI 可交互。
- **arXiv:2611.15592**（Rastogi，cs.AI，2026-11-11 提交；abs 页一手复核）：
  *Small Heads, Strong Decisions*——同协议重训五种 readout：head 复杂度不影响精度
  （0.5M cosine head ≈ 27M joint schema head）、**backbone 才是主导**（0.6B→4B 域内
  +4pt/held-out +11pt）；并称一 prompt 多问与逐问精度相当（1.6× 推理加速）——与
  12521 发现②的跨问干扰**构成第二组张力**，同上处理：仅登记，不据此改任何在册
  协议。另证 Jev 2026-09 发布、开放跟随者 Nimble/Decision 1.0-3.0/Clef（生态节素材）。

### 2.3 并列锚：TypeSafe Model jaggedness 页（一手复核）

`docs.typesafe.ai/model-jaggedness`（Reference 节）九类失败模式：①literal reading
②math/numbers（counting/数值表示/score 插值）③date-time 比较④indirection⑤大 state
无关细节（context rot）⑥adversarial content⑦指令与 criteria 矛盾⑧**choice 选项序**
（顺序影响答案、偏向首个选项）⑨generation。页尾红线句与 Aionis 判别层纪律同构：
「avoid … Asking the model something code can compute exactly. Hiding several
judgments inside one question.」⑧与在册⑥ open-alternative-jev 卡的选项序翻转敏感度
警示（72% vs 21%，D3）同向互证。

## 三、生态时点快照（2026-11-13 抓取时点；仅快照，不构成接入依据）

| 项 | 事实 | 一手复核方式 | Aionis 口径 |
|---|---|---|---|
| Jev 本体 | Wikipedia「Jev (AI model)」：2026-09-15 限免早访问（TypeSafe AI，2024 创立，$40M seed DCVC）；判别式、返回类型化分布+置信度、不生成文本；RLCD（合成数据训练，Brier 式损失疑似）；置信度=normalized margin 闭式；**正文+参考文献[7]载 Jev 1.14（2026-10-15，MarkTechPost：images/box type/262k ctx）**；infobox stable 字段抓取时点仍为 jev-1.13.0（差异如实记） | fox_fetch 全文（含 infobox 与 ref [7]） | 名词指认在册口径（D3）不变：Jev=TypeSafe System One 判别式决策模型，与 JEPA 无关 |
| Cloudflare Clef | HF 模型 `Cloudflare/clef`：**license=apache-2.0**（API `cardData.license` 实证）、base=Qwen/Qwen3.8-27B（finetune）、27.36B BF16、createdAt 2026-09-30、tags 含 systemone/decision-model；LocalLLaMA/typed-decisions 榜（2026-10-16 跑）：acc 0.7275/Brier 0.1032/ECE 0.0253 | fox_fetch HF API `models/Cloudflare/clef` | 许可合规（MIT/Apache/BSD 白名单内）但**仅登记不装不接**——provider 池仍限 GLM/SiliconFlow/ModelScope（在册红线） |
| OpenJev | 交办调研（medium 条）载其许可证 CC BY-NC 4.0 → **按白名单直接排除**；本会话 URL 探测（github.com/openjev/openjev）404 未复得原始仓库位，许可证事实以调研一手核为准，此处如实标注 | 交办素材；本会话仅探测未复得 | 排除裁定不依赖复访：CC BY-NC 族任何落点均落白名单外 |
| 在册⑥ open-alternative-jev 对账 | 在册卡（D3 :159-165）载弱模型选项序翻转敏感度警示 72% vs 21%；本会话 jaggedness 页⑧一手复核同向（选项序影响答案、偏向首个）；对账结论=在册警示获官方文档级独立印证，无冲突 | D3 实读 + §2.3 一手 | 反转重问模式仍=待业主点头可选、默认关闭（在册，不动） |

## 四、arc-wrapup 弧线表代码锚 −3 漂移勘误（arc-wrapup 本体零改动）

根因（git 实证）：轮 132 commit `28b2e7d5b1` 删除 `PREDICTION_LINE_RE` 死变量
（删前全仓 grep 零消费方），`:978` 后锚点统一 −3。arc-wrapup 自述其行号为
2026-11-12 收官时点实读值——时点报告纪律，**不回改**；漂移记入本表：

| arc-wrapup `:13-15` 载值（2026-11-12 时点） | 本会话 HEAD `0a1ce62107` 实测 | 漂移 |
|---|---|---|
| `parse_bounded_answer` :1286-1309 | **:1283-1307**（A3） | start −3 / end −2（函数体内另删 1 行） |
| `render_card` prediction 槽 :958-969 | **:958-969**（A4） | **0**（删行在 :978 后，未波及） |
| `reconcile_predictions` :981-1042 | **:978-1039**（A5） | −3 / −3 |
| 预枚举常量 :1277-1283 | **:1274-1281**（A2） | start −3 / end −2 |
| 分账呈现 :963/:991-1004/:1024-1041 | **:963 不变**/:988-1001/:1021-1038（A5） | :963 在删行前不动；后两段 −3 |
| backlog 名词指认区「现 :98 起」 | **:115 起**（D3） | +17（append 顺移，非删行） |
| backlog 延伸索引④⑤⑥「现 :129-147」 | **:146-165**（D3） | append 顺移 |
| `ops-local-refresh.md:346-362` OTel 注记 | **:346-362**（C5） | 0（doc 面未受代码删行影响） |

## 五、随图动作（本图触发的外部引用锚追加，仅引用不改流程）

`docs/08-lessons.md` 外部同构先例引用锚节（C10）追加「only facts can block」先例
句一条（源=§2.1 Canny README 原文，本会话一手复核；沿在册引用锚先例格式，明示不
改任何在册流程/门/红线）。除此之外本图零改动任何既有文件。

## 验证记录（本会话施工前逐锚实跑）

- 代码/测试/state/docs/报告/决策锚：`sed -n '<range>p'` / `grep -n` 逐锚实读（本图
  各行「入口（实测）」列即其输出）；HEAD 复核 `git log --oneline -1` = `0a1ce62107`。
- 消费方事实：全仓 `grep -rn parse_bounded_answer --include='*.py'`（生产调用=0）；
  `grep -n reconcile_predictions\|lesson_seeds\|render_reflexion_section\|EVENT_OP_RE
  scripts/monthly_review.py`（调用点 :787/:1155/:1474/:1478）。
- 外部四锚：fox_fetch 逐页（github.com/qkal/Canny、arxiv.org/abs/2611.12521 与
  2611.15592、docs.typesafe.ai/model-jaggedness）+ HF API（models/Cloudflare/clef）
  + Wikipedia「Jev (AI model)」全文。OpenJev 原始仓库位本会话未复得（探测 404），
  如实标注于 §三。
- 晚间通道：施工前 `uv run python scripts/ops_local_refresh.py --status` =
  `ok_committed`（2026-11-12 完成，未在运行）。
