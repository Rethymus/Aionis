# TASK-H6 — 建模决策谱系图(被取代配置链:显式 supersede 解析 + ledger 序演化,可追溯决策史)

- Lane:display/export 派生(只读 tracked ledger;零网络、零冻结写、零 now())
- 背景:H5 清单把 11 条 config-only 诚实列示但未呈现**决策链**。ledger 实测锚点:
  - **track_adaptive 显式链**:#51(monthly refit)→ #52 `amend1: WEEKLY cadence + truly-frozen baseline. Supersedes #51 (monthly-A, redundant with Track C).` → #53 `amend2: n_estimators 500→100 (feasibility ~5min vs ~27min; ...)`——取代理由原文在账;
  - **track_c 演化链**:#46(双区域)→ #47(US 确认+CN 探索拆分)→ #48(确认,结果行 49)——无显式 amendment,claim 文本可见演化;
  - track_b #40-42 同 claim(臂变体)、baseline_rank #44/45 同相两版。
- 你是本轮唯一 dev agent(H6),分支 agent/h6 已检出。**不 push、不删 worktree、零网络;wh6 无 runs/——本任务不读 runs/results(纯 ledger 派生),无需 junction。**

## 交付物

### 1. exporter 扩展:`export_model_inventory()` 增加 `chains` 计算(纯 ledger 派生)

- 按 phase 分组 config_committed 行(行序=账本序);每组:
  - `kind:"explicit-supersede"`——amendment 含 `Supersedes #NN`(大小写不敏感,正则 `Supersedes\s+#(\d+)`),解析出被取代行号;链=从无被取代记录的首行到末行,每链接附 `supersede_reason`(amendment 原文截断 ~200 字符);
  - `kind:"ledger-sequence"`——无显式 Supersedes 的多行组:诚实标注"按账本序排列的演化序列(非显式取代声明)";
  - 单行组(track_b 若只有…实际 3 行;单行组不产生链)不输出;
- 输出挂 `model_inventory.json` 新键 `chains`:`[{phase, kind, links:[{row, config_sig, ts, amendment_excerpt(可空), resulted(bool:该 sig 是否有 confirmatory:first/本地目录)}]}]`;
- 排序/截断写死;round 不涉及;`MODEL_INVENTORY_VERSION` 升 **"v2"**(向后不兼容的形状新增,契约测试同步)。

### 2. /model-health 清单节下方加"建模决策谱系(Modeling decision genealogy)"渲染

- 每链一块:phase 标题 + kind 徽章(显式取代/账本序演化)+ 链式行(`#46 → #47 → #48`,箭头连接;explicit 链在被取代行下挂 reason 引文 blockquote);resulted 行高亮(既有 emerald 语义);
- 双语 i18n 键(`inventory.genealogy.*`):标题/两种 kind/取代理由标签/说明句(注明"显式取代=ledger amendment 原文;账本序=推断性排列"的诚实区分)。

### 3. 契约测试:`tests/test_model_inventory_contract.py` 追加(版本断言翻 v2)

- 合成 ledger(带/不带 Supersedes):显式链解析(行号+reason 摘录)、非显式组 kind=ledger-sequence、单行组无链;
- 真实面板:chains 恰 2 块(track_adaptive explicit 3 links 含 #52/#53 reason 原文钉死;track_c sequence 3 links)+ 其余组不出现 + 既有断言保持。

### 4. 重生成 `model_inventory.json`(真实)并提交;双跑 sha 一致。

## 纪律(违反=失败)

零手写数字(amendment/claim 引文为账本原文截断);runs/ 只读(本任务仅 ledger);禁 Date/random/recharts/新依赖/红绿方向色;零 skip;无投资建议;reason 引文如实原文不润色。

## 验证与提交(worktree 内;0xC0000142/fork 失败=本机病理,sleep 30-60 重试)

```bash
uv sync --all-extras
uv run pytest -q tests/test_model_inventory_contract.py tests/test_web_terminal_data.py tests/test_data_health_coverage_contract.py tests/test_model_card_contract.py -x
uv run ruff check scripts/export_terminal_data.py tests/test_model_inventory_contract.py
cd web && node node_modules/typescript/bin/tsc --noEmit && node node_modules/eslint/bin/eslint.js src/data/aionis/index.ts src/i18n/dict.ts <你改的model-health组件>
```

全净后单原子 commit(分支 agent/h6)。报告:chains 解析清单(逐链 kind/links/reason 摘录)、双跑 sha、测试输出摘要。
