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
from getafix.schema import Context, Document, GuidelineDocument, Profile, TypeCode
from getafix.schema.accounting import MonetarySummation, TaxTotal
from getafix.schema.agreement import TradeAgreement
from getafix.schema.delivery import TradeDelivery
from getafix.schema.party import BuyerTradeParty, SellerTradeParty
from getafix.schema.settlement import TradeSettlement
from getafix.schema.trade import Trade
from getafix.schema.types import Currency


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

    Note: build the parties without address details (MINIMUM renders
    only the country code) — see
    :func:`~getafix.build.seller_party`. Some receivers only admit type
    code 751 ("invoice information for accounting purposes") at MINIMUM;
    override ``type_code`` when required.
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
        header=header(Profile.MINIMUM, invoice_number, issue_date, type_code, ()),
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
                    currency=str(currency),
                ),
            ),
        ),
    )
