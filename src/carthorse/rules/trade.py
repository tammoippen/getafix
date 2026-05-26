"""Validators for :mod:`carthorse.schema.trade`.

Cross-sibling rules: every check that needs to read across line items,
header allowances/charges, the monetary summation and the agreement
parties in one pass. The signatures match
:data:`carthorse.rules.Validator`.

Each function:

* self-gates on profile and on the precondition data;
* returns ``list[ValidationError]`` (empty on success);
* never raises.

Most family / single-rate rules emit at most one ``ValidationError``
per call (the original implementation deduplicated by rule code).
``br_co_21..24`` retain their per-occurrence semantics — one error
per offending allowance / charge.

See ``docs/VALIDATOR_REFACTOR.md`` for the rework plan.
"""

# pyright: reportImportCycles=false

from __future__ import annotations

from collections.abc import Callable, Iterator
from decimal import Decimal
from typing import TYPE_CHECKING

from carthorse.schema.element import ValidationError
from carthorse.schema.types import CategoryCode, Profile

if TYPE_CHECKING:
    from carthorse.schema import trade as _trade
    from carthorse.schema.party import BuyerTradeParty, SpecifiedTaxRegistration


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
# Each function emits at most one ValidationError (the original
# implementation deduplicated by rule code).
# ---------------------------------------------------------------------------


