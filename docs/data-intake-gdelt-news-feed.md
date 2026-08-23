# 数据接入 7 门 — GDELT 市场新闻流（news_feed / /news 面板）

> **状态**：**v0.1 · 2026-08-22** · exploratory-only display module。
> **范围**：GDELT Doc 2.0 `artlist` 市场新闻流通过 7 门强制清单，所有第三方数据集进 Aionis 前 **必须** 全部过关。
> **引用**：主 rubric 见 `docs/data-intake-rubric.md`；GDELT 先例见 `news_sentiment_gdelt.py`（themes 的 news_sentiment 主题）。本文档为新闻流面板专用准入评估。

---

## 数据源概述

**GDELT Doc 2.0 API**（`https://api.gdeltproject.org/api/v2/doc/doc`）是全球新闻文章的机器索引。本模块只用 `mode=artlist`：一次有界请求（≤200 条）返回近期市场要闻的**元数据**——`title` / `url` / `domain` / `seendate`（GDELT 首见 UTC 时间，15 分钟分辨率）/ `language` / `sourcecountry`。**文章正文留在出版商处**：面板每行外链原文，不存储、不摘要、不改编、不编造。

固定查询（v1 冻结在 `DEFAULT_QUERY`）：

```
("stock market" OR "S&P 500" OR "Federal Reserve") sourcelang:eng
```

引号是 load-bearing：不加引号的 `federal reserve` 按两词全文散匹配（2026-08-22 实测拉进尼日利亚招聘诈骗文）；加引号后每个备选是短语匹配，抽查全部为市场报道（Fortune/CNBC/等）。

---

## G1 — License allowlist（许可协议白名单）

### 结论：✓ **PASS（沿用 news_sentiment 先例）**

- **规则**：仅 MIT / Apache-2.0 / BSD-2/3-Clause / CC0 / CC-BY-4.0（数据）或等价的开放数据。
- **来源**：GDELT 以开放数据形式发布其索引与聚合；URL / 标题 / 时间戳 / 域名是**事实（facts，不受版权保护）**。
- **边界（诚实）**：**文章正文版权属于出版商**——本模块只携带元数据 + 外链，不复制正文内容（与 news_sentiment 只取聚合 tone 同一立场）。面板 methodology 明示归属。

---

## G2 — PIT / as-of 时点（point-in-time）

### 结论：✓ **PASS**

- **机制**：`seendate` = GDELT 首次爬到该文的 UTC 时间戳（15 分钟分辨率），是"该文对机器可见"的时点锚；快照另带 `snapshot_ts`。
- **实现**：`news_feed.py:normalize_seendate()` 原样转 ISO（YYYYMMDDTHHMMSSZ → YYYY-MM-DDTHH:MM:SSZ），坏时间戳诚实置空、绝不猜测。

---

## G3 — No-revision contract（无回改契约）

### 结论：✓ **PASS（带如实披露）**

- **机制**：新闻流是追加型——同一 URL 的 `seendate` 稳定；缓存合并去重键 = **精确 URL**（新见覆盖旧记录，不改历史语义）。
- **披露**：同一通稿在不同域名下的**联合发布副本不去重**（URL 不同即不同行），计数如实包含副本；面板 methodology 明示。

---

## G4 — Reproducibility / snapshot discipline（可复现）

### 结论：✓ **PASS**

- 幂等缓存 `data/cache/news_feed.parquet`（去重键=url，尾随 30 天窗口）；重跑 = 1 次 artlist 请求 + 合并，网络成本恒定。
- 解析（`parse_artlist` / `normalize_seendate` / `merge_feed` / `count_by_day`）全为纯函数，hermetic 测试锁定（`tests/test_news_feed.py`，fixture 手写且显式标注）。

---

## G5 — Exploratory-only 边界

### 结论：✓ **PASS**

- **display-only / mode=exploratory**：仅进终端 `/news` 面板与静态数据 API（`news_feed.json`）。
- **绝不进研究管线**（features/eval/ingest of research data/OOS）；无 frozen claim 依赖此数据。

---

## G6 — Selection honesty（选择诚实）

### 结论：✓ **PASS（范围限制如实声明）**

- 查询**固定**（无 cherry-pick）：短语市场查询 + `sourcelang:eng`，在 payload `query` 字段原样携带。
- 排序 = GDELT `sort=datedesc`（机器排序，非编辑挑选）；payload 截前 150 条，`by_day` / `total` 覆盖完整尾随窗口（计数诚实）。
- 覆盖偏差如实声明：GDELT 爬虫所见（英文偏向、地域偏向），缺口就是缺口；联合发布副本不去重（见 G3）。

---

## G7 — Politeness / rate limit（礼貌抓取）

### 结论：✓ **PASS**

- **≥15s host spacing**：复用 `news_sentiment_gdelt._policy`（`HostSpacingPolicy(min_interval=15.0)`）。GDELT 文档最低 ≥5s，但项目实测 5s 连续冷拉触发 429（2026-08-11 CI），15s 清除滥用阈值。
- **有界**：每 run 恰 1 次请求 × `maxrecords=200`（GDELT 上限 250 之内）；有界重试（`RetryPolicy(max_retries=2)`）；UA 带 contact。
- CI 步 `timeout-minutes: 10` + `continue-on-error: true`——失败保留旧缓存。

---

## 结论

**7/7 PASS（G1 事实性元数据 + 版权留在出版商；G6 带声明范围）** — 准入为 **display-only / exploratory**。违反任一门（如改查询后不更新本文档、或把该数据接入研究管线）即失效。
