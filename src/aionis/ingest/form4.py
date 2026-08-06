"""Point-in-time Form 4 insider-trading filings (SEC EDGAR).

Form 4 filings capture insider trading transactions: officers, directors, and 10%
owners MUST report buys/sells within 2 business days. This module parses Form 4
XML to extract filer identity, ticker, transaction date, acquisition/disposition
code (A=acquire/buy, D=dispose/sell), shares, and price per share.

SEC EDGAR public domain (17 U.S.C. §105); filed-date PIT; immutable (Form 4/A
amendments are NEW filings with new accession numbers, never silent overwrites)
— G3✓ (cleanest possible surface, strictly better than ALFRED/EPU).

PARSING DISCIPLINE: Form 4 filings are XML with a stable schema
(https://www.sec.gov/info/edgar/edgarfm.htm). We extract:
  * ``filer_cik`` — the reporting person's CIK
  * ``filer_name`` — the reporting person's name
  * ``ticker`` — issuer ticker symbol
  * ``transaction_date`` — when the trade occurred
  * ``acquired_or_disposed`` — ``A`` (buy) or ``D`` (sell) per SEC coding
  * ``shares`` — number of shares traded
  * ``price_per_share`` — price in USD

Only non-derivative, non-ownership-change transactions are extracted (pure
buy/sell events). Derivative securities, exercises, and ownership changes are
excluded to avoid double-counting and noise.

NOTE: This module parses Form 4 XML content. The EFTS search layer lives in
:mod:`aionis.ingest.form4_efts` (mirrors :mod:`aionis.ingest.stakes_13d_efts`).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

import pandas as pd
import structlog

log = structlog.get_logger()


@dataclass(frozen=True)
class Form4Transaction:
    """One non-derivative insider trading transaction from a Form 4 filing."""

    filer_cik: int
    filer_name: str
    ticker: str
    transaction_date: str  # YYYY-MM-DD
    acquired_or_disposed: str  # "A" (buy) or "D" (sell)
    shares: float
    price_per_share: float


def _parse_cik(cik_str: str | None) -> int | None:
    """Extract CIK from SEC format (may have leading zeros or be empty)."""
    if not cik_str:
        return None
    try:
        return int(str(cik_str).strip())
    except (ValueError, TypeError):
        return None


def _clean_number(num_str: str | None) -> float | None:
    """Parse numeric fields (shares, price) which may be empty or malformed."""
    if not num_str:
        return None
    try:
        return float(str(num_str).strip().replace(",", ""))
    except (ValueError, TypeError, AttributeError):
        return None


def _find_text(parent: ET.Element, tag: str, namespace: dict[str, str] | None = None) -> str | None:
    """Find direct child element and return its text, or None."""
    elem = parent.find(tag, namespace)
    return elem.text if elem is not None and elem.text else None


def parse_form4_xml(xml_text: str) -> list[Form4Transaction]:
    """Parse Form 4 XML content and extract non-derivative transactions.

    Returns a list of :class:`Form4Transaction` objects. Only extracts:
      * Non-derivative transactions (``nonDerivativeTransaction``)
      * Pure buy/sell (``acquiredOrDisposed`` = "A" or "D")
      * With valid shares and price

    Derivative transactions, ownership changes, and missing critical fields are
    skipped with a warning.

    Args:
        xml_text: Raw XML content from a Form 4 filing.

    Returns:
        List of parsed transactions (may be empty).
    """
    if not xml_text or not xml_text.strip():
        log.warning("form4_empty_xml")
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        log.warning("form4_xml_parse_error", error=str(exc))
        return []

    # Form 4 has no namespace by default (elements are unqualified)
    transactions: list[Form4Transaction] = []

    # Extract filer info from reportingOwner section
    filer_cik = None
    filer_name = ""
    reporting_owner = root.find(".//reportingOwner")
    if reporting_owner is not None:
        owner_id = reporting_owner.find(".//reportingOwnerId")
        if owner_id is not None:
            cik_elem = owner_id.find("rptOwnerCik")
            if cik_elem is not None and cik_elem.text:
                filer_cik = _parse_cik(cik_elem.text)
            name_elem = owner_id.find("rptOwnerName")
            if name_elem is not None and name_elem.text:
                filer_name = name_elem.text.strip()

    # Extract ticker (issuer)
    ticker = ""
    issuer = root.find(".//issuer")
    if issuer is not None:
        ticker_elem = issuer.find("issuerTradingSymbol")
        if ticker_elem is not None and ticker_elem.text:
            ticker = ticker_elem.text.strip()

    # Extract non-derivative transactions
    for tx_node in root.findall(".//nonDerivativeTransaction"):
        # Transaction date
        date_node = tx_node.find("transactionDate")
        if date_node is None:
            continue

        year_elem = date_node.find("year")
        month_elem = date_node.find("month")
        day_elem = date_node.find("day")

        if not all([year_elem is not None, month_elem is not None, day_elem is not None]):
            continue
        if not all([year_elem.text, month_elem.text, day_elem.text]):
            continue

        try:
            tx_date = (
                f"{int(year_elem.text):04d}-"
                f"{int(month_elem.text):02d}-"
                f"{int(day_elem.text):02d}"
            )
        except (ValueError, TypeError):
            continue

        # Transaction coding (A=acquire, D=dispose)
        coding_node = tx_node.find("transactionCoding")
        if coding_node is None:
            continue
        code_elem = coding_node.find("transactionCode")
        if code_elem is None or not code_elem.text:
            continue

        code = code_elem.text.strip().upper()
        if code not in ("A", "D"):
            continue  # Only pure buy (A) or sell (D)

        # Amounts (SEC wraps values in <value> tags)
        amount_node = tx_node.find("transactionAmounts")
        if amount_node is None:
            continue

        shares_elem = amount_node.find("transactionShares")
        price_elem = amount_node.find("transactionPricePerShare")

        # Handle SEC <value> wrapper for numeric fields
        shares_text = None
        if shares_elem is not None:
            if shares_elem.text and shares_elem.text.strip():
                shares_text = shares_elem.text
            else:
                # SEC wraps values in <value> child
                value_elem = shares_elem.find("value")
                if value_elem is not None and value_elem.text:
                    shares_text = value_elem.text

        price_text = None
        if price_elem is not None:
            if price_elem.text and price_elem.text.strip():
                price_text = price_elem.text
            else:
                # SEC wraps values in <value> child
                value_elem = price_elem.find("value")
                if value_elem is not None and value_elem.text:
                    price_text = value_elem.text

        shares = _clean_number(shares_text)
        price = _clean_number(price_text)

        if shares is None or price is None or shares <= 0 or price < 0:
            continue  # Invalid or suspicious amounts

        if filer_cik is None:
            log.warning("form4_no_filer_cik", ticker=ticker, date=tx_date)
            continue

        transactions.append(
            Form4Transaction(
                filer_cik=int(filer_cik),
                filer_name=filer_name,
                ticker=ticker,
                transaction_date=tx_date,
                acquired_or_disposed=code,
                shares=float(shares),
                price_per_share=float(price),
            )
        )

    log.info("form4_parsed", count=len(transactions), ticker=ticker)
    return transactions


def form4_filings_to_dataframe(transactions: list[Form4Transaction]) -> pd.DataFrame:
    """Convert a list of Form 4 transactions to a tidy pandas DataFrame.

    Returns columns: ``[filer_cik, filer_name, ticker, transaction_date,
    acquired_or_disposed, shares, price_per_share]`` sorted by transaction_date.
    """
    if not transactions:
        return pd.DataFrame(
            columns=[
                "filer_cik",
                "filer_name",
                "ticker",
                "transaction_date",
                "acquired_or_disposed",
                "shares",
                "price_per_share",
            ]
        )

    rows = [
        {
            "filer_cik": tx.filer_cik,
            "filer_name": tx.filer_name,
            "ticker": tx.ticker,
            "transaction_date": tx.transaction_date,
            "acquired_or_disposed": tx.acquired_or_disposed,
            "shares": tx.shares,
            "price_per_share": tx.price_per_share,
        }
        for tx in transactions
    ]

    df = pd.DataFrame(rows)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    return df.sort_values("transaction_date").reset_index(drop=True)


def parse_form4_filing_from_text(xml_text: str) -> pd.DataFrame:
    """Convenience function: parse Form 4 XML and return DataFrame directly.

    This is a one-shot wrapper around :func:`parse_form4_xml` +
    :func:`form4_filings_to_dataframe` for external callers.
    """
    transactions = parse_form4_xml(xml_text)
    return form4_filings_to_dataframe(transactions)
