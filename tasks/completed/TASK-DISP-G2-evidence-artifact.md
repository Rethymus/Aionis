# TASK-DISP-G2 — R2-lite:自包含可分享研究证据工件(standalone evidence HTML)

- Lane:display/导出(只读已提交面板 `web/src/data/aionis/*.json`;零新抓取、零网络、零研究面接触)
- 设计规格:`reports/design/2026-08-28-editorial-diagram-language.md` §6 R2-lite;证据依据:`reports/design/2026-08-28-evidence-corroboration.md`(OpenPM 可审计评估/TS-Arena 预注册工件=external verifiability 的文献支撑)
- 你是本轮 scripts lane 唯一 dev agent,分支 agent/g2 已检出。**不 push、不删 worktree、不跑研究脚本、不碰 runs/。**

## 交付物

### 1. `scripts/export_evidence_html.py`(新文件,自包含生成器)

- 输入:只读 `web/src/data/aionis/{metrics,ic_monthly,evidence,headline_provenance}.json`(存在的面板;缺哪个如实降级,不伪造)。
- 输出:`reports/evidence/atlas-claim-v1.html`(**单文件自包含**:内联 CSS+内联 SVG+内联数据表,零 JS、零外部资源、零字体请求——浏览器直开即读)。
- 内容区块(全中文+英文双语标题均可,固定双语并列,不走 i18n 体系):
  1. 标题与主张陈述(预注册两尾差分主张的一句话);
  2. 头条读数卡:combined_ic / 95% CI / p / n_months / verdict / sesoi / config_sig_short / ledger_row(全部来自 metrics.json 实值,禁止硬编码数字);
  3. 内联 SVG 森林图(CI vs SESOI 带vs 零线;坐标构建期算死);
  4. 内联 SVG IC 序列迷你条形(66 月 combined,零色可选灰阶——自包含工件不依赖站点 CSS 变量,直接用硬编码 oklch/hex,注明与站点 token 的对应关系);
  5. 数据表回退(逐月 IC 表);
  6. 方法学与边界(反泄漏声明:预注册/purged CV/commit-then-reveal 状态;P0-1 E3 措辞按仓库现状如实——"forward-live 已实现待业主契约冻结");
  7. 溯源脚注:headline_provenance 的 as_of 与面板 snapshot、生成器版本常量。
- **确定性(字节稳定)**:禁止 `datetime.now()/Date`;一切 as_of 取自面板字段;排序规则写死;`sort_keys=True` 风格的稳定序列化。文件头注明"byte-stable artifact — regenerate with `uv run python scripts/export_evidence_html.py`"。
- CSS 内联且遵守站点对比度惯例(浅色卡面/深墨文字/单蓝强调,WCAG AA;色盲安全:不用红绿方向对)。

### 2. 契约测试 `tests/test_evidence_html_artifact.py`(新文件,hermetic)

- 对生成函数用**合成夹具 metrics/ic 数据**(测试内构造,标注 fixture)断言:产物含主张数字、含 `<svg`、含 verdict 字符串、无 `undefined/NaN/[object Object]`、无 `Date.now/now(` 残留;
- 对**已提交的真实工件** `reports/evidence/atlas-claim-v1.html`(你会生成并提交它):断言与 `web/src/data/aionis/metrics.json` 的数字逐字一致(IC/CI/p/n/verdict/config_sig)、含 ESOSI… 即 SESOI 字样、零外部资源引用(`http://`、`https://`、`src=` 除 data: 外不得出现)。
- 零 skip。

### 3. 生成并提交真实工件

```bash
uv run python scripts/export_evidence_html.py
```

生成 `reports/evidence/atlas-claim-v1.html` 并提交;重跑一次确认字节一致(sha256 双算写进报告)。

## 纪律(违反=失败)

- 不改任何既有文件;不加依赖;不碰 ledger/frozen/config/prereg
- 产物措辞=呈现测量与设计,不给投资建议;NULL 判定按本仓立场如实呈现(纪律的胜利)
- HTML 单文件自包含是硬要求(文章的 zero-dependency 信条)

## 验证与提交(worktree 内;若 shell 遇 0xC0000142/fork 失败为本机已知病理,sleep 30-60 重试)

```bash
uv sync --all-extras
uv run pytest -q tests/test_evidence_html_artifact.py tests/test_web_terminal_data.py -x
uv run ruff check scripts/export_evidence_html.py tests/test_evidence_html_artifact.py
```

exit 0 后单原子 commit(分支 agent/g2)。报告:实嵌数字清单、字节稳定双算 sha、测试输出、文件大小。
