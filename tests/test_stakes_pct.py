"""Hermetic tests for the bounded SC 13D/13G percent-of-class parser (no network).

Pins :mod:`aionis.ingest.stakes_pct` — the pure extraction/selection pieces
the /stakes-style holding-percentage feature rides on:

* primary-document selection from an index.json listing (modern
  ``primary_doc.xml`` first, traditional ``sc13g.htm`` next, never the
  EDGAR-generated ``-index.htm`` pages or exhibits);
* ``pct_now`` extraction — structured XML tag (13D ``percentOfClass`` +
  13G ``classPercent`` live shapes), the HTML cover label ("Percent of
  class", "PERCENT OF CLASS REPRESENTED BY AMOUNT IN ROW (11)"), and the
  narrative "X.X% of the ... class / outstanding shares" sentence;
* ``pct_prev`` — "previous 5.2%"-style amendment narrative, and the absolute
  rule that original (non-/A) filings NEVER carry a prev;
* out-of-range values rejected; misses are honest nulls.

The network path (``parse_filing_pct``: index.json + one document, ≤2 polite
requests, idempotent cache) is exercised by the manual run + cron, per the
house pattern of the 13G/13D daily-index modules.
"""
from __future__ import annotations

from aionis.ingest.stakes_pct import (
    extract_pct_now,
    extract_pct_prev,
    pick_primary_doc,
    strip_markup,
)

# Live-shaped 13G structured submission (AEON Biopharma 0000935836-26-000442,
# primary_doc.xml, schema http://www.sec.gov/edgar/schedule13g).
_13G_XML = """<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/schedule13g">
  <formData>
    <coverPageHeader>
      <securitiesClassTitle>Class A Common Stock</securitiesClassTitle>
    </coverPageHeader>
    <coverPage>
      <classPercent>13.0%</classPercent>
    </coverPage>
  </formData>
</edgarSubmission>"""

# Live-shaped 13D/A structured submission (5AM Partners / SKYE
# 0001873545-26-000007, primary_doc.xml): group filing — one cover page per
# reporting person; the FIRST cover page is the lead reporter's.
_13DA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/schedule13d">
  <formData>
    <coverPage>
      <reportingPersonId>1</reportingPersonId>
      <percentOfClass>25.9</percentOfClass>
    </coverPage>
    <coverPage>
      <reportingPersonId>2</reportingPersonId>
      <percentOfClass>4.1</percentOfClass>
    </coverPage>
  </formData>
