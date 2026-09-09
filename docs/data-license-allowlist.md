# 数据 / 依赖许可白名单（License Allowlist）— G1 的可审计落表

> 状态：**v0.2 · 2026-09-09 · `docs/data-intake-rubric.md` G1 的配套文档**（v0.1 · 2026-07-28）。
> 范围：Aionis 接入的**每个**第三方数据集 **和** 每个运行时依赖都必须落在 ACCEPTED 列。
> 原则：Aionis 自身代码是 **PolyForm-Noncommercial-1.0.0**（2026-09-09 起由 MIT 变更，
> 见 [`decisions/ADR-013-polyform-noncommercial-license.md`](decisions/ADR-013-polyform-noncommercial-license.md)；
> `pyproject.toml:7`）——所有**入栈物**仍必须 **MIT-compatible**（宽松许可允许合法并入非商用
> 项目），否则就是法律雷。新增数据 / 依赖前先查此表；表外者须先确认其 license 落在
> ACCEPTED 列，否则按 G1 = REJECT。

---

## ACCEPTED（许可通过）

| License | 一句话说明 |
|---|---|
| **MIT** | 最宽松；可商用 / 改 / 闭源分发，仅留版权声明。入栈依赖的主力许可。 |
| **Apache-2.0** | ≈ MIT + 显式专利授权 + 贡献者条款；带专利的项目首选。 |
| **BSD-2-Clause** | MIT 级宽松，两条款（版权声明 + 免责）。 |
| **BSD-3-Clause** | MIT 级宽松，三条款（额外「不得用名字背书」）。 |
| **CC0-1.0** | 公共领域弃权；数据 / 代码皆可，无任何限制。 |
| **CC-BY-4.0**（数据） | 署名即可商用 / 改编——**数据**首选（EPU 用此）。注：仅限数据；代码用 CC-BY 另议。 |
| **NCSA / University of Illinois** | `arch` 用的许可，**法律上 ≈ BSD-3 等价**（保留版权声明 + 不用名字背书）；MIT-compatible。 |
| **SEC / US-gov public domain** | 美国联邦政府作品 = 公共领域（17 U.S.C. §105）；EDGAR、FRED / ALFRED 宏观源皆属此。 |

## REJECTED（许可拒绝）

| License | 拒绝原因 |
|---|---|
| **Commons-Clause** | 在 OSI 许可上加「不得将本软件作为产品出售」——**非自由**，OSI 不承认；带传染性限制。 |
| **GPL-2 / GPL-3** | Copyleft：分发派生作品必须同 GPL——接入会把 Aionis（MIT）「传染」成 GPL。 |
| **AGPL-3** | GPL + 网络使用也触发开源义务——SaaS 场景的法律雷，比 GPL 更严。 |
| **LGPL** | 弱 copyleft；库可被闭源链接，但改动 LGPL 部分须开源——边界复杂，规避。 |
| **CC-BY-NC** | NonCommercial——禁商用。注：Aionis 自身 2026-09-09 起为 PolyForm-NC（ADR-013），但那是对**自有代码**的处分权；**外部** NC 物仍不入栈——避免把第三方的额外限制与传染条款叠加进本已清晰的许可链。 |
| **CC-BY-NC-SA** | NC + ShareAlike——禁商用 + 衍生须同许可；**双重雷**（Financial PhraseBank 用此）。 |
| **no-license / 未声明** | 无 license = 默认「保留所有权利」（All Rights Reserved）——**不可用**，等同 proprietary。 |
| **proprietary / 须授权** | 未获书面授权前一律拒。 |

---

## 项目内实例（已核对）

**ACCEPTED（在 `pyproject.toml` / `ingest/` 中实际使用）**：

| 物 | License | 出处 |
|---|---|---|
| `lightgbm` | MIT | `pyproject.toml:15` 依赖 |
| `purgedcv` | MIT | `pyproject.toml:24` 依赖 |
| `arch` | NCSA（≈ BSD-3） | `pyproject.toml:27` 依赖 |
| `hanshof/sp500_constituents` | MIT | `ingest/universe.py:3`（「MIT-licensed reconstructions」） |
| `pierrebrunelle/sp500-historical-constituents` | MIT | `ingest/universe.py:3` 同 |
| `streamlit` | Apache-2.0 | `pyproject.toml:42`（dashboard extra） |
| `plotly` | MIT | `pyproject.toml:41`（dashboard extra） |
| SEC EDGAR / ALFRED（FRED） | US-gov public domain | `ingest/fundamentals.py`、`features/macro_surprise.py` |

**REJECTED（评估后未接入）**：

| 物 | License | 为何拒 |
|---|---|---|
| `vectorbt` | Commons-Clause | 非 OSI 自由；限制商用出售 |
| `backtrader` | GPL | Copyleft 传染 MIT 栈 |
| `pypbo` | AGPL | 网络使用触发开源义务 |
| `arctic_shift` | 无 license | 默认 All Rights Reserved |
| Financial PhraseBank | CC-BY-NC-SA-3.0 | NC + SA，禁商用 + 衍生须同许可 |

---

> 本表是 `docs/data-intake-rubric.md` G1 的落表实现。G1 = license 必须落 ACCEPTED 列；
> 与 G2（PIT 时点）、G3（无回改契约）共同构成第三方数据的接入门槛。
