"""Numeric helpers — rounding rule per Factur-X 1.08 §7.1.8.

The specification mandates "half away from zero" rounding for every
intermediate calculation that needs to land on two decimal places:

* Positive numbers — round up.  Example: ``13.455 → 13.46``.
* Negative numbers — round down (to the lower value, more negative).
  Example: ``-13.455 → -13.46``.

The rationale (spec §7.1.8) is that this keeps the round of a number
and the round of its negation strictly opposite: ``round(x) + round(-x)
== 0`` for every ``x``.

This is exactly Python's :data:`decimal.ROUND_HALF_UP` mode — "round
to nearest with ties going away from zero" — so this module is mostly
a named alias plus a sensible default precision.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

_TWO_DP = Decimal("0.01")


def round_half_away_from_zero(value: Decimal, *, places: Decimal = _TWO_DP) -> Decimal:
    """Round *value* to *places* decimal precision, half away from zero.

    The default precision is two decimal places — what every monetary
    BT (BT-117, BT-147, BT-92, BT-99, …) lands on after multiplication.
    """
    return value.quantize(places, rounding=ROUND_HALF_UP)
