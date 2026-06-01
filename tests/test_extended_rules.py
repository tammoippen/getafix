"""EXTENDED-only business rules — ``BR-FXEXT-*``.

Two themes (see ``docs/VALIDATION.md §4`` for the full table):

* Tolerance-banded replacements for the strict EN 16931
  ``BR-CO-{10,11,12,13,15}`` identities. The matching EN 16931
  rules short-circuit at EXTENDED so only the EXTENDED variants
  fire. ``BR-FXEXT-CO-04`` and ``BR-FXEXT-CO-15`` are placeholders
  whose strict identity is preserved.

* Per-VAT-category sum identities replacing ``BR-CO-17`` with one
  ``BR-FXEXT-{cat}-08`` per category, plus ``BR-FXEXT-S-09`` (the
  per-rate VAT-amount derivation check, only meaningful for
  category ``S``).
"""

from __future__ import annotations

from decimal import Decimal

import pytest as pt

from carthorse.schema import Profile
from carthorse.schema.accounting import ApplicableTradeTax
from carthorse.schema.element import ValidationErrors
from carthorse.schema.line import (
    DocumentLineDocument,
    LineMonetarySummation,
    LineTradeAgreement,
    LineTradeDelivery,
    LineTradeSettlement,
    NetTradePrice,
    Quantity,
    TradeProduct,
)
from carthorse.schema.settlement import AppliedTradeTax, LogisticsServiceCharge
from carthorse.schema.trade import TradeLineItem
from carthorse.schema.types import (
    CategoryCode,
    LineStatusReasonCode,
    UNTDID2475TaxPointDateCode,
)
from tests._fixtures import make_vat_doc


def _ext(doc):
    """Switch a make_vat_doc-built BASIC document to EXTENDED."""
    doc.context.guideline.id = Profile.EXTENDED
    return doc


def _codes(exc: ValidationErrors) -> set[str]:
    return {v.code for v in exc.errors}


