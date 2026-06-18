"""§3.2 — line-level references (BT-132 / BT-128 / BT-133).

EN 16931 adds three optional cross-reference fields per invoice line:

* **BT-132 ``BuyerOrderReferencedDocument`` (line)** — a single
  ``LineID`` pointing to the position on the referenced purchase
  order. Distinct from the header BG-2 variant (which carries
  ``IssuerAssignedID``) so a new dataclass is needed.
* **BT-128 / BT-128-0 / BT-128-1 ``AdditionalReferencedDocument``
  (line)** — invoice-line object identifier with required
  ``IssuerAssignedID``, fixed ``TypeCode`` = ``130`` and optional
  ``ReferenceTypeCode`` (the UNTDID 1153 scheme id).
* **BT-133 ``ReceivableSpecifiedTradeAccountingAccount`` (line)** —
  reuses the header :class:`ReceivableAccountingAccount`, but gated
  COMFORT+ at line via field-level ``metadata['profile']``.

All three ship at COMFORT+.
"""

from __future__ import annotations

from decimal import Decimal

import pytest as pt

from getafix.schema.accounting import ApplicableTradeTax
from getafix.schema.element import ProfileMismatch
from getafix.schema.line import (
    AppliedTradeAllowanceCharge,
    GrossTradePrice,
    LineAdditionalReferencedDocument,
    LineBuyerOrderReferencedDocument,
    LineMonetarySummation,
    LineTradeAgreement,
    LineTradeSettlement,
    NetTradePrice,
)
from getafix.schema.settlement import ReceivableAccountingAccount
from getafix.schema.types import CategoryCode, Profile, UNTDID2475TaxPointDateCode
from tests._fixtures import wrap_subtree
from tests._parsers import ParseFromBytes


class TestLineBuyerOrderRef:
    def test_construct_with_line_id(self) -> None:
        ref = LineBuyerOrderReferencedDocument(line_id="42")
        assert ref.line_id == "42"

    def test_renders_at_comfort(self) -> None:
        ref = LineBuyerOrderReferencedDocument(line_id="42")
        xml = ref.to_xml_internal(Profile.COMFORT).render(indent=True)
        assert "<ram:BuyerOrderReferencedDocument>" in xml
        assert "<ram:LineID>" in xml
        assert "42" in xml

    def test_parent_render_below_comfort_raises(self) -> None:
        agreement = LineTradeAgreement(
            net_price=NetTradePrice(charge_amount=Decimal("10")),
            buyer_order_ref=LineBuyerOrderReferencedDocument(line_id="42"),
        )
        with pt.raises(ProfileMismatch):
            agreement.to_xml_internal(Profile.BASIC).render(indent=True)

    def test_round_trip(self, parser: ParseFromBytes) -> None:
        agreement = LineTradeAgreement(
            net_price=NetTradePrice(charge_amount=Decimal("10")),
            buyer_order_ref=LineBuyerOrderReferencedDocument(line_id="42"),
        )
        xml = agreement.to_xml_internal(Profile.COMFORT).render(indent=True)
        parsed = LineTradeAgreement.from_xml(
            parser(wrap_subtree(xml, "SpecifiedLineTradeAgreement"))
        )
        assert parsed == agreement


class TestLineAdditionalReferencedDocument:
    def test_construct_with_id_only(self) -> None:
        ref = LineAdditionalReferencedDocument(issuer_assigned_id="OBJ-123")
        assert ref.issuer_assigned_id == "OBJ-123"
        # Default type_code is "130" (invoiced object identifier).
        assert ref.type_code == "130"
        assert ref.reference_type_code is None

    def test_renders_fixed_type_code_130(self) -> None:
        ref = LineAdditionalReferencedDocument(issuer_assigned_id="OBJ-123")
        xml = ref.to_xml_internal(Profile.COMFORT).render(indent=True)
        assert "<ram:IssuerAssignedID>" in xml
        assert "OBJ-123" in xml
        assert "<ram:TypeCode>" in xml
        assert "130" in xml

    def test_renders_with_reference_type_code(self) -> None:
        ref = LineAdditionalReferencedDocument(
            issuer_assigned_id="OBJ-123", reference_type_code="VA"
        )
        xml = ref.to_xml_internal(Profile.COMFORT).render(indent=True)
        assert "<ram:ReferenceTypeCode>" in xml
        assert "VA" in xml

    def test_round_trip(self, parser: ParseFromBytes) -> None:
        settle = LineTradeSettlement(
            applicable_trade_tax=ApplicableTradeTax(
                category_code=CategoryCode.T_S,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("19"),
            ),
            additional_references=[
                LineAdditionalReferencedDocument(
                    issuer_assigned_id="OBJ-123", reference_type_code="VA"
                )
            ],
            monetary_summation=LineMonetarySummation(line_total=Decimal("10")),
        )
        xml = settle.to_xml_internal(Profile.COMFORT).render(indent=True)
        parsed = LineTradeSettlement.from_xml(
            parser(wrap_subtree(xml, "SpecifiedLineTradeSettlement"))
        )
        assert parsed == settle


