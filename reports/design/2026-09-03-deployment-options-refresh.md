# 2026-09-03 — 部署方案全景复核（08-22 文档的增量刷新 + 新免费选项）

> 定位：**基建 lane 研究文件**（PROPOSED，待业主 GO）。是
> `2026-08-22-realtime-deployment-architecture.md`（下称"08-22 文档"）的**增量刷新**，
> 不重复其结论，只写：① 现状实核（什么已经悄悄修好了）；② 2026-09 各平台免费政策
> 复核（哪些方案已死/降级）；③ 两个 08-22 未覆盖的新免费选项；④ 修订后的 runner 排序。
> 本文 0 代码改动；全为 display/infra lane，0 ledger/frozen/config/prereg/OOS。
> 检索方法：WebSearch MCP（配额 09-03 当日耗尽，10-03 重置）→ 内置 WebFetch 直抓官方
> 定价页 → Bing 兜底 → 本仓 `gh` CLI 实核。凡未能官方直证的均显式标注 UNVERIFIED。

---

## 1. 现状实核（2026-09-03，gh CLI / API 实证）

| 项 | 08-22 时 | 09-03 现状 | 证据 |
|---|---|---|---|
| 仓库可见性 | PRIVATE | **仍 PRIVATE** | `gh repo view --json visibility` |
| GH 账单 | 停摆（run 5s 内死） | **已恢复**（Tests 全绿、refresh 可跑） | `gh run list` |
| Pages 部署模式 | Actions 模式（吃分钟数） | **legacy 分支模式**（`gh-pages` 分支直发布，`build_type:"legacy"`，status built） | `gh api repos/…/pages` |
| `deploy-pages.yml` | 停用 | 仍 disabled_manually（**已被分支模式取代，属预期**） | `gh workflow list` |
| `refresh-terminal-data.yml` | 停用 | **已重新启用**（09-03 15:45 有 in_progress run） | `gh run list` |
| 站点构建 | — | 本地 `pnpm build`（1,504 页）+ push → gh-pages（多轮 current.md 实证） | current.md 轮 75-81 |

**结论：08-22 文档 §11「极简 $0 阶梯」的阶梯 1 实际已落地**（Pages 切分支模式 + 账单修复
+ refresh 复活）。托管平面与发布链路**当前是工作的**，且部署不再消耗 Actions 分钟。

### 1.1 但埋着一颗定时炸弹：refresh 管线 vs 私有仓库计量

`refresh-terminal-data.yml` 的设计包络（YAML 注释自证）：

- 冷跑 ≤ **150 min**；热跑 **60-80 min**（缓存收敛后）；每周 5 跑 → **月耗 1,320-1,760 分钟**；
- 叠加 Tests（每 push 4-6 min，多代理高频 push 日 10+ 次）→ **月总耗轻松越过 Pro 3,000 分钟**；
- 私有仓库计量：Free 2,000 / Pro 3,000 分钟/月。**8 月的计费崩盘不是意外，是结构必然**；
  重新启用 = 每月重演一次，直到再次触顶/卡失效。
- 唯一免费出路：仓库转 Public（Actions 分钟无限）——业主可见性决策，前置一次全史 secret 扫描
  （08-22 §10.4 D3 已论证"可见性与成本解耦"，但 Public 的分钟无限仍是事实上的最大杠杆）。

**因此本刷新的真正命题**：在仓库保持私有的前提下，把 refresh 管线（bash + uv + scripts/，
平台无关）从计量 Actions 迁到免费云端 runner——即 08-22 §12 的正选/次选，外加本文 §3 的两个新选项。

---

## 2. 2026-09 免费政策复核：死亡名单与降级（相对 08-22 文档）

