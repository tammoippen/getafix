"""BG-14 invoicing period: BR-29, BR-CO-19, BillingSpecifiedPeriod round-trip."""

from __future__ import annotations

from datetime import date

from carthorse.schema import Profile
from carthorse.schema.settlement import BillingSpecifiedPeriod
from tests._fixtures import wrap_subtree
from tests._parsers import ParseFromBytes


def test_billing_specified_period_round_trips(parser: ParseFromBytes):
    """BG-14 BillingSpecifiedPeriod with start + end round-trips."""
    period = BillingSpecifiedPeriod(start=date(2025, 1, 1), end=date(2025, 1, 31))
    xml = period.to_xml_internal(Profile.BASIC_WL).render(indent=True)
    assert "<ram:BillingSpecifiedPeriod>" in xml
    assert "<ram:StartDateTime>" in xml
    assert "<ram:EndDateTime>" in xml
    parsed = BillingSpecifiedPeriod.from_xml(
        parser(wrap_subtree(xml, "BillingSpecifiedPeriod"))
    )
    assert parsed == period


def test_billing_specified_period_br_co_19_at_least_one_endpoint():
    """BG-14 with neither start nor end set raises BR-CO-19."""
    period = BillingSpecifiedPeriod()
    errors = period.validate_internal(Profile.BASIC_WL)
    assert any(v.code == "BR-CO-19" for v in errors)


def test_billing_specified_period_br_29_end_after_start():
    """BG-14 with end < start raises BR-29."""
    period = BillingSpecifiedPeriod(start=date(2025, 2, 1), end=date(2025, 1, 1))
    errors = period.validate_internal(Profile.BASIC_WL)
    assert any(v.code == "BR-29" for v in errors)
