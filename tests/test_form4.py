"""Hermetic tests for Form 4 ingest (fixture-based, no network).

Tests use hand-written fixtures mimicking EDGAR EFTS Form 4 response structure
and Form 4 XML content. No real SEC/EDGAR network calls — fully hermetic.

Mirrors the testing pattern from `tests/test_stakes_13d.py` but for Form 4.
"""
from __future__ import annotations

import pandas as pd

from aionis.ingest.form4 import (
    Form4Transaction,
    form4_filings_to_dataframe,
    parse_form4_filing_from_text,
    parse_form4_xml,
)

# --- Fixtures (hand-written, mimicking real EDGAR structure) ---

_FORM4_XML_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <schemaVersion>X0203</schemaVersion>
    <documentType>4</documentType>
    <periodOfReport>2024-01-15</periodOfReport>
    <notSubjectToSection16>0</notSubjectToSection16>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerName>APPLE INC</issuerName>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001234567</rptOwnerCik>
            <rptOwnerName>JOHN DOE</rptOwnerName>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isDirector>1</isDirector>
            <isOfficer>1</isOfficer>
            <isTenPercentOwner>0</isTenPercentOwner>
        </reportingOwnerRelationship>
    </reportingOwner>
    <derivativeTable>
        <derivativeTransaction></derivativeTransaction>
    </derivativeTable>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <securityTitle>
                <value>Common Stock</value>
            </securityTitle>
            <transactionDate>
                <year>2024</year>
                <month>01</month>
                <day>15</day>
            </transactionDate>
            <transactionCoding>
                <transactionCode>A</transactionCode>
                <equitySwapInvolved>0</equitySwapInvolved>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares>
                    <value>1000</value>
                    <footnoteId>F1</footnoteId>
                </transactionShares>
                <transactionPricePerShare>
                    <value>185.50</value>
                </transactionPricePerShare>
            </transactionAmounts>
        </nonDerivativeTransaction>
        <nonDerivativeTransaction>
            <securityTitle>
                <value>Common Stock</value>
            </securityTitle>
            <transactionDate>
                <year>2024</year>
                <month>01</month>
                <day>18</day>
            </transactionDate>
            <transactionCoding>
                <transactionCode>D</transactionCode>
                <equitySwapInvolved>0</equitySwapInvolved>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares>
                    <value>500</value>
                </transactionShares>
                <transactionPricePerShare>
                    <value>190.00</value>
                </transactionPricePerShare>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
    <remarks>Officer exercises options and sells shares.</remarks>
    <ownerSignature>
        <signatureName>JOHN DOE</signatureName>
        <signatureDate>2024-01-20</signatureDate>
    </ownerSignature>
</ownershipDocument>
"""

_FORM4_XML_EMPTY = """<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <schemaVersion>X0203</schemaVersion>
    <documentType>4</documentType>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerName>APPLE INC</issuerName>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <nonDerivativeTable>
    </nonDerivativeTable>
</ownershipDocument>
"""

_FORM4_XML_MALFORMED = """not even valid xml"""


_FORM4_XML_MISSING_FILER = """<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <documentType>4</documentType>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <transactionDate>
                <year>2024</year>
                <month>01</month>
                <day>15</day>
            </transactionDate>
            <transactionCoding>
                <transactionCode>A</transactionCode>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares>
                    <value>1000</value>
                </transactionShares>
                <transactionPricePerShare>
                    <value>185.50</value>
                </transactionPricePerShare>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""

_FORM4_XML_DERIVATIVE_ONLY = """<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <documentType>4</documentType>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001234567</rptOwnerCik>
            <rptOwnerName>JANE SMITH</rptOwnerName>
        </reportingOwnerId>
    </reportingOwner>
    <nonDerivativeTable>
    </nonDerivativeTable>
    <derivativeTable>
        <derivativeTransaction>
            <transactionDate>
                <year>2024</year>
                <month>01</month>
                <day>15</day>
            </transactionDate>
            <transactionCoding>
                <transactionCode>A</transactionCode>
            </transactionCoding>
        </derivativeTransaction>
    </derivativeTable>
</ownershipDocument>
"""


# --- Tests ---

def test_parse_form4_xml_basic() -> None:
    """Parse Form 4 XML and extract 2 transactions (1 buy, 1 sell)."""
    transactions = parse_form4_xml(_FORM4_XML_FIXTURE)
    assert len(transactions) == 2

    # First transaction: buy (A)
    tx1 = transactions[0]
    assert isinstance(tx1, Form4Transaction)
    assert tx1.filer_cik == 1234567
    assert tx1.filer_name == "JOHN DOE"
    assert tx1.ticker == "AAPL"
    assert tx1.transaction_date == "2024-01-15"
    assert tx1.acquired_or_disposed == "A"
    assert tx1.shares == 1000.0
    assert tx1.price_per_share == 185.50

    # Second transaction: sell (D)
    tx2 = transactions[1]
    assert tx2.filer_cik == 1234567
    assert tx2.filer_name == "JOHN DOE"
    assert tx2.ticker == "AAPL"
    assert tx2.transaction_date == "2024-01-18"
    assert tx2.acquired_or_disposed == "D"
    assert tx2.shares == 500.0
    assert tx2.price_per_share == 190.00


