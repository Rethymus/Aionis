# TASK-AUD-08 — 全站视觉/结构审计轮③(post-㉕ 增量面优先;零修复只查证)

- Lane:audit(只读;零修复承诺——发现的问题开列报告,由主线/后续 dev 修复)
- 前置:主线数据补漏+全量导出已完成(你审计的是**刷新后的构建产物** `web/out/`,1,503 页)
- 参照:轮㉕ Z 审计方法(1,502 页 8 项)与轮㉒ V 审计报告格式(`reports/audit/`)
- 你是本轮唯一 audit agent(单进程纪律),分支 agent/aud8 已检出(主仓 worktree F:\ZCodeData\Aionis-wa1)。**零网络、零生产改动、只读 web/out/ 与 web/src/;报告提交 reports/audit/。**

## 审计范围(优先级排序)

1. **post-㉕ 增量面(重点)**:/atlas(四区块 SVG/表格/图例/语境行/稳定条)、/track 的 HorizonRobustnessCard、/dashboard、被刷新数据的页面(congress/executives/stakes/filers/ipo/smart-money/reddit/data-health)。
2. **全站 8 项**(照 Z 审计清单):①渲染垃圾(body 内 undefined/NaN/[object Object]/Infinity 字面量——注意甄别 Next RSC payload 的 `"$undefined"` 内部标记,非垃圾);②标题语义(每页恰一 h1、无跳级——/atlas 与 /track 是本轮新面);③死内链(重点:**新数据带入的 ticker 链接是否过宇宙门**——DEV-K 回归形态;/atlas 与 /track 新卡的内链);④img alt;⑤空交互元素;⑥重复 id;⑦tabindex 正常;⑧表单标签。
3. **i18n 对称**:zh/en key 数与值非空(atlas/track.horizon 新键族全覆盖)。
4. **as_of 披露**:刷新后 daily 面板页头计数窗/水位线是否如实(抽 8 页)。
5. **数据-呈现调和**(抽样复算):track horizon 卡的四相数字 ↔ web/src/data/aionis/horizon_robustness.json 逐字;atlas 稳定条 Δ 值复算;data-health 五数(summary)复算;atlas 语境行 t≈-0.70 复算(由 CI 反推)。

## 交付物

`reports/audit/2026-08-29-site-audit-r3.md`(照轮㉒ V 报告格式:P0/P1/P2/P3 分级+逐条证据[页/位置/实测值]+通过项清单)+ 原子 commit(报告单文件)。**P0=误导性错误渲染,P1=功能/可访问性实质缺陷,P2=披露/一致性,P3=打磨。**

## 边界

不修任何生产文件;不跑 next build(用已有 out/);零网络;测试不许改;0xC0000142/fork 失败=本机病理,sleep 30-60 重试。报告含:扫描脚本摘要(你可用 python 一次性扫描 out/)、分级发现清单、通过项、复算记录。

完成后报告:发现数按级汇总 + top 发现的简述 + commit hash。
