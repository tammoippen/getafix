"""BR-51 — payment card last 4..6 digits.

EN 16931 §G.1 — "The last 4 to 6 digits of the Payment card primary
account number (BT-87) shall be present if Payment card information
(BG-18) is provided in the Invoice."

The :class:`carthorse.schema.settlement.FinancialCard` dataclass
enforces presence by declaring ``id`` non-Optional; this validator
adds the format check (regex ``\\d{4,6}``).
"""

from __future__ import annotations

import pytest as pt

from carthorse.schema import Profile
from carthorse.schema.element import ValidationError
from carthorse.schema.settlement import FinancialCard


@pt.mark.parametrize("value", ["1234", "12345", "123456"])
def test_br_51_passes_for_4_to_6_digits(value: str) -> None:
    card = FinancialCard(id=value)
    errors: list[ValidationError] = []
    for v in FinancialCard._validators:
        errors.extend(v(card, Profile.COMFORT))
    assert errors == []


@pt.mark.parametrize("value", ["12", "123", "1234567", "abcd", "12 34", "12-34"])
def test_br_51_fails_for_non_4_to_6_digit_pan(value: str) -> None:
    card = FinancialCard(id=value)
    errors: list[ValidationError] = []
    for v in FinancialCard._validators:
        errors.extend(v(card, Profile.COMFORT))
    assert any(e.code == "BR-51" for e in errors), errors
