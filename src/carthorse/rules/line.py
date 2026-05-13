"""Validators for :mod:`carthorse.schema.line`.

One function per ``BR-*`` rule that today lives inside an
``Element.validate_internal`` body in ``line.py``. The signatures
match :data:`carthorse.rules.Validator`.

Each function:

* self-gates on profile and on the precondition data;
* returns ``list[ValidationError]`` (empty on success);
* never raises.

See ``docs/VALIDATOR_REFACTOR.md`` for the rework plan.
"""

# pyright: reportImportCycles=false

from __future__ import annotations

from typing import TYPE_CHECKING

from carthorse.schema.element import ValidationError
from carthorse.schema.types import Profile

if TYPE_CHECKING:
    from carthorse.schema import line as _line


def br_27(m: _line.NetTradePrice, profile: Profile) -> list[ValidationError]:
    """BR-27: The Item net price (BT-146) shall NOT be negative.

    Applies: BASIC+ (line items first appear at BASIC).
    """
    if m.charge_amount >= 0:
        return []
    return [
        ValidationError(
            "BR-27",
            "The Item net price (BT-146) shall NOT be negative.",
        )
    ]


def br_28(m: _line.GrossTradePrice, profile: Profile) -> list[ValidationError]:
    """BR-28: The Item gross price (BT-148) shall NOT be negative.

    Applies: BASIC+ (line items first appear at BASIC).
    """
    if m.charge_amount >= 0:
        return []
    return [
        ValidationError(
            "BR-28",
            "The Item gross price (BT-148) shall NOT be negative.",
        )
    ]
