# NIGHT-WAVE-A — 低推理 Codex 无人值守 Goal Prompt

将本文件从“BEGIN PROMPT”到“END PROMPT”完整复制为下一次 Codex Goal 模式的用户提示。

---

## BEGIN PROMPT

你在 `/home/re/code/Aionis` 工作。执行一个无人值守、低推理、机械性高的夜间开发 Goal。

### AUTHORIZATION

本提示即 owner 对以下**唯一范围**的实现授权：

1. 完成现有 AUD-05C C1/C2 的独立 Verifier → Reviewer gate；只修复实际 blocking findings。
2. 实现并完成 AUD-05C C3（PRAW 每请求 shared host-spacing hook）及独立 gates。
3. 实现并完成 RD-04、RD-05、RD-06、RD-07、RD-09、RD-10、RD-12。
4. 对通过 gates 的工作创建原子 Conventional Commits；最终验证通过后，允许 fast-forward push
   `HEAD:main`。禁止 force push；远端发生分叉时保留本地 commits 并停止 push。

这不是对 C5、AUD-06、AUD-07B、E3、RD-08、RD-11、RD-13..17、RES-01..10、真实模型/数据/
trial/结果运行的授权。

### EXACT SUCCESS PREDICATE

只有同时满足以下条件，Goal 才能标记 complete：

- C1、C2、C3 均有独立 Verifier `PASS` 和 Reviewer `APPROVE`；
- RD-04/05/06/07/09/10/12 均满足各自任务文件全部 acceptance、独立 `PASS` + `APPROVE`；
- 没有 placeholder、TODO、stub、skip、未实现分支或未解释 warning；
- 最终 `uv run --offline pytest -q`、`uv run --offline ruff check`、`git diff --check` 通过；
- 本 Goal 未修改 frozen prereg/ADR/config、`runs/ledger.jsonl`、`runs/results/**`、`runs/forward/**`、
  `data/**`，未查看 E3 outcome，未运行 phase/strategy/horizon/forward 或真实 network/LLM；
- 每个完成任务的 task/state/handoff 与真实 diff、命令输出一致；
- 仅 reviewer-approved commits 被创建；远程 push 若执行必须是 fast-forward。

某任务真实 BLOCKED 时，不伪造 complete：记录 blocker，继续所有不依赖它的授权任务。最终只有全部
success predicate 成立才 complete；否则返回 blocked/partial 矩阵。

### NON-COUNTING OUTCOMES

以下均不算完成：

- 只有计划、总结或“看起来正确”，没有代码与测试证据；
- Engineer 自己充当同一 diff 的独立 Verifier/Reviewer；
- 为了推进而改变 task 公式、schema、文件白名单、测试 oracle 或 owner gate；
- C3 只在 subreddit 循环前 wait，而未覆盖 token/oauth/pagination 的每个 PRAW HTTP request；
- 将 `temperature=0` 写成远程 API bit-deterministic；
- 把 588 union pool 当作每月 S&P 500 membership；
- 把 raw monthly macro/FF 值当作有截面变化的股票信号；
- 把 cross-fit 称作 chronological OOS，或把 evaluator 测试通过称作 alpha；
- 运行真实 API/数据/研究脚本，写 ledger/result，修改 frozen surface，或查看 E3 outcome；
- 为耗满夜间时间而扩大范围、重构无关模块、增加依赖或新增研究自由度。

### LOCKED / EDITABLE / HUMAN-CONTROLLED SURFACES

- Locked：AGENTS.md/CLAUDE.md、WORKFLOW.md、任务 acceptance、现有测试 oracle、frozen prereg/ADR/config、
  ledger/results/data/forward、研究指标定义。
- Editable：每个当前 task 的“允许修改”白名单；state/current.md、state/handoff.md 与该 task evidence。
- Append/update-only evidence：task 的 Engineer/Verifier/Reviewer evidence 与 handoff checkpoint；不得改写
  失败历史为成功。
- Human-controlled and excluded：C5、统计公式、数据/模型许可、真实 API 花费、trial config commit、
  E3 launch/outcome、force push、远端分叉处理。

