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
    if allowance_category is not None:
        allowance_charges.append(
            TradeAllowanceCharge(
                indicator=False,
                actual_amount=Decimal("5.00"),
                category_trade_tax=CategoryTradeTax(
                    category_code=allowance_category,
                    rate_applicable_percent=Decimal("0"),
                ),
                reason="discount",
            )
        )
    if charge_category is not None:
        allowance_charges.append(
            TradeAllowanceCharge(
                indicator=True,
                actual_amount=Decimal("3.00"),
                category_trade_tax=CategoryTradeTax(
                    category_code=charge_category,
                    rate_applicable_percent=Decimal("0"),
                ),
                reason="surcharge",
            )
        )
    return Document(
        context=Context(guideline=GuidelineDocument(id=Profile.BASIC)),
        header=Header(
            id="1",
            type_code=TypeCode.T_Handelsrechnung,
            issue_date=date(2025, 1, 1),
        ),
        trade=Trade(
            agreement=TradeAgreement(seller=seller, buyer=buyer),
            delivery=TradeDelivery(),
            settlement=TradeSettlement(
                currency_code="EUR",
                monetary_summation=MonetarySummation(
                    line_total=Decimal("100"),
                    tax_basis_total=Decimal("100"),
                    tax_total=[TaxTotal(amount=Decimal("0"), currency_id="EUR")],
                    grand_total=Decimal("100"),
                    due_amount=Decimal("100"),
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
                        net_price=NetTradePrice(charge_amount=Decimal("100")),
                    ),
                    delivery=LineTradeDelivery(
                        billed_quantity=Quantity(
                            value=Decimal("1"), unit_code="C62"
                        ),
                    ),
                    settlement=LineTradeSettlement(
                        applicable_trade_tax=ApplicableTradeTax(
                            category_code=line_category,
                            due_date_code="5",
                            rate_applicable_percent=Decimal("0"),
                        ),
                        monetary_summation=LineMonetarySummation(
                            line_total=Decimal("100"),
                        ),
                    ),
                ),
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
            line_category=CategoryCode.T_AE,
            buyer_va=None,
            buyer_legal_id="HRB12345",
        ).validate()

    def test_br_ae_2_requires_seller_vat_or_local_or_taxrep(self) -> None:
        # Drop every seller identifier — even with a buyer VAT, the line
        # needs the seller side identified per BR-AE-2.
        doc = _make_doc(
            line_category=CategoryCode.T_AE, seller_va=None, seller_fc=None
        )
        # BR-CO-26 fires first (seller must be identifiable at all).
        with pt.raises(ValidationError) as e:
            doc.validate()
        assert e.value.code == "BR-CO-26"
