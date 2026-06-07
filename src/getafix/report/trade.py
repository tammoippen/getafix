"""Rendering for the line-items table (:mod:`getafix.schema.trade`).

``schema/trade.py`` owns the collection of ``TradeLineItem`` (BG-25);
its report counterpart owns :func:`lines_table`, which arranges those
items into the line-items table. The per-line cell content comes from
:mod:`getafix.report.line`; this module handles the table framing and
the EXTENDED sub-invoice-line indentation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.table import Table

from getafix.report._types import describe_table
from getafix.report.line import item_cell, line_vat_cell

if TYPE_CHECKING:
    from getafix.schema.trade import Trade


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
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Item")
    table.add_column("Qty", justify="right")
    table.add_column("Unit", no_wrap=True)
    table.add_column(f"Net price [{currency}]", justify="right")
    table.add_column(f"Line total [{currency}]", justify="right")
    table.add_column("VAT", justify="right", no_wrap=True)

    # Build a parent-line -> depth map so EXTENDED sub-invoice-line
    # trees render indented (Hardware-style: GROUP "01" with DETAIL
    # children "0101" / "0102" — children render two spaces deeper).
    # Compute depth via the parent chain so the order in which lines
    # appear in the document doesn't matter (the Hardware sample
    # actually lists children BEFORE their parent).
    parent_of: dict[str, str] = {
        item.associated_document.line_id: item.associated_document.parent_line_id
        for item in trade.items
        if item.associated_document.parent_line_id is not None
    }

    _EMPTY: frozenset[str] = frozenset()

    def _depth(line_id: str, _seen: frozenset[str] = _EMPTY) -> int:
        parent = parent_of.get(line_id)
        if parent is None or parent in _seen:
            return 0  # root, dangling ref, or cycle guard
        return _depth(parent, _seen | {line_id}) + 1

    depth_by_id = {
        item.associated_document.line_id: _depth(item.associated_document.line_id)
        for item in trade.items
    }

    for item in trade.items:
        ad = item.associated_document
        qty = item.delivery.billed_quantity
        net = item.agreement.net_price
        line_total = item.settlement.monetary_summation.line_total
        # EXTENDED sub-invoice-line subtype (BT-X-8) — show as a tag
        # next to the line id; indent children of GROUP lines.
        indent = "  " * depth_by_id[ad.line_id]
        subtype_tag = (
            f" [dim]({ad.status_reason_code.value})[/dim]"
            if ad.status_reason_code is not None
            else ""
        )
        # All four can be ``None`` on EXTENDED GROUP / INFORMATION lines;
        # render an em-dash placeholder in those cells.
        table.add_row(
            f"{indent}{ad.line_id}{subtype_tag}",
            item_cell(item.product),
            f"{qty.value}" if qty is not None else "—",
            qty.unit_code if qty is not None else "—",
            f"{net.charge_amount}" if net is not None else "—",
            f"{line_total}" if line_total is not None else "—",
            line_vat_cell(item.settlement.applicable_trade_tax),
        )
    return describe_table(table, "One row per invoiced position (BG-25).")