### STARTUP — ONCE ONLY

1. 读取 `AGENTS.md`、`state/current.md`、`state/handoff.md`、本 Goal prompt。
2. `git status --short --branch`；保留当前 C1/C2 与规划文档改动，禁止 reset/checkout/revert 用户工作。
3. 运行一次基线：`uv run --offline pytest -q -x` 与 `uv run --offline ruff check`。
4. 建立 compact queue，禁止再次通读整个仓库、全部 active tasks 或全部历史报告。
5. 在 `state/handoff.md` 维护一个不超过 35 行的 `overnight checkpoint`：
   `Goal / Current task / Completed gates / Files changed / Last tests / Blockers / Next exact action`。

若发现额外 dirty 文件：不修改、不删除。仅在它与当前 task 白名单重叠时将该 task 标 BLOCKED；否则继续。

### FIXED EXECUTION ORDER

#### Group A — transport closure

1. C1 independent Verifier（只读）与 C2 independent Verifier（只读）可最多 2 个并行 agent。
2. 对 PASS 的 C1/C2 分别派发新上下文 Reviewer；Reviewer 只读 task、diff、测试证据和相关代码。
3. 若 REQUEST CHANGES，单独 Engineer 只修 blocking item；最多 2 轮，然后 BLOCKED。
4. C3 Engineer：严格按 `TASK-AUD-05C-C3-praw-wrapper-7gate.md`：
   - 通过 `praw.Reddit(requestor_class=...)` 注入自定义 `prawcore.Requestor`；
   - 在 overridden `request()` 中从真实 request URL 预占 shared host-spacing slot，再调用 `super()`；
   - 覆盖 token host、oauth host、同 host 连续请求与多个 pagination request；
   - PRAW 保留 retry/rate-limit；保留 subreddit 1.5s、cache、ledger、forward-only 语义；
   - 只用 fake clock/fake HTTP，绝不调用 Reddit。
5. C3 新上下文 Verifier，再新上下文 Reviewer；最多 2 轮修复。
6. Group A 全部 APPROVE 后跑 full pytest/ruff/frozen diff；通过才可提交 Group A。

#### Group B — deterministic LLM-eval foundation

顺序：RD-04 → RD-05；RD-04 APPROVE 后 RD-06 → RD-07。

- 每次只读当前 task 文件、task 指定的已有 schema/模块和直接相关 tests。
- RD-04/05/06 中所有字段、公式、canonicalization、零分母与 abstain 语义以 task 文件为准，禁止改造。
- RD-07 只报告 cached/offline metadata，禁止模型调用和 ledger 写入。
- 每个 Engineer 完成 targeted tests + scoped ruff；然后新上下文 Verifier、再 Reviewer。
- Group B 全部 APPROVE 后才跑一次 full pytest/ruff 并提交。

#### Group C — deterministic quant/PIT kernels

RD-09、RD-10、RD-12 文件不重叠，可最多两个 Engineer 并行，但每个独立 gates 串行完成。

- RD-09：严格使用 drift-adjusted pre-trade weights、traded notional 与显式 bps scenario；不实现 borrow、
  capacity、delisting、buffer band 或真实成本估计。
- RD-10：逐字实现 task 内 close/return/window/ddof/min-periods/NaN 公式；不获取数据、不创建 config/runner。
- RD-12：只用 synthetic membership；明确 union pool != contemporaneous membership；freshness threshold
  若 task 未给定则只报告 age，不自行决定 owner threshold。
- Group C 全部 APPROVE 后跑 full pytest/ruff 并提交。

#### Final integration

1. 更新 task status/evidence、state/current.md、state/handoff.md；不得声称未通过项完成。
2. 运行最终 compact gates：
   - `uv run --offline pytest -q`
   - `uv run --offline ruff check`
   - `git diff --check`
   - frozen/ledger/results/data/forward diff 必须为空
   - secret/data scan；不得 stage `.env`、`data/**`、`*.parquet`
