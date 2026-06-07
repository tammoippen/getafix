"""Rendering for the header trade delivery (:mod:`getafix.schema.delivery`).

One panel covering the where-and-when of the goods or services: the
actual delivery date (BT-72), the ship-to party name (BG-13) and the
despatch / receiving advice references (BT-16 / BT-15).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table

from getafix.report._types import described_panel
from getafix.report.references import format_reference

if TYPE_CHECKING:
    from getafix.schema.delivery import TradeDelivery


def delivery_panel(delivery: TradeDelivery) -> Panel | None:
    """Header trade delivery (BG-13).

    Returns ``None`` when none of the relevant fields are set so BASIC
    invoices don't grow an empty panel.
    """
    event = delivery.event
    despatch = delivery.despatch_advice
    receiving = delivery.receiving_advice
    ship_to = delivery.ship_to
    occurrence = event.occurrence if event is not None else None
    if not (occurrence or despatch or receiving or ship_to):
        return None
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold")
    grid.add_column()
    if occurrence is not None:
        grid.add_row("Delivery date (BT-72):", occurrence.isoformat())
    if ship_to is not None and ship_to.name:
        grid.add_row("Ship to (BG-13):", ship_to.name)
    if despatch is not None:
        grid.add_row("Despatch advice (BT-16):", format_reference(despatch))
    if receiving is not None:
        grid.add_row("Receiving advice (BT-15):", format_reference(receiving))
    return described_panel(
        grid,
        title="[bold]Delivery[/bold]",
        description="Where and when the goods or services were delivered.",
        border_style="cyan",
    )
