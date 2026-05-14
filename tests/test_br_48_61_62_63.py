"""BR-48 / BR-61 / BR-62 / BR-63 — open structural rules at BASIC.

* **BR-48** — VAT category rate (BT-119) required on every
  ``ApplicableTradeTax`` row, *except* when the category code is
  ``O`` (Services outside scope of tax).
* **BR-61** — when the Payment means type code (BT-81) is a credit
  transfer (UNTDID 4461 codes ``30``, ``42``, ``58``), the Payment
  account identifier (BT-84) must be present.
* **BR-62** — Seller electronic address (BT-34) requires a
  ``schemeID``.
* **BR-63** — Buyer electronic address (BT-49) requires a
  ``schemeID``.

All four rules apply at BASIC_WL+ (where the source structures first
appear).
"""

from __future__ import annotations

from decimal import Decimal

import pytest as pt

from carthorse.schema import Document, Profile
from carthorse.schema.accounting import ApplicableTradeTax
from carthorse.schema.element import ValidationErrors
from carthorse.schema.party import URIID, URIUniversalCommunication
from carthorse.schema.settlement import PayeePartyCreditorFinancialAccount, PaymentMeans
from carthorse.schema.types import CategoryCode
from tests._fixtures import make_vat_doc


def _set_seller_email(doc: Document, *, scheme_id: str | None) -> None:
    doc.trade.agreement.seller.electronic_address = URIUniversalCommunication(
        uri_id=URIID(id="seller@example.com", scheme_id=scheme_id)
    )


def _set_buyer_email(doc: Document, *, scheme_id: str | None) -> None:
    doc.trade.agreement.buyer.electronic_address = URIUniversalCommunication(
        uri_id=URIID(id="buyer@example.com", scheme_id=scheme_id)
    )


class TestBr48:
    def test_passes_when_rate_present(self) -> None:
        tax = ApplicableTradeTax(
            calculated_amount=Decimal("0"),
            basis_amount=Decimal("0"),
            category_code=CategoryCode.T_S,
            rate_applicable_percent=Decimal("19"),
            due_date_code="5",
        )
        errors = [
            e for v in ApplicableTradeTax._validators for e in v(tax, Profile.BASIC_WL)
        ]
        assert not any(e.code == "BR-48" for e in errors), errors

    def test_passes_for_o_without_rate(self) -> None:
        tax = ApplicableTradeTax(
            calculated_amount=Decimal("0"),
            basis_amount=Decimal("0"),
            category_code=CategoryCode.T_O,
            due_date_code="5",
        )
        errors = [
            e for v in ApplicableTradeTax._validators for e in v(tax, Profile.BASIC_WL)
        ]
        assert not any(e.code == "BR-48" for e in errors), errors

    def test_fails_when_rate_missing_and_not_o(self) -> None:
        tax = ApplicableTradeTax(
            calculated_amount=Decimal("0"),
            basis_amount=Decimal("0"),
            category_code=CategoryCode.T_S,
            due_date_code="5",
        )
        errors = [
            e for v in ApplicableTradeTax._validators for e in v(tax, Profile.BASIC_WL)
        ]
        assert any(e.code == "BR-48" for e in errors), errors


class TestBr61:
    @pt.mark.parametrize("code", ["30", "42", "58"])
    def test_fails_when_credit_transfer_lacks_iban(self, code: str) -> None:
        doc = make_vat_doc()
        doc.trade.settlement.payment_means = [
            PaymentMeans(
                type_code=code,
                payee=PayeePartyCreditorFinancialAccount(proprietary_id="ACC-1"),
            )
        ]
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-61" for v in e.value.errors)

    @pt.mark.parametrize("code", ["30", "42", "58"])
    def test_passes_when_credit_transfer_has_iban(self, code: str) -> None:
        doc = make_vat_doc()
        doc.trade.settlement.payment_means = [
            PaymentMeans(
                type_code=code,
                payee=PayeePartyCreditorFinancialAccount(
                    iban_id="DE89370400440532013000"
                ),
            )
        ]
        doc.validate()

    @pt.mark.parametrize("code", ["10", "20", "49", "57", "59", "97"])
    def test_passes_when_non_credit_transfer_no_iban(self, code: str) -> None:
        doc = make_vat_doc()
        doc.trade.settlement.payment_means = [PaymentMeans(type_code=code)]
        doc.validate()


class TestBr62:
    def test_fails_when_seller_address_missing_scheme_id(self) -> None:
        doc = make_vat_doc()
        _set_seller_email(doc, scheme_id=None)
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-62" for v in e.value.errors)

    def test_passes_when_seller_address_has_scheme_id(self) -> None:
        doc = make_vat_doc()
        _set_seller_email(doc, scheme_id="EM")
        doc.validate()


class TestBr63:
    def test_fails_when_buyer_address_missing_scheme_id(self) -> None:
        doc = make_vat_doc()
        _set_buyer_email(doc, scheme_id=None)
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-63" for v in e.value.errors)

    def test_passes_when_buyer_address_has_scheme_id(self) -> None:
        doc = make_vat_doc()
        _set_buyer_email(doc, scheme_id="EM")
        doc.validate()
