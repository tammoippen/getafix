"""Per-VAT-category exemption-reason constraints — BR-X-10.

For every VAT category X, the corresponding BG-23 row either requires
or forbids the VAT exemption reason (BT-120 text and/or BT-121 code):

* **Forbids** (rate > 0 or VAT applies): S, Z, AF/IGIC (L), AG/IPSI (M).
* **Requires** (rate = 0 / not subject): E, AE, G, IC (K), O.
"""

from __future__ import annotations

import pytest as pt

from getafix.schema.element import ValidationErrors
from getafix.schema.types import CategoryCode
from tests._fixtures import make_vat_doc


def _set_exemption(
    doc, *, reason: str | None = None, reason_code: str | None = None
) -> None:
    doc.trade.settlement.trade_taxes[0].exemption_reason = reason
    doc.trade.settlement.trade_taxes[0].exemption_reason_code = reason_code


class TestForbidsExemption:
    @pt.mark.parametrize(
        ("category", "prefix"),
        [
            (CategoryCode.T_S, "S"),
            (CategoryCode.T_Z, "Z"),
            (CategoryCode.T_L, "AF"),
            (CategoryCode.T_M, "AG"),
        ],
    )
    def test_exemption_text_forbidden(
        self, category: CategoryCode, prefix: str
    ) -> None:
        doc = make_vat_doc(line_category=category)
        _set_exemption(doc, reason="should-not-be-here")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == f"BR-{prefix}-10" for v in e.value.errors)

    @pt.mark.parametrize(
        ("category", "prefix"),
        [
            (CategoryCode.T_S, "S"),
            (CategoryCode.T_Z, "Z"),
            (CategoryCode.T_L, "AF"),
            (CategoryCode.T_M, "AG"),
        ],
    )
    def test_exemption_code_forbidden(
        self, category: CategoryCode, prefix: str
    ) -> None:
        doc = make_vat_doc(line_category=category)
        _set_exemption(doc, reason_code="VATEX-EU-79-C")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == f"BR-{prefix}-10" for v in e.value.errors)


class TestRequiresExemption:
    @pt.mark.parametrize(
        ("category", "prefix", "seller_va", "buyer_va"),
        [
            # E / AE / G / K all need party VAT; the fixture defaults already
            # cover the basic combinations. O wants no Seller/Buyer VAT IDs
            # per BR-O-2..4.
            (CategoryCode.T_E, "E", "DE123456789", None),
            (CategoryCode.T_AE, "AE", "DE123456789", "DE987654321"),
        ],
    )
    def test_missing_exemption_emits_x10(
        self,
        category: CategoryCode,
        prefix: str,
        seller_va: str | None,
        buyer_va: str | None,
    ) -> None:
        doc = make_vat_doc(
            line_category=category, seller_va=seller_va, buyer_va=buyer_va
        )
        _set_exemption(doc, reason=None, reason_code=None)
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == f"BR-{prefix}-10" for v in e.value.errors)

    def test_text_alone_passes(self) -> None:
        doc = make_vat_doc(line_category=CategoryCode.T_E, buyer_va=None)
        _set_exemption(doc, reason="Article 132 exempt")
        try:
            doc.validate()
            errors: list = []
        except ValidationErrors as e:
            errors = list(e.errors)
        assert not any(v.code == "BR-E-10" for v in errors), errors

    def test_code_alone_passes(self) -> None:
        doc = make_vat_doc(line_category=CategoryCode.T_E, buyer_va=None)
        _set_exemption(doc, reason_code="VATEX-EU-132")
        try:
            doc.validate()
            errors: list = []
        except ValidationErrors as e:
            errors = list(e.errors)
        assert not any(v.code == "BR-E-10" for v in errors), errors
