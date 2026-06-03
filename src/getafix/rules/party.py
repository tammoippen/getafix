"""Validators for :mod:`getafix.schema.party`.

One function per ``BR-*`` rule (or per BT shape-check) that today
lives inside an ``Element.validate_internal`` body in ``party.py``.
The signatures match :data:`getafix.rules.Validator`.

Each function:

* self-gates on profile and on the precondition data;
* returns ``list[ValidationError]`` (empty on success);
* never raises.

See ``AGENTS.md`` "Validator architecture" for the design.
"""

# pyright: reportImportCycles=false

from __future__ import annotations

from typing import TYPE_CHECKING

from getafix.schema.element import ValidationError
from getafix.schema.types import Profile

if TYPE_CHECKING:
    from getafix.schema import party as _party


def bt_31_0_scheme_id(
    m: _party.TaxSchemeId, _profile: Profile
) -> list[ValidationError]:
    """BT-31-0 / BT-32-0: ``schemeID`` on a ``SpecifiedTaxRegistration`` must
    be ``"VA"`` (VAT identifier) or ``"FC"`` (local tax identifier).

    Applies: MINIMUM+. Not a numbered EN 16931 rule — a code-shape
    guard against malformed inputs. Raises with error code
    ``"BT-31-0/BT-32-0"`` for back-compat with existing tests.
    """
    if m.scheme_id in ("VA", "FC"):
        return []
    return [
        ValidationError(
            "BT-31-0/BT-32-0",
            "schemeID on a SpecifiedTaxRegistration must be 'VA' "
            "(VAT identifier) or 'FC' (local tax id); got "
            f"{m.scheme_id!r}.",
        )
    ]


def br_co_9(m: _party.TaxSchemeId, _profile: Profile) -> list[ValidationError]:
    """BR-CO-9: The Seller VAT identifier (BT-31), the Seller tax
    representative VAT identifier (BT-63) and the Buyer VAT identifier
    (BT-48) shall have a prefix in accordance with ISO 3166-1 alpha-2 by
    which the country of issue may be identified. Nevertheless, Greece may
    use the prefix ``EL``.

    Applies: MINIMUM+. Only checked for VAT identifiers
    (``scheme_id == "VA"``) — local tax identifiers (``FC``, BT-32)
    are exempt as they're national codes without the country-prefix
    convention.
    """
    if m.scheme_id != "VA":
        return []
    prefix = m.id[:2]
    if len(m.id) >= 3 and prefix.isalpha() and prefix == prefix.upper():
        return []
    return [
        ValidationError(
            "BR-CO-9",
            "The Seller VAT identifier (BT-31), the Seller tax "
            "representative VAT identifier (BT-63) and the Buyer "
            "VAT identifier (BT-48) must each carry a prefix "
            "according to ISO 3166-1 alpha-2 by which the "
            "country of issue may be identified. Greece may use "
            "the prefix 'EL'.",
        )
    ]


def br_co_26(m: _party.SellerTradeParty, _profile: Profile) -> list[ValidationError]:
    """BR-CO-26: In order for the buyer to automatically identify a
    supplier, the Seller identifier (BT-29), the Seller legal registration
    identifier (BT-30) and/or the Seller VAT identifier (BT-31) shall be
    present.

    Applies: MINIMUM+ (Seller is required at every profile).
    """
    has_id = m.id is not None
    has_legal = m.legal_organization is not None and m.legal_organization.id is not None
    has_vat = bool(m.tax_registrations) and any(
        tr.id.scheme_id == "VA" for tr in m.tax_registrations
    )
    if has_id or has_legal or has_vat:
        return []
    return [
        ValidationError(
            "BR-CO-26",
            "In order for the buyer to automatically identify a "
            "supplier, the Seller identifier (BT-29), the Seller "
            "legal registration identifier (BT-30) and/or the "
            "Seller VAT identifier (BT-31) shall be present.",
        )
    ]


def br_10(m: _party.BuyerTradeParty, profile: Profile) -> list[ValidationError]:
    """BR-10: An Invoice shall contain the Buyer postal address (BG-8).

    Applies: BASIC_WL+. The MINIMUM XSD lets ``PostalTradeAddress``
    be omitted, and the MINIMUM appendix does NOT list BG-8 as
    required — the rule only kicks in from BASIC_WL upwards.
    """
    if profile <= Profile.MINIMUM:
        return []
    if m.address is not None:
        return []
    return [
        ValidationError(
            "BR-10", "An Invoice shall contain the Buyer postal address (BG-8)."
        )
    ]


def br_62(m: _party.SellerTradeParty, _profile: Profile) -> list[ValidationError]:
    """BR-62: The Seller electronic address (BT-34) shall have a Scheme
    identifier.

    Applies: BASIC_WL+ (BT-34-00 first appears there).
    """
    addr = m.electronic_address
    if addr is None:
        return []
    if addr.uri_id.scheme_id is not None:
        return []
    return [
        ValidationError(
            "BR-62",
            "The Seller electronic address (BT-34) shall have a Scheme identifier.",
        )
    ]


def br_63(m: _party.BuyerTradeParty, _profile: Profile) -> list[ValidationError]:
    """BR-63: The Buyer electronic address (BT-49) shall have a Scheme
    identifier.

    Applies: BASIC_WL+ (BT-49-00 first appears there).
    """
    addr = m.electronic_address
    if addr is None:
        return []
    if addr.uri_id.scheme_id is not None:
        return []
    return [
        ValidationError(
            "BR-63",
            "The Buyer electronic address (BT-49) shall have a Scheme identifier.",
        )
    ]
