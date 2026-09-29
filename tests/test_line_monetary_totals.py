"""EXTENDED line monetary totals (BT-X-327 … BT-X-330, BT-X-590).

Covers :func:`getafix.rules.trade.line_tax_total_currencies`, which
mirrors the EXTENDED schematron's constraints on the line-level
``TaxTotalAmount``: at most one in the invoice currency (BT-5), at most
one in the VAT accounting currency (BT-6), no other currency.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from getafix.errors import ValidationErrors
from getafix.rules.trade import line_tax_total_currencies
from getafix.schema.accounting import LineTaxTotal, TaxTotal
from getafix.schema.document import Document
from getafix.schema.types import Currency, Profile

_SAMPLE = Path(__file__).parent / "samples" / "EXTENDED_synth_product_line.xml"


def _doc() -> Document:
    return Document.from_xml(etree.fromstring(_SAMPLE.read_bytes()))


def _set_line_tax(doc: Document, *totals: tuple[str, Currency]) -> None:
    doc.trade.items[0].settlement.monetary_summation.tax_total = [
        LineTaxTotal(amount=Decimal(amount), currency_id=cur) for amount, cur in totals
    ]


def _messages(doc: Document) -> list[str]:
    return [e.message for e in line_tax_total_currencies(doc.trade, Profile.EXTENDED)]


def test_sample_is_clean() -> None:
    _doc().validate()


def test_invoice_currency_accepted() -> None:
    doc = _doc()
    _set_line_tax(doc, ("9.88", Currency.EUR))
    assert _messages(doc) == []


def test_accounting_currency_accepted_when_bt6_set() -> None:
    doc = _doc()
    settlement = doc.trade.settlement
    settlement.tax_currency_code = Currency.CHF
    _set_line_tax(doc, ("9.88", Currency.EUR), ("9.30", Currency.CHF))
    assert _messages(doc) == []


def test_foreign_currency_rejected() -> None:
    doc = _doc()
    _set_line_tax(doc, ("9.88", Currency.USD))
    (msg,) = _messages(doc)
    assert "USD" in msg
    assert "BT-5" in msg


def test_accounting_currency_rejected_without_bt6() -> None:
    doc = _doc()
    assert doc.trade.settlement.tax_currency_code is None
    _set_line_tax(doc, ("9.88", Currency.EUR), ("9.30", Currency.CHF))
    (msg,) = _messages(doc)
    assert "CHF" in msg


def test_duplicate_currency_rejected() -> None:
    doc = _doc()
    _set_line_tax(doc, ("9.88", Currency.EUR), ("9.88", Currency.EUR))
    (msg,) = _messages(doc)
    assert "more than one" in msg
    assert "EUR" in msg


def test_rule_silent_below_extended() -> None:
    doc = _doc()
    _set_line_tax(doc, ("9.88", Currency.USD))
    assert line_tax_total_currencies(doc.trade, Profile.COMFORT) == []


def test_document_validate_reports_code() -> None:
    doc = _doc()
    _set_line_tax(doc, ("9.88", Currency.USD))
    with pytest.raises(ValidationErrors) as exc:
        doc.validate()
    assert {e.code for e in exc.value.errors} == {"BT-X-329"}


def test_line_tax_total_has_no_header_decimal_cap() -> None:
    """``BR-DEC-13`` caps the header BT-110 only, not the line total."""
    assert (
        LineTaxTotal(
            amount=Decimal("1.234"), currency_id=Currency.EUR
        ).validate_internal(Profile.EXTENDED)
        == []
    )
    assert [
        e.code
        for e in TaxTotal(
            amount=Decimal("1.234"), currency_id=Currency.EUR
        ).validate_internal(Profile.EXTENDED)
    ] == ["BR-DEC-13"]
