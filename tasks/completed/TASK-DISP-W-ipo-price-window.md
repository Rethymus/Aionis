# TASK-DISP-W — IPO 发行价有界走查的窗口滑动不变量修复（walker 裁剪）

**Lane**: display / 数据导出（display-lane 代码修复）。**工作目录**: worktree
`F:/ZCodeData/Aionis-wx`（分支 `agent-w/ipo-price-window`）。**优先级**: P0（主线契约闸门
`test_form_ipo_panel_contract` 当前红）。

## 0. 背景与根因（主线已确诊，你负责修复实现）

H3 有界走查（`scripts/form_ipo_price_parse.py`）维护
`data/cache/form_ipo_price_parsed.json`（per-accession 解析缓存），导出端
（`scripts/export_terminal_data.py::export_form_ipo`，约 L3760-3830）：

- `merge_offer_prices(filings, price_cache)` 对**全部可见行**合并价格（full-cache）；
- `conf["exact"]` 只统计**最新 ≤80 priced（424B4）目标窗口内**的缓存条目；
- 契约测试钉死 `conf["exact"] == offer_price_parsed`（tests/test_web_terminal_data.py:1290）。

**缺陷**：walker 从不裁剪已滑出目标窗口的缓存条目。轮 23 刷新后 priced 面板
219→227（新 424B4 进入窗口），5 个 exact 条目留在窗外 → 带价行 63 vs 窗口内 exact 58 →
不变量破裂，闸门正确拦截。实测缓存：79 行 = exact 63 / none 15 / FAIL 1。

## 1. 修复方案（按此实现，勿扩scope）

1. 在 `src/aionis/ingest/form_ipo_price.py` 新增纯函数
   `prune_price_cache_to_target(cache: dict, target_accessions: set[str]) -> dict`：
   仅保留 accession ∈ target 的条目（含 FAIL 条目——它们也属窗口状态），返回新 dict
   （不改传入对象语义自定，写清 docstring：窗口只进不退，滑出条目永不回窗，裁剪零信息
   损失且让缓存恒等于"当前有界走查状态"=披露口径）。
2. `scripts/form_ipo_price_parse.py` 在 `save_price_cache(...)` 前调用该函数（两个 save
   点都要：cap 提前退出路径 + 正常结束路径；`--max-requests 0` 干跑路径也裁剪——干跑
   本就声明 ledger 元数据不动，行级裁剪属缓存卫生）。
3. 导出端与合并函数**零改动**（single source of truth = 缓存即窗口）。

## 2. 测试（新增，hermetic，禁止网络）

- 裁剪函数：窗口外 exact/none/FAIL 条目全移除、窗口内全保留、空 target → 空缓存、
  幂等性。
- walker 级（仿既有 monkeypatch 模式）：含窗外条目的缓存经一轮走查后保存的缓存不含窗外
  条目。
- 存量全绿：`uv run pytest tests/test_form_ipo_price.py tests/test_form_ipo.py -q`。

## 3. 验收与边界

- `uv sync --all-extras`（worktree 自己的 venv）→ 上述测试 + 新测试全绿 +
  `uv run ruff check src/aionis/ingest/form_ipo_price.py scripts/form_ipo_price_parse.py tests/`
  净。无 web 改动，不需要 tsc/build。
- `test_form_ipo_panel_contract` 的转绿依赖主线在集成后重跑 walker + 重导出（数据态），
  **不在你范围**——不要试图修 JSON 或跑网络走查。
- 零 ledger/frozen/config/prereg/OOS；不改导出端/前端；不 push；不碰
  `docs/code-review/`。
- 交付：1-2 个原子 Conventional Commits（fix + test 可合一），分支
  `agent-w/ipo-price-window`。收尾在任务文件下方追加"执行记录"段（做了什么/测试数字/
  commit hash），不要改本任务书以上部分。

## 执行记录（DEV-W2，续作）

前任 W 已完成全部代码（本段不重复其内容，仅验收结论）：审阅 `git diff` 与 §1 逐条对齐——
`prune_price_cache_to_target()` 为纯函数、窗口内 FAIL 条目保留、返回新 dict 不改入参；
walker 两个落盘点（循环内 periodic + 循环后 final，cap 提前退出走 break→final）均改经
`_save()` 裁剪落盘；`--max-requests 0` 干跑路径同样裁剪且 `_run_meta()` 在 dry 模式返回
未改动的 `saved_meta`；导出端/`merge_offer_prices`/前端零改动。未发现需修正的问题。

本续作补齐的 hermetic 测试（`tests/test_form_ipo_price.py`，零网络，复用既有 tmp_path /
monkeypatch 风格；walker 级经 `scripts/` 入 sys.path 导入真实 `main()`，仿
`test_export_terminal_data.py` 先例；目标 parquet 为合成 DataFrame）：

- `test_prune_drops_out_of_window_exact_none_fail_keeps_window_incl_fail` — 窗口外
  exact/none/FAIL 三类条目整条移除，窗口内三类全保留（FAIL 也在内、原样保留），
  入参 dict 不被改动（纯函数契约）。
- `test_prune_empty_target_yields_empty_cache` — 空 target → 空缓存，入参不变。
- `test_prune_is_idempotent` — 裁剪两次 == 裁剪一次（不动点）。
- `test_walker_walk_saves_cache_pruned_to_target_window` — 预置含窗外 exact 条目的缓存，
  monkeypatch `parse_filing_offer_price` 跑真实 `main()`：落盘缓存不含窗外条目；
  窗口内 ok 行零重取、FAIL 行被重试并翻正；live 走查 `_meta` 诚实推进
  （requests_cumulative 40→44、walk_cap/last_run 写入）。
- `test_walker_dry_pass_prunes_window_and_leaves_meta_untouched` — `--max-requests 0`
  经真实 argv 走干跑分支：parse 被 monkeypatch 为即炸（证明零请求）、窗外条目仍被裁剪、
  窗口内 FAIL 保留、`_meta` 与前置完全相等（未被改写）。

测试数字：`uv run pytest tests/test_form_ipo_price.py tests/test_form_ipo.py -q`
→ **36 passed**（其中 test_form_ipo_price.py 24，含本续作新增 5 个；test_form_ipo.py 12
存量全绿）。Ruff：`uv run ruff check src/aionis/ingest/form_ipo_price.py
scripts/form_ipo_price_parse.py tests/test_form_ipo_price.py` → All checks passed（净）。
未跑 `tests/test_web_terminal_data.py`（按任务边界，属主线集成步骤）。

Commit：`4ffca8784ada8694a6baedbef60e3378e5790fed`（单原子 fix+test，
`fix(ingest): prune IPO price cache to the bounded walk target window`，
分支 `agent-w/ipo-price-window`，未 push）。零 ledger/frozen/config/prereg/OOS 接触，
零网络。`test_form_ipo_panel_contract` 转绿仍待主线重跑 walker + 重导出（数据态）。
