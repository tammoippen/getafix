"""High-level factories for building profile-shaped invoices.

The :mod:`getafix.schema` dataclasses deliberately mirror the CII XML
tree one-to-one: every business term is set explicitly and nothing is
derived behind the caller's back. This module is the convenience layer
on top — a handful of factories that take the business inputs and
compute everything that *can* be computed:

* :func:`seller_party` / :func:`buyer_party` — BG-4 / BG-7 parties
  without the ``SpecifiedTaxRegistration`` / ``TaxSchemeId`` /
  ``PostalTradeAddressExtended`` boilerplate.
* :func:`line_item` — one BG-25 invoice line from price, quantity and
  VAT category; the line total (BT-131) and the price-discount wiring
  (BT-147) are derived.
* :func:`vat_breakdown` — the BG-23 rows grouped per VAT category /
  rate from the line items and document-level allowances / charges,
  with the category tax amounts (BT-117) rounded per Factur-X §7.1.8.
* :func:`monetary_summation` — the BG-22 totals block computed along
  the ``BR-CO-11`` / ``BR-CO-12`` / ``BR-CO-13`` / ``BR-CO-14`` /
  ``BR-CO-15`` / ``BR-CO-16`` identities.
* :func:`minimum_invoice` / :func:`basic_wl_invoice` — complete
  documents for the two profiles without line items (header totals
  only).
* :func:`invoice` — a complete document for the line-item profiles
  (BASIC, COMFORT / EN 16931, EXTENDED): give it parties and lines,
  get back a document whose VAT breakdown and totals already satisfy
  the arithmetic business rules.

Monetary inputs accept ``Decimal``, ``int`` or ``str`` (``float`` is
rejected — binary floats carry representation noise that leaks into
amounts). The factories return ordinary schema dataclasses, so any
field the factory does not expose can still be set afterwards before
calling :meth:`~getafix.schema.document.Document.validate` /
:meth:`~getafix.schema.document.Document.to_xml`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date
from decimal import Decimal

from getafix.schema import (
    Context,
    Document,
    GuidelineDocument,
    Header,
    IncludedNote,
    Profile,
    TypeCode,
)
from getafix.schema._numeric import round_half_away_from_zero
from getafix.schema.accounting import (
    ApplicableTradeTax,
    HeaderTradeAllowanceCharge,
    MonetarySummation,
    TaxTotal,
)
from getafix.schema.agreement import TradeAgreement
from getafix.schema.delivery import SupplyChainEvent, TradeDelivery
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
from getafix.schema.party import (
    BuyerTradeParty,
    GlobalID,
    PostalTradeAddressExtended,
    SellerTradeParty,
    SpecifiedTaxRegistration,
    TaxSchemeId,
)
from getafix.schema.settlement import PaymentMeans, PaymentTerms, TradeSettlement
from getafix.schema.trade import Trade, TradeLineItem
from getafix.schema.types import CategoryCode, Country, Currency, VATEXCode

Numeric = Decimal | int | str
"""Accepted monetary / quantity input — coerced via :func:`Decimal`.

