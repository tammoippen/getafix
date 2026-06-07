"""Formatting helpers for the coded enums in :mod:`getafix.schema.types`.

Small, pure functions that turn a code (``TypeCode``, ``CategoryCode`` +
rate) into the short human string the report shows. Kept separate from
the panel/table builders so the same formatting is reused everywhere a
code appears — the line VAT cell, the allowance/charge VAT cell, the
logistics-charge VAT cell all funnel through :func:`format_vat`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal

    from getafix.schema.types import CategoryCode, TypeCode


def format_type_code(type_code: TypeCode) -> str:
    """Invoice type code (BT-3) as ``<value> - <name>``.

    Drops the ``T_`` prefix the enum members carry so e.g.
    ``T_CommercialInvoice`` shows as ``380 - CommercialInvoice``.
    """
    return f"{type_code.value} - {type_code.name.removeprefix('T_')}"


def format_vat(category: CategoryCode, rate: Decimal | None) -> str:
    """VAT cell: ``<rate>% <category>``, or just the category when rateless.

    Rate-less VAT categories (``O`` out of scope, ``AE`` reverse charge,
    ``K`` intra-community) legitimately omit BT-119, so fall back to the
    bare category code in that case.
    """
    return f"{rate}% {category.value}" if rate is not None else category.value