def _line_has_category(m: _trade.Trade, category: CategoryCode) -> bool:
    return any(
        item.settlement.applicable_trade_tax.category_code == category
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
    """Build a ValidationError with the BR id stamped into the message
    (preserves the original ``Trade._validate_*`` formatting)."""
    return ValidationError(code, f"{code}: {message}")


_AE_MSG = (
    "VAT category 'Reverse charge' (AE) requires the Seller "
    "VAT identifier (BT-31), the Seller tax registration "
    "identifier (BT-32) and/or the Seller tax representative "
    "VAT identifier (BT-63), and the Buyer VAT identifier "
    "(BT-48) and/or the Buyer legal registration identifier "
    "(BT-47)."
)
_E_MSG = (
    "VAT category 'Exempt from VAT' (E) requires the Seller "
    "VAT identifier (BT-31), the Seller tax registration "
    "identifier (BT-32) and/or the Seller tax representative "
    "VAT identifier (BT-63)."
)
_G_MSG = (
    "VAT category 'Export outside the EU' (G) requires the "
    "Seller VAT identifier (BT-31) or the Seller tax "
    "representative VAT identifier (BT-63). The local tax "
    "identifier (BT-32) is *not* sufficient."
)
_IC_MSG = (
    "VAT category 'Intra-community supply' (K) requires the "
    "Seller VAT identifier (BT-31) or the Seller tax "
    "representative VAT identifier (BT-63), and the Buyer VAT "
    "identifier (BT-48)."
)
_AF_MSG = (
    "VAT category 'IGIC' (L, Canary Islands) requires the "
    "Seller VAT identifier (BT-31), the Seller tax registration "
    "identifier (BT-32) and/or the Seller tax representative "
    "VAT identifier (BT-63)."
)
_AG_MSG = (
    "VAT category 'IPSI' (M, Ceuta/Melilla) requires the "
    "Seller VAT identifier (BT-31), the Seller tax registration "
    "identifier (BT-32) and/or the Seller tax representative "
    "VAT identifier (BT-63)."
)
_S_MSG = (
    "VAT category 'Standard rated' (S) requires the Seller "
    "VAT identifier (BT-31), the Seller tax registration "
    "identifier (BT-32) and/or the Seller tax representative "
    "VAT identifier (BT-63)."
)
_Z_MSG = (
    "VAT category 'Zero rated' (Z) requires the Seller VAT "
    "identifier (BT-31), the Seller tax registration identifier "
    "(BT-32) and/or the Seller tax representative VAT "
    "identifier (BT-63)."
)


# --- AE -- Reverse charge ---------------------------------------------------


def br_ae_2(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-AE-2: An Invoice that contains an Invoice line, a Document level
    allowance or a Document level charge where the VAT category code is
    'Reverse charge' (AE) shall contain the Seller VAT Identifier (BT-31),
    the Seller tax registration identifier (BT-32) and/or the Seller tax
    representative VAT identifier (BT-63), and the Buyer VAT identifier
    (BT-48) and/or the Buyer legal registration identifier (BT-47)."""
    if _seller_predicate_vat_local_or_taxrep(m) and _buyer_predicate_vat_or_legal(m):
        return []
    if not _line_has_category(m, CategoryCode.T_AE):
        return []
    return [_err("BR-AE-2", _AE_MSG)]


def br_ae_3(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-AE-3: same identifier requirement as BR-AE-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_local_or_taxrep(m) and _buyer_predicate_vat_or_legal(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_AE):
        return []
    return [_err("BR-AE-3", _AE_MSG)]


def br_ae_4(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-AE-4: same identifier requirement as BR-AE-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_local_or_taxrep(m) and _buyer_predicate_vat_or_legal(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_AE):
        return []
    return [_err("BR-AE-4", _AE_MSG)]


# --- E -- Exempt from VAT ---------------------------------------------------


def br_e_2(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-E-2: An Invoice that contains an Invoice line where the VAT
    category code is 'Exempt from VAT' (E) shall contain the Seller VAT
    Identifier (BT-31), the Seller tax registration identifier (BT-32)
    and/or the Seller tax representative VAT identifier (BT-63)."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _line_has_category(m, CategoryCode.T_E):
        return []
    return [_err("BR-E-2", _E_MSG)]


def br_e_3(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-E-3: same identifier requirement as BR-E-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_E):
        return []
    return [_err("BR-E-3", _E_MSG)]


def br_e_4(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-E-4: same identifier requirement as BR-E-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_E):
        return []
    return [_err("BR-E-4", _E_MSG)]


# --- G -- Export outside the EU --------------------------------------------


def br_g_2(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-G-2: An Invoice that contains an Invoice line where the VAT
    category code is 'Export outside the EU' (G) shall contain the
    Seller VAT identifier (BT-31) or the Seller tax representative VAT
    identifier (BT-63)."""
    if _seller_predicate_vat_or_taxrep(m):
        return []
    if not _line_has_category(m, CategoryCode.T_G):
        return []
    return [_err("BR-G-2", _G_MSG)]


def br_g_3(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-G-3: same identifier requirement as BR-G-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_or_taxrep(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_G):
        return []
    return [_err("BR-G-3", _G_MSG)]


def br_g_4(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-G-4: same identifier requirement as BR-G-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_or_taxrep(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_G):
        return []
    return [_err("BR-G-4", _G_MSG)]


# --- IC -- Intra-community supply (category code K) -------------------------


def br_ic_2(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-IC-2: An Invoice that contains an Invoice line where the VAT
    category code is 'Intra-community supply' (K) shall contain the
    Seller VAT identifier (BT-31) or the Seller tax representative VAT
    identifier (BT-63), and the Buyer VAT identifier (BT-48)."""
    if _seller_predicate_vat_or_taxrep(m) and _has_vat_id(m.agreement.buyer):
        return []
    if not _line_has_category(m, CategoryCode.T_K):
        return []
    return [_err("BR-IC-2", _IC_MSG)]


def br_ic_3(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-IC-3: same identifier requirement as BR-IC-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_or_taxrep(m) and _has_vat_id(m.agreement.buyer):
        return []
    if not _alw_has_category(m, CategoryCode.T_K):
        return []
    return [_err("BR-IC-3", _IC_MSG)]


def br_ic_4(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-IC-4: same identifier requirement as BR-IC-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_or_taxrep(m) and _has_vat_id(m.agreement.buyer):
        return []
    if not _chg_has_category(m, CategoryCode.T_K):
        return []
    return [_err("BR-IC-4", _IC_MSG)]


# --- AF -- IGIC (category code L, Canary Islands) ---------------------------


def br_af_2(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-AF-2: An Invoice that contains an Invoice line where the VAT
    category code is 'IGIC' (L) shall contain the Seller VAT Identifier
    (BT-31), the Seller tax registration identifier (BT-32) and/or the
    Seller tax representative VAT identifier (BT-63)."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _line_has_category(m, CategoryCode.T_L):
        return []
    return [_err("BR-AF-2", _AF_MSG)]


def br_af_3(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-AF-3: same identifier requirement as BR-AF-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_L):
        return []
    return [_err("BR-AF-3", _AF_MSG)]


def br_af_4(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-AF-4: same identifier requirement as BR-AF-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_L):
        return []
    return [_err("BR-AF-4", _AF_MSG)]


# --- AG -- IPSI (category code M, Ceuta/Melilla) ----------------------------


def br_ag_2(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-AG-2: An Invoice that contains an Invoice line where the VAT
    category code is 'IPSI' (M) shall contain the Seller VAT Identifier
    (BT-31), the Seller tax registration identifier (BT-32) and/or the
    Seller tax representative VAT identifier (BT-63)."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _line_has_category(m, CategoryCode.T_M):
        return []
    return [_err("BR-AG-2", _AG_MSG)]


def br_ag_3(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-AG-3: same identifier requirement as BR-AG-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_M):
        return []
    return [_err("BR-AG-3", _AG_MSG)]


def br_ag_4(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-AG-4: same identifier requirement as BR-AG-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_M):
        return []
    return [_err("BR-AG-4", _AG_MSG)]


# --- S -- Standard rated ----------------------------------------------------


def br_s_2(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-S-2: An Invoice that contains an Invoice line where the VAT
    category code is 'Standard rated' (S) shall contain the Seller VAT
    Identifier (BT-31), the Seller tax registration identifier (BT-32)
    and/or the Seller tax representative VAT identifier (BT-63)."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _line_has_category(m, CategoryCode.T_S):
        return []
    return [_err("BR-S-2", _S_MSG)]


def br_s_3(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-S-3: same identifier requirement as BR-S-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_S):
        return []
    return [_err("BR-S-3", _S_MSG)]


def br_s_4(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-S-4: same identifier requirement as BR-S-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_S):
        return []
    return [_err("BR-S-4", _S_MSG)]


# --- Z -- Zero rated --------------------------------------------------------


def br_z_2(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-Z-2: An Invoice that contains an Invoice line where the VAT
    category code is 'Zero rated' (Z) shall contain the Seller VAT
    Identifier (BT-31), the Seller tax registration identifier (BT-32)
    and/or the Seller tax representative VAT identifier (BT-63)."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _line_has_category(m, CategoryCode.T_Z):
        return []
    return [_err("BR-Z-2", _Z_MSG)]


def br_z_3(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-Z-3: same identifier requirement as BR-Z-2 at the document-level
    allowance (BG-20) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _alw_has_category(m, CategoryCode.T_Z):
        return []
    return [_err("BR-Z-3", _Z_MSG)]


def br_z_4(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-Z-4: same identifier requirement as BR-Z-2 at the document-level
    charge (BG-21) slot."""
    if _seller_predicate_vat_local_or_taxrep(m):
        return []
    if not _chg_has_category(m, CategoryCode.T_Z):
        return []
    return [_err("BR-Z-4", _Z_MSG)]


# --- O -- Not subject to VAT (inverted predicates) --------------------------


def br_o_2(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-O-2: An Invoice that contains an Invoice line where the VAT
    category code is 'Not subject to VAT' (O) shall not contain the
    Seller VAT identifier (BT-31), the Seller tax representative VAT
    identifier (BT-63) or the Buyer identifier (BT-46)."""
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
            "An Invoice line with VAT category 'Not subject to VAT' "
            "(O) shall not contain the Seller VAT identifier "
            "(BT-31), the Seller tax representative VAT identifier "
            "(BT-63) or the Buyer identifier (BT-46).",
        )
    ]


def br_o_3(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-O-3: An Invoice that contains a Document level allowance where
    the VAT category code is 'Not subject to VAT' (O) shall not contain
    the Seller VAT identifier (BT-31), the Seller tax representative VAT
    identifier (BT-63) or the Buyer VAT identifier (BT-48)."""
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
            "A document-level allowance with VAT category 'Not subject "
            "to VAT' (O) shall not contain the Seller VAT identifier "
            "(BT-31), the Seller tax representative VAT identifier "
            "(BT-63) or the Buyer VAT identifier (BT-48).",
        )
    ]


def br_o_4(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-O-4: An Invoice that contains a Document level charge where the
    VAT category code is 'Not subject to VAT' (O) shall not contain the
    Seller VAT identifier (BT-31), the Seller tax representative VAT
    identifier (BT-63) or the Buyer VAT identifier (BT-48)."""
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
            "A document-level charge with VAT category 'Not subject "
            "to VAT' (O) shall not contain the Seller VAT identifier "
            "(BT-31), the Seller tax representative VAT identifier "
            "(BT-63) or the Buyer VAT identifier (BT-48).",
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


def br_ic_11(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-IC-11: An Invoice that contains a VAT breakdown group (BG-23) with
    the VAT category code 'Intra-community supply' (K) shall contain an
    Actual delivery date (BT-72) or an Invoicing period (BG-14)."""
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
            "An Invoice with a VAT breakdown row of category "
            "'Intra-community supply' (K) shall contain the actual "
            "delivery date (BT-72) or the invoicing period (BG-14).",
        )
    ]


def br_ic_12(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-IC-12: An Invoice that contains a VAT breakdown group (BG-23) with
    the VAT category code 'Intra-community supply' (K) shall contain the
    Deliver to country code (BT-80)."""
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
            "An Invoice with a VAT breakdown row of category "
            "'Intra-community supply' (K) shall contain the "
            "deliver-to country code (BT-80).",
        )
    ]


# ---------------------------------------------------------------------------
# 'Not subject to VAT' single-rate restriction
# ---------------------------------------------------------------------------


def _has_o_breakdown_row(m: _trade.Trade) -> bool:
    return any(
        t.category_code == CategoryCode.T_O for t in m.settlement.trade_taxes or []
    )


def br_o_11(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-O-11: An Invoice that contains a VAT breakdown group (BG-23) with
    the VAT category code 'Not subject to VAT' (O) shall not contain other
    VAT breakdown groups."""
    if not _has_o_breakdown_row(m):
        return []
    trade_taxes = m.settlement.trade_taxes or []
    if not any(t.category_code != CategoryCode.T_O for t in trade_taxes):
        return []
    return [
        _err(
            "BR-O-11",
            "An Invoice with a VAT breakdown row of category "
            "'Not subject to VAT' (O) shall not contain other VAT "
            "breakdown rows (BG-23).",
        )
    ]


def br_o_12(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-O-12: An Invoice that contains a VAT breakdown group (BG-23) with
    the VAT category code 'Not subject to VAT' (O) shall not contain an
    Invoice line where the VAT category code is not 'Not subject to VAT'
    (O)."""
    if not _has_o_breakdown_row(m):
        return []
    if not any(
        item.settlement.applicable_trade_tax.category_code != CategoryCode.T_O
        for item in m.items
    ):
        return []
    return [
        _err(
            "BR-O-12",
            "An Invoice with a VAT breakdown row of category "
            "'Not subject to VAT' (O) shall not contain an "
            "Invoice line whose category code is not 'Not "
            "subject to VAT'.",
        )
    ]


def br_o_13(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-O-13: An Invoice that contains a VAT breakdown group (BG-23) with
    the VAT category code 'Not subject to VAT' (O) shall not contain a
    Document level allowance (BG-20) where the VAT category code is not
    'Not subject to VAT' (O)."""
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
            "An Invoice with a VAT breakdown row of category 'Not "
            "subject to VAT' (O) shall not contain a document-level "
            "allowance whose VAT category code is not 'Not subject to "
            "VAT'.",
        )
    ]


def br_o_14(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-O-14: An Invoice that contains a VAT breakdown group (BG-23) with
    the VAT category code 'Not subject to VAT' (O) shall not contain a
    Document level charge (BG-21) where the VAT category code is not 'Not
    subject to VAT' (O)."""
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
            "An Invoice with a VAT breakdown row of category 'Not "
            "subject to VAT' (O) shall not contain a document-level "
            "charge whose VAT category code is not 'Not subject to "
            "VAT'.",
        )
    ]


# ---------------------------------------------------------------------------
# Document-level rules
# ---------------------------------------------------------------------------


def br_16(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-16: An Invoice shall have at least one Invoice line (BG-25).

    Applies: BASIC+ (line items first appear at BASIC).
    """
    if profile <= Profile.BASIC_WL:
        return []
    if m.items:
        return []
    return [
        ValidationError(
            "BR-16", "An Invoice shall have at least one Invoice line (BG-25)."
        )
    ]


def br_co_10(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-CO-10: Sum of Invoice line net amount (BT-106) = sum of all
    Invoice line net amounts (BT-131).

    Applies: BASIC+ except EXTENDED. At EXTENDED ``BR-FXEXT-CO-10``
    replaces this with a tolerance-banded variant that also excludes
    ``GROUP`` / ``INFORMATION`` lines from the sum. ``BT-106`` is
    carthorse-optional (MINIMUM doesn't have it) — the check is
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
        (item.settlement.monetary_summation.line_total for item in m.items),
        Decimal("0"),
    )
    if summation.line_total == sum_line_totals:
        return []
    return [
        ValidationError(
            "BR-CO-10",
            "Sum of Invoice line net amount (BT-106) = "
            f"{summation.line_total} differs from sum(BT-131) = "
            f"{sum_line_totals}.",
        )
    ]


def br_co_11(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-CO-11: Sum of allowances on document level (BT-107) = sum of
    Document level allowance amounts (BT-92).

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
            "Sum of allowances on document level (BT-107) = "
            f"{summation.allowance_total} differs from sum(BT-92) = "
            f"{sum_allowances}.",
        )
    ]


def br_co_12(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-CO-12: Sum of charges on document level (BT-108) = sum of
    Document level charge amounts (BT-99).

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
            "Sum of charges on document level (BT-108) = "
            f"{summation.charge_total} differs from sum(BT-99) = "
            f"{sum_charges}.",
        )
    ]


def br_co_13(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-CO-13: Invoice total amount without VAT (BT-109) = sum of Invoice
    line net amounts (BT-131) - sum of allowances on document level
    (BT-92) + sum of charges on document level (BT-99).

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
        (item.settlement.monetary_summation.line_total for item in m.items),
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
            "Invoice total amount without VAT (BT-109) = "
            f"{summation.tax_basis_total} differs from "
            f"sum(BT-131) - sum(BT-92) + sum(BT-99) = "
            f"{sum_line_totals} - {sum_allowances} + "
            f"{sum_charges} = {expected_basis}.",
        )
    ]


def br_co_21(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-CO-21: Each Document level allowance (BG-20) shall contain a
    Document level allowance reason (BT-97) or a Document level allowance
    reason code (BT-98), or both.

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
                    "Each Document level allowance (BG-20) shall "
                    "contain a Document level allowance reason "
                    "(BT-97) or a Document level allowance reason "
                    "code (BT-98), or both.",
                )
            )
    return errors


def br_co_22(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-CO-22: Each Document level charge (BG-21) shall contain a
    Document level charge reason (BT-104) or a Document level charge
    reason code (BT-105), or both.

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
                    "Each Document level charge (BG-21) shall "
                    "contain a Document level charge reason "
                    "(BT-104) or a Document level charge reason "
                    "code (BT-105), or both.",
                )
            )
    return errors


def br_co_23(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-CO-23: Each Invoice line allowance (BG-27) shall contain an
    Invoice line allowance reason (BT-139) or an Invoice line allowance
    reason code (BT-140), or both.

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
                        "Each Invoice line allowance (BG-27) shall "
                        "contain an Invoice line allowance reason "
                        "(BT-139) or an Invoice line allowance "
                        "reason code (BT-140), or both.",
                    )
                )
    return errors


def br_co_24(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-CO-24: Each Invoice line charge (BG-28) shall contain an Invoice
    line charge reason (BT-144) or an Invoice line charge reason code
    (BT-145), or both.

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
                        "Each Invoice line charge (BG-28) shall "
                        "contain an Invoice line charge reason "
                        "(BT-144) or an Invoice line charge "
                        "reason code (BT-145), or both.",
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
    CategoryCode.T_S: (lambda r: r is not None and r > 0, "shall be greater than zero"),
    CategoryCode.T_Z: (lambda r: r == 0, "shall be 0 (zero)"),
    CategoryCode.T_E: (lambda r: r == 0, "shall be 0 (zero)"),
    CategoryCode.T_AE: (lambda r: r == 0, "shall be 0 (zero)"),
    CategoryCode.T_G: (lambda r: r == 0, "shall be 0 (zero)"),
    CategoryCode.T_K: (lambda r: r == 0, "shall be 0 (zero)"),
    CategoryCode.T_L: (
        lambda r: r is not None and r >= 0,
        "shall be 0 (zero) or greater than zero",
    ),
    CategoryCode.T_M: (
        lambda r: r is not None and r >= 0,
        "shall be 0 (zero) or greater than zero",
    ),
    CategoryCode.T_O: (lambda r: r is None, "shall not be present"),
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
    m: _trade.Trade, profile: Profile
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
                    f"VAT breakdown with category {cat.value!r} shall "
                    "not carry a VAT exemption reason text (BT-120) "
                    "or code (BT-121).",
                )
            )
        if cat in _VAT_EXEMPTION_REQUIRES and not (has_text or has_code):
            errors.append(
                _err(
                    _vat_rate_violation_code(cat, "10"),
                    f"VAT breakdown with category {cat.value!r} shall "
                    "carry a VAT exemption reason text (BT-120) or "
                    "code (BT-121).",
                )
            )
    return errors


def vat_category_rates(m: _trade.Trade, profile: Profile) -> list[ValidationError]:
    """BR-X-5 / BR-X-6 / BR-X-7 — per-VAT-category rate constraints.

    One dispatch covers all nine categories (S, Z, E, AE, G, IC, IG, IP,
    O) at three placements (line / doc allowance / doc charge). Emits
    distinct error codes per (category, placement).
    """
    errors: list[ValidationError] = []

    # BR-X-5 — line-level (BT-151 / BT-152).
    for idx, item in enumerate(m.items):
        cat = item.settlement.applicable_trade_tax.category_code
        rate = item.settlement.applicable_trade_tax.rate_applicable_percent
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
