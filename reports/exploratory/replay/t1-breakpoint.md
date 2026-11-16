<!-- EXPLORATORY REPLAY — not a claim, not a gate (design: reports/design/2026-11-17-replay-training-ignition.md; zero runs/ledger.jsonl writes; research face untouched) -->

# T1 断点记录（t1-training-run 批，2026-11-17 02:40 收档）

## 完成面

- **T0 伴生件（本批内完成）**：`runs/20261116-175239-t0/`——训练窗 2016-01→2025-12
  120 月，恒 p̄=0.5167（62? 见 jsonl），BSS≡0 构造断言 PASS exit 0 零 LLM。
  （注：p̄=0.5167 为引擎输出；62/120=0.5167 ✓）——供 T1 并排报告的 T0 基准。
- **前置批（上一批）**：T0 全实际覆盖窗 125 月（runs/20261116-173833-t0）已提交 ae6f6128b3。

## 受阻面：T1 训练期 2016-01→2025-12 逐月推演——0/10 块完成，零月回答

GLM（glm-4.7-flash，冻结 config provider 钉定）持续不可用，10 次尝试全部中止于
月 1（留档 10 个 header-only 断点目录 runs/20261116-*t1/，manifest 未生成=诚实断点）：

| 时点(本地) | 错误 |
|---|---|
| 02:03:36 | 429 code 1305 平台过载（「该模型当前访问量过大」） |
| 02:04:17 | 429 code 1305 |
| 02:07:43 | Request timed out（240s 客户端超时） |
| 02:08:09→02:18→02:24→02:27→02:34→02:36（后台驱动 12 次计划，5 次实跑后业主向升级前人工停止） | 1305 / 1302「您的账户已达到速率限制」/ timeout 交替 |

**判别探针（一手实测）**：glm-4.7-flash 最小探针 5 次 4 失败 1 瞬通（02:02:36 OK，
其后 02:07/02:12/02:17/02:38 全败）；**siliconflow 探针 OK 1.4s 契约完美**
（Qwen2.5-7B-Instruct，独立配额池）；modelscope 403「complete your profile」账户
资料问题不可用。fox_stats 账本：quotaWindow usedPct=**100%**（snapshot 16:56Z
stale）、today total=70.8M tokens/384 requests——GLM 侧限速与业主自身会话额度共享池。

## 处置：按交办预案「如实记录断点续跑，绝不重跑到通过」收档升级业主

- 冻结 config **零改动**（provider=glm/model/窗口/切点全原样）——恢复后**无需 re-freeze**。
- tuning-log.md 零 delta 零检查点条目（检查点从块 1 完成才开始，未到达）；lessons 零蒸馏。
- **续跑协议**：GLM 恢复后逐块串行 `--tier t1 --from Y-01 --to Y-12`（2016→2025 十块），
  块间检查点（调参 delta 或无-delta 观察）落 tuning-log.md，lessons 跨块注入；
  断点目录 10 个保留为诚实证据，不删除不复用。
- 业主可决项：等配额窗口重置后本批内续跑 / 授权临时切换 provider（siliconflow 现可用、
  独立配额，但冻结 config 钉 glm=设计 T1=GLM，切换须业主点头+新 freeze 或披露式覆盖）/
  延后至后续批次。