def test_parse_form4_xml_empty() -> None:
    """Empty Form 4 (no transactions) returns empty list, no crash."""
    transactions = parse_form4_xml(_FORM4_XML_EMPTY)
    assert transactions == []


def test_parse_form4_xml_malformed() -> None:
    """Malformed XML returns empty list, no crash."""
    transactions = parse_form4_xml(_FORM4_XML_MALFORMED)
    assert transactions == []


def test_parse_form4_xml_missing_filer() -> None:
    """Missing filer CIK skips the transaction with warning, returns empty."""
    transactions = parse_form4_xml(_FORM4_XML_MISSING_FILER)
    # Should skip transaction due to missing filer CIK
    assert transactions == []


def test_parse_form4_xml_derivative_only() -> None:
    """Derivative-only Form 4 returns empty (only non-derivative extracted)."""
    transactions = parse_form4_xml(_FORM4_XML_DERIVATIVE_ONLY)
    assert transactions == []


def test_form4_filings_to_dataframe_basic() -> None:
    """Convert transactions to DataFrame with correct schema and sorting."""
    transactions = parse_form4_xml(_FORM4_XML_FIXTURE)
    df = form4_filings_to_dataframe(transactions)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == [
        "filer_cik",
        "filer_name",
        "ticker",
        "transaction_date",
        "acquired_or_disposed",
        "shares",
        "price_per_share",
    ]

    # Check sorting by transaction_date
    assert df.iloc[0]["transaction_date"] == pd.Timestamp("2024-01-15")
    assert df.iloc[1]["transaction_date"] == pd.Timestamp("2024-01-18")

    # Check data types
    assert df["filer_cik"].dtype == pd.Int64Dtype() or df["filer_cik"].dtype == int
    assert pd.api.types.is_datetime64_any_dtype(df["transaction_date"])
    assert df["shares"].dtype == float
    assert df["price_per_share"].dtype == float


def test_form4_filings_to_dataframe_empty() -> None:
    """Empty transaction list returns empty DataFrame with correct schema."""
    df = form4_filings_to_dataframe([])

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    assert list(df.columns) == [
        "filer_cik",
        "filer_name",
        "ticker",
        "transaction_date",
        "acquired_or_disposed",
        "shares",
        "price_per_share",
    ]


def test_parse_form4_filing_from_text_convenience() -> None:
    """Convenience function parses XML and returns DataFrame directly."""
    df = parse_form4_filing_from_text(_FORM4_XML_FIXTURE)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert df.iloc[0]["ticker"] == "AAPL"
    assert df.iloc[0]["acquired_or_disposed"] == "A"
    assert df.iloc[1]["acquired_or_disposed"] == "D"


def test_parse_form4_xml_invalid_transaction_code() -> None:
    """Transaction codes other than A or D are ignored."""
    xml_with_invalid_code = """<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <documentType>4</documentType>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001234567</rptOwnerCik>
            <rptOwnerName>TEST</rptOwnerName>
        </reportingOwnerId>
    </reportingOwner>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <transactionDate>
                <year>2024</year>
                <month>01</month>
                <day>15</day>
            </transactionDate>
            <transactionCoding>
                <transactionCode>M</transactionCode>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares>
                    <value>1000</value>
                </transactionShares>
                <transactionPricePerShare>
                    <value>185.50</value>
                </transactionPricePerShare>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""
    transactions = parse_form4_xml(xml_with_invalid_code)
    assert transactions == []  # Code "M" is not A or D, should be skipped


def test_parse_form4_xml_missing_price_or_shares() -> None:
    """Transactions with missing or invalid price/shares are skipped."""
    xml_missing_amounts = """<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <documentType>4</documentType>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001234567</rptOwnerCik>
            <rptOwnerName>TEST</rptOwnerName>
        </reportingOwnerId>
    </reportingOwner>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <transactionDate>
                <year>2024</year>
                <month>01</month>
                <day>15</day>
            </transactionDate>
            <transactionCoding>
                <transactionCode>A</transactionCode>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares>
                    <value></value>
                </transactionShares>
                <transactionPricePerShare>
                    <value>185.50</value>
                </transactionPricePerShare>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""
    transactions = parse_form4_xml(xml_missing_amounts)
    assert transactions == []  # Missing shares, should be skipped


def test_parse_form4_xml_negative_shares() -> None:
    """Negative shares are treated as invalid and skipped."""
    xml_negative_shares = """<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <documentType>4</documentType>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001234567</rptOwnerCik>
            <rptOwnerName>TEST</rptOwnerName>
        </reportingOwnerId>
    </reportingOwner>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <transactionDate>
                <year>2024</year>
                <month>01</month>
                <day>15</day>
            </transactionDate>
            <transactionCoding>
                <transactionCode>A</transactionCode>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares>
                    <value>-100</value>
                </transactionShares>
                <transactionPricePerShare>
                    <value>185.50</value>
                </transactionPricePerShare>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""
    transactions = parse_form4_xml(xml_negative_shares)
    assert transactions == []  # Negative shares, should be skipped
