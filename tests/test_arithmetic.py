"""BR-CO-10..17 / BR-16 — document-level totals match the sums of their
line / allowance / charge / tax-breakdown contributions and the
``ApplicableTradeTax`` per-row arithmetic."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest as pt

from getafix.errors import ValidationErrors
from getafix.schema.accounting import ApplicableTradeTax, MonetarySummation, TaxTotal
from getafix.schema.line import (
    DocumentLineDocument,
    LineMonetarySummation,
    LineTradeAgreement,
    LineTradeDelivery,
    LineTradeSettlement,
    NetTradePrice,
    Quantity,
    TradeProduct,
)
from getafix.schema.settlement import PaymentTerms, TradeSettlement
from getafix.schema.trade import TradeLineItem
from getafix.schema.types import (
    CategoryCode,
    Currency,
    Profile,
    UNTDID2475TaxPointDateCode,
)
from tests._fixtures import make_vat_doc


def test_br_16_error():
    """BR-16: at BASIC and above an invoice must carry at least one
    line item; at MINIMUM / BASIC_WL the rule is dropped."""
    doc = make_vat_doc()
    doc.trade.items.clear()

    with pt.raises(ValidationErrors) as e:
        doc.validate()
    assert any(v.code == "BR-16" for v in e.value.errors)

    # At MINIMUM / BASIC_WL the BR-16 line-item requirement is dropped.
    # The fixture carries BASIC_WL+ fields, so relabelling it MINIMUM now
    # trips the generic field-profile gate — assert only that BR-16 itself
    # is gone, not that the (artificially downgraded) document is clean.
    doc.context.guideline.id = Profile.MINIMUM
    try:
        doc.validate()
    except ValidationErrors as exc:
        assert not any(v.code == "BR-16" for v in exc.errors)  # noqa: PT017
    doc.context.guideline.id = Profile.BASIC_WL
    doc.validate()


def test_br_co_15_grand_total_equals_tax_basis_plus_tax_total():
    """BR-CO-15: GrandTotalAmount (BT-112) = TaxBasisTotalAmount (BT-109)
    + TaxTotalAmount in invoice currency (BT-110)."""
    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=[TaxTotal(amount=Decimal("19"), currency_id=Currency.EUR)],
        grand_total=Decimal("999"),  # WRONG — should be 119
        due_amount=Decimal("999"),
    )
    settlement = TradeSettlement(
        currency_code=Currency.EUR,
        monetary_summation=summation,
        trade_taxes=[
            ApplicableTradeTax(
                calculated_amount=Decimal("19"),
                basis_amount=Decimal("100"),
                category_code=CategoryCode.T_S,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("19"),
            )
        ],
        terms=[PaymentTerms(due=date(2025, 2, 1))],
    )
    errors = settlement.validate_internal(Profile.BASIC_WL)
    assert any(v.code == "BR-CO-15" for v in errors)

    # Fix the math → passes.
    summation.grand_total = Decimal("119")
    summation.due_amount = Decimal("119")
    settlement.validate_internal(Profile.BASIC_WL)


def test_br_co_15_with_no_tax_total_treats_bt_110_as_zero():
    """When BT-110 is absent (e.g. a tax-exempt invoice), BR-CO-15
    reduces to BT-112 == BT-109."""
    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=None,
        grand_total=Decimal("100"),
        due_amount=Decimal("100"),
    )
    settlement = TradeSettlement(
        currency_code=Currency.EUR,
        monetary_summation=summation,
        trade_taxes=[
            ApplicableTradeTax(
                category_code=CategoryCode.T_E,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("0"),
                exemption_reason="Exempt",
            )
        ],
        terms=[PaymentTerms(due=date(2025, 2, 1))],
    )
    settlement.validate_internal(Profile.BASIC_WL)


def test_br_co_15_uses_only_invoice_currency_tax_total():
    """The BT-111 row (currency != BT-5) is not part of BR-CO-15."""
    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=[
            TaxTotal(amount=Decimal("19"), currency_id=Currency.EUR),  # BT-110
            TaxTotal(amount=Decimal("20"), currency_id=Currency.USD),  # BT-111
        ],
        grand_total=Decimal("119"),  # 100 + 19 only
        due_amount=Decimal("119"),
    )
    settlement = TradeSettlement(
        currency_code=Currency.EUR,
        tax_currency_code=Currency.USD,
        monetary_summation=summation,
        trade_taxes=[
            ApplicableTradeTax(
                calculated_amount=Decimal("19"),
                basis_amount=Decimal("100"),
                category_code=CategoryCode.T_S,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("19"),
            )
        ],
        terms=[PaymentTerms(due=date(2025, 2, 1))],
    )
    settlement.validate_internal(Profile.BASIC_WL)


def test_br_co_16_due_amount_equals_grand_total_minus_prepaid():
    """BR-CO-16: DuePayableAmount (BT-115) = GrandTotal (BT-112)
    - PrepaidTotal (BT-113) + RoundingAmount (BT-114). BT-114 isn't
    yet modelled in getafix; treat it as 0."""
    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=[TaxTotal(amount=Decimal("19"), currency_id=Currency.EUR)],
        grand_total=Decimal("119"),
        prepaid_total=Decimal("19"),
        due_amount=Decimal("999"),  # WRONG — expected 100
    )
    settlement = TradeSettlement(
        currency_code=Currency.EUR,
        monetary_summation=summation,
        trade_taxes=[
            ApplicableTradeTax(
                calculated_amount=Decimal("19"),
                basis_amount=Decimal("100"),
                category_code=CategoryCode.T_S,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("19"),
            )
        ],
        terms=[PaymentTerms(due=date(2025, 2, 1))],
    )
    errors = settlement.validate_internal(Profile.BASIC_WL)
    assert any(v.code == "BR-CO-16" for v in errors)

    summation.due_amount = Decimal("100")
    settlement.validate_internal(Profile.BASIC_WL)


def test_br_co_16_no_prepaid_total_means_due_equals_grand():
    """When BT-113 is absent (default 0), BR-CO-16 reduces to
    BT-115 == BT-112."""
    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=[TaxTotal(amount=Decimal("19"), currency_id=Currency.EUR)],
        grand_total=Decimal("119"),
        due_amount=Decimal("119"),
    )
    settlement = TradeSettlement(
        currency_code=Currency.EUR,
        monetary_summation=summation,
        trade_taxes=[
            ApplicableTradeTax(
                calculated_amount=Decimal("19"),
                basis_amount=Decimal("100"),
                category_code=CategoryCode.T_S,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("19"),
            )
        ],
        terms=[PaymentTerms(due=date(2025, 2, 1))],
    )
    settlement.validate_internal(Profile.BASIC_WL)


class TestBrCoArithmetic:
    """BR-CO-10..14 — document-level totals match the sums of their
    line / allowance / charge / tax-breakdown contributions."""

    def test_br_co_10_line_total_equals_sum_of_line_amounts(self) -> None:
        """BT-106 = sum of BT-131 across line items."""
        # Add a second line so we exercise the sum (not just one row).
        doc = make_vat_doc()
        doc.trade.items.append(
            TradeLineItem(
                associated_document=DocumentLineDocument(line_id="2"),
                product=TradeProduct(name="Widget 2"),
                agreement=LineTradeAgreement(
                    net_price=NetTradePrice(charge_amount=Decimal("50"))
                ),
                delivery=LineTradeDelivery(
                    billed_quantity=Quantity(value=Decimal("1"), unit_code="C62")
                ),
                settlement=LineTradeSettlement(
                    applicable_trade_tax=ApplicableTradeTax(
                        category_code=CategoryCode.T_S,
                        due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                        rate_applicable_percent=Decimal("19"),
                    ),
                    monetary_summation=LineMonetarySummation(line_total=Decimal("50")),
                ),
            )
        )
        # Sum of line totals = 100 + 50 = 150, but header still says 100.
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-CO-10" for v in e.value.errors)

    def test_br_co_10_passes_when_totals_match(self) -> None:
        """Single-line doc: BT-106 should equal the one BT-131."""
        make_vat_doc().validate()

    def test_br_co_10_skipped_when_line_total_absent(self) -> None:
        """When ``line_total`` (BT-106) is absent, BR-CO-10 cannot fire —
        BR-12 takes over and complains about the missing field instead.
        Keeping these two rules independent matters because at MINIMUM
        BT-106 is not part of the XSD and neither rule should fire."""
        doc = make_vat_doc()
        doc.trade.settlement.monetary_summation.line_total = None
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-12" for v in e.value.errors)
        assert not any(v.code == "BR-CO-10" for v in e.value.errors)

    def test_br_co_11_allowance_total_matches_sum(self) -> None:
        """BT-107 = sum of document-level allowance BT-92."""
        # Use zero-rated categories so the VAT math collapses to zero
        # and ``tax_basis_total == grand_total``; this test only
        # exercises the allowance-sum identity.
        doc = make_vat_doc(
            line_category=CategoryCode.T_Z, allowance_category=CategoryCode.T_Z
        )
        summation = doc.trade.settlement.monetary_summation
        # One allowance of 5.00 in the helper; declare BT-107 wrongly.
        summation.allowance_total = Decimal("99")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-CO-11" for v in e.value.errors)

        # Match the sum and BT-109 / BT-115 to keep the rest happy.
        summation.allowance_total = Decimal("5.00")
        summation.tax_basis_total = Decimal("95")  # 100 - 5
        summation.grand_total = Decimal("95")
        summation.due_amount = Decimal("95")
        doc.validate()

    def test_br_co_12_charge_total_matches_sum(self) -> None:
        """BT-108 = sum of document-level charge BT-99."""
        # Use zero-rated categories so the VAT math collapses to zero.
        doc = make_vat_doc(
            line_category=CategoryCode.T_Z, charge_category=CategoryCode.T_Z
        )
        summation = doc.trade.settlement.monetary_summation
        # One charge of 3.00 in the helper; declare BT-108 wrongly.
        summation.charge_total = Decimal("99")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-CO-12" for v in e.value.errors)

        summation.charge_total = Decimal("3.00")
        summation.tax_basis_total = Decimal("103")  # 100 + 3
        summation.grand_total = Decimal("103")
        summation.due_amount = Decimal("103")
        doc.validate()

    def test_br_co_17_per_row_calculated_equals_basis_times_rate(self) -> None:
        """BT-117 (CalculatedAmount) = round(BT-116 * BT-119 / 100, 2)
        for each BG-23 row at <= COMFORT. EXTENDED replaces this with
        the per-category BR-FXEXT-*-09 rounding-tolerance form."""
        # Wrong arithmetic: 100 * 19 / 100 = 19, but we declare 17.
        bad = ApplicableTradeTax(
            calculated_amount=Decimal("17"),
            basis_amount=Decimal("100"),
            category_code=CategoryCode.T_S,
            due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
            rate_applicable_percent=Decimal("19"),
        )
        errors = bad.validate_internal(Profile.BASIC_WL)
        assert any(v.code == "BR-CO-17" for v in errors)

        # Correct arithmetic passes.
        ApplicableTradeTax(
            calculated_amount=Decimal("19.00"),
            basis_amount=Decimal("100"),
            category_code=CategoryCode.T_S,
            due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
            rate_applicable_percent=Decimal("19"),
        ).validate_internal(Profile.BASIC_WL)

        # Rounded-to-2dp also passes — 99.99 * 19 / 100 = 18.9981 → 19.00.
        ApplicableTradeTax(
            calculated_amount=Decimal("19.00"),
            basis_amount=Decimal("99.99"),
            category_code=CategoryCode.T_S,
            due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
            rate_applicable_percent=Decimal("19"),
        ).validate_internal(Profile.BASIC_WL)

        # EXTENDED: BR-CO-17 is dropped (replaced by BR-FXEXT-S-09 et al.)
        bad.validate_internal(Profile.EXTENDED)

    def test_br_co_17_skipped_without_rate(self) -> None:
        """When BT-119 is absent (e.g. 'Not subject to VAT'), BR-CO-17
        is moot."""
        ApplicableTradeTax(
            calculated_amount=Decimal("0"),
            basis_amount=Decimal("100"),
            category_code=CategoryCode.T_O,
            due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
        ).validate_internal(Profile.BASIC_WL)

    def test_br_co_14_tax_total_equals_sum_of_tax_amounts(self) -> None:
        """BT-110 = sum of BT-117 across the header BG-23 rows."""
        doc = make_vat_doc()
        summation = doc.trade.settlement.monetary_summation
        # Two BG-23 rows: 10% on 50, 20% on 50 → sum 5 + 10 = 15.
        doc.trade.settlement.trade_taxes = [
            ApplicableTradeTax(
                calculated_amount=Decimal("5"),
                basis_amount=Decimal("50"),
                category_code=CategoryCode.T_S,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("10"),
            ),
            ApplicableTradeTax(
                calculated_amount=Decimal("10"),
                basis_amount=Decimal("50"),
                category_code=CategoryCode.T_S,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("20"),
            ),
        ]
        # Declare wrong BT-110.
        summation.tax_total = [TaxTotal(amount=Decimal("99"), currency_id=Currency.EUR)]
        # Keep BR-CO-15 / 16 happy.
        summation.grand_total = summation.tax_basis_total + Decimal("99")
        summation.due_amount = summation.grand_total
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-CO-14" for v in e.value.errors)

        # Correct sum.
        summation.tax_total = [TaxTotal(amount=Decimal("15"), currency_id=Currency.EUR)]
        summation.grand_total = summation.tax_basis_total + Decimal("15")
        summation.due_amount = summation.grand_total
        doc.validate()

    def test_br_co_13_tax_basis_identity(self) -> None:
        """BT-109 = ΣBT-131 - BT-107 + BT-108."""
        doc = make_vat_doc(
            line_category=CategoryCode.T_Z,
            allowance_category=CategoryCode.T_Z,
            charge_category=CategoryCode.T_Z,
        )
        summation = doc.trade.settlement.monetary_summation
        # Keep tax_basis_total / grand_total / due_amount in sync so
        # BR-CO-15 + BR-CO-16 stay satisfied; only break the BT-109
        # vs ΣBT-131 identity that BR-CO-13 watches.
        summation.tax_basis_total = Decimal("999")
        summation.grand_total = Decimal("999")
        summation.due_amount = Decimal("999")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-CO-13" for v in e.value.errors)

        # Real identity: 100 - 5 + 3 = 98.
        summation.tax_basis_total = Decimal("98")
        summation.grand_total = Decimal("98")
        summation.due_amount = Decimal("98")
        doc.validate()
