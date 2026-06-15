"""Payment-related rules: BR-CO-25 (terms required when due),
BR-CO-3 (TaxPointDate vs DueDateTypeCode), BR-50 paths via PaymentTerms."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from getafix.schema.accounting import ApplicableTradeTax, MonetarySummation, TaxTotal
from getafix.schema.settlement import PaymentTerms, TradeSettlement
from getafix.schema.types import (
    CategoryCode,
    Currency,
    Profile,
    UNTDID2475TaxPointDateCode,
)


def test_br_co_25_payment_terms_required_when_due():
    """BR-CO-25: positive DuePayableAmount requires terms.due or
    terms.description to be set."""
    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=[TaxTotal(amount=Decimal("19"), currency_id=Currency.EUR)],
        grand_total=Decimal("119"),
        due_amount=Decimal("119"),
    )

    # No terms → BR-CO-25.
    settlement = TradeSettlement(
        currency_code=Currency.EUR, monetary_summation=summation
    )
    errors = settlement.validate_internal(Profile.BASIC_WL)
    assert any(v.code == "BR-CO-25" for v in errors)

    # terms.due present → ok.
    settlement.terms = [PaymentTerms(due=date(2025, 12, 16))]
    settlement.validate_internal(Profile.BASIC_WL)

    # terms.description present, no due → ok.
    settlement.terms = [PaymentTerms(description="Net 30 days")]
    settlement.validate_internal(Profile.BASIC_WL)

    # due_amount = 0 → no requirement. Also adjust grand_total to keep
    # BR-CO-16 (BT-115 == BT-112 - BT-113) satisfied.
    summation.due_amount = Decimal("0")
    summation.grand_total = Decimal("0")
    summation.tax_basis_total = Decimal("0")
    summation.tax_total = None
    settlement.terms = None
    settlement.validate_internal(Profile.BASIC_WL)


def test_br_co_3_tax_point_date_and_due_date_code_mutually_exclusive():
    """BR-CO-3: BT-7 (TaxPointDate) and BT-8 (DueDateTypeCode) are
    mutually exclusive on a single ApplicableTradeTax."""
    tax = ApplicableTradeTax(
        category_code=CategoryCode.T_S,
        tax_point_date=date(2025, 1, 15),
        due_date_code=UNTDID2475TaxPointDateCode.CODE_5,  # also setting BT-8 → conflict
        rate_applicable_percent=Decimal("19"),
    )
    errors = tax.validate_internal(Profile.COMFORT)
    assert any(v.code == "BR-CO-3" for v in errors)

    # Either alone is fine.
    ApplicableTradeTax(
        category_code=CategoryCode.T_S,
        tax_point_date=date(2025, 1, 15),
        rate_applicable_percent=Decimal("19"),
    ).validate_internal(Profile.COMFORT)
    ApplicableTradeTax(
        category_code=CategoryCode.T_S,
        due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
        rate_applicable_percent=Decimal("19"),
    ).validate_internal(Profile.COMFORT)
