# GitHub Pages 展示方案（DRAFT v0.1 · 2026-07-31）

> **状态：DRAFT — 待业主决策。** 本方案为全新起草（grep 确认 `docs/ tasks/ state/ decisions/
> reports/ archive/ evals/ .omc/` 内无先前产物）。**承重阻塞**：仓库当前为 **PRIVATE**
>（`gh repo view --json visibility` 确认），而 GitHub Pages 免费档**仅对 PUBLIC 仓库**。须先决策
> 托管路径（§1），再实施。

## 1. 托管路径决策（承重 — 业主定）

| 选项 | 成本 | 仓库可见性 | 权衡 |
|---|---|---|---|
| **A. 改公开仓库 + GitHub Pages** | $0 | 公开 | 最简、GitHub 原生、`rethymus.github.io/Aionis` URL；但代码 + 反泄漏纪律全公开 |
| **B. 保持私有 + Cloudflare Pages / Netlify 免费档**（推荐） | $0 | 私有 | 零成本 + 私有；mkdocs 静态产出经 CI 部署到第三方免费托管；多一个账号/CI 配置 |
| **C. 保持私有 + GitHub Pro** | $4/月 | 私有 | GitHub Pages 原生 + 私有；但违反"零成本"约束 |
| **D. 暂不做** | $0 | — | dashboard + RESULTS.md 内部够用；延后 |

**推荐 B**（零成本 + 私有，最贴项目"零成本 + vibe-coding"约束）。若业主不介意公开且想要
`github.io` URL，则 A 最简。**C 被零成本约束排除**（除非业主明确接受付费）。

## 2. 静态站点生成器：mkdocs-material（Apache-2.0）
- 许可证 **Apache-2.0** → 过 ADR-007 闸门（仅 MIT/Apache/BSD）。
- Python 原生（贴项目栈）；MathJax 数学 + mermaid 图 + 内置搜索；单一 `mkdocs.yml`；vibe-coding 友好。
- 淘汰：Quarto（GPL，**不过** ADR-007 闸门）；Jekyll（MIT 但需 Ruby，与 Python 栈不贴）；docsify（客户端渲染，不适合研究文档）。

## 3. 内容规划（反泄漏安全）
**✅ 安全发布（冻结、已 commit、无实时信号）**：
- 首页（`README.md` + `docs/00-vision` + 反泄漏理念 + TCR 框架）
- 可证伪结果（`docs/RESULTS.md` — 4 个 null B/C/D/E1 + 紧致 CI）
- 预注册（`docs/phase-*-preregistration.md` — B/C/D/E1/E3）
- ADR 注册表（`decisions/index.md` + `decisions/ADR-*.md`）
- 7 门数据摄入闸门（`docs/data-intake-rubric.md`）+ 许可白名单（`docs/data-license-allowlist.md`）
- TCR 理论（`docs/theory-of-computable-reality.md`）+ `docs/01-08` 核心文档
- 贡献指南（`CONTRIBUTING.md`）

**⚠️ 探索性（带警示标签，待 §4 决策）**：E3 前向进展（冻结快照 + EXPLORATORY 横幅）。

**❌ 严禁发布（泄漏/密钥面）**：`.env` / `data/` / `*.parquet` / `runs/ledger.jsonl` /
`runs/results/` / `dashboard/app.py`（动态，需服务器）/ 任何前向实时信号或未实现前向数据。

## 4. E3 前向公开策略（承重 — 业主定）
- **A. 只发 E3 预注册**（不公开任何累积进展）— 反泄漏最保守。**推荐**。
- **B. 冻结快照 + EXPLORATORY 横幅**（公开累积进展）— 增泄漏面：前向 IC 被公众观察 → 可能影响 headline 决策（即便有横幅）。
- 依据：pre-reg §1/§7 — 前向 IC 在 calendar gate（≥ 阈值月数 + ci_half<0.015）前为 EXPLORATORY，**不得**当 confirmatory。

## 5. 反泄漏硬防护
1. 只发已 `git commit` 的冻结内容（时间戳早于部署）。
2. 无实时数据/动态内容（纯静态 HTML/CSS/JS）。
3. E3 页（若发布）显眼 EXPLORATORY 横幅 + 冻结时间戳 + 无可操作信号。
4. CI 只读权限；无密钥/数据访问；`.gitignore` 保护 `.env`/`data/`/`*.parquet`。
5. 不暴露 config hash / 可复现实验配置（防 rerun-to-significance）。
6. 图表为冻结快照（带时间戳水印）。

## 6. 分阶段实施
- **Phase 1 (MVP)**：`/docs`（站点根）+ `mkdocs.yml` + 一个 CI（Pages 或 Cloudflare/Netlify）+ `RESULTS.md` + 预注册 + ADR 注册表 + 数据闸门。~2h。
- **Phase 2 (v2)**：`docs/00-08` 全量 + 冻结图表（rank-IC 结果 PNG）+ E3 页（按 §4 决策）。~3h。
- **Phase 3 (v3)**：主题微调 + SEO + 可访问性。~4h。

## 7. 成本
$0（选项 A/B/D）；$4/月（选项 C）。

## 8. 开放决策（业主）
1. **托管路径**（§1）：A 公开+Pages / B 私有+Cloudflare/Netlify（**推荐**）/ C 私有+Pro（违反零成本）/ D 延后。
2. **E3 公开策略**（§4）：A 只发预注册（**推荐**）/ B 冻结快照+横幅。
3. **站点许可证**：repo 当前**无 LICENSE 文件** → 需定（建议内容 CC-BY-4.0 + 代码 Apache-2.0，或与业主偏好一致）。
4. **图表优先级**：Phase 1 纯文本（**推荐**）/ Phase 1 即含图。
5. **自定义域名**：默认 github.io / Cloudflare 子域（**推荐**）/ 自购域名。
