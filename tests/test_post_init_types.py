"""Regression tests for ``Element.__post_init__`` shape checks.

The base ``__post_init__`` runs an ``isinstance``-style walk of every
declared field at construction time and raises :class:`TypeError` on
the first mismatch. It is the boundary check that complements the
``_validators`` business-rule layer (which assumes the shape is
already correct).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest as pt

from getafix.schema.accounting import (
    HeaderTradeAllowanceCharge,
    MonetarySummation,
    TaxTotal,
)
from getafix.schema.document import GuidelineDocument, Header, IncludedNote
from getafix.schema.types import Currency, TypeCode


class TestScalarFields:
    def test_str_field_rejects_int(self) -> None:
        with pt.raises(TypeError, match=r"Header\.id: expected str"):
            Header(
                id=42,  # type: ignore[arg-type]
                type_code=TypeCode.T_CommercialInvoice,
                issue_date=date(2025, 1, 1),
            )

    def test_decimal_field_rejects_float(self) -> None:
        with pt.raises(TypeError, match=r"TaxTotal\.amount: expected Decimal"):
            TaxTotal(amount=19.00, currency_id=Currency.EUR)  # type: ignore[arg-type]

    def test_decimal_field_rejects_str(self) -> None:
        with pt.raises(TypeError, match=r"TaxTotal\.amount: expected Decimal"):
            TaxTotal(amount="19.00", currency_id=Currency.EUR)  # type: ignore[arg-type]

    def test_date_field_rejects_str(self) -> None:
        with pt.raises(TypeError, match=r"Header\.issue_date: expected date"):
            Header(
                id="INV-1",
                type_code=TypeCode.T_CommercialInvoice,
                issue_date="2025-01-01",  # type: ignore[arg-type]
            )

    def test_enum_field_rejects_plain_str(self) -> None:
        with pt.raises(TypeError, match=r"GuidelineDocument\.id: expected Profile"):
            GuidelineDocument(id="urn:factur-x.eu:1p0:minimum")  # type: ignore[arg-type]

    def test_optional_field_accepts_none(self) -> None:
        # ``name`` (BT-X-2) is Optional[str]; None must construct cleanly.
        Header(
            id="INV-1",
            name=None,
            type_code=TypeCode.T_CommercialInvoice,
            issue_date=date(2025, 1, 1),
        )

    def test_optional_field_rejects_wrong_type(self) -> None:
        with pt.raises(TypeError, match=r"Header\.name: expected str"):
            Header(
                id="INV-1",
                name=123,  # type: ignore[arg-type]
                type_code=TypeCode.T_CommercialInvoice,
                issue_date=date(2025, 1, 1),
            )


class TestBoolStrictness:
    """``bool`` is a subclass of ``int`` — verify the strict guard."""

    def test_bool_field_rejects_int(self) -> None:
        with pt.raises(TypeError, match="expected bool"):
            HeaderTradeAllowanceCharge(
                indicator=1,  # type: ignore[arg-type]
                actual_amount=Decimal("5.00"),
            )

    def test_bool_field_accepts_true(self) -> None:
        HeaderTradeAllowanceCharge(indicator=True, actual_amount=Decimal("5.00"))

    def test_bool_field_accepts_false(self) -> None:
        HeaderTradeAllowanceCharge(indicator=False, actual_amount=Decimal("5.00"))


class TestLiteralFields:
    """``Literal[...]`` annotations must reject any non-member value
    at construction time — BT-128-0 is fixed to ``"130"``."""

    def test_literal_field_accepts_declared_value(self) -> None:
        from getafix.schema.line import LineAdditionalReferencedDocument

        LineAdditionalReferencedDocument(issuer_assigned_id="X-1", type_code="130")

    def test_literal_field_uses_default(self) -> None:
        from getafix.schema.line import LineAdditionalReferencedDocument

        ref = LineAdditionalReferencedDocument(issuer_assigned_id="X-1")
        assert ref.type_code == "130"

    def test_literal_field_rejects_other_value(self) -> None:
        from getafix.schema.line import LineAdditionalReferencedDocument

        with pt.raises(TypeError, match=r"type_code: expected one of \{'130'\}"):
            LineAdditionalReferencedDocument(
                issuer_assigned_id="X-1",
                type_code="916",  # type: ignore[arg-type]
            )


class TestListFields:
    def test_list_field_rejects_scalar(self) -> None:
        with pt.raises(TypeError, match=r"Header\.notes: expected list"):
            Header(
                id="INV-1",
                type_code=TypeCode.T_CommercialInvoice,
                issue_date=date(2025, 1, 1),
                notes=IncludedNote(content="hi"),  # type: ignore[arg-type]
            )

    def test_list_field_rejects_wrong_item_type(self) -> None:
        with pt.raises(TypeError, match=r"Header\.notes\[0\]: expected IncludedNote"):
            Header(
                id="INV-1",
                type_code=TypeCode.T_CommercialInvoice,
                issue_date=date(2025, 1, 1),
                notes=["just a string"],  # type: ignore[list-item]
            )

    def test_list_field_accepts_well_typed_items(self) -> None:
        Header(
            id="INV-1",
            type_code=TypeCode.T_CommercialInvoice,
            issue_date=date(2025, 1, 1),
            notes=[IncludedNote(content="hi")],
        )

    def test_list_field_accepts_empty_list(self) -> None:
        Header(
            id="INV-1",
            type_code=TypeCode.T_CommercialInvoice,
            issue_date=date(2025, 1, 1),
            notes=[],
        )


class TestNestedElement:
    def test_summation_rejects_wrong_nested_type(self) -> None:
        with pt.raises(
            TypeError, match=r"MonetarySummation\.tax_total\[0\]: expected TaxTotal"
        ):
            MonetarySummation(
                tax_basis_total=Decimal("100"),
                tax_total=["not-a-taxtotal"],  # type: ignore[list-item]
                grand_total=Decimal("119"),
                due_amount=Decimal("119"),
            )


class TestRequiredFields:
    """Non-Optional fields must not hold ``None`` — even when the parser
    or a builder forgets to populate them.

    Dataclasses only raise at ``__init__`` when a required kwarg is
    missing entirely; passing ``None`` explicitly slips through unless
    we catch it here.
    """

    def test_required_str_rejects_none(self) -> None:
        with pt.raises(TypeError, match=r"Header\.id: required, got None"):
            Header(
                id=None,  # type: ignore[arg-type]
                type_code=TypeCode.T_CommercialInvoice,
                issue_date=date(2025, 1, 1),
            )

    def test_required_date_rejects_none(self) -> None:
        with pt.raises(TypeError, match=r"Header\.issue_date: required, got None"):
            Header(
                id="INV-1",
                type_code=TypeCode.T_CommercialInvoice,
                issue_date=None,  # type: ignore[arg-type]
            )

    def test_required_decimal_rejects_none(self) -> None:
        with pt.raises(TypeError, match=r"TaxTotal\.amount: required, got None"):
            TaxTotal(amount=None, currency_id=Currency.EUR)  # type: ignore[arg-type]

    def test_required_enum_rejects_none(self) -> None:
        with pt.raises(TypeError, match=r"GuidelineDocument\.id: required, got None"):
            GuidelineDocument(id=None)  # type: ignore[arg-type]
