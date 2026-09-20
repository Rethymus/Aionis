# state/blockers.md — what is blocking and why

> 2026-09-21 轮 99 全量重写：逐条对照 tasks/completed/ 归档证据核验。已解决项移入文末
> "已解除"区（保留一段史，防重复排查）；只有**当前真实阻塞**留在上方。

## 当前阻塞（真实）

- **E3 headline 是 NO-GO，直至影子样本 + 业主 GO。** 判据要求影子满 2 个月：9-30 与 10-31 两个
  窗口（9-30 窗口的 runbook 自动化 97cec742 已武装，北京 10-01 04:05 触发；10-31 评估点待武装）。
  统计门已有效（AUD-07B RESOLVED，ADR-010 Jennison-Turnbull 修正案）；点燃仍需 owner GO。
- **E2 作为 backtest 欠功效（结构性，非新）。** cutoff 门把 125 月 OOS 压到 ~10-18 月。
  解法=唯一有功效的零泄漏路径 E3 forward-live。不阻塞 E2 作为设计/假设发生器。
  **业主决策（TASK-STRAT）未做。** 见 `decisions/ADR-005-e2-underpowered-e3-forward-live.md`。
- **Phase B OOS 面板被 `uv.lock` 搁浅（良性，业主裁决待做）。** A1 同签名卫兵按设计触发：
  B 冻结 sig 算自旧锁 `e045a023…`，现树用 `ee985437…`；差异仅 praw 系五包，lightgbm/pandas/
  numpy/pyarrow/sklearn/purgedcv 全未动 → IC 序列仍可逐位复现，仅 sig 字符串移动。
  处置选项（推荐 DROP，纯装饰性）：DROP · 恢复旧锁跑一次 · 按现锁重冻 B（需 ADR）·
  收窄 config sig 至承载版本（架构性）。非 4-null headline 的阻塞。
- **Kenneth French / FF 数据准入业主暂持。** `features/selection_panel.py:fama_french_daily`
  走 SDK 自带 HTTP；准入评审（7-gate）未做前 cache miss BLOCKED。见
  `docs/data-intake-french-ff5.md` + `tasks/active/TASK-RES-02-baseline-ff5.md`。
- **GLM 5 小时限额（429，周期性）。** 供应商配额，滚动窗口重置。缓解=模型分层+单次有界重试
  +ProviderRouter 冷却+幂等磁盘缓存。非代码阻塞。
- **RES 基线梯全部 owner-gated（RES-01/03/04/05/06/07/09/10 等）。** 无业主显式 GO 不得启动。
  FF5 数据准入（上条）是其子阻塞。

## 已解除（历史，勿重复排查）

- ~~GitHub Actions 计费失败（2026-08-21）~~ → 09-01 解冻；deploy-pages/refresh-terminal-data
  两 workflow 保持 disabled_manually：refresh 已被轮 89 本地通道**按设计退役**（workflow_dispatch
  保留作断线兜底），Pages 发布由 publish-site.yml（push main 触碰 web/**）承担。
- ~~BLS CPI/NFP live transport~~ → AUD-05C-C1 COMPLETE（fail-closed，无 BLS adapter）。
- ~~PRAW wrapper~~ → AUD-05C-C3 owner 授权 7-gate COMPLETE。
- ~~模型 API ≥2s 规则范围~~ → AUD-05C-C5 业主裁决 Option A（数据源 ≥2s；模型 API 走 RPM/冷却）。
- ~~E3 inferential HOLD pending AUD-07B~~ → AUD-07B RESOLVED（ADR-010 Amendment）。
- ~~GBK 编码停摆（09-10/11）~~ → 轮 97 修复（PYTHONUTF8 注入+显式 encoding）。
- ~~strict-JSON NaN 上线（09-11）~~ → 轮 98 三层修复。
- ~~三晚契约门自锁（09-16/17/18）~~ → 92b088cbf 漂移免疫修钉 + da15bb70d 恢复推送（轮 99）。
- ~~form_ipo walk_cap / macro_drivers 部分缓存 CI 病理（09-04）~~ → 轮 83 修复+回归钉。