3. 每次 commit 前使用**显式文件列表** `git add <files>`；禁止 `git add .`、`git add -A`、`git add -f`。
4. `git diff --cached --check` 并审查 `git diff --cached --name-only`；只提交当前 approved group。
5. 建议 commits：
   - `fix(ingest): close remaining transport policy gaps`
   - `feat(extraction): add deterministic evaluation foundations`
   - `feat(research): add offline cost momentum and universe oracles`
   - 必要的规划/state 文档放入与其真实状态一致的最近 commit，不单独虚构完成。
6. 最终 `git fetch origin`；只有 `origin/main` 是本地 HEAD 的祖先且工作树无未审改动时，
   `git push origin HEAD:main`。否则不 rebase/merge/force，记录 blocker。

### AGENT TOPOLOGY AND CONTEXT BUDGET

- 根 agent 只做 Orchestrator：维护 queue、文件边界、gates、commits、handoff；不要亲自写大段实现。
- 最多 2 个并发 subagents（加 root 共 3），避免代理故障和 token 放大。
- 每个 subagent 使用 fresh/最小上下文（优先 `fork_turns="none"`），只给：角色、一个 task 路径、
  state checkpoint、允许文件、测试命令、输出格式。禁止传完整聊天、全部 roadmap 或整个仓库。
- Engineer 输出最多 30 行：`files / implementation / tests / risks / next gate`。
- Verifier 输出最多 25 行：`PASS|FAIL|BLOCKED / acceptance evidence / commands / blocker`。
- Reviewer 输出最多 25 行：`APPROVE|REQUEST CHANGES|BLOCKED / blocking findings / advisory`。
- 工具检索优先 `rg`、限定 `sed` 行区间；不要打印完整大文件、完整 pytest 日志或重复 diff。
- pytest 默认 `-q`；失败时只重跑首个失败文件/测试并保留必要 traceback。修复后再跑 targeted，不反复跑
  full suite；full suite 仅 startup、Group A、Group B、Group C/final（相邻时可合并）。
- 一个 task 完成后立即把关键事实写入 task evidence + 35 行 checkpoint，然后从上下文丢弃旧工具输出。
- 出现重复阅读、遗忘文件、混淆 task 或上下文接近 70% 时，在 task 边界做 anchored compaction，只保留：
  Goal、完成矩阵、文件/commits、测试、blockers、下一动作。压缩后用 AGENTS + 当前 task + checkpoint 重启，
  不重新加载旧聊天或完整报告。
- 不使用 web；所需 PRAW/LightGBM/schema 事实已在本地 task/code 中冻结。缺少事实时 BLOCKED，不搜索扩题。

### FAILURE / RECOVERY POLICY

- 同一 blocking failure 最多 2 个修复轮次；第 3 次标 BLOCKED，记录实际错误与最后命令，继续独立任务。
- agent/proxy 503：记录一次，改为单 agent 或 root 完成机械调度；不重复无限 spawn。
- 测试环境/依赖缺失：先用 `uv run --offline` 验证；需要联网安装则 BLOCKED，不联网。
- 发现 frozen/ledger/result/data/forward 变更：立即停止该 task，不提交，记录精确 diff；不得用 destructive
  reset 清除用户改动。
- 不确定任务含义、公式或 schema：不得推理补全，标 BLOCKED；继续无依赖任务。
- 无需等待用户夜间回复。只在所有授权队列处理完、真实 blocker 已记录或成功谓词成立后返回。

### FINAL REPORT CONTRACT

最终只返回：

1. `COMPLETE` 或 `PARTIAL/BLOCKED`；
2. C1/C2/C3/RD-04/05/06/07/09/10/12 完成矩阵与 Verifier/Reviewer verdict；
3. commits 与是否 push main；
4. 最终 pytest/ruff/diff/frozen/secret 证据；
5. 未完成项的精确 blocker 和下一条安全动作；
6. 明确声明未运行真实 network/LLM/research/forward、未查看 E3 outcome、未修改 ledger/results/data/frozen。

不要返回过程叙事、长日志、泛化建议或新的研究方向。

## END PROMPT
