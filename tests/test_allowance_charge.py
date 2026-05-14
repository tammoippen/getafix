"""BR-CO-21..24 — line-level allowance / charge reason coupling.

Header-level BR-CO-21/22 are exercised by sample / hypothesis
round-trips; this file owns the line-level (BR-CO-23 / BR-CO-24)
variants, where the rule code distinguishes line context from header.
"""

from __future__ import annotations

from decimal import Decimal

import pytest as pt

from carthorse.schema import Document
from carthorse.schema.accounting import LineTradeAllowanceCharge
from carthorse.schema.element import ValidationErrors
from tests._fixtures import make_vat_doc


class TestBrCoLineCoupling:
    """BR-CO-23 / BR-CO-24 — line-level allowance / charge reason
    coupling. Same shape as BR-CO-21/22 (header) but raises a
    line-context rule code so error messages are unambiguous."""

    def _add_line_allowance(
        self,
        doc: Document,
        *,
        indicator: bool,
        reason: str | None = None,
        reason_code: str | None = None,
    ) -> None:
        line = doc.trade.items[0]
        line.settlement.allowance_charge = [
            LineTradeAllowanceCharge(
                indicator=indicator,
                actual_amount=Decimal("1.00"),
                reason=reason,
                reason_code=reason_code,
            )
        ]

    def test_br_co_23_line_allowance_needs_reason_or_code(self) -> None:
        doc = make_vat_doc()
        self._add_line_allowance(doc, indicator=False)
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-CO-23" for v in e.value.errors)

    def test_br_co_24_line_charge_needs_reason_or_code(self) -> None:
        doc = make_vat_doc()
        self._add_line_allowance(doc, indicator=True)
        with pt.raises(ValidationErrors) as e:
            doc.validate()
        assert any(v.code == "BR-CO-24" for v in e.value.errors)

    def test_br_co_23_passes_with_reason(self) -> None:
        doc = make_vat_doc()
        self._add_line_allowance(doc, indicator=False, reason="quantity discount")
        doc.validate()

    def test_br_co_24_passes_with_code(self) -> None:
        doc = make_vat_doc()
        self._add_line_allowance(doc, indicator=True, reason_code="TAC")
        doc.validate()
