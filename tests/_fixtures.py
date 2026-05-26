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
    HeaderTradeAllowanceCharge,
    MonetarySummation,
    TaxTotal,
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
from carthorse.schema.types import (
    CategoryCode,
    Country,
    Currency,
    UNTDID2475TaxPointDateCode,
)

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
        address=PostalTradeAddressExtended(country_id=Country.DE),
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
        address=PostalTradeAddressExtended(country_id=Country.DE),
        tax_registrations=buyer_regs,
        legal_organization=(
            LegalOrganization(id=ISO6523SchemeId(id=buyer_legal_id, scheme_id="0021"))
            if buyer_legal_id is not None
            else None
        ),
    )
    # Pick a category-appropriate rate per BR-{cat}-5/-6/-7. Callers
    # can still override per-instance after construction if the test
    # exercises rate-violation paths.
    _DEFAULT_RATE: dict[CategoryCode, Decimal | None] = {
        CategoryCode.T_S: Decimal("19"),
        CategoryCode.T_O: None,
    }
    line_rate = _DEFAULT_RATE.get(line_category, Decimal("0"))
    allowance_rate = (
        _DEFAULT_RATE.get(allowance_category, Decimal("0"))
        if allowance_category is not None
        else Decimal("0")
    )
    charge_rate = (
        _DEFAULT_RATE.get(charge_category, Decimal("0"))
        if charge_category is not None
        else Decimal("0")
    )

    allowance_charges: list[HeaderTradeAllowanceCharge] = []
    allowance_amount = Decimal("0")
    charge_amount = Decimal("0")
    if allowance_category is not None:
        allowance_amount = Decimal("5.00")
        allowance_charges.append(
            HeaderTradeAllowanceCharge(
                indicator=False,
                actual_amount=allowance_amount,
                category_trade_tax=CategoryTradeTax(
                    category_code=allowance_category,
                    rate_applicable_percent=allowance_rate,
                ),
                reason="discount",
            )
        )
    if charge_category is not None:
        charge_amount = Decimal("3.00")
        allowance_charges.append(
            HeaderTradeAllowanceCharge(
                indicator=True,
                actual_amount=charge_amount,
                category_trade_tax=CategoryTradeTax(
                    category_code=charge_category, rate_applicable_percent=charge_rate
                ),
                reason="surcharge",
            )
        )

    # Keep the header totals self-consistent under BR-CO-10..16. For
    # categories other than ``S`` the rate is zero, so the VAT total
    # stays at zero. ``S`` (rate 19%) and any allowance/charge whose
    # category differs from the line's go through a small VAT walk to
    # produce the correct BG-23 row(s) and the matching ``TaxTotal``.
    line_total = Decimal("100")
    tax_basis = line_total - allowance_amount + charge_amount
    # Per-category basis: lines minus allowances plus charges for the
    # same category.
    per_cat_basis: dict[CategoryCode, Decimal] = {line_category: line_total}
    if allowance_category is not None:
        per_cat_basis[allowance_category] = (
            per_cat_basis.get(allowance_category, Decimal("0")) - allowance_amount
        )
    if charge_category is not None:
        per_cat_basis[charge_category] = (
            per_cat_basis.get(charge_category, Decimal("0")) + charge_amount
        )
    per_cat_rate: dict[CategoryCode, Decimal | None] = {line_category: line_rate}
    if allowance_category is not None and allowance_category not in per_cat_rate:
        per_cat_rate[allowance_category] = allowance_rate
    if charge_category is not None and charge_category not in per_cat_rate:
        per_cat_rate[charge_category] = charge_rate
    # Categories that require an exemption reason per BR-{cat}-10 —
    # default reason text so the fixture is spec-valid out of the box.
    _REQUIRES_EXEMPTION: frozenset[CategoryCode] = frozenset(
        {
            CategoryCode.T_E,
            CategoryCode.T_AE,
            CategoryCode.T_G,
            CategoryCode.T_K,
            CategoryCode.T_O,
        }
    )
    _EXEMPTION_TEXT: dict[CategoryCode, str] = {
        CategoryCode.T_E: "Exempt from VAT",
        CategoryCode.T_AE: "Reverse charge",
        CategoryCode.T_G: "Export outside the EU",
        CategoryCode.T_K: "Intra-community supply",
        CategoryCode.T_O: "Not subject to VAT",
    }
    trade_taxes: list[ApplicableTradeTax] = []
    total_vat = Decimal("0")
    for cat, basis in per_cat_basis.items():
        rate = per_cat_rate.get(cat)
        calculated = (
            (basis * rate / Decimal("100")).quantize(Decimal("0.01"))
            if rate is not None
            else Decimal("0")
        )
        total_vat += calculated
        exemption_text = (
            _EXEMPTION_TEXT.get(cat) if cat in _REQUIRES_EXEMPTION else None
        )
        trade_taxes.append(
            ApplicableTradeTax(
                calculated_amount=calculated,
                basis_amount=basis,
                category_code=cat,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=rate,
                exemption_reason=exemption_text,
            )
        )
    grand_total = tax_basis + total_vat
    return Document(
        context=Context(guideline=GuidelineDocument(id=Profile.BASIC)),
        header=Header(
            id="1", type_code=TypeCode.T_CommercialInvoice, issue_date=date(2025, 1, 1)
        ),
        trade=Trade(
            agreement=TradeAgreement(seller=seller, buyer=buyer),
            delivery=TradeDelivery(),
            settlement=TradeSettlement(
                currency_code=Currency.EUR,
                monetary_summation=MonetarySummation(
                    line_total=line_total,
                    allowance_total=allowance_amount or None,
                    charge_total=charge_amount or None,
                    tax_basis_total=tax_basis,
                    tax_total=[TaxTotal(amount=total_vat, currency_id=Currency.EUR)],
                    grand_total=grand_total,
                    due_amount=grand_total,
                ),
                trade_taxes=trade_taxes,
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
                            due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                            rate_applicable_percent=line_rate,
                        ),
                        monetary_summation=LineMonetarySummation(
                            line_total=Decimal("100")
                        ),
                    ),
                )
            ],
        ),
    )
