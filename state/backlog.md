# state/backlog.md — candidates, not committed

> Add ideas here during a sprint; evaluate at milestone boundaries. Do NOT interrupt the current
> task. See `WORKFLOW.md` §6 (freeze rules).
>
> 2026-09-21 轮 99 刷新：已完成项移入文末"已完成"区。owner-gated 研究项的权威清单在
> `tasks/active/TASK-RES-*.md`，此处只留指针。

## 开放候选

- **Phase B OOS panel.** `scripts/phase_b_run.py` predates the schema-2 OOS-persistence wiring;
  pass `oos_state` / `oos_base` to `save_run` + a solo B rerun so all 4 phases demo the fit charts.
  **S** task.（与 blockers 的 uv.lock sig 处置联动——先裁 sig 再跑 rerun。）
- **E2 build (LLM macro-causal, cutoff-controlled).** Blocked on TASK-STRAT owner decision.
  See `../docs/phase-e2-preregistration.md`, `../decisions/ADR-005-e2-underpowered-e3-forward-live.md`.
- **E3 forward-live launch.** The only POWERED zero-leak path; calendar-gated（9-30/10-31 影子窗，
  10-01 04:05 自动化已武装）。See `../docs/phase-e3-preregistration.md`.
- **Earnings as abstain / event-study event.** Zero-LLM abstention table (RD-08) covers
  FOMC/CPI/NFP/13D but NOT earnings; `earnings_8k_forward.py` exists so the PIT path is open.
  **BLOCKED until**: E3 headline HOLD lifted AND new owner-approved pre-registration/config
  (new event type = scope expansion; 7-gate; new ledger row). Never mutate B/C/D/E1. **M**.
- **SIC vintage.** SIC is current-snapshot (mild lookahead for reclassifiers); low priority
  (small effect). **M** task.
- **evals/cases golden fixtures.** Slot in once E3 forward-live produces commit/reveal fixtures.
- ~~**Slice 2 review LOW×5 cleanup（advisory）。**~~ **完成清账（10-05 轮 184）**：docstring 首跑注记
  ×3、structlog `forward_persist_real_ledger` warning、`persist_snapshot` DRY 均已在早前轮落地；
  最后一项 `keyfn = str.upper` 别名化简本轮落地（行为等价，forward 电池 EXIT=0）。

- ~~**i18n 字典按语言拆块（轮 201 候选）。**~~ **完成（10-06 轮 201，375064b19）**：每路由 -95KB；dict-zh 静态/dict-en 动态；audit+3 契约适配。

- **恢复道"仅重试软败步骤"策略（反思四 §一.3）。** 23:53 恢复道在 ok_committed 时 SKIP——软败步骤的
  数据最坏陈旧 24h+（如 GDELT 源缓存夜）。变更为"软败步骤选择性重跑"影响通道核心语义（幂等性/记账/
  push 边界），需 owner 对通道策略表态后专轮设计。**M**。

<!-- 以下五条=2026-11-12 iterate 轮 backlog-candidates-register 登记（研究面/代码级候选，
     全部不上施工：研究面须 mission 指名+预注册+config_committed，见各条触发条件） -->

- **purgedcv effective_n_trials / min_track_record_length（DSR n_trials 升级 + SR 最短跟踪记录）。**
  安装版 purgedcv 0.1.2 顶层已导出两函数名（2026-11-12 实测 `import purgedcv; dir()`；License MIT），
  能力在但语义属**研究面**（DSR/SPA 判定族=src/aionis/eval/ 面）。**触发条件：mission 明确指名研究面** +
  新预注册（N 计数口径随 config 冻结入 prereg 附录）+ `config_committed` ledger 行——三者缺一不上施工。
  来源：iterate 轮外向调研条目 2；与前沿吸收 #10（DSR 试验计数通缩+minTRL）同族。
- **langextract 结构化抽取辅助试点。** Apache-2.0（白名单内），但 extraction 面属研究管线
  （src/aionis/extraction/）——**试点限 tests/fixtures 标注层**（labeled fixture 合规域），绝不入真实
  抽取管线；扩至真实抽取须预注册 + mission 指名 + 新 ledger 行。来源：iterate 轮外向调研条目 3。
