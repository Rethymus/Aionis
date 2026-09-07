---
description: 手动触发 Aionis 终端数据晚间刷新（守卫判定，可强制）
---

# /refresh-data — Aionis 终端数据手动刷新

业主手动触发晚间刷新通道。**默认尊重守卫**（交易日晚间之外/当日已完成会 SKIP）。

执行步骤：

1. 运行守卫：
   `uv run --project F:/ZCodeData/Aionis python F:/ZCodeData/Aionis/scripts/ops_local_refresh.py --guard`
2. 若输出 `RUN`：以后台任务运行完整通道并轮询到退出，把最终 `SUMMARY {...}` 原样报告：
   `uv run --project F:/ZCodeData/Aionis python F:/ZCodeData/Aionis/scripts/ops_local_refresh.py --run`
3. 若输出 `SKIP:<原因>`：原样转述原因。**仅当我在本次对话中明确说了"强制"** 时才加 `--force`
   覆盖守卫执行第 2 步，否则就此结束。
4. 成功推送后尽力核对：`gh run list --workflow=publish-site.yml -L 1`（失败注明"未能核对"）。

红线：绝不伪造成功；绝不 force push；绝不提交 data/、*.parquet、runs 工件或 runs/ledger.jsonl；
绝不修改 frozen 面板/配置/测试。通道自己完成 fetch→导出→契约门→提交→push，你只触发+等待+如实报告。
详情见 docs/ops-local-refresh.md。
