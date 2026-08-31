# 数据接入 7 门（Data Intake Rubric）— 第三方数据集进 Aionis 前的强制清单

> 状态：**v0.1 · 2026-07-28 · 治理文档（durable registry 的一部分）**。
> 范围：**任何**第三方数据集（含 exploratory / 一次性探查）进 Aionis 前，**必须**全部 7 门过关。
> 与 `docs/phase-b-preregistration.md` §9（durable registry）、`CONTRIBUTING.md` §2（ledger 纪律）
> 同源——抗泄漏锚点是「config / data 的 sha256 先于 OOS 结果入 ledger」；本 rubric 把同一条纪律
> **前移到数据接入**这一更早的环节。任一门不过 → 该数据**不得**进 confirmatory / Phase-B。

---

## 0. 为什么是这 7 门

Aionis 是 anti-leakage 研究。泄漏不止发生在「用未来标签训模型」——**数据本身**就会泄漏：

- license 把代码/数据变成法律雷（**G1**）
- 没有 PIT 时点就没有「当时可知」（**G2**）
- **provider 静默回改历史**是最隐蔽的杀手（**G3**）
- 不可复现 = 不可审计（**G4**）
- 未经 PIT 验证就当 confirmatory（**G5**）
- selection / survivorship 当 ground truth（**G6**）
- 不礼貌被封 = 断供 = 数据腐烂（**G7**）

判定矩阵：**G1 + G2 过 + G3 已验证** → 可 confirmatory；**G1 + G2 过 + G3 不可证** → 快照冻结 +
exploratory；任一门不过 → 仅 exploratory 或 REJECT。

---

## G1 — License allowlist（许可协议白名单）

- **规则**：仅 MIT / Apache-2.0 / BSD-2/3-Clause / CC0 / CC-BY-4.0（数据）。拒绝 Commons-Clause、
  GPL、AGPL、LGPL、CC-BY-NC-SA、无 license。
- **机制**：当前为**隐式规范**——`hanshof / pierrebrunelle` 因 MIT 而被选（`ingest/universe.py:1-18`
  docstring，明示「Two independent MIT-licensed reconstructions」）；项目自身 `pyproject.toml:7`
  `license = { text = "MIT" }`。G1 的可审计落表见配套文档 `docs/data-license-allowlist.md`。
- **通过**：EPU = CC-BY-4.0 ✓（数据许可，可商用、可改）。
- **失败**：Financial PhraseBank = CC-BY-NC-SA-3.0 ✗（非商用 + 相同方式共享，与 Aionis 的 MIT
  身份冲突）。

## G2 — PIT / as-of 时点（point-in-time）

- **规则**：每个观测带一个「当时可知」的 timestamp；t 时刻的值不得依赖 >t 的信息。对**不透明
  的指数 / 指标**，要求 provider 公布 release-lag / as-of 声明。
- **机制**：`ingest/fundamentals.py:pit_align`（`merge_asof(direction='backward')` 钉 filed-date、
  NaN-before-first-filing、绝不替成 period-end）；`features/macro_surprise.py` 的 ALFRED vintage
  as-of join（`merge_asof(..., allow_exact_matches=False)`，prior-month base 必须严格早于发布日）；
  `ingest/universe.py:constituents_on`（取 `≤ date` 的最新成员快照，**无 forward-fill**）。
- **通过**：SEC XBRL——每条 fact 带 `filed` 日期，由构造 PIT ✓。
- **失败**：某指数 provider 无 vintage 声明（只给一条「现值」序列，无法判断某历史值是何时的）→
  **REJECT**（G2 不可证，无法构造 PIT）。

## G3 — No-revision contract（无回改契约——**杀手级泄漏**）

- **规则**：provider **不得**追溯重算历史。若不可证：首次接入即**快照 + sha256 = 冻结真相**；
  之后的任何修订 = **新数据集版本 = 新 ledger 行**，**绝不**静默覆盖。
- **机制**：`ingest/universe.py:_sha256`（raw cache 哈希、日志记录）；`runs/ledger.jsonl`
  append-only（config / data sha256 行，`CONTRIBUTING.md` §2 冻结 config 变更必须 append）。
- **失败（强制快照）**：**EPU 不过 G3**。policyuncertainty.com 明示——
  - 「data from the preceding two months may be revised slightly」；
  - 「each day we update the data from the previous 30 days」；
  - 且有全历史「Revisions to US Index」重算。

  → 历史值随时间漂移，**不能**当 frozen truth；**必须**首次接入快照 + sha256，之后修订 = 新版本 / 新行。

