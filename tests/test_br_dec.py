"""BR-DEC-* — decimal-precision rules across every monetary BT.

EN 16931 (and the Factur-X 1.08 ``Business Rules`` sheet) caps every
monetary BT at two decimal places. The plan in
``docs/PROFILES/COMFORT.md §4.5`` wires this as a single factory:
each affected Decimal field on the schema dataclasses gets a small
validator that reports a ``BR-DEC-NN`` ValidationError when the
provided value carries more than two fractional digits.

Coverage (21 rules at COMFORT):

* ``MonetarySummation`` — BR-DEC-09..18.
* ``ApplicableTradeTax`` — BR-DEC-19/20.
* ``TaxTotal`` — BR-DEC-13 (invoice currency) / BR-DEC-15 (accounting
  currency).
* ``LineMonetarySummation`` — BR-DEC-23.
* Header ``TradeAllowanceCharge`` — BR-DEC-01/02/05/06.
* Line ``TradeAllowanceCharge`` — BR-DEC-24/25/27/28.
"""

from __future__ import annotations

from decimal import Decimal

import pytest as pt

from carthorse.schema import Profile
from carthorse.schema.accounting import (
    ApplicableTradeTax,
    HeaderTradeAllowanceCharge,
    LineTradeAllowanceCharge,
    MonetarySummation,
    TaxTotal,
)
from carthorse.schema.line import LineMonetarySummation
from carthorse.schema.types import CategoryCode, Currency, UNTDID2475TaxPointDateCode


def _run(elem, profile=Profile.BASIC_WL):
    return [e for v in elem._validators for e in v(elem, profile)]


class TestMonetarySummation:
    @pt.mark.parametrize(
        ("field", "code"),
        [
            ("line_total", "BR-DEC-09"),
            ("allowance_total", "BR-DEC-10"),
            ("charge_total", "BR-DEC-11"),
            ("tax_basis_total", "BR-DEC-12"),
            ("grand_total", "BR-DEC-14"),
            ("prepaid_total", "BR-DEC-16"),
            ("rounding_amount", "BR-DEC-17"),
            ("due_amount", "BR-DEC-18"),
        ],
    )
    def test_three_decimals_fail(self, field: str, code: str) -> None:
        kwargs: dict[str, Decimal] = {
            "tax_basis_total": Decimal("0"),
            "grand_total": Decimal("0"),
            "due_amount": Decimal("0"),
            field: Decimal("1.234"),
        }
        sm = MonetarySummation(**kwargs)
        errors = _run(sm)
        assert any(e.code == code for e in errors), errors

    def test_two_decimals_pass(self) -> None:
        sm = MonetarySummation(
            tax_basis_total=Decimal("99.99"),
            grand_total=Decimal("99.99"),
            due_amount=Decimal("99.99"),
        )
        errors = _run(sm)
        assert not any(e.code.startswith("BR-DEC") for e in errors)


class TestApplicableTradeTax:
    def test_basis_amount_three_decimals_fails(self) -> None:
        tt = ApplicableTradeTax(
            calculated_amount=Decimal("0"),
            basis_amount=Decimal("1.234"),
            category_code=CategoryCode.T_S,
            due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
            rate_applicable_percent=Decimal("19"),
        )
        errors = _run(tt)
        assert any(e.code == "BR-DEC-19" for e in errors), errors

    def test_calculated_amount_three_decimals_fails(self) -> None:
        tt = ApplicableTradeTax(
            calculated_amount=Decimal("0.123"),
            basis_amount=Decimal("0"),
            category_code=CategoryCode.T_S,
            due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
            rate_applicable_percent=Decimal("19"),
        )
        errors = _run(tt)
        assert any(e.code == "BR-DEC-20" for e in errors), errors


class TestTaxTotal:
    def test_invoice_currency_three_decimals_fails(self) -> None:
        tt = TaxTotal(amount=Decimal("19.123"), currency_id=Currency.EUR)
        errors = _run(tt)
        assert any(e.code == "BR-DEC-13" for e in errors), errors


class TestLineMonetarySummation:
    def test_three_decimals_fails(self) -> None:
        lms = LineMonetarySummation(line_total=Decimal("1.234"))
        errors = _run(lms)
        assert any(e.code == "BR-DEC-23" for e in errors), errors


class TestHeaderAllowanceCharge:
    def test_header_allowance_amount(self) -> None:
        ac = HeaderTradeAllowanceCharge(
            indicator=False, actual_amount=Decimal("1.234"), reason="x"
        )
        errors = _run(ac)
        assert any(e.code == "BR-DEC-01" for e in errors), errors

    def test_header_allowance_basis(self) -> None:
        ac = HeaderTradeAllowanceCharge(
            indicator=False,
            actual_amount=Decimal("1"),
            basis_amount=Decimal("100.123"),
            reason="x",
        )
        errors = _run(ac)
        assert any(e.code == "BR-DEC-02" for e in errors), errors

    def test_header_charge_amount(self) -> None:
        ac = HeaderTradeAllowanceCharge(
            indicator=True, actual_amount=Decimal("1.234"), reason="x"
        )
        errors = _run(ac)
        assert any(e.code == "BR-DEC-05" for e in errors), errors

    def test_header_charge_basis(self) -> None:
        ac = HeaderTradeAllowanceCharge(
            indicator=True,
            actual_amount=Decimal("1"),
            basis_amount=Decimal("100.123"),
            reason="x",
        )
        errors = _run(ac)
        assert any(e.code == "BR-DEC-06" for e in errors), errors


class TestLineAllowanceCharge:
    def test_line_allowance_amount(self) -> None:
        ac = LineTradeAllowanceCharge(
            indicator=False, actual_amount=Decimal("1.234"), reason="x"
        )
        errors = _run(ac, Profile.COMFORT)
        assert any(e.code == "BR-DEC-24" for e in errors), errors

    def test_line_allowance_basis(self) -> None:
        ac = LineTradeAllowanceCharge(
            indicator=False,
            actual_amount=Decimal("1"),
            basis_amount=Decimal("100.123"),
            reason="x",
        )
        errors = _run(ac, Profile.COMFORT)
        assert any(e.code == "BR-DEC-25" for e in errors), errors

    def test_line_charge_amount(self) -> None:
        ac = LineTradeAllowanceCharge(
            indicator=True, actual_amount=Decimal("1.234"), reason="x"
        )
        errors = _run(ac, Profile.COMFORT)
        assert any(e.code == "BR-DEC-27" for e in errors), errors

    def test_line_charge_basis(self) -> None:
        ac = LineTradeAllowanceCharge(
            indicator=True,
            actual_amount=Decimal("1"),
            basis_amount=Decimal("100.123"),
            reason="x",
        )
        errors = _run(ac, Profile.COMFORT)
        assert any(e.code == "BR-DEC-28" for e in errors), errors
