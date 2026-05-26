"""EXTENDED-only business rules — ``BR-FXEXT-*`` (§5.2 + §5.3 of
``docs/PROFILES/EXTENDED.md``).

Two themes:

* §5.2 — tolerance-banded replacements for the strict EN 16931
  ``BR-CO-{10,11,12,13,15}`` identities. The matching EN 16931
  rules short-circuit at EXTENDED so only the EXTENDED variants
  fire. ``BR-FXEXT-CO-04`` and ``BR-FXEXT-CO-15`` are placeholders
  whose strict identity is preserved.

* §5.3 — per-VAT-category sum identities replacing ``BR-CO-17``
  with one ``BR-FXEXT-{cat}-08`` per category, plus ``BR-FXEXT-S-09``
  (the per-rate VAT-amount derivation check, only meaningful for
  category ``S``).
"""

from __future__ import annotations

from decimal import Decimal

import pytest as pt

from carthorse.schema import Profile
from carthorse.schema.element import ValidationErrors
from carthorse.schema.settlement import (
    AppliedTradeTax,
    LogisticsServiceCharge,
)
from carthorse.schema.types import CategoryCode
from tests._fixtures import make_vat_doc


def _ext(doc):
    """Switch a make_vat_doc-built BASIC document to EXTENDED."""
    doc.context.guideline.id = Profile.EXTENDED
    return doc


def _codes(exc: ValidationErrors) -> set[str]:
    return {v.code for v in exc.errors}


