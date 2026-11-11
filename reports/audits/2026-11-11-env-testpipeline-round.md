# 环境与测试流水线整备审计 — 轮 127 决策报告（2026-11-11）

四路证据源：测试流水线审计（全量，pytest --collect-only 实测 + gh run list/view 实测）、环境配置缺口（全量）、第 1/2 路前沿调研。本报告为决策记录与施工依据；证据原文见 ask 附件。本轮决策会话亲测复核的关键锚点见 §6。

---

## 0. 施工清单（按执行顺序，文档在前、代码在后）

| # | id | 内容 | 触碰面 | 量级 |
|---|----|----|--------|------|
| 1 | round127-audit-report | 本报告落盘 | reports/audits/2026-11-11-env-testpipeline-round.md | M |
| 2 | docs-drift-fixes | runbook 八层口径 + staleness 每日化 + 微信出处复核实测注 + reflexion 措辞 + .env.example key 名补全 | docs/ops-local-refresh.md、scripts/monthly_review.py:641-644、.env.example | S |
| 3 | state-reconciliation | handoff append-only 勘误表 + current.md 用例数修正 + backlog 前沿吸收条目 | state/handoff.md、state/current.md、state/backlog.md | S |
| 4 | workflow-hardening | node24 重钉 + uv --frozen + vintage 三修 + permissions 收敛 + dormant 补钉 + 注释证伪修正 | .github/workflows/*.yml（6 个文件） | M |
| 5 | test-guards | 新建 tests/test_workflow_yaml_hygiene.py + 跨午夜竞态修复 + 一次性验收永 skip 反转 | tests/test_workflow_yaml_hygiene.py（新建）、tests/test_ops_local_refresh.py、tests/test_ops_fastpath_triage.py | M |

提交规范：Conventional Commits 原子分批，一 item 一 commit：
1. `docs(audit): round-127 环境与测试流水线整备审计报告`
2. `docs(ops): runbook 八层/staleness 每日化勘误 + reflexion 措辞修正 + .env.example key 名补全`
3. `docs(state): round-127 对账勘误表 + current 用例数修正 + 前沿 backlog 吸收`
4. `ci(workflows): node24 重钉 + uv --frozen + vintage 钉点/换模修正 + permissions 收敛`
5. `test(guards): workflow YAML 卫生守卫 + doctor 跨午夜竞态修复 + triage 验收断言反转`

---

## 1. 上轮 5 条 low 复核意见处置表

| 上轮意见 | 处置 | 施工落点 |
|----------|------|----------|
| ① doctor 层数笔误（七层→八层） | **修**。:157/:228/:340 三处亲测仍为 seven-layer/七层，与代码 collect_layers 八层（scripts/ops_local_refresh.py:1166-1179）及文档自身 :282（第 8 层描述）矛盾 | item 2 |
| ② monthly_review.py reflexion『archived』措辞 | **修**。:644『itself is archived research scripts』亲测在案；gh api 实测 archived:false（pushed_at 2025-01-14）→ 改『stale/unmaintained-since-2025-01-but-not-archived』 | item 2 |
| ③ 微信文章出处张力 | **按本轮实测处置（不替换出处）**。上轮前提『正文不可读』今日不成立：curl 直取 HTTP 200/5.05MB、js_content×18、fox_fetch 得全文含四机制。处置 = runbook 出处行加『2026-11-11 复核实测可读』注记，引用张力随之消解 | item 2 |
| ④ state/current.md 用例数修正 | **修**。:4『53 用例』→ 55=17+23+15（collect-only 实测）；总数口径并列 2430 全仓实测 | item 3 |
| ⑤ handoff 老轮次不重写 | **遵守**。不回改历史；轮 127 新记录写对账勘误表（见 §2） | item 3 |

## 2. 审计对账勘误表（写入 handoff 轮 127 记录；老轮次原文不动）

以 `uv run pytest --collect-only -q` 逐文件实测为准：

- fastpath 17 ✓（自报正确；提交信息 0528ccec65『18 hermetic cases』实 17——提交历史不回改，此处存档勘误）
- watchdog **23**（自报 20，+3）
- deadman **15**（自报 16，−1）
- monthly **27**（自报 30，−3）
- lane **40**（自报 38，+2）；triage+lane = **57**（自报 56）
- 新 3 套件合计 **55**（current.md:4 记 53）
- 总数全对：round-126 面 **95**（17+23+15+40）✓；聚合 **142**（95+27+20）✓；全仓 **2430** 用例（174 个 tests/ 文件，pytest 9.1.1 无汇总尾行，逐行求和实测）

## 3. 环境缺口表（含待业主区）

### 3a. 本轮施工修复（fixableLocally=true 全修，框架 #2）

| 缺口 | 处置 | item |
|------|------|------|
| docs/ops-local-refresh.md:157/228/340 七层口径 | 改八层；:279 为 2026-11-06 历史叙事保留并标注时点 | 2 |
| monthly_review.py:641-644 archived 失实 | 改准确表述（见 §1②） | 2 |
| docs/ops-local-refresh.md:229 staleness 周一档过时 | 改『每日 02:37 UTC（离整点）』+ 解锁日滞留红 rerun 再判 | 2 |
| .env.example 仅 2 个 key 名（亲测） | 补 config.py:57-89 消费的其余 8 个 key 名，**留空占位、不写任何值** | 2 |
| handoff/current 用例数 6 处笔误 | 勘误表（append-only）+ current 修正 | 3 |
| vintage-probe.yml:70 vars.LLM_MODEL 换模机制失效（gh secret list 在列、gh variable list 为空——ask 实测） | :70 改读 secrets.LLM_MODEL + :24-26 注释实述 | 4 |
| refresh-terminal-data.yml:31 冗余 actions:write + :364 陈旧注释 | 收敛 contents:write + 注释修正 | 4 |
| staleness-check.yml:29『锁中不运行』被证伪 | 改实测事实：锁中 schedule 仍触发、零步秒红（2026-11-09 run 42596200442 steps=[]） | 4 |
| vintage-probe.yml:83 upload-artifact@v7 TAG 未钉（活跃工作流） | 钉 40 位 SHA + 版本注释 | 4 |
| vintage-probe.yml:41 cron 整点 06:00 | 改 '23 6 3 * *' 离整点 | 4 |
| deploy-pages.yml:57/71 TAG 未钉（dormant） | **补钉不删文件**（保守：owner sign-off 删除案未决，不自行删） | 4 |
| tests/test_ops_local_refresh.py:461 跨午夜竞态 | fixture 与被测层共用注入 date | 5 |
| tests/test_ops_fastpath_triage.py:214-221 永久 skip | 反转为肯定断言（note 不存在=修复态保持；marker 缺失视为修复态通过） | 5 |
| 6 个工作流无 YAML 卫生测试钉 | 新建 tests/test_workflow_yaml_hygiene.py（见 §5） | 5 |

注：.env.example 不在可触碰面枚举内，但框架 #2『fixableLocally=true 全修』为必须遵守项，故纳入；只补 key 名、绝不写入凭据值。

### 3b. 待业主区（不可本地施工）

1. **GitHub billing 解锁 #2**——doctor 第 7 层 site-repo drift 8.0 天（live 2026-11-02 vs repo 2026-11-10，ask 实测）即冻结签名；解锁后 publish-site 自动追平，doctor 复跑核验转 PASS。
2. **freeze 真推许可**（冻结通道）。
3. **-wj 账本孤儿 2 行裁决**。
4. AGENTS.md DoD 是否显式豁免『环境观察型条件 skip（主逻辑另有无条件覆盖）』——AGENTS.md 非本轮可触碰面；既有 10 处 skip 为既定调和形态（ci.yml:10-11 round-59 先例），本轮新增 2 处由 item 5 消除后字面张力缩小。

## 4. 零报错差距（2026-11-11 实测基线 → 可达定义）

**现状**：billing-lock 面红 = Tests 14 连红（11-05 15:54 起）+ Publish site 4 连红 + Staleness 2 红（11-05 17:24 + 11-09 09:48 schedule），三组均零步签名（gh run view 4287696971249 / 42596200442：jobs[].steps=[]）——billing-lock 不算可施工缺陷（框架 #3）。real-defect 面无新增红（vintage 三连红已定性为测量仪布线缺陷、11-06 修复落地，待 2026-12-03 06:00 UTC 首跑复验）。doc-drift/flaky-risk 面全部由 item 2/4/5 消除。

**★新增 P0（前沿第 2 路）**：Node 20 已从 runner 移除（2026-09），本地 5 个 SHA 钉点声明 node20（setup-uv v1 162b8acf@ci:56 与 v3 caf0cab@refresh:53、pnpm/action-setup b906aff@ci:73、setup-node 49933ea@ci:78、actions/cache 0057852@refresh:55/84/105、deploy-pages@v4）——是步骤直接启动失败、非透明回退，6/7 工作流受影响（仅 staleness-check 幸免）。**不修则解锁后首跑必红**，属『解锁后 Actions 首跑绿』目标的一部分 → item 4 一次性重钉为已验证 node24 版本（重钉前逐个 `curl -sfL https://raw.githubusercontent.com/OWNER/REPO/TAG/action.yml | grep using:` 验证）。诚实声明：node20 硬失败行为依据前沿文档而非本仓库实跑记录（计费锁无法实测首跑）。

**零报错可达定义**（框架 #4）：本地 `uv run pytest -q` / `uv run ruff check` / YAML 校验零失败 + 解锁后首跑由配置正确性保证为绿。PyYAML 先修条件已满足（亲测 `uv run python -I -c "import yaml"` → 6.0.3；pyproject.toml:59 已含 pyyaml>=6.0）→ **走审计建议的 pytest 守卫路线**（tests/test_workflow_yaml_hygiene.py），**不建 scripts/check_ci_yaml.py 第二入口**（审计评估『守卫优于独立脚本』；ADR-006 无一次性仪式）。

**解锁日首验清单更新**（handoff:2911 底稿 + runbook :289-301）：
- (a) 『首个周一误红』→ staleness 已每日化且锁中已产生零步红（11-09 实测）；解锁日滞留红 = 11-05/11-09 存量 + 当日 02:37 一条，rerun 一次再判（playbook 顺序不变）。
- (b) vintage 12-03 首跑复验（cron 已改离整点则时刻随之）、refresh 双缓存 GC 全清、Pages 非零分钟 billing usage、ops_freeze_deploy.py --check-recovery 三态——均在案。
- (c) 钥匙区三条不变（§3b）。
- 新增：解锁首跑后核对 node24 重钉全绿；YAML 卫生守卫在 CI 与本地同绿。

## 5. 测试面定性（skip / flaky / 守卫）

- **skip 盘点**：12 处 skip 语义（11 调用点 + test_macro_headline.py:13 为反向声明注释）。既有 10 处 = 环境观察型 + 平台 skipif，守卫背后即主逻辑断言，属 ci.yml:10-11 round-59『explicit skip-with-reason guards』既定调和形态——**不动**，AGENTS.md 字面张力记入待业主区。新增 2 处（fastpath:217/221）由 item 5 消除。
- **flaky 盘点**：打桩纪律良好（deadman 纯时钟注入、平台分支 monkeypatch 钉 IS_WINDOWS、freeze_deploy 双平台参数化、全仓零 freezegun）。未打桩候选 2 个：doctor fixture 跨午夜竞态（→ item 5 修）；test_ops_freeze_deploy.py:190 平台自适应断言——审计定性『确定性非 flaky』，**不动**。
- **YAML 卫生守卫**（item 5 新建）：PyYAML safe_load 全 7 工作流；断言 uses 全 40 位 SHA（deploy-pages 补钉后无豁免）；runs-on 全 ubuntu-24.04；permissions 显式；cron 与测试钉一致（staleness '37 2 * * *' 呼应 test_ops_deadman.py:178，vintage 离整点）。随 `uv run pytest` 门禁自动执行。

## 6. 前沿采纳双清单

### 6a. 采纳 → 本轮施工（high + S/M）

| 来源 | 落点 |
|------|------|
| 第 2 路 P0：node20 重钉 | item 4 |
| 第 2 路：uv `--frozen`/`--locked`（ci.yml:62/66 亲测裸命令） | item 4（e3/vintage 同改） |
| 第 2 路：zizmor 所指 3 处 unpinned-uses（与流水线审计实测一致：vintage:83、deploy-pages:57/71） | item 4 |
| 审计建议：tests/test_workflow_yaml_hygiene.py（PyYAML 可用性已亲测） | item 5 |

### 6b. 采纳 → state/backlog.md（L 或存疑；逐条含 URL，此为吸收落地）

1. 哈希链账本 + 一次性 holdout 回执 + 门合取（https://arxiv.org/abs/2611.06607；MIT 参考实现 github.com/henryzhangpku/autonomous-quant-researcher）——**触红线**：ledger 语义零改动、receipt 属 scripts/phase_*。
2. 动量倾斜归因预注册（https://doi.org/10.1016/j.jfds.2026.100207；SSRN 7010050）——下一 phase 预注册，owner 研究决策。
3. 知识截止/结果感知新门（https://www.ravenpack.com/blog/insights-and-limitations-in-stock-price-prediction-using-llms；arXiv:2401.03737）——需改 docs/data-intake-rubric.md，非本轮可触碰面。
4. purged-CV 第二实现一致性测试（https://github.com/eslazarev/purged-cross-validation，MIT 64★）——**存疑**：PyPI 可安装性未验证；CPCV/PBO 仅诊断、不作主分割器。
5. time-machine 时间桩 conftest（https://adamj.eu/tech/2026/08/03/python-time-machine-o1-freezegun-on；MIT v3.6.0）——8 个 src 模块墙钟语义分批。
6. pytest-randomly（https://github.com/pytest-dev/pytest-randomly，MIT v5.1.0）——2430 用例随机序体检 + 豁免治理。
7. pytest-xdist -n auto --dist loadfile + faulthandler_timeout=300（https://docs.pytest.org/en/stable/explanation/flaky.html，MIT v3.8.0）——需 H6 位一致豁免组设计。
8. 抽取错误分类学人工审计（https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6496861）——人工标注成本 L；审计集与 prompt 调整隔离。
9. 组合级 FDR 读数（https://people.duke.edu/~charvey/Research/Published_Papers/P143_False_and_missed.pdf）——docs/RESULTS.md 报告层，不回溯改 α。
10. DSR 试验计数通缩 + minTRL（https://arxiv.org/html/2512.12924v1）——N 随 config 冻结，仅预注册附录。
11. 时序共形区间（https://arxiv.org/html/2507.05470v1）——稳健性视角，不变更主检验。
12. actionlint + zizmor 常驻静态校验（https://github.com/rhysd/actionlint；https://github.com/zizmorcore/zizmor，均 MIT）——二进制本轮未装未跑；如集成 doctor 需条件存在守卫，保守后置。
13. act 本地 dry-run（https://github.com/nektos/act，MIT）——解锁前预检工具，不入 repo 依赖。

### 6c. 不采纳（进报告存档）

GT-Score 适应度目标（arXiv:2602.00080，优化目标=数据窥探新轴）；CPCV 多路径挑最优汇报（即被测过拟合）；LLM 自主回路跑量找显著（mass multiple testing，违 rerun-to-significance 禁令）；Dolt/PIT 存储换引擎（H6 风险徒增）；PIT 工程博客类（7-gate 已覆盖）；微观结构 walk-forward 照搬（领域错配）；time-varying IC 状态重分割；**pytest-rerunfailures / pytest-repeat（MPL-2.0，违 MIT/Apache/BSD 白名单 + 红洗绿语义）**；ubuntu-latest 翻案（26.04 迁移已钉定在案）；自托管 runner 绕计费锁（平台问题平台解）；flaky-bot 类自动重跑（假零红）；Dependabot/Renovate 自动改工作流（手工 SHA 注释钉法已足）。

## 7. 亲测记录与诚实声明

本轮决策会话执行的命令与结果：
- `uv run python -I -c "import yaml; print(yaml.__version__)"` → **pyyaml 6.0.3**；`grep yaml pyproject.toml` → :59 `pyyaml>=6.0`（base 依赖，无新依赖）；:23 `purgedcv>=0.1.2`、:38-39 robustness extra。
- `grep seven-layer|七层 docs/ops-local-refresh.md` → **:157/:228/:340** 在案。
- `grep cron tests/test_ops_deadman.py` → :174-178 钉 `37 2 * * *`。
- `grep LLM_MODEL .github/workflows/vintage-probe.yml` → :24-26 注释、**:70 `vars.LLM_MODEL || 'glm-4.7-flash'`**。
- `ls tests/test_workflow_yaml_hygiene.py` → **不存在**（守卫缺口实证）。
- `cat .env.example` → 仅 OPENAI_API_KEY / FRED_API_KEY（+OPENAI_MODEL 注释行）。
- `grep ci.yml` → :54 checkout SHA ✓、**:56 setup-uv@162b8acf（v1）**、**:62 裸 `uv sync --all-extras`**、**:66 裸 `uv run pytest -q`**、:73 pnpm@b906aff、:78 setup-node@49933ea。
- `grep refresh-terminal-data.yml` → :53 setup-uv@caf0cab、:55/:84/:105 cache@0057852、:364 陈旧注释。
- `grep archived scripts/monthly_review.py` → :644『archived research scripts』。
- `sed` 实测：test_ops_local_refresh.py:461 `datetime.now()` ✓；test_ops_fastpath_triage.py:214-221 两处条件 skip ✓；staleness-check.yml:29『锁中不运行』✓；vintage-probe.yml:41-42 cron `'0 6 3 * *'` ✓、:56 setup-uv v1 SHA ✓、**:83 `actions/upload-artifact@v7` TAG ✓**。

**未执行/未验证（不冒充）**：全量 pytest 运行（任务约束，仅 collect 口径承审计实测）；actionlint / zizmor / act 未安装未运行；gh api / gh run list / gh secret list 复核（承 ask 当日实测）；purged-cross-validation 的 PyPI 可安装性；node24 目标版本的 curl 验证（属 item 4 施工期动作）。

## 8. 红线与跳过原则（施工者必读）

1. `src/aionis/**` 与 `scripts/phase_*` 零改动；`runs/ledger.jsonl` 语义零改动（哈希链/回执类提案一律 backlog）。
2. 许可证仅 MIT/Apache/BSD：本轮**零新增依赖**（PyYAML 已在 base deps）。
3. 无后台长驻进程；无一次性仪式脚本。
4. handoff 老轮次与提交历史一律不回改——勘误只 append。
5. 行号漂移时以实测 grep/sed 重新锚定，不按本报告行号盲改。
6. token 经济：不新增任何 LLM 调用面；.env.example 只补 key 名不写值。
7. deploy-pages.yml dormant **补钉不删**；refresh 的 `uv cache prune --ci` 步骤为可选（依重钉后 setup-uv 版本能力，不确定则不加）。

---

## 漂移注记（append-only，2026-11-11 gen2 复核意见 2/3）

:46 与 :116（§6b 条目 6）的 **2430 用例 / 174 个 tests/ 文件**为**轮 127 决策时点基线**（提交 `15cfcba7f4`），原句一律不回改（§8 第 4 条 append-only 原则）。截至 `390d7d7002` 实测：**2482 / 176（+52/+2）**，构成：propose +20（`tests/test_monthly_review_propose.py` 新套件，gen2 条目 3）+ hygiene +23（`tests/test_workflow_yaml_hygiene.py` 新套件，本报告 item 5 落地）+ lane 40→43（`tests/test_ops_local_refresh.py`）+ watchdog 23→25（`tests/test_monthly_review_watchdog.py`）+ fastpath 17→21（`tests/test_ops_fastpath_triage.py`）；+2 文件即上述两个新套件文件。核验口径同 §2（`uv run pytest --collect-only -q tests/` 逐文件求和，pytest 9.1.1 无汇总尾行）；2026-11-11 施工会话复测逐项吻合——总数 **2482**、文件 **176**、五套件 **20/23/43/25/21**、构成和 **52**——且 `git diff 390d7d7002..HEAD -- tests/` 为空（其后仅 lane 数据提交 `8605bd45b3`，计数不受影响）。
