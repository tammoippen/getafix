"""Rendering for the document header (:mod:`getafix.schema.document`).

Builds the top-level Invoice panel — the at-a-glance overview of the
document. It owns the header fields proper (BT-1 / BT-2 / BT-3 / BT-24,
plus the EXTENDED name / language and the BG-1 notes) and composes in
the rows contributed by the neighbouring sections: the invoicing period
and preceding invoices from the settlement, and the order / contract /
project references from the agreement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table

from getafix.report._types import described_panel
from getafix.report.agreement import reference_rows
from getafix.report.settlement import (
    accounting_currency_row,
    accounting_reference_rows,
    billing_period_row,
    preceding_invoice_rows,
)
from getafix.report.types import dim_paren, format_type_code

if TYPE_CHECKING:
    from getafix.schema import Document
    from getafix.schema.document import Header


def header_panel(doc: Document) -> Panel:
    """Invoice overview (BG-2 / BT-1-00 plus the framing references)."""
    header = doc.header
    profile = doc.context.guideline.id
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold cyan")
    grid.add_column()
    grid.add_row("Invoice number (BT-1):", str(header.id))
    grid.add_row("Issue date (BT-2):", header.issue_date.isoformat())
    grid.add_row("Type code (BT-3):", format_type_code(header.type_code))
    grid.add_row("Profile (BT-24):", profile.name)
    business = doc.context.business
    if business is not None and business.id:
        grid.add_row("Process (BT-23):", business.id)
    if header.name:
        grid.add_row("Document name:", header.name)
    if header.language_id:
        grid.add_row("Language:", header.language_id)
    currency = accounting_currency_row(doc.trade.settlement)
    if currency is not None:
        grid.add_row(*currency)
    period = billing_period_row(doc.trade.settlement)
    if period is not None:
        grid.add_row(*period)
    for label, value in reference_rows(doc.trade.agreement):
        grid.add_row(label, value)
    for label, value in accounting_reference_rows(doc.trade.settlement):
        grid.add_row(label, value)
    for label, value in preceding_invoice_rows(doc.trade.settlement):
        grid.add_row(label, value)
    notes = notes_text(header)
    if notes is not None:
        grid.add_row("Notes:", notes)
    return described_panel(
        grid,
        title="[bold]Invoice[/bold]",
        description="Document identification, dates and the trading references.",
        border_style="cyan",
    )


def notes_text(header: Header) -> str | None:
    """Join the invoice notes (BG-1) into one block, or ``None`` if none.

    Each note is prefixed with its dim subject code (BT-21) when set.
    """
    if not header.notes:
        return None
    return "\n".join(
        f"{dim_paren(n.subject_code)} {n.content or ''}"
        if n.subject_code
        else (n.content or "")
        for n in header.notes
    )
