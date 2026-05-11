"""VAT-category required-party rules.

Each VAT category code constrains which Seller / Buyer identifiers must
be present on the invoice — this file owns the BR-AE / BR-E / BR-IC /
BR-S / BR-Z / BR-IG / BR-IP -2/-3/-4 families (line / allowance /
charge variants). BR-O (the inverted "not subject to VAT" predicate)
lives in :mod:`tests.test_vat_not_subject`; the BR-IC delivery rules
live in :mod:`tests.test_vat_intra_community`.
"""

from __future__ import annotations

from datetime import date

import pytest as pt

from carthorse.schema.delivery import SupplyChainEvent
from carthorse.schema.element import ValidationErrors
from carthorse.schema.party import PostalTradeAddressExtended, ShipToTradeParty
from carthorse.schema.types import CategoryCode
from tests._fixtures import make_vat_doc


class TestBrAe:
    """BR-AE — Reverse charge VAT category."""

    def test_br_ae_2_line_requires_seller_and_buyer_vat(self) -> None:
        # Buyer has no VAT id and no legal organisation → fails.
        doc = make_vat_doc(
            line_category=CategoryCode.T_AE, buyer_va=None, buyer_legal_id=None
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-AE-2" for v in e.value.errors)

    def test_br_ae_2_passes_with_buyer_vat(self) -> None:
        make_vat_doc(line_category=CategoryCode.T_AE).validate()

    def test_br_ae_2_passes_with_buyer_legal_only(self) -> None:
        # Buyer has no VAT id but has a legal registration id (BT-47).
        make_vat_doc(
            line_category=CategoryCode.T_AE, buyer_va=None, buyer_legal_id="HRB12345"
        ).validate()

    def test_br_ae_2_requires_seller_vat_or_local_or_taxrep(self) -> None:
        # Drop every seller identifier — even with a buyer VAT, the line
        # needs the seller side identified per BR-AE-2.
        doc = make_vat_doc(
            line_category=CategoryCode.T_AE, seller_va=None, seller_fc=None
        )
        # BR-CO-26 fires first (seller must be identifiable at all).
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-CO-26" for v in e.value.errors)

    def test_br_ae_3_doc_level_allowance_requires_seller_and_buyer_vat(self) -> None:
        # Allowance (BG-20) with category AE; buyer has no identifiers.
        doc = make_vat_doc(
            line_category=CategoryCode.T_S,
            allowance_category=CategoryCode.T_AE,
            buyer_va=None,
            buyer_legal_id=None,
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-AE-3" for v in e.value.errors)

    def test_br_ae_3_passes_with_buyer_legal_id(self) -> None:
        make_vat_doc(
            line_category=CategoryCode.T_S,
            allowance_category=CategoryCode.T_AE,
            buyer_va=None,
            buyer_legal_id="HRB12345",
        ).validate()

    def test_br_ae_4_doc_level_charge_requires_seller_and_buyer_vat(self) -> None:
        # Charge (BG-21) with category AE; buyer has no identifiers.
        doc = make_vat_doc(
            line_category=CategoryCode.T_S,
            charge_category=CategoryCode.T_AE,
            buyer_va=None,
            buyer_legal_id=None,
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-AE-4" for v in e.value.errors)


class TestBrE:
    """BR-E — Exempt from VAT: Seller VAT/local/tax-rep required;
    Buyer side unrestricted."""

    def test_br_e_2_line_requires_seller_vat_or_local_or_taxrep(self) -> None:
        # Seller has only an FC tax id (which counts for BR-E-2) plus a
        # BT-29 to satisfy BR-CO-26; no VAT registration.
        # Buyer has nothing — that's allowed for E.
        make_vat_doc(
            line_category=CategoryCode.T_E,
            seller_id="S-001",
            seller_va=None,
            seller_fc="123/456/789",
            buyer_va=None,
        ).validate()

    def test_br_e_2_fails_without_any_seller_tax_id(self) -> None:
        # Seller has BT-29 (so BR-CO-26 passes) but no VAT and no FC.
        doc = make_vat_doc(
            line_category=CategoryCode.T_E,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
            buyer_va=None,
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-E-2" for v in e.value.errors)

    def test_br_e_2_line_passes_with_seller_vat(self) -> None:
        make_vat_doc(line_category=CategoryCode.T_E, buyer_va=None).validate()

    def test_br_e_3_doc_level_allowance_with_e_passes_when_seller_identifiable(
        self,
    ) -> None:
        make_vat_doc(
            line_category=CategoryCode.T_S,
            allowance_category=CategoryCode.T_E,
            buyer_va=None,
        ).validate()

    def test_br_e_4_doc_level_charge_with_e_passes(self) -> None:
        make_vat_doc(
            line_category=CategoryCode.T_S,
            charge_category=CategoryCode.T_E,
            buyer_va=None,
        ).validate()


class TestBrIc:
    """BR-IC — Intra-community supply (UNTDID code ``K``).

    Requires Seller VAT (or tax-rep VAT) AND Buyer VAT.
    """

    def test_br_ic_2_line_passes_with_both_vats(self) -> None:
        # K (Intra-community) also needs BT-72 + BT-80 (BR-IC-11/12);
        # supply both so we exercise BR-IC-2 cleanly.
        doc = make_vat_doc(line_category=CategoryCode.T_K)
        doc.trade.delivery.event = SupplyChainEvent(occurrence=date(2025, 1, 15))
        doc.trade.delivery.ship_to = ShipToTradeParty(
            address=PostalTradeAddressExtended(country_id="FR")
        )
        doc.validate()

    def test_br_ic_2_line_fails_without_buyer_vat(self) -> None:
        # Buyer has no VAT and no legal id; per BR-IC-2 the legal id
        # alone wouldn't help — IC requires a Buyer VAT identifier.
        doc = make_vat_doc(
            line_category=CategoryCode.T_K, buyer_va=None, buyer_legal_id="HRB12345"
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-IC-2" for v in e.value.errors)

    def test_br_ic_2_line_fails_when_seller_only_has_local_id(self) -> None:
        # IC requires Seller VAT (or tax-rep VAT) — BT-32 (FC) doesn't
        # count, unlike BR-E/AE.
        doc = make_vat_doc(
            line_category=CategoryCode.T_K,
            seller_id="S-001",
            seller_va=None,
            seller_fc="123/456/789",
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-IC-2" for v in e.value.errors)

    def test_br_ic_3_doc_level_allowance_with_k(self) -> None:
        doc = make_vat_doc(
            line_category=CategoryCode.T_S,
            allowance_category=CategoryCode.T_K,
            buyer_va=None,
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-IC-3" for v in e.value.errors)

    def test_br_ic_4_doc_level_charge_with_k(self) -> None:
        doc = make_vat_doc(
            line_category=CategoryCode.T_S,
            charge_category=CategoryCode.T_K,
            buyer_va=None,
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-IC-4" for v in e.value.errors)


class TestBrSellerVatLocalTaxRep:
    """BR-S, BR-Z, BR-IG, BR-IP — all four families share one
    predicate: Seller has VAT, BT-32, *or* tax-rep VAT."""

    @pt.mark.parametrize(
        ("category", "code"),
        [
            (CategoryCode.T_S, "BR-S-2"),
            (CategoryCode.T_Z, "BR-Z-2"),
            (CategoryCode.T_L, "BR-IG-2"),
            (CategoryCode.T_M, "BR-IP-2"),
        ],
    )
    def test_line_requires_seller_tax_id(
        self, category: CategoryCode, code: str
    ) -> None:
        doc = make_vat_doc(
            line_category=category,
            seller_id="S-001",  # satisfies BR-CO-26
            seller_va=None,
            seller_fc=None,
            buyer_va=None,
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == code for v in e.value.errors)

    @pt.mark.parametrize(
        ("category", "code"),
        [
            (CategoryCode.T_S, "BR-S-3"),
            (CategoryCode.T_Z, "BR-Z-3"),
            (CategoryCode.T_L, "BR-IG-3"),
            (CategoryCode.T_M, "BR-IP-3"),
        ],
    )
    def test_doc_level_allowance_requires_seller_tax_id(
        self, category: CategoryCode, code: str
    ) -> None:
        doc = make_vat_doc(
            # T_O ("Not subject to VAT") is handled separately and lets
            # the allowance rule below fire first.
            line_category=CategoryCode.T_O,
            allowance_category=category,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == code for v in e.value.errors)

    @pt.mark.parametrize(
        ("category", "code"),
        [
            (CategoryCode.T_S, "BR-S-4"),
            (CategoryCode.T_Z, "BR-Z-4"),
            (CategoryCode.T_L, "BR-IG-4"),
            (CategoryCode.T_M, "BR-IP-4"),
        ],
    )
    def test_doc_level_charge_requires_seller_tax_id(
        self, category: CategoryCode, code: str
    ) -> None:
        doc = make_vat_doc(
            line_category=CategoryCode.T_O,
            charge_category=category,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == code for v in e.value.errors)
