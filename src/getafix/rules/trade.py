"""Validators for :mod:`getafix.schema.trade`.

Cross-sibling rules: every check that needs to read across line items,
header allowances/charges, the monetary summation and the agreement
parties in one pass. The signatures match
:data:`getafix.rules.Validator`.

Each function:

* self-gates on profile and on the precondition data;
* returns ``list[ValidationError]`` (empty on success);
* never raises.

Most family / single-rate rules emit at most one ``ValidationError``
per call (deduplicated by rule code). ``br_co_21..24`` use
per-occurrence semantics — one error per offending allowance /
charge.
"""

# pyright: reportImportCycles=false

from __future__ import annotations

from collections.abc import Callable, Iterator
from decimal import Decimal
from typing import TYPE_CHECKING

from getafix.errors import ValidationError
from getafix.schema.types import CategoryCode, Profile

if TYPE_CHECKING:
    from getafix.schema import trade as _trade
    from getafix.schema.party import BuyerTradeParty, SpecifiedTaxRegistration


# ---------------------------------------------------------------------------
# Party helpers
# ---------------------------------------------------------------------------


def _iter_tax_registrations(
    registrations: SpecifiedTaxRegistration | list[SpecifiedTaxRegistration] | None,
) -> Iterator[SpecifiedTaxRegistration]:
    """Yield each SpecifiedTaxRegistration regardless of the carrying
    party's cardinality on the field (some parties carry a single
    registration, others a ``list[...] | None``)."""
    if registrations is None:
        return
    if isinstance(registrations, list):
        yield from registrations
    else:
        yield registrations


def _has_vat_id(party: object) -> bool:
    if party is None:
        return False
    return any(
        tr.id.scheme_id == "VA"
        for tr in _iter_tax_registrations(getattr(party, "tax_registrations", None))
    )


def _has_vat_or_local_tax_id(party: object) -> bool:
    if party is None:
        return False
    return any(
        tr.id.scheme_id in ("VA", "FC")
        for tr in _iter_tax_registrations(getattr(party, "tax_registrations", None))
    )


def _has_buyer_legal_id(buyer: BuyerTradeParty) -> bool:
    return (
        buyer.legal_organization is not None and buyer.legal_organization.id is not None
    )


# ---------------------------------------------------------------------------
# Per-VAT-category required-party rules.
#
# For each family ``X`` (AE / E / G / IC / IG / IP / S / Z), three rules
# fire when the seller / buyer identifier matrix is incomplete:
#
# * ``br_X_2`` — at least one line item carries category X.
# * ``br_X_3`` — at least one document-level allowance carries category X.
# * ``br_X_4`` — at least one document-level charge carries category X.
#
# Each function emits at most one ValidationError; offences are
# deduplicated by rule code.
# ---------------------------------------------------------------------------


# EN 16931 per-line "field shall be present" rules. The line-level
# fields they gate (BT-129 / BT-130 / BT-131 / BT-146 / BT-151) are
# ``Optional`` on the getafix dataclasses so EXTENDED GROUP /
# INFORMATION lines can legitimately omit them. Each rule
# short-circuits at EXTENDED; the matching ``BR-FXEXT-2x`` /
# ``BR-FXEXT-CO-04`` in :mod:`getafix.rules.extended` enforce the
# same constraint with the DETAIL / unset filter applied.


