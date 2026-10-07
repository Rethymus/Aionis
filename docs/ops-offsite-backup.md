# 异地备份 Runbook — restic → Backblaze B2（2026-10-07，轮 221 审计 A.1 落地）

> **为什么**：`data/`（5.7GB，含 GDELT 新闻情绪史 2017→、provider cutoff 探针记录、
> 抓取缓存史）是**不可重取**的——GDELT 只伺服近期窗口，磁盘损失 = 研究数据历史永久
> 丢失。`backup_audit_chain.py`（轮 172）只做**同机** bundle（`data/backups/`），
> 防的是 GitHub 侧事故，防不了磁盘损失。3-2-1 原则缺的最后一环是异地。
>
> **状态**：⛔ 业主门——需业主开 Backblaze B2 账号（~$6/TB/月，5.7GB ≈ $0.04/月）
> 并生成 application key。本文档把开通后的全部步骤写死，开通即用。

## 0. 什么必须备份（优先级）

| 内容 | 位置 | 可重取？ | 优先级 |
|---|---|---|---|
| GDELT 新闻情绪史 + 各 parquet 缓存史 | `data/cache/` | **否**（源只伺服近期） | 🔴 最高 |
| cutoff 探针 / ops marker / 备份 bundle | `data/backups/` `data/ops/` `data/snapshots/` | 否 | 🟡 |
| `runs/ledger.jsonl` | 仓库（已入库）+ 同机 bundle | 是（git+GitHub） | 🟢 已有双异地级 |
| 代码/文档/committed 面板 | git + GitHub + Software Heritage（公共仓自动） | 是 | 🟢 已覆盖 |
| `.env` | 本机 | — | **不备份**（密钥不进备份仓；新机重发） |

## 1. 一次性开通（业主）

1. <https://www.backblaze.com> → B2 Cloud Storage → 建 bucket `aionis-data`
   （Private）。
2. App Keys → Add → 限制到该 bucket，**只给 read/write**（不给 deleteLifecycle 等管理权）。
3. keyID + applicationKey 存入密码管理器（不入 `.env`、不入仓库）。

## 2. 安装与初始化（Git Bash）

```bash
winget install restic.restic          # 或 scoop install restic
export B2_ACCOUNT_ID=<keyID>
export B2_ACCOUNT_KEY=<applicationKey>
export RESTIC_REPOSITORY=b2:aionis-data:restic
export RESTIC_PASSWORD_FILE=~/.aionis-restic-pass   # openssl rand -base64 32 > 该文件
restic init
```

## 3. 备份命令（首备 + 每晚）

```bash
# 只备不可重取的（数据史），不备可再生的 .venv/web/node_modules
restic backup data/cache data/backups data/ops data/snapshots \
  --tag aionis-data --pack-size 64
# 保留策略：30 天内全保，之后 90 天/1 年各保一个，永不丢最长月链
restic forget --keep-within 30d --keep-monthly 12 --prune
```

`--pack-size 64`：B2 按 API 调用计费（class C），大包显著摊薄 parquet 重写费用。

## 4. 接入晚间通道（可选后续，先手工验证两周）

`scripts/ops_local_refresh.py` 的 bundle 步骤后追加同一命令（soft=True——备份
失败不杀通道，只记 `warn:`）。**本接线动通道核心，需按惯例先业主过目再实施。**

## 5. 验证与演练（月度）

```bash
restic check --read-data-subset=10%   # 完整性抽样
restic snapshots                      # 快照链在
# 恢复演练（到临时目录，不动生产）：
restic restore latest --target /tmp/restore-drill && ls /tmp/restore-drill/data/cache | head
```

月度回顾五步（轮 143）可加一步"restic 快照存在 + 上月内有新快照"。

## 6. 供应商与工具选型记录（审计 §F-运维-6 结论）

- **restic**：快照+去重+加密=真灾备；git-annex 官方自称"不是备份系统"；DVC 是
  管线数据版本化非 DR（sha 账本已提供 provenance，缺的是 disaster recovery）。
- **B2** ~$6/TB/月 零出口费档；恢复频繁可换 Cloudflare R2/Wasabi。
- Windows：原生 restic + VSS 处理打开中的文件；Task Scheduler 或晚间通道触发。