| 平台 | 08-22 判定 | 09-03 复核 | 判定变化 |
|---|---|---|---|
| **HF Spaces** | 备选 #7（2vCPU/16GB + ping 保活） | **政策变更：免费账号不能再建计算型（Gradio/Docker）Space，需 PRO $9/月**；免费只剩 Static + 2 个 ZeroGPU Gradio（官方 docs 原文） | **❌ 死亡**（付费墙） |
| **Koyeb** | （未列） | 免费_web 服务_档已取消，仅剩免费 Postgres 5h 实例；最低 Pro $29/月；正并入 Mistral AI（pricing 页实抓） | **❌ 死亡** |
| **Render** | 08-22 §10.2 备胎 | 免费档仍在但缩水：web 512MB、**带宽仅 5GB/月**、cron **收费**（$0.00016/min）、定位"个人探索"（pricing 页实抓） | **❌ 出局**（512MB 跑不动 pandas 管线 + cron 收费） |
| **Zeabur** | （未列） | 免费档转型为"管理你自己的服务器"（BYO 1 台），**不提供运行时算力**；Dev $5/月（pricing 页实抓） | **❌ 出局**（无免费算力） |
| **CF Containers** | 排除（需 Workers Paid） | 确认仍 "Available on Workers Paid plan"（developers 页 2026-08-28 更新，实抓） | ❌ 维持排除（$5/月门） |
| **CloudBase 免费体验版** | （未列） | 2026-01-16 起 3,000 资源点/月 ¥0，**但云函数超时锁死 3s / 内存 256M 不可改**（腾讯官方文档实抓） | **❌ 出局**（跑不动管线；个人版 ¥19.9/月非免费） |
| **Oracle Always Free** | §12 正选 ⭐ | 配额减半（2 OCPU/12GB，08-18 已强制执行）之外，**出现合规实例被误禁用的执行事故**（官方社区多帖）；注册仍需卡 | **⚠️ 降级**：正选 → 备胎 |
| GH self-hosted runner | 政策风险（$0.002/min 延期中） | **延期仍未落地，官方计费文档现文：self-hosted 免费**（搜证：2025-12-17 官宣 postponement，非取消） | ✅ 维持可用（政策尾部风险在） |
| GitHub Codespaces | §12.2 过渡位 | 官方计费文档实抓：个人账号 **120 核时/月 + 15GB**，**免绑卡**（"无有效付款方式时，配额耗尽才封锁"） | ✅ 维持（08-22 判断被官方文档坐实） |
| GCP Cloud Run Jobs | §12 次选 | pricing 页实抓：Jobs 免费档 **240,000 vCPU-s + 450,000 GiB-s/月**（按 billing account 聚合）；egress 北美 1GiB/月 | ✅ 数字坐实 |
| CF Workers/Pages/R2 | §4/§10 已核 | 无变化（静态资产请求免费无限；Worker 10 万 req/日；R2 10GB/100 万写/月；Cron 免费）——本轮官方页被内容过滤拦截未重抓，沿用 08-22 双源核实值 | ✅ 沿用 |

---

## 3. 新选项深挖（08-22 文档未覆盖）

### 3.1 Modal — Python 原生 serverless，$30/月免费额度 ⭐新增首选

官方 pricing 页实抓（2026-09-03）：Starter（$0）含 **$30/月免费算力额度**、100 容器并发、
**5 个 cron job**、3 席位；限制：Scheduled/Web Functions 受限、日志仅留 1 天、区域加价 1.15-1.75×。

