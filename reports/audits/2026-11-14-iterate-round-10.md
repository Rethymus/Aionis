# 2026-11-14 iterate round 10 — 交付报告（aionis-iterate 长周期迭代轮交付物）

四条目：first-month-playbook（M）/ frontier-citation-anchors（S）/ residuals-cleanup（S）/
flywheel-rehearsal（M，核心增量）。全部施工与门禁为本会话（2026-11-13/14 施工员+收尾）实跑；
边界：docs/state/reports lane + 运维面 `scripts/monthly_review.py` __main__ 尾指名改动；
**0 ledger 写 / 0 frozen / 0 OOS / 研究面零改动 / 零装包零新依赖**。收尾五原子批已
push（见 §8）。

## 1. first-month-playbook：首月执行剧本入册（runbook :737-964）

`docs/ops-local-refresh.md` 文末新节「首月执行剧本（2026-11-30 月末全链操作手册）」
:737-964，纯增沿 :697 自治梯文末追加先例——`git diff` 单 hunk `@@ -733,3 +733,232 @@`
（含 residuals-cleanup 锚勘误后累计 237/2，其中 2 del=指名锚值跟改行）。内容：

- **六步链每步命令/预期输出/检查点/失败处置**：--propose 打卡（run_propose :1122，
  exit 恒 0、零提案=合法态）→ 月末会话填 p+bounded answer（WATCHDOG :1354 单行
  JSON {answer,p}；lessons 草稿 bullet 语法 EVENT_OP_RE :1210）→ --verify-bounded
  校验（run_verify_bounded :1507，exit 0/1、首月 none-yet 不误报）→ 下月 outcome
  记录（解析契约 :1046、记法卡面 :965）→ reconciliation+calibration_summary 双面
  （--weekly 逐条 :787 + --lessons 五桶 :1059）→ --append-lessons-from insight 沉淀
  （append_lessons :1289，exit 0/2/3；INSIGHT_HINT :1439 0-2 条）。
- **--month 语义坑钉条**：default_month=上月（:81-88）vs propose=当前月（:1615-1617）
  ——11-30 复盘/写回必须显式 `--month 2026-11`，缺省拿到 2026-10 写错月份块。
- **GBK 坑处置专节**：强制 `--out` 落盘 `reports/monthend/<月>/` 为证据链主载体
  （四 --out 分支 write_text utf-8 :1612/:1637/:1657/:1677；stdout 已修注记 :1601-1604；
  --weekly 默认锚 runs/ops_local_refresh/ gitignored=.gitignore:41 check-ignore 实测）。
- **审计轨迹位置表**（含 runs/ledger.jsonl 零触碰行）+ **oversight 层边界与三互锁
  自查表**（判别=运维面零 LLM 只读 vs 生成=月末 HITL 唯一 LLM 面；沿 :719-723 形态、
  人工自查非 L2 启用）+ **四检查点落点表**（①FinBench arXiv:2607.16229
  confidence-competence gap+gate 时间同构②small-llm-calibration MIT p 聚集 85-95%
  警讯→环1a 反聚集实证③arXiv:2610.25846 verbalized 单通道效度只引注不增设第二通道
  ④arXiv:2604.23049 HITL 解耦+三互锁）+ 次级锚 ERL arXiv:2603.24639（INSIGHT_HINT
  0-2 条上限第三方依据）+ CAGE-1 arXiv:2607.03510 不落剧本一行注记（主用途=L2 晋级
  自检清单留待晋级轮）。

## 2. frontier-citation-anchors：⑬-⑰ + CLE 参照行（backlog 纯增 25/0）

