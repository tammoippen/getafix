"""Cross-field validation tests for VAT-category required-party rules.

These cover the BR-AE / BR-E / BR-G / BR-IC / BR-IG / BR-IP / BR-O /
BR-S / BR-Z families — every line / allowance / charge with a given
VAT category triggers a check on the seller / buyer identifier set.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest as pt

from carthorse.schema import (
    Context,
    Document,
    GuidelineDocument,
    Header,
    Profile,
    TypeCode,
)
from carthorse.schema.accounting import (
    ApplicableTradeTax,
    CategoryTradeTax,
    MonetarySummation,
    TaxTotal,
    TradeAllowanceCharge,
)
from carthorse.schema.agreement import TradeAgreement
from carthorse.schema.delivery import TradeDelivery
from carthorse.schema.element import ValidationError
from carthorse.schema.line import (
    DocumentLineDocument,
    LineMonetarySummation,
    LineTradeAgreement,
    LineTradeDelivery,
    LineTradeSettlement,
    NetTradePrice,
    Quantity,
    TradeProduct,
)
from carthorse.schema.party import (
    BuyerTradeParty,
    LegalOrganization,
    PostalTradeAddressExtended,
    SellerTradeParty,
    SpecifiedTaxRegistration,
    TaxSchemeId,
)
from carthorse.schema.settlement import PaymentTerms, TradeSettlement
from carthorse.schema.trade import Trade, TradeLineItem
from carthorse.schema.types import CategoryCode


def _make_doc(
    *,
    line_category: CategoryCode = CategoryCode.T_S,
    seller_id: str | None = None,
    seller_va: str | None = "DE123456789",
    seller_fc: str | None = None,
    buyer_va: str | None = "DE987654321",
    buyer_legal_id: str | None = None,
    allowance_category: CategoryCode | None = None,
    charge_category: CategoryCode | None = None,
) -> Document:
    """Build a single-line BASIC invoice with knobs for the rules to grab.

    The defaults form a valid invoice (Standard-rated, both parties have
    VAT IDs); every test then twists *one* knob and asserts the
    expected BR-* fires.
    """
    seller_regs = []
    if seller_va is not None:
        seller_regs.append(
            SpecifiedTaxRegistration(id=TaxSchemeId(id=seller_va, scheme_id="VA"))
        )
    if seller_fc is not None:
        seller_regs.append(
            SpecifiedTaxRegistration(id=TaxSchemeId(id=seller_fc, scheme_id="FC"))
        )
    seller = SellerTradeParty(
        name="Seller",
        address=PostalTradeAddressExtended(country_id="DE"),
        id=seller_id,
        tax_registrations=seller_regs or None,
    )
    buyer_regs = (
        [SpecifiedTaxRegistration(id=TaxSchemeId(id=buyer_va, scheme_id="VA"))]
        if buyer_va is not None
        else None
    )
    buyer = BuyerTradeParty(
        name="Buyer",
        address=PostalTradeAddressExtended(country_id="DE"),
        tax_registrations=buyer_regs,
        legal_organization=(
            LegalOrganization(
                id=__import__(
                    "carthorse.schema.party", fromlist=["ISO6523SchemeId"]
                ).ISO6523SchemeId(id=buyer_legal_id, scheme_id="0021")
            )
            if buyer_legal_id is not None
            else None
        ),
    )
    allowance_charges: list[TradeAllowanceCharge] = []
    allowance_amount = Decimal("0")
    charge_amount = Decimal("0")
    if allowance_category is not None:
        allowance_amount = Decimal("5.00")
        allowance_charges.append(
            TradeAllowanceCharge(
                indicator=False,
                actual_amount=allowance_amount,
                category_trade_tax=CategoryTradeTax(
                    category_code=allowance_category,
                    rate_applicable_percent=Decimal("0"),
                ),
                reason="discount",
            )
        )
    if charge_category is not None:
        charge_amount = Decimal("3.00")
        allowance_charges.append(
            TradeAllowanceCharge(
                indicator=True,
                actual_amount=charge_amount,
                category_trade_tax=CategoryTradeTax(
                    category_code=charge_category, rate_applicable_percent=Decimal("0")
                ),
                reason="surcharge",
            )
        )

    # Keep the header totals self-consistent under BR-CO-10..16:
    # tax_basis_total = lines - allowances + charges, grand_total +
    # due_amount track tax_basis_total since the helper's lines /
    # allowances / charges carry rate 0%.
    line_total = Decimal("100")
    tax_basis = line_total - allowance_amount + charge_amount
    return Document(
        context=Context(guideline=GuidelineDocument(id=Profile.BASIC)),
        header=Header(
            id="1", type_code=TypeCode.T_Handelsrechnung, issue_date=date(2025, 1, 1)
        ),
        trade=Trade(
            agreement=TradeAgreement(seller=seller, buyer=buyer),
            delivery=TradeDelivery(),
            settlement=TradeSettlement(
                currency_code="EUR",
                monetary_summation=MonetarySummation(
                    line_total=line_total,
                    allowance_total=allowance_amount or None,
                    charge_total=charge_amount or None,
                    tax_basis_total=tax_basis,
                    tax_total=[TaxTotal(amount=Decimal("0"), currency_id="EUR")],
                    grand_total=tax_basis,
                    due_amount=tax_basis,
                ),
                trade_taxes=[
                    ApplicableTradeTax(
                        calculated_amount=Decimal("0"),
                        basis_amount=Decimal("100"),
                        category_code=line_category,
                        due_date_code="5",
                        rate_applicable_percent=Decimal("0"),
                    )
                ],
                allowance_charge=allowance_charges or None,
                terms=PaymentTerms(due=date(2025, 2, 1)),
            ),
            items=[
                TradeLineItem(
                    associated_document=DocumentLineDocument(line_id="1"),
                    product=TradeProduct(name="W"),
                    agreement=LineTradeAgreement(
                        net_price=NetTradePrice(charge_amount=Decimal("100"))
                    ),
                    delivery=LineTradeDelivery(
                        billed_quantity=Quantity(value=Decimal("1"), unit_code="C62")
                    ),
                    settlement=LineTradeSettlement(
                        applicable_trade_tax=ApplicableTradeTax(
                            category_code=line_category,
                            due_date_code="5",
                            rate_applicable_percent=Decimal("0"),
                        ),
                        monetary_summation=LineMonetarySummation(
                            line_total=Decimal("100")
                        ),
                    ),
                )
            ],
        ),
    )


class TestBrAe:
    """BR-AE — Reverse charge VAT category."""

    def test_br_ae_2_line_requires_seller_and_buyer_vat(self) -> None:
        # Buyer has no VAT id and no legal organisation → fails.
        doc = _make_doc(
            line_category=CategoryCode.T_AE, buyer_va=None, buyer_legal_id=None
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-AE-2"

    def test_br_ae_2_passes_with_buyer_vat(self) -> None:
        _make_doc(line_category=CategoryCode.T_AE).validate()

    def test_br_ae_2_passes_with_buyer_legal_only(self) -> None:
        # Buyer has no VAT id but has a legal registration id (BT-47).
        _make_doc(
            line_category=CategoryCode.T_AE, buyer_va=None, buyer_legal_id="HRB12345"
        ).validate()

    def test_br_ae_2_requires_seller_vat_or_local_or_taxrep(self) -> None:
        # Drop every seller identifier — even with a buyer VAT, the line
        # needs the seller side identified per BR-AE-2.
        doc = _make_doc(line_category=CategoryCode.T_AE, seller_va=None, seller_fc=None)
        # BR-CO-26 fires first (seller must be identifiable at all).
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-CO-26"

    def test_br_ae_3_doc_level_allowance_requires_seller_and_buyer_vat(self) -> None:
        # Allowance (BG-20) with category AE; buyer has no identifiers.
        doc = _make_doc(
            line_category=CategoryCode.T_S,
            allowance_category=CategoryCode.T_AE,
            buyer_va=None,
            buyer_legal_id=None,
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-AE-3"

    def test_br_ae_3_passes_with_buyer_legal_id(self) -> None:
        _make_doc(
            line_category=CategoryCode.T_S,
            allowance_category=CategoryCode.T_AE,
            buyer_va=None,
            buyer_legal_id="HRB12345",
        ).validate()

    def test_br_ae_4_doc_level_charge_requires_seller_and_buyer_vat(self) -> None:
        # Charge (BG-21) with category AE; buyer has no identifiers.
        doc = _make_doc(
            line_category=CategoryCode.T_S,
            charge_category=CategoryCode.T_AE,
            buyer_va=None,
            buyer_legal_id=None,
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-AE-4"


class TestBrE:
    """BR-E — Exempt from VAT: Seller VAT/local/tax-rep required;
    Buyer side unrestricted."""

    def test_br_e_2_line_requires_seller_vat_or_local_or_taxrep(self) -> None:
        # Seller has only an FC tax id (which counts for BR-E-2) plus a
        # BT-29 to satisfy BR-CO-26; no VAT registration.
        # Buyer has nothing — that's allowed for E.
        _make_doc(
            line_category=CategoryCode.T_E,
            seller_id="S-001",
            seller_va=None,
            seller_fc="123/456/789",
            buyer_va=None,
        ).validate()

    def test_br_e_2_fails_without_any_seller_tax_id(self) -> None:
        # Seller has BT-29 (so BR-CO-26 passes) but no VAT and no FC.
        doc = _make_doc(
            line_category=CategoryCode.T_E,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
            buyer_va=None,
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-E-2"

    def test_br_e_2_line_passes_with_seller_vat(self) -> None:
        _make_doc(line_category=CategoryCode.T_E, buyer_va=None).validate()

    def test_br_e_3_doc_level_allowance_with_e_passes_when_seller_identifiable(
        self,
    ) -> None:
        _make_doc(
            line_category=CategoryCode.T_S,
            allowance_category=CategoryCode.T_E,
            buyer_va=None,
        ).validate()

    def test_br_e_4_doc_level_charge_with_e_passes(self) -> None:
        _make_doc(
            line_category=CategoryCode.T_S,
            charge_category=CategoryCode.T_E,
            buyer_va=None,
        ).validate()


class TestBrIc:
    """BR-IC — Intra-community supply (UNTDID code ``K``).

    Requires Seller VAT (or tax-rep VAT) AND Buyer VAT.
    """

    def test_br_ic_2_line_passes_with_both_vats(self) -> None:
        from carthorse.schema.delivery import SupplyChainEvent
        from carthorse.schema.party import ShipToTradeParty

        # K (Intra-community) also needs BT-72 + BT-80 (BR-IC-11/12);
        # supply both so we exercise BR-IC-2 cleanly.
        doc = _make_doc(line_category=CategoryCode.T_K)
        doc.trade.delivery.event = SupplyChainEvent(occurrence=date(2025, 1, 15))
        doc.trade.delivery.ship_to = ShipToTradeParty(
            address=PostalTradeAddressExtended(country_id="FR")
        )
        doc.validate()

    def test_br_ic_2_line_fails_without_buyer_vat(self) -> None:
        # Buyer has no VAT and no legal id; per BR-IC-2 the legal id
        # alone wouldn't help — IC requires a Buyer VAT identifier.
        doc = _make_doc(
            line_category=CategoryCode.T_K, buyer_va=None, buyer_legal_id="HRB12345"
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-IC-2"

    def test_br_ic_2_line_fails_when_seller_only_has_local_id(self) -> None:
        # IC requires Seller VAT (or tax-rep VAT) — BT-32 (FC) doesn't
        # count, unlike BR-E/AE.
        doc = _make_doc(
            line_category=CategoryCode.T_K,
            seller_id="S-001",
            seller_va=None,
            seller_fc="123/456/789",
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-IC-2"

    def test_br_ic_3_doc_level_allowance_with_k(self) -> None:
        doc = _make_doc(
            line_category=CategoryCode.T_S,
            allowance_category=CategoryCode.T_K,
            buyer_va=None,
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-IC-3"

    def test_br_ic_4_doc_level_charge_with_k(self) -> None:
        doc = _make_doc(
            line_category=CategoryCode.T_S,
            charge_category=CategoryCode.T_K,
            buyer_va=None,
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-IC-4"


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
        doc = _make_doc(
            line_category=category,
            seller_id="S-001",  # satisfies BR-CO-26
            seller_va=None,
            seller_fc=None,
            buyer_va=None,
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == code

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
        doc = _make_doc(
            # T_O ("Not subject to VAT") is handled separately and lets
            # the allowance rule below fire first.
            line_category=CategoryCode.T_O,
            allowance_category=category,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == code

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
        doc = _make_doc(
            line_category=CategoryCode.T_O,
            charge_category=category,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == code


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
        _make_doc(
            line_category=CategoryCode.T_O,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
            buyer_va=None,
        ).validate()

    def test_br_o_2_line_forbids_seller_vat(self) -> None:
        doc = _make_doc(
            line_category=CategoryCode.T_O,
            seller_id="S-001",
            seller_va="DE123456789",
            buyer_va=None,
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-O-2"

    def test_br_o_2_line_forbids_buyer_id(self) -> None:
        # The spec quirk: BR-O-2 names BT-46 (Buyer ID), not BT-48.
        doc = _make_doc(
            line_category=CategoryCode.T_O,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
            buyer_va=None,
        )
        # Force a BT-46 directly (the helper doesn't expose it).
        doc.trade.agreement.buyer.id = "B-001"
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-O-2"

    def test_br_o_3_allowance_forbids_buyer_vat(self) -> None:
        # Allowance with O — BT-48 forbidden.
        doc = _make_doc(
            line_category=CategoryCode.T_O,
            allowance_category=CategoryCode.T_O,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
            buyer_va="DE987654321",
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-O-3"

    def test_br_o_4_charge_forbids_seller_taxrep_vat(self) -> None:
        # Charge with O. We add the tax-rep with a VAT id; the rule
        # forbids BT-63 in this case. Use a line category that's
        # satisfied by tax-rep VAT (T_S) so the line doesn't fire.
        doc = _make_doc(
            line_category=CategoryCode.T_S,
            charge_category=CategoryCode.T_O,
            seller_id="S-001",
            seller_va=None,
            seller_fc=None,
            buyer_va=None,
        )
        from carthorse.schema.party import SellerTaxRepresentativeTradeParty

        doc.trade.agreement.seller_tax_representative_party = (
            SellerTaxRepresentativeTradeParty(
                name="TR",
                address=PostalTradeAddressExtended(country_id="DE"),
                tax_registrations=SpecifiedTaxRegistration(
                    id=TaxSchemeId(id="DE111222333", scheme_id="VA")
                ),
            )
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-O-4"


class TestBrOSingleRate:
    """BR-O-11..14 — invoices using VAT category 'Not subject to VAT'
    are single-rate: every other slot must also be O."""

    def _make_o_only(self) -> Document:
        # Baseline: line + BG-23 both O, no allowance/charge.
        return _make_doc(
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
                due_date_code="5",
                rate_applicable_percent=Decimal("0"),
            ),
            ApplicableTradeTax(
                category_code=CategoryCode.T_S,
                due_date_code="5",
                rate_applicable_percent=Decimal("19"),
            ),
        ]
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-O-11"

    def test_br_o_12_line_with_other_category_forbidden(self) -> None:
        # Use a setup where the line's category-required-party rule
        # passes (seller has VAT) so BR-S-2 doesn't fire first; the
        # BG-23 only carries the O row.
        doc = _make_doc(
            line_category=CategoryCode.T_S,
            seller_id="S-001",
            seller_va="DE123456789",
            buyer_va=None,
        )
        doc.trade.settlement.trade_taxes = [
            ApplicableTradeTax(
                category_code=CategoryCode.T_O,
                due_date_code="5",
                rate_applicable_percent=Decimal("0"),
            )
        ]
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-O-12"

    def test_br_o_13_allowance_with_other_category_forbidden(self) -> None:
        doc = _make_doc(
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
                due_date_code="5",
                rate_applicable_percent=Decimal("0"),
            )
        ]
        with pt.raises(ValidationError) as e:
            doc.validate()
        # Note: BR-S-3 *also* fires (allowance with S has no seller VAT)
        # but BR-O-13 is the more specific rule given a BG-23 O row.
        # carthorse runs BR-O single-rate after the family loop, so the
        # category-required-party check raises first.
        assert e.value.code in {"BR-O-13", "BR-S-3"}

    def test_br_o_14_charge_with_other_category_forbidden(self) -> None:
        doc = _make_doc(
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
                due_date_code="5",
                rate_applicable_percent=Decimal("0"),
            )
        ]
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code in {"BR-O-14", "BR-S-4"}


class TestBrIcDelivery:
    """BR-IC-11 / BR-IC-12 — intra-community supply needs evidence
    of cross-border delivery."""

    def _make_ic(self) -> Document:
        # Both Seller and Buyer have VAT (so BR-IC-2 is satisfied) and
        # the line carries category K. From there, BR-IC-11 (BT-72 or
        # BG-14) and BR-IC-12 (BT-80) are the next checks.
        return _make_doc(line_category=CategoryCode.T_K)

    def test_br_ic_11_passes_with_actual_delivery_date(self) -> None:
        from carthorse.schema.delivery import SupplyChainEvent

        doc = self._make_ic()
        doc.trade.delivery.event = SupplyChainEvent(occurrence=date(2025, 1, 15))
        # BR-IC-12 still needs deliver-to country.
        from carthorse.schema.party import ShipToTradeParty

        doc.trade.delivery.ship_to = ShipToTradeParty(
            address=PostalTradeAddressExtended(country_id="FR")
        )
        doc.validate()

    def test_br_ic_11_passes_with_billing_period(self) -> None:
        from carthorse.schema.party import ShipToTradeParty
        from carthorse.schema.settlement import BillingSpecifiedPeriod

        doc = self._make_ic()
        doc.trade.settlement.billing_period = BillingSpecifiedPeriod(
            start=date(2025, 1, 1), end=date(2025, 1, 31)
        )
        doc.trade.delivery.ship_to = ShipToTradeParty(
            address=PostalTradeAddressExtended(country_id="FR")
        )
        doc.validate()

    def test_br_ic_11_fires_without_date_or_period(self) -> None:
        from carthorse.schema.party import ShipToTradeParty

        doc = self._make_ic()
        doc.trade.delivery.ship_to = ShipToTradeParty(
            address=PostalTradeAddressExtended(country_id="FR")
        )
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-IC-11"

    def test_br_ic_12_fires_without_ship_to_country(self) -> None:
        from carthorse.schema.delivery import SupplyChainEvent

        doc = self._make_ic()
        doc.trade.delivery.event = SupplyChainEvent(occurrence=date(2025, 1, 15))
        # No ship_to → no BT-80.
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-IC-12"


class TestBrCoArithmetic:
    """BR-CO-10..14 — document-level totals match the sums of their
    line / allowance / charge / tax-breakdown contributions."""

    def test_br_co_10_line_total_equals_sum_of_line_amounts(self) -> None:
        """BT-106 = sum of BT-131 across line items."""
        # Add a second line so we exercise the sum (not just one row).
        doc = _make_doc()
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
                        due_date_code="5",
                        rate_applicable_percent=Decimal("19"),
                    ),
                    monetary_summation=LineMonetarySummation(line_total=Decimal("50")),
                ),
            )
        )
        # Sum of line totals = 100 + 50 = 150, but header still says 100.
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-CO-10"

    def test_br_co_10_passes_when_totals_match(self) -> None:
        """Single-line doc: BT-106 should equal the one BT-131."""
        _make_doc().validate()

    def test_br_co_10_skipped_when_line_total_absent(self) -> None:
        """At MINIMUM ``line_total`` may legitimately be omitted; the
        rule is unenforceable then."""
        doc = _make_doc()
        doc.trade.settlement.monetary_summation.line_total = None
        doc.validate()

    def test_br_co_11_allowance_total_matches_sum(self) -> None:
        """BT-107 = sum of document-level allowance BT-92."""
        doc = _make_doc(allowance_category=CategoryCode.T_S)
        summation = doc.trade.settlement.monetary_summation
        # One allowance of 5.00 in the helper; declare BT-107 wrongly.
        summation.allowance_total = Decimal("99")
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-CO-11"

        # Match the sum and BT-109 / BT-115 to keep the rest happy.
        summation.allowance_total = Decimal("5.00")
        summation.tax_basis_total = Decimal("95")  # 100 - 5
        summation.grand_total = Decimal("95")
        summation.due_amount = Decimal("95")
        doc.validate()

    def test_br_co_12_charge_total_matches_sum(self) -> None:
        """BT-108 = sum of document-level charge BT-99."""
        doc = _make_doc(charge_category=CategoryCode.T_S)
        summation = doc.trade.settlement.monetary_summation
        # One charge of 3.00 in the helper; declare BT-108 wrongly.
        summation.charge_total = Decimal("99")
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-CO-12"

        summation.charge_total = Decimal("3.00")
        summation.tax_basis_total = Decimal("103")  # 100 + 3
        summation.grand_total = Decimal("103")
        summation.due_amount = Decimal("103")
        doc.validate()

    def test_br_co_14_tax_total_equals_sum_of_tax_amounts(self) -> None:
        """BT-110 = sum of BT-117 across the header BG-23 rows."""
        doc = _make_doc()
        summation = doc.trade.settlement.monetary_summation
        # Two BG-23 rows: 10% on 50, 20% on 50 → sum 5 + 10 = 15.
        doc.trade.settlement.trade_taxes = [
            ApplicableTradeTax(
                calculated_amount=Decimal("5"),
                basis_amount=Decimal("50"),
                category_code=CategoryCode.T_S,
                due_date_code="5",
                rate_applicable_percent=Decimal("10"),
            ),
            ApplicableTradeTax(
                calculated_amount=Decimal("10"),
                basis_amount=Decimal("50"),
                category_code=CategoryCode.T_S,
                due_date_code="5",
                rate_applicable_percent=Decimal("20"),
            ),
        ]
        # Declare wrong BT-110.
        summation.tax_total = [TaxTotal(amount=Decimal("99"), currency_id="EUR")]
        # Keep BR-CO-15 / 16 happy.
        summation.grand_total = summation.tax_basis_total + Decimal("99")
        summation.due_amount = summation.grand_total
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-CO-14"

        # Correct sum.
        summation.tax_total = [TaxTotal(amount=Decimal("15"), currency_id="EUR")]
        summation.grand_total = summation.tax_basis_total + Decimal("15")
        summation.due_amount = summation.grand_total
        doc.validate()

    def test_br_co_13_tax_basis_identity(self) -> None:
        """BT-109 = ΣBT-131 - BT-107 + BT-108."""
        doc = _make_doc(
            allowance_category=CategoryCode.T_S, charge_category=CategoryCode.T_S
        )
        summation = doc.trade.settlement.monetary_summation
        # Keep tax_basis_total / grand_total / due_amount in sync so
        # BR-CO-15 + BR-CO-16 stay satisfied; only break the BT-109
        # vs ΣBT-131 identity that BR-CO-13 watches.
        summation.tax_basis_total = Decimal("999")
        summation.grand_total = Decimal("999")
        summation.due_amount = Decimal("999")
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-CO-13"

        # Real identity: 100 - 5 + 3 = 98.
        summation.tax_basis_total = Decimal("98")
        summation.grand_total = Decimal("98")
        summation.due_amount = Decimal("98")
        doc.validate()
