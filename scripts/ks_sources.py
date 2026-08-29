"""Single source of truth for the knowledge-shelf curated research bookmarks.

Imported by BOTH export_terminal_data (knowledge_shelf.json panel, Layer 2)
and export_research_dossier (dossier external-source registry) so the two
downstream artifacts never hash each other into a circular dependency
(round-34 integration: the dossier previously embedded the shelf file's
content sha while the shelf embedded the dossier's — no fixpoint).

stdlib-only by design; frozen editorial literals, never fetched or scraped.
"""

RESEARCH_SOURCES: list[dict[str, str]] = [
    {
        "name": "BIS Working Papers",
        "org": "Bank for International Settlements",
        "url": "https://www.bis.org/list/wppubls/index.htm",
        "desc_en": (
            "Monetary and financial-stability research; the series page "
            "(RSS available) is the first-hand release point."
        ),
        "desc_zh": "货币与金融稳定方向的工作论文系列页（提供 RSS）——一手发布处。",
    },
    {
        "name": "FEDS Papers",
        "org": "Federal Reserve Board",
        "url": "https://www.federalreserve.gov/econres/feds/index.htm",
        "desc_en": (
            "Finance and Economics Discussion Papers — the Board's own "
            "in-house research series."
        ),
        "desc_zh": "美联储理事会的金融与经济学讨论论文（FEDS）——机构自有研究系列。",
    },
    {
        "name": "IMF Working Papers",
        "org": "International Monetary Fund",
        "url": "https://www.imf.org/en/Publications/WP",
        "desc_en": (
            "IMF staff research on macro-finance topics, published as the "
            "official WP series."
        ),
        "desc_zh": "国际货币基金组织（IMF）工作人员的宏观金融研究——官方工作论文系列。",
    },
    {
        "name": "NBER Working Papers",
        "org": "National Bureau of Economic Research",
        "url": "https://www.nber.org/papers",
        "desc_en": (
            "The classic economics working-paper series; abstract pages are "
            "first-hand author submissions."
        ),
        "desc_zh": "经典的经济学工作论文系列；摘要页为作者一手提交。",
    },
    {
        "name": "arXiv q-fin",
        "org": "arXiv (Cornell University)",
        "url": "https://arxiv.org/archive/q-fin",
        "desc_en": (
            "Quantitative finance preprints — open author manuscripts "
            "before journal versions."
        ),
        "desc_zh": "数量金融预印本专区——期刊版本之前的开放作者手稿。",
    },
    {
        "name": "FRASER",
        "org": "Federal Reserve Bank of St. Louis",
        "url": "https://fraser.stlouisfed.org",
        "desc_en": (
            "Public-domain digital archive of U.S. economic history: Fed "
            "publications, banking documents, statistical releases."
        ),
        "desc_zh": "美国经济史公共领域数字档案：联储出版物、银行文献与统计发布。",
    },
    {
        "name": "FRED / ALFRED",
        "org": "Federal Reserve Bank of St. Louis",
        "url": "https://fred.stlouisfed.org",
        "desc_en": (
            "U.S. government public-domain macro data + as-of vintages "
            "(ALFRED) — Aionis's own macro backbone."
        ),
        "desc_zh": "美国政府公共领域宏观数据库与 ALFRED 时点版本库——Aionis 宏观数据的主源。",
    },
    {
        "name": "RePEc / IDEAS",
        "org": "RePEc (Research Papers in Economics)",
        "url": "https://ideas.repec.org",
        "desc_en": (
            "Community-run economics research index — bibliographic catalog "
            "that links out to primary sources."
        ),
        "desc_zh": "社区运维的经济学研究索引——书目目录，链出到各一手来源。",
    },
]