class TestFXExtCOTolerance:
    """§5.2 — tolerance-banded BR-CO-* replacements."""

    def test_co_10_accepts_one_cent_per_line_drift(self) -> None:
        # Single-line doc: tolerance = 0.01 * 1 = 0.01. Drift BT-106
        # by exactly 0.01 and expect the EN 16931 BR-CO-10 to NOT
        # fire (because it short-circuits at EXTENDED) and the
        # EXTENDED variant to accept the drift.
        doc = _ext(make_vat_doc())
        doc.trade.settlement.monetary_summation.line_total += Decimal("0.01")
        # Also drift dependent totals so the per-category check stays
        # happy — we only want to assert CO-10 acceptance here.
        doc.trade.settlement.monetary_summation.tax_basis_total += Decimal("0.01")
        doc.trade.settlement.monetary_summation.grand_total += Decimal("0.01")
        doc.trade.settlement.monetary_summation.due_amount += Decimal("0.01")
        doc.validate()  # no errors

    def test_co_10_fires_beyond_tolerance(self) -> None:
        doc = _ext(make_vat_doc())
        # 0.02 drift on a single-line doc (tolerance 0.01) exceeds.
        doc.trade.settlement.monetary_summation.line_total += Decimal("0.02")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-CO-10" in _codes(e.value)

    def test_co_11_skipped_when_no_allowance_total(self) -> None:
        # Default doc has no allowance — allowance_total is None →
        # CO-11 skipped entirely (no firing, no error).
        doc = _ext(make_vat_doc())
        doc.validate()  # clean

    def test_co_12_includes_logistics_charges_in_sum(self) -> None:
        # Add a logistics charge: charge_total must equal Σ BT-99 +
        # Σ BT-X-272 (the EXTENDED variant folds logistics in).
        doc = _ext(make_vat_doc(charge_category=CategoryCode.T_S))
        doc.trade.settlement.logistics_service_charges = [
            LogisticsServiceCharge(
                description="Freight",
                applied_amount=Decimal("4.00"),
                applied_trade_tax=[
                    AppliedTradeTax(
                        category_code=CategoryCode.T_S,
                        rate_applicable_percent=Decimal("19"),
                    )
                ],
            )
        ]
        # Default charge from make_vat_doc is 3.00; with the new
        # 4.00 logistics charge the charge_total should be 7.00.
        doc.trade.settlement.monetary_summation.charge_total = Decimal("7.00")
        # Re-derive BT-109 and downstream so only CO-12 is under
        # test (the other identities also need to hold).
        # BT-106 (line total) stays at 100.00; allowances none;
        # charges 7.00; → BT-109 = 100 + 7 = 107. BT-110 = 19% of
        # 107 = 20.33; BT-112 = 127.33.
        doc.trade.settlement.monetary_summation.tax_basis_total = Decimal("107.00")
        doc.trade.settlement.trade_taxes[0].basis_amount = Decimal("107.00")
        doc.trade.settlement.trade_taxes[0].calculated_amount = Decimal("20.33")
        doc.trade.settlement.monetary_summation.tax_total = [
            type(doc.trade.settlement.monetary_summation.tax_total[0])(
                amount=Decimal("20.33"), currency_id=doc.trade.settlement.currency_code
            )
        ]
        doc.trade.settlement.monetary_summation.grand_total = Decimal("127.33")
        doc.trade.settlement.monetary_summation.due_amount = Decimal("127.33")
        doc.validate()  # clean — CO-12 must accept the logistics-inclusive sum

    def test_co_12_fires_when_logistics_omitted_from_total(self) -> None:
        doc = _ext(make_vat_doc(charge_category=CategoryCode.T_S))
        doc.trade.settlement.logistics_service_charges = [
            LogisticsServiceCharge(
                description="Freight",
                applied_amount=Decimal("4.00"),
                applied_trade_tax=[
                    AppliedTradeTax(
                        category_code=CategoryCode.T_S,
                        rate_applicable_percent=Decimal("19"),
                    )
                ],
            )
        ]
        # Leave charge_total at 3.00 (the original charge only) —
        # CO-12 should now fire because 3.00 ≠ 3.00 + 4.00.
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-CO-12" in _codes(e.value)

    def test_co_13_includes_logistics_in_bt109(self) -> None:
        # The .sch's actual XPath for CO-13 folds logistics into
        # the charge sum even though the human-readable text says
        # otherwise. BT-109 must reflect logistics charges.
        doc = _ext(make_vat_doc())
        doc.trade.settlement.logistics_service_charges = [
            LogisticsServiceCharge(
                description="Freight",
                applied_amount=Decimal("4.00"),
                applied_trade_tax=[
                    AppliedTradeTax(
                        category_code=CategoryCode.T_S,
                        rate_applicable_percent=Decimal("19"),
                    )
                ],
            )
        ]
        # If we don't push 4.00 into BT-108 / BT-109 we'd see CO-13
        # fire as well — that's the bad case. Update the totals so
        # CO-13 sees a self-consistent document.
        doc.trade.settlement.monetary_summation.charge_total = Decimal("4.00")
        doc.trade.settlement.monetary_summation.tax_basis_total = Decimal("104.00")
        doc.trade.settlement.trade_taxes[0].basis_amount = Decimal("104.00")
        doc.trade.settlement.trade_taxes[0].calculated_amount = Decimal("19.76")
        doc.trade.settlement.monetary_summation.tax_total = [
            type(doc.trade.settlement.monetary_summation.tax_total[0])(
                amount=Decimal("19.76"), currency_id=doc.trade.settlement.currency_code
            )
        ]
        doc.trade.settlement.monetary_summation.grand_total = Decimal("123.76")
        doc.trade.settlement.monetary_summation.due_amount = Decimal("123.76")
        doc.validate()  # clean

    def test_co_13_fires_when_bt109_excludes_logistics(self) -> None:
        doc = _ext(make_vat_doc())
        doc.trade.settlement.logistics_service_charges = [
            LogisticsServiceCharge(
                description="Freight",
                applied_amount=Decimal("4.00"),
                applied_trade_tax=[
                    AppliedTradeTax(
                        category_code=CategoryCode.T_S,
                        rate_applicable_percent=Decimal("19"),
                    )
                ],
            )
        ]
        doc.trade.settlement.monetary_summation.charge_total = Decimal("4.00")
        # Leave tax_basis_total at 100.00 (i.e. exclude the
        # logistics contribution) → CO-13 should fire.
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-CO-13" in _codes(e.value)


