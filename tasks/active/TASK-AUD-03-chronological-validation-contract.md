# AUD-03 — Establish the chronological validation contract

- 编号: AUD-03
- 标题: Separate purged cross-fitting from strictly chronological validation in code, tests, and terminology.
- 状态: **COMPLETE — independent re-verification PASS; Reviewer APPROVE**
- Priority: **P0**
- Size: **M**
- Risk: **HIGH**（方法学 load-bearing；任何真实 rerun 都会构成新的研究决策）
- 建议 agent role / model tier: **Engineer / strong**；Verifier / strong；Reviewer / strong。
- 目标: 用 hermetic synthetic tests 固化两个不同合同：`PurgedGroupKFold` 是 purge+embargo 的
  cross-fit/OOF；chronological validation 必须保证所有 train prediction/evaluation times 早于 test。
- 背景: `purgedcv.PurgedGroupKFold` 的 candidate train 是 test complement，早期 folds 会使用未来月份；
  项目现有 group-kfold tests 只检查 group/index disjoint。严格 before-test 的断言只覆盖
  `purged_walk_forward_splits`。因此 B/C/D/E1 不能无条件称为 chronological OOS。
- 依赖: AUD-01 PASS。AUD-02 的最终术语依赖本任务 verdict。
- 允许修改: `src/aionis/eval/cv.py`、仅与术语/合同相关的 `src/aionis/eval/two_arm.py` docstrings、
  `tests/test_cv.py`；可新增 `docs/chronological-validation-contract.md`（方法合同，不是 pre-reg）。
- 禁止修改: learner/features/config、phase scripts/orchestrators、rank-IC/CI 计算、frozen prereg/ADR、
  `runs/**`、`data/**`、公开结果数字；禁止运行任何 real-data phase/strategy/horizon/forward 脚本。
- 前置条件: 先用小型 synthetic monthly panel 复现并记录：group K-fold 可包含 future train rows，
  walk-forward 满足 strict-before-test；不得加载真实 OOS parquet 或结果 artifacts。
- 实施要求:
  - 保留现有 frozen research行为；本任务只建立语义、assertion/helper 与 hermetic gate，不偷偷把
    已发布 pipeline 切换成另一 splitter。
  - chronological contract 至少要求 `max(train prediction_time) < min(test prediction_time)`，且
    train label/evaluation time 不越过 test start；embargo/group 不变量继续成立。
  - API/docstring 必须显式标识 splitter 的 validation kind；任何 future caller 声称 chronological
    必须走 strict helper/assertion。
  - 已发布结果的重分类由 AUD-02 处理；是否执行 chronological re-analysis 是新的 owner decision。
- 验收标准:
  - [ ] synthetic test 证明 PurgedGroupKFold 的 non-chronological complement 行为，避免再误称 forward OOS。
  - [ ] synthetic tests 对 chronological path 逐 fold 验证 train prediction/evaluation time 均早于 test。
  - [ ] purge、embargo、group-disjoint 原测试继续通过；无真实数据、无 score、无 IC 被读取/生成。
  - [ ] code/doc 合同不能把“same folds isolate treatment difference”夸成 chronological out-of-sample。
  - [ ] `git diff` 不含 phase config、prereg、ledger 或 result artifacts。
- 必须运行的测试: `uv run pytest -q tests/test_cv.py`；`uv run pytest -q`；`uv run ruff check`；
  `git diff --check`；只读 `git diff -- runs/ledger.jsonl 'docs/phase-*-preregistration.md'`（空）。
- 失败处理: 若落实合同必须改变 frozen pipeline 输出，立即 STOP/BLOCKED；提交 owner decision 选项
  （保持历史 OOF 标签 / 新 exploratory chronological study / 新 confirmatory config），不得自行跑任何一个。
- 预期产物: 一个可测试的 chronology contract、synthetic regression gates 与准确术语。
- 完成后需要更新: AUD-02 evidence table、`state/current.md`、`state/handoff.md`；真实重跑保持未授权。
- see: `src/aionis/eval/cv.py:77`；`src/aionis/eval/two_arm.py:45`；`tests/test_cv.py:37`、`:85`；
  `purgedcv/_base.py:121`。

## 2026-07-31 read-only preflight

- `PurgedGroupKFold` uses the test complement as its candidate train set; it is purged cross-fitted,
  not chronological. `WalkForwardSplit` is the path that restricts candidates to earlier observations.
- The chronology assertion must preserve half-open label intervals: train prediction time `< test_start`
  and train evaluation time `<= test_start`. Tightening the latter to `<` is an owner decision because an
  existing synthetic fold has equality at the boundary.
- A minimal implementation can add validation-kind metadata and fail-closed synthetic assertions without
  changing frozen folds, scores, configs, ledger rows, or results.

## 2026-07-31 execution evidence

- Engineer added explicit `chronological` versus `purged_cross_fit` metadata, a fail-closed chronology
  assertion, accurate cross-fit terminology, and hermetic tests without changing splitter indices or any
  frozen research behavior.
- Independent Verifier PASS before repair: targeted CV tests, scoped ruff, diff integrity, unchanged frozen
  preregistration/ledger surfaces, and correct half-open time inequalities.
- Reviewer round 1 requested compatibility and boundary-test strengthening. Repair round 1 gives three-argument
  `CVSplit` construction the conservative `purged_cross_fit` default and adds negative prediction/evaluation
  boundary tests plus the permitted evaluation-time equality case.
- Repair Engineer reports `uv run pytest -q tests/test_cv.py`: 15 passed; scoped ruff and diff checks PASS.
- Independent re-Verifier PASS: targeted 15 tests and full 589-test suite pass; all-repo ruff, diff integrity,
  and frozen preregistration/ledger checks pass. It confirmed conservative three-argument compatibility,
  half-open time boundaries, explicit validation kinds, and unchanged frozen splitter parameters/indices.
  Reviewer re-review APPROVE: prior compatibility and time-boundary findings are resolved; implementation
  preserves frozen folds while making cross-fit versus chronology explicit.
