"""Cross-profile helpers shared by the per-profile builders.

These functions back :mod:`getafix.build.minimum`,
:mod:`getafix.build.basic_wl` and :mod:`getafix.build.basic`. Only
helpers used by more than one profile (or by several of those modules'
own helpers) live here — anything specific to a single profile sits in
that profile's module.

Monetary inputs accept ``Decimal``, ``int`` or ``str`` (``float`` is
rejected — binary floats carry representation noise that leaks into
amounts).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date
from decimal import Decimal

from getafix.schema import Header, IncludedNote, Profile, TypeCode
from getafix.schema._numeric import round_half_away_from_zero
from getafix.schema.accounting import (
    ApplicableTradeTax,
    HeaderTradeAllowanceCharge,
    MonetarySummation,
    TaxTotal,
)
from getafix.schema.delivery import SupplyChainEvent, TradeDelivery
from getafix.schema.party import (
    BuyerTradeParty,
    PostalTradeAddressExtended,
    SellerTradeParty,
    SpecifiedTaxRegistration,
    TaxSchemeId,
)
from getafix.schema.settlement import PaymentTerms
from getafix.schema.types import CategoryCode, Country, Currency, VATEXCode

Numeric = Decimal | int | str
"""Accepted monetary / quantity input — coerced via :func:`Decimal`.

``float`` is deliberately not accepted: ``Decimal(0.1)`` is
``0.1000000000000000055511151231257827…``, which is never the amount
the caller meant. Pass the value as ``str`` (or ``Decimal``) instead.
"""

ZERO = Decimal("0")
_CENT = Decimal("0.01")

# Canonical VATEX exemption-reason codes (BT-121) per category. ``E``
# has no single canonical code (the legal basis differs case by case),
# so it is absent here and must be supplied by the caller.
DEFAULT_EXEMPTION_CODE: dict[CategoryCode, VATEXCode] = {
    CategoryCode.T_AE: VATEXCode.VATEX_EU_AE,
    CategoryCode.T_G: VATEXCode.VATEX_EU_G,
    CategoryCode.T_K: VATEXCode.VATEX_EU_IC,
    CategoryCode.T_O: VATEXCode.VATEX_EU_O,
}


def to_decimal(value: Numeric, *, name: str) -> Decimal:
    """Coerce *value* to :class:`Decimal`, rejecting ``float``."""
    if isinstance(value, float):
        raise TypeError(
            f"{name}: float is not accepted (binary representation noise); "
            "pass a str or Decimal instead."
        )
    return Decimal(value)


def optional_decimal(value: Numeric | None, *, name: str) -> Decimal | None:
    return None if value is None else to_decimal(value, name=name)


def category_tax_amount(basis: Decimal, rate: Decimal | None) -> Decimal:
    """VAT category tax amount (BT-117) per ``BR-CO-17`` — basis * rate,
    rounded half away from zero; 0 for rate-less categories."""
    if rate is None:
        return ZERO.quantize(_CENT)
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


def monetary_summation(
    *,
    currency: Currency,
    line_total: Numeric | None = None,
    trade_taxes: Sequence[ApplicableTradeTax] = (),
    allowance_charges: Sequence[HeaderTradeAllowanceCharge] = (),
    prepaid_total: Numeric | None = None,
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
    * BT-115 — ``BT-112 - BT-113`` (``BR-CO-16``).

    Note: ``line_total`` (BT-106) is required from BASIC_WL upwards
    (``BR-12``). The rounding amount (BT-114) is COMFORT+ and therefore
    out of range for these builders.
    """
    allowances = [ac.actual_amount for ac in allowance_charges if not ac.indicator]
    charges = [ac.actual_amount for ac in allowance_charges if ac.indicator]
    allowance_total = sum(allowances, ZERO) if allowances else None
    charge_total = sum(charges, ZERO) if charges else None

    lines = optional_decimal(line_total, name="line_total")
    if lines is not None:
        tax_basis = lines - (allowance_total or ZERO) + (charge_total or ZERO)
    else:
        tax_basis = sum((tt.basis_amount or ZERO for tt in trade_taxes), ZERO)
    tax = sum((tt.calculated_amount or ZERO for tt in trade_taxes), ZERO)
    grand_total = tax_basis + tax

    prepaid = optional_decimal(prepaid_total, name="prepaid_total")
    due = grand_total - (prepaid or ZERO)

    return MonetarySummation(
        line_total=lines,
        charge_total=charge_total,
        allowance_total=allowance_total,
        tax_basis_total=tax_basis,
        tax_total=(
            [TaxTotal(amount=tax, currency_id=currency)] if trade_taxes else None
        ),
        grand_total=grand_total,
        prepaid_total=prepaid,
        due_amount=due,
        currency=str(currency),
    )


def payment_terms(
    terms: PaymentTerms | None, due_date: date | None
) -> list[PaymentTerms] | None:
    if terms is not None and due_date is not None:
        raise ValueError("pass either terms or due_date, not both.")
    if terms is not None:
        return [terms]
    if due_date is not None:
        return [PaymentTerms(due=due_date)]
    return None


def trade_delivery(delivery_date: date | None) -> TradeDelivery:
    return TradeDelivery(
        event=(
            SupplyChainEvent(occurrence=delivery_date)
            if delivery_date is not None
            else None
        )
    )


def header(
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


def stamp_currency(
    allowance_charges: Sequence[HeaderTradeAllowanceCharge], currency: Currency
) -> list[HeaderTradeAllowanceCharge] | None:
    stamped = [
        ac if ac.currency is not None else replace(ac, currency=str(currency))
        for ac in allowance_charges
    ]
    return stamped or None
