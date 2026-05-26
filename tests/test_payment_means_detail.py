"""§3.3 — header payment-means detail (BT-82 / BG-18 / BT-85 / BT-86).

EN 16931 enriches the BASIC_WL ``PaymentMeans`` (BG-16) with four
optional sub-elements:

* **BT-82 ``Information``** — free-text payment-means description.
* **BG-18 ``ApplicableTradeSettlementFinancialCard``** — card details
  with ``ID`` (BT-87 — PAN, last 4..6 digits) and optional
  ``CardholderName`` (BT-88).
* **BT-85 ``AccountName``** on
  ``PayeePartyCreditorFinancialAccount`` — the account holder name.
* **BG-17 ``PayeeSpecifiedCreditorFinancialInstitution``** — single
  ``BICID`` (BT-86) identifying the receiving bank.

All four ship at COMFORT+. ``BR-51`` (PAN regex 4..6 digits) is wired
in a follow-up step under §4.1.
"""

from __future__ import annotations

import pytest as pt

from carthorse.schema import Profile
from carthorse.schema.element import ProfileMismatch
from carthorse.schema.settlement import (
    CreditorFinancialInstitution,
    FinancialCard,
    PayeePartyCreditorFinancialAccount,
    PaymentMeans,
)
from carthorse.schema.types import UNTDID4461PaymentMeansCode
from tests._fixtures import wrap_subtree
from tests._parsers import ParseFromBytes


class TestPaymentMeansInformation:
    def test_construct(self) -> None:
        pm = PaymentMeans(
            type_code=UNTDID4461PaymentMeansCode.CODE_58,
            information="Pay before due date",
        )
        assert pm.information == "Pay before due date"

    def test_renders_at_comfort(self) -> None:
        pm = PaymentMeans(
            type_code=UNTDID4461PaymentMeansCode.CODE_58, information="hello"
        )
        xml = pm.to_xml_internal(Profile.COMFORT).render(indent=True)
        assert "<ram:Information>" in xml
        assert "hello" in xml

    def test_below_comfort_raises(self) -> None:
        pm = PaymentMeans(
            type_code=UNTDID4461PaymentMeansCode.CODE_58, information="hello"
        )
        with pt.raises(ProfileMismatch):
            pm.to_xml_internal(Profile.BASIC_WL).render(indent=True)


class TestFinancialCard:
    def test_construct_with_pan_only(self) -> None:
        card = FinancialCard(id="1234")
        assert card.id == "1234"
        assert card.cardholder_name is None

    def test_construct_with_cardholder(self) -> None:
        card = FinancialCard(id="1234", cardholder_name="Alice")
        assert card.cardholder_name == "Alice"

    def test_renders_id_and_name(self) -> None:
        card = FinancialCard(id="1234", cardholder_name="Alice")
        xml = card.to_xml_internal(Profile.COMFORT).render(indent=True)
        assert "<ram:ID>" in xml
        assert "1234" in xml
        assert "<ram:CardholderName>" in xml
        assert "Alice" in xml

    def test_parent_render_below_comfort_raises(self) -> None:
        pm = PaymentMeans(
            type_code=UNTDID4461PaymentMeansCode.CODE_48,
            financial_card=FinancialCard(id="1234"),
        )
        with pt.raises(ProfileMismatch):
            pm.to_xml_internal(Profile.BASIC_WL).render(indent=True)


class TestPayeeAccountName:
    def test_renders_account_name(self) -> None:
        acct = PayeePartyCreditorFinancialAccount(
            iban_id="DE89370400440532013000", account_name="Seller GmbH"
        )
        xml = acct.to_xml_internal(Profile.COMFORT).render(indent=True)
        assert "<ram:AccountName>" in xml
        assert "Seller GmbH" in xml

    def test_account_name_below_comfort_raises(self) -> None:
        acct = PayeePartyCreditorFinancialAccount(
            iban_id="DE89370400440532013000", account_name="Seller GmbH"
        )
        with pt.raises(ProfileMismatch):
            acct.to_xml_internal(Profile.BASIC_WL).render(indent=True)


class TestCreditorFinancialInstitution:
    def test_construct_with_bic(self) -> None:
        inst = CreditorFinancialInstitution(bic_id="DEUTDEFFXXX")
        assert inst.bic_id == "DEUTDEFFXXX"

    def test_renders_bic(self) -> None:
        inst = CreditorFinancialInstitution(bic_id="DEUTDEFFXXX")
        xml = inst.to_xml_internal(Profile.COMFORT).render(indent=True)
        assert "<ram:BICID>" in xml
        assert "DEUTDEFFXXX" in xml

    def test_parent_render_below_comfort_raises(self) -> None:
        pm = PaymentMeans(
            type_code=UNTDID4461PaymentMeansCode.CODE_58,
            creditor_institution=CreditorFinancialInstitution(bic_id="DEUTDEFFXXX"),
        )
        with pt.raises(ProfileMismatch):
            pm.to_xml_internal(Profile.BASIC_WL).render(indent=True)


class TestPaymentMeansRoundTrip:
    def test_full_payment_means_round_trip(self, parser: ParseFromBytes) -> None:
        pm = PaymentMeans(
            type_code=UNTDID4461PaymentMeansCode.CODE_58,
            information="SEPA credit transfer, due in 30 days",
            financial_card=FinancialCard(id="1234", cardholder_name="Alice"),
            payee=PayeePartyCreditorFinancialAccount(
                iban_id="DE89370400440532013000", account_name="Seller GmbH"
            ),
            creditor_institution=CreditorFinancialInstitution(bic_id="DEUTDEFFXXX"),
        )
        xml = pm.to_xml_internal(Profile.COMFORT).render(indent=True)
        parsed = PaymentMeans.from_xml(
            parser(wrap_subtree(xml, "SpecifiedTradeSettlementPaymentMeans"))
        )
        assert parsed == pm
