"""Unit tests for ``carthorse.schema.element.coerce_enum``.

The helper inspects a dataclass field's annotation via
:func:`typing.get_type_hints`, unwraps ``Optional[X]``, and if ``X`` is
a :class:`enum.StrEnum` subclass returns ``X(value)``; otherwise it
returns the value unchanged. Custom ``from_xml`` overrides use it to
coerce XML attribute strings into their field's annotated type without
hard-coding the StrEnum class at every call site.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import pytest as pt

from carthorse.schema.element import Element, coerce_enum
from carthorse.schema.types import MIME, Currency


@dataclass(kw_only=True, slots=True)
class _Sample(Element):
    """Stand-in dataclass exercising the helper's annotation lookup."""

    tag: ClassVar[str] = "Sample"

    currency: Currency
    mime: MIME | None
    label: str
    optional_label: str | None


class TestCoerceEnum:
    def test_strenum_field_coerces(self) -> None:
        out = coerce_enum("EUR", _Sample, "currency")
        assert out == Currency.EUR
        assert isinstance(out, Currency)

    def test_optional_strenum_field_coerces_value(self) -> None:
        out = coerce_enum("application/pdf", _Sample, "mime")
        assert out == MIME.pdf
        assert isinstance(out, MIME)

    def test_optional_strenum_field_passes_none(self) -> None:
        assert coerce_enum(None, _Sample, "mime") is None

    def test_str_field_returned_unchanged(self) -> None:
        assert coerce_enum("plain", _Sample, "label") == "plain"

    def test_optional_str_field_handles_none(self) -> None:
        assert coerce_enum(None, _Sample, "optional_label") is None
        assert coerce_enum("plain", _Sample, "optional_label") == "plain"

    def test_unknown_field_falls_back_to_str(self) -> None:
        assert coerce_enum("x", _Sample, "no_such_field") == "x"

    def test_invalid_enum_value_raises(self) -> None:
        with pt.raises(ValueError):
            coerce_enum("not-a-currency", _Sample, "currency")
