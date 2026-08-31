# TASK-DISP-T — Southpoint/Citrone 准入（规格 §2-4 裁决 + MANAGERS +1 落地）

**Lane**: display / data（13F 生态）。**优先级**: P1（证据已齐，唯一待办的准入门）。
**工作目录**: worktree `F:\ZCodeData\Aionis-wt`（分支 `feat/southpoint-admission`）。
**前置**: 主仓缺口补跑（filing_stream 等 EFTS/www 车道）完成后才可开抓—— politeness 同主机隔离。

## 0. 背景与设计依据（设计已完成，本任务纯开发）

- 策展门槛规格：`reports/design/2026-08-26-stars-curation-bar.md`（闸门 G0-G5 + watch/出局语义）。
- 轮 2 证据：`reports/design/2026-08-27-stars-candidates-evidence-round2.md`——Southpoint 二壳
  CIK **0001319998** = `Southpoint Capital Advisors LP`，近 8 报告季 **8/8 连续 13F-HR**
  （壳级 PASS；accession 全链留档于 round2 JSON）。
- 轮 ⑲ 先例：全 PASS 候选由主线按规格 §2-4 代裁采纳（GAMCO/Corvex 同款流程）。
- 当前明星数 **42**；准入成功 → 43，首页统计条自动跟随。

## 1. 主线预裁决记录（按 §2-4，agent 复核后执行）

- **G0 身份**：`Southpoint Capital Advisors LP`（DE），CIK 0001319998——轮 2 证据逐字符可核验。PASS。
- **G1 连续性**：8/8 季 13F-HR（2024-09-30…2026-06-30 全封闭窗）。PASS。
- **G2 规模/知名度双轨**：知名度轨——Rob Citrone 为长期公开市场评论人
  （Bloomberg/CNBC 常驻嘉宾，Citrone Research 创始人）；Southpoint 规模轨证据不足 $5B
  则以知名度轨 PASS（与 Corvex 同款判断口径）。agent 复核轮 1 证据文件中 Southpoint 条目，
  如实记录判定依据；若轮 1 证据与此冲突 → 停止并报告，不硬准入。
- **G3 分类**：`activist`（Citrone 以催化/activist 立场知名；若轮 1 证据表明偏 macro 则用 `macro`，
  二选一，拒绝 other 兜底，如证据不足则 STOP 报告）。
- **G4 中文名**：zh=`null`（Corvex 先例：medium 置信宁缺毋滥；Southpoint/Citrone 无仓内白名单
  中文译名出处）。
- **G5 去重**：仅入 LP 壳 0001319998；LLC 主壳（轮 1 的 NT-only 壳）不入，杜绝双壳双计。

## 2. 执行步骤

1. 读 `scripts/form13f_fetch.py` 的 `MANAGERS` 结构，**+1 行 verbatim**（照现有行格式：
   CIK/name/zh(null)/category），附一行注释指向 round2 证据文件。
2. 只拉新管理人的 13F 历史（礼貌 ≥2s，预计 ≤15 请求；幂等缓存命中则零请求）。
3. 跑该脚本的导出路径（form13f + form13f-stars 两个导出都要刷新）。
4. `uv run pytest -q tests/test_web_terminal_data.py tests/`（至少 web 契约 + 13f 相关测试全绿）。
5. commit：一笔原子（MANAGERS 行 + 导出 JSON 变更）。**不 push**。

## 3. 铁律

- 0 ledger/frozen/config/prereg/OOS；不碰 参照站；不 rm -rf；
  .env 不提交不外传；冻结面板 retain=设计（worktree 无研究面产物）。
- politeness：开工前必须得到主线"补跑完成"信号（任务派发即代表已给信号）。
- 若任一闸门证据不足：**宁可不准入**，报告 STOP 原因（诚实止损 = 合格交付）。

## 4. 报告

(a) §2-4 五闸门逐条判定与证据引用；(b) 抓取请求记账；(c) 测试结果；(d) commit hash；
(e) 明星数 42→43 的导出证据（form13f-stars.json manager 计数）；(f) 首页统计条预期变化说明。
