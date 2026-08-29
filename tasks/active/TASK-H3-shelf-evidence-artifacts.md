# TASK-H3 — 证据工件上架 /shelf(溯源链最后一公里:目录级 sha 校验闭环)

- Lane:display/export(knowledge_shelf 导出扩展 + /shelf 视图新层;零网络、零研究面接触)
- 背景:轮㉜/㉚ 产出的两个自包含证据工件(`reports/evidence/atlas-claim-v1.html`、`reports/evidence/research-dossier-v1.html`)已 tracked 但终端不可发现——溯源链最后一公里缺口。工件自带 byte-stable sha;目录条目在导出时现算同一 sha → 读者可校验所下载工件与目录一致(Trust-Tiered 溯源闭环)。
- 你是本轮唯一 dev agent(H3),分支 agent/h3 已检出。**不 push、不删 worktree、零网络。**

## 先例(必读)

- `scripts/export_terminal_data.py::export_knowledge_shelf`(约 line 6329)与 `_KS_RESEARCH_SOURCES`(约 6123,固定字面量层先例);`web/src/components/shelf/shelf-view.tsx`(research_sources 渲染先例);`tests/test_knowledge_shelf_panel_contract.py`(契约测试风格)。

## 交付物

### 1. exporter:`_KS_EVIDENCE_ARTIFACTS` 固定字面量 + 装配

- 两条固定条目(名称/描述双语静态字符串,**非抓取**):
  - `atlas-claim-v1` — "头条主张证据卡:IC/CI/p/verdict/SESOI 单页速览(browse: web/out/atlas.html 的可溯源对应物)" / 英文对应;
  - `research-dossier-v1` — "溯源研究档案:24 条来源登记表 → 报告 → 建模分析全流程,[S#] 引用闭包" / 英文对应。
- 每条:`{id, name_en, name_zh, desc_en, desc_zh, path, url(GitHub blob), sha256(导出时对本地文件现算;文件缺失 → sha256=None + 诚实降级,不伪造), n_bytes}`。
- `payload["evidence_artifacts"]` + methodology 追加第三层一句话(Layer 3 — generated evidence artifacts: self-contained HTML, byte-stable, sha256 pinned at export for reader verification)。
- **不改五类白名单、不动 docs/decisions 扫描、不动 research_sources。**

### 2. /shelf 视图:新"Evidence artifacts"层

- 读 `knowledgeShelf.evidence_artifacts`,渲染于 research_sources 之前或之后(就近视觉先例);双语名+描述、sha256 前 12 位 mono 展示、字节数、GitHub link-out(既有 link-out 样式)。
- i18n 键(zh/en 对称):`shelf.artifacts.title`(证据工件 / Evidence artifacts)、`shelf.artifacts.note`(自包含 HTML,字节稳定;sha256 在导出时钉死,供读者校验 / 对应英文)、`shelf.artifacts.sha`(SHA-256)。

### 3. 契约测试:`tests/test_knowledge_shelf_panel_contract.py` 追加(不新建文件)

- knowledge_shelf.json 的 `evidence_artifacts` 恰 2 条、id 集合钉死、URL 形如 github blob、**sha256 与仓内实际文件重算一致**、n_bytes 一致;
- barrel/dict 注册存在(shelf.artifacts.* 双语非空)。

### 4. 重生成并提交 `web/src/data/aionis/knowledge_shelf.json`

```bash
uv run python -c "import sys; sys.path.insert(0,'scripts'); import export_terminal_data as m; m._safe_export('knowledge_shelf', m.export_knowledge_shelf)"
```

## 纪律(违反=失败)

- 不改既有面板语义;零 Date/random;描述双语静态字符串不抓取;语态=呈现,无投资建议
- 报告含:双条目 sha 实值、契约测试输出、(0xC0000142/fork 失败=本机病理,sleep 30-60 重试)

## 验证与提交(worktree 内)

```bash
uv sync --all-extras
uv run pytest -q tests/test_knowledge_shelf_panel_contract.py tests/test_web_terminal_data.py -x
uv run ruff check scripts/export_terminal_data.py tests/test_knowledge_shelf_panel_contract.py
cd web && node node_modules/typescript/bin/tsc --noEmit && node node_modules/eslint/bin/eslint.js src/components/shelf/ src/i18n/dict.ts
```

全净后单原子 commit(分支 agent/h3)。报告:条目 sha/字节数实值、测试输出、(视文件实际)任何与任务书的偏离。
