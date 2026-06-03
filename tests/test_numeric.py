"""Unit tests for Factur-X / ZUGFeRD numeric helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest as pt

from getafix.schema._numeric import round_half_away_from_zero


class TestFacturXRounding:
    """Factur-X 1.08 §7.1.8 — half away from zero.

    For positive numbers, ties go up (13.455 -> 13.46).
    For negative numbers, ties go down (-13.455 -> -13.46).
    The choice keeps ``round(x) + round(-x) == 0`` for every x.
    """

    @pt.mark.parametrize(
        ("value", "expected"),
        [
            (Decimal("13.455"), Decimal("13.46")),
            (Decimal("-13.455"), Decimal("-13.46")),
            (Decimal("13.445"), Decimal("13.45")),
            (Decimal("-13.445"), Decimal("-13.45")),
            (Decimal("0.005"), Decimal("0.01")),
            (Decimal("-0.005"), Decimal("-0.01")),
            # Already at 2dp — round-trip without change.
            (Decimal("12.34"), Decimal("12.34")),
            (Decimal("-12.34"), Decimal("-12.34")),
            # No fractional part — gain trailing zeros.
            (Decimal("100"), Decimal("100.00")),
        ],
    )
    def test_rounds_to_two_decimals(self, value: Decimal, expected: Decimal) -> None:
        assert round_half_away_from_zero(value) == expected

    def test_round_of_negation_is_negation_of_round(self) -> None:
        """Spec rationale: pair-wise symmetry around zero."""
        for v in [
            Decimal("13.455"),
            Decimal("0.125"),
            Decimal("99.999"),
            Decimal("0.001"),
        ]:
            assert round_half_away_from_zero(v) == -round_half_away_from_zero(-v)
