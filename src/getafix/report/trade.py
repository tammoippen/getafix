"""Rendering for the line-items table (:mod:`getafix.schema.trade`).

``schema/trade.py`` owns the collection of ``TradeLineItem`` (BG-25);
its report counterpart owns :func:`lines_table`, which arranges those
items into the line-items table. The per-line cell content comes from
:mod:`getafix.report.line`; this module handles the table framing and
the EXTENDED sub-invoice-line hierarchy (children ordered and indented
under their parent).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.table import Table

from getafix.report._types import describe_table
from getafix.report.line import item_cell, line_vat_cell, net_price_cell

if TYPE_CHECKING:
    from getafix.schema.trade import Trade, TradeLineItem


def _ordered_lines(items: list[TradeLineItem]) -> list[tuple[int, TradeLineItem]]:
    """Return ``(depth, item)`` in sub-invoice-line tree order.

    EXTENDED sub-invoice-lines link to a parent via BT-X-304; children
    render directly under their parent, one level deeper, regardless of
    document order (the Hardware sample lists children *before* their
    GROUP parent). A missing / dangling parent makes a root; a cycle
    survivor falls back to depth 0 so every line is shown exactly once.
    """
    by_id = {item.associated_document.line_id: item for item in items}
    children: dict[str, list[str]] = {}
    roots: list[str] = []
    for item in items:
        ad = item.associated_document
        parent = ad.parent_line_id
        if parent is not None and parent in by_id and parent != ad.line_id:
            children.setdefault(parent, []).append(ad.line_id)
        else:
            roots.append(ad.line_id)

    ordered: list[tuple[int, TradeLineItem]] = []
    seen: set[str] = set()

    def _walk(line_id: str, depth: int) -> None:
        if line_id in seen:
            return  # cycle guard
        seen.add(line_id)
        ordered.append((depth, by_id[line_id]))
        for child in children.get(line_id, []):
            _walk(child, depth + 1)

    for root in roots:
        _walk(root, 0)
    # Any line not reached above (part of a cycle) still gets shown once.
    for item in items:
        if item.associated_document.line_id not in seen:
            _walk(item.associated_document.line_id, 0)
    return ordered


def lines_table(trade: Trade, currency: str) -> Table:
    """Line items (BG-25): one row per invoiced position."""
    table = Table(
        title="Line items",
        title_style="bold",
        header_style="bold",
        border_style="blue",
        show_lines=False,
        expand=True,
    )
    # The line-id column is left-justified so the sub-line indentation is
    # visible (a right-justified column would swallow the leading spaces).
    table.add_column("#", style="dim", no_wrap=True)
    table.add_column("Item")
    table.add_column("Qty", justify="right")
    table.add_column("Unit", no_wrap=True)
    table.add_column(f"Net price [{currency}]", justify="right")
    table.add_column(f"Line total [{currency}]", justify="right")
    table.add_column("VAT", justify="right", no_wrap=True)

    for depth, item in _ordered_lines(trade.items):
        ad = item.associated_document
        qty = item.delivery.billed_quantity
        line_total = item.settlement.monetary_summation.line_total
        # Indent children under their parent; tag the EXTENDED
        # sub-invoice-line subtype (BT-X-8) next to the line id.
        indent = "  " * depth
        subtype_tag = (
            f" [dim]({ad.status_reason_code.value})[/dim]"
            if ad.status_reason_code is not None
            else ""
        )
        # Qty / unit / line total can be ``None`` on EXTENDED GROUP /
        # INFORMATION lines; render an em-dash placeholder there.
        table.add_row(
            f"{indent}{ad.line_id}{subtype_tag}",
            item_cell(item),
            f"{qty.value}" if qty is not None else "—",
            qty.unit_code if qty is not None else "—",
            net_price_cell(item.agreement),
            f"{line_total}" if line_total is not None else "—",
            line_vat_cell(item.settlement.applicable_trade_tax),
        )
    return describe_table(
        table,
        "One row per invoiced position (BG-25); sub-lines indent under their parent.",
    )
