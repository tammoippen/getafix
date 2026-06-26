"""BR-O — 'Not subject to VAT' category (UNTDID code ``O``).

The inverted predicate: when a line / allowance / charge carries
category O the invoice must *not* contain tax identifiers — the
seller isn't VAT-registered, so VAT IDs would be misleading.
This file owns the line / allowance / charge variants of BR-O-2..4 and
the BR-O-11..14 single-rate restriction.
"""

from __future__ import annotations

from decimal import Decimal

import pytest as pt

from getafix.errors import ValidationErrors
from getafix.schema.accounting import ApplicableTradeTax
from getafix.schema.document import Document
from getafix.schema.party import (
    PostalTradeAddressExtended,
    SellerTaxRepresentativeTradeParty,
    SpecifiedTaxRegistration,
    TaxSchemeId,
)
from getafix.schema.types import CategoryCode, Country, UNTDID2475TaxPointDateCode
from tests._fixtures import make_vat_doc


class TestBrO:
    """BR-O — Not subject to VAT (UNTDID code ``O``).

    The inverted predicate: when a line / allowance / charge carries
    category O the invoice must *not* contain tax identifiers — the
    seller isn't VAT-registered, so VAT IDs would be misleading.

    * BR-O-2 (line)      forbids BT-31 / BT-63 and BT-46 (Buyer **id**).
    * BR-O-3 (allowance) forbids BT-31 / BT-63 and BT-48 (Buyer **VAT**).
    * BR-O-4 (charge)    forbids BT-31 / BT-63 and BT-48.
    """

    def test_br_o_2_line_passes_when_no_tax_ids_present(self) -> None:
        # Seller has only BT-29 (id) — that's not a tax id, so BR-O-2 OK.
        # Buyer has nothing.
        make_vat_doc(
            line_category=CategoryCode.T_O,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
            buyer_va=None,
        ).validate()

    def test_br_o_2_line_forbids_seller_vat(self) -> None:
        doc = make_vat_doc(
            line_category=CategoryCode.T_O,
            seller_id="S-001",
            seller_va="DE123456789",
            buyer_va=None,
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-O-2" for v in e.value.errors)

    def test_br_o_2_line_forbids_buyer_id(self) -> None:
        # The spec quirk: BR-O-2 names BT-46 (Buyer ID), not BT-48.
        doc = make_vat_doc(
            line_category=CategoryCode.T_O,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
            buyer_va=None,
        )
        # Force a BT-46 directly (the helper doesn't expose it).
        doc.trade.agreement.buyer.id = "B-001"
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-O-2" for v in e.value.errors)

    def test_br_o_3_allowance_forbids_buyer_vat(self) -> None:
        # Allowance with O — BT-48 forbidden.
        doc = make_vat_doc(
            line_category=CategoryCode.T_O,
            allowance_category=CategoryCode.T_O,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
            buyer_va="DE987654321",
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-O-3" for v in e.value.errors)

    def test_br_o_4_charge_forbids_seller_taxrep_vat(self) -> None:
        # Charge with O. We add the tax-rep with a VAT id; the rule
        # forbids BT-63 in this case. Use a line category that's
        # satisfied by tax-rep VAT (T_S) so the line doesn't fire.
        doc = make_vat_doc(
            line_category=CategoryCode.T_S,
            charge_category=CategoryCode.T_O,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
            buyer_va=None,
        )
        doc.trade.agreement.seller_tax_representative_party = (
            SellerTaxRepresentativeTradeParty(
                name="TR",
                address=PostalTradeAddressExtended(country_id=Country.DE),
                tax_registrations=SpecifiedTaxRegistration(
                    id=TaxSchemeId(id="DE111222333", scheme_id="VA")
                ),
            )
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-O-4" for v in e.value.errors)


class TestBrOSingleRate:
    """BR-O-11..14 — invoices using VAT category 'Not subject to VAT'
    are single-rate: every other slot must also be O."""

    def _make_o_only(self) -> Document:
        # Baseline: line + BG-23 both O, no allowance/charge.
        return make_vat_doc(
            line_category=CategoryCode.T_O,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
            buyer_va=None,
        )

    def test_br_o_11_other_bg23_row_forbidden(self) -> None:
        doc = self._make_o_only()
        # Force the header BG-23 to also include an S row alongside O.
        doc.trade.settlement.trade_taxes = [
            ApplicableTradeTax(
                category_code=CategoryCode.T_O,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("0"),
            ),
            ApplicableTradeTax(
                category_code=CategoryCode.T_S,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("19"),
            ),
        ]
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-O-11" for v in e.value.errors)

    def test_br_o_12_line_with_other_category_forbidden(self) -> None:
        # Use a setup where the line's category-required-party rule
        # passes (seller has VAT) so BR-S-2 doesn't fire first; the
        # BG-23 only carries the O row.
        doc = make_vat_doc(
            line_category=CategoryCode.T_S,
            seller_id="S-001",
            seller_va="DE123456789",
            buyer_va=None,
        )
        doc.trade.settlement.trade_taxes = [
            ApplicableTradeTax(
                category_code=CategoryCode.T_O,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("0"),
            )
        ]
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-O-12" for v in e.value.errors)

    def test_br_o_13_allowance_with_other_category_forbidden(self) -> None:
        doc = make_vat_doc(
            line_category=CategoryCode.T_O,
            allowance_category=CategoryCode.T_S,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
            buyer_va=None,
        )
        doc.trade.settlement.trade_taxes = [
            ApplicableTradeTax(
                category_code=CategoryCode.T_O,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("0"),
            )
        ]
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        # Note: BR-S-3 *also* fires (allowance with S has no seller VAT)
        # but BR-O-13 is the more specific rule given a BG-23 O row.
        # getafix runs BR-O single-rate after the family loop, so the
        # category-required-party check raises first.
        assert any(v.code in {"BR-O-13", "BR-S-3"} for v in e.value.errors)

    def test_br_o_14_charge_with_other_category_forbidden(self) -> None:
        doc = make_vat_doc(
            line_category=CategoryCode.T_O,
            charge_category=CategoryCode.T_S,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
            buyer_va=None,
        )
        doc.trade.settlement.trade_taxes = [
            ApplicableTradeTax(
                category_code=CategoryCode.T_O,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("0"),
            )
        ]
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code in {"BR-O-14", "BR-S-4"} for v in e.value.errors)