## G4 — Reproducibility / snapshot discipline（可复现）

- **规则**：第三方接入本身是一个**冻结产物**——在 ledger 记录 data-sha256 + as-of + source-URL +
  fetch-ts。
- **机制**：`extraction/extract.py:1-6`（cache key = sha256(source_text)，docstring「Cache key =
  sha256(source_text)」）；`data/cache/` sha256-pinnable（`ingest/universe.py:17`、
  `ingest/fundamentals.py:10`、`features/macro_surprise.py:31` 均明示）；`runs/ledger.jsonl` 行结构。
- **通过**：hanshof CSV / pierrebrunelle tar.gz / ALFRED JSON 全部落 `data/cache/`，rerun 零 HTTP ✓。

## G5 — Exploratory-only by default（默认探索性）

- **规则**：未通过 G2 + G3 PIT 验证的第三方数据 = **EXPLORATORY ONLY**（ledger `mode: exploratory`）；
  **绝不**confirmatory / Phase-B。
- **升格条件**：G2 + G3 已验证，**或**已冻结快照 + 已知发布日历。
- **机制**：ledger `mode` 字段（`exploratory` / `confirmatory` / `freeze`）；
  `phase-b-preregistration.md` §9 durable-registry（同 sha256 重跑免费、改 config = 新行）。
- **含义**：EPU（G3 ✗）即便快照后也只能 `mode: exploratory`，不进 headline。

## G6 — Selection / survivorship honesty（选择 / 幸存者诚实）

- **规则**：社会 / 政策类数据有 selection bias（哪些股票被讨论、哪些政策被索引）——**声明为 scope
  限制，绝不当 ground truth**。
- **机制**：`ingest/universe.py:mask_panel_to_pit`（survivorship 诚实：某日截面 = 当时的 PIT 成员，
  **非**今天的 500）；selection-doc §8.4「headline = 保守上界」；TCR frame（观测 = latent 世界状态的
  **含噪**观测，非真相）。
- **应用**：Reddit / StockTwits / EPU 这类「被讨论度」数据天然 selection-biased → 写进 scope 限制，
  不作为可定价真值。

## G7 — Politeness / ToS（礼貌 / 服务条款）

- **规则**：限速、遵守 robots.txt、不批量爬、用 descriptive User-Agent、尊重源 ToS。
- **机制**：**礼貌是 binding**——`ingest/fundamentals.py:9`（SEC fair-access ≤10 req/s，line 92
  `time.sleep(0.15)` 落实）；`ingest/market.py:173`（`time.sleep(0.4)` 符号间，line 73 / 122
  `time.sleep(1.0)`）；`ingest/universe.py`（User-Agent `aionis/0.1`，line 123 / 154）；
  `fundamentals.py:company_facts` 指数退避（line 99，429 / SSL reset 重试）。
- **含义**：不礼貌 = 被 rate-limit / 封 IP = 断供 = 数据腐烂 → 直接破坏 G4。

---

## 接入决策汇总（intake decision summary）

| 数据集 | G1 | G2 | G3 | 结论 |
|---|---|---|---|---|
| **EPU**（Economic Policy Uncertainty） | ✓ CC-BY-4.0 | ✓ 有日 timestamp | ✗ 回改历史 | **快照强制 + exploratory**（修订 = 新版本 / 新行） |
| **Reddit / StockTwits**（历史 sentiment） | — | — | — | 无 permissive 历史源 → **仅前向采集**（PRAW + FinBERT），不接入历史 dump |
| **VIX**（via FRED / ALFRED） | ✓ US-gov public domain | ✓ ALFRED as-of join 已在栈内 | ✓ vintage 不可回改 | **无需新接入**——`features/macro_surprise.py` 同路径已 PIT-safe |
| **参照站 参照站** | — | ✗ 非 PIT-safe | — | 见 [[aionis-参照站-data-source]]；仅 Phase C/D exploratory、仅 SEC-immutable surfaces（Aionis 经 EDGAR 已有）→ **基本冗余** |

---

> 本 rubric 是**前置闸门**——把 `phase-b-preregistration.md` §9「sha256 先于结果入 ledger」的纪律，
> 从实验环节前移到**数据接入**环节。数据不过 G3 快照 + sha256，就没有可信的 ledger 行可言。
