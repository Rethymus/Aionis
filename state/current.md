# state/current.md — read first each session

- **active (2026-08-06):** fintech 数据终端**已上线** + special 另类数据持续扩展：TACO（真实 VIX）+ EDGAR 13D 聪明钱 + **选股确信度（Aionis 独有模型元信号，截面分散度）** + Reddit（待激活，政策阻塞）。
  9 页：Overview/选股决策/证据墙/**选股确信度**/聪明钱/TACO/Reddit/Power Floor/反泄漏。**Form 4 ingest + XML orchestrator 都就绪验证**（ingest sonnet agent + orchestrator opus fallback，我跑 20/20 绿；full repo ruff clean）。可见模块待业主 SEC 邮箱 + bounded fetch 授权。详见 `state/handoff.md` § (b)(c)(d)(e)(f)(g)。
  **待业主**：审 /conviction + Form 4 agent 回报后审 + 13D 刷新 + Quarto/旧站去留。
- **version:** 0.1.0 (pyproject)
- **milestone:** **CONFIRMATORY CLIMAX ACHIEVED (2026-08-05)** — first confirmatory OOS run sediments
  ledger row #49 (`confirmatory:first`, phase=track_c, sig `e14b9d44...` → frozen #48). Combined rank-IC
  = **−0.0088** (null, p_hac=0.484, n=71); J-T look-1 (n=60, RCI 99.44%) = **NOT_EQUIVALENT** (RCI
  [−0.051,+0.027] wider than ±0.010 SESOI = underpowered look-1, NOT an effect signal). H6 double-run
  bit-identical PASS on real data. draft v0.1 → **v1.0-draft** (§5 confirmatory filled). Prior: B/C/D/E1
  ledger results + h={10,42} sensitivity exist; E3 Slices 1–7 + AUD-06 contracts frozen; 2026-07-31 audit
  reclassifies historical evidence as **purged cross-fitted/CV-proxy**, not chronological/live OOS.
- **research verdict:** no B/C/D/E1 treatment arm shows reliable positive incremental rank-IC under
  the frozen nine-column baseline. Phase B has no recorded paired differential CI; Phase C is not
  strictly equivalent within post-hoc ±0.015; none of the four headline arms uses LLM features.
- **active:** `TASK-AUD-00` remediation program. AUD-01 and AUD-03 are COMPLETE after independent Verifier PASS
  and Reviewer APPROVE. AUD-04 is also COMPLETE after repair re-Verifier PASS and Reviewer APPROVE. AUD-02
  documentation reconciliation and AUD-05A are COMPLETE after independent Verifier PASS and Reviewer APPROVE.
  AUD-05B is COMPLETE after re-Verifier PASS and authorized re-Reviewer APPROVE. AUD-05C disposition
  is recorded. C1, C2 and C3 are COMPLETE after owner authorization, Engineer evidence, independent
  Verifier PASS and Reviewer APPROVE. C5 remains owner-gated. The dashboard view extraction and
  owner-authorized C4 standalone cleanup passed review and are committed in `7dede9b`.
- **E3:** engineering may continue, but headline is **NO-GO**. No scheduler, real E2E, or forward result
  exists; shadow/headline must not observe outcome-bearing metrics before AUD-07 and owner approval.
- **agents:** supervisor+worker protocol codified in `docs/orchestration-protocol.md` (ADR-012): opus
  Orchestrator + low-freq opus Supervisor (gates only) + sonnet `executor`/haiku workers (serialized,
  ≤2 concurrent) + independent `verifier`/`code-reviewer`/`qa-tester` lanes; dispatch via
  `scripts/orchestrate_dispatch.py`. One writer per file boundary still binds. Multi-agent inference
  is not part of the stock-selection signal.
