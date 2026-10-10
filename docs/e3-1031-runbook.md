# E3 10-31 runbook — 修订版（2026-10-10，轮 249；吸收 9-30 全剧教训）

> 执行者：10-31 自动化（automation-094c3b3a）或任何会话。本文件是 ⓪b 步的
> **权威修订**——原版缺陷：无时间轴推进器（9-30 fail-closed 根因）、无配额/
> 断点意识（10-09 六小时学费）、无 submissions 新鲜度意识（9 月窗 0 行根因）。
> 全部已修复并实弹验证（面板扩展 09-30 五项判定全 PASS、9 月 READINESS
> PASS+预测密封提交 config a2d3a4a9）。

## 排程纪律（小时配额现实，轮 244 实证）

- Tiingo 免费档=**小时**配额（"hourly request allocation"，~50 符号/窗）；
  597 符号全量 ≈ 10 小时滴流。**⓪b 必须当日窗口早段启动**（04:05 首班即可），
  断点续传让小时守卫（04:05-23:05）逐窗推进，完成标记门控防丢版。
- Alpaca 后备现已真实可用（轮 246b 参数序修复后双源轮转）——每符号
  Tiingo 失败即落 Alpaca，~3/分钟。
- 中途杀掉/断电：部分存储在 `data/cache/e3_extend_partial.parquet` +
  `e3_extend_fetched.json`，重启自动跳过已抓。

## 步骤（修订处标注）

- **⓪a** membership 扩展：`extend_membership_wikipedia.py`（不变）。
- **⓪b（修订）** E3 面板扩展：
  ```bash
  uv run python scripts/e3_extend_prices.py --through 2026-10-30
  ```
  - `--through` 是 9-30 剧终的结构修复：只延长 `_e3` 面板行到目标日，
    冻结基底 `phase_b_prices.parquet` 字节不动（sha 27c63577afc66f5a
    前后核对）。
  - 逐符号容错（退市名 NaN 合法）；连续 5 空/429 睡眠至下一小时界。
  - 完成标志：`phase_b_prices_e3.parquet` 边=2026-10-30，partial 存储消失。
- **①②** volume/materialize（不变；CN 腿软败参见
  `docs/source-redundancy.md` 切换预案）。
- **③** `uv run python scripts/e3_forward_trigger.py --run-date 2026-10-31`
  - submissions 新鲜度已内建（轮 248：缓存最新申报早于窗下界即重取）——
    9 月窗 0 行的根因已消除。
  - 预期路径：READINESS 全梯 → fit → commit → 密封（**不揭盲**）。
- **收尾**：账本 sha 前后记录；`test_ledger_append_only_*` 钉的按协议重钉。

## 判据 1 算术（10-31 证据包呈业主）

8/31 PASS + 9/30 PASS（标注补跑）+ 10/31 live = 双 PASS 影子月。
9-30 的两行 forward 账本行（重冻+提交）属设计内幂等语义，证据包如实
标注"marked re-run"。

## 已知剩余缺口（如实）

- `forward_8k_no_cik` 的 5 个 CIK 覆盖缺口（AVB/BBBY/BK/EQR/SATS）由
  `_CIK_OVERRIDES` 在 ⓪b 兜底（BBBY 已退市仅历史列）。
- 面板 no-data 6 活名（APTV/ARE/ARES/ATO/AVB/LEG）为 NaN 列——readiness
  门会在横截面处如实裁决。
