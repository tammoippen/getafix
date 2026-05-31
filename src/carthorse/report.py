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
    # Force a true 50/50 split — ``Columns(equal=True)`` only equalises
    # widths when content fits, so a long Seller block was previously
    # squishing the Buyer side. A 2-column grid with ``ratio=1`` columns
    # gives each panel exactly half the terminal width.
    parties = Table.grid(expand=True, padding=(0, 1))
    parties.add_column(ratio=1)
    parties.add_column(ratio=1)
    parties.add_row(
        _party_panel("Seller", doc.trade.agreement.seller),
        _party_panel("Buyer", doc.trade.agreement.buyer),
    )
    console.print(parties)
    delivery = _delivery_panel(doc)
    if delivery is not None:
        console.print(delivery)
    if doc.trade.items:
        console.print(_lines_table(doc))
    if doc.trade.settlement.trade_taxes:
        console.print(_tax_table(doc))
    allowance_charges = _allowance_charge_panel(doc)
    if allowance_charges is not None:
        console.print(allowance_charges)
    logistics_charges = _logistics_charges_panel(doc)
    if logistics_charges is not None:
        console.print(logistics_charges)
    console.print(_totals_panel(doc))
    advance_payments = _advance_payments_panel(doc)
    if advance_payments is not None:
        console.print(advance_payments)
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
    period = doc.trade.settlement.billing_period
    if period is not None and (period.start or period.end):
        start = period.start.isoformat() if period.start else "…"
        end = period.end.isoformat() if period.end else "…"
        grid.add_row("Period (BG-14):", f"{start} → {end}")
    agreement = doc.trade.agreement
    if agreement.buyer_reference:
        grid.add_row("Buyer reference (BT-10):", agreement.buyer_reference)
    if agreement.buyer_order is not None:
        grid.add_row(
            "Purchase order (BT-13):", agreement.buyer_order.issuer_assigned_id
        )
    if agreement.seller_order is not None:
        grid.add_row("Sales order (BT-14):", agreement.seller_order.issuer_assigned_id)
    if agreement.contract is not None:
        grid.add_row("Contract (BT-12):", agreement.contract.issuer_assigned_id)
    if agreement.procuring_project is not None:
        proj = agreement.procuring_project
        grid.add_row("Project (BT-11):", f"{proj.id} — {proj.name}")
    for ref in doc.trade.settlement.invoice_referenced_document or []:
        label = "Preceding invoice (BT-25):"
        value = ref.issuer_assigned_id
        if ref.issue_date_time is not None:
            value += f" [dim]({ref.issue_date_time.isoformat()})[/dim]"
        grid.add_row(label, value)
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


def _item_cell(product: object) -> str:
    """Compose the ``Item`` cell: name plus optional COMFORT enrichments
    (BT-154 description, BT-155 / BT-156 ids, BG-32 characteristics,
    BG-34 origin) as dim follow-up lines."""
    name = getattr(product, "name", None) or ""
    lines: list[str] = [name]
    description = getattr(product, "description", None)
    if description:
        lines.append(f"[dim]{description}[/dim]")
    id_bits: list[str] = []
    seller_id = getattr(product, "seller_assigned_id", None)
    if seller_id:
        id_bits.append(f"Seller#: {seller_id}")
    buyer_id = getattr(product, "buyer_assigned_id", None)
    if buyer_id:
        id_bits.append(f"Buyer#: {buyer_id}")
    if id_bits:
        lines.append(f"[dim]{' · '.join(id_bits)}[/dim]")
    chars = getattr(product, "characteristics", None) or []
    if chars:
        rendered = " · ".join(f"{c.description}: {c.value}" for c in chars[:3])
        if len(chars) > 3:
            rendered += f" · (+{len(chars) - 3})"
        lines.append(f"[dim]{rendered}[/dim]")
    origin = getattr(product, "origin_country", None)
    if origin is not None:
        lines.append(f"[dim]Origin: {origin.id}[/dim]")
    return "\n".join(lines)


