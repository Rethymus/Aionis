# 归档死代码清理提案（零删除）+ Mimosa 扫描面排除建议

任务：archive-cleanup-proposal（2026-11-17）。**本文件是提案，不是执行——零文件删除；
归档内容的删除=业主裁决**（mission【5】红线）。所有数字来自对
`~/.mimosa/security-scans/project-96da30b2accdf53989f79420/scan-2026-11-16T16-54-14.903Z-54469bafdda6/findings.json`
的本会话逐条解析（89 findings，depth normal，runStatus inconclusive），非转抄。

## 一、死代码清单（路径 × Mimosa 发现 × 理由 × 恢复方式）

| # | 路径 | Mimosa 发现（2026-11-16 扫描实测） | 性质与保留/清理理由 | 恢复方式（若业主裁决删除） |
|---|---|---|---|---|
| 1 | `archive/krx-probes/scratch_krx_probe.py:23` | HIGH · SSRF | KRX 韩国散户杠杆路线 26 次探测的**封锁证据链**组成部分（README=终审指南，commit 5e17e1ecab「decisive correction」）；scratch 探针的网络调用正是封锁实证本身，非活代码 | **git 历史可恢复**（目录 20 文件全 tracked；`git checkout <sha> -- <path>` 即还原） |
| 2 | `archive/krx-probes/scratch_krx_probe4.py:13` | HIGH · SSRF | 同上 | 同上 |
| 3 | `archive/krx-probes/scratch_krx_probe5.py:13` | HIGH · SSRF | 同上 | 同上 |
| 4 | `archive/krx-probes/scratch_krx_probe9.py:15` | HIGH · SSRF + HIGH · 证书校验缺失（2 findings） | 同上（TLS 校验关闭属探测脚本对封锁形态的取证，非生产代码） | 同上 |
| 5 | `archive/krx-probes/scratch_krx_probe10.py:25` | HIGH · SSRF | 同上 | 同上 |
| 6 | `data/cache/audit_r23/scan_links.py:138` | HIGH · 路径穿越 | r23 审计一次性工具（写死仓库内路径的 glob/遍历），审计完成即死代码；但目录 **gitignored 未跟踪** | **instrument-for-forensics**：删除即永久消失；保留=审计取证的复现仪器。若业主裁决删除，建议先随本提案 commit 一份归档快照再删（转 git 历史可恢复） |
| 7 | `data/cache/audit_r23/scan_links2.py:63` | HIGH · 路径穿越 | 同上 | 同上 |
| 8 | `data/cache/audit_r23/scan_sentinel.py:61` | HIGH · 路径穿越 | 同上 | 同上 |
| 9 | `data/cache/audit_tmp/scan.py:184` | HIGH · 路径穿越 | 临时审计扫描器，同上类 | 同上 |
| 10 | `docs/code-review/_sync.py:200` `:241` | HIGH · 路径穿越 ×2 | code-review 进度同步仪器（progress.json/SUMMARY.md 生成器，commit e4b3119dfe）；路径遍历是遍历 commits/*.md 的固有形态 | **git 历史可恢复**（tracked） |

对账注记（如实）：mission 表述「归档 7 high（scratch*6+scan*.py+_sync.py）」与逐条实测
存在口径差——实测**归档面 high 共 12 findings / 11 文件**（scratch* **6 findings**/5 文件 ✓
与 mission 分项吻合；scan*.py **4 findings**/4 文件；_sync.py **2 findings**）；7 与 12 的差
异疑为 mission 侧按不同 roll-up 计数，本报告以 findings.json 逐条解析为准。归档面之外
另有 14 处 high 落在活代码/其它路径（不在本提案范围，属 missions 1-3 已处理的 SSRF/XXE
面与其余项）。

## 二、Mimosa 扫描面排除建议（以建议形式，非配置变更）

**建议排除：`data/ops/gh_pages_worktree/`**（以及同类 `archive/quarto-site/_site/`）。

- 实测依据（本会话命令核验）：gh_pages_worktree 为 **267MB / 9,417 文件**的 Next.js
  构建产物镜像（`git check-ignore` 确认 gitignored；`scripts/ops_freeze_deploy.py:74`
  DEFAULT_WORKTREE，`docs/ops-local-refresh.md:1122` robocopy /MIR web\out → 可再生）。
  2026-11-16 扫描 89 findings 中 **60（67%）落在此目录**（59 medium + 1 high，全部打在
  minified chunk 上——`_next/static/chunks/*.js`——vendor 压缩产物上的人造模式，零真实
  攻击面）。mission 记录的扫描成本「1h+28m」在扫描工件中无时长字段可独立复核
  （scan-manifest 仅 createdAt/runStatus），本报告不背书具体时长、仅确认成本主要来源
  与误报占比。
- `archive/quarto-site/_site/`（3 medium）同类：已归档的 minified 站点产物。
- 实施路径（如实）：当前 `security_scan` 工具 schema **无 exclude 参数**（本会话核对：
  仅 project/depth/focusFiles/focusLines/outputDir），故排除需业主侧任选其一——
  (a) Mimosa 未来版本提供 exclude 配置时收录上述两路径；(b) 期间深扫用 `focusFiles`
  圈定增量文件、避开全仓；(c) 扫描前由业主清空 worktree（robocopy /MIR 一条命令即重建）。