``float`` is deliberately not accepted: ``Decimal(0.1)`` is
``0.1000000000000000055511151231257827…``, which is never the amount
the caller meant. Pass the value as ``str`` (or ``Decimal``) instead.
"""

_ZERO = Decimal("0")
_CENT = Decimal("0.01")

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

# Canonical VATEX exemption-reason codes (BT-121) per category. ``E``
# has no single canonical code (the legal basis differs case by case),
# so it is absent here and must be supplied by the caller.
_DEFAULT_EXEMPTION_CODE: dict[CategoryCode, VATEXCode] = {
    CategoryCode.T_AE: VATEXCode.VATEX_EU_AE,
    CategoryCode.T_G: VATEXCode.VATEX_EU_G,
    CategoryCode.T_K: VATEXCode.VATEX_EU_IC,
    CategoryCode.T_O: VATEXCode.VATEX_EU_O,
}


def _decimal(value: Numeric, *, name: str) -> Decimal:
    """Coerce *value* to :class:`Decimal`, rejecting ``float``."""
    if isinstance(value, float):
        raise TypeError(
            f"{name}: float is not accepted (binary representation noise); "
            "pass a str or Decimal instead."
        )
    return Decimal(value)


def _optional_decimal(value: Numeric | None, *, name: str) -> Decimal | None:
    return None if value is None else _decimal(value, name=name)


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
        return _decimal(rate, name="vat_rate")
    if category in _ZERO_RATE_CATEGORIES:
        return _ZERO
    raise ValueError(
        f"vat_rate is required for VAT category {category.value!r} — "
        "the applicable rate cannot be derived."
    )


def _category_tax_amount(basis: Decimal, rate: Decimal | None) -> Decimal:
    """VAT category tax amount (BT-117) per ``BR-CO-17`` — basis * rate,
    rounded half away from zero; 0 for rate-less categories."""
    if rate is None:
        return _ZERO.quantize(_CENT)
    return round_half_away_from_zero(basis * rate / Decimal("100"))


def _tax_registrations(
    vat_id: str | None, tax_id: str | None
) -> list[SpecifiedTaxRegistration] | None:
    registrations = [
        SpecifiedTaxRegistration(id=TaxSchemeId(id=value, scheme_id=scheme))
        for value, scheme in ((vat_id, "VA"), (tax_id, "FC"))
        if value is not None
    ]
    return registrations or None


def seller_party(
    name: str,
    *,
    country: Country,
    vat_id: str | None = None,
    tax_id: str | None = None,
    postcode: str | None = None,
    city: str | None = None,
    line_one: str | None = None,
    line_two: str | None = None,
    country_subdivision: str | None = None,
) -> SellerTradeParty:
    """Build a Seller (BG-4) from the common identifying fields.

    ``vat_id`` becomes the BT-31 VAT registration (``schemeID="VA"``),
    ``tax_id`` the BT-32 local tax number (``schemeID="FC"``). The
    address detail fields (postcode, city, address lines, subdivision)
    are BASIC_WL+ — leave them unset for a MINIMUM document, where the
    address carries only the country code (BT-40).

    Note: at least one of BT-29 / BT-30 / BT-31 must identify the
    Seller (``BR-CO-26``) — in practice pass ``vat_id``, or set
    ``id`` / ``global_ids`` / ``legal_organization`` on the returned
    party afterwards.
    """
    return SellerTradeParty(
        name=name,
        address=PostalTradeAddressExtended(
            postcode=postcode,
            line_one=line_one,
            line_two=line_two,
            city_name=city,
            country_id=country,
            country_subdivision=country_subdivision,
        ),
        tax_registrations=_tax_registrations(vat_id, tax_id),
    )


def buyer_party(
    name: str,
    *,
    country: Country,
    vat_id: str | None = None,
    postcode: str | None = None,
    city: str | None = None,
    line_one: str | None = None,
    line_two: str | None = None,
    country_subdivision: str | None = None,
) -> BuyerTradeParty:
    """Build a Buyer (BG-7) from the common identifying fields.

    ``vat_id`` becomes the BT-48 VAT registration (``schemeID="VA"``).
    As with :func:`seller_party`, the address detail fields are
    BASIC_WL+ — only the country code renders at MINIMUM.
    """
    return BuyerTradeParty(
        name=name,
        address=PostalTradeAddressExtended(
            postcode=postcode,
            line_one=line_one,
            line_two=line_two,
            city_name=city,
            country_id=country,
            country_subdivision=country_subdivision,
        ),
        tax_registrations=_tax_registrations(vat_id, None),
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
    description: str | None = None,
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

    ``description`` is COMFORT+ (BT-154) — leave it unset on BASIC
    documents. ``unit_code`` defaults to ``C62`` ("one", UN/ECE
    Rec. 20).
    """
    net = _decimal(net_price, name="net_price")
    qty = _decimal(quantity, name="quantity")
    basis = _optional_decimal(basis_quantity, name="basis_quantity")
    rate = _vat_rate(vat_category, vat_rate)

    line_total = round_half_away_from_zero(net * qty / (basis or Decimal("1")))

    gross: GrossTradePrice | None = None
    if gross_price is not None:
        gross_amount = _decimal(gross_price, name="gross_price")
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
        product=TradeProduct(name=name, description=description, global_id=global_id),
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
    currency: Currency | None = None,
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
        basis_by_group[key] = basis_by_group.get(key, _ZERO) + line_total

    for ac in allowance_charges:
        category_tax = ac.category_trade_tax
        if category_tax is None:
            raise ValueError(
                "document-level allowance/charge carries no VAT category "
                "(BT-95-00 / BT-102-00) — required to compute the breakdown."
            )
        key = (category_tax.category_code, category_tax.rate_applicable_percent)
        delta = ac.actual_amount if ac.indicator else -ac.actual_amount
        basis_by_group[key] = basis_by_group.get(key, _ZERO) + delta

    rows: list[ApplicableTradeTax] = []
    for (category, rate), basis in basis_by_group.items():
        reason = reasons.get(category)
        code = reason_codes.get(category)
        if reason is None and code is None:
            code = _DEFAULT_EXEMPTION_CODE.get(category)
            if category is CategoryCode.T_E:
                raise ValueError(
                    "VAT category 'E' (exempt) requires an exemption reason "
                    "(BT-120) or code (BT-121); pass exemption_reasons={"
                    "CategoryCode.T_E: '…'} (or exemption_reason_codes)."
                )
        rows.append(
            ApplicableTradeTax(
                calculated_amount=_category_tax_amount(basis, rate),
                exemption_reason=reason,
                basis_amount=basis,
                category_code=category,
                exemption_reason_code=code,
                rate_applicable_percent=rate,
                currency=str(currency) if currency is not None else None,
            )
        )
    return rows