`state/backlog.md` 延伸索引 ⑫ 末行 :118 后纯增（25/0 零删除；prediction:/outcome:
双零区零触碰）。⑬arXiv:2611.16321 决策信息集中中间层（纯架构效率、Aionis 系外部
API 消费者 provider 侧不可触碰）⑭2611.00496 typed 接口生产偏见审计口径与 bounded
answer 固定契约同构 ⑮2611.09264 数字轻推可操纵 System One 实证支持环1b facts only+
固定禁令字面（CALIBRATION_FEEDBACK_NOTE :1427）⑯2611.01015 IJev ⑰2610.42148 Flide
生态延伸登记（内容待引用时一手复核、不转述不装包）；每条照 ⑫ 格式「仅引用零接入」
+adaptation 口径+边界注记（零新依赖零 SDK 零框架）。CLE arXiv:2610.33956 单独一行
登记「飞轮验收口径参照（continual learning，运维面 A/B 设想，未开工）」。

**验证**：六 ID 改前全仓 grep 零命中=真增量；改后 `--propose` 实弹 exit 0 七卡不变/
刷新指令 0 条零幻影键。

## 3. residuals-cleanup：残项清偿勘误批（append-only；handoff 轮 138）

- **monthly 37→39 三处**：复跑 `uv run python -m pytest tests/test_monthly_review.py
  -q --co` 输出尾行 `tests/test_monthly_review.py: 39`（留证；注：后续加回归钉用例数
  会增，读数以当期命令输出为准）。handoff :2952 原行不回改以轮 138 块为准；
  current.md:4 跟改（沿轮 136 current:3 先例）；设计报告 :235 原行不动+文末勘误条。
- **numstat 68→69**：复跑 `git show --numstat da29c32bd6` = `69 0` scripts/
  monthly_review.py / `62 0` tests/test_monthly_review_propose.py（tests 62 一致，
  轮 8/9 其余 numstat 声明审计全核一致）；轮 8 报告文末勘误条 §7；提交信息不可回改
  以勘误条为准。
- **runbook 旧锚 :1399 双处**：本批 grep 实测 :292+:343 两处（轮 137 仅登记 :343 一处）
  → 现值 `:1571`（--propose argparse help 折行 :1571-1572，落笔前亲测、与自治梯节
  引法一致）。
- **「另两处 ±1」**：审计 grep（±1/+-1/差 1/偏 1 于设计报告/handoff/轮 8 报告）零命中
  未定位——按一处实锤（37→39）落账+待源如实注记，不造数不追猜。

## 4. flywheel-rehearsal：GBK 甲胄 + tmp 九齿轮演练（核心增量）

**代码**（numstat 15/0+53/2）：`scripts/monthly_review.py` 仅 __main__ 尾
（raise SystemExit(main()) 前）对 stdout+stderr 双流
`reconfigure(encoding="utf-8", errors="replace")`，先于 main() 运行故 argparse 面同护；
在册锚 :1026-:1589 全零漂移，三处 (p−y)² 字面（U+2212+U+00B2 共 6 处×3 行
:966/:1022/:1118）零触碰——`test_reconcile_rendering_byte_identical_after_ring1a_lift`
首钉保持绿即证。tests 新钉 `test_cli_survives_gbk_child_environment`：subprocess
`-I`+剥离 PYTHONIOENCODING/PYTHONUTF8/PYTHONLEGACYWINDOWSSTDIO+管道复现 GBK 子进程
环境，断言 --lessons rc==0+stdout 严格 UTF-8 解码含「(p−y)² 同口径取均值」字面+
refuse 负例 rc==3+stderr 严格 UTF-8 可解；套件 39→40 用例（文件头「zero subprocess」
声明如实修订为单一例外）。

**修前实测辨明（与交办「必崩」口径的偏差，如实记）**：裸子进程
`python -I -c "print('（p−y）²')"` UnicodeEncodeError '\u2212' 一手复现（-I 忽略
PYTHONIOENCODING/PYTHONUTF8、stdout=gbk 亲测）；但**经 CLI 修前不崩**——stash 隔离
实测（可解析夹具、真 U+2212 入 stdout、GBK 子进程管道）rc=0 无 UnicodeEncodeError，
因 main():1601-1604 自 148fdd62ea 起已护 stdout；修前实测**真红面**=refuse 路径
stderr 裸 GBK 字节（严格 UTF-8 解码必败=新钉红面）+stderr/argparse 对未来非 GBK
字面无甲胄。修法仍按任务书 __main__ 尾零漂移方案；测试 docstring 按实测措辞。