</edgarSubmission>"""

# Traditional HTML cover page: the two label phrasings EDGAR cover pages use.
_HTML_LABEL_US = (
    "<table><tr><td>6. PERCENT OF CLASS REPRESENTED BY AMOUNT IN ROW (11)</td>"
    "<td>5.5%</td></tr></table>"
)
_HTML_LABEL_PLAIN = "Percent of class: 4.99%"

# Narrative sentences (cover pages + Item 5 + explanatory notes).
_NARRATIVES = [
    "The Reporting Person beneficially owns 4.99% of the outstanding shares of"
    " Class A Common Stock.",
    "This represents approximately 6.1% of the outstanding common stock of the"
    " Issuer.",
    "constitutes 8.3% of the class of securities check the following",
]

# Previous-value sentences seen in /A amendments.
_PREV_SENTENCES = [
    ("The Reporting Person previously reported beneficial ownership of 5.2%.",
     5.2),
    ("The Reporting Person decreased its ownership from 6.4% to 5.1%.", 6.4),
    ("previous 12.2%", 12.2),
    ("The percentage was reduced from 9.9% down to 4.0% of the class.", 9.9),
]


# --- primary-document selection ------------------------------------------------

def test_pick_prefers_modern_primary_doc_xml() -> None:
    names = [
        "0000935836-26-000442-index-headers.html",
        "0000935836-26-000442-index.html",
        "0000935836-26-000442.txt",
        "primary_doc.xml",
    ]
    assert pick_primary_doc(names) == "primary_doc.xml"


def test_pick_traditional_sc13_doc_when_no_xml() -> None:
    names = [
        "0000903420-26-000123-index.htm",
        "sc13d.htm",
        "exhibit99.htm",
        "graphic.gif",
    ]
    assert pick_primary_doc(names) == "sc13d.htm"


def test_pick_falls_back_to_first_plain_htm() -> None:
    # An oddly named primary doc (no sc13 pattern) still beats nothing.
    names = ["0000903420-26-000123-index.htm", "form.htm", "ex1.htm"]
    assert pick_primary_doc(names) == "form.htm"


def test_pick_never_returns_index_or_exhibit_pages() -> None:
    names = [
        "0000903420-26-000123-index.htm",
        "0000903420-26-000123-index-headers.html",
        "ex99.htm",
        "exhibit1.htm",
    ]
    assert pick_primary_doc(names) is None


# --- pct_now extraction --------------------------------------------------------

def test_pct_now_from_13g_class_percent_tag() -> None:
    assert extract_pct_now(_13G_XML) == 13.0


def test_pct_now_from_13d_percent_of_class_tag_takes_first_cover() -> None:
    # Group filing: the LEAD reporter's cover page (25.9), not a later member.
    assert extract_pct_now(_13DA_XML) == 25.9


def test_pct_now_from_html_cover_labels() -> None:
    assert extract_pct_now(_HTML_LABEL_US) == 5.5
    assert extract_pct_now(_HTML_LABEL_PLAIN) == 4.99


def test_pct_now_from_narrative_sentences() -> None:
    for sent, want in zip(
        _NARRATIVES, [4.99, 6.1, 8.3], strict=True
    ):
        assert extract_pct_now(sent) == want, sent


def test_pct_now_xml_tag_beats_narrative() -> None:
    doc = _13G_XML.replace(
        "</formData>",
        "<explanation>The Reporting Person owns 4.99% of the outstanding"
        " shares of Class A Common Stock.</explanation></formData>",
    )
    assert extract_pct_now(doc) == 13.0


def test_pct_now_honest_null_when_nothing_matches() -> None:
    assert extract_pct_now("10-Q quarterly report, no stake language") is None


def test_pct_now_rejects_out_of_range() -> None:
    assert extract_pct_now("Percent of class: 250%") is None
    assert extract_pct_now("<percentOfClass>1,000</percentOfClass>") is None


def test_pct_now_rejects_irrelevant_percent_sentence() -> None:
    # A percentage NOT tied to the class/outstanding-share context must not match.
    assert extract_pct_now("The fee is 100% of proceeds.") is None


# --- pct_prev extraction -------------------------------------------------------

def test_pct_prev_extracts_amendment_narratives() -> None:
    for sent, want in _PREV_SENTENCES:
        assert extract_pct_prev(sent, is_amendment=True) == want, sent


def test_pct_prev_never_set_on_original_filings() -> None:
    # The absolute contract: prev only in /A amendments — the parser refuses
    # even when the text contains a previous-value sentence.
    for sent, _ in _PREV_SENTENCES:
        assert extract_pct_prev(sent, is_amendment=False) is None


def test_pct_prev_honest_null_when_silent() -> None:
    assert extract_pct_prev(
        "The Reporting Person owns 25.9% of the class.", is_amendment=True
    ) is None


def test_pct_prev_rejects_out_of_range() -> None:
    assert extract_pct_prev(
        "previously reported 300%", is_amendment=True
    ) is None


# --- strip_markup ----------------------------------------------------------------

def test_strip_markup_unescapes_and_flattens() -> None:
    assert "5.5" in strip_markup(
        "<td>Percent of class:</td><td>5.5&#37;</td>"
    )
    assert strip_markup("<script>x=1%</script><b>ok</b>") == " ok "