def monetary_summation(
    *,
    currency: Currency,
    line_total: Numeric | None = None,
    trade_taxes: Sequence[ApplicableTradeTax] = (),
    allowance_charges: Sequence[HeaderTradeAllowanceCharge] = (),
    prepaid_total: Numeric | None = None,
    rounding_amount: Numeric | None = None,
) -> MonetarySummation:
    """Compute the BG-22 totals along the ``BR-CO-*`` identities.

    * BT-107 / BT-108 — sums of the document allowances / charges
      (``BR-CO-11`` / ``BR-CO-12``); omitted when there are none.
    * BT-109 — ``BT-106 - BT-107 + BT-108`` (``BR-CO-13``); when
      ``line_total`` is not given (MINIMUM / BASIC_WL documents), the
      sum of the breakdown bases (BT-116) is used instead.
    * BT-110 — sum of the BT-117 tax amounts (``BR-CO-14``); the
      ``TaxTotal`` row is omitted when there is no breakdown.
    * BT-112 — ``BT-109 + BT-110`` (``BR-CO-15``).
    * BT-115 — ``BT-112 - BT-113 + BT-114`` (``BR-CO-16``).

    Note: ``line_total`` (BT-106) is required from BASIC_WL upwards
    (``BR-12``); ``rounding_amount`` (BT-114) is COMFORT+.
    """
    allowances = [ac.actual_amount for ac in allowance_charges if not ac.indicator]
    charges = [ac.actual_amount for ac in allowance_charges if ac.indicator]
    allowance_total = sum(allowances, _ZERO) if allowances else None
    charge_total = sum(charges, _ZERO) if charges else None

    lines = _optional_decimal(line_total, name="line_total")
    if lines is not None:
        tax_basis = lines - (allowance_total or _ZERO) + (charge_total or _ZERO)
    else:
        tax_basis = sum((tt.basis_amount or _ZERO for tt in trade_taxes), _ZERO)
    tax = sum((tt.calculated_amount or _ZERO for tt in trade_taxes), _ZERO)
    grand_total = tax_basis + tax

    prepaid = _optional_decimal(prepaid_total, name="prepaid_total")
    rounding = _optional_decimal(rounding_amount, name="rounding_amount")
    due = grand_total - (prepaid or _ZERO) + (rounding or _ZERO)

    return MonetarySummation(
        line_total=lines,
        charge_total=charge_total,
        allowance_total=allowance_total,
        tax_basis_total=tax_basis,
        tax_total=(
            [TaxTotal(amount=tax, currency_id=currency)] if trade_taxes else None
        ),
        rounding_amount=rounding,
        grand_total=grand_total,
        prepaid_total=prepaid,
        due_amount=due,
        currency=str(currency),
    )