- **Harvey-Liu-Zhu t≥3.0 门槛入 docs/RESULTS.md（稳健性并列呈现）。** 多重检验视角与既有两尾预注册
  判定**并列呈现**候选，append-only 勘误语义，**不改判定门**（主检验=预注册两尾不变，HLZ 仅附录
  视角）。触发条件：业主对 RESULTS.md 呈现面点头。来源：iterate 轮外向调研条目 4。
- **fja05680/sp500 PIT 成员双源对照。** constituents_on 单源的双源审计候选（scripts/ 审计类，不改
  研究管线）；**只认 MIT 原仓**，fork/转载不认。**M**。触发条件：审计轮 mission 指名。来源：iterate
  轮外向调研条目 4。
- **Jev 代码级候选（{answer,p} 输出契约 + --propose 预测陈述字段 + Brier 式月末对账）。** 判别层输出
  附概率陈述、提案卡带预测字段、月末对账命中记录（裁决与两栏分析见
  `reports/audits/2026-11-12-iterate-round.md` Jev 章节）。**诚实边界**：GLM 概率未校准、仅路由用——
  不得作校准概率消费；月度小样本对账仅**记录性**校准，禁任何统计显著性声称。触发条件：mission 指名 +
  预注册（涉 eval 呈现面）；provider 红线不变（不接 Jev API/typesafe-sdk）。来源：iterate 轮 Jev 专题
  （backlog-candidates-register 条）。

## 前沿吸收（轮 127，2026-11-11；来源=reports/audits/2026-11-11-env-testpipeline-round.md §6b——两路前沿调研中 high 但 L 规模/存疑/触红线者，逐条含来源 URL）

> 实施前逐条过 7-gate（docs/data-intake-rubric.md）与许可证白名单（MIT/Apache/BSD）。

1. **哈希链账本 + 一次性 holdout 回执 + 门合取**（https://arxiv.org/abs/2611.06607；MIT 参考实现 github.com/henryzhangpku/autonomous-quant-researcher）——**触红线**：`runs/ledger.jsonl` 语义零改动、receipt 属 scripts/phase_*。
2. **动量倾斜归因预注册**（https://doi.org/10.1016/j.jfds.2026.100207；SSRN 7010050）——下一 phase 预注册，owner 研究决策。
3. **知识截止/结果感知新门**（https://www.ravenpack.com/blog/insights-and-limitations-in-stock-price-prediction-using-llms；arXiv:2401.03737）——需改 docs/data-intake-rubric.md，非运维轮可触碰面。
4. **purged-CV 第二实现一致性测试**（https://github.com/eslazarev/purged-cross-validation，MIT 64★）——**存疑**：PyPI 可安装性未验证；CPCV/PBO 仅诊断、不作主分割器。
5. **time-machine 时间桩 conftest**（https://adamj.eu/tech/2026/08/03/python-time-machine-o1-freezegun-on；MIT v3.6.0）——8 个 src 模块墙钟语义分批。
6. **pytest-randomly**（https://github.com/pytest-dev/pytest-randomly，MIT v5.1.0）——2430 用例随机序体检 + 豁免治理。
7. **pytest-xdist -n auto --dist loadfile + faulthandler_timeout=300**（https://docs.pytest.org/en/stable/explanation/flaky.html，MIT v3.8.0）——需 H6 位一致豁免组设计。
8. **抽取错误分类学人工审计**（https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6496861）——人工标注成本 L；审计集与 prompt 调整隔离。
9. **组合级 FDR 读数**（https://people.duke.edu/~charvey/Research/Published_Papers/P143_False_and_missed.pdf）——docs/RESULTS.md 报告层，不回溯改 α。
10. **DSR 试验计数通缩 + minTRL**（https://arxiv.org/html/2512.12924v1）——N 随 config 冻结，仅预注册附录。
11. **时序共形区间**（https://arxiv.org/html/2507.05470v1）——稳健性视角，不变更主检验。
12. **actionlint + zizmor 常驻静态校验**（https://github.com/rhysd/actionlint；https://github.com/zizmorcore/zizmor，均 MIT）——二进制未装未跑；如集成 doctor 需条件存在守卫，保守后置。
13. **act 本地 dry-run**（https://github.com/nektos/act，MIT）——解锁前预检工具，不入 repo 依赖。

