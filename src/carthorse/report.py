"""Rich console report of a parsed Cross-Industry-Invoice :class:`Document`.

Importing this module requires the optional ``rich`` dependency::

    pip install 'carthorse[cli]'

Two entry points:

* :func:`render_invoice` — pretty-print the document (header, parties,
  lines, VAT breakdown, totals, payment block).
* :func:`render_validation_errors` — pretty-print a list of
  :class:`carthorse.schema.element.ValidationError` from
  ``Document.validate_internal``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

from rich.columns import Columns
from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from carthorse.schema import Document
    from carthorse.schema.element import ValidationError
    from carthorse.schema.party import (
        BuyerTradeParty,
        PostalTradeAddress,
        SellerTradeParty,
    )


def render_invoice(doc: Document, console: Console | None = None) -> None:
    """Print a structured, colourised report of ``doc`` to ``console``."""
    console = console or Console()
    console.print(_header_panel(doc))
    console.print(
        Columns(
            [
                _party_panel("Seller", doc.trade.agreement.seller),
                _party_panel("Buyer", doc.trade.agreement.buyer),
            ],
            expand=True,
            equal=True,
        )
    )
    if doc.trade.items:
        console.print(_lines_table(doc))
    if doc.trade.settlement.trade_taxes:
        console.print(_tax_table(doc))
    console.print(_totals_panel(doc))
    payment = _payment_panel(doc)
    if payment is not None:
        console.print(payment)


def render_validation_errors(
    errors: Sequence[ValidationError], console: Console | None = None
) -> None:
    """Print ``errors`` as a red-bordered table; print a success note when empty."""
    console = console or Console()
    if not errors:
        console.print("[green]✓ No validation errors[/green]")
        return
    table = Table(
        title=f"Validation errors ({len(errors)})",
        title_style="bold red",
        border_style="red",
        show_lines=False,
    )
    table.add_column("Rule", style="yellow", no_wrap=True)
    table.add_column("Message")
    for err in errors:
        table.add_row(err.code, err.message)
    console.print(table)


def _header_panel(doc: Document) -> Panel:
    header = doc.header
    profile = doc.context.guideline.id
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold cyan")
    grid.add_column()
    grid.add_row("Invoice number (BT-1):", str(header.id))
    grid.add_row("Issue date (BT-2):", header.issue_date.isoformat())
    grid.add_row(
        "Type code (BT-3):",
        f"{header.type_code.value} - {header.type_code.name.removeprefix('T_')}",
    )
    grid.add_row("Profile (BT-24):", profile.name)
    if header.name:
        grid.add_row("Document name:", header.name)
    if header.language_id:
        grid.add_row("Language:", header.language_id)
    if header.notes:
        notes = "\n".join(
            f"[dim]({n.subject_code})[/dim] {n.content or ''}"
            if n.subject_code
            else (n.content or "")
            for n in header.notes
        )
        grid.add_row("Notes:", notes)
    return Panel(grid, title="[bold]Invoice[/bold]", border_style="cyan")


def _party_panel(role: str, party: SellerTradeParty | BuyerTradeParty | None) -> Panel:
    if party is None:
        return Panel("(not set)", title=role, border_style="green")
    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="bold", no_wrap=True)
    grid.add_column()
    grid.add_row("Name:", party.name or "")
    legal = getattr(party, "legal_organization", None)
    if legal is not None and legal.trade_name:
        grid.add_row("Trading as:", legal.trade_name)
    address = getattr(party, "address", None)
    addr_text = _format_address(address)
    if addr_text:
        grid.add_row("Address:", addr_text)
    contact = getattr(party, "contact", None)
    if contact is not None:
        if contact.person_name:
            grid.add_row("Contact:", contact.person_name)
        if contact.email and contact.email.address:
            grid.add_row("E-mail:", contact.email.address)
        if contact.telephone and contact.telephone.number:
            grid.add_row("Phone:", contact.telephone.number)
    electronic = getattr(party, "electronic_address", None)
    if electronic is not None and electronic.uri_id.id:
        scheme = electronic.uri_id.scheme_id
        grid.add_row(
            "Electronic addr.:",
            f"{electronic.uri_id.id}"
            + (f" [dim](scheme {scheme})[/dim]" if scheme else ""),
        )
    for label, value in _iter_tax_ids(party):
        grid.add_row(f"{label}:", value)
    return Panel(grid, title=f"[bold]{role}[/bold]", border_style="green")


def _iter_tax_ids(party: object) -> Iterable[tuple[str, str]]:
    registrations = getattr(party, "tax_registrations", None)
    if registrations is None:
        return
    if not isinstance(registrations, list):
        registrations = [registrations]
    for reg in registrations:
        scheme = reg.id.scheme_id or "Tax ID"
        label = {"VA": "VAT ID", "FC": "Tax number"}.get(scheme, scheme)
        yield label, reg.id.id


def _format_address(addr: PostalTradeAddress | None) -> str:
    if addr is None:
        return ""
    lines: list[str] = [
        line for line in (addr.line_one, addr.line_two, addr.line_three) if line
    ]
    city_bits = [bit for bit in (addr.postcode, addr.city_name) if bit]
    if city_bits:
        lines.append(" ".join(city_bits))
    subdivision = getattr(addr, "country_subdivision", None)
    if subdivision:
        lines.append(subdivision)
    if addr.country_id:
        lines.append(addr.country_id)
    return "\n".join(lines)


def _lines_table(doc: Document) -> Table:
    currency = doc.trade.settlement.currency_code
    table = Table(
        title="Line items",
        title_style="bold",
        header_style="bold",
        border_style="blue",
        show_lines=False,
    )
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Item")
    table.add_column("Qty", justify="right")
    table.add_column("Unit", no_wrap=True)
    table.add_column(f"Net price [{currency}]", justify="right")
    table.add_column(f"Line total [{currency}]", justify="right")
    table.add_column("VAT", justify="right", no_wrap=True)
    for item in doc.trade.items:
        tax = item.settlement.applicable_trade_tax
        rate = tax.rate_applicable_percent
        vat_str = (
            f"{rate}% {tax.category_code.value}"
            if rate is not None
            else tax.category_code.value
        )
        table.add_row(
            item.associated_document.line_id,
            item.product.name or "",
            f"{item.delivery.billed_quantity.value}",
            item.delivery.billed_quantity.unit_code,
            f"{item.agreement.net_price.charge_amount}",
            f"{item.settlement.monetary_summation.line_total}",
            vat_str,
        )
    return table


def _tax_table(doc: Document) -> Table:
    currency = doc.trade.settlement.currency_code
    table = Table(
        title="VAT breakdown (BG-23)",
        title_style="bold",
        header_style="bold",
        border_style="blue",
    )
    table.add_column("Cat", no_wrap=True)
    table.add_column("Rate", justify="right")
    table.add_column(f"Basis [{currency}]", justify="right")
    table.add_column(f"Tax [{currency}]", justify="right")
    table.add_column("Exemption reason")
    for tax in doc.trade.settlement.trade_taxes or []:
        rate = tax.rate_applicable_percent
        reason = tax.exemption_reason or ""
        if tax.exemption_reason_code:
            reason = f"[dim]({tax.exemption_reason_code})[/dim] {reason}".strip()
        table.add_row(
            tax.category_code.value,
            f"{rate}%" if rate is not None else "-",
            f"{tax.basis_amount}" if tax.basis_amount is not None else "-",
            f"{tax.calculated_amount}" if tax.calculated_amount is not None else "-",
            reason,
        )
    return table


def _totals_panel(doc: Document) -> Panel:
    summ = doc.trade.settlement.monetary_summation
    currency = doc.trade.settlement.currency_code
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold")
    grid.add_column(justify="right")
    rows: list[tuple[str, object | None]] = [
        ("Line total (BT-106)", summ.line_total),
        ("Allowances (BT-107)", summ.allowance_total),
        ("Charges (BT-108)", summ.charge_total),
        ("Tax basis (BT-109)", summ.tax_basis_total),
    ]
    for label, value in rows:
        if value is None:
            continue
        grid.add_row(label, f"{value} {currency}")
    for tax in summ.tax_total or []:
        grid.add_row(
            f"Tax total ({tax.currency_id})", f"{tax.amount} {tax.currency_id}"
        )
    tail: list[tuple[str, object | None]] = [
        ("Rounding (BT-114)", summ.rounding_amount),
        ("Grand total (BT-112)", summ.grand_total),
        ("Prepaid (BT-113)", summ.prepaid_total),
    ]
    for label, value in tail:
        if value is None:
            continue
        grid.add_row(label, f"{value} {currency}")
    grid.add_row(
        "[bold yellow]Amount due (BT-115)[/bold yellow]",
        f"[bold yellow]{summ.due_amount} {currency}[/bold yellow]",
    )
    return Panel(grid, title="[bold]Totals[/bold]", border_style="yellow")


def _payment_panel(doc: Document) -> RenderableType | None:
    settlement = doc.trade.settlement
    if not (
        settlement.payment_means
        or settlement.terms
        or settlement.payment_reference
        or settlement.creditor_reference
    ):
        return None
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold", no_wrap=True)
    grid.add_column()
    if settlement.terms is not None:
        if settlement.terms.description:
            grid.add_row("Terms:", settlement.terms.description)
        if settlement.terms.due:
            grid.add_row("Due date:", settlement.terms.due.isoformat())
        if settlement.terms.debit_mandate_id:
            grid.add_row("SEPA mandate:", settlement.terms.debit_mandate_id)
    for pm in settlement.payment_means or []:
        grid.add_row("Means (BT-81):", pm.type_code)
        if pm.payee is not None:
            if pm.payee.iban_id:
                grid.add_row("IBAN:", pm.payee.iban_id)
            if pm.payee.proprietary_id:
                grid.add_row("Account:", pm.payee.proprietary_id)
        if pm.payer is not None and pm.payer.iban_id:
            grid.add_row("Debited IBAN:", pm.payer.iban_id)
    if settlement.payment_reference:
        grid.add_row("Reference (BT-83):", settlement.payment_reference)
    if settlement.creditor_reference:
        grid.add_row("Creditor id (BT-90):", settlement.creditor_reference)
    return Panel(grid, title="[bold]Payment[/bold]", border_style="magenta")