def _payment_terms(
    terms: PaymentTerms | None, due_date: date | None
) -> list[PaymentTerms] | None:
    if terms is not None and due_date is not None:
        raise ValueError("pass either terms or due_date, not both.")
    if terms is not None:
        return [terms]
    if due_date is not None:
        return [PaymentTerms(due=due_date)]
    return None


def _trade_delivery(delivery_date: date | None) -> TradeDelivery:
    return TradeDelivery(
        event=(
            SupplyChainEvent(occurrence=delivery_date)
            if delivery_date is not None
            else None
        )
    )


def _header(
    profile: Profile,
    invoice_number: str,
    issue_date: date,
    type_code: TypeCode,
    notes: Sequence[str],
) -> Header:
    del profile  # reserved for future per-profile defaults
    return Header(
        id=invoice_number,
        type_code=type_code,
        issue_date=issue_date,
        notes=[IncludedNote(content=n) for n in notes] or None,
    )


def _complete_trade_taxes(
    trade_taxes: Sequence[ApplicableTradeTax], currency: Currency
) -> list[ApplicableTradeTax]:
    """Fill the derivable fields on caller-supplied BG-23 rows.

    Each row needs at least the taxable amount (BT-116) and the
    category (BT-118); the tax amount (BT-117, per ``BR-CO-17``), the
    canonical exemption-reason code (BT-121, where one exists) and the
    currency stamp are filled in when absent. Returns copies — the
    caller's rows are not mutated.
    """
    completed: list[ApplicableTradeTax] = []
    for tt in trade_taxes:
        if tt.basis_amount is None:
            raise ValueError(
                "VAT breakdown row (BG-23) needs basis_amount (BT-116) set."
            )
        calculated = tt.calculated_amount
        if calculated is None:
            calculated = _category_tax_amount(
                tt.basis_amount, tt.rate_applicable_percent
            )
        code = tt.exemption_reason_code
        if code is None and tt.exemption_reason is None:
            code = _DEFAULT_EXEMPTION_CODE.get(tt.category_code)
        completed.append(
            replace(
                tt,
                calculated_amount=calculated,
                exemption_reason_code=code,
                currency=tt.currency or str(currency),
            )
        )
    return completed