## 名词指认资料（Jev 指认规则；2026-11-12 轮 130-续入册，杜绝 JEPA 混读）

> 本区为名词指认参考，**非任务候选**——propose 引擎不解析本区（`backlog_open_candidates`
> 仅读「开放候选」节内 bullet，prop: 前缀标记扫描本区无命中；`scripts/monthly_review.py:697`
> 解析语义实读证实）。**Jev = TypeSafe 公司 AI System One 判别式决策模型**
> （discriminative decision model；2026-09-15 发布，RLCD 训练）；**与 LeCun 的
> JEPA（Joint-Embedding Predictive Architecture）无关**——两名词不得混读/互替。
> 裁决边界：协议级同构仅采两点（判别/生成分层、预测误差=改进信号），落点 docs+state
> （`docs/ops-local-refresh.md` 值班协议「判别层/生成层分层」小节 +
> `reports/audits/2026-11-12-iterate-round.md` Jev 章节）；「内部世界模型」叙事不采用
> （过度类比贴金）；**代码级 rejected**——无白名单轮子支撑（`docs/data-license-allowlist.md`
> grep 零命中）且接入 Jev API/typesafe-sdk 违 provider 红线（LLM pool =
> GLM/SiliconFlow/ModelScope ONLY，AGENTS.md）；代码级候选见同批
> backlog-candidates-register 条。
>
> **勘误（append-only，2026-11-12 复核）**：上方段内 `scripts/monthly_review.py:697`
> 行号过时——def `backlog_open_candidates` 行号实读 **:698**（2026-11-12 复核；
> :696-697 为空行）。
>
> **延伸阅读索引与同批指认（2026-11-12 append，仅索引不装条目）**：
> ① 阅读索引两清单（均 CC0-1.0，`docs/data-license-allowlist.md` ACCEPTED 表在册）：
> awesome-system-one（github.com/andyrewlee——System One 模型/agent/SDK/benchmark
> 总目）与 awesome-jev（github.com/KennethAshley——Jev 生态 410 条 19 类，评测类
> 含 Brier/ECE 校准条目）；**仅索引用途，不装任何条目、不引任何包**。
> ② Jeva null-aware 延伸研读：arXiv:2610.18773（Jeva: System One Models from
> First Principles，2026-10-13 提交，null-aware 为其四结构要求之首）；参考实现
> typesafe-sdk-python/js（官方仓，MIT）——**只读不引**（接入仍违 provider 红线）。
> ③ **Microsoft-Decision-1 实体指认**：微软决策评分模型（2026-10-09 官方 Command
> Line 博文发布，Qwen3.5-9B 后训练单遍判别决策模型）——与 JEPA 无关，同 Jev
> 指认规则防混读；其 Foundry API 接入与定价模式**不采**（provider 红线 +
> 无关本地运维）。

## Owner-gated（预注册级 GO 才可动；权威 spec 在 tasks/active/）

- **Strong-baseline ladder.** RES-01/02/03/10（momentum/FF5-cross-sectional/rank-label/LLM-eval）。
  FF5 另需数据准入（docs/data-intake-french-ff5.md）。
- **Economic-validity lens.** RES-04 next-open / RES-05 turnover-slippage / RES-06 liquidity-borrow /
  RES-07 delisting-capacity。
- **Zero-LLM ablation 扩展.** RES-09。
- **Gold set 后续阶段.** RES-08（stage 1 已冻结 e3-causal-gold-v1）。
- **P1-4 Track A 因子生成器.** 轮 59 裁决 DEFER 至 10 月末（单焦点纪律）。

## 已完成（自本清单销项，证据在 tasks/completed/ 或 state/current.md）

- ~~Horizon-robustness extension（h=10/h=42 已跑，B/C/D/E1 全 null 保持）~~（轮 ㉛ 审计发现已 DONE）。
- ~~SESOI/TOST + sequential gate~~ → AUD-07 + AUD-07B 完成（ADR-010 Amendment）。
- ~~Macro cumulative-preserve test [MEDIUM]~~ → ORCH-01 COMPLETE（8d19b28）。
- ~~LLM extractor evaluation 基建~~ → RD-04/05/06/07/08/11 + RES-10 rewrite 完成。
- ~~本地刷新通道/晚班 token 经济/GBK+NaN 修复~~ → 轮 89/96/97/98 运营化。
