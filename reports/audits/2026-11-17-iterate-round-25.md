# iterate 轮 25 交付报告——安全加固三件+T2 对照+T1 推进器+清理提案（2026-11-17）

动工前 `test -f reports/audits/2026-11-17-iterate-round-25.md` → NOT-EXISTS（本文件为
首建）。五批施工全部当晚 ops 通道 idle 窗口内完成（通道 18:05→19:46 运行期间零代码
写入，ok_committed 2c24f3afb 实录在案）。

## 批① ingest-host-guard：ingest SSRF 加固（M）

`src/aionis/ingest/_url_guard.py` 新建——OWASP SSRF Cheat Sheet 蓝本双道校验：
**(a)** 域名白名单第一道（9 处 fetcher 现有硬编码端点域机械收口）；**(b)**
`socket.getaddrinfo` AF_UNSPEC 全 A+AAAA 记录逐 IP 第二道（防 DNS rebinding）；
**(c)** 12 条使命钉定**显式拒绝网段常量表**（127/8、0/8、10/8、172.16/12、192.168/16、
169.254/16、100.64/10、224/4、fc00::/7、fe80::/10、::ffff:0:0/96、64:ff9b::/96；
「Normalize before you compare」：IPv4-mapped/NAT64 规范化后比对）；scheme∈{http,https}
fail-closed。**实测钉**：`100.64.0.1 is_private=False`（载荷级 NAT 漏判=弃 is_private
单判定的依据，测试钉死）。**不做**：pin resolved IP 直连（9 静态域名过度工程且改请求
行为）；TOCTOU 残窗 docstring 如实注记收窄非消除。

9 处接线：ape_wisdom/ark_holdings/theme_etfs 的 `_get`、ff5/news_feed/
news_sentiment_gdelt/reddit_sentiment:470 请求前一行、aionis-data 客户端
`_default_fetch_json` 前、universe **两处调用点**。**如实偏差（重大）**：mission 钉的
universe.py:71 实为全仓 ~15 模块（alpaca/fundamentals/stakes_13d/form4_efts/macro_*/
eval/ff5_residual 等含研究面 fetcher）共享的 `_policy_get` 汇合点——按原方案接线当即
打破 test_http_policy_adapters 5 例（`data.alpaca.markets` 被拒，实跑证据），违反
「语义零变化」自身红线，故改 universe 自己的两处 fetch 调用点接线（同等机械收口）；
universe_ext Wikipedia fetch 不在 9 点清单保持未接线。aionis-data 客户端
`dependencies=[]` 独立可装→stdlib-only 孪生实现（测试钉双表 byte-equal 防漂移）；
**enobufs 兼容放行注记**：孪生实现初版对 getaddrinfo 空返回（含 OS 缓冲压力形态）
为兼容放行（`records or ()` 跳循环=放行），已对齐 canonical 改 fail-closed+测试钉
（`test_client_guard_refuses_empty_resolution`）——如实注记：此为缺陷修正非设计特性，
不据此声称绝对安全（TOCTOU 残窗仍在）。`tests/test_url_guard.py` 14 用例（白名单
通过/先拒后 DNS/私网/环回/CGNAT/mapped-IPv6/NAT64/非 http/多记录全查/DNS 失败
fail-closed/9 fetcher URL 离线 smoke/双表同步钉/客户端路径×2）；
`tests/test_ff5_ingest.py` 补 2 处 `_getaddrinfo` seam mock 保封闭性（断言未动）。

## 批② xxe-hardening：XXE 加固 3 处（S）