- **known issues:** protected historical claims may retain superseded wording; non-chronological historical CV;
  blocked market-source fallbacks and sub-2s fetch paths; Phase B A1 lock stranding; current SIC snapshot;
  ADR-010 Amendment 2026-08-01 APPLIED (Jennison-Turnbull group-sequential equivalence; RCI 99.44/97.64/95.00%; strict-containment; double-opus AUD-07B correction; prereg §7 amended in lockstep) — **E3 statistical-gate HOLD LIFTED**. E3 still gated by AUD-06 live-input readiness + owner GO (no scheduler/real-E2E/forward result yet).
- **last verification (2026-08-01):** Wave-A complete. The full hermetic pytest suite passes (zero skips;
  only the existing forward-score warnings), `uv run --offline ruff check` is clean, `git diff --check` is
  clean, and the frozen prereg/ADR/config/ledger/results/data/forward diff is empty. C1/C2/C3 and
  RD-04/05/06/07/09/10/12 each have independent Verifier PASS + Reviewer APPROVE; committed as `6085e92`
  (Group A), `2653907` (Group B), `5f884a3` (Group C). No frozen config, preregistration, ledger/result
  artifact, or forward outcome changed; no real network/LLM/research/forward script ran.
- **planning (2026-08-01):** a planning-only low-reasoning development program was frozen as
  `reports/milestone/2026-08-01-low-reasoning-development-roadmap.md`, the Wave-A launch brief,
  `TASK-RD-00..17` and strong-only `TASK-AUD-07B`. **Wave-A has executed under the owner-provided Goal
  prompt: C1/C2/C3 + RD-04/05/06/07/09/10/12 are all COMPLETE** (independent Verifier PASS + Reviewer
  APPROVE each; RD-07 byte-stability, RD-10 window/std, and RD-12 manifest-oracle findings were fixed
  and re-gated). RD-01/02/03/08/11/13..17 remain PLANNED for future waves. No real
  network/LLM/data/trial ran; no frozen surface, ledger, result, or E3 outcome changed.