def _lines_table(doc: Document) -> Table:
    currency = doc.trade.settlement.currency_code
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
        for item in doc.trade.items
        if item.associated_document.parent_line_id is not None
    }

    def _depth(line_id: str, _seen: frozenset[str] = frozenset()) -> int:
        parent = parent_of.get(line_id)
        if parent is None or parent in _seen:
            return 0  # root, dangling ref, or cycle guard
        return _depth(parent, _seen | {line_id}) + 1

    depth_by_id = {
        item.associated_document.line_id: _depth(item.associated_document.line_id)
        for item in doc.trade.items
    }

    for item in doc.trade.items:
        ad = item.associated_document
        tax = item.settlement.applicable_trade_tax
        if tax is None:
            vat_str = "—"  # EXTENDED GROUP / INFORMATION lines have no line VAT
        else:
            rate = tax.rate_applicable_percent
            vat_str = (
                f"{rate}% {tax.category_code.value}"
                if rate is not None
                else tax.category_code.value
            )
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
            _item_cell(item.product),
            f"{qty.value}" if qty is not None else "—",
            qty.unit_code if qty is not None else "—",
            f"{net.charge_amount}" if net is not None else "—",
            f"{line_total}" if line_total is not None else "—",
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
        expand=True,
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


def _delivery_panel(doc: Document) -> Panel | None:
    """Header trade delivery (BG-13) — actual delivery date plus despatch/
    receiving advice references and the ship-to party name. Returns
    ``None`` if none of the relevant fields are set so BASIC invoices
    don't grow an empty panel."""
    delivery = doc.trade.delivery
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
        value = despatch.issuer_assigned_id
        if despatch.issue_date_time is not None:
            value += f" [dim]({despatch.issue_date_time.isoformat()})[/dim]"
        grid.add_row("Despatch advice (BT-16):", value)
    if receiving is not None:
        value = receiving.issuer_assigned_id
        if receiving.issue_date_time is not None:
            value += f" [dim]({receiving.issue_date_time.isoformat()})[/dim]"
        grid.add_row("Receiving advice (BT-15):", value)
    return Panel(grid, title="[bold]Delivery[/bold]", border_style="cyan")


def _allowance_charge_panel(doc: Document) -> Table | None:
    """Document-level allowances (BG-20) and charges (BG-21).

    Each row shows the indicator label, reason, amount, optional VAT
    category + rate, and an optional ``% * basis`` derivation. Returns
    ``None`` if no header-level allowance/charge is present."""
    items = doc.trade.settlement.allowance_charge or []
    if not items:
        return None
    currency = doc.trade.settlement.currency_code
    table = Table(
        title="Document-level allowances & charges (BG-20 / BG-21)",
        title_style="bold",
        header_style="bold",
        border_style="blue",
        expand=True,
    )
    table.add_column("Kind", no_wrap=True)
    table.add_column("Reason")
    table.add_column(f"Amount [{currency}]", justify="right")
    table.add_column("Calc.", justify="right")
    table.add_column("VAT", justify="right", no_wrap=True)
    for ac in items:
        kind = "[red]Charge[/red]" if ac.indicator else "[green]Allowance[/green]"
        reason_bits = [ac.reason or ""]
        if ac.reason_code:
            reason_bits.append(f"[dim]({ac.reason_code})[/dim]")
        if ac.calculation_percent is not None and ac.basis_amount is not None:
            calc = f"{ac.calculation_percent}% of {ac.basis_amount}"
        elif ac.calculation_percent is not None:
            calc = f"{ac.calculation_percent}%"
        elif ac.basis_amount is not None:
            calc = f"basis {ac.basis_amount}"
        else:
            calc = "-"
        ctt = ac.category_trade_tax
        if ctt is not None:
            rate = ctt.rate_applicable_percent
            vat = (
                f"{rate}% {ctt.category_code.value}"
                if rate is not None
                else ctt.category_code.value
            )
        else:
            vat = "-"
        table.add_row(
            kind,
            " ".join(b for b in reason_bits if b),
            f"{ac.actual_amount}",
            calc,
            vat,
        )
    return table


def _logistics_charges_panel(doc: Document) -> Table | None:
    """Logistics service charges (BG-X-42); EXTENDED only.

    One row per :class:`LogisticsServiceCharge` (description,
    applied amount, VAT category + rate). Returns ``None`` for
    BASIC / COMFORT documents and for EXTENDED documents that
    don't carry any logistics charge.
    """
    items = doc.trade.settlement.logistics_service_charges or []
    if not items:
        return None
    currency = doc.trade.settlement.currency_code
    table = Table(
        title="Logistics service charges (BG-X-42)",
        title_style="bold",
        header_style="bold",
        border_style="blue",
        expand=True,
    )
    table.add_column("Description")
    table.add_column(f"Amount [{currency}]", justify="right")
    table.add_column("VAT", justify="right", no_wrap=True)
    for lsc in items:
        # Each logistics charge has 1..* AppliedTradeTax rows; in the
        # common case there's exactly one — render its category + rate.
        # If there are multiple, join with " / ".
        vat_cells = []
        for atx in lsc.applied_trade_tax:
            rate = atx.rate_applicable_percent
            vat_cells.append(
                f"{rate}% {atx.category_code.value}"
                if rate is not None
                else atx.category_code.value
            )
        table.add_row(
            lsc.description,
            f"{lsc.applied_amount}",
            " / ".join(vat_cells) if vat_cells else "-",
        )
    return table


