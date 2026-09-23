"""Advance payments (BG-X-45) — getafix-specific rules.

* ``GETAFIX-ADV-PREPAID`` — Σ BT-X-291 must not exceed BT-113.
* ``GETAFIX-FIELD-REQUIRED`` — BT-X-293 must be present, and is
  derived on construction when a single VAT entry has a rate.
* ``GETAFIX-ADV-VAT-PLAUSIBLE`` — warning when BT-X-293 does not fit
  BT-X-291 at the entry's rate.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest as pt
from lxml import etree

from getafix.cli import main
from getafix.errors import ValidationErrors, ValidationWarning
from getafix.schema.document import Document
from getafix.schema.settlement import AdvancePayment, AdvancePaymentTradeTax
from getafix.schema.types import CategoryCode, Profile

SAMPLES = Path(__file__).parent / "samples"
# One advance of 119.00 incl. 19.00 VAT at 19 %; BT-113 = 119.00.
SAMPLE = SAMPLES / "EXTENDED_synth_settlement_parties.xml"
# Upstream sample whose advances report 1900 VAT on 2975.00 gross.
IMPLAUSIBLE_SAMPLE = SAMPLES / "EXTENDED_zf24_Projektabschluss.xml"


def _load(path: Path = SAMPLE) -> Document:
    return Document.from_xml(etree.parse(str(path)).getroot())


def _tax(
    amount: str | None,
    rate: str | None = "19",
    category: CategoryCode = CategoryCode.T_S,
) -> AdvancePaymentTradeTax:
    return AdvancePaymentTradeTax(
        calculated_amount=None if amount is None else Decimal(amount),
        category_code=category,
        rate_applicable_percent=None if rate is None else Decimal(rate),
    )


def _codes(exc: ValidationErrors) -> set[str]:
    return {e.code for e in exc.errors}


class TestPrepaidSum:
    def test_matching_sum_passes(self) -> None:
        assert _load().validate() == []

    def test_prepaid_total_above_sum_passes(self) -> None:
        """BT-113 may include prepayments that are not itemised."""
        doc = _load()
        summation = doc.trade.settlement.monetary_summation
        summation.prepaid_total = Decimal("200.00")
        summation.due_amount = summation.grand_total - Decimal("200.00")
        assert doc.validate() == []

    def test_sum_above_prepaid_total_fires(self) -> None:
        doc = _load()
        summation = doc.trade.settlement.monetary_summation
        summation.prepaid_total = Decimal("100.00")
        summation.due_amount = summation.grand_total - Decimal("100.00")
        with pt.raises(ValidationErrors) as e:
            _ = doc.validate()
        assert _codes(e.value) == {"GETAFIX-ADV-PREPAID"}

    def test_missing_bt_113_fires(self) -> None:
        doc = _load()
        summation = doc.trade.settlement.monetary_summation
        summation.prepaid_total = None
        summation.due_amount = summation.grand_total
        with pt.raises(ValidationErrors) as e:
            _ = doc.validate()
        assert _codes(e.value) == {"GETAFIX-ADV-PREPAID"}

    def test_several_advances_are_summed(self) -> None:
        doc = _load()
        advances = doc.trade.settlement.advance_payments
        assert advances is not None
        advances.append(
            AdvancePayment(
                paid_amount=Decimal("11.90"), included_trade_tax=[_tax("1.90")]
            )
        )
        summation = doc.trade.settlement.monetary_summation
        summation.prepaid_total = Decimal("130.90")
        summation.due_amount = summation.grand_total - Decimal("130.90")
        assert doc.validate() == []

    def test_tax_totals_unaffected_by_advances(self) -> None:
        """BT-110 covers the whole invoice; prepaid VAT is not deducted."""
        doc = _load()
        tax_total = doc.trade.settlement.monetary_summation.tax_total
        assert tax_total is not None
        assert tax_total[0].amount == Decimal("76.67")
        assert doc.validate() == []


class TestVatAmountRequired:
    def test_derived_from_single_rate(self) -> None:
        adv = AdvancePayment(
            paid_amount=Decimal("2975.00"), included_trade_tax=[_tax(None)]
        )
        assert adv.included_trade_tax[0].calculated_amount == Decimal("475.00")

    def test_derivation_rounds_half_away_from_zero(self) -> None:
        # 10.05 * 7 / 107 = 0.6574… → 0.66
        adv = AdvancePayment(
            paid_amount=Decimal("10.05"), included_trade_tax=[_tax(None, rate="7")]
        )
        assert adv.included_trade_tax[0].calculated_amount == Decimal("0.66")

    def test_explicit_amount_kept(self) -> None:
        adv = AdvancePayment(
            paid_amount=Decimal("119.00"), included_trade_tax=[_tax("18.99")]
        )
        assert adv.included_trade_tax[0].calculated_amount == Decimal("18.99")

    def test_derived_amount_is_rendered(self) -> None:
        doc = _load()
        advances = doc.trade.settlement.advance_payments
        assert advances is not None
        advances[0] = AdvancePayment(
            paid_amount=Decimal("119.00"), included_trade_tax=[_tax(None)]
        )
        assert "<ram:CalculatedAmount>19.00</ram:CalculatedAmount>" in str(doc.to_xml())

    @pt.mark.parametrize(
        "taxes",
        [
            pt.param([_tax(None, rate=None)], id="no-rate"),
            pt.param([_tax(None), _tax("5.00", rate="7")], id="several-entries"),
        ],
    )
    def test_underivable_amount_fires(
        self, taxes: list[AdvancePaymentTradeTax]
    ) -> None:
        adv = AdvancePayment(paid_amount=Decimal("119.00"), included_trade_tax=taxes)
        assert adv.included_trade_tax[0].calculated_amount is None
        codes = [e.code for e in adv.validate_internal(Profile.EXTENDED)]
        assert "GETAFIX-FIELD-REQUIRED" in codes

    def test_unset_after_construction_fails_validate(self) -> None:
        doc = _load()
        advances = doc.trade.settlement.advance_payments
        assert advances is not None
        advances[0].included_trade_tax[0].calculated_amount = None
        with pt.raises(ValidationErrors) as e:
            _ = doc.validate()
        assert _codes(e.value) == {"GETAFIX-FIELD-REQUIRED"}


class TestVatPlausibility:
    @pt.mark.parametrize(
        ("paid", "taxes"),
        [
            pt.param("119.00", [_tax("19.00")], id="exact"),
            pt.param("119.00", [_tax("19.01")], id="one-cent-off"),
            pt.param("-119.00", [_tax("-19.00")], id="negative"),
            pt.param(
                "100.00", [_tax("0.00", rate="0", category=CategoryCode.T_Z)], id="zero"
            ),
            pt.param("226.00", [_tax("19.00"), _tax("7.00", rate="7")], id="mixed"),
            pt.param("119.00", [_tax("1900", rate=None)], id="no-rate-skips"),
        ],
    )
    def test_plausible(self, paid: str, taxes: list[AdvancePaymentTradeTax]) -> None:
        adv = AdvancePayment(paid_amount=Decimal(paid), included_trade_tax=taxes)
        assert adv.validate_internal(Profile.EXTENDED) == []

    @pt.mark.parametrize(
        ("paid", "taxes"),
        [
            pt.param("119.00", [_tax("19.02")], id="two-cents-off"),
            pt.param("2975.00", [_tax("1900")], id="projektabschluss"),
            pt.param(
                "226.00", [_tax("40.00"), _tax("7.00", rate="7")], id="mixed-too-high"
            ),
            pt.param("119.00", [_tax("19.00", rate="7")], id="wrong-rate"),
        ],
    )
    def test_implausible_warns(
        self, paid: str, taxes: list[AdvancePaymentTradeTax]
    ) -> None:
        adv = AdvancePayment(paid_amount=Decimal(paid), included_trade_tax=taxes)
        findings = adv.validate_internal(Profile.EXTENDED)
        assert [e.code for e in findings] == ["GETAFIX-ADV-VAT-PLAUSIBLE"]
        assert isinstance(findings[0], ValidationWarning)

    def test_sample_warns_without_raising(self) -> None:
        warnings = _load(IMPLAUSIBLE_SAMPLE).validate()
        assert [w.code for w in warnings] == ["GETAFIX-ADV-VAT-PLAUSIBLE"] * 4

    def test_warning_does_not_hide_errors(self) -> None:
        doc = _load(IMPLAUSIBLE_SAMPLE)
        summation = doc.trade.settlement.monetary_summation
        summation.prepaid_total = Decimal("0.00")
        summation.due_amount = summation.grand_total
        with pt.raises(ValidationErrors) as e:
            _ = doc.validate()
        assert _codes(e.value) == {"GETAFIX-ADV-PREPAID"}

    def test_cli_prints_warnings_and_exits_zero(
        self, capsys: pt.CaptureFixture[str]
    ) -> None:
        assert main([str(IMPLAUSIBLE_SAMPLE)]) == 0
        out = capsys.readouterr().out
        assert "No validation errors" in out
        assert "Validation warnings (4)" in out
        assert "GETAFIX-ADV-VAT-PLAUSIBLE" in out
