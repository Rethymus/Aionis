# iterate 轮 16 交付报告（2026-11-14 收官；报告=补写实录）

**轮次辨明**：轮 16 四条目按交办序=例行核查双读数（routine-checks-review-zero，S）/backlog 延伸索引续编㊸-㊺（frontier-citation-anchors，S）/patch-card-surface-rollback（S）/anchor-guard-v2（M）。核对最新号=handoff 轮 157-续 条目（:2974-2977）顺延。三施工条目=轮 15 报告 §四「patch-unit-fields 暂不推广」与 §五/§七 待指名区的本轮 mission 指名落地。**报告缺位如实**：四批施工提交与 state 收尾（17e04f8207/131005ac7d/95ff7b4abd/8eb67715d6，push 353d791c0e..8eb67715d6）先行落定，本报告系主会话指名补写（发布失败根因=文件未创建，ls+git ls-files 双实测缺失）——补写不改变已提交事实。**边界**：本轮触面=scripts/anchor_guard.py+tests/test_anchor_guard.py+scripts/monthly_review.py+tests/test_monthly_review.py+tests/test_monthly_review_propose.py（mission 指名）+state/backlog.md+docs/ops-local-refresh.md（锚跟改+hint 迁移）+state/handoff.md+state/current.md+本报告；0 ledger 写/0 frozen config/0 OOS/研究管线（src/aionis、scripts/phase_*、runs/ledger.jsonl 语义）零改动；零新依赖零装包。

## 一、例行核查三件套双读数（本会话亲跑，动工前与收工终态逐项一致）

| 检查（精确命令） | 读数（动工前=收工终态） |
|---|---|
| `uv run python scripts/ops_local_refresh.py --status` | rc=0：date=2026-11-13，**ok_committed**，pushed=true，ci 双 paused(actions-disabled)，backup=ok |
| `uv run python scripts/ops_local_refresh.py --doctor` | **rc=1，8/9**，唯一红=7/9 site-repo drift 11.0 天（live=2026-11-02T11:32:33.889178+00:00 repo=2026-11-13T11:25:37.269376+00:00）=billing 冻结签名已知预期态；其余八层 PASS（marker/scheduler/hook/push credential/gh auth/api env/deadman[due 2026-11-16]/env-lock resolved=198） |
| `gh run list --limit 5` | rc=0：最新 run 42966387146 停 **2026-11-11T05:32:08Z**——零新 run=业主停用令持续生效 |
| `uv run python scripts/anchor_guard.py` | rc=0：**explicit=93/hit=91/drifted=0/lost=2**/external=0/bare-unverified=467（动工前读数，v2 上线前）；两 lost=handoff.md:2922 prompts.py:113+:2936 iterate-round-2.md（KNOWN_BAD 冻结恒定判据） |
| 四套件合跑 `uv run pytest -q tests/test_monthly_review.py tests/test_monthly_review_propose.py tests/test_monthly_review_watchdog.py tests/test_anchor_guard.py` | rc=0，**137**（进度点 72+65，与决策会话读数吻合） |
| `uv run ruff check` | rc=0：All checks passed! |
| `git status --short --branch`（双时点） | `## main...origin/main` 零未跟踪；动工前 HEAD=353d791c0e、收工终态 HEAD 不变（例行核查任务零触碰实证） |

**轮 15 复核零意见无残项（首零）**——如实记录不扩写。

## 二、frontier-citation-anchors（backlog 延伸索引㊸-㊺，36+/0 纯增）

三条纯引用锚全部 gh api 一手复核（+README 实读）后才入册，避让在册①-㊷ 全部；逐条许可/星级/停更态/不采边界照㊱-㊷ 格，docs 在前：

