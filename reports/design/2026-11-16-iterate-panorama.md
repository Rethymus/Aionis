# 全景盘点报告 iterate-panorama：轮 1→18 时间线 + RLCD 关键函数 + 锚守卫三层演进 + ①-60 锚图谱 + 演化速率统计

- **日期**：2026-11-16（文件名日期系交办给定路径；施工时点 2026-11-15 会话——沿轮 16/18 报告抬头时点注记先例）。
- **定位**：iterate 长周期迭代序列（轮 1→18）的**单一导航入口**——后续会话与业主经此报告直达时间线/函数面/守卫演进/锚图谱/速率统计五视图。**迁移前门禁基线冻结载体**（框架明示盘点数据源含迁移前基线）。
- **数据源（全只读）**：14 份在册审计报告（`reports/audits/2026-11-12-iterate-round*.md` 系列，ls 实测恰 14 份）+ `state/handoff.md` iterate 序列区段（:2916-:2989，python 逐行实读轮号映射）+ `state/current.md` 顶部条 + 训练法设计报告（`reports/design/2026-11-14-personal-training-method-and-automation-ladder.md`，300 行）+ `scripts/monthly_review.py` grep 现值与 `git log -S` 引入提交 + `state/backlog.md` 延伸索引实读。**以审计盘点为准，非轮次自报**。
- **迁移前门禁基线（本会话实跑冻结）**：`uv run python scripts/anchor_guard.py` → **explicit=100 / hit=98 / drifted=0 / lost=2 / external=0 / semantic=0 / bare-unverified=503，rc=0**——与交办所引审计实跑值逐值一致（本报告落盘前时点；本报告位于 reports/design/ 非守卫扫描面——`anchor_guard.py:60` DEFAULT_SOURCES 仅 runbook+handoff，落盘不扰读数）。

---

## §一 轮 1→18 时间线（源=审计报告+handoff 条目，以在册为准）

