"""BASIC-profile invoice factory plus the line-item helpers.

BASIC is the first profile that carries invoice lines (BG-25). This
module owns :func:`line_item` (one line, with the line total derived),
:func:`vat_breakdown` (the BG-23 rows grouped from the lines) and
:func:`basic_invoice` (the whole document).

The high-level builders intentionally stop at BASIC: COMFORT
(EN 16931) and EXTENDED add far more optional structure than a
convenience constructor can usefully default, so build those by hand
against :mod:`getafix.schema`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal

from getafix.build._shared import (
    DEFAULT_EXEMPTION_CODE,
    ZERO,
    Numeric,
    category_tax_amount,
    header,
    monetary_summation,
    optional_decimal,
    payment_terms,
    to_decimal,
    trade_delivery,
)
from getafix.build._shared import buyer_party as buyer_party
from getafix.build._shared import seller_party as seller_party
from getafix.schema._numeric import round_half_away_from_zero
from getafix.schema.accounting import ApplicableTradeTax, HeaderTradeAllowanceCharge
from getafix.schema.agreement import TradeAgreement
from getafix.schema.document import Context, Document, GuidelineDocument
from getafix.schema.line import (
    AppliedTradeAllowanceCharge,
    BasisQuantity,
    DocumentLineDocument,
    GrossTradePrice,
    LineIncludedNote,
    LineMonetarySummation,
    LineTradeAgreement,
    LineTradeDelivery,
    LineTradeSettlement,
    NetTradePrice,
    Quantity,
    TradeProduct,
)
from getafix.schema.party import BuyerTradeParty, GlobalID, SellerTradeParty
from getafix.schema.settlement import PaymentMeans, PaymentTerms, TradeSettlement
from getafix.schema.trade import Trade, TradeLineItem
from getafix.schema.types import CategoryCode, Currency, Profile, TypeCode, VATEXCode

# Categories whose VAT rate (BT-119 / BT-152) must be 0 — defaulted so
# the caller need not spell out the only legal value.
_ZERO_RATE_CATEGORIES: frozenset[CategoryCode] = frozenset(
    {
        CategoryCode.T_Z,
        CategoryCode.T_E,
        CategoryCode.T_AE,
        CategoryCode.T_G,
        CategoryCode.T_K,
    }
)


def _vat_rate(category: CategoryCode, rate: Numeric | None) -> Decimal | None:
    """Resolve the VAT rate for *category*, defaulting where the spec
    leaves exactly one legal value.

    * ``Z`` / ``E`` / ``AE`` / ``G`` / ``K`` — rate must be 0; defaulted.
    * ``O`` — rate must be absent; a supplied rate raises.
    * ``S`` / ``L`` / ``M`` — the rate is jurisdiction-specific and
      must be supplied explicitly.
    """
    if category is CategoryCode.T_O:
        if rate is not None:
            raise ValueError(
                "VAT category 'O' (not subject to VAT) must not carry a rate."
            )
        return None
    if rate is not None:
        return to_decimal(rate, name="vat_rate")
    if category in _ZERO_RATE_CATEGORIES:
        return ZERO
    raise ValueError(
        f"vat_rate is required for VAT category {category.value!r} — "
        "the applicable rate cannot be derived."
    )


def line_item(
    line_id: str,
    name: str,
    *,
    net_price: Numeric,
    quantity: Numeric = 1,
    unit_code: str = "C62",
    basis_quantity: Numeric | None = None,
    gross_price: Numeric | None = None,
    vat_category: CategoryCode = CategoryCode.T_S,
    vat_rate: Numeric | None = None,
    global_id: GlobalID | None = None,
    note: str | None = None,
) -> TradeLineItem:
    """Build one invoice line (BG-25), deriving everything derivable.

    * The line total (BT-131) is computed as ``net_price * quantity /
      basis_quantity`` rounded half away from zero to two decimals
      (Factur-X §7.1.8), satisfying ``BR-CO-10`` / ``BR-CO-13`` once
      the document totals are computed from the lines.
    * When ``gross_price`` (BT-148) is given, the price discount
      (BT-147) is derived as ``gross_price - net_price`` and wired into
      the gross-price group; a gross price below the net price raises
      (a price *charge* is EXTENDED-only).
    * The VAT rate defaults to the only legal value where the category
      admits exactly one (0 for ``Z`` / ``E`` / ``AE`` / ``G`` / ``K``,
      absent for ``O``); for ``S`` / ``L`` / ``M`` it must be given.

    Note: the item description (BT-154) is COMFORT+ and so is not
    exposed here. ``unit_code`` defaults to ``C62`` ("one", UN/ECE
    Rec. 20).
    """
    net = to_decimal(net_price, name="net_price")
    qty = to_decimal(quantity, name="quantity")
    basis = optional_decimal(basis_quantity, name="basis_quantity")
    rate = _vat_rate(vat_category, vat_rate)

    line_total = round_half_away_from_zero(net * qty / (basis or Decimal("1")))

    gross: GrossTradePrice | None = None
    if gross_price is not None:
        gross_amount = to_decimal(gross_price, name="gross_price")
        discount = gross_amount - net
        if discount < 0:
            raise ValueError(
                "gross_price must not be below net_price — a price-level "
                "charge is only representable at EXTENDED."
            )
        gross = GrossTradePrice(
            charge_amount=gross_amount,
            basis_quantity=(
                BasisQuantity(value=basis, unit_code=unit_code)
                if basis is not None
                else None
            ),
            applied_allowance_charge=(
                [AppliedTradeAllowanceCharge(indicator=False, actual_amount=discount)]
                if discount
                else None
            ),
        )

    return TradeLineItem(
        associated_document=DocumentLineDocument(
            line_id=line_id,
            note=LineIncludedNote(content=note) if note is not None else None,
        ),
        product=TradeProduct(name=name, global_id=global_id),
        agreement=LineTradeAgreement(
            gross_price=gross,
            net_price=NetTradePrice(
                charge_amount=net,
                basis_quantity=(
                    BasisQuantity(value=basis, unit_code=unit_code)
                    if basis is not None
                    else None
                ),
            ),
        ),
        delivery=LineTradeDelivery(
            billed_quantity=Quantity(value=qty, unit_code=unit_code)
        ),
        settlement=LineTradeSettlement(
            applicable_trade_tax=ApplicableTradeTax(
                category_code=vat_category, rate_applicable_percent=rate
            ),
            monetary_summation=LineMonetarySummation(line_total=line_total),
        ),
    )


def vat_breakdown(
    items: Sequence[TradeLineItem],
    allowance_charges: Sequence[HeaderTradeAllowanceCharge] = (),
    *,
    exemption_reasons: Mapping[CategoryCode, str] | None = None,
    exemption_reason_codes: Mapping[CategoryCode, VATEXCode] | None = None,
) -> list[ApplicableTradeTax]:
    """Compute the BG-23 VAT breakdown from lines and allowances / charges.

    Groups the line totals (BT-131) by (category, rate), nets in the
    document-level allowances (BT-92, subtracted) and charges (BT-99,
    added) by *their* category (BT-95 / BT-102), and derives per group
    the taxable amount (BT-116) and the tax amount (BT-117) per
    ``BR-CO-17``.

    Exemption reasons: categories ``E`` / ``AE`` / ``G`` / ``K`` / ``O``
    must carry a reason text (BT-120) or code (BT-121). The canonical
    VATEX code is defaulted for ``AE`` / ``G`` / ``K`` / ``O``;
    category ``E`` has no canonical code, so a reason must be supplied
    via ``exemption_reasons`` / ``exemption_reason_codes`` — otherwise
    this function raises rather than emitting a row that cannot
    validate.
    """
    reasons = exemption_reasons or {}
    reason_codes = exemption_reason_codes or {}

    basis_by_group: dict[tuple[CategoryCode, Decimal | None], Decimal] = {}
    for item in items:
        line_id = item.associated_document.line_id
        trade_tax = item.settlement.applicable_trade_tax
        if trade_tax is None:
            raise ValueError(
                f"line {line_id!r}: no line VAT (BG-30) to group the breakdown by."
            )
        line_total = item.settlement.monetary_summation.line_total
        if line_total is None:
            raise ValueError(f"line {line_id!r}: line total (BT-131) is not set.")
        key = (trade_tax.category_code, trade_tax.rate_applicable_percent)
        basis_by_group[key] = basis_by_group.get(key, ZERO) + line_total

    for ac in allowance_charges:
        category_tax = ac.category_trade_tax
        if category_tax is None:
            raise ValueError(
                "document-level allowance/charge carries no VAT category "
                "(BT-95-00 / BT-102-00) — required to compute the breakdown."
            )
        key = (category_tax.category_code, category_tax.rate_applicable_percent)
        delta = ac.actual_amount if ac.indicator else -ac.actual_amount
        basis_by_group[key] = basis_by_group.get(key, ZERO) + delta

    rows: list[ApplicableTradeTax] = []
    for (category, rate), basis in basis_by_group.items():
        reason = reasons.get(category)
        code = reason_codes.get(category)
        if reason is None and code is None:
            code = DEFAULT_EXEMPTION_CODE.get(category)
            if category is CategoryCode.T_E:
                raise ValueError(
                    "VAT category 'E' (exempt) requires an exemption reason "
                    "(BT-120) or code (BT-121); pass exemption_reasons={"
                    "CategoryCode.T_E: '…'} (or exemption_reason_codes)."
                )
        rows.append(
            ApplicableTradeTax(
                calculated_amount=category_tax_amount(basis, rate),
                exemption_reason=reason,
                basis_amount=basis,
                category_code=category,
                exemption_reason_code=code,
                rate_applicable_percent=rate,
            )
        )
    return rows


def basic_invoice(
    invoice_number: str,
    issue_date: date,
    *,
    seller: SellerTradeParty,
    buyer: BuyerTradeParty,
    items: Sequence[TradeLineItem],
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
    exemption_reasons: Mapping[CategoryCode, str] | None = None,
    exemption_reason_codes: Mapping[CategoryCode, VATEXCode] | None = None,
) -> Document:
    """Build a complete BASIC-profile document from parties and lines.

    Give it the parties and the lines (see :func:`line_item`); the
    BG-23 VAT breakdown (:func:`vat_breakdown`) and the BG-22 totals
    (:func:`~getafix.build.monetary_summation`) are computed so the
    arithmetic rules (``BR-CO-10`` … ``BR-CO-16``) hold by
    construction.

    ``due_date`` is shorthand for ``terms=PaymentTerms(due=…)`` — one
    of the two (or a payment-terms text) is required by ``BR-CO-25``
    whenever the amount due is positive.
    """
    if not items:
        raise ValueError("at least one line item (BG-25) is required (BR-16).")

    charges = list(allowance_charges) or None
    trade_taxes = vat_breakdown(
        items,
        allowance_charges,
        exemption_reasons=exemption_reasons,
        exemption_reason_codes=exemption_reason_codes,
    )
    line_total = sum(
        (item.settlement.monetary_summation.line_total or ZERO for item in items), ZERO
    )

    return Document(
        context=Context(guideline=GuidelineDocument(id=Profile.BASIC)),
        header=header(invoice_number, issue_date, type_code, notes),
        trade=Trade(
            items=list(items),
            agreement=TradeAgreement(
                buyer_reference=buyer_reference, seller=seller, buyer=buyer
            ),
            delivery=trade_delivery(delivery_date),
            settlement=TradeSettlement(
                currency_code=currency,
                payment_means=list(payment_means) or None,
                trade_taxes=trade_taxes,
                allowance_charge=charges,
                terms=payment_terms(terms, due_date),
                monetary_summation=monetary_summation(
                    currency=currency,
                    line_total=line_total,
                    trade_taxes=trade_taxes,
                    allowance_charges=allowance_charges,
                    prepaid_total=prepaid_total,
                ),
            ),
        ),
    )
