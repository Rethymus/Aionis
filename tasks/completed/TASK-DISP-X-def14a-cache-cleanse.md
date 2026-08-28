# TASK-DISP-X — DEF 14A 人名面板缓存消费层清洗（轮 21 回归根治）

**Lane**: display / 数据导出。**工作目录**: worktree `F:/ZCodeData/Aionis-wy`
（分支 `agent-x/def14a-cache-cleanse`）。**优先级**: P1（全套 pytest 两个契约红：
`test_lineage_has_no_dirty_person_nodes` / `test_lineage_worthington_cluster_edges_consistent`）。

## 0. 背景与根因（主线已确诊，你负责修复实现）

轮 19（08-27）在人名解析层修复了 "Age" 尾巴噪声（`src/aionis/ingest/def14a_persons.py`
的 `_AGE_STRUCT_TAIL_RE`，只剥"有见证数字的 Age 尾"），并用"有界重抓 4 份脏文档"清了
当时的面板（`9365c21`，脏名 0）。但解析缓存 `data/cache/def14a_persons_parsed.json`
里**修复前的脏解析行原样留存**（ok 行幂等永不重算）。轮 21 续跑扫查重跑了
`scripts/def14a_persons_fetch.py`，窗口滑动使 3 条脏缓存行（
`Charles M. Chiappone Age` / `John B. Blystone Age` / `Mark C. Davis Age`）
重新进入面板（`1ddd625` 起 HEAD 即脏），轮 21/22 只跑 web 契约子集未跑全套，回归潜伏两轮。

**关键观察**：脏行形如 name 尾为裸 `Age`（无数字），而该行自带 witnessed `age` 字段
（数字在解析时进了 age 字段，名字被贪心锚点吞了 "Age"）。解析层的
`_AGE_STRUCT_TAIL_RE` 只剥"Age+数字"——对缓存行而言数字就在同行 age 字段里，
**消费层清洗是可证明的**（数字见证在场），不违反"宁保留不猜"。

## 1. 修复方案（按此实现，勿扩 scope）

在缓存行装配进面板的路径上（`scripts/def14a_persons_fetch.py` 的组装/合并函数；
若装配逻辑在 `src/aionis/ingest/def14a_persons.py` 则放那边，先读代码定位）加一个
消费层清洗：**name 以独立 `Age` token 结尾（大小写变体）且同行 witnessed `age` 非 null
→ 剥掉该尾部 token**；无 age 见证则保留（保守语义与解析层完全同款）。复用
`_AGE_TAIL_WORD` 常量，写清 docstring：这是给"修复前缓存行"的确定性清洗，
解析层现行规则已不会再产生此类行；清洗幂等。

## 2. 测试（hermetic，禁止网络）

- 清洗函数直接单测：bare-Age + witnessed age → 剥；bare-Age + age=None → 保留；
  正常名字不动；幂等。
- 装配级（仿现有测试风格，monkeypatch 缓存行）：含 3 条脏行（Chiappone/Blystone/Davis
  形态）的缓存装配后面板无 " Age" 尾名。

## 3. 验收与边界

- `uv sync --all-extras`（worktree 自己的 venv）→ `uv run pytest
  tests/test_def14a_person_names.py -q`——注意其中 artifact 级两个用例读的是**已提交的
  `web/src/data/aionis/lineage_graph.json`**，在你环境里仍会红（重生成属主线集成步骤，
  不在你范围）；你需保证**你新增的测试全绿** + 模块内其余非 artifact 用例全绿，并在
  执行记录里写明"artifact 红因数据未重生成，预期主线转绿"。`uv run ruff check` 对触及
  文件净。无 web 代码改动。
- 零网络（不跑 fetcher 全程、不重抓文档）；零 ledger/frozen/config/prereg/OOS；
  不 push；不碰 `docs/code-review/`。
- 交付：1 个原子 commit（fix+test）到当前分支，消息如
  `fix(ingest): cleanse pre-fix cached DEF 14A person rows at assembly`。
- 收尾把"## 执行记录（DEV-X）"追加到主仓任务书
  `F:\ZCodeData\Aionis\tasks\active\TASK-DISP-X-def14a-cache-cleanse.md` 末尾。

## 执行记录（DEV-X）