| 编号 | 锚 | 一手复核定数（本日实跑） | 落点/不采边界 |
|---|---|---|---|
| ㊸ | github.com/fiberplane/drift | MIT/159★（stars:159 精确搜索唯一命中）/pushed 2026-06-22 停更态沿㉗；archived=false；**实现语言 Zig 实测** | 供 anchor-guard-v2 三语义（归一化指纹防重排版误报/symbol 级锚收窄声明子树/指纹随 link 落盘）；**本体不装**——tree-sitter 解析面（README「parses with tree-sitter and hashes a normalized AST fingerprint」实测）+Zig 工具链（zig build）违 scripts/anchor_guard.py:11 纯 stdlib 红线（:11 原文本日实测命中） |
| ㊹ | K8s release-note 约定（docs 在前）+ github.com/kubernetes/release | Apache-2.0/505★/pushed 2026-11-13 活跃 | 供 patch-card-surface-rollback：release-note block 默认「NONE」+「action required」句式**三层一手坐实**（kubernetes/kubernetes PR 模板+kubernetes/release cmd/release-notes/README.md+community guide release-notes.md）；**bot 自动消费不采**（Go CLI+Prow 链不装不引）；**rollback 词面未一手坐实**（约定文档三层均无、repo 内仅 changelog_data_test.go 测试数据 1 处）——如实留缺口沿轮 15 报告 :48 缺口行先例 |
| ㊺ | github.com/Joe-rq/ReJev | MIT/22★/pushed 2026-10-22 活跃 | 第三方反泄漏纪律样本：README 原文实测「The −2.33pp figure this line used to cite is **void (corrected 2026-09-28)** — it was measured on a **contaminated split**」（clean holdout 更正读数 +0.63pp CI[−1.13, +2.37]+勘误指向 technical report §2.3）——发现 headline 数字受数据污染即公开作废+原行 void 标注不抹历史 ≡ config_committed 先于结果/禁 rerun-to-significance 同族+勘误追加制同向 |

**如实辨明**：交办理由写 drift「tree-sitter/Rust 工具链」——一手实测实现语言=Zig（zig build 安装面），Rust 实为其解析支持语言列表一员（TypeScript/Python/Rust/Go/Zig/Java），条目内已如实注记。**五项 medium/low 调研项不登记**（CLAIR_and_APO/RSI-Jev/sndr_core_engine/vegaml/invalidate）——留档待后续 mission 指名；d-check/doc-drift slug 缺口（轮 15 报告 :48）待业主补供不动。两落点条目名（anchor-guard-v2/patch-card-surface-rollback）登记时 backlog 在册未见（grep 零命中）——系交办给定名，条目内如实注记，本轮施工后已成真。

## 三、patch-card-surface-rollback（render_card 两 bullet+双钉）

1. **render_card 两 bullet**（scripts/monthly_review.py +6/0，proposal/prediction 与 research-gate 条件 bullet 之后、disposition 之前）：`- surface: NONE=零行为面（docs-only 如实写 NONE）｜行为面必写触达文件——K8s release-note 词面先例（backlog ㊹），与五列卡缺一不可互补` + `- rollback: docs-only=git revert 平凡；代码条目=revert 窗口+连带测试钉；action required=accept 分流即人工执行面（对接 disposition accept→tasks/active/，K8s 句式 case insensitive）`——三 K8s 词面全部在场；施工前锚值实测（def=:990/evidence=:995/proposal=:996/prediction=:997-1008/disposition=:1011-1013，与交办现值吻合；交办 :975-999 已漂以现值为锚）。
2. **渲染钉**（test_monthly_review.py）：两 bullet 恰 1 处+词面断言（NONE/docs-only/git revert/revert 窗口/action required/tasks/active/）+落位 disposition 前+`scan_proposal_keys(卡文本)=={"prop:demo"}` 零新键。
3. **负向钉**（test_monthly_review_propose.py）：backlog 含 K8s 词面行（无 `key: prop:`）→ `run_propose` n==0+「无提案」渲染+`scan_proposal_keys(词面文本)==set()`——PROPOSAL_KEY_RE :693 只对 `key: prop:` 行 findall，新 bullet 不触发 propose/reconcile/refresh（码内边界钉死）。
4. 套件 137→139；旧值零命中（surface/rollback 卡 bullet grep 实测全为无关词面）与负向钉施工前不存在均如实验证。

