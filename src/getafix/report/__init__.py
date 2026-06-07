"""Rich console report of a parsed Cross-Industry-Invoice :class:`Document`.

Importing this package requires the optional ``rich`` dependency::

    pip install 'getafix[cli]'

The package mirrors :mod:`getafix.schema`: every schema module has a
report counterpart that knows how to render the elements defined there
(``document`` → Invoice panel, ``party`` → Seller / Buyer panels,
``trade`` → line-items table, ``accounting`` → VAT breakdown / totals,
``settlement`` → payment / prepayment sections, …). Shared primitives
live in :mod:`getafix.report._types`; code-formatting helpers in
:mod:`getafix.report.types`. (``schema/_numeric.py`` has no counterpart
— it is a rounding helper, not a renderable element.)

Two public entry points:

* :func:`render_invoice` — pretty-print the document (header, parties,
  lines, VAT breakdown, totals, payment block).
* :func:`render_validation_errors` — pretty-print a list of
  :class:`getafix.schema.element.ValidationError` from
  ``Document.validate_internal``.

See ``docs/plans/report-package.md`` for the roadmap towards rendering
every COMFORT-profile element.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.table import Table

from getafix.report._types import SectionRenderer as SectionRenderer
from getafix.report.accounting import allowance_charge_panel, tax_table, totals_panel
from getafix.report.delivery import delivery_panel
from getafix.report.document import header_panel
from getafix.report.element import render_validation_errors as render_validation_errors
from getafix.report.party import party_panel
from getafix.report.settlement import (
    advance_payments_panel,
    logistics_charges_panel,
    payment_panel,
)
from getafix.report.trade import lines_table

if TYPE_CHECKING:
    from rich.console import Console

    from getafix.schema import Document


def render_invoice(doc: Document, console: Console | None = None) -> None:
    """Print a structured, colourised report of ``doc`` to ``console``.

    Sections are emitted top to bottom in reading order; each optional
    section short-circuits to ``None`` when it has nothing to show, so a
    bare MINIMUM invoice prints only the header, parties and totals.
    """
    from rich.console import Console

    console = console or Console()
    settlement = doc.trade.settlement
    currency = settlement.currency_code

    console.print(header_panel(doc))
    # Force a true 50/50 split: a 2-column grid with ``ratio=1``
    # columns gives each party panel exactly half the terminal width.
    # ``Columns(equal=True)`` only equalises widths when content fits,
    # which truncates a long Seller block against the Buyer side.
    parties = Table.grid(expand=True, padding=(0, 1))
    parties.add_column(ratio=1)
    parties.add_column(ratio=1)
    parties.add_row(
        party_panel("Seller", doc.trade.agreement.seller),
        party_panel("Buyer", doc.trade.agreement.buyer),
    )
    console.print(parties)
    delivery = delivery_panel(doc.trade.delivery)
    if delivery is not None:
        console.print(delivery)
    if doc.trade.items:
        console.print(lines_table(doc.trade, currency))
    if settlement.trade_taxes:
        console.print(tax_table(settlement))
    allowance_charges = allowance_charge_panel(settlement)
    if allowance_charges is not None:
        console.print(allowance_charges)
    logistics_charges = logistics_charges_panel(settlement)
    if logistics_charges is not None:
        console.print(logistics_charges)
    console.print(totals_panel(settlement))
    advance_payments = advance_payments_panel(settlement)
    if advance_payments is not None:
        console.print(advance_payments)
    payment = payment_panel(settlement)
    if payment is not None:
        console.print(payment)
