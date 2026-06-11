"""Validators for :mod:`getafix.schema.line`.

One function per ``BR-*`` rule that today lives inside an
``Element.validate_internal`` body in ``line.py``. The signatures
match :data:`getafix.rules.Validator`.

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
    from getafix.schema import line as _line


def br_27(m: _line.NetTradePrice, profile: Profile) -> list[ValidationError]:
    """BR-27: a negative Item net price (BT-146) is not allowed.

    Applies: BASIC+ (line items first appear at BASIC). Short-circuits
    at EXTENDED — there the replacement
    :func:`getafix.rules.extended.br_fxext_27` re-evaluates the
    same identity with the DETAIL / unset line-subtype qualifier so
    GROUP / INFORMATION lines (which may legitimately carry a
    negative reference price) escape.
    """
    if profile >= Profile.EXTENDED:
        return []
    if m.charge_amount >= 0:
        return []
    return [ValidationError("BR-27", "Item net price (BT-146) is negative.")]


def br_28(m: _line.GrossTradePrice, _profile: Profile) -> list[ValidationError]:
    """BR-28: a negative Item gross price (BT-148) is not allowed.

    Applies: BASIC+ (line items first appear at BASIC).
    """
    if m.charge_amount >= 0:
        return []
    return [ValidationError("BR-28", "Item gross price (BT-148) is negative.")]


def applied_price_charge_extended_only(
    m: _line.AppliedTradeAllowanceCharge, profile: Profile
) -> list[ValidationError]:
    """A price-level *charge* (ChargeIndicator true, BT-X-302-00) is only
    permitted at EXTENDED.

    Below EXTENDED the gross-price ``AppliedTradeAllowanceCharge`` may
    only be a price *allowance* (ChargeIndicator false, BT-147-00); the
    charge variant is a Factur-X EXTENDED extension. Applies BASIC+
    (the gross price is line-level). Emits the synthetic
    ``GETAFIX-FIELD-PROFILE`` code shared by the other profile gates.
    """
    if not m.indicator or profile >= Profile.EXTENDED:
        return []
    return [
        ValidationError(
            "GETAFIX-FIELD-PROFILE",
            "A price charge (BT-X-302-00, ChargeIndicator true) is only "
            "allowed at EXTENDED; below EXTENDED only a price allowance "
            f"(BT-147-00) may appear (current profile: {profile.name}).",
        )
    ]