class TestFXExtPerCategorySums:
    """§5.3 — per-VAT-category sum identities (BR-FXEXT-{cat}-08 / -09)."""

    def test_s_08_passes_on_default_doc(self) -> None:
        # Default make_vat_doc has one S-rated line at 100 / 19% →
        # BG-23 row basis=100. The category-S sum identity should
        # accept it cleanly.
        doc = _ext(make_vat_doc())
        doc.validate()

    def test_s_08_fires_on_basis_mismatch(self) -> None:
        doc = _ext(make_vat_doc())
        # Inflate BG-23 BT-116 beyond what the lines justify.
        doc.trade.settlement.trade_taxes[0].basis_amount = Decimal("110.00")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-S-08" in _codes(e.value)

    def test_s_09_fires_on_tax_amount_mismatch(self) -> None:
        doc = _ext(make_vat_doc())
        # BG-23 row: 100 * 19% = 19.00. Set calculated_amount way
        # off to trigger -09 — but keep tax_basis_total / grand
        # consistent so the cross-rule machinery doesn't drown the
        # signal.
        doc.trade.settlement.trade_taxes[0].calculated_amount = Decimal("30.00")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-S-09" in _codes(e.value)


def _add_line(
    doc,
    *,
    line_id: str,
    line_total: Decimal,
    parent_line_id: str | None = None,
    status_reason_code: LineStatusReasonCode | None = None,
) -> None:
    """Append a minimal additional invoice line; used to build
    sub-invoice-line scenarios on top of ``make_vat_doc()``."""
    doc.trade.items.append(
        TradeLineItem(
            associated_document=DocumentLineDocument(
                line_id=line_id,
                parent_line_id=parent_line_id,
                status_reason_code=status_reason_code,
            ),
            product=TradeProduct(name=f"Item {line_id}"),
            agreement=LineTradeAgreement(
                net_price=NetTradePrice(charge_amount=line_total)
            ),
            delivery=LineTradeDelivery(
                billed_quantity=Quantity(value=Decimal("1"), unit_code="C62")
            ),
            settlement=LineTradeSettlement(
                applicable_trade_tax=ApplicableTradeTax(
                    category_code=CategoryCode.T_S,
                    due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                    rate_applicable_percent=Decimal("19"),
                ),
                monetary_summation=LineMonetarySummation(line_total=line_total),
            ),
        )
    )


