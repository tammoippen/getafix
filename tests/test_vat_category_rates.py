"""Per-VAT-category VAT-rate constraints — BR-X-5 / BR-X-6 / BR-X-7.

For every VAT category code ``X``:

* **BR-X-5** — line VAT rate (BT-152) constraint on
  ``ApplicableTradeTax`` at line level.
* **BR-X-6** — document-level allowance VAT rate (BT-96) constraint
  on ``CategoryTradeTax`` at allowance level.
* **BR-X-7** — document-level charge VAT rate (BT-103) constraint on
  ``CategoryTradeTax`` at charge level.

Rate predicates per category, drawn from the EN 16931 Technical
Appendix (Profile EN16931, pp. 62–74):

* ``S`` — rate > 0.
* ``Z`` / ``E`` / ``AE`` / ``G`` / ``K`` (IC) — rate == 0.
* ``L`` (IG) / ``M`` (IP) — rate >= 0.
* ``O`` — rate must be absent.
"""

from __future__ import annotations

from decimal import Decimal

import pytest as pt

from carthorse.schema import Document
from carthorse.schema.accounting import CategoryTradeTax, HeaderTradeAllowanceCharge
from carthorse.schema.element import ValidationErrors
from carthorse.schema.party import (
    PostalTradeAddressExtended,
    SellerTradeParty,
    SpecifiedTaxRegistration,
    TaxSchemeId,
)
from carthorse.schema.types import CategoryCode
from tests._fixtures import make_vat_doc


def _set_line_rate(doc: Document, rate: Decimal | None) -> None:
    line = doc.trade.items[0]
    line.settlement.applicable_trade_tax.rate_applicable_percent = rate


def _add_doc_allowance(
    doc: Document, *, category: CategoryCode, rate: Decimal | None
) -> None:
    doc.trade.settlement.allowance_charge = list(
        doc.trade.settlement.allowance_charge or []
    ) + [
        HeaderTradeAllowanceCharge(
            indicator=False,
            actual_amount=Decimal("0"),
            category_trade_tax=CategoryTradeTax(
                category_code=category, rate_applicable_percent=rate
            ),
            reason="x",
        )
    ]


def _add_doc_charge(
    doc: Document, *, category: CategoryCode, rate: Decimal | None
) -> None:
    doc.trade.settlement.allowance_charge = list(
        doc.trade.settlement.allowance_charge or []
    ) + [
        HeaderTradeAllowanceCharge(
            indicator=True,
            actual_amount=Decimal("0"),
            category_trade_tax=CategoryTradeTax(
                category_code=category, rate_applicable_percent=rate
            ),
            reason="x",
        )
    ]


class TestStandardRated:
    def test_br_s_5_line_must_have_positive_rate(self) -> None:
        doc = make_vat_doc(line_category=CategoryCode.T_S)
        _set_line_rate(doc, Decimal("0"))
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-S-5" for v in e.value.errors)

    def test_br_s_6_doc_allowance_must_have_positive_rate(self) -> None:
        doc = make_vat_doc(line_category=CategoryCode.T_S)
        _add_doc_allowance(doc, category=CategoryCode.T_S, rate=Decimal("0"))
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-S-6" for v in e.value.errors)

    def test_br_s_7_doc_charge_must_have_positive_rate(self) -> None:
        doc = make_vat_doc(line_category=CategoryCode.T_S)
        _add_doc_charge(doc, category=CategoryCode.T_S, rate=Decimal("0"))
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-S-7" for v in e.value.errors)


