"""MINIMUM-profile invoice factory (header totals only)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from getafix.build._shared import (
    ZERO,
    Numeric,
    category_tax_amount,
    header,
    optional_decimal,
    to_decimal,
)
from getafix.build._shared import buyer_party as _buyer_party
from getafix.build._shared import seller_party as _seller_party
from getafix.schema.accounting import MonetarySummation, TaxTotal
from getafix.schema.agreement import TradeAgreement
from getafix.schema.delivery import TradeDelivery
from getafix.schema.document import Context, Document, GuidelineDocument
from getafix.schema.party import BuyerTradeParty, SellerTradeParty
from getafix.schema.settlement import TradeSettlement
from getafix.schema.trade import Trade
from getafix.schema.types import Country, Currency, Profile, TypeCode


def seller_party(
    name: str, *, country: Country, vat_id: str | None = None, tax_id: str | None = None
) -> SellerTradeParty:
    """Build a MINIMUM Seller (BG-4) — name, country and tax ids only.

    MINIMUM carries no address detail: only the country code (BT-40) is
    rendered, so this builder exposes no postcode / city / street-line
    parameters (they are gated at BASIC_WL+ and would fail validation
    here). Use :func:`getafix.build.basic.seller_party` (or the
    ``basic_wl`` twin) when you need them. Delegates to the shared
    full-field builder.
    """
    return _seller_party(name, country=country, vat_id=vat_id, tax_id=tax_id)


def buyer_party(
    name: str, *, country: Country, vat_id: str | None = None
) -> BuyerTradeParty:
    """Build a MINIMUM Buyer (BG-7) — name, country and VAT id only.

    As with :func:`seller_party`, MINIMUM permits no address detail.
    Delegates to the shared full-field builder.
    """
    return _buyer_party(name, country=country, vat_id=vat_id)


def minimum_invoice(
    invoice_number: str,
    issue_date: date,
    *,
    seller: SellerTradeParty,
    buyer: BuyerTradeParty,
    tax_basis_total: Numeric,
    tax_amount: Numeric | None = None,
    vat_rate: Numeric | None = None,
    currency: Currency = Currency.EUR,
    type_code: TypeCode = TypeCode.T_CommercialInvoice,
    buyer_reference: str | None = None,
) -> Document:
    """Build a complete MINIMUM-profile document (header totals only).

    MINIMUM carries no line items and no VAT breakdown — only the
    headline totals. Give it the total without VAT (BT-109) and either
    the VAT amount (BT-110) directly via ``tax_amount`` or a single
    ``vat_rate`` to compute it from; the totals with VAT (BT-112) and
    due (BT-115) follow per ``BR-CO-15`` / ``BR-CO-16``. With neither
    ``tax_amount`` nor ``vat_rate`` the document carries no VAT total
    and the grand total equals the basis.

    Note: build the parties with this module's :func:`seller_party` /
    :func:`buyer_party`, which expose only the MINIMUM-valid fields
    (the country code, BT-40, plus tax ids). Some receivers only admit
    type code 751 ("invoice information for accounting purposes") at
    MINIMUM; override ``type_code`` when required.
    """
    basis = to_decimal(tax_basis_total, name="tax_basis_total")
    if tax_amount is not None and vat_rate is not None:
        raise ValueError("pass either tax_amount or vat_rate, not both.")
    tax: Decimal | None = optional_decimal(tax_amount, name="tax_amount")
    if tax is None and vat_rate is not None:
        tax = category_tax_amount(basis, to_decimal(vat_rate, name="vat_rate"))
    grand_total = basis + (tax or ZERO)

    return Document(
        context=Context(guideline=GuidelineDocument(id=Profile.MINIMUM)),
        header=header(invoice_number, issue_date, type_code, ()),
        trade=Trade(
            agreement=TradeAgreement(
                buyer_reference=buyer_reference, seller=seller, buyer=buyer
            ),
            delivery=TradeDelivery(),
            settlement=TradeSettlement(
                currency_code=currency,
                monetary_summation=MonetarySummation(
                    tax_basis_total=basis,
                    tax_total=(
                        [TaxTotal(amount=tax, currency_id=currency)]
                        if tax is not None
                        else None
                    ),
                    grand_total=grand_total,
                    due_amount=grand_total,
                ),
            ),
        ),
    )