def _advance_payments_panel(doc: Document) -> Table | None:
    """Advance payments / prepayments (BG-X-45); EXTENDED only.

    One row per :class:`AdvancePayment` (received date, paid amount,
    included tax category + rate + amount, optional prepayment
    invoice reference). Returns ``None`` for BASIC / COMFORT
    documents and for EXTENDED documents with no prepayment.
    """
    items = doc.trade.settlement.advance_payments or []
    if not items:
        return None
    currency = doc.trade.settlement.currency_code
    table = Table(
        title="Advance payments (BG-X-45)",
        title_style="bold",
        header_style="bold",
        border_style="blue",
        expand=True,
    )
    table.add_column("Received", no_wrap=True)
    table.add_column(f"Paid [{currency}]", justify="right")
    table.add_column("Included VAT", justify="right", no_wrap=True)
    table.add_column("Prepayment invoice")
    for adv in items:
        # IncludedTradeTax is 1..* per XSD; common case is one row.
        # Render each as "<calculated> @ <rate>% <category>" and
        # join with " / " when several.
        vat_cells: list[str] = []
        for tax in adv.included_trade_tax:
            rate = tax.rate_applicable_percent
            calc = tax.calculated_amount
            cell = f"{calc}" if calc is not None else "—"
            if rate is not None:
                cell = f"{cell} @ {rate}% {tax.category_code.value}"
            else:
                cell = f"{cell} {tax.category_code.value}"
            vat_cells.append(cell)
        ref = adv.invoice_referenced_document
        ref_cell = "—"
        if ref is not None:
            ref_cell = ref.issuer_assigned_id
            if ref.issue_date_time is not None:
                ref_cell = f"{ref_cell} ({ref.issue_date_time.isoformat()})"
        table.add_row(
            adv.received_date_time.isoformat() if adv.received_date_time else "—",
            f"{adv.paid_amount}",
            " / ".join(vat_cells) if vat_cells else "-",
            ref_cell,
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
        or settlement.payee
    ):
        return None
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold", no_wrap=True)
    grid.add_column()
    if settlement.payee is not None:
        grid.add_row("Payee (BG-10):", settlement.payee.name)
    for t in settlement.terms or []:
        if t.description:
            grid.add_row("Terms:", t.description)
        if t.due:
            grid.add_row("Due date:", t.due.isoformat())
        if t.debit_mandate_id:
            grid.add_row("SEPA mandate:", t.debit_mandate_id)
    for pm in settlement.payment_means or []:
        grid.add_row("Means (BT-81):", pm.type_code)
        if pm.payee is not None:
            if pm.payee.iban_id:
                grid.add_row("IBAN (BT-84):", pm.payee.iban_id)
            if pm.payee.proprietary_id:
                grid.add_row("Account (BT-84):", pm.payee.proprietary_id)
            if pm.payee.account_name:
                grid.add_row("Account name (BT-85):", pm.payee.account_name)
        if pm.creditor_institution is not None and pm.creditor_institution.bic_id:
            grid.add_row("BIC (BT-86):", pm.creditor_institution.bic_id)
        if pm.financial_card is not None:
            holder = pm.financial_card.cardholder_name
            value = f"··· {pm.financial_card.id}"
            if holder:
                value += f" ({holder})"
            grid.add_row("Card (BG-18):", value)
        if pm.payer is not None and pm.payer.iban_id:
            grid.add_row("Debited IBAN (BT-91):", pm.payer.iban_id)
    if settlement.payment_reference:
        grid.add_row("Reference (BT-83):", settlement.payment_reference)
    if settlement.creditor_reference:
        grid.add_row("Creditor id (BT-90):", settlement.creditor_reference)
    return Panel(grid, title="[bold]Payment[/bold]", border_style="magenta")
