"""§3.4 — context-aware profile gating for ``TradeAllowanceCharge``.

The same XSD element backs four BG groups:

* BG-20 / BG-21 header allowance / charge — BT-93 / BT-100 basis amount
  and BT-94 / BT-101 calculation percent ship at BASIC_WL+.
* BG-27 / BG-28 line allowance / charge — BT-137 / BT-141 basis amount
  and BT-138 / BT-142 calculation percent ship at COMFORT+.

Getafix models this via two thin sentinel subclasses
``HeaderTradeAllowanceCharge`` and ``LineTradeAllowanceCharge`` that
override a class-level ``context`` flag on the abstract base
``TradeAllowanceCharge``.

The gating tests below pin the spec-correct behaviour: rendering a
line-level allowance / charge with ``calculation_percent`` or
``basis_amount`` set at BASIC must raise ``ProfileMismatch``, since
the value would otherwise be silently lost; rendering the same
construct at COMFORT must round-trip cleanly. Header context keeps
BASIC_WL gating.
"""

from __future__ import annotations

from decimal import Decimal

import pytest as pt

from getafix.schema.accounting import (
    HeaderTradeAllowanceCharge,
    LineTradeAllowanceCharge,
)
from getafix.schema.element import ProfileMismatch
from getafix.schema.types import Profile


class TestLineContextGating:
    def test_calculation_percent_at_basic_raises(self) -> None:
        ac = LineTradeAllowanceCharge(
            indicator=False,
            actual_amount=Decimal("5.00"),
            calculation_percent=Decimal("5"),
            reason="discount",
        )
        with pt.raises(ProfileMismatch):
            ac.to_xml_internal(Profile.BASIC).render(indent=True)

    def test_basis_amount_at_basic_raises(self) -> None:
        ac = LineTradeAllowanceCharge(
            indicator=False,
            actual_amount=Decimal("5.00"),
            basis_amount=Decimal("100.00"),
            reason="discount",
        )
        with pt.raises(ProfileMismatch):
            ac.to_xml_internal(Profile.BASIC).render(indent=True)

    def test_calculation_percent_at_basic_wl_raises(self) -> None:
        ac = LineTradeAllowanceCharge(
            indicator=False,
            actual_amount=Decimal("5.00"),
            calculation_percent=Decimal("5"),
            reason="discount",
        )
        with pt.raises(ProfileMismatch):
            ac.to_xml_internal(Profile.BASIC_WL).render(indent=True)

    def test_calculation_percent_at_comfort_renders(self) -> None:
        ac = LineTradeAllowanceCharge(
            indicator=False,
            actual_amount=Decimal("5.00"),
            calculation_percent=Decimal("5"),
            basis_amount=Decimal("100.00"),
            reason="discount",
        )
        xml = ac.to_xml_internal(Profile.COMFORT).render(indent=True)
        assert "<ram:CalculationPercent>" in xml
        assert "<ram:BasisAmount>" in xml

    def test_line_without_percent_or_basis_at_basic_renders(self) -> None:
        """The amount/reason fields still ship at BASIC for line context."""
        ac = LineTradeAllowanceCharge(
            indicator=False, actual_amount=Decimal("5.00"), reason="discount"
        )
        xml = ac.to_xml_internal(Profile.BASIC).render(indent=True)
        assert "<ram:ActualAmount>" in xml
        assert "<ram:CalculationPercent>" not in xml
        assert "<ram:BasisAmount>" not in xml


class TestHeaderContextGating:
    def test_calculation_percent_at_basic_wl_renders(self) -> None:
        ac = HeaderTradeAllowanceCharge(
            indicator=False,
            actual_amount=Decimal("5.00"),
            calculation_percent=Decimal("5"),
            basis_amount=Decimal("100.00"),
            reason="discount",
        )
        xml = ac.to_xml_internal(Profile.BASIC_WL).render(indent=True)
        assert "<ram:CalculationPercent>" in xml
        assert "<ram:BasisAmount>" in xml

    def test_calculation_percent_at_minimum_raises(self) -> None:
        ac = HeaderTradeAllowanceCharge(
            indicator=False,
            actual_amount=Decimal("5.00"),
            calculation_percent=Decimal("5"),
            reason="discount",
        )
        with pt.raises(ProfileMismatch):
            ac.to_xml_internal(Profile.MINIMUM).render(indent=True)


class TestAbstractBase:
    def test_subclasses_have_correct_context(self) -> None:
        assert HeaderTradeAllowanceCharge.context == "header"
        assert LineTradeAllowanceCharge.context == "line"

    def test_bare_class_is_abstract(self) -> None:
        from getafix.schema.accounting import TradeAllowanceCharge

        with pt.raises(TypeError, match="abstract"):
            TradeAllowanceCharge(indicator=False, actual_amount=Decimal("5.00"))