**为什么贴合本仓**：
- 管线就是 Python（uv + scripts/*.py），Modal 是 Python 原生容器云——08-22 §12.3 的
  "runner 可插槽"设计原样适用：`update_and_deploy.sh` 的命令序列转写为 Modal
  `modal.Cron` 函数 + 容器镜像（或 `modal.Image.debian_slim().pip_install(...)`）；
- 成本测算：2 vCPU × 1h × 22 天 = 44 vCPU-h；Modal CPU ≈ $0.125/vCPU-h → **≈ $5.5/月**，
  即使按"无卡仅 $5"的最坏口径也基本覆盖，$30 口径余量 5 倍+；
- data/cache（~4-5GB）挂 `modal.Volume`（持久卷）即可替代 `actions/cache`；
- 产出 JSON 用 gh token 推回 main（与现 workflow 同构），gh-pages 发布链不动。

**待实施时核实（UNVERIFIED）**：① 无信用卡注册的额度口径（第三方源有 "$5/月无卡 / $30/月
绑卡"两说，官方页未写）；② Volume 存储计费；③ Starter "Scheduled Functions 受限"的具体限制。

### 3.2 ClawCloud Run — GitHub 老账号每月 $5 永久额度，免绑卡 ⭐新增次选

多源交叉验证（LowEndTalk 官宣帖 + CSDN/知乎/少数派中文评测，2026 检索）：**GitHub 账号
注册满 180 天 → 每月 $5 额度永久发放，免绑卡**；限额内可用 4 vCPU/8GB/10GB 盘的容器；
76+ 开源一键部署模板。**官方文档站（doc.claw.cloud / docs.runclaw.cn）从本网络两次 TLS
重置无法直连复核**——实施前须业主网络自证（UNVERIFIED-官方）。

**适配形态**：常驻小容器（1C1-2G ≈ $3-5/月，额度内）跑 cron + bash 管线；10GB 盘装
repo + venv + data/cache（~4-5GB）偏紧但可行；或容器睡死 + 外部 cron（cron-job.org 免费档）
拉起。**风险**：第三方小厂稳定性/寿命不可承诺——只做 runner 备份位，不做唯一依赖。

### 3.3 国内新用户试用窗口（一次性，非长期）

- **腾讯云试用中心**（cloud.tencent.com/act/free 实抓）：个人认证新用户轻量服务器
  **2C2G/3M/40GB 免费 1 个月**（另有 2C4G、4C8G 档，部分每日限量）；试用内续年 3.5 折。
- **阿里云试用中心**（free.aliyun.com 实抓）：160+ 产品试用，规则=每账号每产品一次、
  需实名、试用不可延长（ECS/轻量具体档位为动态页，UNVERIFIED）。

**定位**：不是长期方案，是"把管线容器化并实战验证一周"的**免费脚手架**——验证过的容器
镜像随后原样迁 Modal/ClawCloud。若不想折腾容器化，可跳过本节。

---

## 4. 修订后的 runner 排序（08-22 §12.2 的 2026-09 版）

| # | 方案 | 免费额度（核实态） | $0 可信度 | 关键代价/风险 | 相对 08-22 |
|---|------|-------------------|:---:|------|------|
| 0 | **转 Public + GH Actions** | 分钟无限 | 高 | 业主可见性决策 + 全史 secret 扫描；方法论公开本身契合项目"可证伪/公开账本"身份 | 维持（最大单一杠杆） |
| 1 | **Modal** ⭐新增 | $30/月额度（无卡口径待核：≥$5/月） | 中高 | 第三方源卡口径分歧；日志 1 天；Volume 计费待核 | **新增，私有前提下首选** |
| 2 | **ClawCloud** ⭐新增 | $5/月永久（GitHub ≥180d，免卡） | 中 | 小厂寿命风险；官方文档未直连复核；10GB 盘紧 | 新增，备份位 |
| 3 | GCP Cloud Run Jobs | 240k vCPU-s + 450k GiB-s/月（官方坐实） | 高 | **需绑卡**（预算告警护栏必须）；镜像 ≤0.5GB（Artifact Registry 免费位）；缓存外置 R2 | 维持次选 |
| 4 | Codespaces + 外部 cron | 120 核时/月 + 15GB，**免绑卡**（官方坐实） | 中高 | 编排复杂（cron-job.org/CF Cron → gh api 起停）；非为 cron 设计 | 维持过渡位 |
| 5 | 本地 Windows 计划任务 | 无限 | 高 | 依赖开发机在线（StartWhenAvailable 可错过补跑） | 维持保底 |
| 6 | self-hosted runner | 0 计费分钟（官方文档坐实） | 中 | $0.002/min 平台费"延期未取消"，尾部政策风险；依赖 PC 在线 | 维持 |
| 7 | Oracle Always Free | 2 OCPU/12GB/200GB | 中低 | 卡门槛 + 热门区容量 + **08-18 后合规实例误禁事故** | **降级**（正选→备胎） |
| 8 | 腾讯/阿里试用机 | 1 个月窗口 | 高（但一次性） | 到期即释放；仅作容器化脚手架 | 新增补充 |

死亡名单（不再列入）：HF Spaces（付费墙）、Koyeb（免费档取消）、Render（512MB+5GB 带宽+cron 收费）、
Zeabur（无免费算力）、CloudBase 免费版（函数锁 3s/256M）、CF Containers（$5/月门）、Serv00（无 wheel）。

**礼貌纪律提醒**：任何 runner 迁移，≥2s 间距 + 指数退避原样随管线走（脚本自带），与宿主无关。

---

## 5. 推荐组合与落地阶梯（全部 $0）

```
发布平面（不动）：本地 build → push gh-pages → Pages 分支模式     ← 已工作，0 分钟
数据平面（可选升级）：data-gateway Worker + R2 + Cron（08-22 §4）  ← $0 未变，按需
runner（本刷新的命题）：
  私有前提下：Modal（首选）→ ClawCloud（并行保险）→ GCP CRJ/Codespaces（备）→ 本地计划任务（保底）
  愿转 Public：GH Actions 无限分钟，一切回到最简
```

落地步骤（私有前提，Modal 路线为例）：
1. 注册 Modal，核实无卡额度口径（$5 还是 $30）——不合适立即切 ClawCloud，双轨成本≈0；
2. 管线容器化：`update_and_deploy.sh`（08-22 §11.2 配方）→ Modal image + Cron 函数 +
   Volume（data/cache）+ gh token secret；**先跑 PHASE 侧 display 管线的 dry 演练**；
3. 双跑一周（Actions 与 Modal 并行，比对导出 JSON 的 as_of/哈希一致性）；
4. 切换：禁用 refresh workflow 的 schedule（保留 workflow_dispatch 应急）；JSON 推回 main
   与 gh-pages 发布链路原样；Actions 分钟回落到纯 CI（月耗骤降 ~1,500 分钟）；
5. 08-22 §10.2 矩阵其余平面（宿主/网关）不受影响，D1/D2 决策继续可无限期推迟。

## 6. 决策清单增量

| # | 决策 | 建议 |
|---|------|------|
| D7′ | runner 选型（修订） | 私有：**Modal 首选 + ClawCloud 并行**；Oracle 降为备胎。转 Public 则 D7 整体作废 |
| D8（新） | 是否转 Public | 一次 secret 全史扫描后由业主裁断；公开=Actions 无限+Pages 免费的最简终局，与项目公开账本身份契合 |
| D9（新） | 试用窗口是否利用 | 仅当需要"实战容器化演练"时用腾讯 1 个月轻量；否则跳过 |

## 7. 来源（2026-09-03 核实）

- 官方直抓：[Cloud Run pricing（Jobs 免费档）](https://cloud.google.com/run/pricing) ·
  [Render pricing](https://render.com/pricing) · [Modal pricing](https://modal.com/pricing) ·
  [CF Containers（需 Workers Paid）](https://developers.cloudflare.com/containers/) ·
  [HF Spaces overview（计算型需付费计划）](https://huggingface.co/docs/hub/spaces-overview) ·
  [Koyeb pricing](https://www.koyeb.com/pricing) · [Zeabur pricing](https://zeabur.com/pricing) ·
  [GitHub Codespaces 计费（120 核时免绑卡）](https://docs.github.com/en/billing/concepts/product-billing/github-codespaces) ·
  [CloudBase 套餐（免费体验版 3s/256M）](https://cloud.tencent.com/document/product/876/127357) ·
  [腾讯云免费试用中心](https://cloud.tencent.com/act/free) · [阿里云试用中心](https://free.aliyun.com)
- 检索佐证：GitHub self-hosted 平台费延期（[changelog](https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/) ·
  [community #182186](https://github.com/orgs/community/discussions/182186) ·
  [The Register](https://www.theregister.com/software/2025/12/17/github-walks-back-plan-to-charge-for-self-hosted-runners/2064954)）；
  Oracle 减配与执行事故（[InfoQ](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/) ·
  [r/oraclecloud 执行帖](https://www.reddit.com/r/oraclecloud/comments/1vflerk/action_required_oci_always_free_update/) ·
  [Oracle 官方 FAQ](https://www.oracle.com/cloud/free/faq/)）；
  ClawCloud $5/月（LowEndTalk 官宣 + CSDN/知乎多源；官方文档站本网络不可达，UNVERIFIED-官方）
- 本仓实核：`gh workflow list --all` / `gh run list` / `gh api repos/Rethymus/Aionis/pages` /
  `refresh-terminal-data.yml` 全文（分钟消耗测算）
