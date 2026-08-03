# state/current.md — read first each session

- **version:** 0.1.0 (pyproject)
- **milestone:** B/C/D/E1 ledger results and h={10,42} sensitivity exist; E3 Slices 1–5 and the
  near-final dashboard are implemented. The 2026-07-31 quant+LLM audit reclassifies the historical
  evidence as **purged cross-fitted/CV-proxy**, not chronological/live OOS.
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
  ADR-010 TOST p-value direction/sequential-equivalence construction CONFIRMED BROKEN by AUD-07B (2 CRITICAL, double-opus review); E3 verdict/headline HOLD pending owner-authorized ADR-010 + prereg §7 amendment.
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