def br_22(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-22: every BG-25 line shall carry an invoiced quantity (BT-129)."""
    if profile >= Profile.EXTENDED:
        return []
    return [
        ValidationError(
            "BR-22",
            f"line {item.associated_document.line_id!r}: invoiced "
            f"quantity (BT-129) is required.",
        )
        for item in m.items
        if item.delivery.billed_quantity is None
    ]


def br_23(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-23: every BG-25 line shall carry a unit of measure (BT-130)."""
    if profile >= Profile.EXTENDED:
        return []
    return [
        ValidationError(
            "BR-23",
            f"line {item.associated_document.line_id!r}: unit-of-measure "
            f"code (BT-130) is required.",
        )
        for item in m.items
        if item.delivery.billed_quantity is None
        or not item.delivery.billed_quantity.unit_code
    ]


def br_24(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-24: every BG-25 line shall carry a line net amount (BT-131)."""
    if profile >= Profile.EXTENDED:
        return []
    return [
        ValidationError(
            "BR-24",
            f"line {item.associated_document.line_id!r}: invoice line "
            f"net amount (BT-131) is required.",
        )
        for item in m.items
        if item.settlement.monetary_summation.line_total is None
    ]


def br_26(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-26: every BG-25 line shall carry an item net price (BT-146)."""
    if profile >= Profile.EXTENDED:
        return []
    return [
        ValidationError(
            "BR-26",
            f"line {item.associated_document.line_id!r}: item net price "
            f"(BT-146) is required.",
        )
        for item in m.items
        if item.agreement.net_price is None
    ]


def br_co_4(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-CO-4: every BG-25 line shall carry a VAT category code (BT-151)."""
    if profile >= Profile.EXTENDED:
        return []
    return [
        ValidationError(
            "BR-CO-4",
            f"line {item.associated_document.line_id!r}: line VAT "
            f"category (BT-151) is required.",
        )
        for item in m.items
        if item.settlement.applicable_trade_tax is None
    ]


def _line_has_category(m: _trade.Trade, category: CategoryCode) -> bool:
    return any(
        item.settlement.applicable_trade_tax is not None
        and item.settlement.applicable_trade_tax.category_code == category
        for item in m.items
    )


def _alw_has_category(m: _trade.Trade, category: CategoryCode) -> bool:
    return any(
        not ac.indicator
        and ac.category_trade_tax is not None
        and ac.category_trade_tax.category_code == category
        for ac in m.settlement.allowance_charge or []
    )


def _chg_has_category(m: _trade.Trade, category: CategoryCode) -> bool:
    return any(
        ac.indicator
        and ac.category_trade_tax is not None
        and ac.category_trade_tax.category_code == category
        for ac in m.settlement.allowance_charge or []
    )


def _seller_predicate_vat_local_or_taxrep(m: _trade.Trade) -> bool:
    """Seller has VAT id, local tax id, or tax representative has VAT id.

    Applies to families AE / E / IG / IP / S / Z.
    """
    return _has_vat_or_local_tax_id(m.agreement.seller) or _has_vat_id(
        m.agreement.seller_tax_representative_party
    )


def _seller_predicate_vat_or_taxrep(m: _trade.Trade) -> bool:
    """Seller has VAT id, or tax representative has VAT id.

    Applies to families G / IC. ``BT-32`` (local tax id) is *not*
    sufficient.
    """
    return _has_vat_id(m.agreement.seller) or _has_vat_id(
        m.agreement.seller_tax_representative_party
    )


def _buyer_predicate_vat_or_legal(m: _trade.Trade) -> bool:
    """Buyer has VAT id or legal registration id. Applies to AE."""
    return _has_vat_id(m.agreement.buyer) or _has_buyer_legal_id(m.agreement.buyer)


def _err(code: str, message: str) -> ValidationError:
    """Build a ValidationError whose message is prefixed with the BR id."""
    return ValidationError(code, f"{code}: {message}")


_AE_MSG = (
    "VAT category 'Reverse charge' (AE) requires a Seller VAT id "
    "(BT-31), Seller tax registration id (BT-32) and/or "
    "tax-representative VAT id (BT-63), plus a Buyer VAT id "
    "(BT-48) and/or Buyer legal registration id (BT-47)."
)
_E_MSG = (
    "VAT category 'Exempt from VAT' (E) requires a Seller VAT id "
    "(BT-31), Seller tax registration id (BT-32) and/or "
    "tax-representative VAT id (BT-63)."
)
_G_MSG = (
    "VAT category 'Export outside the EU' (G) requires a Seller "
    "VAT id (BT-31) or tax-representative VAT id (BT-63). The "
    "local tax id (BT-32) is *not* sufficient."
)
_IC_MSG = (
    "VAT category 'Intra-community supply' (K) requires a Seller "
    "VAT id (BT-31) or tax-representative VAT id (BT-63), plus a "
    "Buyer VAT id (BT-48)."
)
_AF_MSG = (
    "VAT category 'IGIC' (L, Canary Islands) requires a Seller "
    "VAT id (BT-31), Seller tax registration id (BT-32) and/or "
    "tax-representative VAT id (BT-63)."
)
_AG_MSG = (
    "VAT category 'IPSI' (M, Ceuta/Melilla) requires a Seller "
    "VAT id (BT-31), Seller tax registration id (BT-32) and/or "
    "tax-representative VAT id (BT-63)."
)
_S_MSG = (
    "VAT category 'Standard rated' (S) requires a Seller VAT id "
    "(BT-31), Seller tax registration id (BT-32) and/or "
    "tax-representative VAT id (BT-63)."
)
_Z_MSG = (
    "VAT category 'Zero rated' (Z) requires a Seller VAT id "
    "(BT-31), Seller tax registration id (BT-32) and/or "
    "tax-representative VAT id (BT-63)."
)


# --- AE -- Reverse charge ---------------------------------------------------


def br_ae_2(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-AE-2: when any line carries VAT category 'Reverse charge'
    (AE), the seller side must show a VAT id (BT-31), tax
    registration id (BT-32) and/or tax-representative VAT id
    (BT-63), and the buyer side a VAT id (BT-48) and/or legal
    registration id (BT-47)."""
    if _seller_predicate_vat_local_or_taxrep(m) and _buyer_predicate_vat_or_legal(m):
        return []
    if not _line_has_category(m, CategoryCode.T_AE):
        return []
    return [_err("BR-AE-2", _AE_MSG)]


def br_ae_3(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-AE-3: same identifier requirement as BR-AE-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_local_or_taxrep(m) and _buyer_predicate_vat_or_legal(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_AE):
        return []
    return [_err("BR-AE-3", _AE_MSG)]


def br_ae_4(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-AE-4: same identifier requirement as BR-AE-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_local_or_taxrep(m) and _buyer_predicate_vat_or_legal(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_AE):
        return []
    return [_err("BR-AE-4", _AE_MSG)]


# --- E -- Exempt from VAT ---------------------------------------------------


def br_e_2(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-E-2: when any line carries VAT category 'Exempt from VAT'
    (E), the seller side must show a VAT id (BT-31), tax
    registration id (BT-32) and/or tax-representative VAT id
    (BT-63)."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _line_has_category(m, CategoryCode.T_E):
        return []
    return [_err("BR-E-2", _E_MSG)]


def br_e_3(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-E-3: same identifier requirement as BR-E-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_E):
        return []
    return [_err("BR-E-3", _E_MSG)]


def br_e_4(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-E-4: same identifier requirement as BR-E-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_E):
        return []
    return [_err("BR-E-4", _E_MSG)]


# --- G -- Export outside the EU --------------------------------------------


def br_g_2(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-G-2: when any line carries VAT category 'Export outside the
    EU' (G), a Seller VAT id (BT-31) or tax-representative VAT id
    (BT-63) must be present."""
    if _seller_predicate_vat_or_taxrep(m):
        return []
    if not _line_has_category(m, CategoryCode.T_G):
        return []
    return [_err("BR-G-2", _G_MSG)]


def br_g_3(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-G-3: same identifier requirement as BR-G-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_or_taxrep(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_G):
        return []
    return [_err("BR-G-3", _G_MSG)]


def br_g_4(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-G-4: same identifier requirement as BR-G-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_or_taxrep(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_G):
        return []
    return [_err("BR-G-4", _G_MSG)]


# --- IC -- Intra-community supply (category code K) -------------------------


def br_ic_2(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-IC-2: when any line carries VAT category 'Intra-community
    supply' (K), a Seller VAT id (BT-31) or tax-representative VAT
    id (BT-63) must be present, plus a Buyer VAT id (BT-48)."""
    if _seller_predicate_vat_or_taxrep(m) and _has_vat_id(m.agreement.buyer):
        return []
    if not _line_has_category(m, CategoryCode.T_K):
        return []
    return [_err("BR-IC-2", _IC_MSG)]


def br_ic_3(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-IC-3: same identifier requirement as BR-IC-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_or_taxrep(m) and _has_vat_id(m.agreement.buyer):
        return []
    if not _alw_has_category(m, CategoryCode.T_K):
        return []
    return [_err("BR-IC-3", _IC_MSG)]


def br_ic_4(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-IC-4: same identifier requirement as BR-IC-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_or_taxrep(m) and _has_vat_id(m.agreement.buyer):
        return []
    if not _chg_has_category(m, CategoryCode.T_K):
        return []
    return [_err("BR-IC-4", _IC_MSG)]


# --- AF -- IGIC (category code L, Canary Islands) ---------------------------


def br_af_2(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-AF-2: when any line carries VAT category 'IGIC' (L), the
    seller side must show a VAT id (BT-31), tax registration id
    (BT-32) and/or tax-representative VAT id (BT-63)."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _line_has_category(m, CategoryCode.T_L):
        return []
    return [_err("BR-AF-2", _AF_MSG)]


def br_af_3(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-AF-3: same identifier requirement as BR-AF-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_L):
        return []
    return [_err("BR-AF-3", _AF_MSG)]


def br_af_4(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-AF-4: same identifier requirement as BR-AF-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_L):
        return []
    return [_err("BR-AF-4", _AF_MSG)]


# --- AG -- IPSI (category code M, Ceuta/Melilla) ----------------------------


def br_ag_2(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-AG-2: when any line carries VAT category 'IPSI' (M), the
    seller side must show a VAT id (BT-31), tax registration id
    (BT-32) and/or tax-representative VAT id (BT-63)."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _line_has_category(m, CategoryCode.T_M):
        return []
    return [_err("BR-AG-2", _AG_MSG)]


def br_ag_3(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-AG-3: same identifier requirement as BR-AG-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_M):
        return []
    return [_err("BR-AG-3", _AG_MSG)]


def br_ag_4(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-AG-4: same identifier requirement as BR-AG-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_M):
        return []
    return [_err("BR-AG-4", _AG_MSG)]


# --- S -- Standard rated ----------------------------------------------------


def br_s_2(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-S-2: when any line carries VAT category 'Standard rated'
    (S), the seller side must show a VAT id (BT-31), tax
    registration id (BT-32) and/or tax-representative VAT id
    (BT-63)."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _line_has_category(m, CategoryCode.T_S):
        return []
    return [_err("BR-S-2", _S_MSG)]


def br_s_3(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-S-3: same identifier requirement as BR-S-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_S):
        return []
    return [_err("BR-S-3", _S_MSG)]


def br_s_4(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-S-4: same identifier requirement as BR-S-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_S):
        return []
    return [_err("BR-S-4", _S_MSG)]


# --- Z -- Zero rated --------------------------------------------------------


def br_z_2(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-Z-2: when any line carries VAT category 'Zero rated' (Z),
    the seller side must show a VAT id (BT-31), tax registration id
    (BT-32) and/or tax-representative VAT id (BT-63)."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _line_has_category(m, CategoryCode.T_Z):
        return []
    return [_err("BR-Z-2", _Z_MSG)]


def br_z_3(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-Z-3: same identifier requirement as BR-Z-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_Z):
        return []
    return [_err("BR-Z-3", _Z_MSG)]


def br_z_4(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-Z-4: same identifier requirement as BR-Z-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_Z):
        return []
    return [_err("BR-Z-4", _Z_MSG)]


# --- O -- Not subject to VAT (inverted predicates) --------------------------


def br_o_2(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-O-2: a line with VAT category 'Not subject to VAT' (O)
    forbids the Seller VAT id (BT-31), the tax-representative VAT id
    (BT-63) and the Buyer id (BT-46) on the invoice."""
    if not _line_has_category(m, CategoryCode.T_O):
        return []
    forbidden = (
        _has_vat_id(m.agreement.seller)
        or _has_vat_id(m.agreement.seller_tax_representative_party)
        or m.agreement.buyer.id is not None
    )
    if not forbidden:
        return []
    return [
        _err(
            "BR-O-2",
            "A line carries VAT category 'Not subject to VAT' (O), "
            "which forbids a Seller VAT id (BT-31), a "
            "tax-representative VAT id (BT-63) and a Buyer id "
            "(BT-46) — at least one of those is present.",
        )
    ]


def br_o_3(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-O-3: a document-level allowance with VAT category 'Not
    subject to VAT' (O) forbids the Seller VAT id (BT-31), the
    tax-representative VAT id (BT-63) and also the Buyer VAT id
    (BT-48) on the invoice."""
    if not _alw_has_category(m, CategoryCode.T_O):
        return []
    forbidden = (
        _has_vat_id(m.agreement.seller)
        or _has_vat_id(m.agreement.seller_tax_representative_party)
        or _has_vat_id(m.agreement.buyer)
    )
    if not forbidden:
        return []
    return [
        _err(
            "BR-O-3",
            "A document-level allowance carries VAT category 'Not "
            "subject to VAT' (O), which forbids a Seller VAT id "
            "(BT-31), a tax-representative VAT id (BT-63) and a "
            "Buyer VAT id (BT-48) — at least one of those is present.",
        )
    ]


def br_o_4(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-O-4: a document-level charge with VAT category 'Not subject
    to VAT' (O) forbids the Seller VAT id (BT-31), the
    tax-representative VAT id (BT-63) and also the Buyer VAT id
    (BT-48) on the invoice."""
    if not _chg_has_category(m, CategoryCode.T_O):
        return []
    forbidden = (
        _has_vat_id(m.agreement.seller)
        or _has_vat_id(m.agreement.seller_tax_representative_party)
        or _has_vat_id(m.agreement.buyer)
    )
    if not forbidden:
        return []
    return [
        _err(
            "BR-O-4",
            "A document-level charge carries VAT category 'Not "
            "subject to VAT' (O), which forbids a Seller VAT id "
            "(BT-31), a tax-representative VAT id (BT-63) and a "
            "Buyer VAT id (BT-48) — at least one of those is present.",
        )
    ]


# ---------------------------------------------------------------------------
# Intra-community supply — supplementary rules
# ---------------------------------------------------------------------------


def _ic_in_use(m: _trade.Trade) -> bool:
    """Any header BG-23 row or line item or document-level
    allowance/charge carries category 'Intra-community supply' (K)."""
    if _line_has_category(m, CategoryCode.T_K):
        return True
    return any(
        ac.category_trade_tax is not None
        and ac.category_trade_tax.category_code == CategoryCode.T_K
        for ac in m.settlement.allowance_charge or []
    )


def br_ic_11(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-IC-11: an intra-community supply (K) needs a date anchor —
    either an actual delivery date (BT-72) or an invoicing period
    (BG-14)."""
    if not _ic_in_use(m):
        return []
    event = m.delivery.event
    has_delivery_date = event is not None and event.occurrence is not None
    period = m.settlement.billing_period
    has_period = period is not None and (
        period.start is not None or period.end is not None
    )
    if has_delivery_date or has_period:
        return []
    return [
        _err(
            "BR-IC-11",
            "Intra-community supply (K) in use, but neither an "
            "actual delivery date (BT-72) nor an invoicing period "
            "(BG-14) is given.",
        )
    ]


def br_ic_12(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-IC-12: an intra-community supply (K) needs the deliver-to
    country code (BT-80)."""
    if not _ic_in_use(m):
        return []
    ship_to = m.delivery.ship_to
    has_ship_to_country = (
        ship_to is not None
        and ship_to.address is not None
        and bool(ship_to.address.country_id)
    )
    if has_ship_to_country:
        return []
    return [
        _err(
            "BR-IC-12",
            "Intra-community supply (K) in use, but the deliver-to "
            "country code (BT-80) is missing.",
        )
    ]


# ---------------------------------------------------------------------------
# 'Not subject to VAT' single-rate restriction
# ---------------------------------------------------------------------------


def _has_o_breakdown_row(m: _trade.Trade) -> bool:
    return any(
        t.category_code == CategoryCode.T_O for t in m.settlement.trade_taxes or []
    )


def br_o_11(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-O-11: a 'Not subject to VAT' (O) breakdown row excludes
    every other VAT breakdown row (BG-23) — 'O' stands alone."""
    if not _has_o_breakdown_row(m):
        return []
    trade_taxes = m.settlement.trade_taxes or []
    if not any(t.category_code != CategoryCode.T_O for t in trade_taxes):
        return []
    return [
        _err(
            "BR-O-11",
            "A 'Not subject to VAT' (O) breakdown row coexists with "
            "rows of other categories — 'O' must stand alone.",
        )
    ]


def br_o_12(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-O-12: with a 'Not subject to VAT' (O) breakdown row present,
    every invoice line must itself carry category 'O'."""
    if not _has_o_breakdown_row(m):
        return []
    if not any(
        item.settlement.applicable_trade_tax is not None
        and item.settlement.applicable_trade_tax.category_code != CategoryCode.T_O
        for item in m.items
    ):
        return []
    return [
        _err(
            "BR-O-12",
            "A 'Not subject to VAT' (O) breakdown row coexists with "
            "an invoice line of another VAT category.",
        )
    ]


def br_o_13(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-O-13: with a 'Not subject to VAT' (O) breakdown row present,
    every document-level allowance (BG-20) must itself carry
    category 'O'."""
    if not _has_o_breakdown_row(m):
        return []
    if not any(
        not ac.indicator
        and ac.category_trade_tax is not None
        and ac.category_trade_tax.category_code != CategoryCode.T_O
        for ac in m.settlement.allowance_charge or []
    ):
        return []
    return [
        _err(
            "BR-O-13",
            "A 'Not subject to VAT' (O) breakdown row coexists with "
            "a document-level allowance of another VAT category.",
        )
    ]


def br_o_14(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-O-14: with a 'Not subject to VAT' (O) breakdown row present,
    every document-level charge (BG-21) must itself carry category
    'O'."""
    if not _has_o_breakdown_row(m):
        return []
    if not any(
        ac.indicator
        and ac.category_trade_tax is not None
        and ac.category_trade_tax.category_code != CategoryCode.T_O
        for ac in m.settlement.allowance_charge or []
    ):
        return []
    return [
        _err(
            "BR-O-14",
            "A 'Not subject to VAT' (O) breakdown row coexists with "
            "a document-level charge of another VAT category.",
        )
    ]


# ---------------------------------------------------------------------------
# Document-level rules
# ---------------------------------------------------------------------------


def br_16(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-16: the invoice must carry one or more invoice lines (BG-25).

    Applies: BASIC+ (line items first appear at BASIC).
    """
    if profile <= Profile.BASIC_WL:
        return []
    if m.items:
        return []
    return [
        ValidationError(
            "BR-16", "The invoice has no lines (BG-25) — one or more are required."
        )
    ]


def br_co_10(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-CO-10: BT-106 must equal the individual line net amounts
    (BT-131) added up.

    Applies: BASIC+ except EXTENDED. At EXTENDED ``BR-FXEXT-CO-10``
    replaces this with a tolerance-banded variant that also excludes
    ``GROUP`` / ``INFORMATION`` lines from the sum. ``BT-106`` is
    getafix-optional (MINIMUM doesn't have it) — the check is
    skipped when it's absent or when there are no line items
    (``BR-16`` covers that case).
    """
    if profile >= Profile.EXTENDED:
        return []
    if not m.items:
        return []
    summation = m.settlement.monetary_summation
    if summation.line_total is None:
        return []
    sum_line_totals = sum(
        (
            item.settlement.monetary_summation.line_total
            for item in m.items
            if item.settlement.monetary_summation.line_total is not None
        ),
        Decimal("0"),
    )
    if summation.line_total == sum_line_totals:
        return []
    return [
        ValidationError(
            "BR-CO-10",
            f"BT-106 = {summation.line_total} differs from "
            f"sum(BT-131) = {sum_line_totals}.",
        )
    ]


def br_co_11(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-CO-11: BT-107 must equal the individual BT-92 allowance
    amounts added up.

    Applies: BASIC_WL+ except EXTENDED. At EXTENDED ``BR-FXEXT-CO-11``
    replaces this with a tolerance-banded variant. Skipped when
    BT-107 is absent.
    """
    if profile >= Profile.EXTENDED:
        return []
    summation = m.settlement.monetary_summation
    if summation.allowance_total is None:
        return []
    sum_allowances = sum(
        (
            ac.actual_amount
            for ac in (m.settlement.allowance_charge or [])
            if not ac.indicator
        ),
        Decimal("0"),
    )
    if summation.allowance_total == sum_allowances:
        return []
    return [
        ValidationError(
            "BR-CO-11",
            f"BT-107 = {summation.allowance_total} differs from "
            f"sum(BT-92) = {sum_allowances}.",
        )
    ]


def br_co_12(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-CO-12: BT-108 must equal the individual BT-99 charge
    amounts added up.

    Applies: BASIC_WL+ except EXTENDED. At EXTENDED
    ``BR-FXEXT-CO-12`` replaces this with a tolerance-banded variant
    that also folds ``Σ BT-X-272`` (logistics service fees) into the
    sum. Skipped when BT-108 is absent.
    """
    if profile >= Profile.EXTENDED:
        return []
    summation = m.settlement.monetary_summation
    if summation.charge_total is None:
        return []
    sum_charges = sum(
        (
            ac.actual_amount
            for ac in (m.settlement.allowance_charge or [])
            if ac.indicator
        ),
        Decimal("0"),
    )
    if summation.charge_total == sum_charges:
        return []
    return [
        ValidationError(
            "BR-CO-12",
            f"BT-108 = {summation.charge_total} differs from "
            f"sum(BT-99) = {sum_charges}.",
        )
    ]


def br_co_13(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-CO-13: BT-109 must equal sum(BT-131) - sum(BT-92) +
    sum(BT-99) — the net total derives from the line amounts less
    document-level allowances plus document-level charges.

    Applies: BASIC+ except EXTENDED. At EXTENDED ``BR-FXEXT-CO-13``
    replaces this with a tolerance-banded variant that excludes
    ``GROUP`` / ``INFORMATION`` lines. (BT-X-272 deliberately does
    NOT enter the EXTENDED identity — logistics fees flow into
    BT-108 and are checked separately by ``BR-FXEXT-CO-12``.) The
    check applies only where line items exist (the line-totals sum
    is only meaningful then).
    """
    if profile >= Profile.EXTENDED:
        return []
    if not m.items:
        return []
    summation = m.settlement.monetary_summation
    sum_line_totals = sum(
        (
            item.settlement.monetary_summation.line_total
            for item in m.items
            if item.settlement.monetary_summation.line_total is not None
        ),
        Decimal("0"),
    )
    sum_allowances = sum(
        (
            ac.actual_amount
            for ac in (m.settlement.allowance_charge or [])
            if not ac.indicator
        ),
        Decimal("0"),
    )
    sum_charges = sum(
        (
            ac.actual_amount
            for ac in (m.settlement.allowance_charge or [])
            if ac.indicator
        ),
        Decimal("0"),
    )
    expected_basis = sum_line_totals - sum_allowances + sum_charges
    if summation.tax_basis_total == expected_basis:
        return []
    return [
        ValidationError(
            "BR-CO-13",
            f"BT-109 = {summation.tax_basis_total} differs from "
            f"sum(BT-131) - sum(BT-92) + sum(BT-99) = "
            f"{sum_line_totals} - {sum_allowances} + "
            f"{sum_charges} = {expected_basis}.",
        )
    ]


def br_co_21(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-CO-21: every document-level allowance (BG-20) must state
    its reason — as text (BT-97), code (BT-98), or both.

    Emits one ValidationError per offending allowance.
    """
    errors: list[ValidationError] = []
    for ac in m.settlement.allowance_charge or []:
        if ac.indicator:
            continue
        if ac.reason is None and ac.reason_code is None:
            errors.append(
                ValidationError(
                    "BR-CO-21",
                    "Document-level allowance (BG-20) gives no reason "
                    "text (BT-97) or reason code (BT-98).",
                )
            )
    return errors


def br_co_22(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-CO-22: every document-level charge (BG-21) must state its
    reason — as text (BT-104), code (BT-105), or both.

    Emits one ValidationError per offending charge.
    """
    errors: list[ValidationError] = []
    for ac in m.settlement.allowance_charge or []:
        if not ac.indicator:
            continue
        if ac.reason is None and ac.reason_code is None:
            errors.append(
                ValidationError(
                    "BR-CO-22",
                    "Document-level charge (BG-21) gives no reason "
                    "text (BT-104) or reason code (BT-105).",
                )
            )
    return errors


def br_co_23(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-CO-23: every line allowance (BG-27) must state its reason —
    as text (BT-139), code (BT-140), or both.

    Emits one ValidationError per offending line allowance.
    """
    errors: list[ValidationError] = []
    for item in m.items:
        for ac in item.settlement.allowance_charge or []:
            if ac.indicator:
                continue
            if ac.reason is None and ac.reason_code is None:
                errors.append(
                    ValidationError(
                        "BR-CO-23",
                        "Invoice line allowance (BG-27) gives no reason "
                        "text (BT-139) or reason code (BT-140).",
                    )
                )
    return errors


def br_co_24(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-CO-24: every line charge (BG-28) must state its reason — as
    text (BT-144), code (BT-145), or both.

    Emits one ValidationError per offending line charge.
    """
    errors: list[ValidationError] = []
    for item in m.items:
        for ac in item.settlement.allowance_charge or []:
            if not ac.indicator:
                continue
            if ac.reason is None and ac.reason_code is None:
                errors.append(
                    ValidationError(
                        "BR-CO-24",
                        "Invoice line charge (BG-28) gives no reason "
                        "text (BT-144) or reason code (BT-145).",
                    )
                )
    return errors


# ---------------------------------------------------------------------------
# Per-VAT-category rate constraints — BR-X-5 / BR-X-6 / BR-X-7
# ---------------------------------------------------------------------------
#
# Each VAT category code constrains the VAT rate carried on
# (a) every invoice line (BT-152) — BR-X-5,
# (b) every document-level allowance (BT-96) — BR-X-6, and
# (c) every document-level charge (BT-103) — BR-X-7.
#
# Predicates per category, lifted from the EN16931 Technical Appendix
# pp. 62-74:

_RatePredicate = Callable[[Decimal | None], bool]

_VAT_RATE_PREDICATES: dict[CategoryCode, tuple[_RatePredicate, str]] = {
    CategoryCode.T_S: (lambda r: r is not None and r > 0, "must be above zero"),
    CategoryCode.T_Z: (lambda r: r == 0, "must be exactly zero"),
    CategoryCode.T_E: (lambda r: r == 0, "must be exactly zero"),
    CategoryCode.T_AE: (lambda r: r == 0, "must be exactly zero"),
    CategoryCode.T_G: (lambda r: r == 0, "must be exactly zero"),
    CategoryCode.T_K: (lambda r: r == 0, "must be exactly zero"),
    CategoryCode.T_L: (lambda r: r is not None and r >= 0, "must be zero or above"),
    CategoryCode.T_M: (lambda r: r is not None and r >= 0, "must be zero or above"),
    CategoryCode.T_O: (lambda r: r is None, "must be omitted"),
}

_VAT_RULE_PREFIX: dict[CategoryCode, str] = {
    CategoryCode.T_S: "S",
    CategoryCode.T_Z: "Z",
    CategoryCode.T_E: "E",
    CategoryCode.T_AE: "AE",
    CategoryCode.T_G: "G",
    CategoryCode.T_K: "IC",
    CategoryCode.T_L: "AF",
    CategoryCode.T_M: "AG",
    CategoryCode.T_O: "O",
}


def _vat_rate_violation_code(category: CategoryCode, suffix: str) -> str:
    return f"BR-{_VAT_RULE_PREFIX[category]}-{suffix}"


def _check_rate(category: CategoryCode, rate: Decimal | None) -> str | None:
    """Return the failure description if ``rate`` violates the category's
    predicate; otherwise ``None``."""
    predicate, description = _VAT_RATE_PREDICATES[category]
    if predicate(rate):
        return None
    return description


_VAT_EXEMPTION_REQUIRES: frozenset[CategoryCode] = frozenset(
    {
        CategoryCode.T_E,
        CategoryCode.T_AE,
        CategoryCode.T_G,
        CategoryCode.T_K,
        CategoryCode.T_O,
    }
)

_VAT_EXEMPTION_FORBIDS: frozenset[CategoryCode] = frozenset(
    {CategoryCode.T_S, CategoryCode.T_Z, CategoryCode.T_L, CategoryCode.T_M}
)


def vat_category_exemption_reason(
    m: _trade.Trade, _profile: Profile
) -> list[ValidationError]:
    """BR-X-10 — per-VAT-category exemption-reason constraint on
    every header VAT breakdown row (BG-23).

    Categories that levy VAT (S, Z, IG, IP) must NOT carry an
    exemption reason text (BT-120) or code (BT-121). Categories that
    do not levy VAT (E, AE, G, IC, O) MUST carry at least one of
    them — both text and code are also acceptable.
    """
    errors: list[ValidationError] = []
    for tt in m.settlement.trade_taxes or []:
        cat = tt.category_code
        has_text = tt.exemption_reason is not None
        has_code = tt.exemption_reason_code is not None
        if cat in _VAT_EXEMPTION_FORBIDS and (has_text or has_code):
            errors.append(
                _err(
                    _vat_rate_violation_code(cat, "10"),
                    f"VAT breakdown with category {cat.value!r} must "
                    "not carry an exemption reason — neither as text "
                    "(BT-120) nor as code (BT-121).",
                )
            )
        if cat in _VAT_EXEMPTION_REQUIRES and not (has_text or has_code):
            errors.append(
                _err(
                    _vat_rate_violation_code(cat, "10"),
                    f"VAT breakdown with category {cat.value!r} must "
                    "carry an exemption reason — as text (BT-120), "
                    "code (BT-121), or both.",
                )
            )
    return errors


def vat_category_rates(m: _trade.Trade, _profile: Profile) -> list[ValidationError]:
    """BR-X-5 / BR-X-6 / BR-X-7 — per-VAT-category rate constraints.

    One dispatch covers all nine categories (S, Z, E, AE, G, IC, IG, IP,
    O) at three placements (line / doc allowance / doc charge). Emits
    distinct error codes per (category, placement).
    """
    errors: list[ValidationError] = []

    # BR-X-5 — line-level (BT-151 / BT-152). Lines without line VAT
    # (EXTENDED GROUP / INFORMATION) carry no category to check.
    for idx, item in enumerate(m.items):
        att = item.settlement.applicable_trade_tax
        if att is None:
            continue
        cat = att.category_code
        rate = att.rate_applicable_percent
        description = _check_rate(cat, rate)
        if description is not None:
            errors.append(
                _err(
                    _vat_rate_violation_code(cat, "5"),
                    f"line {idx + 1}: VAT category {cat.value!r} "
                    f"rate (BT-152) {description}.",
                )
            )

    # BR-X-6 / BR-X-7 — document-level allowance (BT-95 / BT-96) and
    # charge (BT-102 / BT-103).
    for ac in m.settlement.allowance_charge or []:
        ctt = ac.category_trade_tax
        if ctt is None:
            continue
        cat = ctt.category_code
        description = _check_rate(cat, ctt.rate_applicable_percent)
        if description is None:
            continue
        suffix = "7" if ac.indicator else "6"
        level = "charge" if ac.indicator else "allowance"
        bt = "BT-103" if ac.indicator else "BT-96"
        errors.append(
            _err(
                _vat_rate_violation_code(cat, suffix),
                f"document-level {level}: VAT category "
                f"{cat.value!r} rate ({bt}) {description}.",
            )
        )

    return errors