| 轮 | 日期 | handoff 映射 | 主题（条目） | 载体 | 关键提交 | 复核意见（清偿闭环） |
|----|------|------|------|------|------|------|
| 1 | 11-11/12 | 轮 130-续 | Jev 专题 `jev-protocol-sediment`（协议级文档+state；RLCD=TypeSafe AI System One 判别式决策模型 2026-09-15，与 JEPA 无关——消歧义结论入册） | 报告在册（53 行） | `db10a085a1`/`df5416a893` | —（报告仅 append 勘误一处） |
| 2 | 11-12 | 轮 131 | 六条落地：{answer,p} bounded question 契约+`parse_bounded_answer`+Brier 式 `reconcile_predictions`（含复活链抢救） | 报告在册（139 行） | `b298469235` 等 | 3 low（round2-lows，轮 132 清偿） |
| 3 | 11-12 | 轮 132 | 五条目：lane-ledger-repin 等 | **补写**（发布失败：文件不存在，收尾会话按已提交记录补写） | `d1f83e41bb`/`7db2bd2b70`/`d3950253a7`/`28b2e7d5b1`/`d8fb6a1b5c`（另晚间通道 `3fba104ac9`） | 报告复核记=行号复核自查，无外部复核意见在册 |
| 4 | — | — | **无载体无记载**（round-5 报告补写声明注记：仓内 handoff/current/backlog/runbook/.omc 四域 grep 无 iterate 轮 4 记载——不代写不虚构） | 缺失 | 无 | 无从计证 |
| 5 | 11-12→13 | 轮 133 | 三条目；报告承载 anchor-debt-cleanup 六条存量锚债复核 low 清偿 | **补写**（同轮 3 机制，先例 `bf9813163d`） | `af6e1af275`/`c9685dba97`/`3735cf1283`/`57e6039bcc` | 3 low（round5-lows，轮 134/134-续 清偿） |
| 6 | 11-13 | 轮 134-续2 | monthend-dryrun 月末首跑就绪证明（三链实弹走查+tmp 隔离写回） | 报告在册（119 行，首建-后补体例） | `02f7cb2816` | — |
| 7 | 11-13 | 轮 135 | 六章节：monthend-readiness/jev-artifact-map/frontier-reading-index/例行核查/state/待业主区（纯 docs） | 报告在册（143 行） | `0a1ce62107`/`14015fe4d2`/`1794564096`/`811cedab37` | 3 low（round7-lows，轮 136 清偿） |
| 8 | 11-13 | 轮 136-续 | 四条目：round7-lows 三 low 清偿/frontier ⑩⑪⑫/`--verify-bounded` 最小生产接线（`run_verify_bounded` 诞生）/round8-report-ledger | 报告在册（65 行） | `da29c32bd6` | （本轮承载轮 7 清偿） |
| 9 | 11-13 | 轮 137 | 五条目收官：训练法定案稿+自治梯 runbook 入册+**训练法三环代码面**（环 1a 聚合器/环 1b 注入/环 2 ExpeL 钩子） | **无 round-9 报告在册**（ls 实测）；handoff 轮 137 条目+设计报告附录 B.1-B.5 as-built 承载 | `f51e759eb7`（三环 145/19）等 | 设计报告勘误批（39 用例计数等，residuals-cleanup 轮 138） |
| 10 | 11-13/14 | 轮 139 | 四条目：first-month-playbook（M）/frontier/residuals-cleanup/flywheel-rehearsal（M 核心） | 报告在册（146 行） | 收尾五原子批（`148fdd62ea`/`53b8da4b2b`/`5479bcb144`/`63c30cf42a`/`e9cf4e42aa` 等） | round10-hunk-errata（轮 140）：hunk 散文勘误 232→238（勘误非复核意见） |
| 11 | 11-14 | 轮 141 | 三条目：frontier ⑱-㉔+LIMBO 注记/focus-feedback-selector 重点反哺行+promotion-gate-function（`promotion_gate_assessment` 诞生） | 报告在册（126 行，首建-后补体例） | `6c04ce5737`/`600938d8b7` | — |
| 12 | 11-14 | 轮 142-146 | 五条目：frontier ㉕-㉛/anchor-errata-batch/**overdue-outcome-watch+feedback-dedup-contract+cross-month-evolution 三代码条目**（`overdue_outcome_records`/`feedback_dedup_verdict` 诞生） | **补写**（发布失败零 git 历史，与轮 10 同款成因——轮次块在册注记非静默丢失） | `98c6dabcd3`/`f5db3c3527`/`1873f41013`/`421fccbdc3` | — |
| 13 | 11-14 | 轮 147/147-续 | 三条目：frontier ㉜/anchor-errata-preflight/patch-unit-fields 三行结构化首例+**anchor_guard v1 诞生**（248 行纯 stdlib+5 钉） | **宿主会话永久死亡**（dwfrun-421b0517 errored=Model creation failed）；round-13 报告不存在 | 轮 15 代收：`ce52d11d06`/`0c19049104` | —（代收即恢复） |
| 14 | 11-15 | 轮 148-151 | 四条目（分支 B 降级设计稿）：frontier ㉝-㉟ 就绪块/insight-quality-gate/gate-assessment-bridge/memp-insight-lifecycle 设计稿 | 报告在册（222 行） | `6f587cf91e`/`adb7062328`/`6e13220cc7`/`0fce06f7dc` | 复核归属轮 14 审计（设计稿无施工复核面） |
| 15 | 11-15 | 轮 152-157 | 六条目：轮 13/14 代收+backlog post-close+**三设计稿升格施工**（`insight_quality_verdict`/`promotion_gate_summary_line`/`insight_lifecycle_verdict` 诞生）+报告 | 报告在册（88 行=编号八节+辨明段） | `ce52d11d06`/`0c19049104`/`7cd8b717cf`/`fef5fa6f09`/`7586d23782`/`c30390dc4c`+`4525aa84b9` | **findings×4**（轮 157-续 复核勘误批逐条修复：1 high+3 low）；轮 16 例行复核轮 15=**零意见首零** |
| 16 | 11-14 收官 | 轮 158 | 四条目：routine-checks 双读数+轮 15 复核零意见首零/frontier ㊸-㊺/patch-card-surface-rollback（render_card 两 bullet）/anchor-guard-v2 第五态 | **补写**（发布失败=文件未创建，ls+git ls-files 双实测） | `17e04f8207`/`131005ac7d`/`95ff7b4abd`/`8eb67715d6`+报告 `4c1549fab5` | — |
| 17 | 11-14 | （无 handoff 条目，轮 159 补记） | semantic-scope-key-fix 会话：backlog ㊻-53/dead-anchor-hunt/**semantic-scope-key-fix** | **closeout 缺失三证**（报告不存在/handoff 无条目/current 顶部=轮 16——轮 159 补记在案） | `8b191d2896`/`7e3a6bbc7b`/`33c1e875e6` | —（补记即恢复） |
| 18 | 11-15 施工/11-16 命名 | 轮 160 | semantic-scope-key-fix 审计承接：辨明段主题句纠偏（semantic=0=修复后预期真阴性）+决定性实验翻转×5 复现+扩面分批计划只报不落地+报告 | 报告在册（65 行，八节+辨明段） | `c5e9f19185`/`23da555069`/`5e776275f8`/`cf81576c92`+收尾批 `0fc167f0e7` | —（收尾 push 本会话实测已完成：main==origin/main 零偏差） |

**映射口径**：iterate 轮号 ↔ handoff 施工轮号双序列并存（iterate 轮 2=handoff 轮 131、轮 3=132、轮 5=133…沿 round-5 报告在册映射续推）；handoff 另有 2026-10-04 旧 UI 序列同号（:129-:139）——**不机械 grep 定号**（轮 159 双序列辨明先例）。

---

## §二 RLCD 训练法关键函数清单+调用链（现值全 `scripts/monthly_review.py` 实测）

**RLCD 本体锚**：arXiv:2307.12950（runbook :304-305 已入册「判别器反馈即改进信号」）；本仓落地形态=设计报告 §2 三环飞轮（聚合→注入→蒸馏，零梯度零微调全 rides 月末单场）。

**清单（本会话 grep 实测 13 个 def+3 常量；交办口径「11 关键函数」与实测并集 13 的差异如实注记——交办两路素材[审计 grep 9 函数+框架归属映射 4 函数]去重后即 13，不臆造丢函数也不硬凑 11）：**

| # | 符号 | 现值行 | 诞生提交（`git log -S` 实证） | 轮次归属 | 调用点（实测） |
|---|------|------|------|------|------|
| 1 | `run_weekly` | :568 | `a08a8a75a8`（weekly watchdog+monthly reflexion，round 126） | 轮 126（iterate 前置） | main :1785 |
| 2 | `render_card` | :990 | `2569489bed`（gen2 条目 3 propose 引擎，handoff 轮 128-续2） | **交办映射「轮 126」与 git 实证不符，以实证为准**（轮 126 系 `run_weekly`；render_card 属 gen2 批） | run_propose 内 :1254 |
| 3 | `reconcile_predictions` | :1023 | `b298469235`（round 131=iterate 轮 2 条目 4-5） | 轮 2 ✓ | run_weekly 内 :806 |
| 4 | `overdue_outcome_records` | :1100 | `98c6dabcd3`（iterate 轮 12，轮 144/145/146 批） | 轮 12（handoff 轮 145 批）✓ | :816（run_weekly）+:1523（lesson_seeds） |
| 5 | `calibration_bucket_summary` | :1141 | `f51e759eb7`（训练法三环，环 1a） | 轮 137=iterate 轮 9 ✓ | lesson_seeds 内 :1520 |
| 6 | `run_propose` | :1204 | `2569489bed`（gen2 条目 3） | 轮 128-续2 | main :1810 |
| 7 | `parse_bounded_answer` | :1468 | `b298469235`（round 131） | 轮 2 ✓ | run_verify_bounded 内 :1705 |
| 8 | `run_verify_bounded` | :1684 | `da29c32bd6`（bounded-answer-wiring，iterate 轮 8） | 轮 8 ✓ | main :1830 |
| 9 | `feedback_dedup_verdict` | :1933 | `98c6dabcd3`（iterate 轮 12 dedup 契约） | 轮 12（handoff 轮 145 批）✓ | lesson_seeds 内 :1614 |
| 10 | `insight_quality_verdict` | :2031 | `fef5fa6f09`（轮 154 升格施工） | 轮 15（轮 152-157 区间）✓ | insight_quality_report 内 :2131 |
| 11 | `insight_lifecycle_verdict` | :2070 | `c30390dc4c`（轮 156） | 轮 15 ✓ | insight_quality_report 内 :2122 |
| 12 | `promotion_gate_assessment` | :2330 | `6c04ce5737`（iterate 轮 11 条目 2/3） | 轮 11（handoff 轮 141）✓ | promotion_gate_summary_line 内 :2506 |
| 13 | `promotion_gate_summary_line` | :2491 | `7586d23782`（轮 155 gate 桥） | 轮 15 ✓（gate 桥） | run_weekly 尾 :668 |
| C1 | `CALIBRATION_FEEDBACK_NOTE` | :1550 | `f51e759eb7`（环 1b 固定禁令，prohibition≠disposition） | 轮 9 | 注入 :1603 |
| C2 | `INSIGHT_HINT` | :1562 | `f51e759eb7`（环 2 ExpeL 钩子；轮 15 双路径句扩展） | 轮 9→轮 15 | 渲染 :1637 |
| C3 | `GATE_SCOPE_NOTE` | :2305 | `7586d23782`（只算不启用，钥匙在业主） | 轮 15 | :2351 |

**调用链图（节点=现值行号，边=本会话调用点实测）**：

```text
main（:1785/:1810/:1830 分派）
├─ run_weekly（:568，weekly watchdog+reflexion 主链）
│  ├─ :806 proposal_reconciliation → reconcile_predictions（:1023）→ 逐条 Brier 对账
│  ├─ :816 overdue_outcome_records（:1100，逾期 outcome 独立统计块）
│  ├─ lesson_seeds（:1520 区，确定性事实收集，one parser N consumers）
│  │  ├─ :1520 calibration_bucket_summary（:1141，环 1a 五桶+Wilson CI）
│  │  │    → CALIBRATION_FEEDBACK_NOTE（:1550 注入 :1603，环 1b facts-only 禁令）
│  │  │    → INSIGHT_HINT（:1562 渲染 :1637，环 2 蒸馏钩子 0-2 条额度）
│  │  ├─ :1523 overdue_outcome_records（lesson_seeds 侧键）
│  │  ├─ :1614 feedback_dedup_verdict（:1933，同桶判重降级「刷新提示」）
│  │  └─ insight_quality_report（:2122/:2131）
│  │       ├─ insight_lifecycle_verdict（:2070，UPDATE/DELETE 生命周期门）
│  │       └─ insight_quality_verdict（:2031，hook-miss/bad-ref/retire-restatement 三判据 first-miss）
│  └─ :668 promotion_gate_summary_line（:2491，gate 桥三态摘要——退出码零改动）
│       └─ :2506 promotion_gate_assessment（:2330，X/N/Y/M 四轴）[GATE_SCOPE_NOTE :2305 只算不启用]
├─ :1810 run_propose（:1204，七卡确定性引擎，零 LLM 零网络）
│  └─ :1254 render_card（:990，卡呈现——轮 16 surface/rollback 两 bullet 后五列卡）
└─ :1830 run_verify_bounded（:1684，--verify-bounded 四态判定）
   └─ :1705 parse_bounded_answer（:1468，{answer,p} 三态兜底）
```

---

## §三 锚守卫三层演进（v1 四态 → v2 五态+hint → semantic scope 键修复）

1. **v1（iterate 轮 13 施工/handoff 轮 147-续；宿主死亡后由轮 15 代收提交 `ce52d11d06` 入库）**：`scripts/anchor_guard.py` 248 行纯 stdlib——显式 `file:line` 锚解析（ASCII 字符集防 CJK 粘连）+唯一 basename 确定性解析+存在/界内验证+PATCHES.md external skip+fail-soft 默认 exit 0（`--strict` exit 1 硬门禁化留业主）+`--fix` 只诊断拒写；**四态 explicit/hit/drifted/lost**+KNOWN_BAD 冻结 2（handoff :2922 `prompts.py:113` 全树无此文件+:2936 `iterate-round-2.md` 简写名——append-only 区存量债冻结不修）。首跑基线 explicit=84/hit=82/drifted=0/lost=2/external=0/bare=408（handoff 轮 147 在册）。
2. **v2（iterate 轮 16/handoff 轮 158，`95ff7b4abd`）**：**第五态 `semantic`**——锚带 hint 且 (src,target)∈SEMANTIC_SCOPE 时目标行窗口纯 stdlib 子串检查，任一 hint 符号不在场→semantic（v1 记 hit 的界内语义漂移缺口补上）；**hint 括注语法**（ASCII `()` 可选组，逗号分隔多符号 AND 语义，全角（）永不匹配）+**SEMANTIC_SCOPE 分批白名单**（首批仅 (docs/ops-local-refresh.md, scripts/monthly_review.py) 一对）+`--strict` 未动（semantic 不并入，负向钉）；tests 5→9 用例+docs 高价值子集 hint 迁移 9 锚。读数 93/91/0/2/0/467（轮 16 报告 §六）。
3. **semantic scope 键修复（iterate 轮 17，`33c1e875e6`/`7e3a6bbc7b`）**：pre-fix 键比对用锚的书写拼法（简写 `monthly_review.py` 与 scope 键 `scripts/monthly_review.py` 必然失配→hint 分支静默跳过=**修复前 semantic 恒 0 系假阴性区**，5 处简写 hint 锚属装饰性）；修复键改用 resolve 后路径——简写 hint 从装饰性升真验证，不改命中集。**实效判据=轮 18 报告 §二 决定性实验复现转录**：五假锚（简写错误 hint，行号 289/828/1128/1550/2054）HEAD `verify_anchor` 判 semantic ×5 vs pre-fix 规则（按 `7e3a6bbc7b:215` 比对行逐字内联重实现）判 hit ×5=**翻转 ×5 复现**+P6（简写正确 hint 双版皆 hit，非一刀切）/P7（全名错误 hint 双版皆 semantic，全名路径不变）双对照。**live 仓 semantic=0=修复后预期真阴性**（在册 12 hint 锚符号全在窗口内）——「计数应从 0 变正」系与 v2 机制不符的主题句，轮 18 辨明段已纠偏，不得硬造变正叙事。
4. **判据口径（贯穿三层）**：drifted=0/lost=2/semantic=0 三值恒定=通过判据；explicit/hit/bare 随 state 新增 :N 提及自然增长（非恒定判据，轮 16 报告辨明在册）。**迁移前基线（本会话实跑）：100/98/0/2/0/503 rc=0。**

---

## §四 ①-60 引用锚在册图谱（backlog 实读）

**物理分布两区**（本会话实测定位）：①-⑥ 位于「名词指认资料」节 blockquote（:702/:706/:709/:713/:721/:726，Jev 指认语义域）；⑦-㊿+51-60 位于文件前部延伸索引长区（:58 起，frontier-citation-anchors 续编至 :607），编号续接记法 :467 在册（「51/52/53…阿拉伯数字直书」）。**全部仅引用零装包零接入**（逐条附 license/星级/停更态一手复核）。

**按用途族分组（导航视图）**：

| 族 | 代表锚（编号） | 语义轴 |
|----|------|------|
| **RLCD 谱系/校准训练法** | ④ lm-evaluation-harness 枚举打分先例、⑤ RouteLLM 阈值校准边界（n=1 禁拟合）、⑬-⑰ 校准 arXiv 群、⑲ ANYTIME、⑳ LIMBO、54 代际兼容（provider 池变更须复测）、55 DINCO（suggestibility 两纪律） | 三环飞轮+月度小样本记录性校准的文献正源与边界 |
| **反泄漏同构** | ㊺ ReJev（污染 headline 公开作废≡config_committed 同族）、⑩ S1CogBench（格式合规≠语义合规）、⑨ 张力对（并列不偏引）、59 CatchBench（三信息态≡config_committed/ledger append-only/state 三态同构） | 第三方反泄漏/诚实呈报纪律样本 |
| **去重语义/防配套混引** | ㉜ hermes-patches 五列卡范式、㊻-㊽ 定夺框架三件（已入册去重）、56+57 自演化综述两篇**分立**（防配套混引；repo 许可分层辨明） | 登记纪律：同文不重登、异轴不合并、license=null 不认 |
| **补丁集治理/工程同构** | ㊸ drift（归一化指纹——anchor-guard-v2 upstream 注记）、㊹ K8s release-note（NONE/action required 词面）、㉞ Argo 三态 verdict+㊷ ArgoCD（同 org 异轴不重登）、㊱ ACE/㊲ ReasoningBank（失败侧同权）、58 TRAIL（分类学词汇表） | 卡面/守卫/门桥的工程同构正源 |

**在册缺口（如实）**：d-check/doc-drift 供证 slug 待业主补供（轮 15 报告 §五 缺口行）；轮 18 报告 rejected 九项未随文枚举留缺口。

> **61-68 指针（避免落地即过时）**：本轮同步批次另有条目拟新增延伸索引 61-68——**本报告落盘时点尚未入册**（本会话 `grep -E '^6[1-8]\.' state/backlog.md` 零命中实录），内容与落点以该条目入册为准，本图谱不预写。

---

## §五 自动演化速率统计（逐数以审计实锚复核）

1. **门禁**：有在册门禁记录的轮次 **17/17 全绿**（轮 1-18 中除轮 4——无载体无记载无从计证，不虚计；「18/18」口径不可全证如实注记）。各轮门禁面=ruff 全仓净+相关套件绿+（轮 13 起）anchor_guard rc=0+--status ok_committed；--doctor 恒 8/9 唯一红 7/9 site-repo drift=billing 冻结签名（已知预期态）。
2. **复核**：在册复核意见=轮 2/5/7 各 3 low+轮 15 findings×4（1 high+3 low）+轮 5 报告承载存量锚债 6 low，**全部清偿闭环**（roundN-lows 机制+轮 157-续 勘误批）；轮 15 例行复核=零意见首零（轮 16 报告 §一在册）。
3. **中断自动恢复计数（7 次在册）**：载体补写 5（轮 3/5/10/12/16——发布失败=文件缺失/零 git 历史→后续会话按已提交记录补写，非静默丢失）+宿主死亡代收 1（轮 13：dwfrun-421b0517 errored=Model creation failed→轮 15 代收两批）+closeout 缺失补记 1（轮 17：三证补录于 handoff 轮 159）。**恢复机制本身即 append-only 账本+补写先例的制度产物**。
4. **提交总量**：交办所引「153 提交总量」**未能在仓内锚定**——`grep -rn "153 提交|共 153|总量 153" state/ reports/ docs/` 零命中；六个 git rev-list 口径实测（`95a841a9e3..HEAD`=47、`2569489bed^..HEAD`=101、`db10a085a1^..HEAD`=85、`a08a8a75a8^..HEAD`=114、`f51e759eb7^..HEAD`=41、--since=2026-11-11=116）均不吻合。**可复核口径**：handoff iterate 区段（:2932-2989）出现且经 `git rev-parse` 验证为真实提交的哈希 **56 个**（含少量晚间通道/环境轮提交混入）；14 份审计报告哈希并集同量级。如实注记不硬凑。
5. **措辞纪律范本**：交办提示可引 projectmem「预警候选≠预警有效」范本（条件=引用锚条目同轮先行入册则作内部互引）——**全仓 grep（除 archive）零命中，锚条目未入册**，按条件 else 分支不引用不虚构；本节统计措辞自持同一纪律（计数只报在册可证值，缺口显式标注）。

---

## §六 验证清单（本会话实跑）与边界

- 动工前 `uv run python scripts/ops_local_refresh.py --status` → **ok_committed**（date=2026-11-13、95a841a9e3、pushed=true——晚间通道未在运行）。
- 目标文件预检：`ls reports/design/2026-11-16-iterate-panorama.md` → No such file（真增量）。
- 素材实读：handoff :2911-:2989 逐行（python，双序列轮号映射）；14 份 iterate-round 报告头部/复核行/哈希提取；设计报告 300 行全文；轮 15/16/18 报告全文；backlog ①-60 定位（①-⑥ :702-:726+⑦-60 延伸索引区）。
- 代码面实测：13 函数+3 常量 grep 现值（与交办行号逐值一致）；13 个 def 调用点逐一验证（§二 表）；11 符号 `git log -S` 引入提交（render_card 归属差异如实注记）。
- **迁移前门禁基线冻结**：`uv run python scripts/anchor_guard.py` → 100/98/0/2/0/503 rc=0（本报告头部所记）。
- `uv run ruff check`（全仓）→ All checks passed（纯 docs 条目，动 code 门禁不触发如实未跑——B.1 纯 docs 先例同判）。
- `git status -sb` → `## main...origin/main` 零偏差（轮 18 收尾批 push 已完成，与 current.md 顶部条计划一致——本会话实测）。
- 61-68 与 projectmem：grep 零命中实录（§四指针+§五.5）。
- **边界**：单文件新建 docs(reports) lane；数据源全只读（handoff/current/backlog/审计报告/代码零触碰）；0 ledger 写/0 frozen/0 OOS/研究面零改动；零新依赖零装包；本报告自身不在守卫扫描面（reports/design 非 DEFAULT_SOURCES），落盘后 guard 读数以当期命令输出为准（bare 时点值口径沿轮 15 §九/轮 16 辨明先例）。
