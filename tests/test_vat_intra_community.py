"""BR-IC-11 / BR-IC-12 — intra-community supply needs evidence of
cross-border delivery (an actual delivery date or billing period, and
a deliver-to country)."""

from __future__ import annotations

from datetime import date

import pytest as pt

from getafix.schema import Document
from getafix.schema.delivery import SupplyChainEvent
from getafix.schema.element import ValidationErrors
from getafix.schema.party import PostalTradeAddressExtended, ShipToTradeParty
from getafix.schema.settlement import BillingSpecifiedPeriod
from getafix.schema.types import CategoryCode, Country
from tests._fixtures import make_vat_doc


class TestBrIcDelivery:
    """BR-IC-11 / BR-IC-12 — intra-community supply needs evidence
    of cross-border delivery."""

    def _make_ic(self) -> Document:
        # Both Seller and Buyer have VAT (so BR-IC-2 is satisfied) and
        # the line carries category K. From there, BR-IC-11 (BT-72 or
        # BG-14) and BR-IC-12 (BT-80) are the next checks.
        return make_vat_doc(line_category=CategoryCode.T_K)

    def test_br_ic_11_passes_with_actual_delivery_date(self) -> None:
        doc = self._make_ic()
        doc.trade.delivery.event = SupplyChainEvent(occurrence=date(2025, 1, 15))
        # BR-IC-12 still needs deliver-to country.
        doc.trade.delivery.ship_to = ShipToTradeParty(
            address=PostalTradeAddressExtended(country_id=Country.FR)
        )
        doc.validate()

    def test_br_ic_11_passes_with_billing_period(self) -> None:
        doc = self._make_ic()
        doc.trade.settlement.billing_period = BillingSpecifiedPeriod(
            start=date(2025, 1, 1), end=date(2025, 1, 31)
        )
        doc.trade.delivery.ship_to = ShipToTradeParty(
            address=PostalTradeAddressExtended(country_id=Country.FR)
        )
        doc.validate()

    def test_br_ic_11_fires_without_date_or_period(self) -> None:
        doc = self._make_ic()
        doc.trade.delivery.ship_to = ShipToTradeParty(
            address=PostalTradeAddressExtended(country_id=Country.FR)
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-IC-11" for v in e.value.errors)

    def test_br_ic_12_fires_without_ship_to_country(self) -> None:
        doc = self._make_ic()
        doc.trade.delivery.event = SupplyChainEvent(occurrence=date(2025, 1, 15))
        # No ship_to → no BT-80.
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-IC-12" for v in e.value.errors)
