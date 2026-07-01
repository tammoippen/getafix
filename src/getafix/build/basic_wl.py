"""BASIC_WL-profile invoice factory (VAT breakdown, no line items)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date

from getafix.build._shared import (
    DEFAULT_EXEMPTION_CODE,
    ZERO,
    Numeric,
    category_tax_amount,
    header,
    monetary_summation,
    payment_terms,
    trade_delivery,
)
from getafix.build._shared import buyer_party as buyer_party
from getafix.build._shared import seller_party as seller_party
from getafix.schema.accounting import ApplicableTradeTax, HeaderTradeAllowanceCharge
from getafix.schema.agreement import TradeAgreement
from getafix.schema.document import Context, Document, GuidelineDocument
from getafix.schema.party import BuyerTradeParty, SellerTradeParty
from getafix.schema.settlement import PaymentMeans, PaymentTerms, TradeSettlement
from getafix.schema.trade import Trade
from getafix.schema.types import Currency, Profile, TypeCode


def _complete_trade_taxes(
    trade_taxes: Sequence[ApplicableTradeTax],
) -> list[ApplicableTradeTax]:
    """Fill the derivable fields on caller-supplied BG-23 rows.

    Each row needs at least the taxable amount (BT-116) and the
    category (BT-118); the tax amount (BT-117, per ``BR-CO-17``) and the
    canonical exemption-reason code (BT-121, where one exists) are
    filled in when absent. Returns copies — the caller's rows are not
    mutated.
    """
    completed: list[ApplicableTradeTax] = []
    for tt in trade_taxes:
        if tt.basis_amount is None:
            raise ValueError(
                "VAT breakdown row (BG-23) needs basis_amount (BT-116) set."
            )
        calculated = tt.calculated_amount
        if calculated is None:
            calculated = category_tax_amount(
                tt.basis_amount, tt.rate_applicable_percent
            )
        code = tt.exemption_reason_code
        if code is None and tt.exemption_reason is None:
            code = DEFAULT_EXEMPTION_CODE.get(tt.category_code)
        completed.append(
            replace(tt, calculated_amount=calculated, exemption_reason_code=code)
        )
    return completed


def basic_wl_invoice(
    invoice_number: str,
    issue_date: date,
    *,
    seller: SellerTradeParty,
    buyer: BuyerTradeParty,
    trade_taxes: Sequence[ApplicableTradeTax],
    allowance_charges: Sequence[HeaderTradeAllowanceCharge] = (),
    currency: Currency = Currency.EUR,
    type_code: TypeCode = TypeCode.T_CommercialInvoice,
    due_date: date | None = None,
    terms: PaymentTerms | None = None,
    payment_means: Sequence[PaymentMeans] = (),
    delivery_date: date | None = None,
    notes: Sequence[str] = (),
    prepaid_total: Numeric | None = None,
    buyer_reference: str | None = None,
) -> Document:
    """Build a complete BASIC_WL-profile document (no line items).

    BASIC_WL has no lines but does require the VAT breakdown (BG-23,
    ``BR-CO-18``) — supply one ``ApplicableTradeTax`` row per VAT
    category / rate with at least ``basis_amount`` (BT-116) and
    ``category_code`` (BT-118) set. Everything derivable is computed:
    the per-row tax amount (BT-117) when absent, the canonical VATEX
    exemption code for ``AE`` / ``G`` / ``K`` / ``O`` rows, the line
    total (BT-106, from the bases and the allowances / charges per the
    inverse of ``BR-CO-13``) and the BG-22 totals.

    ``due_date`` is shorthand for ``terms=PaymentTerms(due=…)`` — one
    of the two (or a payment-terms text) is required by ``BR-CO-25``
    whenever the amount due is positive.
    """
    completed = _complete_trade_taxes(trade_taxes)
    charges = list(allowance_charges) or None
    allowance_total = sum(
        (ac.actual_amount for ac in allowance_charges if not ac.indicator), ZERO
    )
    charge_total = sum(
        (ac.actual_amount for ac in allowance_charges if ac.indicator), ZERO
    )
    basis_sum = sum((tt.basis_amount or ZERO for tt in completed), ZERO)
    line_total = basis_sum + allowance_total - charge_total

    return Document(
        context=Context(guideline=GuidelineDocument(id=Profile.BASIC_WL)),
        header=header(invoice_number, issue_date, type_code, notes),
        trade=Trade(
            agreement=TradeAgreement(
                buyer_reference=buyer_reference, seller=seller, buyer=buyer
            ),
            delivery=trade_delivery(delivery_date),
            settlement=TradeSettlement(
                currency_code=currency,
                payment_means=list(payment_means) or None,
                trade_taxes=completed,
                allowance_charge=charges,
                terms=payment_terms(terms, due_date),
                monetary_summation=monetary_summation(
                    currency=currency,
                    line_total=line_total,
                    trade_taxes=completed,
                    allowance_charges=allowance_charges,
                    prepaid_total=prepaid_total,
                ),
            ),
        ),
    )
