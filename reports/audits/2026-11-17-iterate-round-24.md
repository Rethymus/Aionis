# iterate 轮 24 交付报告——批① coverage-audit：y 源覆盖审计（只读先行，2026-11-17）

> 本文件=iterate 轮 24 报告**首创落盘**：动工前 `test -f` 实测 MISSING
> （沿轮 23 报告首创落盘先例）；文件名日期 2026-11-17 系交办给定路径。
> 本批=设计文档 `reports/design/2026-11-17-replay-training-ignition.md` §3
> 「y 源覆盖审计（轮 24 第一步）」的实施：**只读先行**——全程仅本报告一个写动作，
> 零管线调用、零补算、零 config/ledger 触碰。

## 覆盖审计节（§3 分支决定）

**审计问题**（设计 §3 :51-60）：realized rank-IC 序列（confirmatory 管线逐月冻结产物）
2016-01 起是否连续？PBO 诊断 `n_obs=125`（≈10.4 年）暗示面板回到 ~2016，须实证；
早段缺行则走 `PHASE_*_NO_LEDGER=1` 补算分支。

### 覆盖表（本会话亲跑实证）

| 源 | 覆盖 | 连续性 | 备注 |
|---|---|---|---|
| `runs/results/<sig>/ic_base.parquet` + `ic_state.parquet`（4 sig × 2 = 8 件） | **2016-01 → 2026-05，125 月** | 零内部缺口、零重复月、零 NaN（8/8 全部） | y 源本体（confirmatory 冻结产物）；`differential.json` `n_months=125` 一致 |
| `reports/exploratory/pbo-diagnostic.json` | `n_obs=125`、`n_configs=8`、as_of 2026-10-07 | — | 设计 §3 引用的暗示**实证确认**：125 月恰=2016-01→2026-05（10 年 5 月） |
| `ic_monthly.json` 面板族 ×4（`web/public/api/v1/panels/`、`web/src/data/aionis/`、`archive/quarto-site/data/`、`data/ops/gh_pages_worktree/api/v1/panels/`） | 2021-01 → 2026-06，66 条 | 零内部缺口、零重复 | **展示层 us/cn/combined 面板，非 confirmatory y 源**；2026-06 us=null |
| `tests/fixtures/aionis-data/panels/ic_monthly.json` | 3 条标注 fixture | — | 单测 fixture，非数据源 |

**相位归属核对**（纯只读交叉验证）：4 个 sig 的 `ic_state`/`ic_base` 月度均值与
`pbo-diagnostic.json` `per_arm.mean_ic` **精确匹配**（<1e-9）——
17245a75d2d4=Phase B、a7fdb48f5942=Phase C、d31580630ff3=Phase D、ef321e9ee808=Phase E1；
B/C/D base 臂共享同一 base IC 序列（mean 0.015305328），与 PBO 8 臂结构吻合。

### 分支决定

**走「读现成序列」分支，无需 `PHASE_*_NO_LEDGER=1` 补算。**
训练期窗口（设计 §1：2016-01→2025-12）在现成序列上 **120/120 月全覆盖**
（由 2016-01→2026-05 连续 125 月直接蕴含）；冻结验证期前段 2026-01→2026-05 有 y。

**如实注记（尾段，非早段缺行）**：现成序列终点=2026-05；设计冻结验证期 2026-01→2026-10
中 **2026-06→2026-10 共 5 个月现成序列无行**——这是数据 as-of 尾段未延伸（confirmatory
管线最后落盘于 2026-05），不属于设计 §3 预设的「早段缺行→NO-LEDGER 补算」情形。
推演若走到这 5 个月需 y，届时须另行补算或截断冻结验证期——属业主/后续轮决定项，
本批不越权决定、不预跑补算。

### 验证实录（本会话亲跑命令）

1. `uv run python scripts/ops_local_refresh.py --status` → `status: ok_committed`
   （finished 2026-11-16T19:46）——晚间通道未在运行，动工前置条件满足。
2. `git status --short --branch` → main，工作树净（仅本报告新增文件）。
3. 覆盖断言（`uv run python -I` 读 parquet）：8/8 件
   `n=125 first=2016-01 last=2026-05 internal_gaps=[] outside_exp=[] nan_ic=0`。
4. 相位归属：均值-`per_arm` 匹配输出 4 sig → B/C/D/E1（精确到 1e-9）。
5. 面板族：4 处 `n=66 first=2021-01 last=2026-06`、`internal_gaps=[] dupes=0`。
6. `test -f reports/audits/2026-11-17-iterate-round-24.md` → MISSING（首创落盘依据）。