**九齿轮 tmp 演练**（系统 tempdir、紧凑契约行形、synthetic 标注、毕即销毁零残留）：
①分列四行（甲/乙 resolved+高带标 (p−y)²=0.040/0.490、丙 pending due 未过、丁 p=0.3
resolved 无带标）②五桶 Wilson (0.2065,1.0000)/(0.0000,0.7935) 与设计报告 :235 钉值
**逐位一致**+分列行 p<0.5 已对账 1/p 未填 0/pending 1+mean Brier 0.340（手算
(0.04+0.49+0.49)/3 吻合）③stdout 双路 rc=0（直承管道+GBK 子进程严格 UTF-8 解码字面
完好；真 tty 控制台本 harness 不可得如实记）④INSIGHT_HINT 指引行在（resolved=3>0）
⑤写回 rc=0 handoff 块 0→1⑥聚合读回「Latest block month=2026-11; active entries 1」
⑦契约门负例 rc=3 且 handoff 字节不变⑧同月重复 rc=2 字节不变（审计未单独跑项本轮补）
⑨修后 GBK 复现路径 lessons rc=0/refuse rc=3 且 stderr 严格 UTF-8。

**演练发现两处置**：render_card 卡面展示形「（judgments: p=」不含解析器连串「（p=」
子串（_collect_prediction_records :1036-1042 契约、_prediction_backlog_text 权威
夹具形）→月末粘贴须落紧凑契约行形，已勘正入剧本步 2；演练夹具注释行自污染解析器开
伪记录（轮 136 needle 教训重演）净化重跑齿轮①②。

## 5. 门禁终态（施工+收尾会话实跑）

三套件 `uv run pytest -q tests/test_monthly_review.py
tests/test_monthly_review_propose.py tests/test_monthly_review_watchdog.py` →
**exit=0**（monthly 40=39+新钉 / propose 34 / watchdog 25）；`uv run ruff check`
全仓 All checks passed；`--propose`/`--lessons` 实弹双 **rc=0**；`grep -c
"prediction:"/"outcome:" state/backlog.md` = **0/0** 不变；动码前后 `--status` 均
ok_committed（95a841a9e3，2026-11-13T19:26:55 收工非 running）。

## 6. state 入册与轮次（138/139）

residuals-cleanup 交办指名 handoff **轮 138** 块；其余三条目收官顺延**轮 139** 块
（「核对最新号」条款）。current.md 顶部新条「active (11-13，handoff 轮 138-139)
【iterate 轮 10 四条目收官…】」；:4 用例数 37→39 跟改。待业主区不变。

## 7. 待业主区（只列不动）

- billing 解锁（doctor L7 根因）；
- L2 启用钥匙与晋级门槛数值定标（X/N/Y/M 待 2026-11 基线月数据）；
- L3 定义权；
- ZCode 月末提示词模板 {answer,p} 同步确认。

## 8. 提交与推送（收尾会话，2026-11-14）

五原子分批（Conventional Commits）+ `git pull --rebase`（up to date）后
`git push origin main` 一次成功（`e9cf4e42aa..53b8da4b2b main -> main`，rc=0）：

| 哈希 | 类型 | 内容 |
|---|---|---|
| `e0a825557a` | docs(ops) | 首月剧本 runbook :737-964 + 锚勘误 + 行形勘正（237/2） |
| `63c30cf42a` | docs(frontier) | backlog ⑬-⑰+CLE（25/0） |
| `eaa7e111a6` | docs(reports) | 两报告文末勘误条（10/0+8/0） |
| `5479bcb144` | feat(ops) | GBK 甲胄+回归钉（15/0+53/2） |
| `53b8da4b2b` | docs(state) | 轮 138/139 入册+current 顶部新条 |