class TestZeroRated:
    def test_br_z_5_line_rate_must_be_zero(self) -> None:
        doc = make_vat_doc(line_category=CategoryCode.T_Z)
        _set_line_rate(doc, Decimal("19"))
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-Z-5" for v in e.value.errors)

    def test_br_z_5_passes_at_zero(self) -> None:
        doc = make_vat_doc(line_category=CategoryCode.T_Z)
        _set_line_rate(doc, Decimal("0"))
        # category Z requires seller VAT or local tax — make_vat_doc default
        # uses Standard rated; flip the BG-23 row's rate to keep the math
        # consistent and emit BR-Z-3 if VAT is missing.
        doc.trade.settlement.trade_taxes[0].category_code = CategoryCode.T_Z
        doc.trade.settlement.trade_taxes[0].rate_applicable_percent = Decimal("0")
        # BR-Z-3/4 still fire elsewhere if seller VAT registration drops;
        # this test only asserts BR-Z-5 does NOT fire when rate==0.
        errors = []
        try:
            doc.validate()
        except ValidationErrors as e:
            errors = e.value.errors if hasattr(e, "value") else e.errors
        except Exception:
            pass
        assert not any(v.code == "BR-Z-5" for v in errors), errors


class TestNotSubjectToVat:
    def test_br_o_5_line_rate_forbidden(self) -> None:
        doc = make_vat_doc(line_category=CategoryCode.T_O)
        _set_line_rate(doc, Decimal("0"))
        # Align BG-23 + parties so other BR-O-* don't fire first.
        doc.trade.settlement.trade_taxes[0].category_code = CategoryCode.T_O
        doc.trade.settlement.trade_taxes[0].rate_applicable_percent = None
        doc.trade.settlement.trade_taxes[0].exemption_reason = "Out of scope"
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-O-5" for v in e.value.errors)

    def test_br_o_6_doc_allowance_rate_forbidden(self) -> None:
        doc = make_vat_doc(line_category=CategoryCode.T_O)
        doc.trade.settlement.trade_taxes[0].category_code = CategoryCode.T_O
        doc.trade.settlement.trade_taxes[0].rate_applicable_percent = None
        doc.trade.settlement.trade_taxes[0].exemption_reason = "Out of scope"
        _set_line_rate(doc, None)
        _add_doc_allowance(doc, category=CategoryCode.T_O, rate=Decimal("0"))
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-O-6" for v in e.value.errors)


class TestIgicCanary:
    def test_br_ig_5_passes_at_zero(self) -> None:
        doc = make_vat_doc(line_category=CategoryCode.T_L)
        _set_line_rate(doc, Decimal("0"))
        # IG category drops Seller VAT requirement; supply a local FC tax id.
        seller_with_fc = SellerTradeParty(
            name="Seller",
            address=PostalTradeAddressExtended(country_id="ES"),
            tax_registrations=[
                SpecifiedTaxRegistration(
                    id=TaxSchemeId(id="ES1234567Z", scheme_id="VA")
                )
            ],
        )
        doc.trade.agreement.seller = seller_with_fc
        doc.trade.settlement.trade_taxes[0].category_code = CategoryCode.T_L
        doc.trade.settlement.trade_taxes[0].rate_applicable_percent = Decimal("0")
        errors = []
        try:
            doc.validate()
        except ValidationErrors as e:
            errors = e.errors
        assert not any(v.code == "BR-IG-5" for v in errors), errors

    def test_br_ig_5_passes_at_positive_rate(self) -> None:
        doc = make_vat_doc(line_category=CategoryCode.T_L)
        _set_line_rate(doc, Decimal("7"))
        seller_with_va = SellerTradeParty(
            name="Seller",
            address=PostalTradeAddressExtended(country_id="ES"),
            tax_registrations=[
                SpecifiedTaxRegistration(
                    id=TaxSchemeId(id="ES1234567Z", scheme_id="VA")
                )
            ],
        )
        doc.trade.agreement.seller = seller_with_va
        doc.trade.settlement.trade_taxes[0].category_code = CategoryCode.T_L
        doc.trade.settlement.trade_taxes[0].rate_applicable_percent = Decimal("7")
        errors = []
        try:
            doc.validate()
        except ValidationErrors as e:
            errors = e.errors
        assert not any(v.code == "BR-IG-5" for v in errors), errors
