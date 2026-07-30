# 否决 — 采用 Guo-Kavalakis-Xiu (GKX) 主因子数据集

- 编号: REJECT-gkx
- 标题: Use Guo-Kavalakis-Xiu (GKX) master factor dataset
- 状态: rejected
- 目标: 为 Phase B 选定一条 confirmatory 候选数据路径（GKX 曾是候选 `A-GKX` 路径）。
- 背景: GKX 曾被评估为 Phase B 的候选「A-GKX」主因子数据路径。
- 否决理由: GKX 以 **permno** 为键，**无免费的、point-in-time 的 permno↔CIK 桥**；
  一个今天快照的 `cik_map` 会构成 **look-ahead 泄漏**（critic 发现 C1）。
  confirmatory 路径必须满足 PIT + no-revision，GKX 在此不通。
- 替代方案: **自建 ticker-keyed PIT S&P500 universe**（hanshof + pierrebrunelle 成员资格），
  以 ticker 为键直连 SEC EDGAR（`filed`-date PIT、不可回改）。
- see: [`../../decisions/ADR-002-gkx-excluded-ticker-keyed.md`](../../decisions/ADR-002-gkx-excluded-ticker-keyed.md)