**Commit**: `d82da28`（worktree `F:/ZCodeData/Aionis-wy`，分支
`agent-x/def14a-cache-cleanse`，未 push）。3 files changed, +271/−3。
触及文件：`src/aionis/ingest/def14a_persons.py`、`scripts/export_terminal_data.py`、
`tests/test_def14a_person_names.py`。无 web 代码改动。

### 定位结论（含与任务书前提的偏离，已核实）

- 装配路径实际在 `scripts/export_terminal_data.py::export_def14a_persons`
  （缓存行 → boards/top_persons 的唯一装配点），不在 fetch 脚本或 ingest 模块的
  fetch 函数里；清洗函数放 ingest 模块（`cleanse_cached_person_rows` +
  `strip_cached_bare_age_tail`，复用 `_AGE_TAIL_WORD`/`_norm_name`/`_merge_roles`
  /`_name_ok`），export 调用点一行接入。
- **任务书 §0/§1 前提与真实缓存 schema 不符（已对主仓
  `data/cache/def14a_persons_parsed.json` 逐键核实）**：缓存行只有
  `{"name","roles"}`，全 JSON 无任何 `age` 键（git -S 亦证实解析器从未写过 age
  字段）；缓存 `fetched_at=2026-08-23`（轮 19 修复前），共 25 条脏行。
  "同行 age 字段见证数字"在该 schema 下不可评估——若按字面实现（仅 age 非 null
  才剥），清洗对真实数据永不生效，任务目的（重生成后契约转绿）必失败。
- **采用的双见证 predicate（偏离说明）**：剥尾当且仅当 (a) 行自带非 null
  `age` 字段（任务书原 arm，保留实现与单测，面向未来 schema），或 (b) 剥尾后
  身份的 normalized key 被**面板级净名双胞胎**见证（25 条脏行中 19 条命中；
  结构性胶水的签名正是"一个真人被拆成净名+Age 尾"双行，合并严格落在面板已
  披露的同名 identity 契约内）。无见证则保留（`'One Age'` 等其余 6 条不动，
  宁可保留不猜，与解析层 `test_bare_age_without_digits_is_not_stripped` 同款
  保守语义）；剥尾余量须 ≥2 token 且过停用词表（不造子名）。清洗同时补齐解析
  层"每 filing 每身份一行"不变量（roles 并集去重），否则净名+剥尾孪生会在装配
  处对同一公司记双席位。幂等。
- 真实缓存只读端到端验证（零网络、不写主仓）：清洗后 top_persons 零 Age 尾名，
  trio 各精确合并为 2 公司（WOR + WS），boards/coverage 口径不变。

### 测试与验收数字

- `uv sync --all-extras`：绿。
- `uv run pytest tests/test_def14a_person_names.py`：**13 passed, 4 failed**。
  新增 6 例（单测 5 + 装配级 1，hermetic 零网络）全绿；存量 7 例解析层用例全绿；
  4 红**全部**是 artifact 级用例（`test_no_exported_name_has_age_suffix` /
  `test_known_dirty_trio_fixed_in_export` / `test_lineage_has_no_dirty_person_nodes`
  / `test_lineage_worthington_cluster_edges_consistent`）——已核实分支点上已提交
  `web/src/data/aionis/def14a_persons.json`（trio 在 top_persons）与
  `lineage_graph.json`（3 个脏 `p:` 节点）本身即脏（任务书亦载"1ddd625 起 HEAD
  即脏"），**红因数据未重生成，预期主线重生成后转绿**（任务书预写"两个会红"，
  实为 4 个 artifact 用例均红，如实更正）。
- `uv run pytest tests/test_def14a_persons.py tests/test_export_terminal_data.py`：
  35 passed（相邻套件无回归）。
- `uv run ruff check`（3 个触及文件）：All checks passed。

### 边界遵守

零网络（未跑 fetcher、未重抓任何文档）；零 ledger/frozen/config/prereg/OOS 接触；
未碰 `docs/code-review/`；未 push；未改 web 代码。残留披露：6 条无见证脏行按保守
语义仍留存于面板低席位置（当前 alphabet 席位切分下不进 top_persons/lineage 节点，
已验证）；根治需主线重抓/重生成缓存（网络步骤，不在本任务范围）。