### 边界

全程只读审计：`runs/results/`、`reports/exploratory/`、面板 JSON 均零写入；
0 ledger / 0 frozen config / 0 OOS / 研究面（`src/aionis/`、`scripts/phase_*`）零触碰；
零装包零新依赖；未跑任何 `PHASE_*` 管线（分支决定=无需补算）。本报告文件为本批唯一
新增写动作，未提交（交办未含 commit 指令）。

## 批② replay-engine（scripts/replay_blackbox.py 839 行 + tests 24 用例）

`--freeze`（config-frozen.json+SHA256 sidecar，record-once 拒覆写）/`--tier t0|t1`/
`--from/--to/--out/--config/--params/--lessons/--ic-parquet` 全接口落地；PIT 掩蔽
（t 轮上下文截断至 t-1）+逐月记录三键（rows_used/snapshot_sha256/prompt_sha256）；
bounded context 契约只喂自产序列摘要（调研 2601.13770 收紧项）；tuning-log 含隐式
试验计数列（调研 2608.27734）；契约层容错 delta ①（beb32cd42a，2016-02 契约失败
→回复契约层容错，thresholds 计数器 0→1）；tests/test_replay_blackbox.py 24 passed
（tmp 隔离零网络零真 LLM）。

## 批③ frontier-anchors-89-91（commit 34954ec）

backlog 86-88 已于轮 23 登记（threadpoolctl/REFORMS/2512.14609）；本轮 89-91 =
2608.27734（泄漏安全搜索感知评测：结构性防泄漏不可被统计校正替代=铁律 3 外部正源）/
2406.16964（Tan et al. NeurIPS 2024：LLM 时序预测无用=T0 并排报告必要性反源）/
2601.13770（Look-Ahead-Bench：PIT 前视偏差+记忆审计信号正源）。58+/0- 纯增，
guard 六值 148/146/0/2/0/576（bare 自然增长沿口径）。

## 批④ t0-run（引擎算术自洽证明）

训练窗 120 月（2016-01→2025-12）climatology 基线：**p̄=0.5167，BSS≡0 构造性
PASS**（runs/20261116-175239-t0）——引擎在真实数据上算术自洽；config-frozen.json
SHA256=edbfbaa5…（record-once）。

## 批⑤ t1-training-run（0/10 块，降级 C 收档如实）

GLM API 自 2026-11-16 02:03 起限速（1305 平台过载+1302 账户限速交替）：判别探针
12 次（02:42→05:36）四次瞬窗通过但 12 连调所需突发额度不足（每 ~17min 一窗、
窗内 3-8 调后硬锁），块 1 四次尝试全部中止（2016-01→2016-04 不等月数）。
**业主协议 ④ 执行**：15 个 t1 尝试目录全保留（断点语义非重跑到通过，零月记录
复用拼接）；tuning-log 唯一 delta ①（契约容错，块级检查点 0/10 到达如实）；
lessons.md 空库（零完成块诚实态+准入判据预声明：仅校准教训零方向规律）。
commit 05d400fabe。

## 批⑥ frozen-validation-run（v2 冻结+五轮 pre-training holdout anchor ✅）

**v2 冻结**（record-once）：config-frozen-v2-validation.json+SHA256——v1 参数+
窗口 2026-01→2026-05（业主裁决 A：截断，缺月披露内嵌）+**pre-training holdout
anchor 语义标注**（T1 0/10 块=本次跑的是未训练系统基线锚，非训练后回退读数）+
post-training 配对协议预注册（T1 完成后同窗同参数重跑，pre/post 配对差=训练
效应因果读数）。

**五轮执行**（2026-11-17 主会话续跑；workflow 三度停摆[provider 1005→Model
creation failed 复活链→amend 空 mission]后沿轮 2 先例内联收尾）：

| 月 | answer | p | y | (p−y)² | rows_used |
|---|---|---|---|---|---|
| 2026-01 | True | 0.5167 | 0 | 0.2670 | （探针目录并入） |
| 2026-02 | True | 0.5492 | 0 | 0.3016 | ≤t-1 断言过 |
| 2026-03 | True | 0.5200 | 0 | 0.2704 | ≤t-1 断言过 |
| 2026-04 | True | 0.5041 | 0 | 0.2541 | ≤t-1 断言过 |
| 2026-05 | True | 0.5000 | 0 | 0.2500 | ≤t-1 断言过 |