## 四、anchor-guard-v2（第五态+hint 语法+分批白名单）

1. **第五态 `semantic`**：`verify_anchor` 界内分支后 hint 验证——锚带 hint 且 (src,target)∈SEMANTIC_SCOPE 时，目标行区间 window（`lines[start-1:upper]` join）纯 stdlib 子串检查，任一 hint 符号不在场→STATUS_SEMANTIC（v1 记 hit）；summary 增 `semantic=` 字段；summary 括注句同步改写（v1 gaps 句中 in-bounds semantic drift 缺口已补）。
2. **hint 括注语法**：ANCHOR_RE 增可选 ASCII 圆括注组——`tool.py:123(render_card)`/`tool.py:1-9(def foo, return)`，逗号分隔多符号 **AND 语义**；全角（）胶合永不匹配（ledger 内 `path:N(` ASCII 模式 grep 零命中实测=零误捕）。
3. **SEMANTIC_SCOPE 分批白名单**：首批仅 `("docs/ops-local-refresh.md", "scripts/monthly_review.py")`；scope 外锚带 hint 解析后忽略=v1 行为（负向钉）；`_norm_src` 归一化 scope 键（仓内→相对 posix/仓外 fallback as_posix）。存量分批迁移原则：每批 (src, target) 对显式声明+仅迁括注语义已在册的锚+跑 semantic=0 确认；**不为迁而迁**。
4. **--strict 未动**：仍只看 drifted/lost，semantic 不并入（负向钉 test_strict_ignores_semantic_state）；硬门禁化与 semantic 是否并入 strict 留业主区。
5. **docstring 升级**：v1 两缺口段保留（bare :N 仍 open——COUNTED but not verified）+新增 v2 段（五态/语法/白名单/strict 不变+upstream 出处=fiberplane/drift ㊸ cite-only 纯 stdlib 重实现注记）。
6. **tests 5→9 用例**：semantic 三态钉（单锚 miss/span AND miss 双 semantic+双 hit）/scope 外忽略钉/语法钉（反引号内/多符号/全角不误捕/空格形/三分隔）/strict 不并入负向钉/live pin 扩 `semantic==0` 行。
7. **中途修复如实**：初版测试 :122 红——`run((str(src),),…)` 传绝对路径致 a.src 与 scope 键 ("ledger.md",…) 失配→`_norm_src` 归一化+测试相对调用，修复后 9 用例全绿。
8. **第五态真触发双向对照**（python -c 构造实测）：hint `nonexistent_symbol_xyz`→`semantic | exact, in bounds but hint(s) absent from lines 990-990`；hint `render_card`→`hit`——semantic=0 系真阴性非 scope 失配假阴性。
9. **docs 高价值子集 hint 迁移 9 锚**（二选一取「迁移」支，不为迁而迁）：:378 `(def reconcile_predictions, return)`/:733 `(render_card)`/:732 `(run_propose)`/:765 `(promotion_gate_assessment)`/:913/:953/:337 `(def parse_bounded_answer, return)`；:306/:357 **值修正** :1748→`1744(propose)`——实读 :1748 系 --propose argparse help 字串折行续行、:1744 才是 `parser.add_argument("--propose"` 块首。每处 hint 子串对工作树实值核验后才写。

## 五、锚跟改随批（内容定位审计，handoff 零触碰）