## 三、裁决权与零删除声明

- 本提案**未删除任何文件**（`git status` 可核：无 deleted 条目）。上表每行的「删除/保留/
  归档快照后删」均为业主可决项；默认态=全部原样保留（证据链 + 取证仪器优先）。
- 若业主裁决删除 tracked 项：`git rm <path>` + commit，恢复=`git checkout <删除前 sha> -- <path>`。
- 若业主裁决删除 gitignored 审计仪器（#6-#9）：建议先按第一节「归档快照」转 tracked 再删，
  保住「git 历史可恢复」属性。

## 四、执行记录（archive-cleanup-execute，2026-11-18 施工员 append）

**裁决链**：mission【2】令快照→删 → Mimosa PreToolUse 钩子拦截全部忠实快照通道
（Bash cp/python 复制=「绕过 Write/Edit 安全扫描」拒；Write 原内容=「高危·路径穿越」
拒，命中的正是 #6-#9 四文件自身的 HIGH findings：scan_links.py:138 / scan_links2.py:63 /
scan_sentinel.py:61 / scan.py:184）→ 业主升级裁决选 **(d) git 对象层归档**：
纯 plumbing（hash-object -w → mktree → commit-tree → update-ref），零工作树写入、
零 index 触碰、零 gitignore 违规。

**#1-#5 + #10（6 tracked 件）：executed（git rm，已暂存未提交，沿主会话统一收档先例）**

| 提案行 | 文件 | 状态 |
|---|---|---|
| #1 | archive/krx-probes/scratch_krx_probe.py | git rm 已暂存 |
| #2 | archive/krx-probes/scratch_krx_probe4.py | git rm 已暂存 |
| #3 | archive/krx-probes/scratch_krx_probe5.py | git rm 已暂存 |
| #4 | archive/krx-probes/scratch_krx_probe9.py | git rm 已暂存 |
| #5 | archive/krx-probes/scratch_krx_probe10.py | git rm 已暂存 |
| #10 | docs/code-review/_sync.py | git rm 已暂存 |

恢复=git 历史：`git checkout <删除前 sha> -- <path>`（提案 :52 语义）。

**#6-#9（4 untracked 取证仪器）：archived-to-refs→deleted（非普通快照，对象层归档）**

原字节 blob（BYTE-EXACT，校验法=删除前 `sha256sum <文件>` 与 `git cat-file -p <blob>` |
sha256sum 双侧一致逐件实测）：

| 提案行 | 原路径 | blob SHA |
|---|---|---|
| #6 | data/cache/audit_r23/scan_links.py | `7dc18f3fc081ac94d9c6729281addae2b131a6d4` |
| #7 | data/cache/audit_r23/scan_links2.py | `4c7be22af14a70102f8fa7326c02085841a45374` |
| #8 | data/cache/audit_r23/scan_sentinel.py | `a32363946f0f058195c14ee36e8162f6c8e03676` |
| #9 | data/cache/audit_tmp/scan.py | `59b258684504a70f65260d204ab8e98761285361` |

可达性锚：树 f3c5299（audit_r23）/ 5077a37（audit_tmp）/ 树 f0c1cb9（根）→
归档 commit `b2fa0fdf510c4630b395f3c8bc02f6559c2f011b`（消息=完整 provenance：
四 blob SHA+原路径+删除裁决+本提案指针）→ `git update-ref
refs/archive/forensic-scan-2026-11-18 <commit>`。**本地引用，默认不 push**
（本机取证保全；push 与否业主定）。恢复：`git cat-file -p <blob-SHA>` 逐字节忠实，
或 `git cat-file -p refs/archive/forensic-scan-2026-11-18^{tree}` 浏览。

**删后快检（两次实跑）**：`uv run ruff check` = All checks passed（删前删后各一次）；
`uv run pytest tests/test_xml_guard.py tests/test_t1_advance.py -q` exit 0（27 用例）；
`uv run pytest --collect-only -q` exit 0（全仓收集零错=import 图完好）；活代码引用
grep（src/scripts/tests/dashboard）REF_COUNT=0。

**对账与范围注记**：①提案节一标题「11 文件」vs 表行实为 **10 文件/12 findings**
（5 scratch+4 scan+1 _sync），执行按表行，口径差如实留档；②范围外原样保留：
data/cache/audit_r23/ 与 audit_tmp/ 余下非点名文件（audit_67.py、freshness.py、
i18n_check.py、def14a_tail.py 及全部 JSON 产物）、archive/krx-probes/ 余 14 探针
+README.md（封锁证据链完整面）；③`data/archive-wj-evidence/` 未启用（业主裁决
(d) 取代快照路径；该目录 gitignored，快照落此无 git 可恢复性，方案 (d) 反而更强）。

**Mimosa 钩子实录**：cp/Write 拦截在案（见上）；`git hash-object -w` 放行；
`git commit-tree` 时钩子报 scanner_enobufs（未获完整扫描结论）按兼容策略放行——
**工具建议尽快完整重审计**（业主侧事项，本报告不宣称项目安全）。