def _stamp_currency(
    allowance_charges: Sequence[HeaderTradeAllowanceCharge], currency: Currency
) -> list[HeaderTradeAllowanceCharge] | None:
    stamped = [
        ac if ac.currency is not None else replace(ac, currency=str(currency))
        for ac in allowance_charges
    ]
    return stamped or None


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
    only the country code) — see :func:`seller_party`. Some receivers
    only admit type code 751 ("invoice information for accounting
    purposes") at MINIMUM; override ``type_code`` when required.
    """
    basis = _decimal(tax_basis_total, name="tax_basis_total")
    if tax_amount is not None and vat_rate is not None:
        raise ValueError("pass either tax_amount or vat_rate, not both.")
    tax: Decimal | None = _optional_decimal(tax_amount, name="tax_amount")
    if tax is None and vat_rate is not None:
        tax = _category_tax_amount(basis, _decimal(vat_rate, name="vat_rate"))
    grand_total = basis + (tax or _ZERO)

    return Document(
        context=Context(guideline=GuidelineDocument(id=Profile.MINIMUM)),
        header=_header(Profile.MINIMUM, invoice_number, issue_date, type_code, ()),
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
    completed = _complete_trade_taxes(trade_taxes, currency)
    stamped = _stamp_currency(allowance_charges, currency)
    allowance_total = sum(
        (ac.actual_amount for ac in stamped or [] if not ac.indicator), _ZERO
    )
    charge_total = sum(
        (ac.actual_amount for ac in stamped or [] if ac.indicator), _ZERO
    )
    basis_sum = sum((tt.basis_amount or _ZERO for tt in completed), _ZERO)
    line_total = basis_sum + allowance_total - charge_total

    return Document(
        context=Context(guideline=GuidelineDocument(id=Profile.BASIC_WL)),
        header=_header(Profile.BASIC_WL, invoice_number, issue_date, type_code, notes),
        trade=Trade(
            agreement=TradeAgreement(
                buyer_reference=buyer_reference, seller=seller, buyer=buyer
            ),
            delivery=_trade_delivery(delivery_date),
            settlement=TradeSettlement(
                currency_code=currency,
                payment_means=list(payment_means) or None,
                trade_taxes=completed,
                allowance_charge=stamped,
                terms=_payment_terms(terms, due_date),
                monetary_summation=monetary_summation(
                    currency=currency,
                    line_total=line_total,
                    trade_taxes=completed,
                    allowance_charges=stamped or (),
                    prepaid_total=prepaid_total,
                ),
            ),
        ),
    )


def invoice(
    invoice_number: str,
    issue_date: date,
    *,
    seller: SellerTradeParty,
    buyer: BuyerTradeParty,
    items: Sequence[TradeLineItem],
    profile: Profile = Profile.COMFORT,
    allowance_charges: Sequence[HeaderTradeAllowanceCharge] = (),
    currency: Currency = Currency.EUR,
    type_code: TypeCode = TypeCode.T_CommercialInvoice,
    due_date: date | None = None,
    terms: PaymentTerms | None = None,
    payment_means: Sequence[PaymentMeans] = (),
    delivery_date: date | None = None,
    notes: Sequence[str] = (),
    prepaid_total: Numeric | None = None,
    rounding_amount: Numeric | None = None,
    buyer_reference: str | None = None,
    exemption_reasons: Mapping[CategoryCode, str] | None = None,
    exemption_reason_codes: Mapping[CategoryCode, VATEXCode] | None = None,
) -> Document:
    """Build a complete document for a line-item profile (BASIC+).

    Give it the parties and the lines (see :func:`line_item`); the
    BG-23 VAT breakdown (:func:`vat_breakdown`) and the BG-22 totals
    (:func:`monetary_summation`) are computed so the arithmetic
    rules (``BR-CO-10`` … ``BR-CO-16``) hold by construction.

    ``profile`` defaults to COMFORT (EN 16931) and must be BASIC or
    higher — use :func:`minimum_invoice` / :func:`basic_wl_invoice`
    for the profiles without line items. ``rounding_amount`` (BT-114)
    is COMFORT+. ``due_date`` is shorthand for
    ``terms=PaymentTerms(due=…)`` (``BR-CO-25``).
    """
    if profile < Profile.BASIC:
        raise ValueError(
            "invoice() builds line-item profiles (BASIC+); use "
            "minimum_invoice() or basic_wl_invoice() for "
            f"{profile.name}."
        )
    if not items:
        raise ValueError("at least one line item (BG-25) is required (BR-16).")

    stamped = _stamp_currency(allowance_charges, currency)
    trade_taxes = vat_breakdown(
        items,
        stamped or (),
        currency=currency,
        exemption_reasons=exemption_reasons,
        exemption_reason_codes=exemption_reason_codes,
    )
    line_total = sum(
        (item.settlement.monetary_summation.line_total or _ZERO for item in items),
        _ZERO,
    )

    return Document(
        context=Context(guideline=GuidelineDocument(id=profile)),
        header=_header(profile, invoice_number, issue_date, type_code, notes),
        trade=Trade(
            items=list(items),
            agreement=TradeAgreement(
                buyer_reference=buyer_reference, seller=seller, buyer=buyer
            ),
            delivery=_trade_delivery(delivery_date),
            settlement=TradeSettlement(
                currency_code=currency,
                payment_means=list(payment_means) or None,
                trade_taxes=trade_taxes,
                allowance_charge=stamped,
                terms=_payment_terms(terms, due_date),
                monetary_summation=monetary_summation(
                    currency=currency,
                    line_total=line_total,
                    trade_taxes=trade_taxes,
                    allowance_charges=stamped or (),
                    prepaid_total=prepaid_total,
                    rounding_amount=rounding_amount,
                ),
            ),
        ),
    )