patch-card 施工（monthly_review.py +6 行）触发 docs/ops-local-refresh.md 锚平移：内容定位审计（HEAD blob 旧行内容==工作树新位内容逐一验证 **23 锚全 OK/0 mismatch** 后方写回）——17 处全名锚刷新（:1742→:1748/:1453→:1459/:1274→:1280/:1462-1485→:1468-1491/:1017-1091→:1023-1097/:1286→:1292/:1198→:1204×2/:2324→:2330/tests 972-1068→991-1087/:1800-1802→:1806-1808/:1094→:1100/:1927→:1933/:1772-1775→:1778-1781 等）+5 处简写锚（:1422-1445→:1428-1451/:1270-1283→:1276-1289/:1679→:1685/:1223→:1229/:2048→:2054，均 blob==wt 逐对验证）；:986-987/:997/:862-967/:895/:806/:990/:81-88 插入点前实测不动。偏移以 `git diff --numstat` 实测为准（bullet 各折 3 行=+6，非初估 +4）。handoff.md 旧条目锚**不刷**（轮 157-续 前向规则）；两 KNOWN_BAD lost 冻结锚状态不变。工具链如实：锚审计脚本经 Mimosa 三次拦截（heredoc 写脚本/写模式 open/动态路径构造）后改只读审计+Edit 工具写回，全程零绕过。

## 六、门禁终态（本会话实跑）

- `uv run python scripts/anchor_guard.py` → rc=0：**explicit=93/hit=91/drifted=0/lost=2/external=0/semantic=0/bare-unverified=467**（四值判据 v1 恒定+第五态真阴性；v2 后 summary 新增 semantic 字段）
- 四套件合跑 → rc=0，**143 全绿**（进度点 72+71；progression 137→139→143）；anchor_guard 独跑 9 用例 rc=0
- `uv run ruff check` → All checks passed（line-length=100 折行合规）
- `--status` 动工前/收工 ok_committed（晚间通道未在运行）
- git 终态：`## main...origin/main` 零偏差（push 后本地=origin=8eb67715d6）

## 七、待业主区（只列不动）

①billing 解锁（Actions 停用令恢复清单在 billing playbook）；②anchor_guard `--strict` 硬门禁化（**新增**：semantic 是否并入 strict 同批裁决）；③d-check/doc-drift slug 补供（轮 15 报告 :48 缺口行）；④L2 钥匙与门槛定标（gate/桥只呈现不启用）；⑤五项 medium/low 调研项（CLAIR_and_APO/RSI-Jev/sndr_core_engine/vegaml/invalidate）与 **SEMANTIC_SCOPE 后续批次**（handoff 内 (src,target) 对、docs→ops_local_refresh.py 对）待 mission 指名；⑥轮 14 报告 §七.5 日期命名约定/ZCode 模板确认（沿轮 15 §七 未变项）。

## 八、提交清单（四批+本报告，均 pull --rebase 后 push 一次成功）

| 批 | 哈希 | 类型 | 内容 | numstat |
|---|---|---|---|---|
| 1 | `17e04f8207` | feat(ops) | frontier-citation-anchors ㊸-㊺ | state/backlog.md 36+/0 |
| 2 | `131005ac7d` | feat(ops) | patch-card-surface-rollback | monthly_review.py 6+/0+tests 19+/0+24+/0 |
| 3 | `95ff7b4abd` | feat(ops) | anchor-guard-v2 | anchor_guard.py 78+/11-+tests 84+/0 |
| 4 | `8eb67715d6` | docs(state) | 锚跟改+hint 迁移+handoff 轮 158+current 顶部条 | docs 20+/20-+handoff 3+/0+current 4+/0 |
| 5 | 本报告 | docs(reports) | 本文件新建（补写） | 单文件新建 |

push 实录：`git pull --rebase`→"Current branch main is up to date."（rc=0）；`git push`→`353d791c0e..8eb67715d6 main -> main`（rc=0 一次成功）；终态 `## main...origin/main` 零偏差零未跟踪。

---

**bare :N 提及与锚值时效辨明（无编号辨明段）**：bare-unverified 数值随各轮 handoff/docs 新增 :N 提及自然增长（467=本报告提交前 HEAD 时点值），非恒定基线；有意义判据=explicit/hit/drifted/lost 四值（本轮恒 93/91/0/2）+v2 起新增 semantic（0=真阴性）。本报告自身新增裸 :N 提及属预期（沿轮 15 §九 勘误先例口径）。本报告位于 append-only 勘误追加制承载面——原文不回改，勘误走 §九 追加（沿轮 157-续 裁定）。