- **evidence:** `reports/audits/2026-07-31-quant-llm-research-audit.md` and `tasks/active/TASK-AUD-00-remediation-coordination.md`.
- **strategic review (2026-08-02):** deep-dive on "是否跑偏 + 七主题低成本覆盖" → `reports/2026-08-02-strategic-review-coverage-and-alignment.md`. Verdict: direction sound; two失调 (目标叙事双轨未裁断; 治理复杂度>研究产出). Produced 6 design artifacts under `reports/design/` (Track A/B slice plans, slice review, qlib-fork-vs-library POC, wheel-mount design pack, reuse-catalog v2) + `src/aionis/eval/ff5_residual.py` (挂接③ FF5 residual + Amihud, 18 tests green, ruff clean; exploratory utility, **not wired to pipeline, writes no ledger**). **Owner decision (2026-08-02):** Track B (seven-theme platform) adopted + new prereg/frozen config → `decisions/ADR-011-track-b-seven-theme-platform.md` + `docs/track-b-preregistration.md` (PROPOSED). First slice 挂接③ (FF5 residual) done. **Pending:** owner freezes Track B config sha256 before any real-data result. B/C/D/E1 frozen surfaces untouched; no real network/LLM/trial ran.
- **Wave-B (2026-08-01):** owner `/goal` authorized the priority offline RD program ("启用更多 agents 根据优先
  等级…各自推进"). 8 sonnet-tier tasks COMPLETE, each Engineer → independent Verifier PASS → independent
  Reviewer APPROVE → atomic commit: RD-01/02/03/11/13/14/16/17 (commits `97e5688`…`f397383`). Full hermetic
  pytest GREEN (only pre-existing forward-score warnings); `ruff check` clean; ledger 0 diff; no frozen
  surface touched; no real network/LLM/trial ran; E3 outcome unobserved. Writers serialized (parallel-writer
  race; see memory aionis-parallel-writer-race). `opus`/`fable` aliases blocked by `[1M]` resolver values →
  AUD-07B + RD-15 deferred; RD-08 HOLD (needs frozen rule table). Safe RD queue exhausted for sonnet tier.
  Not pushed. Detail: `state/handoff.md` § Wave-B FINAL.
- **updated:** 2026-08-05 (h). **arXiv preprint scaffold（rec #2；framing a；PREP，未上传）。**
  owner approved framing (a) + LaTeX 预制。`manuscript/` 三件套：`main.tex`（arXiv 通用 article class，仅标准宏包；
  power-floor 为 lead）+ `references.bib`（6 cited，4 WebSearch verified + 2 标准 + 5 extras）+ `README.md`（构建 +
  provenance + gaps）。结构性自查：9 begin=9 end，6 cite key 全在 .bib。**未编译**（无本地 TeX 工具链）。
  **边界**：预制非上传——arXiv 上传不可逆外发，仍待业主单独点头；纯新建 manuscript/ + state；0 ledger/frozen surface/
  prereg/ADR/config/data/E3；未外发。**待业主**：首次编译 + 授权 arXiv 上传 + venue 定位 → tailoring + 作者占位。
- **updated:** 2026-08-05 (g). **发表强化 — power-floor 文献锚定 + 复现声明（2 新 PROPOSED 文档）。**
  owner 第二次 `/goal` 推方向 1。powerfloor sonnet agent [1210] 失败（与 positioning 同模式，§17 停重试）→ opus §8 fallback。
  ① `reports/design/2026-08-05-power-floor-literature-anchoring.md`：把 σ≈0.10 锚定到 Gu-Kelly-Xiu (2020 RFS, 月 OOS R²
  **1.08-1.80%**) + Goyal-Welch (2008 RFS) + Grinold-Kahn Fundamental Law（年化 IR **0.5="good"** → σ(IC)≈7×mean → σ≈0.10
  与 Aionis 0.106 一致）+ Schuirmann/Lakens TOST；WebSearch 验证 4 引用，诚实标注精确 σ 为间接推断（§5 ⚠️）；结论稳健
  （σ∈0.08-0.15 区间内 ±0.010 等价均不可达）；推荐强 framing (a) 升 power-floor 为一等方法学贡献。② `docs/replication-availability.md`：
  reproducible-by-conconstruction（`config_committed` ledger + H6 bit-identical + tracked fetch 脚本）+ 逐源 license 表 +
  独立方复现步骤 + cover-letter 简版；引用核验真实。**边界**：纯 docs（2 新 PROPOSED）+ state；未改已定稿 draft v1.0/v1.0-en
  （venue tailoring 时由业主决定并入引用）；0 ledger/frozen surface/prereg/ADR/config/data/E3；未外发。**待业主**：
  framing 选择 + 是否补 σ 直接实证 + arXiv 引用并入 + 复现 package 形态。
- **updated:** 2026-08-05 (f). **产物化收尾（process→product）— 3 推荐 + 1 fallback 全交付（4 commit + 1 memory，push origin/main）。**
  owner `/goal` 授权"推进推荐项 + 批判性比对 + 并行 agents + 分层省 token + reuse-first"。① 静态站点 Track C climax section
  （`e94eac2`，25/25 测试绿，CI 部署成功）；② bps 敏感度 sweep（`3a3c2cf`，复用 `net_cost_summary` 0 造轮子；衰减 gross 0.149→bps=5
  0.125→bps=50 −0.088，break-even ~31 bps；8/8 测试绿）；③ 英文 v1.0-en draft（`52a3d69`，sonnet agent 忠实翻译，数字与 ledger #49
  + 中文 v1.0 交叉核对一致）；④ venue 定位 brief（`reports/design/2026-08-05-publishable-unit-positioning.md`，web search 验证：
  CFR 免费/~28 天/null-再检验 fit / RevFin null 友好 / JFEc 计量 / arXiv baseline；出版商 403 处诚实标注）。positioning agent
  [1210] 失败 → opus §8 fallback 直接写（独立性局限已披露）。分层：2 sonnet agent 并行（draft ✅ / positioning ❌）+ opus 集成。
  memory `aionis-publication-framing-option-a` 写入（锁战略约束：勿再提议拓宽 SESOI / 救 equivalence / 追新 alpha）。全套 pytest
  exit 0；ruff clean。**待业主**：选 venue 路径 + 授权 arXiv preprint（外发不可逆）+ framing 选择 + 英文 v1.0-en venue tailoring。
  **边界**：纯 docs/scripts(state-only)/state/memory；0 ledger/frozen surface/prereg/ADR/config/data/E3 改动；未跑
  confirmatory/forward/strategy；未触 E3；未外发。
- **updated:** 2026-08-05 (e). **选项 A 定稿（accept reframing）— draft v1.0-draft → v1.0。** 业主授权"按推荐方式处理"
  = 选项 A（贡献 = null 点估计 + 反泄漏纪律 + power-limit 披露；**不**拓宽 SESOI、**不**动冻结面、**不**
  rerun-to-significance）。两份独立审计 APPROVE：① power-analysis sonnet review APPROVE（0 blocking/HIGH/MEDIUM，
  3 LOW advisory：AR(1) 近似 / block size / 舍入——不影响"结构性欠功率"结论，analytic + bootstrap 双支撑）；
  ② climax diff review APPROVE（0 CRITICAL/HIGH/MEDIUM/LOW，跨文件数字完全一致，"publish as-is"）。draft 4 处
  定稿（标题+状态、§6 选项段标记 A 已选、§7 边界行、§7 残留 v1.0-draft→v1.0）。**预存 lint 债修复**：
  `scripts/track_c_commit.py:180` E501（跨多 session 的 print 行过长，非本轮 2 commit 引入）→ 提取局部变量；
  **#46 frozen sig 精确复现**（`758ca4d7...` dry-run == ledger，证明编辑未触 config 逻辑）。**验证**：ruff clean；
  全套 hermetic pytest exit 0（仅预存 forward-score/numpy warnings）；frozen-surface diff 仅 `runs/ledger.jsonl` +1
（=#49 append-only）。下一步：commit（lint fix + draft v1.0 + state）+ push origin/main。**边界**：本轮
  docs/scripts(state-only print 行)/state；无 frozen surface / ledger / prereg / ADR / config 改动；未跑
  confirmatory/forward/strategy；未触 E3。
- **updated:** 2026-08-05 (d). **Power analysis 揭示 J-T schedule 结构性欠功率（设计级发现，业主决策待定）。**
  prospective power analysis（`scripts/track_c_power_analysis.py`，复用 #49 IC series 噪声 σ≈0.106 + ρ≈0.07）
  显示 SESOI ±0.010 + looks 60/90/120 **任何一眼都无法宣布等价**：n_min = 869/580/435 月（72/48/36 年）；
  block bootstrap P(equiv)=0.0000 at all 3 looks；look-3 (n=120) RCI half 0.019 >> SESOI 0.010。**判读**：
  look-1 NOT_EQUIVALENT 不是局部保守，是整个 schedule 的必然状态（月频 rank-IC 噪声地板 vs ±0.010 SESOI）。
  E3 forward-live 即使点火也需 ~36 年才达 look-3 等价。**贡献 reframing**：null 点估计 + 反泄漏纪律 + power-limit
  披露（非"等价已宣告"）。业主 3 选项（`reports/design/2026-08-05-track-c-power-analysis-options.md`）：
  A 接受 reframing（推荐）/ B 拓宽 SESOI ±0.025（新 amendment，post-hoc 嫌疑）/ C 延长 horizon n=435（不可行）。
  draft §5/§6 已更新（诚实披露 power floor）。sonnet review 待回报。**边界**：本轮纯新建 script + design brief
  + docs/state；**0 ledger / frozen surface 改动**；未跑 confirmatory/forward；power analysis 用 gitignored artifact。
- **updated:** 2026-08-05 (c). **CONFIRMATORY CLIMAX — 首条 confirmatory OOS 入账（ledger #49）。**
  owner D6 GO 授权后，opus 直接建 `scripts/track_c_confirmatory_run.py`（frozen #48 sig 校验 + H6 双跑
  bit-identical + J-T 门 look-reachable + `confirmatory:first` 沉积；artifact-reuse 模式避免 GO 重跑）
  + `tests/test_track_c_confirmatory_run.py`（19/19 hermetic 绿，含空/NaN/边界边缘用例 + artifact-reuse
  4 守卫）。dry-run 双跑（~46min）证明 H6 → artifact-reuse GO commit 瞬时入账。**结果**：combined rank-IC
  **−0.0088**（p_hac=0.484，CI [−0.034,+0.016] 跨零 = null）；US IC +0.005 / CN IC −0.026；cond-IC β
  −0.0076（p=0.43，regime 交互 null，multiplicity 预算 1 保持）；**J-T look-1 NOT_EQUIVALENT**（RCI 99.44%
  [−0.051,+0.027] 宽于 ±0.010 SESOI = look-1 OBF 欠功率，非效应信号；look-2/3 需 E3 forward-live）。
  **bit-identical 于 asym41 exploratory**（cross-invocation H6）。**独立性**：sonnet code-review APPROVE
  （0 CRITICAL，estimand Reading A 可辩护，H6 充分，look 截断 Type-I 正确）。draft v0.1 → **v1.0-draft**
  （§5 实填 + §4 加 #14/#15 + §0/§7 更新）。**边界**：本轮 1 行 ledger（#49 append-only）+ 新建 scripts/tests
  /docs/state；**B/C/D/E1 + Track B 冻结面 / prereg / ADR 未改**；未跑 research/forward/strategy；未触 E3。
  **climax 判读**：null 点估计 + 欠功率 look-1 = 预期结果（非"不乐观"，非 bug）；J-T 门拒绝过早等价 = 反泄漏
  纪律的活体演示 = 方法学贡献。待业主审 v1.0-draft → 定稿 + 是否 push。
- **updated:** 2026-08-05. **P1 整合（audit 3 caveat 关闭）+ P0 confirmatory-GO 业主签注包交付。**
  **P1(a)** Phase B paired HAC CI 补算 = **[−0.01057, +0.00897]**（ci_half 0.00977，p_hac 0.872，n=125，maxlag=4；
  mean bit-identical #28；orchestrator opus 直接重算，Agent A `phaseb-ci` idle-without-result → memory
  `aionis-agent-dispatch-verification` 从 repo 恢复）。**P1(c)** Track C 3-layer conditional-IC 沉积 =
  combined β=−0.0148 (p=0.21) / us β=−0.0287 (p=0.13) / cn β=+0.004 (p=0.80)（joint-fold IC × 3-layer
  composite；Agent B `trackc-3layer` 交付 + opus 核验；与 handoff culmination 的 Track-B-fitter 单区
  β=−0.001/+0.015 是不同 IC series 的 sensitivity，诚实分级）。**P1(b)** Baseline FF5/RANK 措辞校准
  （exploratory-by-design 非 ledger，audit HIGH #2）+ RESULTS.md §2 行 B 补 CI + draft §4 行 #1/#9 补数字。
  **P0**：`reports/design/2026-08-05-track-c-confirmatory-go-brief.md` 交付；**owner 签 D1=A** → 起草
  `scripts/track_c_amend2.py`（amendment #48，dry-run sig `e14b9d44...`，累积 #46+#47+#48：meso US-only +
  41 列 + Q1/D2/D3/D5 冻结 + baostock G3 raw）+ amend2 doc。ruff clean + sig 自洽；ledger 仍 47 行。
  **✅ ledger #48 已入账**（sig `e14b9d44...`，owner `--commit` 授权 2026-08-05；sha256 自洽；47→48 行）。
  **待第二个业主 GO**（d6_go：授权首次 confirmatory OOS 跑 → J-T 门 → draft v1.0 climax）。**边界**：0 ledger / frozen surface / prereg / ADR 改动；
  未跑 research/forward/strategy；未观察 confirmatory rank-IC / E3。独立性局限：A 由 orchestrator 替代
  （非独立 pass），B 单一交付 + opus 核验（非独立 verifier lane）。
- **updated:** 2026-08-04 (b). **Track C confirmatory machinery staged (joint US-CN fold).** 3 commits
  on main (unpushed): `841fee4` joint fold estimator (`src/aionis/eval/track_c_joint.py`: `fit_track_c_joint`
  + `build_joint_panel` + region-month groups + per-region chronological assert; core insight: month-end
  sampling + calendar-month boundary = auto per-region 21-session embargo, so cv.py/purgedcv 0 change) +
  9/9 anti-degeneracy tests + exploratory runner; `d2606d7` shenwan 7-gate verdict (CN meso G3 fail →
  exploratory-only; confirmatory meso = US-only = current state formalized); `f4bbab7` amendment #48
  PROPOSED (meso US-only). Full hermetic pytest exit 0; ruff clean; 0 frozen-surface/ledger change.
  **Pending**: real-data exploratory joint run (proves machinery on US 588 + CN 929 panels) + independent
  review (Lane C). Confirmatory run needs owner GO + new ledger row #48 + Q1 group-construction sign-off.
  Detail: `state/handoff.md` § 2026-08-04 联合 US-CN 折叠估计量.
- **updated:** 2026-08-03. **BASELINE-FF5-001 + BASELINE-RANK-001 EXECUTED (owner-authorized, `104b21e`).**
  FF5: mean_IC=0.0106 (ci 0.0196, t 1.059, n=125, H6 True) — 18 cols (beta_dff pair RD-13-excluded:
  42 CONSTANT months 2024-08+). RANK: mean 0.015420 (ci 0.014870, t 2.0323, p 0.0421, n=125, H6 True).
  Both EXPLORATORY CV-proxy; config_committed ledger rows BEFORE results. Fixes: RES-02 SIG_ONLY +
  2015-08 window (DFF vintage start); ff5 beta_dff NaN de-contamination; RES-03 month-end sampling +
  month-end folds (LightGBM 10k/group cap) + ledger gate. FF5 snapshot + DFF vintages acquired.
  **E3 Slice 7 E2E COMPLETE + AUD-06 contracts FROZEN (D2) — `0f94620`.** `tests/test_forward_e2e.py`
  (hermetic chain: commit → I1 gate → reveal/score → I2 idempotency + immutable sealed-scores sha256 → accumulate →
  I9 separation; I3–I8 owned by existing suites). `config/e3_live_contracts.yaml`: max_age_sessions 23 → **22** +
  authoritative_refresh null + PROPOSED → FROZEN; cron stays DISABLED (headline needs owner GO). `test_e3_forward_trigger.py`
  aligned 7×. 7 forward suites 84 passed; full hermetic suite exit 0; ruff clean; real-ledger guard PASS.
  E3 code surface COMPLETE (Slices 1–7); remaining: owner GO for shadow/headline. **Orchestration protocol + reuse-first batch all committed & pushed; full hermetic
  suite back to 1352 passed / 0 failed.** **Track B 首个 rank-IC（2026-08-02, treatment 臂, config #41）**: mean_ic 0.0055, CI (-0.021, 0.033), p=0.689 null; DM -1.78/p=0.079 边际（vs 等权）。**差分（#41 treatment - #42 price-only, headline）**: mean_diff 0.0076, CI (-0.004, 0.020) 跨零, p=0.219 → 未显著优于 price-only（null，符合 null-favored）；CI 上界 0.020 > SESOI 0.010 → 不构成严格等价（需更多样本）。
- **orchestration (2026-08-03):** `ADR-012` + `docs/orchestration-protocol.md` + `scripts/orchestrate_dispatch.py`
  (11/11 tests green, ruff clean) + dispatch-contract template landed — owner chose **local task files = issues**
  (zero GitHub surface). Lane model = opus Orchestrator + low-freq opus Supervisor (监工) + sonnet/haiku workers
  (serialized) + independent verifier/reviewer/e2e lanes; 6-layer denoised dispatch; anti-leakage guardrails binding.
  Committed `daa92e8`. **Wave validation**: ORCH-01 macro cumulative-preserve test (COMMITTED `8d19b28`) — first
  dispatch wave: executor succeeded, reviewer lane hit an idle-without-verdict harness gap → protocol §8 hardened
  (`83d9d61`); ORCH-02 REJECTED (`3ad4710`) — premise was a grep-suffix miss (8-K already covered); also found a
  `[1210]`-failed agent can leave partial work in the tree → §8 hardened again. **`/goal` reuse-first batch**:
  `f6e0536` DRY the 3 forward collectors' persist tail into `_common.persist_snapshot` (byte-identical ledger
  output); `e6c71ec` static-site tests aligned to the Track B page (was 12 failing) + hermetic `--out-dir` so
  tests never touch `site/` WIP. **Full hermetic suite: 1352 passed / 0 failed; ruff clean.** Track-B uncommitted
  WIP untouched throughout; no frozen surface / ledger / data touched; no real network/LLM/trial ran.
