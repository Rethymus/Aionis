# Reproducibility & Data-Availability Statement

> 状态：**v0.1 · 2026-08-05 · PROPOSED · 业主审阅**。本文档诚实声明 Aionis 结果如何被独立方复现，
> 以及哪些数据可/不可随论文分发。设计为可被 `docs/methods-and-results-draft.md`（§6 局限 / 附录）
> 与 arXiv preprint 的 data-availability 段直接引用。
>
> 一句话：**Aionis 是 reproducible-by-construction**——原始 PIT 数据按各源 ToS 不再分发（gitignored），
> 但冻结 config 注册（`config_committed` ledger）+ 版本钉死的依赖 + 全套 fetch 脚本使任何独立方可从公开源
> bit-identical 地重建结果（H6 确定性，断言）。

---

## 1. 可复现性构造（anti-leakage 即复现契约）

Aionis 的反泄漏纪律**本身就是复现契约**——同一组机制既防止 rerun-to-significance，也使结果可独立验证：

| 机制 | 可复现含义 | 落地证据 |
|---|---|---|
| `config_committed` BEFORE result | 每个冻结 config 的 sha256 在任何 OOS 指标观察**之前** append 进 `runs/ledger.jsonl`（append-only，TRACKED）。改 config = 新 ledger 行，绝不静默覆盖 | `runs/ledger.jsonl` 行 #28/#30/#34/#37/#41/#42/#49 等 |
| H6 确定性 | `n_jobs=1`、所有 seed=0、`uv.lock` 版本钉死 → IC 系列**与**原始 score 跨重跑 bit-identical（asserted） | `tests/`（H6 双跑断言）、`uv.lock` |
| PIT fetch 脚本 tracked | 全部数据采集脚本是 tracked 源码，从公开源拉取 + 落 `data/cache/*.parquet`（gitignored artifact） | `scripts/phase_b_fetch.py`、`scripts/phase_d_fetch.py`、`scripts/ashare_price_fetch_csi300.py`、`scripts/track_b_fetch_volume.py` |
| 配置 → 结果可追溯 | 每条 ledger 行的 `config_sig` 指向一个冻结 config；从该 config 跑对应 runner 必然重现同一 IC（H6 保证） | `scripts/track_c_confirmatory_run.py:assert_h6_identical`（双跑 `.equals` + `.tobytes` + CSV hash 三重） |

**含义**：复现 = clone 仓库 + 自备 API key + 跑 fetch 脚本 → `data/cache/` 重建 → 跑对应 runner → 与 ledger 记录的指标 bit-identical（H6 断言会捕获任何漂移）。

---

## 2. 数据源与许可（逐项）

| 数据 | 用途 | 源 | License | 入库? | 再分发? |
|---|---|---|---|---|---|
| US 端末价格 + 基本面 | Track B/C 等价格与基本面特征 | Tiingo（API key） | Tiingo ToS（research） | `data/` gitignored | **否**（ToS 禁再分发原始数据） |
| US 交易价格（备用） | 价格校验 | Alpaca（API key） | Alpaca ToS | gitignored | **否** |
| SEC EDGAR 申报 | 13D（filed-date）、8-K 盈利、SIC | EDGAR | **US-gov 公共领域**（17 U.S.C. §105） | gitignored（重建产物） | **可**（公共领域） |
| FRED / ALFRED 宏观 vintage | DFF/CPI/VIX 等宏观 surprise | FRED/ALFRED | **US-gov 公共领域** | gitignored | **可** |
| VIX | no-revision 合同（非 vintage） | FRED（VIXCLS） | **US-gov 公共领域** | gitignored | **可** |
| A 股价格（CSI 300） | Track C CN 区 | baostock | 免费研究用（适配器 lazy import，非 core dep） | gitignored | 否（按 baostock 使用条款） |
| S&P 500 PIT 成分 | universe（`constituents_on(t)`） | `hanshof/sp500_constituents` + `pierrebrunelle/sp500-historical-constituents` | **MIT** | gitignored（重建产物） | **可**（MIT） |
| Reddit sentiment（exploratory） | Phase C/D 探索（forward-only，无 backfill） | PRAW（API creds） | PRAW BSD-2；Reddit ToS | gitignored | **否**（Reddit ToS internal-only） |

