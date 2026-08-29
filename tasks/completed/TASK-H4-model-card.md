# TASK-H4 — model_card 面板垂直切片(冻结建模元数据 → 机器可读卡片 → /model-health 呈现)

- Lane:display/export 派生(读 **gitignored** runs/results/<confirmatory>/ + tracked runs/ledger.jsonl + web/src/data/aionis/metrics.json + uv.lock + docs/track-c-preregistration.md;零网络、零冻结写、零 now())
- 设计规格:`reports/design/2026-08-29-model-card-design.md`(必读——文献印证:A 级 arXiv 实检 7 篇 + B 级 SR 11-7/FAIR/TIA,分级已声明)
- 你是本轮唯一 dev agent(H4),分支 agent/h4 已检出。**不 push、不删 worktree、不跑研究脚本、runs/ 只读。**

## 先例(必读)

- R1A 的 `export_score_diagnostics` 四注册点先例(grep score_diagnostics);`export_ledger_audit` 的 `_read_ledger_rows` 用法;D 的 `scripts/export_research_dossier.py`(内容 sha/溯源脚注体例);G2 的 `scripts/export_evidence_html.py`(字节稳定体例);`tests/test_score_diagnostics_panel_contract.py`(契约测试风格)。

## 交付物

### 1. `export_model_card()`(export_quarto_data.py 同区或 terminal 侧就近)

- **确认 run 解析**:读 tracked ledger,取 track_c 确认相关 freeze/config_committed 行与 result 行(参照 D 生成器的 freeze→result 解析),用其 config_sig 匹配 `runs/results/<sig>/meta.json` 的 config_sig;本地无该目录 → raise FileNotFoundError 走 `_safe_export` SKIP(诚实保留旧值,既有守卫)。**不要硬编码 4 个目录名中的任何一个。**
- 输出 `model_card.json`,节结构照设计规格 §3:identity/intended_use/data/model/evaluation_protocol/results/governance/provenance。全部值机器读取:
  - `runs/results/<sig>/config.json`:feature_cols、horizon、n_splits、embargo_sessions、cv_scheme、frozen_params(全 dict)、end_lag_months、versions、fund_sha256/prices_sha256/membership_sha256/uv_lock_sha256
  - 同目录 `meta.json`:config_sig、h6_deterministic、aionis_version、schema、ts
  - ledger:freeze 行 ts+行号+行 sha、result 行行号;metrics.json:headline 实值(IC/CI/p/n_months/verdict/sesoi/config_sig_short/ledger_row)
  - docs/track-c-preregistration.md:内容 sha(intended_use 的 S 引用)
  - uv.lock:内容 sha(uv_lock_sha256 与重算一致性校验,不一致 raise)
- 数值 round 6 位稳定;字段可空如实(null);生成器版本常量 `MODEL_CARD_VERSION="v1"`;文件头注明 byte-stable 与再生成命令;LF 输出。
- **自校验**:uv_lock_sha256 != 重算 → raise;config_sig != meta.config_sig → raise(防错目录)。

### 2. 注册四点 + barrel + i18n + /model-health 呈现

- 照 score_diagnostics 四注册点(data_health 类别 `_DH_FROZEN`;as_of 取 run_ts 日期;_API_LICENSE 文案"Aionis research artifacts (repo MIT)" / "machine-readable model card of the frozen confirmatory Track C model")。
- barrel 显式类型 ModelCard(逐字段含可空性);dict `modelcard.*` zh/en 对称(标题/各节名/字段名/方法论)。
- `/model-health` 页(view 组件)加"Model card"节:identity 行卡 + 分节表格(data/model/evaluation/results/governance),sha mono 展示,链接 docs 预注册(GitHub)与 ledger_audit 页;无卡片数据时诚实空态(表头仍渲染,force-camp P9 先例)。

### 3. 生成真实面板 + 契约测试 `tests/test_model_card_contract.py`(hermetic 零 skip)

- 合成夹具(tmp 树:config/meta/ledger 行/uv.lock/docs)断言:节字段逐字、两处自校验 raise(错 sig/错 uv_lock)、缺失目录 SKIP 语义;
- 真实 `model_card.json`:与 metrics.json 逐字对账(results 节)、uv_lock_sha256 重算一致、identity.config_sig 与 data_health/api_catalog 注册一致、feature_cols 长度与 metrics… 可调和项;
- 已提交真实面板(生成命令:`uv run python -c "import sys; sys.path.insert(0,'scripts'); import export_terminal_data as m; m._safe_export('model_card', m.export_model_card)"`,照 score_diagnostics 先例;**注意主仓 runs/results 在,生成应成功**);双跑 sha 一致写进报告。

## 纪律(违反=失败)

零手写数字;不跑研究脚本(只读冻结产物);禁 Date/random/recharts/新依赖/红绿方向色;投资建议措辞禁止;测试零 skip。

## 验证与提交(worktree 内;0xC0000142/fork 失败=本机病理,sleep 30-60 重试)

```bash
uv sync --all-extras
uv run pytest -q tests/test_model_card_contract.py tests/test_web_terminal_data.py -x
uv run ruff check scripts/export_terminal_data.py scripts/export_quarto_data.py tests/test_model_card_contract.py
cd web && node node_modules/typescript/bin/tsc --noEmit && node node_modules/eslint/bin/eslint.js src/data/aionis/index.ts src/i18n/dict.ts <你改的model-health组件>
```

全净后单原子 commit(分支 agent/h4)。报告:确认 run 解析结果(哪个 sig/目录)、卡片实嵌数字清单、双跑 sha、测试输出。
