"""EXTENDED line monetary totals (BT-X-327 … BT-X-330, BT-X-590).

Covers :func:`getafix.rules.trade.line_tax_total_currencies`, which
mirrors the EXTENDED schematron's constraints on the line-level
``TaxTotalAmount``: at most one in the invoice currency (BT-5), at most
one in the VAT accounting currency (BT-6), no other currency — and the
``GETAFIX-LINE-*`` plausibility warnings that recompute the line totals
from the line's allowances / charges, quantity, price and VAT rate.

The first line of the sample: 52.00 net at 19 %, VAT 9.88, gross 61.88.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from getafix.errors import ValidationErrors, ValidationWarning
from getafix.rules.trade import (
    getafix_line_allowances,
    getafix_line_charges,
    getafix_line_gross,
    getafix_line_net,
    getafix_line_vat,
    getafix_line_vat_accounting,
    line_tax_total_currencies,
)
from getafix.schema.accounting import LineTaxTotal, LineTradeAllowanceCharge, TaxTotal
from getafix.schema.document import Document
from getafix.schema.line import BasisQuantity
from getafix.schema.settlement import TaxCurrencyExchange
from getafix.schema.types import Currency, LineStatusReasonCode, Profile

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


# ---- GETAFIX-LINE-* plausibility warnings ----------------------------------


def _line_codes(doc: Document) -> list[str]:
    item = doc.trade.items[0]
    found = [
        *getafix_line_charges(item, Profile.EXTENDED),
        *getafix_line_allowances(item, Profile.EXTENDED),
        *getafix_line_net(item, Profile.EXTENDED),
        *getafix_line_vat(doc.trade, Profile.EXTENDED),
        *getafix_line_gross(doc.trade, Profile.EXTENDED),
        *getafix_line_vat_accounting(doc.trade, Profile.EXTENDED),
    ]
    assert all(isinstance(w, ValidationWarning) for w in found)
    return [w.code for w in found]


def _add_line_allowance_charge(doc: Document, allowance: str, charge: str) -> None:
    """Add one allowance and one charge and keep BT-131 consistent."""
    settlement = doc.trade.items[0].settlement
    settlement.allowance_charge = [
        LineTradeAllowanceCharge(indicator=False, actual_amount=Decimal(allowance)),
        LineTradeAllowanceCharge(indicator=True, actual_amount=Decimal(charge)),
    ]
    ms = settlement.monetary_summation
    assert ms.line_total is not None
    ms.line_total += Decimal(charge) - Decimal(allowance)


def test_sample_line_totals_plausible() -> None:
    assert _line_codes(_doc()) == []


def test_allowance_and_charge_totals_match() -> None:
    doc = _doc()
    _add_line_allowance_charge(doc, "2.00", "5.00")
    ms = doc.trade.items[0].settlement.monetary_summation
    ms.allowance_total, ms.charge_total = Decimal("2.00"), Decimal("5.00")
    ms.tax_total = ms.grand_total = None
    assert _line_codes(doc) == []


def test_charge_total_mismatch_warns() -> None:
    doc = _doc()
    _add_line_allowance_charge(doc, "2.00", "5.00")
    ms = doc.trade.items[0].settlement.monetary_summation
    ms.allowance_total, ms.charge_total = Decimal("2.00"), Decimal("4.00")
    ms.tax_total = ms.grand_total = None
    assert _line_codes(doc) == ["GETAFIX-LINE-CHARGES"]


def test_allowance_total_mismatch_warns() -> None:
    doc = _doc()
    ms = doc.trade.items[0].settlement.monetary_summation
    ms.allowance_total = Decimal("1.00")
    assert _line_codes(doc) == ["GETAFIX-LINE-ALLOWANCES"]


def test_group_line_totals_not_checked_against_own_allowances() -> None:
    doc = _doc()
    item = doc.trade.items[0]
    item.associated_document.status_reason_code = LineStatusReasonCode.GROUP
    item.settlement.monetary_summation.allowance_total = Decimal("1.00")
    item.settlement.monetary_summation.line_total = Decimal("1.00")
    codes = _line_codes(doc)
    assert "GETAFIX-LINE-ALLOWANCES" not in codes
    assert "GETAFIX-LINE-NET" not in codes


def test_net_amount_mismatch_warns() -> None:
    doc = _doc()
    ms = doc.trade.items[0].settlement.monetary_summation
    ms.line_total = Decimal("50.00")
    ms.tax_total = ms.grand_total = None
    (warning,) = getafix_line_net(doc.trade.items[0], Profile.BASIC)
    assert warning.code == "GETAFIX-LINE-NET"
    assert "50.00" in warning.message


def test_net_amount_includes_allowances_and_charges() -> None:
    doc = _doc()
    _add_line_allowance_charge(doc, "2.00", "5.00")
    assert getafix_line_net(doc.trade.items[0], Profile.BASIC) == []


def test_net_amount_honours_base_quantity() -> None:
    doc = _doc()
    price = doc.trade.items[0].agreement.net_price
    assert price is not None
    unit = doc.trade.items[0].delivery.billed_quantity
    assert unit is not None
    price.charge_amount *= 100
    price.basis_quantity = BasisQuantity(value=Decimal("100"), unit_code=unit.unit_code)
    assert getafix_line_net(doc.trade.items[0], Profile.BASIC) == []


def test_line_vat_mismatch_warns() -> None:
    doc = _doc()
    _set_line_tax(doc, ("9.00", Currency.EUR))
    doc.trade.items[0].settlement.monetary_summation.grand_total = Decimal("61.00")
    assert _line_codes(doc) == ["GETAFIX-LINE-VAT"]


def test_line_gross_mismatch_warns() -> None:
    doc = _doc()
    doc.trade.items[0].settlement.monetary_summation.grand_total = Decimal("62.00")
    assert _line_codes(doc) == ["GETAFIX-LINE-GROSS"]


def test_line_gross_derives_vat_from_rate() -> None:
    doc = _doc()
    ms = doc.trade.items[0].settlement.monetary_summation
    ms.tax_total = None
    assert _line_codes(doc) == []
    ms.grand_total = Decimal("52.00")
    assert _line_codes(doc) == ["GETAFIX-LINE-GROSS"]


def test_line_vat_accounting_currency_converted() -> None:
    doc = _doc()
    settlement = doc.trade.settlement
    settlement.tax_currency_code = Currency.CHF
    settlement.currency_exchange = TaxCurrencyExchange(
        source_currency_code=Currency.EUR,
        target_currency_code=Currency.CHF,
        conversion_rate=Decimal("0.95"),
    )
    _set_line_tax(doc, ("9.88", Currency.EUR), ("9.39", Currency.CHF))
    assert _line_codes(doc) == []
    _set_line_tax(doc, ("9.88", Currency.EUR), ("9.88", Currency.CHF))
    assert _line_codes(doc) == ["GETAFIX-LINE-VAT-ACCOUNTING"]


def test_line_warnings_silent_below_extended() -> None:
    doc = _doc()
    ms = doc.trade.items[0].settlement.monetary_summation
    ms.allowance_total = Decimal("1.00")
    ms.grand_total = Decimal("1.00")
    item = doc.trade.items[0]
    assert getafix_line_allowances(item, Profile.COMFORT) == []
    assert getafix_line_gross(doc.trade, Profile.COMFORT) == []


def test_validate_returns_line_warnings() -> None:
    doc = _doc()
    doc.trade.items[0].settlement.monetary_summation.grand_total = Decimal("62.00")
    warnings = doc.validate()
    assert [w.code for w in warnings] == ["GETAFIX-LINE-GROSS"]