class TestFXExtCOTolerance:
    """§5.2 — tolerance-banded BR-CO-* replacements."""

    def test_co_10_accepts_one_cent_per_line_drift(self) -> None:
        # Single-line doc: tolerance = 0.01 × 1 = 0.01. Drift BT-106
        # by exactly 0.01 and expect the EN 16931 BR-CO-10 to NOT
        # fire (because it short-circuits at EXTENDED) and the
        # EXTENDED variant to accept the drift.
        doc = _ext(make_vat_doc())
        doc.trade.settlement.monetary_summation.line_total += Decimal("0.01")
        # Also drift dependent totals so the per-category check stays
        # happy — we only want to assert CO-10 acceptance here.
        doc.trade.settlement.monetary_summation.tax_basis_total += Decimal("0.01")
        doc.trade.settlement.monetary_summation.grand_total += Decimal("0.01")
        doc.trade.settlement.monetary_summation.due_amount += Decimal("0.01")
        doc.validate()  # no errors

    def test_co_10_fires_beyond_tolerance(self) -> None:
        doc = _ext(make_vat_doc())
        # 0.02 drift on a single-line doc (tolerance 0.01) exceeds.
        doc.trade.settlement.monetary_summation.line_total += Decimal("0.02")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-CO-10" in _codes(e.value)

    def test_co_11_skipped_when_no_allowance_total(self) -> None:
        # Default doc has no allowance — allowance_total is None →
        # CO-11 skipped entirely (no firing, no error).
        doc = _ext(make_vat_doc())
        doc.validate()  # clean

    def test_co_12_includes_logistics_charges_in_sum(self) -> None:
        # Add a logistics charge: charge_total must equal Σ BT-99 +
        # Σ BT-X-272 (the EXTENDED variant folds logistics in).
        doc = _ext(make_vat_doc(charge_category=CategoryCode.T_S))
        doc.trade.settlement.logistics_service_charges = [
            LogisticsServiceCharge(
                description="Freight",
                applied_amount=Decimal("4.00"),
                applied_trade_tax=[
                    AppliedTradeTax(
                        category_code=CategoryCode.T_S,
                        rate_applicable_percent=Decimal("19"),
                    )
                ],
            )
        ]
        # Default charge from make_vat_doc is 3.00; with the new
        # 4.00 logistics charge the charge_total should be 7.00.
        doc.trade.settlement.monetary_summation.charge_total = Decimal("7.00")
        # Re-derive BT-109 and downstream so only CO-12 is under
        # test (the other identities also need to hold).
        # BT-106 (line total) stays at 100.00; allowances none;
        # charges 7.00; → BT-109 = 100 + 7 = 107. BT-110 = 19% of
        # 107 = 20.33; BT-112 = 127.33.
        doc.trade.settlement.monetary_summation.tax_basis_total = Decimal("107.00")
        doc.trade.settlement.trade_taxes[0].basis_amount = Decimal("107.00")
        doc.trade.settlement.trade_taxes[0].calculated_amount = Decimal("20.33")
        doc.trade.settlement.monetary_summation.tax_total = [
            type(doc.trade.settlement.monetary_summation.tax_total[0])(
                amount=Decimal("20.33"),
                currency_id=doc.trade.settlement.currency_code,
            )
        ]
        doc.trade.settlement.monetary_summation.grand_total = Decimal("127.33")
        doc.trade.settlement.monetary_summation.due_amount = Decimal("127.33")
        doc.validate()  # clean — CO-12 must accept the logistics-inclusive sum

    def test_co_12_fires_when_logistics_omitted_from_total(self) -> None:
        doc = _ext(make_vat_doc(charge_category=CategoryCode.T_S))
        doc.trade.settlement.logistics_service_charges = [
            LogisticsServiceCharge(
                description="Freight",
                applied_amount=Decimal("4.00"),
                applied_trade_tax=[
                    AppliedTradeTax(
                        category_code=CategoryCode.T_S,
                        rate_applicable_percent=Decimal("19"),
                    )
                ],
            )
        ]
        # Leave charge_total at 3.00 (the original charge only) —
        # CO-12 should now fire because 3.00 ≠ 3.00 + 4.00.
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-CO-12" in _codes(e.value)

    def test_co_13_includes_logistics_in_bt109(self) -> None:
        # The .sch's actual XPath for CO-13 folds logistics into
        # the charge sum even though the human-readable text says
        # otherwise. BT-109 must reflect logistics charges.
        doc = _ext(make_vat_doc())
        doc.trade.settlement.logistics_service_charges = [
            LogisticsServiceCharge(
                description="Freight",
                applied_amount=Decimal("4.00"),
                applied_trade_tax=[
                    AppliedTradeTax(
                        category_code=CategoryCode.T_S,
                        rate_applicable_percent=Decimal("19"),
                    )
                ],
            )
        ]
        # If we don't push 4.00 into BT-108 / BT-109 we'd see CO-13
        # fire as well — that's the bad case. Update the totals so
        # CO-13 sees a self-consistent document.
        doc.trade.settlement.monetary_summation.charge_total = Decimal("4.00")
        doc.trade.settlement.monetary_summation.tax_basis_total = Decimal("104.00")
        doc.trade.settlement.trade_taxes[0].basis_amount = Decimal("104.00")
        doc.trade.settlement.trade_taxes[0].calculated_amount = Decimal("19.76")
        doc.trade.settlement.monetary_summation.tax_total = [
            type(doc.trade.settlement.monetary_summation.tax_total[0])(
                amount=Decimal("19.76"),
                currency_id=doc.trade.settlement.currency_code,
            )
        ]
        doc.trade.settlement.monetary_summation.grand_total = Decimal("123.76")
        doc.trade.settlement.monetary_summation.due_amount = Decimal("123.76")
        doc.validate()  # clean

    def test_co_13_fires_when_bt109_excludes_logistics(self) -> None:
        doc = _ext(make_vat_doc())
        doc.trade.settlement.logistics_service_charges = [
            LogisticsServiceCharge(
                description="Freight",
                applied_amount=Decimal("4.00"),
                applied_trade_tax=[
                    AppliedTradeTax(
                        category_code=CategoryCode.T_S,
                        rate_applicable_percent=Decimal("19"),
                    )
                ],
            )
        ]
        doc.trade.settlement.monetary_summation.charge_total = Decimal("4.00")
        # Leave tax_basis_total at 100.00 (i.e. exclude the
        # logistics contribution) → CO-13 should fire.
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-CO-13" in _codes(e.value)


class TestFXExtPerCategorySums:
    """§5.3 — per-VAT-category sum identities (BR-FXEXT-{cat}-08 / -09)."""

    def test_s_08_passes_on_default_doc(self) -> None:
        # Default make_vat_doc has one S-rated line at 100 / 19% →
        # BG-23 row basis=100. The category-S sum identity should
        # accept it cleanly.
        doc = _ext(make_vat_doc())
        doc.validate()

    def test_s_08_fires_on_basis_mismatch(self) -> None:
        doc = _ext(make_vat_doc())
        # Inflate BG-23 BT-116 beyond what the lines justify.
        doc.trade.settlement.trade_taxes[0].basis_amount = Decimal("110.00")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-S-08" in _codes(e.value)

    def test_s_09_fires_on_tax_amount_mismatch(self) -> None:
        doc = _ext(make_vat_doc())
        # BG-23 row: 100 × 19% = 19.00. Set calculated_amount way
        # off to trigger -09 — but keep tax_basis_total / grand
        # consistent so the cross-rule machinery doesn't drown the
        # signal.
        doc.trade.settlement.trade_taxes[0].calculated_amount = Decimal("30.00")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-S-09" in _codes(e.value)
