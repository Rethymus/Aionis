# TASK-DISP-G1 — atlas 森林图文献语境线 + IC 样本期稳定性描述条(P0-3② + P3-2 lite)

- Lane:display(纯展示层;派生自已提交面板,零新抓取、零导出改动)
- 设计规格:`reports/design/2026-08-28-editorial-diagram-language.md`;证据依据:`reports/design/2026-08-28-evidence-corroboration.md` 主张 4/5
- 你是本轮 web lane 唯一 dev agent,可在自己 worktree 改共享文件(dict.ts);分支 agent/g1 已检出。**不 push、不删 worktree、不跑 next build。**

## 交付物(只改 `web/src/components/atlas/atlas-claims.tsx` + `web/src/i18n/dict.ts`)

### A. 森林图文献语境(在既有森林图区块内)

- 从 `aionis.metrics` 派生 t 值:`se ≈ (ci_hi - ci_lo) / (2 × 1.96)`,`t = combined_ic / se`(纯展示推导,写明公式注释);无 CI 时诚实不显示。
- 在森林图下方加一行"文献语境"小字:Harvey-Liu-Zhu (2016 RFS) 对已发表因子要求 **t > 3.0**(haircut 修正后);对照呈现本研究实际 t 值与判定(NULL 是预注册诚实结论,不因阈值改变)——措辞必须避免"本结果通过了/失败了文献阈值"的暗示,只做并列语境。
- i18n 键(你自行加,zh/en 对称,放 dict.ts atlas 块末尾):`atlas.forest.context`(含 {t} 插值,仓库 `.replace` 模式)、`atlas.forest.context.source`("Harvey, Liu & Zhu (2016 RFS):已发表因子多重检验阈值 t > 3.0" / 对应英文)。

### B. IC 样本期稳定性描述条(热力透视图下方追加一小条)

- 从 `aionis.icMonthly` 客户端确定性派生:按月序前/后半分样本(奇数月则前半多一月,写死规则),对 us/cn/combined 各算前半均值、后半均值、差值。
- 呈现:三行小表或紧凑条(US/CN/合并 × 前半 → 后半 → Δ),不做显著性声明(样本量不支持),只做描述并注明"描述性,非检验"。
- i18n 键:`atlas.icpivot.halves.title`(样本期稳定性(描述性)/ Sample-period stability (descriptive))、`atlas.icpivot.halves.first`(前半样本)、`atlas.icpivot.halves.second`(后半样本)、`atlas.icpivot.halves.delta`(Δ)、`atlas.icpivot.halves.note`。
- 诚实规则:任一半样本不足 12 个月则整条不渲染(不伪造)。

## 纪律(违反=失败)

- 禁 Date/random/recharts/新依赖/红绿方向色;零客户端请求;布局构建期算死
- 不改 page.tsx/其他区块/data 模块;不写投资建议措辞

## 验证与提交(worktree 内)

```bash
cd F:/ZCodeData/Aionis-wg1/web && node node_modules/typescript/bin/tsc --noEmit
node node_modules/eslint/bin/eslint.js src/components/atlas/atlas-claims.tsx src/i18n/dict.ts
```

(worktree 已有 node_modules junction;若 shell 遇主机病理 0xC0000142/fork 失败,sleep 30-60 后重试,本机有已知好坏窗口循环)
tsc/eslint 0 error 后单原子 commit(分支 agent/g1)。报告:t 值实算数字、前后半均值表、键清单、验证输出。
