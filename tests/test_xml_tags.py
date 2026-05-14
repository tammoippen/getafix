"""Small XSD-shape regression tests — bug-sweep findings where a
field rendered under the wrong tag or where two distinct fields
collided on the same tag. Each test is a focused round-trip of a
single sub-tree."""

from __future__ import annotations

from decimal import Decimal

from carthorse.schema import Profile
from carthorse.schema.accounting import (
    ApplicableTradeTax,
    CategoryTradeTax,
    TradeAllowanceCharge,
)
from carthorse.schema.types import CategoryCode
from tests._fixtures import wrap_subtree
from tests._parsers import ParseFromBytes


def test_exemption_reason_code_uses_distinct_tag(parser: ParseFromBytes):
    """BT-121 (ExemptionReasonCode) must round-trip independently of BT-120
    (ExemptionReason). Bug sweep #3."""
    tax = ApplicableTradeTax(
        calculated_amount=Decimal("0.00"),
        basis_amount=Decimal("0.00"),
        category_code=CategoryCode.T_E,
        due_date_code="5",
        exemption_reason="exempt-text",
        exemption_reason_code="VATEX-EU-79-C",
    )
    xml = tax.to_xml_internal(Profile.BASIC_WL).render(indent=True)
    assert "<ram:ExemptionReason>" in xml
    assert "<ram:ExemptionReasonCode>" in xml
    parsed = ApplicableTradeTax.from_xml(
        parser(wrap_subtree(xml, "ApplicableTradeTax"))
    )
    assert parsed == tax


def test_trade_allowance_charge_basis_amount_uses_correct_tag(parser: ParseFromBytes):
    """BT-93 (BasisAmount) must render under <ram:BasisAmount>, not
    <ram:CalculationPercent>. Bug sweep #4."""
    ac = TradeAllowanceCharge(
        indicator=False,
        actual_amount=Decimal("5.00"),
        category_trade_tax=CategoryTradeTax(
            category_code=CategoryCode.T_S, rate_applicable_percent=Decimal("19")
        ),
        calculation_percent=Decimal("5"),
        basis_amount=Decimal("100.00"),
        reason="x",
    )
    xml = ac.to_xml_internal(Profile.COMFORT).render(indent=True)
    assert "<ram:BasisAmount>" in xml
    assert "<ram:CalculationPercent>" in xml
    parsed = TradeAllowanceCharge.from_xml(
        parser(wrap_subtree(xml, "SpecifiedTradeAllowanceCharge"))
    )
    assert parsed == ac