class TestLineAccountingAccount:
    def test_round_trip(self, parser: ParseFromBytes) -> None:
        settle = LineTradeSettlement(
            applicable_trade_tax=ApplicableTradeTax(
                category_code=CategoryCode.T_S,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("19"),
            ),
            accounting_account=ReceivableAccountingAccount(id="ACC-1"),
            monetary_summation=LineMonetarySummation(line_total=Decimal("10")),
        )
        xml = settle.to_xml_internal(Profile.COMFORT).render(indent=True)
        assert "<ram:ReceivableSpecifiedTradeAccountingAccount>" in xml
        parsed = LineTradeSettlement.from_xml(
            parser(wrap_subtree(xml, "SpecifiedLineTradeSettlement"))
        )
        assert parsed == settle

    def test_parent_render_below_comfort_raises(self) -> None:
        settle = LineTradeSettlement(
            applicable_trade_tax=ApplicableTradeTax(
                category_code=CategoryCode.T_S,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("19"),
            ),
            accounting_account=ReceivableAccountingAccount(id="ACC-1"),
            monetary_summation=LineMonetarySummation(line_total=Decimal("10")),
        )
        # Line-level BT-133 ships at COMFORT+; rendering at BASIC must
        # raise — the field metadata pins the gate above the class's
        # native BASIC_WL profile (which applies to the header BT-19).
        with pt.raises(ProfileMismatch):
            settle.to_xml_internal(Profile.BASIC).render(indent=True)


class TestPriceAllowanceCharge:
    """Item price allowance (BT-147-00) / charge (BT-X-302-00) on the gross
    price. At most one allowance below EXTENDED; multiple entries, price
    charges and the reason / percent / basis fields are EXTENDED-only."""

    def test_two_allowances_render_and_round_trip_at_extended(
        self, parser: ParseFromBytes
    ) -> None:
        gross = GrossTradePrice(
            charge_amount=Decimal("1.50"),
            applied_allowance_charge=[
                AppliedTradeAllowanceCharge(
                    indicator=False,
                    actual_amount=Decimal("0.03"),
                    reason="Artikelrabatt 1",
                ),
                AppliedTradeAllowanceCharge(
                    indicator=False,
                    actual_amount=Decimal("0.02"),
                    reason="Artikelrabatt 2",
                ),
            ],
        )
        assert gross.validate_internal(Profile.EXTENDED) == []
        xml = gross.to_xml_internal(Profile.EXTENDED).render(indent=True)
        assert xml.count("<ram:AppliedTradeAllowanceCharge>") == 2
        assert "Artikelrabatt 1" in xml
        assert "Artikelrabatt 2" in xml
        parsed = GrossTradePrice.from_xml(
            parser(wrap_subtree(xml, "GrossPriceProductTradePrice"))
        )
        assert [a.reason for a in parsed.applied_allowance_charge or []] == [
            "Artikelrabatt 1",
            "Artikelrabatt 2",
        ]

    def test_price_charge_is_extended_only(self) -> None:
        charge = AppliedTradeAllowanceCharge(
            indicator=True, actual_amount=Decimal("0.05")
        )
        # A price charge (ChargeIndicator true) is not allowed below EXTENDED.
        below = [e.code for e in charge.validate_internal(Profile.COMFORT)]
        assert "GETAFIX-FIELD-PROFILE" in below
        # At EXTENDED it is fine.
        assert charge.validate_internal(Profile.EXTENDED) == []

    def test_multiple_allowances_capped_below_extended(self) -> None:
        two = GrossTradePrice(
            charge_amount=Decimal("1.50"),
            applied_allowance_charge=[
                AppliedTradeAllowanceCharge(
                    indicator=False, actual_amount=Decimal("0.03")
                ),
                AppliedTradeAllowanceCharge(
                    indicator=False, actual_amount=Decimal("0.02")
                ),
            ],
        )
        capped = [e.code for e in two.validate_internal(Profile.COMFORT)]
        assert "GETAFIX-FIELD-CARDINALITY" in capped
        # A single allowance is fine below EXTENDED.
        one = GrossTradePrice(
            charge_amount=Decimal("1.50"),
            applied_allowance_charge=[
                AppliedTradeAllowanceCharge(
                    indicator=False, actual_amount=Decimal("0.03")
                )
            ],
        )
        assert one.validate_internal(Profile.COMFORT) == []

    def test_reason_is_extended_only(self) -> None:
        ac = AppliedTradeAllowanceCharge(
            indicator=False, actual_amount=Decimal("0.03"), reason="Rabatt"
        )
        # Validation flags the EXTENDED-only reason below EXTENDED …
        assert "GETAFIX-FIELD-PROFILE" in [
            e.code for e in ac.validate_internal(Profile.COMFORT)
        ]
        # … and rendering it below EXTENDED raises.
        with pt.raises(ProfileMismatch):
            ac.to_xml_internal(Profile.COMFORT).render(indent=True)
