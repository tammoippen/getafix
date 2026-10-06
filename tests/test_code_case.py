"""GETAFIX-CODE-CASE — codes parsed case-insensitively, with a warning.

The Factur-X schematron compares code values exactly
(``enumeration[@value=$codeValue]``), so ``vatex-eu-132`` or ``eur``
is invalid there. getafix still parses such a code — mapping it to the
code-list entry it matches ignoring case — and reports a
``GETAFIX-CODE-CASE`` warning. Re-rendering writes the canonical code.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from getafix.errors import ValidationWarning
from getafix.schema.document import Document
from getafix.schema.element import parse_code
from getafix.schema.types import MIME, CategoryCode, Currency, VATEXCode

_SAMPLE = Path(__file__).parent / "samples" / "EN16931_Einfach.cii.xml"


def _parse(*replacements: tuple[str, str]) -> Document:
    text = _SAMPLE.read_text(encoding="utf-8")
    for old, new in replacements:
        assert old in text, old
        text = text.replace(old, new)
    return Document.from_xml(etree.fromstring(text.encode()))


def _case_warnings(doc: Document) -> list[str]:
    return [w.message for w in doc.validate() if w.code == "GETAFIX-CODE-CASE"]


def test_parse_code() -> None:
    assert parse_code(VATEXCode, "VATEX-EU-132") == (VATEXCode.VATEX_EU_132, False)
    assert parse_code(VATEXCode, "vatex-eu-132") == (VATEXCode.VATEX_EU_132, True)
    assert parse_code(MIME, "Application/PDF") == (MIME("application/pdf"), True)
    with pytest.raises(ValueError):
        _ = parse_code(VATEXCode, "vatex-eu-999")


def test_canonical_sample_has_no_warning() -> None:
    assert _case_warnings(_parse()) == []


def test_element_text_code() -> None:
    doc = _parse(
        (
            "<ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>",
            "<ram:InvoiceCurrencyCode>eur</ram:InvoiceCurrencyCode>",
        )
    )
    assert doc.trade.settlement.currency_code is Currency.EUR
    (message,) = _case_warnings(doc)
    assert "'eur' read as 'EUR'" in message


def test_one_warning_per_occurrence() -> None:
    doc = _parse(
        (
            "<ram:CategoryCode>S</ram:CategoryCode>",
            "<ram:CategoryCode>s</ram:CategoryCode>",
        )
    )
    assert doc.trade.settlement.trade_taxes
    assert doc.trade.settlement.trade_taxes[0].category_code is CategoryCode.T_S
    assert len(_case_warnings(doc)) == 4


def test_attribute_code() -> None:
    doc = _parse(
        (
            '<ram:TaxTotalAmount currencyID="EUR">',
            '<ram:TaxTotalAmount currencyID="Eur">',
        )
    )
    (message,) = _case_warnings(doc)
    assert "TaxTotal.currency_id: 'Eur' read as 'EUR'" in message


def test_rerender_writes_canonical_code() -> None:
    doc = _parse(
        (
            "<ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>",
            "<ram:InvoiceCurrencyCode>eur</ram:InvoiceCurrencyCode>",
        )
    )
    rendered = Document.from_xml(etree.fromstring(doc.to_xml().render().encode()))
    assert _case_warnings(rendered) == []


def test_warning_is_not_an_error() -> None:
    doc = _parse(
        (
            "<ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>",
            "<ram:InvoiceCurrencyCode>eur</ram:InvoiceCurrencyCode>",
        )
    )
    assert all(isinstance(w, ValidationWarning) for w in doc.validate())


def test_unknown_code_still_rejected() -> None:
    with pytest.raises(ValueError):
        _ = _parse(
            (
                "<ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>",
                "<ram:InvoiceCurrencyCode>eurx</ram:InvoiceCurrencyCode>",
            )
        )
