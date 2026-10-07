# 新机器 Bootstrap — 从零到能跑（2026-10-07，轮 221/222 落地）

> 目标：一台新 Windows 机器（Git Bash 环境）从 clone 到
> `just check` 绿 + 晚间通道可运行。约 30-60 分钟（含数据抓取）。

## 0. 前置

- Windows + [Git for Windows](https://gitforwindows.org/)（Git Bash）
- Python ≥ 3.10、[uv](https://docs.astral.sh/uv/)：`winget install astral-sh.uv`
  （或 `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`）
- [Node.js ≥ 20](https://nodejs.org/) + `corepack enable`（web 终端用 pnpm）
- [just](https://github.com/casey/just)：`uv tool install just`
- Git 凭据：PAT（细粒度、`contents:write`、**设过期日**——轮 89 纪律）

## 1. 克隆与安装

```bash
git clone https://github.com/Rethymus/Aionis.git && cd Aionis
just install            # = uv sync --all-extras
```

## 2. 防线（一次性）

```bash
uv tool install pre-commit
pre-commit install       # ruff + 暂存区守卫（data/·parquet·.env·>5MB）
```

手动等价物（不装 pre-commit 也可用）：`just guard`。

## 3. 验证世界如描述（会话协议第 3 步）

```bash
just check               # ruff 0 + pytest 全绿（封闭套件，无需任何 key）
```

## 4. 数据与密钥（研究/通道需要，测试套件不需要）

```bash
cp .env.example .env     # 填 FRED_API_KEY / TIINGO_API_KEY / ALPACA_* / REDDIT_*（LLM key 可选）
just fetch               # 一次性抓取 588 只 PIT 宇宙（可断点续跑、礼貌限速）
```

`.env`、`data/`、`*.parquet` 永不入库（守卫强制）。

## 5. 常用入口

| 命令 | 作用 |
|---|---|
| `just check` | ruff + 全量 hermetic 测试 |
| `just evidence` | 证据级联正典顺序重渲染 + 契约门（交互改导出器后**必须**走这个，不要手跑各导出器） |
| `just run` | 一条 confirmatory run（config_committed 先于结果） |
| `just dashboard` | 本地 Streamlit 仪表盘 |
| `just web` | web 终端开发伺服 |
| `just lane` | 手动触发晚间通道（正常情况让自动化跑，见 `docs/ops-local-refresh.md`） |

## 6. Windows 坑位备忘（实测）

- **路径**：一切脚本用 `Path` 相对仓库根；Git Bash 的 `/tmp` 与 Python 的
  TEMP 不是同一目录，跨工具传文件用绝对 Windows 路径。
- **本地伺服 web/out 截图/调试**：站点以 `/Aionis` basePath 导出，直接挂
  `web/out` 会 404 全部 `_next` 资源——需在临时目录造 junction
  `site-root/Aionis -> web/out` 再 `python -m http.server -d site-root`。
- **junction**：`cmd //c mklink //J`；删除用 `rmdir`（不加 /s——删的是链接不是目标）。
- **Playwright 截图**：`screenshot(animations="disabled")` 会把 recharts v3
  入场动画冻结在 0%（内容全隐形）——不要传该参数。

## 7. 晚间通道（可选，接手运维时）

见 `docs/ops-local-refresh.md`（架构/失败模式/手动操作）与
`docs/ops-offsite-backup.md`（异地备份——**新机器接手后第一件事是确认备份
仓库可写**）。
