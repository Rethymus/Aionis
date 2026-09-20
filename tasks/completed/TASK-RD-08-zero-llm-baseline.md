# RD-08 — 零 LLM 闭集规则基线

- 编号: RD-08
- 标题: 建立保守、可 abstain 的零 LLM 抽取对照。
- 状态: **IMPLEMENTATION COMPLETE — sonnet Engineer + 独立 Verifier（功能全 PASS）+ haiku lint-fix（ruff clean）+ 独立 Reviewer APPROVE（0 阻塞）。zero_llm_baseline.py 机械应用冻结表（11 规则逐条、小写 enum、sha256 溯源、6 条 abstain 路径、fomc_guidance_abstain_001 precedence-110 抑制前瞻指引误判）；structural-only 无 sentiment/market_impact；25 tests + RD-06 兼容。frozen 表/providers/llm_client 未改。**
- Priority: **P1**
- Size: **M**（90–150 分钟）
- Risk: **MEDIUM**
- 目标: 建立只依赖 event_type/metadata 与明确关键词的保守 ERL baseline，支持 abstain，作为小模型
  抽取评估对照；不进入选股 feature 或研究结果。
- 背景: 没有零 LLM 对照，无法判断模型是否真正增加了结构化信息，还是只复述 metadata。
- 允许修改: `src/aionis/extraction/zero_llm_baseline.py`、`tests/test_zero_llm_baseline.py`。
- 禁止修改: features/eval phase runners、模型 prompt/provider、data/ledger/results/config/prereg/ADR/state。
- 前置条件: RD-04、RD-06 APPROVE；strong Researcher + owner 先冻结 tracked
  `evals/expected/zero_llm_rules_v1.yaml`，逐条给出 event_type、正则/token pattern、否定窗口、edge tuple、
  precedence、冲突时 abstain 与 rule id；owner 再授权 RD-08。Engineer 无权新增/改规则或阈值。
- 实施要求: 逐字执行冻结规则表；无 sentiment/market impact；无匹配、冲突或否定窗口命中即 abstain；
  每个命中返回 rule id/provenance。规则表 hash 写入输出。
- 验收标准: fixture 输出确定；否定词/歧义/空文本不产生激进 edge；可直接交给 RD-06 计分。
- 必须运行的测试: `uv run pytest -q tests/test_zero_llm_baseline.py tests/test_extraction_eval_metrics.py`；
  `uv run ruff check`。
- 失败处理: 规则表不存在/矛盾或需要领域判断的新规则时 HOLD/记 backlog，不在本任务扩展。
- 预期产物: baseline extractor、rule provenance、边界 tests。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