> 完整许可审计见 [`docs/data-license-allowlist.md`](data-license-allowlist.md)（G1 配套文档）。Aionis 自身是 MIT
> （`pyproject.toml`）；全部运行时依赖落在 ACCEPTED 列（MIT/Apache/BSD/NCSA/US-gov public domain）。
> 明确排除：vectorbt（Commons-Clause）、backtrader（GPL）、mlfinlab（paid）、pypbo（AGPL）、nautilus_trader（LGPL）。

---

## 3. 复现步骤（独立方）

```bash
# 1. clone（MIT；含全部 tracked 源码 + fetch 脚本 + 冻结 ledger）
git clone <repo> && cd Aionis
uv sync --all-extras                  # 装版本钉死的依赖（uv.lock）

# 2. 自备 API key（写入 gitignored .env；不入库）
#    必需：TIINGO_API_KEY、FRED_API_KEY（免费）
#    可选：ALPACA_KEY/SECRET、REDDIT_CLIENT_ID/SECRET（探索性 Reddit 臂）
cp .env.example .env  # 填入自有 key（.env 为 gitignored）

# 3. 重建 PIT 数据缓存（从公开源；礼貌 ≥2s spacing + 退避）
uv run python scripts/phase_b_fetch.py        # US 基本面 + 价格 + 成分
uv run python scripts/phase_d_fetch.py        # SIC + 13D
uv run python scripts/ashare_price_fetch_csi300.py   # A 股价格（CSI 300）

# 4. 跑冻结 confirmatory runner（ledger 行 #49 的 config_sig 指向 frozen #48）
uv run python scripts/track_c_confirmatory_run.py
# → combined rank-IC −0.0088，J-T look-1 NOT_EQUIVALENT，H6 双跑 bit-identical（与 ledger #49 一致）
```

**预期**：步骤 4 的 H6 断言（`assert_h6_identical`：双跑 IC 系列 `.equals` + 原始 score `.tobytes` + CSV hash）
会在任何漂移时 fail。因此独立方跑出的结果与 `runs/ledger.jsonl` 记录的指标 bit-identical——这是 by-construction
的，不是"希望一致"。

---

## 4. 不入库的理由（诚实）

`data/`、`*.parquet`、`.env` 被 gitignore，原因：
1. **凭证**：`.env` 含 API key（秘密，永不入库）。
2. **ToS**：Tiingo/Alpaca/Reddit 原始数据禁止再分发。
3. **体积**：完整 PIT 面板数百 MB；git 不适合大二进制。
4. **可重建**：fetch 脚本 + 公开源使数据可 bit-identical 重建（H6 保证）——入库是冗余且违反 ToS。

**入库且可审计的**（TRACKED）：
- `runs/ledger.jsonl`（append-only 冻结 config 注册 + 结果指标）。
- 全部 `src/`、`scripts/`、`tests/`、`docs/`、`decisions/`（ADR）、`config/`（E3 合约）。
- `uv.lock`（版本钉死）。

---

## 5. 给审稿人 / 编辑的声明（cover-letter 用的简版）

> Aionis 的全部结果可独立复现。冻结配置的 sha256 在任何 out-of-sample 指标观察之前注册进 append-only 的
> 公开 ledger（`runs/ledger.jsonl`），且依赖版本经 `uv.lock` 钉死、所有随机种子固定为 0、单线程执行——
> 使 IC 系列与原始 score 跨重跑 bit-identical（由测试套件断言）。原始 point-in-time 数据按各源服务条款不再分发，
> 但全部采集脚本是仓库的 tracked 源码，配合公开数据源（SEC EDGAR、FRED/ALFRED 为 US 公共领域；
> Tiingo/Alpaca 需用户自有 key）使任何独立方可从公开源 bit-identical 地重建全部结果。

---

## 6. 不越界声明（PROPOSED）

- `[F]` 本文档是复现/数据可用性声明；未写 ledger；未改 config / prereg / ADR / data / E3。
- `[F]` 数据源 license 陈述基于 `docs/data-license-allowlist.md`（G1 配套文档）+ 各源公开 ToS。
- `[I]` 业主决策：① 是否随论文附一个 frozen snapshotted `data/cache/`（仅公共领域子集：EDGAR/FRED/hanshof MIT）作为
  便利 replication package（Tiingo/Alpaca 部分仍需用户自有 key 重建）；② 是否提供 DOI / Zenodo 归档（外发，需点头）。