- **qlib dual-region POC (2026-08-03):** owner-authorized 可逆证据 POC,解决 Option A 辩论(独立批判者 REJECT;辩护/裁断 agent 因 `[1210]` 5 次失败缺失,由 orchestrator 非独立核查替代)。完整报告 `reports/2026-08-03-qlib-dualregion-poc.md`。**5 硬证据:** ①qlib 双区域特性存在(`REG_CN/US`+`LocalPITProvider`+CSI300/500 采集器[从 csindex 历史公告重建,非当日快照]+pit 采集器)→**推翻批判者 #2/#8/#10** vaporware/捏造/当日快照; ②cp313 门(pyqlib 0.9.7 无 cp313 wheel;Aionis 跑 3.13;3.11 隔离 venv `IMPORT_OK` 0.9.7 已验绕过)→部分验证 #2; ③RobustZScoreNorm 泄漏陷阱实证确认+折内钉 fit 修复有效(CLEAN train z-median 0.0000 vs LEAKY −0.3453); ④DatasetH 手术点③需 3h 真实接线; ⑤**baostock G3 结构性不可合规**(`query_profit/balance_data(code,year,quarter)` 期末键、无 as-of/vintage)→**验证并强化批判者 #1**。**Net: Option A′ 条件-sound,8 门实证背书(见报告 §3);** A 股基本面须换 filed-date 键源(cninfo/Tushare-`ann_date`/自建)或降 exploratory-only。Scratch `/home/re/code/aionis-qlib-poc/`(仓库外),合成数据,**未 commit/未触冻结面/ledger**;网络仅 GitHub+PyPI;无 baostock.com 数据调用、无 research/forward 脚本、未观察 E3。Loop cron `3219e84b` 已取消。Owner 未裁决前不构成方向变更;Option A′ 落地=新预注册+新 config+新 ledger 行。
- **Option A′ `/goal` 推进 (2026-08-03):** owner `/goal` 授权(多 agent 按优先级 + 模型分层省 token + reuse-first)。**[1210]** opus/sonnet 子代理今天执行不稳 → 分层:orchestrator 直接 opus 设计 + sonnet/haiku 后台 agent。产出(PROPOSED/docs,未触冻结面/ledger):`reports/design/2026-08-03-conditional-rank-ic-multiplicity.md`(gate 7 解决:预指定交互=1 检验非 K,复用 purgedcv/arch/YannickKae;Deflated-RankICIR 待 license)+ `reports/design/2026-08-03-track-c-prereg-skeleton.md`(Track C 预注册骨架 v0.1;§3 features/§5 折设计/§1 regime 定义 TBD)。后台 agent 运行中:`ashare-gate-research`(sonnet,P0 A 股 filed-date 源 7-gate,gate 4)+ `drankicir-check`(haiku,Deflated-RankICIR license)。下一步待 T1 回报填 Track C §3 + 定 A 股源(headline 可行 vs exploratory-only)。