class TestFXExtSubInvoiceLineWalker:
    """§5.1 — cross-line walker enforcing the sub-invoice-line tree
    constraints (BR-FXEXT-06, -08, -11)."""

    def test_br_fxext_06_fires_when_subtype_missing_on_parent(self) -> None:
        doc = _ext(make_vat_doc())
        # The default line has line_id="1"; mark it as a parent by
        # adding a child whose ParentLineID points to it, but do not
        # set status_reason_code on the parent.
        _add_line(
            doc,
            line_id="1a",
            line_total=Decimal("100"),
            parent_line_id="1",
            status_reason_code=LineStatusReasonCode.DETAIL,
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-06" in _codes(e.value)

    def test_br_fxext_06_fires_when_subtype_missing_on_child(self) -> None:
        doc = _ext(make_vat_doc())
        # First mark the default line as GROUP so it can be a parent.
        doc.trade.items[
            0
        ].associated_document.status_reason_code = LineStatusReasonCode.GROUP
        # Add a child without status_reason_code — should fire.
        _add_line(doc, line_id="1a", line_total=Decimal("100"), parent_line_id="1")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-06" in _codes(e.value)

    def test_br_fxext_11_fires_on_orphan_parent_ref(self) -> None:
        doc = _ext(make_vat_doc())
        _add_line(
            doc,
            line_id="2",
            line_total=Decimal("100"),
            parent_line_id="does-not-exist",
            status_reason_code=LineStatusReasonCode.DETAIL,
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-11" in _codes(e.value)

    def test_br_fxext_08_fires_on_group_sum_mismatch(self) -> None:
        # Build: GROUP "G" with line_total=10 but child totals = 100.
        doc = _ext(make_vat_doc())
        # Make the default line the GROUP, override its line_total.
        ad0 = doc.trade.items[0].associated_document
        ad0.line_id = "G"
        ad0.status_reason_code = LineStatusReasonCode.GROUP
        doc.trade.items[0].settlement.monetary_summation.line_total = Decimal("10")
        _add_line(
            doc,
            line_id="G1",
            line_total=Decimal("100"),
            parent_line_id="G",
            status_reason_code=LineStatusReasonCode.DETAIL,
        )
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-08" in _codes(e.value)

    def test_br_fxext_08_excludes_information_children_from_sum(self) -> None:
        # GROUP "G" with line_total=100; one DETAIL child of 100 plus
        # one INFORMATION child of 99 (should NOT count).
        doc = _ext(make_vat_doc())
        ad0 = doc.trade.items[0].associated_document
        ad0.line_id = "G"
        ad0.status_reason_code = LineStatusReasonCode.GROUP
        doc.trade.items[0].settlement.monetary_summation.line_total = Decimal("100")
        _add_line(
            doc,
            line_id="G1",
            line_total=Decimal("100"),
            parent_line_id="G",
            status_reason_code=LineStatusReasonCode.DETAIL,
        )
        _add_line(
            doc,
            line_id="G2",
            line_total=Decimal("99"),
            parent_line_id="G",
            status_reason_code=LineStatusReasonCode.INFORMATION,
        )
        # If INFORMATION was counted, sum would be 199 ≠ 100 and CO-08
        # would fire. Validate: BR-FXEXT-08 must not appear.
        # (Other rules may fire because the doc is intentionally
        # malformed elsewhere — we only assert BR-FXEXT-08 is silent.)
        try:
            doc.validate()
            codes: set[str] = set()
        except ValidationErrors as e:
            codes = _codes(e)
        assert "BR-FXEXT-08" not in codes


class TestFXExtSubInvoiceLineSampleClean:
    """The ZF24 SubInvoiceLines Hardware sample (2 GROUP + 4 DETAIL)
    should validate cleanly — exercises the walker on a real
    well-formed sub-invoice-line tree."""

    def test_hardware_sample_passes_full_validation(self) -> None:
        from pathlib import Path

        from lxml import etree

        from carthorse.schema import Document

        xml = Path(
            "tests/samples/EXTENDED_zf24_SubInvoiceLines_Hardware.xml"
        ).read_bytes()
        doc = Document.from_xml(etree.fromstring(xml))
        # No errors — every parent ref resolves, GROUP totals match
        # children, subtypes are set everywhere they need to be.
        doc.validate()


class TestFXExtLineQualifiers:
    """§5.4 — BR-FXEXT-22/23/24/26/27 and BR-FXEXT-CO-04 promoted
    from placeholders to real DETAIL-qualified checks.

    Each rule fires when an EXTENDED DETAIL / unset line is missing
    a field the spec mandates; GROUP / INFORMATION lines may legitimately
    omit the same field without firing.
    """

    def test_br_fxext_22_fires_on_detail_without_quantity(self) -> None:
        doc = _ext(make_vat_doc())
        doc.trade.items[0].delivery.billed_quantity = None
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-22" in _codes(e.value)

    def test_br_fxext_22_silent_on_group_without_quantity(self) -> None:
        doc = _ext(make_vat_doc())
        doc.trade.items[
            0
        ].associated_document.status_reason_code = LineStatusReasonCode.GROUP
        doc.trade.items[0].delivery.billed_quantity = None
        try:
            doc.validate()
            codes: set[str] = set()
        except ValidationErrors as e:
            codes = _codes(e)
        assert "BR-FXEXT-22" not in codes

    def test_br_fxext_24_fires_on_detail_without_line_total(self) -> None:
        doc = _ext(make_vat_doc())
        doc.trade.items[0].settlement.monetary_summation.line_total = None
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-24" in _codes(e.value)

    def test_br_fxext_26_fires_on_detail_without_net_price(self) -> None:
        doc = _ext(make_vat_doc())
        doc.trade.items[0].agreement.net_price = None
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-26" in _codes(e.value)

    def test_br_fxext_27_fires_on_detail_with_negative_price(self) -> None:
        doc = _ext(make_vat_doc())
        # Avoid BR-27 by ensuring the construction reaches validation:
        # set a negative net price *after* construction.
        doc.trade.items[0].agreement.net_price.charge_amount = Decimal("-1.00")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        codes = _codes(e.value)
        # The EXTENDED variant fires; the EN16931 BR-27 short-circuits.
        assert "BR-FXEXT-27" in codes
        assert "BR-27" not in codes

    def test_br_fxext_27_silent_on_group_with_negative_price(self) -> None:
        doc = _ext(make_vat_doc())
        doc.trade.items[
            0
        ].associated_document.status_reason_code = LineStatusReasonCode.GROUP
        doc.trade.items[0].agreement.net_price.charge_amount = Decimal("-1.00")
        try:
            doc.validate()
            codes: set[str] = set()
        except ValidationErrors as e:
            codes = _codes(e)
        assert "BR-FXEXT-27" not in codes

    def test_br_fxext_co_04_fires_on_detail_without_line_vat(self) -> None:
        doc = _ext(make_vat_doc())
        doc.trade.items[0].settlement.applicable_trade_tax = None
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-FXEXT-CO-04" in _codes(e.value)

    def test_br_fxext_co_04_silent_on_group_without_line_vat(self) -> None:
        doc = _ext(make_vat_doc())
        doc.trade.items[
            0
        ].associated_document.status_reason_code = LineStatusReasonCode.GROUP
        doc.trade.items[0].settlement.applicable_trade_tax = None
        try:
            doc.validate()
            codes: set[str] = set()
        except ValidationErrors as e:
            codes = _codes(e)
        assert "BR-FXEXT-CO-04" not in codes


class TestEN16931LineFieldChecks:
    """EN 16931 BR-22/23/24/26/BR-CO-4 — line-level field-presence
    rules that became explicit when their backing dataclass fields
    were relaxed to ``Optional`` (so EXTENDED GROUP / INFORMATION
    lines can drop them).
    """

    def test_br_22_fires_at_basic_when_quantity_missing(self) -> None:
        doc = make_vat_doc()
        doc.trade.items[0].delivery.billed_quantity = None
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-22" in _codes(e.value)

    def test_br_24_fires_at_basic_when_line_total_missing(self) -> None:
        doc = make_vat_doc()
        doc.trade.items[0].settlement.monetary_summation.line_total = None
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-24" in _codes(e.value)

    def test_br_26_fires_at_basic_when_net_price_missing(self) -> None:
        doc = make_vat_doc()
        doc.trade.items[0].agreement.net_price = None
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-26" in _codes(e.value)

    def test_br_co_4_fires_at_basic_when_line_vat_missing(self) -> None:
        doc = make_vat_doc()
        doc.trade.items[0].settlement.applicable_trade_tax = None
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "BR-CO-4" in _codes(e.value)

    def test_br_22_silent_at_extended(self) -> None:
        # Same setup as above but at EXTENDED — BR-22 short-circuits
        # and BR-FXEXT-22 takes over (the DETAIL/unset filter applies).
        doc = _ext(make_vat_doc())
        doc.trade.items[0].delivery.billed_quantity = None
        try:
            doc.validate()
            codes: set[str] = set()
        except ValidationErrors as e:
            codes = _codes(e)
        assert "BR-22" not in codes


class TestFXExtProfileGating:
    """Carthorse-emitted profile gates on EXTENDED-only fields —
    ``CARTHORSE-FIELD-PROFILE`` and ``CARTHORSE-FIELD-CARDINALITY``."""

    def test_partial_payment_amount_on_basic_wl_fires(self) -> None:
        # Default doc is BASIC. Set an EXTENDED-only field; carthorse
        # would silently drop it at render — but the new validator
        # surfaces it as CARTHORSE-FIELD-PROFILE.
        doc = make_vat_doc()
        doc.trade.settlement.terms[0].partial_payment_amount = Decimal("50.00")
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "CARTHORSE-FIELD-PROFILE" in _codes(e.value)

    def test_partial_payment_amount_on_extended_passes(self) -> None:
        doc = _ext(make_vat_doc())
        doc.trade.settlement.terms[0].partial_payment_amount = Decimal("50.00")
        doc.validate()  # clean — EXTENDED allows the field

    def test_terms_list_capped_below_extended(self) -> None:
        doc = make_vat_doc()  # BASIC profile
        doc.trade.settlement.terms = [
            doc.trade.settlement.terms[0],
            doc.trade.settlement.terms[0],
        ]
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert "CARTHORSE-FIELD-CARDINALITY" in _codes(e.value)

    def test_terms_list_unbounded_at_extended(self) -> None:
        doc = _ext(make_vat_doc())
        doc.trade.settlement.terms = [
            doc.trade.settlement.terms[0],
            doc.trade.settlement.terms[0],
        ]
        # Cardinality cap doesn't fire at EXTENDED. (Other rules might,
        # but they're not the focus of this test — assert only that
        # the cardinality code isn't emitted.)
        try:
            doc.validate()
            codes: set[str] = set()
        except ValidationErrors as e:
            codes = _codes(e)
        assert "CARTHORSE-FIELD-CARDINALITY" not in codes