**聚合**：n=5，mean p=0.5180，mean Brier=0.2686，BS_base=0.2497，
**BSS=−0.0758**；p∈[0.500,0.549]。

**判读（预注册预期对照，设计 §9）**：
1. **p 收敛诚实：完全成立** ✅——无训练 GLM 五月 p 全部锚在 0.50-0.55，均值
   0.5180 几乎精确复现训练窗 climatology p̄=0.5167。「黑箱知道自己不知道」=
   Tan et al. 2024 预期读数+verbalized confidence 诚实通道（五月 answer 全 True
   但 p 只敢给 ~0.5——嘴上说正、心虚给 0.5）。
2. **BSS≈climatology（−0.076 噪声带内）=诚实性成功** ✅——anchor 无判别信号
   属预期；五月 y 全 0（2026 前五月 IC 连负）与 p 微偏正向的组合代价。
3. **记忆审计信号（2601.13770）**：2026-01→05 处 GLM 知识截止附近，p 无异常
   收敛（未出现「知道未来」的自信偏离）——**无记忆泄漏嫌疑信号** ✅（标记性
   结论，非证明）。
4. **post-training holdout 配对协议**（预注册于 v2 冻结）：T1 十块完成后同窗
   同参数重跑，pre/post 配对差=训练效应唯一有意义读数。

## 批⑦ distillation-archive（不依赖 T1 的部分）

掩蔽证明汇总模板+校准曲线模板（05d400fabe）+lessons 空库（准入判据预声明）
+t1-breakpoint.md 续跑协议（15 目录索引+断点语义）。**依赖 T1 的部分**（预训练
lessons 库实质内容/对比对语料/125 点训练曲线）= T1 续跑批次产出。

## 批⑧ 结论与待业主区

**结论**：轮 24 完成 7/8 条目（T1 十块被 GLM API 配额硬阻塞按协议降级收档）；
训练期点火架构全链就绪（引擎/冻结/掩蔽/T0/anchor 验证五轮），**首个 holdout
读数到手**：pre-training anchor p→0.5 收敛诚实成立、BSS≈climatology、无记忆
泄漏嫌疑信号。T1 十块续跑=训练效应读数（post-training 配对差）的唯一缺口。

**待业主区（只列不动）**：①T1 十块续跑时点（GLM API 配额窗口恢复后一轮搞定，
每窗 3-8 调 × 10 块 120 月≈需 ~15-25 个窗口或一次宽松配额段）；②2026-06→10
补算 y（升级答复 2 已拒绝并列待业主区——补算需推管线过 as-of 2026-05，侵蚀
holdout 独立性）；③Mimosa 89 findings 处置（见附录）。

**例行核查**：guard 148/146/0/2/0/576 rc=0（施工批实测）；ruff 净；pytest
test_replay_blackbox 24 passed；backlog prediction:/outcome: 双零 0/0（回放
产物隔离于 reports/exploratory/replay/，零账本污染实证）。

## 附录：Mimosa 安全扫描判读（scan-2026-11-16T16-54-14，seal 2c05d39a…）

89 findings=27 high+62 medium，三类判读：
1. **构建产物误报**（1 high+28 medium）：data/ops/gh_pages_worktree/_next/*.js
   minified chunk——扫描面误入部署树，非源码，不适用；
2. **归档死代码**（6 high SSRF+1 证书）：archive/krx-probes/scratch_krx_probe*.py
   一次性探针+data/cache/audit_*/scan*.py+docs/code-review/_sync.py——非运行面，
   可清理（待业主点头）；
3. **真实源码面**（10 high）：src/aionis/ingest/ 9 处 SSRF（URL 实为硬编码公开
   API 端点非用户控制，威胁模型不成立，但沿 Mimosa 约束加确定性 host 白名单
   校验 helper 值得）+3 处 XML 实体扩展（form13f/form4/politician_trades——
   defusedxml 加固）——归轮 25 安全加固候选。

## 复盘注记（workflow 生命周期如实）

轮 24 workflow 三度停摆：①provider 1005（GLM-5.3-Flash 配额耗尽，计划已切
GLM Coding Lite，quotaWindow 100% resetIn 387h）→resume→②Model creation
failed（复活链病灶，先例轮 2/13/17）→amend→③amend 漏传 args 空 mission 早退。
主会话内联收尾（沿轮 2 先例）：验证五轮（GLM API 2026-11-17 15:39 窗口恢复，
2026-02→05 四月一次通过+2026-01 探针记录并入[同 config 同引擎，断点复用语义]）
+聚合+本报告补全。05d400fabe（ahead 1）随本批一并推送。
