"""Shared helpers and fixtures used across the per-topic test files.

Two things live here:

* :data:`NS_DECL` / :func:`wrap_subtree` — inject the ``ram``/``udt``
  namespace bindings on a rendered sub-tree so it can be parsed
  standalone. Used by the XML-tag and round-trip regression tests.
* :func:`make_vat_doc` — build a single-line BASIC invoice with knobs
  for every party identifier / VAT-category combination the BR-AE /
  BR-E / BR-IC / BR-O / BR-S / BR-Z / BR-IG / BR-IP rules care about.
  Used by the per-category VAT tests.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

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
    ISO6523SchemeId,
    LegalOrganization,
    PostalTradeAddressExtended,
    SellerTradeParty,
    SpecifiedTaxRegistration,
    TaxSchemeId,
)
from carthorse.schema.settlement import PaymentTerms, TradeSettlement
from carthorse.schema.trade import Trade, TradeLineItem
from carthorse.schema.types import CategoryCode

NS_DECL = (
    'xmlns:ram="urn:un:unece:uncefact:data:standard:'
    'ReusableAggregateBusinessInformationEntity:100" '
    'xmlns:udt="urn:un:unece:uncefact:data:standard:'
    'UnqualifiedDataType:100"'
)


def wrap_subtree(rendered: str, root_tag: str) -> bytes:
    """Inject the ram/udt namespace bindings on the root element so a
    sub-tree rendered via ``Element.to_xml_internal`` parses standalone."""
    return rendered.replace(
        f"<ram:{root_tag}>", f"<ram:{root_tag} {NS_DECL}>", 1
    ).encode()


def make_vat_doc(
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
            LegalOrganization(id=ISO6523SchemeId(id=buyer_legal_id, scheme_id="0021"))
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