`src/aionis/ingest/_xml_guard.py` 新建——手写 defusedxml `forbid_dtd` 语义零新依赖。
**前提本机复钉**：expat 2.6.2（<2.7.2 OWASP DoS 区间）+ stock `ET.fromstring` 5×10
嵌套内部实体展开 100,000 字符零报错 + 外部实体 `ParseError: undefined entity`
（外封内开成立）。**技术要点（实测）**：C 加速 `_elementtree.XMLParser` 不暴露
`.parser`（AttributeError 实录）→ 沿 defusedxml `_get_py3_cls`（源自
test.support.import_fresh_module）掩加速器取纯 Python XMLParser 类，实例
`.parser.StartDoctypeDeclHandler` 抛异常拒 DOCTYPE（DOCTYPE=ENTITY 唯一合法位置=
拒实体全集），纯模块 `ParseError` 重绑 C 版使调用方 except 子句零变化。接线：
form13f.py:126/form4.py:113（沿各自优雅降级契约 except 扩 `XmlDtdForbiddenError`→
warning+`[]`）、politician_trades.py:88（沿传播契约）。`tests/test_xml_guard.py` 7 用例
（billion-laughs 拒/SYSTEM 拒/C 版 ParseError 保持/三入口契约/三 fixture 复用逐值
断言/sys.modules 复原钉）。**如实注记**：测试文件最初含「stock ET 展开负控」断言被
Mimosa hook 以「XML 实体扩展」拦截——故意喂实体载荷恰是工具拦截对象，前提证据保留
为会话实跑输出，安全断言全保留。

## 批③ t2-provider-contrast：T2 对照臂五窗（M）

`scripts/replay_blackbox.py --provider {glm,siliconflow}`（默认 None=冻结名 glm 零变化；
差异=运行时覆盖 meta 入 manifest，冻结字节不动）；**结构性红线**：差异 provider+
`--lessons` 组合 EXIT_USAGE（对照臂零 lessons 落代码层）。实跑五窗 2026-01→05 全
**首试过**（12 次帽退避备而未用零降级；5 调 tokens 2968/77）。**分歧表**
（`runs/t2-contrast/report.md`）：answer 分歧率 **1/5=20%**（唯一 2026-04：GLM
true/0.5041 vs SF false/0.35）；Δp 均值 +0.0402（GLM 略高）/最大 0.1541；Brier
GLM 0.268609 vs SF 0.232419；引擎口径 BSS 两臂同因 y≡0 退化无定义（引擎诚实降级
原话）+辅助 vs 气候值列（公式自算声明，−0.006236 vs +0.129336，n=5 单点效应禁据此
选供应商）。红线实证：v2 冻结 sha 运行前后=GLM 臂 sidecar（257165bf…）；两臂
`lessons_provided=0`；零 contract-fail；逐月 `masking_ok`；y 逐月断言相等。

## 批④ t1-advance-formalize：T1 月级推进器（S）

`scripts/t1_advance.py` 新建（主会话后台循环 exec_68ca17cc 同参正式化）：读
`t1-monthly-plan.txt`→与冻结 config 训练窗逐月一致性校验（不一致 exit 4）→断点月
（首缺月）逐月单月调用→语义化退出码 **0 完成（含幂等 no-op）/1 部分（--stop-after
预算到）/2 窗口耗尽（引擎失败即停绝不重跑到通过）/3 参数错/4 计划-冻结窗不一致**
+`--status` 只读模式（逐年块计数表）。`tests/test_t1_advance.py` 19 用例（计划生成
跨年/解析四类拒绝/进度扫描（header-only 不计、损坏行跳过）/断点判定保序取首缺/
退出码四路径全注入式零子进程零网络）。`t1-breakpoint.md` append-only +51 行使用
说明+**schtasks 挂载模板**（沿晚间通道先例：每日多触发+StartWhenAvailable+退出码 2=
诚实断点非故障注记）——**挂载动作明确待业主执行，本批未代做**。
**主会话循环进度实录**：`runs/t1-monthly-advance/` 目录不存在、`--status` 实跑
**0/120 月**（断点月 2016-01）——主会话循环截至本批收尾零月记录落地，与
t1-breakpoint「0/10 块」收档态一致；引擎与推进器就绪，等 GLM 窗口+业主挂载。

## 批⑤ archive-cleanup-proposal：归档清理提案（S，零删除）

`reports/audits/2026-11-17-archive-cleanup-proposal.md`：11 文件逐行
「路径×Mimosa 发现×理由×恢复方式」（5 krx scratch=封锁证据链 git 可恢复；4
audit scan*=gitignored 取证仪器 instrument-for-forensics；_sync.py=tracked 可恢复）
+ **零删除**（裁决权=业主）+ **Mimosa 扫描面排除建议**：`data/ops/gh_pages_worktree`
（267MB/9,417 文件/gitignored/robocopy 可再生，89 findings 中 **60=67%** 全打在
minified Next.js chunk 上）+ 同类 `archive/quarto-site/_site`；现工具 schema 无
exclude 参数（实测核对）→ 三条业主侧路径。mission「7 high」vs 逐条实测 12 findings/
11 文件对账注记（scratch*6 分项吻合）；「1h+28m」扫描时长工件无字段可独立复核，
如实不背书。

