# Lessons learned

> Distilled findings that changed how the project runs.

1. **Evidence boundaries matter.** B/C/D/E1 show no significant positive increment
   under one frozen, purged cross-fitted implementation. B has no paired CI; C is
   outside a post-hoc +/-0.015 equivalence band; none proves market efficiency.
2. **Recurring orchestrator save-skip bug.** An `if results_base is not None:`
   guard skips artifact writes when the main passes `None`. Orchestrators must
   **always** `save_run` — never gate persistence on a caller-supplied path.
3. **VIXCLS is unrevised** → PIT via the no-revision contract (G3), *not* via
   ALFRED-style vintage tracking.
4. **pandas >= 3.0 `transform("size")`** counts NaN-inclusive groups; use
   `transform("count")` for NaN-aware group sizes.
5. **The cumulative-IC random-walk band uses sigma**, not `se_hac`. sigma/sqrt(n)
   is ~11x too narrow and falsely shows "skill" for a null IC.
6. **Durable registry beats disposable artifacts.** `config_committed` sha256
   BEFORE the result: same-sig reruns are reproducibility, a changed config is a
   new ledger row — never a silent overwrite.
7. **Purged cross-fitting is not chronological OOS.** Purge and embargo prevent
   label overlap, while complement-based folds may still train on later months.
8. **LLM attribution must be explicit.** B/C/D/E1 are zero-LLM; Phase A is an
   underpowered 53-ERL/43-cluster pilot, not evidence of stock-selection alpha.
9. **Economic claims need economic inputs.** The B/C strategy lens is exploratory,
   gross of costs and lacks turnover; it cannot establish net tradability.
10. **Nested `<a>` guarantees hydration mismatch (#418).** A card-level `<Link>`
    wrapping rows that are themselves `<Link>`s parses differently as a string
    (browser force-closes the outer anchor) than as a vDOM — every load throws
    React #418. Found by controlled ablation builds + targeted subtree diff,
    not by reading the code.
11. **content-visibility has a DOM-size threshold (~10k elements).** It paid
    -45% TBT on a 7k-DOM page and cost +20% on a 1.5k-DOM one — containment
    bookkeeping exceeds the layout savings below the threshold. Chart-heavy
    pages need deferred *mounts* (dynamic ssr:false) instead: hydration is not
    skipped by paint containment.
12. **A chart-level async split pays only when charts dominate page cost.**
    Same recipe: -40% on a chart-led page, +300ms net-harmful on a
    table-led page with one small chart (measured 4 runs, control page).
13. **TBT is sensitive to delivery interleaving.** The same build measures
    differently across network windows (slow windows spread long tasks);
    single live runs mislead — take medians, and treat local A/B as the
    deciding instrument.
14. **Never trust a saved marker's stale fields.** A marker mixing last
    night's `finished_at` with this run's `status: running` read as "crashed";
    it was mid-run. Verify against process liveness before acting.
15. **Multi-pathspec `git add` fails atomically.** One stale pathspec aborts
    the whole staging — a commit then shipped only part of the change. Check
    `git diff --cached` after every staged add.

## 外部同构先例引用锚（frontier-citation-anchors，2026-11-13；仅引用不装包不接入）

以下两条为外部文献与本仓既有纪律的同构对照，**仅作引用锚**——不改变任何在册
流程、判定门与红线：

- **预注册协议公开哈希 + 未来实价打分**（arXiv:2611.13962，*Deceleration
  without identification: testing a power-law trend in Bitcoin prices under
  persistent noise*，stat.AP 2026-11-10；本会话 fox_fetch 一手复核）：原文明示
  「The procedure was fixed, validated and publicly hashed before it was
  applied once」+ 2027-2030 注册预测将由未来实价打分——与 lesson 6
  （config_committed sha256 BEFORE result、冻结后单次应用）同族先例。
  **明示：不改 `runs/ledger.jsonl` 语义（在册前沿吸收 #1 红线裁定不变）。**
- **门控解锁复制协议**（arXiv:2611.09286，*The End-of-Day Reversal After
  2019: A Pre-Registered Test on S&P 500 Stocks Excluding Heavily Traded
  Names*，q-fin.ST 2026-11-06；本会话 fox_fetch 一手复核）：私有预注册下
  「2016-2019 数据须先复现已发表符号，才解锁在后续主样本上计算任何 linking
  statistic」——先复制后解锁的门控顺序，与本仓「确认性运行前冻结
  config + 预注册」流程同向对照。**明示：不改任何现有 phase 预注册流程。**
- **「Only facts can block」判别层阻断先例**（qkal/Canny README，MIT，v0.4.0；
  jev-artifact-map §2.1 素材，本会话 fox_fetch 一手复核）：「Facts go to code.
  Judgments go to Jev. Only facts can block.」——确定性钩子以账本可证事实
  （exit 码/文件变更）才可阻断，LLM 判断仅成注记（Jev never blocks）——与本仓
  值班协议「判别层零 LLM 阻断」+ exit 码契约门同构先例。**明示：仅引用锚，
  不改任何在册流程、判定门与红线（不引入外部判别 API 裁定不变）。**

## See also

- [RESULTS.md](RESULTS.md)
- [the display-era campaign report](../reports/design/2026-10-02-performance-campaign.md)
  (12 wins, 11 nulls, the four measured boundaries behind lessons 10-13)
