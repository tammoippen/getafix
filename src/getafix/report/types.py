"""Value formatters for the report.

Small, pure ``value -> str`` helpers shared across the section builders so
the same formatting (and the same Rich markup) is written once:

* code formatters — :func:`format_type_code`, :func:`format_vat`;
* value formatters — :func:`format_amount`, :func:`format_period`,
  :func:`scheme_suffix`;
* markup helpers — :func:`dim`, :func:`dim_paren` centralise the muted
  ``[dim]…[/dim]`` styling used for secondary detail.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

    from getafix.schema.types import CategoryCode, TypeCode


def dim(text: str) -> str:
    """Wrap ``text`` in Rich's muted ``[dim]`` style."""
    return f"[dim]{text}[/dim]"


def dim_paren(text: str) -> str:
    """Dim, parenthesised hint — ``[dim](text)[/dim]``.

    The house style for a secondary qualifier shown next to a value: a
    reason code beside its text, a scheme beside an id, a date beside a
    reference.
    """
    return dim(f"({text})")


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


def format_amount(value: Decimal, currency: str) -> str:
    """Monetary value with its currency code — ``<value> <currency>``."""
    return f"{value} {currency}"


def format_bytes(size: int) -> str:
    """Byte count with a binary (IEC) unit suffix.

    Bytes show as a bare integer (``512 B``); larger sizes step through
    ``KiB`` / ``MiB`` / ``GiB`` / ``TiB`` / ``PiB`` (1024-based) with one
    decimal (``35.6 KiB``).
    """
    if size < 1024:
        return f"{size} B"
    value = float(size)
    for unit in ("KiB", "MiB", "GiB", "TiB"):
        value /= 1024
        if value < 1024:
            return f"{value:.1f} {unit}"
    return f"{value / 1024:.1f} PiB"


def format_period(start: date | None, end: date | None) -> str:
    """Date range ``<start> → <end>`` with ``…`` for an open endpoint.

    Used for both the header invoicing period (BG-14) and the line
    invoicing period (BG-26); the caller checks at least one endpoint is
    set before rendering.
    """
    start_text = start.isoformat() if start else "…"
    end_text = end.isoformat() if end else "…"
    return f"{start_text} → {end_text}"


def scheme_suffix(scheme_id: str | None) -> str:
    """Dim `` (scheme XXX)`` suffix for an identifier, or empty when unset.

    Appended after an identifier value (global id, legal registration id,
    electronic address) to show which registration scheme issued it
    without crowding the primary value.
    """
    return f" {dim_paren(f'scheme {scheme_id}')}" if scheme_id else ""