## 安全加固逐 finding 处置表（89 findings → 对平）

数据源：`scan-2026-11-16T16-54-14.903Z-54469bafdda6/findings.json` 本会话逐条解析。

| 处置 | findings | 明细 |
|---|---|---|
| **本批处置（已修+测试钉）** | **12** | 8×SSRF ingest（ape:44/ark:46/ff5:196/news_feed:254/nsg:228/reddit:470/theme:128/universe:71——全部本批接线）+1×SSRF 客户端（aionis_data:48，孪生 guard）+3×XXE（form13f:126/form4:113/politician_trades:88） |
| **提案（零删除待裁决）** | **15** | 12×归档死代码 high（krx 6+audit_r23 3+audit_tmp 1+_sync 2）+3×quarto _site medium |
| **误报面（排除建议）** | **60** | gh_pages_worktree 59 medium+1 high，全打 minified 构建产物 |
| **遗留候选（未处置，如实）** | **2** | scripts/track_b_mounts_run.py:176 路径穿越+scripts/health_check.py:50 SSRF——mission 未点名不扩范围，列后续候选 |
| **合计** | **89** | 12+15+60+2=89 ✓ 对平 |

## 例行核查（本会话实跑）

- `uv run pytest -p no:warnings` → **2640 passed**（6:16，零失败，含 4 个新套件
  url_guard/xml_guard/t1_advance/replay 扩展）；
- `uv run ruff check`（全仓）→ All checks passed；
- `uv run python scripts/anchor_guard.py` → **148/146/0/2/0/576 rc=0**（=轮 24
  基线恒定；本批 ingest 改动零新锚——写入 state/报告后的复测值见 handoff 轮 169
  evidence 行，如增长沿「自然增长沿口径」如实注记）；
- backlog `prediction:`/`outcome:` 双零 **0/0**；
- `ops_local_refresh.py --doctor` → **9/9 layers pass**；
- `ops_local_refresh.py --status` 批前复查：通道 idle（ok_committed 2c24f3afb，
  19:46 完成）。

## 待业主区（只列不动）

1. **T1 挂载**：schtasks 模板已备（t1-breakpoint.md），触发频率/`--stop-after` 帽值
   与是否挂载=业主裁决；T1 十块 120 月推进需 GLM 窗口（当前 0/120）。
2. **归档删除裁决**：11 文件零删除原样保留（提案 §三含恢复模板）。
3. **Mimosa 排除**：gh_pages_worktree+quarto _site 排除路径三选一（提案 §二）。
4. **遗留 2 findings**：track_b_mounts_run.py:176/health_check.py:50 后续批次候选。
5. **T2 续跑与否**：五窗对照已收档；扩大对照窗=新 mission（零 lessons 红线随行）。

## 边界

0 ledger/0 frozen config/0 OOS；研究管线语义零变化（防御面=机械收口+DOCTYPE 拒绝，
请求行为与解析输出对合法输入逐字节不变；universe 汇合点改调用点接线保 ~15 共享
消费者零变化，adapter 测试复绿实证）；Mimosa 红线遵行（网络仅 http(s)+拒绝
localhost/环回/私有/保留地址=guard 常量表；凭据只环境变量读，本批零凭据字面量）；
EXPLORATORY REPLAY 标签全程（T2/T1 面）。

**scanner_enobufs 兼容放行注记（如实，不声称安全）**：本批四次 git commit 的
Mimosa pre-commit 钩子均报「没有得到完整扫描结论（scanner_enobufs）——按兼容策略
继续，但不要宣称项目安全；请尽快重新运行完整审计」。即提交时点钩子扫描器因缓冲
耗尽未产出完整结论、以兼容策略放行；本批安全性依据=2640 passed 全量测试+ruff 全仓
净+本报告逐 finding 处置表（12 处置/15 提案/60 误报/2 遗留对平），**非**依据钩子
放行；业主侧宜择时重跑完整 Mimosa 审计（归档面排除建议生效后成本更低）。
